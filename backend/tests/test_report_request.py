"""Integration test for unified report request flow.

Tests the complete report request lifecycle:
1. Create a report request for a group with stale/absent prompts
2. Verify request is created in AWAITING status
3. Simulate BrightData webhook callbacks
4. Verify request moves to READY then COMPLETED
5. Verify report was auto-generated
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.billing.models.domain import ChargeResult
from src.database.evals_models import (
    GroupReport,
    PromptEvaluation,
    ReportRequest,
    ReportRequestStatus,
)


class NoOpChargeService:
    """No-op charge service for tests.

    Returns success without actually charging the user.
    """

    async def charge_for_evaluations(
        self,
        user_id: str,
        evaluation_ids: list[int],
    ) -> ChargeResult:
        """Return success without charging."""
        return ChargeResult(
            charged_evaluation_ids=evaluation_ids,
            skipped_evaluation_ids=[],
            total_charged=Decimal("0"),
            remaining_balance=Decimal("0"),
        )

    async def preview_charge(
        self,
        user_id: str,
        evaluation_ids: list[int],
    ) -> dict:
        """Preview returns zero cost."""
        return {
            "fresh_count": len(evaluation_ids),
            "already_consumed_count": 0,
            "estimated_cost": Decimal("0"),
            "user_balance": Decimal("0"),
            "affordable_count": len(evaluation_ids),
            "needs_top_up": False,
        }


def _make_session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    """Create async session maker for direct DB access."""
    return async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def _get_prompts_for_topic(client, auth_headers, topic_id: int = 1) -> list[dict]:
    """Fetch prompts from database for a given topic."""
    response = client.get(
        f"/prompts/api/v1/prompts?topic_ids={topic_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200, f"Failed to get prompts: {response.json()}"
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
    """Create a group and add prompts to it."""
    # Create group
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": title,
            "topic": {"existing_topic_id": 1},
            "brand": {"name": f"Brand-{title}", "domain": f"{title.lower()}.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201, f"Group creation failed: {group_response.json()}"
    group_id = group_response.json()["id"]

    # Add prompts
    add_resp = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_resp.status_code == 200, f"Add prompts failed: {add_resp.json()}"

    return group_id


async def _make_evaluations_stale(
    session_maker,
    prompt_ids: list[int],
    hours_ago: int = 48,
) -> None:
    """Make evaluations for given prompts stale by setting old timestamps."""
    async with session_maker() as session:
        stale_time = datetime.now() - timedelta(hours=hours_ago)
        await session.execute(
            update(PromptEvaluation)
            .where(PromptEvaluation.prompt_id.in_(prompt_ids))
            .values(completed_at=stale_time)
        )
        await session.commit()


async def _get_report_request(session_maker, request_id: int) -> ReportRequest | None:
    """Get report request by ID."""
    async with session_maker() as session:
        result = await session.execute(
            select(ReportRequest).where(ReportRequest.id == request_id)
        )
        return result.scalar_one_or_none()


async def _get_report_for_group(session_maker, group_id: int) -> GroupReport | None:
    """Get latest report for a group."""
    async with session_maker() as session:
        result = await session.execute(
            select(GroupReport)
            .where(GroupReport.group_id == group_id)
            .order_by(GroupReport.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()


async def _check_and_process_ready_requests(session_maker) -> int:
    """Process ready requests to generate reports."""
    from src.reports.services.report_service import ReportService
    from src.reports.services.report_request_service import ReportRequestService

    async with session_maker() as prompts_session:
        async with session_maker() as evals_session:
            charge_service = NoOpChargeService()
            report_service = ReportService(prompts_session, evals_session, charge_service)
            request_service = ReportRequestService(
                prompts_session,
                evals_session,
                report_service=report_service,
            )

            count = await request_service.generate_ready_reports()
            await evals_session.commit()
            await prompts_session.commit()
            return count


def test_report_request_full_flow_with_stale_prompts(
    client,
    test_engine,
    create_verified_user,
    simulate_webhook,
):
    """Test complete report request flow with stale prompts.

    Scenario:
    - User creates a group with 3 prompts (P1, P2, P3)
    - All 3 prompts have stale evaluations (>24h old)
    - User creates a report request
    - BrightData webhook returns with fresh answers
    - Report is auto-generated

    This tests the unified manual report request flow.
    """
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    # === STEP 1: Create user ===
    user_email = f"report-request-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123", "Test User")

    # === STEP 2: Get available prompts ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 3, "Need at least 3 prompts for test"
    p1, p2, p3 = prompts[0], prompts[1], prompts[2]
    prompt_ids = [p1["id"], p2["id"], p3["id"]]
    prompts_dict = {p["id"]: p["prompt_text"] for p in [p1, p2, p3]}

    # === STEP 3: Create group with prompts ===
    group_id = _create_group_with_prompts(
        client, auth_headers, "TestGroup", prompt_ids
    )

    # === STEP 4: Make all evaluations stale ===
    run_async(_make_evaluations_stale(session_maker, prompt_ids, hours_ago=48))

    # === STEP 5: Create report request ===
    request_resp = client.post(
        f"/reports/api/v1/groups/{group_id}/request",
        json={"assistant_id": 1},
        headers=auth_headers,
    )
    assert request_resp.status_code == 201, f"Create request failed: {request_resp.json()}"

    request_data = request_resp.json()
    request_id = request_data["id"]

    # Verify initial state
    assert request_data["status"] == "awaiting"
    assert request_data["group_id"] == group_id
    assert request_data["total_prompts"] == 3
    assert request_data["prompts_fresh_at_request"] == 0
    assert request_data["prompts_requested"] == 3
    assert request_data["report_id"] is None

    # === STEP 6: Verify request status endpoint ===
    status_resp = client.get(
        f"/reports/api/v1/groups/{group_id}/request-status",
        headers=auth_headers,
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["has_pending"] is True
    assert status_data["request"]["id"] == request_id
    assert status_data["request"]["status"] == "awaiting"

    # === STEP 7: Get the BrightData batch ID from the request ===
    # We need to query directly since batch_ids aren't exposed in API
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj is not None
    assert len(request_obj.batch_ids) >= 1, "Expected at least 1 BrightData batch"

    # === STEP 8: Simulate webhook for all prompts ===
    for batch_id in request_obj.batch_ids:
        webhook_items = [
            {"prompt": prompts_dict[p1["id"]], "answer_text": "Fresh answer for P1", "citations": []},
            {"prompt": prompts_dict[p2["id"]], "answer_text": "Fresh answer for P2", "citations": []},
            {"prompt": prompts_dict[p3["id"]], "answer_text": "Fresh answer for P3", "citations": []},
        ]
        webhook_resp = simulate_webhook(batch_id, webhook_items)
        assert webhook_resp.status_code == 200, f"Webhook failed: {webhook_resp.json()}"

    # === STEP 9: Check request status after webhook ===
    # The webhook handler should have moved the request to READY
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj.status == ReportRequestStatus.READY, f"Expected READY, got {request_obj.status}"

    # === STEP 10: Trigger report generation (simulates scheduler job) ===
    report_count = run_async(_check_and_process_ready_requests(session_maker))
    assert report_count >= 1, "Expected at least 1 report generated"

    # === STEP 11: Verify request completed ===
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj.status == ReportRequestStatus.COMPLETED
    assert request_obj.report_id is not None
    assert request_obj.completed_at is not None

    # === STEP 12: Verify report was generated ===
    report = run_async(_get_report_for_group(session_maker, group_id))
    assert report is not None
    assert report.id == request_obj.report_id
    assert report.total_prompts == 3
    assert report.prompts_with_data == 3
    assert report.prompts_awaiting == 0

    # === STEP 13: Verify request status endpoint shows no pending ===
    status_resp = client.get(
        f"/reports/api/v1/groups/{group_id}/request-status",
        headers=auth_headers,
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    # Request is completed, so no pending
    assert status_data["has_pending"] is False

    # === STEP 14: Verify report accessible via API ===
    reports_resp = client.get(
        f"/reports/api/v1/groups/{group_id}/reports",
        headers=auth_headers,
    )
    assert reports_resp.status_code == 200
    reports_list = reports_resp.json()["reports"]
    assert len(reports_list) >= 1
    assert any(r["id"] == request_obj.report_id for r in reports_list)


def test_report_request_cancel(
    client,
    test_engine,
    create_verified_user,
):
    """Test cancelling a pending report request."""
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    # === STEP 1: Create user and group ===
    user_email = f"cancel-request-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123", "Test User")

    prompts = _get_prompts_for_topic(client, auth_headers)
    p1 = prompts[0]
    group_id = _create_group_with_prompts(client, auth_headers, "CancelGroup", [p1["id"]])

    # Make evaluation stale
    run_async(_make_evaluations_stale(session_maker, [p1["id"]], hours_ago=48))

    # === STEP 2: Create request ===
    request_resp = client.post(
        f"/reports/api/v1/groups/{group_id}/request",
        json={"assistant_id": 1},
        headers=auth_headers,
    )
    assert request_resp.status_code == 201
    request_id = request_resp.json()["id"]

    # === STEP 3: Cancel request ===
    cancel_resp = client.delete(
        f"/reports/api/v1/groups/{group_id}/request",
        headers=auth_headers,
    )
    assert cancel_resp.status_code == 204

    # === STEP 4: Verify cancelled ===
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj.status == ReportRequestStatus.CANCELLED
    assert request_obj.completed_at is not None

    # === STEP 5: Verify no pending request ===
    status_resp = client.get(
        f"/reports/api/v1/groups/{group_id}/request-status",
        headers=auth_headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["has_pending"] is False
