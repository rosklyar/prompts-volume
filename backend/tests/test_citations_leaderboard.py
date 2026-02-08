"""Integration test for aggregated citations leaderboard endpoint.

Tests:
- Create a group with prompts that have evaluations with citations
- Generate two reports
- Call the citations-leaderboard endpoint
- Verify aggregated counts with deduplication across reports
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.evals_models import (
    GroupReport,
    GroupReportItem,
    PromptEvaluation,
    ReportItemStatus,
    EvaluationStatus,
)


def _make_session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def _get_prompts_for_topic(client, auth_headers, topic_id: int = 1) -> list[dict]:
    response = client.get(
        f"/prompts/api/v1/prompts?topic_ids={topic_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    prompts = []
    for topic in response.json()["topics"]:
        for prompt in topic["prompts"]:
            prompts.append({"id": prompt["id"], "prompt_text": prompt["prompt_text"]})
    return prompts


def _create_group_with_prompts(
    client,
    auth_headers,
    title: str,
    prompt_ids: list[int],
) -> int:
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": title,
            "topic": {"existing_topic_id": 1},
            "brand": {
                "name": f"Brand-{title}",
                "domain": f"{title.lower()}.com",
                "variations": [],
            },
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201, f"Group creation failed: {group_response.json()}"
    group_id = group_response.json()["id"]

    add_resp = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_resp.status_code == 200
    return group_id


async def _create_reports_with_citations(
    session_maker: async_sessionmaker[AsyncSession],
    group_id: int,
    user_id: str,
    prompt_ids: list[int],
) -> list[int]:
    """Create two reports with overlapping evaluations that have citations.

    Returns list of report IDs created.
    """
    async with session_maker() as session:
        # Get existing evaluations for the prompts
        result = await session.execute(
            select(PromptEvaluation)
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
        )
        evaluations = list(result.scalars().all())

        # Update evaluations to have citations
        citations_data = [
            [
                {"url": "https://example.com/page1", "text": "Citation 1"},
                {"url": "https://other.com/article", "text": "Citation 2"},
            ],
            [
                {"url": "https://example.com/page2", "text": "Citation 3"},
                {"url": "https://third.org/doc", "text": "Citation 4"},
            ],
            [
                {"url": "https://other.com/news", "text": "Citation 5"},
            ],
        ]

        eval_by_prompt: dict[int, PromptEvaluation] = {}
        for e in evaluations:
            if e.prompt_id not in eval_by_prompt:
                eval_by_prompt[e.prompt_id] = e

        # Update answers with citations
        for i, pid in enumerate(prompt_ids[:3]):
            if pid in eval_by_prompt:
                ev = eval_by_prompt[pid]
                ev.answer = {
                    "response": f"Test response {i}",
                    "citations": citations_data[i] if i < len(citations_data) else [],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                session.add(ev)

        await session.flush()

        # Create report 1 with all prompts
        report1 = GroupReport(
            group_id=group_id,
            user_id=user_id,
            assistant_id=1,
            country_id=1,
            title="Report 1",
            total_prompts=len(prompt_ids),
            prompts_with_data=min(len(prompt_ids), len(eval_by_prompt)),
            prompts_awaiting=0,
            total_evaluations_loaded=min(len(prompt_ids), len(eval_by_prompt)),
            total_cost=Decimal("0"),
            is_complete=True,
        )
        session.add(report1)
        await session.flush()

        for pid in prompt_ids:
            ev = eval_by_prompt.get(pid)
            item = GroupReportItem(
                report_id=report1.id,
                prompt_id=pid,
                evaluation_id=ev.id if ev else None,
                status=ReportItemStatus.INCLUDED if ev else ReportItemStatus.AWAITING,
                is_fresh=True,
            )
            session.add(item)

        # Create report 2 (same evaluations - tests deduplication)
        report2 = GroupReport(
            group_id=group_id,
            user_id=user_id,
            assistant_id=1,
            country_id=1,
            title="Report 2",
            total_prompts=len(prompt_ids),
            prompts_with_data=min(len(prompt_ids), len(eval_by_prompt)),
            prompts_awaiting=0,
            total_evaluations_loaded=min(len(prompt_ids), len(eval_by_prompt)),
            total_cost=Decimal("0"),
            is_complete=True,
        )
        session.add(report2)
        await session.flush()

        for pid in prompt_ids:
            ev = eval_by_prompt.get(pid)
            item = GroupReportItem(
                report_id=report2.id,
                prompt_id=pid,
                evaluation_id=ev.id if ev else None,
                status=ReportItemStatus.INCLUDED if ev else ReportItemStatus.AWAITING,
                is_fresh=False,
            )
            session.add(item)

        await session.commit()
        return [report1.id, report2.id]


def test_citations_leaderboard_aggregation(
    client,
    test_engine,
    create_verified_user,
):
    """Test aggregated citations leaderboard endpoint.

    Creates a group with prompts that have evaluations with citations,
    generates two reports (with overlapping evaluations), and verifies
    the aggregated leaderboard deduplicates citations correctly.
    """
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    # Create user
    user_email = f"citations-test-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123")

    # Get prompts
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 3
    prompt_ids = [prompts[0]["id"], prompts[1]["id"], prompts[2]["id"]]

    # Create group with prompts
    group_id = _create_group_with_prompts(
        client, auth_headers, "CitationsTest", prompt_ids
    )

    # Get user ID from token
    me_resp = client.get("/api/v1/users/me", headers=auth_headers)
    assert me_resp.status_code == 200
    user_id = me_resp.json()["id"]

    # Create reports with citations directly in DB
    report_ids = run_async(
        _create_reports_with_citations(session_maker, group_id, user_id, prompt_ids)
    )
    assert len(report_ids) == 2

    # Call the citations leaderboard endpoint
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/citations-leaderboard?period=30d",
        headers=auth_headers,
    )
    assert resp.status_code == 200, f"Citations endpoint failed: {resp.json()}"

    data = resp.json()
    assert data["group_id"] == group_id
    assert data["preset_used"] == "30d"
    assert "from_date" in data
    assert "to_date" in data
    assert data["assistant_id"] is None
    assert data["reports_included"] == 2

    leaderboard = data["citation_leaderboard"]
    assert leaderboard["total_citations"] > 0

    # Verify deduplication: same evaluations in 2 reports should yield
    # same counts as a single report (not doubled)
    domain_paths = {d["path"]: d["count"] for d in leaderboard["domains"]}
    assert "example.com" in domain_paths
    assert "other.com" in domain_paths

    # example.com appears in prompt 0 and prompt 1 citations = 2 citations
    assert domain_paths["example.com"] == 2
    # other.com appears in prompt 0 and prompt 2 citations = 2 citations
    assert domain_paths["other.com"] == 2


def test_citations_leaderboard_with_assistant_filter(
    client,
    test_engine,
    create_verified_user,
):
    """Test that assistant_id filter works on citations leaderboard."""
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    user_email = f"citations-filter-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123")

    prompts = _get_prompts_for_topic(client, auth_headers)
    prompt_ids = [prompts[0]["id"], prompts[1]["id"]]

    group_id = _create_group_with_prompts(
        client, auth_headers, "FilterTest", prompt_ids
    )

    me_resp = client.get("/api/v1/users/me", headers=auth_headers)
    user_id = me_resp.json()["id"]

    run_async(
        _create_reports_with_citations(session_maker, group_id, user_id, prompt_ids)
    )

    # Filter by assistant_id=1 (should return data)
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/citations-leaderboard?period=30d&assistant_id=1",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assistant_id"] == 1
    assert data["reports_included"] == 2

    # Filter by assistant_id=999 (no reports for this assistant)
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/citations-leaderboard?period=30d&assistant_id=999",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reports_included"] == 0
    assert data["citation_leaderboard"]["total_citations"] == 0


def test_citations_leaderboard_requires_auth(client):
    """Test that the endpoint requires authentication."""
    resp = client.get(
        "/reports/api/v1/groups/1/citations-leaderboard?period=7d"
    )
    assert resp.status_code == 401


def test_citations_leaderboard_invalid_period(
    client,
    create_verified_user,
):
    """Test that invalid period parameter is rejected."""
    user_email = f"citations-period-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123")

    resp = client.get(
        "/reports/api/v1/groups/1/citations-leaderboard?period=999d",
        headers=auth_headers,
    )
    assert resp.status_code == 422  # Validation error
