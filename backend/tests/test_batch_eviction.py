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
        json={"prompt_ids": prompt_ids, "country_id": 1},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: First request - creates batch in PENDING state ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids, "country_id": 1},
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
        json={"prompt_ids": prompt_ids, "country_id": 1},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    data = request_resp.json()
    assert data["batch_id"] is None, "No new batch should be created"
    assert data["already_pending_count"] == 2
    assert data["queued_count"] == 0

    # === STEP 6: Make batch stale (simulate time passing) ===
    # Eviction timeout is 6 hours (chunk_timeout=2 * (max_retries+1)=3)
    # Use 7 hours to exceed the timeout
    asyncio.get_event_loop().run_until_complete(
        _make_batch_stale(test_engine, first_batch_id, hours_ago=7)
    )

    # === STEP 7: Third request - should evict stale batch and create new one ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids, "country_id": 1},
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
        json={"prompt_ids": prompt_ids, "country_id": 1},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: Request fresh execution ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids, "country_id": 1},
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
