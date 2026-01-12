"""Integration tests for BrightData batch eviction and chunk processing.

Tests:
1. Stale batch eviction when webhooks never arrive
2. Partial webhook delivery (some prompts succeed, some fail)
3. Webhook fully received - no eviction needed
4. Chunk-based prompt processing
5. Eviction timeout configuration
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.evals_models import BrightDataBatch, BrightDataBatchStatus

# Default topic input using seeded topic ID 1
DEFAULT_TOPIC = {"existing_topic_id": 1}


def _make_session_maker(test_engine) -> async_sessionmaker[AsyncSession]:
    """Create a reusable session maker for test database operations."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
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


async def _get_batch_by_id(test_engine, batch_id: str) -> BrightDataBatch | None:
    """Get batch from database by batch_id."""
    async with _make_session_maker(test_engine)() as session:
        result = await session.execute(
            select(BrightDataBatch).where(BrightDataBatch.batch_id == batch_id)
        )
        return result.scalar_one_or_none()


async def _get_all_pending_batches(test_engine) -> list[BrightDataBatch]:
    """Get all PENDING batches from database."""
    async with _make_session_maker(test_engine)() as session:
        result = await session.execute(
            select(BrightDataBatch).where(
                BrightDataBatch.status == BrightDataBatchStatus.PENDING
            )
        )
        return list(result.scalars().all())


async def _make_batch_stale(test_engine, batch_id: str, hours_ago: int = 4) -> None:
    """Update batch created_at to make it stale (older than eviction timeout)."""
    stale_time = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    async with _make_session_maker(test_engine)() as session:
        await session.execute(
            update(BrightDataBatch)
            .where(BrightDataBatch.batch_id == batch_id)
            .values(created_at=stale_time)
        )
        await session.commit()


def test_batch_eviction_webhook_never_arrives(client, create_verified_user, test_engine):
    """Test that stale PENDING batches are evicted when webhook never arrives.

    Scenario:
    1. User requests fresh execution for prompts
    2. Batch is created in PENDING state
    3. Webhook never arrives (batch becomes stale)
    4. Next request triggers eviction of stale batch
    5. Prompts are released and can be re-requested
    """
    # === STEP 1: Sign up and login ===
    unique_email = f"test-evict-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Eviction Test User")

    # === STEP 2: Create group ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Eviction Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Get prompts ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 2, "Need at least 2 prompts for test"
    prompt_ids = [prompts[0]["id"], prompts[1]["id"]]

    # Add prompts to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: First request - creates batch in PENDING state ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    data = request_resp.json()
    first_batch_id = data["batch_id"]
    assert first_batch_id is not None, "Expected batch to be created"
    assert data["queued_count"] == 2

    # Verify batch exists in PENDING state
    batch = asyncio.get_event_loop().run_until_complete(
        _get_batch_by_id(test_engine, first_batch_id)
    )
    assert batch is not None
    assert batch.status == BrightDataBatchStatus.PENDING

    # === STEP 5: Second request - prompts should be "already_pending" ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    data = request_resp.json()
    assert data["batch_id"] is None, "No new batch should be created"
    assert data["already_pending_count"] == 2
    assert data["queued_count"] == 0

    # === STEP 6: Make batch stale (simulate time passing) ===
    asyncio.get_event_loop().run_until_complete(
        _make_batch_stale(test_engine, first_batch_id, hours_ago=4)
    )

    # === STEP 7: Third request - should evict stale batch and create new one ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    data = request_resp.json()
    new_batch_id = data["batch_id"]
    assert new_batch_id is not None, "New batch should be created after eviction"
    assert new_batch_id != first_batch_id, "Should be a new batch"
    assert data["queued_count"] == 2
    assert data["already_pending_count"] == 0

    # Verify old batch was marked as FAILED
    old_batch = asyncio.get_event_loop().run_until_complete(
        _get_batch_by_id(test_engine, first_batch_id)
    )
    assert old_batch.status == BrightDataBatchStatus.FAILED
    assert old_batch.completed_at is not None


def test_batch_eviction_partial_webhook_received(
    client, create_verified_user, simulate_webhook, test_engine
):
    """Test partial webhook delivery - some webhook items fail to match prompts.

    Scenario:
    1. Request execution for 2 prompts
    2. Webhook contains 2 items, but one has wrong prompt text (doesn't match)
    3. Batch should be marked PARTIAL (1 success, 1 failure)
    """
    # === STEP 1: Sign up and login ===
    unique_email = f"test-partial-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Partial Test User")

    # === STEP 2: Create group ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Partial Webhook Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Get 2 prompts ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 2, "Need at least 2 prompts for test"
    test_prompts = prompts[:2]
    prompt_ids = [p["id"] for p in test_prompts]

    # Add prompts to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: Request fresh execution ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    batch_id = request_resp.json()["batch_id"]
    assert batch_id is not None

    # === STEP 5: Simulate partial webhook - one matches, one has wrong text ===
    webhook_items = [
        {
            "prompt": test_prompts[0]["prompt_text"],  # Correct prompt text
            "answer_text": "Response for prompt 1",
            "citations": [],
        },
        {
            "prompt": "This is a wrong prompt text that doesn't exist",  # Wrong text
            "answer_text": "Response for unknown prompt",
            "citations": [],
        },
    ]
    webhook_resp = simulate_webhook(batch_id, webhook_items)
    assert webhook_resp.status_code == 200
    webhook_data = webhook_resp.json()
    assert webhook_data["status"] == "partial"
    assert webhook_data["processed_count"] == 1
    assert webhook_data["failed_count"] == 1  # Failed to match

    # === STEP 6: Verify batch is marked PARTIAL ===
    batch = asyncio.get_event_loop().run_until_complete(
        _get_batch_by_id(test_engine, batch_id)
    )
    assert batch.status == BrightDataBatchStatus.PARTIAL
    assert batch.completed_at is not None


def test_batch_eviction_full_webhook_received(
    client, create_verified_user, simulate_webhook, test_engine
):
    """Test full webhook delivery - all prompts succeed.

    Scenario:
    1. Request execution for prompts
    2. Webhook contains results for all prompts
    3. Batch should be marked COMPLETED
    4. No eviction needed on subsequent requests
    """
    # === STEP 1: Sign up and login ===
    unique_email = f"test-full-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Full Test User")

    # === STEP 2: Create group ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Full Webhook Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Get 2 prompts ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 2, "Need at least 2 prompts for test"
    test_prompts = prompts[:2]
    prompt_ids = [p["id"] for p in test_prompts]
    prompts_dict = {p["id"]: p["prompt_text"] for p in test_prompts}

    # Add prompts to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: Request fresh execution ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    batch_id = request_resp.json()["batch_id"]
    assert batch_id is not None

    # === STEP 5: Simulate full webhook (all prompts) ===
    webhook_items = [
        {
            "prompt": prompts_dict[pid],
            "answer_text": f"Response for prompt {pid}",
            "citations": [],
        }
        for pid in prompt_ids
    ]
    webhook_resp = simulate_webhook(batch_id, webhook_items)
    assert webhook_resp.status_code == 200
    webhook_data = webhook_resp.json()
    assert webhook_data["status"] == "completed"
    assert webhook_data["processed_count"] == 2
    assert webhook_data["failed_count"] == 0

    # === STEP 6: Verify batch is marked COMPLETED ===
    batch = asyncio.get_event_loop().run_until_complete(
        _get_batch_by_id(test_engine, batch_id)
    )
    assert batch.status == BrightDataBatchStatus.COMPLETED
    assert batch.completed_at is not None


def test_chunk_based_processing(client, create_verified_user, test_engine, monkeypatch):
    """Test that prompts are processed in configurable chunk sizes.

    Scenario:
    1. Configure chunk size to 2
    2. Request execution for 5 prompts
    3. Should create 3 batches (2+2+1)
    """
    # Override chunk size for this test
    from src.config import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "brightdata_chunk_size", 2)

    # === STEP 1: Sign up and login ===
    unique_email = f"test-chunk-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Chunk Test User")

    # === STEP 2: Create group ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Chunk Processing Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Get 5 prompts ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 5, "Need at least 5 prompts for test"
    test_prompts = prompts[:5]
    prompt_ids = [p["id"] for p in test_prompts]

    # Add prompts to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: Request fresh execution ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    data = request_resp.json()
    assert data["queued_count"] == 5

    # Should have created batches for all prompts
    # The primary batch_id is the first one created
    primary_batch_id = data["batch_id"]
    assert primary_batch_id is not None

    # === STEP 5: Verify multiple PENDING batches were created ===
    pending_batches = asyncio.get_event_loop().run_until_complete(
        _get_all_pending_batches(test_engine)
    )

    # With chunk_size=2 and 5 prompts, we expect 3 batches (2+2+1)
    assert len(pending_batches) >= 3, f"Expected at least 3 batches, got {len(pending_batches)}"

    # Verify prompt distribution across batches
    all_prompt_ids = set()
    for batch in pending_batches:
        all_prompt_ids.update(batch.prompt_ids)
        # Each batch should have at most chunk_size prompts
        assert len(batch.prompt_ids) <= 2, f"Batch has {len(batch.prompt_ids)} prompts, expected <= 2"

    # All requested prompts should be in batches
    for pid in prompt_ids:
        assert pid in all_prompt_ids, f"Prompt {pid} not found in any batch"


def test_batch_eviction_respects_timeout_setting(
    client, create_verified_user, test_engine, monkeypatch
):
    """Test that eviction respects the configurable timeout setting.

    Scenario:
    1. Set eviction timeout to 1 hour
    2. Create batch that is 30 minutes old (not stale)
    3. Request again - should NOT evict
    4. Make batch 2 hours old
    5. Request again - should evict
    """
    # Override eviction timeout for this test
    from src.config import settings as settings_module
    monkeypatch.setattr(settings_module.settings, "brightdata_batch_eviction_timeout_hours", 1)

    # === STEP 1: Sign up and login ===
    unique_email = f"test-timeout-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Timeout Test User")

    # === STEP 2: Create group ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Timeout Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Get prompts ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 1, "Need at least 1 prompt for test"
    prompt_id = prompts[0]["id"]

    # Add prompt to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: First request - creates batch ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    first_batch_id = request_resp.json()["batch_id"]
    assert first_batch_id is not None

    # === STEP 5: Make batch 30 minutes old (NOT stale yet) ===
    async def set_batch_age(batch_id: str, minutes_ago: int) -> None:
        age_time = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        async with _make_session_maker(test_engine)() as session:
            await session.execute(
                update(BrightDataBatch)
                .where(BrightDataBatch.batch_id == batch_id)
                .values(created_at=age_time)
            )
            await session.commit()

    asyncio.get_event_loop().run_until_complete(
        set_batch_age(first_batch_id, minutes_ago=30)
    )

    # === STEP 6: Second request - should NOT evict (30 min < 1 hour timeout) ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    data = request_resp.json()
    assert data["batch_id"] is None, "Should not create new batch (not stale yet)"
    assert data["already_pending_count"] == 1

    # Verify batch is still PENDING
    batch = asyncio.get_event_loop().run_until_complete(
        _get_batch_by_id(test_engine, first_batch_id)
    )
    assert batch.status == BrightDataBatchStatus.PENDING

    # === STEP 7: Make batch 2 hours old (now stale) ===
    asyncio.get_event_loop().run_until_complete(
        set_batch_age(first_batch_id, minutes_ago=120)
    )

    # === STEP 8: Third request - should evict (2 hours > 1 hour timeout) ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    data = request_resp.json()
    new_batch_id = data["batch_id"]
    assert new_batch_id is not None, "Should create new batch after eviction"
    assert new_batch_id != first_batch_id

    # Verify old batch was evicted (marked FAILED)
    old_batch = asyncio.get_event_loop().run_until_complete(
        _get_batch_by_id(test_engine, first_batch_id)
    )
    assert old_batch.status == BrightDataBatchStatus.FAILED
