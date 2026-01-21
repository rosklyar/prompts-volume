"""Integration test for daily scheduling batch processing.

Tests the complete daily batch flow:
1. Create 2 users with scheduled groups
2. Mix of fresh and stale prompts
3. Trigger daily batch
4. Simulate webhook callbacks
5. Verify reports generated for both groups
"""

import asyncio
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.billing.models.domain import ChargeResult
from src.database.evals_models import (
    DailyBatchGroupStatus,
    DailyBatchStatus,
    DailyScheduleBatch,
    DailyBatchGroupResult,
    GroupReport,
    PromptEvaluation,
)
from src.database.models import PromptGroup


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

# Default topic using seeded topic ID 1
DEFAULT_TOPIC = {"existing_topic_id": 1}


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


def _create_group_with_schedule(
    client,
    auth_headers,
    title: str,
    topic_id: int = 1,
) -> int:
    """Create a group with schedule enabled."""
    # Create group
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": title,
            "topic": {"existing_topic_id": topic_id},
            "brand": {"name": f"Brand-{title}", "domain": f"{title.lower()}.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201, f"Group creation failed: {group_response.json()}"
    group_id = group_response.json()["id"]

    # Enable schedule
    schedule_response = client.put(
        f"/prompt-groups/api/v1/groups/{group_id}/schedule",
        json={"enabled": True},
        headers=auth_headers,
    )
    assert schedule_response.status_code == 200, f"Enable schedule failed: {schedule_response.json()}"
    assert schedule_response.json()["enabled"] is True

    return group_id


def _make_session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    """Create async session maker for direct DB access."""
    return async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def _trigger_daily_batch_async(session_maker) -> int | None:
    """Manually trigger daily batch using session maker."""
    from src.daily_scheduling.services.daily_batch_orchestrator import DailyBatchOrchestrator
    from src.brightdata.services.brightdata_service import BrightDataService
    from src.brightdata.services.batch_service import BrightDataBatchService

    async with session_maker() as prompts_session:
        async with session_maker() as evals_session:
            # Create a BrightData service WITHOUT http client (only registers batches)
            batch_service = BrightDataBatchService(evals_session)
            brightdata_service = BrightDataService(
                client=None,  # No HTTP calls
                batch_service=batch_service,
                webhook_base_url="http://testserver",
                webhook_secret="test-secret",
            )

            charge_service = NoOpChargeService()
            orchestrator = DailyBatchOrchestrator(
                prompts_session,
                evals_session,
                charge_service=charge_service,
                brightdata_service=brightdata_service,
            )

            batch_id = await orchestrator.start_daily_batch()
            return batch_id


async def _get_daily_batch_async(session_maker, batch_id: int) -> DailyScheduleBatch | None:
    """Get daily batch by ID."""
    async with session_maker() as session:
        result = await session.execute(
            select(DailyScheduleBatch).where(DailyScheduleBatch.id == batch_id)
        )
        return result.scalar_one_or_none()


async def _get_group_results_async(session_maker, batch_id: int) -> list[DailyBatchGroupResult]:
    """Get group results for a batch."""
    async with session_maker() as session:
        result = await session.execute(
            select(DailyBatchGroupResult).where(DailyBatchGroupResult.batch_id == batch_id)
        )
        return list(result.scalars().all())


async def _get_reports_for_groups_async(session_maker, group_ids: list[int]) -> list[GroupReport]:
    """Get reports for groups."""
    async with session_maker() as session:
        result = await session.execute(
            select(GroupReport).where(GroupReport.group_id.in_(group_ids))
        )
        return list(result.scalars().all())


async def _get_group_async(session_maker, group_id: int) -> PromptGroup | None:
    """Get group by ID."""
    async with session_maker() as session:
        result = await session.execute(
            select(PromptGroup).where(PromptGroup.id == group_id)
        )
        return result.scalar_one_or_none()


async def _make_evaluations_stale_async(
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


async def _trigger_report_generation_async(session_maker, batch_id: int) -> int:
    """Trigger report generation for a batch."""
    from src.daily_scheduling.services.batch_report_generator import BatchReportGenerator
    from src.daily_scheduling.repositories.daily_batch_repo import DailyBatchRepository

    async with session_maker() as prompts_session:
        async with session_maker() as evals_session:
            # First, update batch status to GENERATING
            batch_repo = DailyBatchRepository(evals_session)
            await batch_repo.update_batch_status(batch_id, DailyBatchStatus.GENERATING)
            await evals_session.commit()

            # Generate reports
            charge_service = NoOpChargeService()
            generator = BatchReportGenerator(
                prompts_session, evals_session, charge_service=charge_service
            )
            count = await generator.generate_all_reports(batch_id)

            await evals_session.commit()
            await prompts_session.commit()

            return count


def test_daily_batch_with_fresh_and_stale_prompts(
    client,
    test_engine,
    create_verified_user,
    simulate_webhook,
):
    """Test complete daily batch flow with 2 users and fresh/stale prompts.

    Scenario:
    - User 1: Group A with 2 prompts (P1 fresh, P2 stale)
    - User 2: Group B with 2 prompts (P3, P4 both stale)

    Expected:
    - Daily batch collects both groups
    - P2, P3, P4 sent to BrightData (P1 already fresh)
    - After webhook, reports generated for both groups
    """
    # Create session maker for async operations
    session_maker = _make_session_maker(test_engine)

    # === STEP 1: Create two users ===
    user1_email = f"user1-{uuid.uuid4()}@example.com"
    user2_email = f"user2-{uuid.uuid4()}@example.com"

    user1_headers = create_verified_user(user1_email, "testpassword123", "User One")
    user2_headers = create_verified_user(user2_email, "testpassword123", "User Two")

    # === STEP 2: Get available prompts ===
    prompts = _get_prompts_for_topic(client, user1_headers)
    assert len(prompts) >= 4, "Need at least 4 prompts for test"

    # Assign prompts: P1, P2 for user1; P3, P4 for user2
    p1, p2, p3, p4 = prompts[0], prompts[1], prompts[2], prompts[3]
    prompts_dict = {p["id"]: p["prompt_text"] for p in prompts}

    # === STEP 3: Create scheduled groups ===
    group_a_id = _create_group_with_schedule(client, user1_headers, "GroupA")
    group_b_id = _create_group_with_schedule(client, user2_headers, "GroupB")

    # === STEP 4: Add prompts to groups ===
    # Group A: P1, P2
    add_resp = client.post(
        f"/prompt-groups/api/v1/groups/{group_a_id}/prompts",
        json={"prompt_ids": [p1["id"], p2["id"]]},
        headers=user1_headers,
    )
    assert add_resp.status_code == 200, f"Add to group A failed: {add_resp.json()}"

    # Group B: P3, P4
    add_resp = client.post(
        f"/prompt-groups/api/v1/groups/{group_b_id}/prompts",
        json={"prompt_ids": [p3["id"], p4["id"]]},
        headers=user2_headers,
    )
    assert add_resp.status_code == 200, f"Add to group B failed: {add_resp.json()}"

    # === STEP 4.5: Make all seeded evaluations stale ===
    # This ensures that P2, P3, P4 have stale evaluations (>24h old)
    # P1 will become fresh in the next step via webhook
    asyncio.get_event_loop().run_until_complete(
        _make_evaluations_stale_async(
            session_maker,
            [p1["id"], p2["id"], p3["id"], p4["id"]],
            hours_ago=48,
        )
    )

    # === STEP 5: Make P1 fresh by requesting and simulating webhook ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": [p1["id"]], "country_id": 1},
        headers=user1_headers,
    )
    assert request_resp.status_code == 200, f"Request fresh failed: {request_resp.json()}"
    p1_batch_id = request_resp.json()["batch_id"]

    # Simulate webhook for P1
    webhook_items = [
        {"prompt": prompts_dict[p1["id"]], "answer_text": "Fresh answer for P1", "citations": []}
    ]
    webhook_resp = simulate_webhook(p1_batch_id, webhook_items)
    assert webhook_resp.status_code == 200, f"Webhook for P1 failed: {webhook_resp.json()}"

    # P1 is now fresh (<24h old)

    # === STEP 6: Trigger daily batch ===
    batch_id = asyncio.get_event_loop().run_until_complete(
        _trigger_daily_batch_async(session_maker)
    )
    assert batch_id is not None, "Daily batch was not created"

    # Helper to run async in sync context
    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    # === STEP 7: Verify batch was created correctly ===
    batch = run_async(_get_daily_batch_async(session_maker, batch_id))
    assert batch is not None, "Batch not found"
    assert batch.scheduled_date == date.today()
    assert set(batch.group_ids) == {group_a_id, group_b_id}
    assert batch.total_prompts == 4
    assert batch.prompts_already_fresh == 1  # P1
    assert batch.prompts_needing_refresh == 3  # P2, P3, P4

    # Get BrightData batch IDs from the daily batch
    brightdata_batch_ids = batch.batch_ids
    assert len(brightdata_batch_ids) >= 1, "Expected at least 1 BrightData batch"

    # === STEP 8: Simulate webhook for P2, P3, P4 ===
    # The daily batch would have triggered BrightData with prompts needing refresh
    for bd_batch_id in brightdata_batch_ids:
        webhook_items = [
            {"prompt": prompts_dict[p2["id"]], "answer_text": "Fresh answer for P2", "citations": []},
            {"prompt": prompts_dict[p3["id"]], "answer_text": "Fresh answer for P3", "citations": []},
            {"prompt": prompts_dict[p4["id"]], "answer_text": "Fresh answer for P4", "citations": []},
        ]
        webhook_resp = simulate_webhook(bd_batch_id, webhook_items)
        assert webhook_resp.status_code == 200, f"Webhook failed: {webhook_resp.json()}"

    # === STEP 9: Trigger report generation ===
    report_count = run_async(_trigger_report_generation_async(session_maker, batch_id))
    assert report_count == 2, f"Expected 2 reports, got {report_count}"

    # === STEP 10: Verify batch completed ===
    batch = run_async(_get_daily_batch_async(session_maker, batch_id))
    assert batch.status == DailyBatchStatus.COMPLETED
    assert batch.completed_at is not None

    # === STEP 11: Verify group results ===
    group_results = run_async(_get_group_results_async(session_maker, batch_id))
    assert len(group_results) == 2

    for result in group_results:
        assert result.status == DailyBatchGroupStatus.COMPLETED
        assert result.report_id is not None

    # Verify specific group stats
    group_a_result = next(r for r in group_results if r.group_id == group_a_id)
    group_b_result = next(r for r in group_results if r.group_id == group_b_id)

    assert group_a_result.prompts_in_group == 2
    assert group_a_result.prompts_already_fresh == 1  # P1
    assert group_a_result.prompts_needing_refresh == 1  # P2

    assert group_b_result.prompts_in_group == 2
    assert group_b_result.prompts_already_fresh == 0
    assert group_b_result.prompts_needing_refresh == 2  # P3, P4

    # === STEP 12: Verify reports exist ===
    reports = run_async(_get_reports_for_groups_async(session_maker, [group_a_id, group_b_id]))
    assert len(reports) == 2

    # Each report should have the correct number of items
    for report in reports:
        assert report.total_prompts == 2
        assert report.prompts_with_data == 2
        assert report.prompts_awaiting == 0

    # === STEP 13: Verify schedule_last_run_at updated ===
    group_a = run_async(_get_group_async(session_maker, group_a_id))
    group_b = run_async(_get_group_async(session_maker, group_b_id))

    assert group_a.schedule_last_run_at is not None
    assert group_b.schedule_last_run_at is not None

    # === STEP 14: Verify reports accessible via API ===
    # User 1 can see their report
    reports_resp = client.get(
        f"/reports/api/v1/groups/{group_a_id}/reports",
        headers=user1_headers,
    )
    assert reports_resp.status_code == 200, f"Get reports failed: {reports_resp.json()}"
    user1_reports = reports_resp.json()["reports"]
    assert len(user1_reports) >= 1

    # User 2 can see their report
    reports_resp = client.get(
        f"/reports/api/v1/groups/{group_b_id}/reports",
        headers=user2_headers,
    )
    assert reports_resp.status_code == 200, f"Get reports failed: {reports_resp.json()}"
    user2_reports = reports_resp.json()["reports"]
    assert len(user2_reports) >= 1
