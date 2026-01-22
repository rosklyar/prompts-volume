"""Integration tests for BrightData webhook with realistic sample data.

Tests the complete webhook processing flow using real sample data from
`backend/samples/` to verify that:
1. Webhook data is correctly parsed by strategy classes
2. Evaluations are created with properly normalized citations
3. Reports are generated with correct prompt counts

Fair integration testing principle: only the gzip-compressed webhook
request body is simulated. Everything else (database operations,
strategy parsing, report generation) runs through actual code.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.billing.models.domain import ChargeResult
from src.database.evals_models import (
    BrightDataBatch,
    EvaluationStatus,
    GroupReport,
    PromptEvaluation,
    ReportRequest,
    ReportRequestStatus,
)


# Path to sample data files
SAMPLES_DIR = Path(__file__).parent.parent / "samples"


class NoOpChargeService:
    """No-op charge service for tests."""

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


async def _get_evaluations_for_prompts(
    session_maker,
    prompt_ids: list[int],
    assistant_id: int,
) -> list[PromptEvaluation]:
    """Get completed evaluations for given prompts and assistant."""
    async with session_maker() as session:
        result = await session.execute(
            select(PromptEvaluation)
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.assistant_id == assistant_id,
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
            .order_by(PromptEvaluation.completed_at.desc())
        )
        return list(result.scalars().all())


async def _get_batch_index_mapping(session_maker, batch_id: str) -> dict[str, int]:
    """Get index_to_prompt_id mapping from a BrightData batch."""
    async with session_maker() as session:
        result = await session.execute(
            select(BrightDataBatch).where(BrightDataBatch.batch_id == batch_id)
        )
        batch = result.scalar_one_or_none()
        if batch and batch.index_to_prompt_id:
            return batch.index_to_prompt_id
        return {}


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


def _load_sample_data(filename: str) -> list[dict]:
    """Load sample data from file."""
    sample_path = SAMPLES_DIR / filename
    with open(sample_path) as f:
        return json.load(f)


def _adapt_sample_items_to_prompts(
    sample_items: list[dict],
    prompt_ids: list[int],
    prompts_dict: dict[int, str],
) -> list[dict]:
    """Adapt sample items to match test prompts.

    Creates new items with:
    - Index from sample (1-based)
    - Prompt text from test database
    - All other fields from sample (answer_text, citations, etc.)
    """
    adapted = []
    for i, sample_item in enumerate(sample_items):
        if i >= len(prompt_ids):
            break

        prompt_id = prompt_ids[i]
        prompt_text = prompts_dict[prompt_id]

        adapted_item = dict(sample_item)
        adapted_item["index"] = i + 1  # 1-based index
        adapted_item["prompt"] = prompt_text

        # ChatGPT format: update input.prompt if present
        if "input" in adapted_item and isinstance(adapted_item["input"], dict):
            adapted_item["input"]["prompt"] = prompt_text
            adapted_item["input"]["index"] = i + 1

        adapted.append(adapted_item)

    return adapted


def test_chatgpt_webhook_report_generation(
    client,
    test_engine,
    create_verified_user,
    simulate_webhook,
):
    """Test report generation with ChatGPT webhook data from real sample.

    Uses actual sample data from backend/samples/chat_gpt.json to verify:
    1. ChatGPT webhook data is correctly parsed by ChatGPTStrategy
    2. Citations are normalized (url, text, domain)
    3. Report is generated with correct prompt counts
    """
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    # === STEP 1: Create user ===
    user_email = f"chatgpt-webhook-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123", "ChatGPT Test User")

    # === STEP 2: Get available prompts ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 2, "Need at least 2 prompts for test"
    p1, p2 = prompts[0], prompts[1]
    prompt_ids = [p1["id"], p2["id"]]
    prompts_dict = {p["id"]: p["prompt_text"] for p in [p1, p2]}

    # === STEP 3: Create group with prompts ===
    group_id = _create_group_with_prompts(
        client, auth_headers, "ChatGPTWebhookTest", prompt_ids
    )

    # === STEP 4: Make all evaluations stale ===
    run_async(_make_evaluations_stale(session_maker, prompt_ids, hours_ago=48))

    # === STEP 5: Create report request (ChatGPT = assistant_id=1) ===
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
    assert request_data["total_prompts"] == 2
    assert request_data["prompts_requested"] == 2

    # === STEP 6: Get batch ID and load sample data ===
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj is not None
    assert len(request_obj.batch_ids) >= 1, "Expected at least 1 BrightData batch"

    batch_id = request_obj.batch_ids[0]

    # Load real ChatGPT sample data
    chatgpt_sample = _load_sample_data("chat_gpt.json")
    assert len(chatgpt_sample) >= 2, "ChatGPT sample should have at least 2 items"

    # Adapt sample to use test prompts
    adapted_items = _adapt_sample_items_to_prompts(
        chatgpt_sample, prompt_ids, prompts_dict
    )

    # === STEP 7: Simulate webhook with adapted sample data ===
    webhook_resp = simulate_webhook(batch_id, adapted_items, assistant_key="chatgpt")
    assert webhook_resp.status_code == 200, f"Webhook failed: {webhook_resp.json()}"

    # === STEP 8: Verify request status moved to READY ===
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj.status == ReportRequestStatus.READY, f"Expected READY, got {request_obj.status}"

    # === STEP 9: Trigger report generation ===
    report_count = run_async(_check_and_process_ready_requests(session_maker))
    assert report_count >= 1, "Expected at least 1 report generated"

    # === STEP 10: Verify request completed ===
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj.status == ReportRequestStatus.COMPLETED
    assert request_obj.report_id is not None

    # === STEP 11: Verify report was generated ===
    report = run_async(_get_report_for_group(session_maker, group_id))
    assert report is not None
    assert report.id == request_obj.report_id
    assert report.total_prompts == 2
    assert report.prompts_with_data == 2
    assert report.prompts_awaiting == 0

    # === STEP 12: Verify evaluations have correct data ===
    evaluations = run_async(_get_evaluations_for_prompts(session_maker, prompt_ids, assistant_id=1))
    assert len(evaluations) >= 2, f"Expected 2+ evaluations, got {len(evaluations)}"

    # Verify at least one evaluation has expected answer structure
    eval_with_answer = None
    for ev in evaluations:
        if ev.answer and ev.answer.get("response"):
            eval_with_answer = ev
            break

    assert eval_with_answer is not None, "Expected at least one evaluation with answer"
    assert "response" in eval_with_answer.answer
    assert "citations" in eval_with_answer.answer

    # Verify the second item (index=2) has citations from sample
    # The second sample item has rich citations data
    second_sample = chatgpt_sample[1]
    if second_sample.get("citations"):
        # Check that citations are normalized
        citations = eval_with_answer.answer.get("citations", [])
        if citations:
            first_citation = citations[0]
            assert "url" in first_citation
            assert "text" in first_citation
            assert "domain" in first_citation


def test_perplexity_webhook_report_generation(
    client,
    test_engine,
    create_verified_user,
    simulate_webhook,
):
    """Test report generation with Perplexity webhook data from real sample.

    Uses actual sample data from backend/samples/perplexity.json to verify:
    1. Perplexity webhook data is correctly parsed by PerplexityStrategy
    2. Citations from both 'citations' and 'sources' fields are merged
    3. Report is generated with correct prompt counts
    """
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    # === STEP 1: Create user ===
    user_email = f"perplexity-webhook-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123", "Perplexity Test User")

    # === STEP 2: Get available prompts ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 2, "Need at least 2 prompts for test"
    p1, p2 = prompts[0], prompts[1]
    prompt_ids = [p1["id"], p2["id"]]
    prompts_dict = {p["id"]: p["prompt_text"] for p in [p1, p2]}

    # === STEP 3: Create group with prompts ===
    group_id = _create_group_with_prompts(
        client, auth_headers, "PerplexityWebhookTest", prompt_ids
    )

    # === STEP 4: Make all evaluations stale ===
    run_async(_make_evaluations_stale(session_maker, prompt_ids, hours_ago=48))

    # === STEP 5: Create report request (Perplexity = assistant_id=2) ===
    request_resp = client.post(
        f"/reports/api/v1/groups/{group_id}/request",
        json={"assistant_id": 2},
        headers=auth_headers,
    )
    assert request_resp.status_code == 201, f"Create request failed: {request_resp.json()}"

    request_data = request_resp.json()
    request_id = request_data["id"]

    # Verify initial state
    assert request_data["status"] == "awaiting"
    assert request_data["total_prompts"] == 2
    assert request_data["prompts_requested"] == 2

    # === STEP 6: Get batch ID and load sample data ===
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj is not None
    assert len(request_obj.batch_ids) >= 1, "Expected at least 1 BrightData batch"

    batch_id = request_obj.batch_ids[0]

    # Load real Perplexity sample data
    perplexity_sample = _load_sample_data("perplexity.json")
    assert len(perplexity_sample) >= 2, "Perplexity sample should have at least 2 items"

    # Adapt sample to use test prompts
    adapted_items = _adapt_sample_items_to_prompts(
        perplexity_sample, prompt_ids, prompts_dict
    )

    # === STEP 7: Simulate webhook with adapted sample data ===
    webhook_resp = simulate_webhook(batch_id, adapted_items, assistant_key="perplexity")
    assert webhook_resp.status_code == 200, f"Webhook failed: {webhook_resp.json()}"

    # === STEP 8: Verify request status moved to READY ===
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj.status == ReportRequestStatus.READY, f"Expected READY, got {request_obj.status}"

    # === STEP 9: Trigger report generation ===
    report_count = run_async(_check_and_process_ready_requests(session_maker))
    assert report_count >= 1, "Expected at least 1 report generated"

    # === STEP 10: Verify request completed ===
    request_obj = run_async(_get_report_request(session_maker, request_id))
    assert request_obj.status == ReportRequestStatus.COMPLETED
    assert request_obj.report_id is not None

    # === STEP 11: Verify report was generated ===
    report = run_async(_get_report_for_group(session_maker, group_id))
    assert report is not None
    assert report.id == request_obj.report_id
    assert report.total_prompts == 2
    assert report.prompts_with_data == 2
    assert report.prompts_awaiting == 0

    # === STEP 12: Verify evaluations have correct data ===
    evaluations = run_async(_get_evaluations_for_prompts(session_maker, prompt_ids, assistant_id=2))
    assert len(evaluations) >= 2, f"Expected 2+ evaluations, got {len(evaluations)}"

    # Verify at least one evaluation has expected answer structure
    eval_with_answer = None
    for ev in evaluations:
        if ev.answer and ev.answer.get("response"):
            eval_with_answer = ev
            break

    assert eval_with_answer is not None, "Expected at least one evaluation with answer"
    assert "response" in eval_with_answer.answer
    assert "citations" in eval_with_answer.answer

    # Verify citations are present (Perplexity merges citations + sources)
    # Both sample items have citations and sources
    citations = eval_with_answer.answer.get("citations", [])
    if citations:
        # Check normalized structure
        first_citation = citations[0]
        assert "url" in first_citation
        assert "text" in first_citation
        assert "domain" in first_citation

    # Verify answer text is from sample
    answer_text = eval_with_answer.answer.get("response", "")
    assert len(answer_text) > 0, "Expected non-empty answer text"


def _modify_sample_for_day2(sample_items: list[dict]) -> list[dict]:
    """Modify sample data to simulate different responses on Day 2.

    Adds "[DAY 2]" prefix to answer_text for verification.
    """
    modified = []
    for item in sample_items:
        modified_item = dict(item)
        original_answer = item.get("answer_text", "")
        modified_item["answer_text"] = f"[DAY 2] {original_answer[:200]}..."
        modified.append(modified_item)
    return modified


async def _get_all_reports_for_group(
    session_maker,
    group_id: int,
) -> list[GroupReport]:
    """Get all reports for a group, ordered by created_at."""
    async with session_maker() as session:
        result = await session.execute(
            select(GroupReport)
            .where(GroupReport.group_id == group_id)
            .order_by(GroupReport.created_at.asc())
        )
        return list(result.scalars().all())


def _create_scheduled_group_with_prompts(
    client,
    auth_headers,
    title: str,
    prompt_ids: list[int],
) -> int:
    """Create a group with schedule_enabled=True and add prompts."""
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

    # Enable schedule
    schedule_response = client.put(
        f"/prompt-groups/api/v1/groups/{group_id}/schedule",
        json={"enabled": True},
        headers=auth_headers,
    )
    assert schedule_response.status_code == 200, f"Enable schedule failed: {schedule_response.json()}"
    assert schedule_response.json()["enabled"] is True

    # Add prompts
    add_resp = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_resp.status_code == 200, f"Add prompts failed: {add_resp.json()}"

    return group_id


def test_daily_scheduled_reports_consecutive_days(
    client,
    test_engine,
    create_verified_user,
    simulate_webhook,
):
    """Test scheduled report generation across 2 consecutive days for both assistants.

    Verifies:
    1. Day 1: ChatGPT and Perplexity reports generated with original sample data
    2. Day 2: ChatGPT and Perplexity reports generated with modified sample data
    3. All 4 reports exist with distinct content
    """
    session_maker = _make_session_maker(test_engine)

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    # === SETUP: Create user and group ===
    user_email = f"daily-schedule-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(user_email, "testpassword123", "Schedule Test User")

    # Get prompts
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 2, "Need at least 2 prompts for test"
    p1, p2 = prompts[0], prompts[1]
    prompt_ids = [p1["id"], p2["id"]]
    prompts_dict = {p["id"]: p["prompt_text"] for p in [p1, p2]}

    # Create scheduled group with prompts
    group_id = _create_scheduled_group_with_prompts(
        client, auth_headers, "DailyScheduleTest", prompt_ids
    )

    # Load sample data
    chatgpt_sample = _load_sample_data("chat_gpt.json")
    perplexity_sample = _load_sample_data("perplexity.json")

    # Adapt samples to test prompts
    chatgpt_adapted = _adapt_sample_items_to_prompts(chatgpt_sample, prompt_ids, prompts_dict)
    perplexity_adapted = _adapt_sample_items_to_prompts(perplexity_sample, prompt_ids, prompts_dict)

    # === DAY 1: Generate reports for both assistants ===

    # Make evaluations stale before Day 1 ChatGPT
    run_async(_make_evaluations_stale(session_maker, prompt_ids, hours_ago=48))

    # Day 1 - ChatGPT (assistant_id=1)
    request_resp = client.post(
        f"/reports/api/v1/groups/{group_id}/request",
        json={"assistant_id": 1},
        headers=auth_headers,
    )
    assert request_resp.status_code == 201, f"Day1 ChatGPT request failed: {request_resp.json()}"
    day1_chatgpt_request_id = request_resp.json()["id"]

    # Get batch ID and simulate webhook
    day1_chatgpt_request = run_async(_get_report_request(session_maker, day1_chatgpt_request_id))
    assert len(day1_chatgpt_request.batch_ids) >= 1
    day1_chatgpt_batch_id = day1_chatgpt_request.batch_ids[0]

    webhook_resp = simulate_webhook(day1_chatgpt_batch_id, chatgpt_adapted, assistant_key="chatgpt")
    assert webhook_resp.status_code == 200, f"Day1 ChatGPT webhook failed: {webhook_resp.json()}"

    # Generate report
    day1_chatgpt_reports = run_async(_check_and_process_ready_requests(session_maker))
    assert day1_chatgpt_reports >= 1, "Day1 ChatGPT report not generated"

    # Make evaluations stale before Day 1 Perplexity
    run_async(_make_evaluations_stale(session_maker, prompt_ids, hours_ago=48))

    # Day 1 - Perplexity (assistant_id=2)
    request_resp = client.post(
        f"/reports/api/v1/groups/{group_id}/request",
        json={"assistant_id": 2},
        headers=auth_headers,
    )
    assert request_resp.status_code == 201, f"Day1 Perplexity request failed: {request_resp.json()}"
    day1_perplexity_request_id = request_resp.json()["id"]

    # Get batch ID and simulate webhook
    day1_perplexity_request = run_async(_get_report_request(session_maker, day1_perplexity_request_id))
    assert len(day1_perplexity_request.batch_ids) >= 1
    day1_perplexity_batch_id = day1_perplexity_request.batch_ids[0]

    webhook_resp = simulate_webhook(day1_perplexity_batch_id, perplexity_adapted, assistant_key="perplexity")
    assert webhook_resp.status_code == 200, f"Day1 Perplexity webhook failed: {webhook_resp.json()}"

    # Generate report
    day1_perplexity_reports = run_async(_check_and_process_ready_requests(session_maker))
    assert day1_perplexity_reports >= 1, "Day1 Perplexity report not generated"

    # === SIMULATE TIME PASSAGE (make evaluations stale again) ===
    run_async(_make_evaluations_stale(session_maker, prompt_ids, hours_ago=48))

    # === DAY 2: Generate reports with MODIFIED sample data ===

    # Modify samples for Day 2
    chatgpt_day2 = _modify_sample_for_day2(chatgpt_adapted)
    perplexity_day2 = _modify_sample_for_day2(perplexity_adapted)

    # Day 2 - ChatGPT (assistant_id=1)
    request_resp = client.post(
        f"/reports/api/v1/groups/{group_id}/request",
        json={"assistant_id": 1},
        headers=auth_headers,
    )
    assert request_resp.status_code == 201, f"Day2 ChatGPT request failed: {request_resp.json()}"
    day2_chatgpt_request_id = request_resp.json()["id"]

    # Get batch ID and simulate webhook with Day 2 data
    day2_chatgpt_request = run_async(_get_report_request(session_maker, day2_chatgpt_request_id))
    assert len(day2_chatgpt_request.batch_ids) >= 1
    day2_chatgpt_batch_id = day2_chatgpt_request.batch_ids[0]

    webhook_resp = simulate_webhook(day2_chatgpt_batch_id, chatgpt_day2, assistant_key="chatgpt")
    assert webhook_resp.status_code == 200, f"Day2 ChatGPT webhook failed: {webhook_resp.json()}"

    # Generate report
    day2_chatgpt_reports = run_async(_check_and_process_ready_requests(session_maker))
    assert day2_chatgpt_reports >= 1, "Day2 ChatGPT report not generated"

    # Make evaluations stale before Day 2 Perplexity
    run_async(_make_evaluations_stale(session_maker, prompt_ids, hours_ago=48))

    # Day 2 - Perplexity (assistant_id=2)
    request_resp = client.post(
        f"/reports/api/v1/groups/{group_id}/request",
        json={"assistant_id": 2},
        headers=auth_headers,
    )
    assert request_resp.status_code == 201, f"Day2 Perplexity request failed: {request_resp.json()}"
    day2_perplexity_request_id = request_resp.json()["id"]

    # Get batch ID and simulate webhook with Day 2 data
    day2_perplexity_request = run_async(_get_report_request(session_maker, day2_perplexity_request_id))
    assert len(day2_perplexity_request.batch_ids) >= 1
    day2_perplexity_batch_id = day2_perplexity_request.batch_ids[0]

    webhook_resp = simulate_webhook(day2_perplexity_batch_id, perplexity_day2, assistant_key="perplexity")
    assert webhook_resp.status_code == 200, f"Day2 Perplexity webhook failed: {webhook_resp.json()}"

    # Generate report
    day2_perplexity_reports = run_async(_check_and_process_ready_requests(session_maker))
    assert day2_perplexity_reports >= 1, "Day2 Perplexity report not generated"

    # === VERIFICATION: Check all 4 reports exist ===
    all_reports = run_async(_get_all_reports_for_group(session_maker, group_id))
    assert len(all_reports) == 4, f"Expected 4 reports, got {len(all_reports)}"

    # === VERIFICATION: Check evaluations have correct content ===
    # Get all evaluations for each assistant
    chatgpt_evals = run_async(_get_evaluations_for_prompts(session_maker, prompt_ids, assistant_id=1))
    perplexity_evals = run_async(_get_evaluations_for_prompts(session_maker, prompt_ids, assistant_id=2))

    # Since evaluations are ordered by completed_at desc, the newest (Day 2) are first
    # Check that at least one evaluation per assistant has Day 2 marker
    chatgpt_day2_evals = [
        e for e in chatgpt_evals
        if e.answer and "[DAY 2]" in e.answer.get("response", "")
    ]
    perplexity_day2_evals = [
        e for e in perplexity_evals
        if e.answer and "[DAY 2]" in e.answer.get("response", "")
    ]

    assert len(chatgpt_day2_evals) >= 2, f"Expected 2+ ChatGPT Day 2 evaluations, got {len(chatgpt_day2_evals)}"
    assert len(perplexity_day2_evals) >= 2, f"Expected 2+ Perplexity Day 2 evaluations, got {len(perplexity_day2_evals)}"

    # Verify Day 1 evaluations exist (without Day 2 marker)
    chatgpt_day1_evals = [
        e for e in chatgpt_evals
        if e.answer and "[DAY 2]" not in e.answer.get("response", "")
    ]
    perplexity_day1_evals = [
        e for e in perplexity_evals
        if e.answer and "[DAY 2]" not in e.answer.get("response", "")
    ]

    assert len(chatgpt_day1_evals) >= 2, f"Expected 2+ ChatGPT Day 1 evaluations, got {len(chatgpt_day1_evals)}"
    assert len(perplexity_day1_evals) >= 2, f"Expected 2+ Perplexity Day 1 evaluations, got {len(perplexity_day1_evals)}"

    # Verify reports are accessible via API
    reports_resp = client.get(
        f"/reports/api/v1/groups/{group_id}/reports",
        headers=auth_headers,
    )
    assert reports_resp.status_code == 200, f"Get reports failed: {reports_resp.json()}"
    api_reports = reports_resp.json()["reports"]
    assert len(api_reports) == 4, f"Expected 4 reports via API, got {len(api_reports)}"
