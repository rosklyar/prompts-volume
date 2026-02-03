"""Integration test for dashboard analytics endpoint.

Tests:
- Create a group with brand and competitors
- Generate reports with brand mentions and citations
- Call the dashboard endpoint with period filtering
- Verify visibility percentages, competitors ranking, sources, and prompt gaps
- Verify aggregation and deduplication across multiple reports
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


def _create_group_with_brand(
    client,
    auth_headers,
    title: str,
    prompt_ids: list[int],
    brand_name: str = "TestBrand",
    competitors: list[dict] | None = None,
) -> int:
    """Create a group with brand and competitors configured."""
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": title,
            "topic": {"existing_topic_id": 1},
            "brand": {
                "name": brand_name,
                "domain": f"{brand_name.lower()}.com",
                "variations": [brand_name.lower()],
            },
            "competitors": competitors or [
                {"name": "Competitor1", "domain": "comp1.com", "variations": []},
                {"name": "Competitor2", "domain": "comp2.com", "variations": []},
            ],
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


async def _create_report_with_brand_mentions(
    session_maker: async_sessionmaker[AsyncSession],
    group_id: int,
    user_id: str,
    prompt_ids: list[int],
    brand_name: str,
    brand_snapshot: dict,
    competitors_snapshot: list[dict],
    *,
    created_at: datetime | None = None,
) -> int:
    """Create a report with evaluations containing brand mentions and citations.

    - Prompt 0: mentions TestBrand and Competitor1, has citations
    - Prompt 1: mentions Competitor1 only, has citations
    - Prompt 2: mentions Competitor2 only, no citations
    - Prompt 3+: no mentions (prompt gaps)
    """
    async with session_maker() as session:
        # Get existing evaluations
        result = await session.execute(
            select(PromptEvaluation)
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
        )
        evaluations = list(result.scalars().all())

        eval_by_prompt: dict[int, PromptEvaluation] = {}
        for e in evaluations:
            if e.prompt_id not in eval_by_prompt:
                eval_by_prompt[e.prompt_id] = e

        # Define answers with brand mentions and citations
        answers_data = [
            {
                "response": f"I recommend {brand_name} and Competitor1 for this task.",
                "citations": [
                    {"url": "https://source1.com/article", "text": "Source 1"},
                    {"url": "https://source2.com/review", "text": "Source 2"},
                ],
            },
            {
                "response": "Competitor1 is a popular choice for this use case.",
                "citations": [
                    {"url": "https://source1.com/guide", "text": "Guide"},
                    {"url": "https://source3.com/docs", "text": "Docs"},
                ],
            },
            {
                "response": "Only Competitor2 offers this specific feature.",
                "citations": [],
            },
            {
                "response": "No specific brand recommendation for this query.",
                "citations": [],
            },
        ]

        # Update evaluations with answers
        for i, pid in enumerate(prompt_ids[:4]):
            if pid in eval_by_prompt and i < len(answers_data):
                ev = eval_by_prompt[pid]
                ev.answer = {
                    **answers_data[i],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                session.add(ev)

        await session.flush()

        # Create report
        report = GroupReport(
            group_id=group_id,
            user_id=user_id,
            assistant_id=1,
            country_id=1,
            title="Dashboard Test Report",
            total_prompts=len(prompt_ids),
            prompts_with_data=min(len(prompt_ids), len(eval_by_prompt)),
            prompts_awaiting=0,
            total_evaluations_loaded=min(len(prompt_ids), len(eval_by_prompt)),
            total_cost=Decimal("0"),
            is_complete=True,
            brand_snapshot=brand_snapshot,
            competitors_snapshot=competitors_snapshot,
        )
        if created_at is not None:
            report.created_at = created_at
        session.add(report)
        await session.flush()

        # Create report items
        for pid in prompt_ids:
            ev = eval_by_prompt.get(pid)
            item = GroupReportItem(
                report_id=report.id,
                prompt_id=pid,
                evaluation_id=ev.id if ev else None,
                status=ReportItemStatus.INCLUDED if ev else ReportItemStatus.AWAITING,
                is_fresh=True,
            )
            session.add(item)

        await session.commit()
        return report.id


def test_dashboard_analytics(
    client,
    test_engine,
    create_verified_user,
):
    """Test dashboard endpoint returns correct brand visibility and analytics."""
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    # Create user
    user_email = f"dashboard-test-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123")

    # Get prompts
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 4
    prompt_ids = [prompts[i]["id"] for i in range(4)]

    brand_name = "TestBrand"
    competitors = [
        {"name": "Competitor1", "domain": "comp1.com", "variations": ["Competitor1"]},
        {"name": "Competitor2", "domain": "comp2.com", "variations": ["Competitor2"]},
    ]

    # Create group with brand
    group_id = _create_group_with_brand(
        client, auth_headers, "DashboardTest", prompt_ids, brand_name, competitors
    )

    # Get user ID
    me_resp = client.get("/api/v1/users/me", headers=auth_headers)
    assert me_resp.status_code == 200
    user_id = me_resp.json()["id"]

    brand_snapshot = {"name": brand_name, "domain": "testbrand.com", "variations": ["testbrand"]}
    competitors_snapshot = competitors

    # Create report with brand mentions
    report_id = run_async(
        _create_report_with_brand_mentions(
            session_maker,
            group_id,
            user_id,
            prompt_ids,
            brand_name,
            brand_snapshot,
            competitors_snapshot,
        )
    )
    assert report_id > 0

    # Call dashboard endpoint with default period (7d)
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/dashboard?assistant_id=1",
        headers=auth_headers,
    )
    assert resp.status_code == 200, f"Dashboard endpoint failed: {resp.json()}"

    data = resp.json()

    # Verify basic structure
    assert data["group_id"] == group_id
    assert data["period"] == "7d"  # Default period
    assert data["reports_included"] == 1
    assert data["assistant_name"] == "ChatGPT"
    assert data["brand_name"] == brand_name

    # Verify brand visibility (TestBrand mentioned in 1/4 prompts = 25%)
    assert data["brand_visibility_percent"] == 25.0

    # Verify competitors are sorted by visibility
    competitors_list = data["competitors"]
    assert len(competitors_list) >= 2

    # Competitor1 mentioned in 2/4 prompts = 50%, should be first
    assert competitors_list[0]["name"] == "Competitor1"
    assert competitors_list[0]["visibility_percent"] == 50.0

    # TestBrand and Competitor2 both at 25%
    brand_entry = next(c for c in competitors_list if c["is_target_brand"])
    assert brand_entry["name"] == brand_name
    assert brand_entry["visibility_percent"] == 25.0

    # Verify sources (citation domains)
    sources = data["sources"]
    assert len(sources) > 0
    source_domains = {s["domain"] for s in sources}
    assert "source1.com" in source_domains

    # Verify prompt gaps (prompts without target brand mention)
    assert data["prompt_gaps_count"] >= 2  # At least prompts 1, 2, 3 don't mention TestBrand


def test_dashboard_no_report_returns_empty(
    client,
    create_verified_user,
):
    """Test dashboard returns empty response when no reports exist."""
    user_email = f"dashboard-empty-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123")

    prompts = _get_prompts_for_topic(client, auth_headers)
    prompt_ids = [prompts[0]["id"]]

    group_id = _create_group_with_brand(
        client, auth_headers, "EmptyDashboard", prompt_ids
    )

    # Call dashboard without creating any report
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/dashboard?assistant_id=1",
        headers=auth_headers,
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["group_id"] == group_id
    assert data["period"] == "7d"
    assert data["reports_included"] == 0
    assert data["brand_visibility_percent"] == 0.0
    assert data["competitors"] == []
    assert data["sources"] == []
    assert data["prompt_gaps"] == []


def test_dashboard_requires_assistant_id(
    client,
    create_verified_user,
):
    """Test that assistant_id parameter is required."""
    user_email = f"dashboard-param-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123")

    prompts = _get_prompts_for_topic(client, auth_headers)
    group_id = _create_group_with_brand(
        client, auth_headers, "ParamTest", [prompts[0]["id"]]
    )

    # Call without assistant_id
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/dashboard",
        headers=auth_headers,
    )
    assert resp.status_code == 422  # Validation error


def test_dashboard_requires_auth(client):
    """Test that the dashboard endpoint requires authentication."""
    resp = client.get(
        "/reports/api/v1/groups/1/dashboard?assistant_id=1"
    )
    assert resp.status_code == 401


def test_dashboard_period_parameter(
    client,
    test_engine,
    create_verified_user,
):
    """Test dashboard respects period parameter and filters reports accordingly."""
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    user_email = f"dashboard-period-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123")

    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 4
    prompt_ids = [prompts[i]["id"] for i in range(4)]

    brand_name = "TestBrand"
    competitors = [
        {"name": "Competitor1", "domain": "comp1.com", "variations": ["Competitor1"]},
    ]

    group_id = _create_group_with_brand(
        client, auth_headers, "PeriodTest", prompt_ids, brand_name, competitors
    )

    me_resp = client.get("/api/v1/users/me", headers=auth_headers)
    user_id = me_resp.json()["id"]

    brand_snapshot = {"name": brand_name, "domain": "testbrand.com", "variations": ["testbrand"]}

    # Create a report within 7d window
    report_id = run_async(
        _create_report_with_brand_mentions(
            session_maker,
            group_id,
            user_id,
            prompt_ids,
            brand_name,
            brand_snapshot,
            competitors,
        )
    )
    assert report_id > 0

    # Test with 7d period - should include the report
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/dashboard?assistant_id=1&period=7d",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "7d"
    assert data["reports_included"] == 1

    # Test with 1d period - should also include (just created)
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/dashboard?assistant_id=1&period=1d",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "1d"
    assert data["reports_included"] == 1

    # Test with 30d period
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/dashboard?assistant_id=1&period=30d",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "30d"
    assert data["reports_included"] == 1


def test_dashboard_invalid_period_returns_422(
    client,
    create_verified_user,
):
    """Test that invalid period values return 422 validation error."""
    user_email = f"dashboard-invalid-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123")

    prompts = _get_prompts_for_topic(client, auth_headers)
    group_id = _create_group_with_brand(
        client, auth_headers, "InvalidPeriodTest", [prompts[0]["id"]]
    )

    # Call with invalid period
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/dashboard?assistant_id=1&period=99d",
        headers=auth_headers,
    )
    assert resp.status_code == 422  # Validation error


def test_dashboard_aggregates_multiple_reports(
    client,
    test_engine,
    create_verified_user,
):
    """Test dashboard aggregates data from multiple reports in time window."""
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    user_email = f"dashboard-multi-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123")

    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 4
    prompt_ids = [prompts[i]["id"] for i in range(4)]

    brand_name = "TestBrand"
    competitors = [
        {"name": "Competitor1", "domain": "comp1.com", "variations": ["Competitor1"]},
    ]

    group_id = _create_group_with_brand(
        client, auth_headers, "MultiReportTest", prompt_ids, brand_name, competitors
    )

    me_resp = client.get("/api/v1/users/me", headers=auth_headers)
    user_id = me_resp.json()["id"]

    brand_snapshot = {"name": brand_name, "domain": "testbrand.com", "variations": ["testbrand"]}

    # Create first report
    report_id_1 = run_async(
        _create_report_with_brand_mentions(
            session_maker,
            group_id,
            user_id,
            prompt_ids,
            brand_name,
            brand_snapshot,
            competitors,
        )
    )
    assert report_id_1 > 0

    # Create second report (slightly newer)
    report_id_2 = run_async(
        _create_report_with_brand_mentions(
            session_maker,
            group_id,
            user_id,
            prompt_ids,
            brand_name,
            brand_snapshot,
            competitors,
        )
    )
    assert report_id_2 > 0

    # Dashboard should show both reports
    resp = client.get(
        f"/reports/api/v1/groups/{group_id}/dashboard?assistant_id=1&period=7d",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reports_included"] == 2
