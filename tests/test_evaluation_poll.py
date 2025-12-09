"""Integration test for evaluation poll endpoint."""

import asyncio
import time
from datetime import datetime

import pytest
from sqlalchemy import select

from src.database.models import PromptEvaluation
from src.evaluations.services.evaluation_service import EvaluationService


@pytest.mark.asyncio
async def test_poll_for_evaluation_success(client):
    """Test successfully polling for a prompt evaluation."""
    # Poll for a prompt
    response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "Plus"
        }
    )

    # Should return 200 with a prompt
    assert response.status_code == 200

    data = response.json()

    # Should have claimed a prompt
    assert data["evaluation_id"] is not None
    assert data["prompt_id"] is not None
    assert data["prompt_text"] is not None
    assert data["topic_id"] is not None
    assert data["claimed_at"] is not None

    # Verify the prompt text is not empty
    assert len(data["prompt_text"]) > 0

    # Verify the topic_id matches one of the seeded topics
    assert data["topic_id"] in [1, 2]


@pytest.mark.asyncio
async def test_concurrent_bot_polling(client):
    """Test concurrent bot polling with locking mechanism.

    Scenario:
    1. Bot 1 polls and claims a prompt
    2. Bot 2 polls immediately after Bot 1 (should get different prompt)
    3. Bot 1 waits 1 second after Bot 2 polls, then submits result
    4. Bot 2 waits 2 seconds after polling, then submits result
    5. Bot 3 polls and should get a third prompt (different from 1 and 2)
    """
    # Bot 1: Poll for first prompt
    response1 = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "Plus"
        }
    )

    assert response1.status_code == 200
    bot1_data = response1.json()
    assert bot1_data["evaluation_id"] is not None
    assert bot1_data["prompt_id"] is not None

    bot1_evaluation_id = bot1_data["evaluation_id"]
    bot1_prompt_id = bot1_data["prompt_id"]

    # Bot 2: Poll immediately after Bot 1 (should get different prompt due to locking)
    response2 = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "Plus"
        }
    )

    assert response2.status_code == 200
    bot2_data = response2.json()
    assert bot2_data["evaluation_id"] is not None
    assert bot2_data["prompt_id"] is not None

    bot2_evaluation_id = bot2_data["evaluation_id"]
    bot2_prompt_id = bot2_data["prompt_id"]

    # Verify Bot 2 got a different prompt than Bot 1
    assert bot2_prompt_id != bot1_prompt_id, "Bot 2 should get a different prompt than Bot 1"
    assert bot2_evaluation_id != bot1_evaluation_id, "Bot 2 should get a different evaluation ID"

    # Bot 1: Wait 1 second after Bot 2 polled, then submit result
    time.sleep(1)

    # Bot 1: Submit result
    submit_response1 = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": bot1_evaluation_id,
            "answer": {
                "response": "Bot 1 fake answer for testing",
                "citations": [
                    {
                        "url": "https://example.com/source1",
                        "text": "Example Source 1"
                    }
                ],
                "timestamp": datetime.now().isoformat()
            }
        }
    )

    assert submit_response1.status_code == 200
    submit1_data = submit_response1.json()
    assert submit1_data["status"] == "completed"
    assert submit1_data["evaluation_id"] == bot1_evaluation_id

    # Bot 2: Wait 2 seconds from when it polled, then submit result
    time.sleep(2)

    # Bot 2: Submit result
    submit_response2 = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": bot2_evaluation_id,
            "answer": {
                "response": "Bot 2 fake answer for testing",
                "citations": [
                    {
                        "url": "https://example.com/source2",
                        "text": "Example Source 2"
                    }
                ],
                "timestamp": datetime.now().isoformat()
            }
        }
    )

    assert submit_response2.status_code == 200
    submit2_data = submit_response2.json()
    assert submit2_data["status"] == "completed"
    assert submit2_data["evaluation_id"] == bot2_evaluation_id

    # Bot 3: Poll for another prompt (should get a third one, different from 1 and 2)
    response3 = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "Plus"
        }
    )

    assert response3.status_code == 200
    bot3_data = response3.json()

    # Check if there's a third prompt available
    # Note: The seeded data might have limited prompts, so we handle both cases
    if bot3_data["prompt_id"] is not None:
        bot3_prompt_id = bot3_data["prompt_id"]

        # Verify Bot 3 got a different prompt from both Bot 1 and Bot 2
        assert bot3_prompt_id != bot1_prompt_id, "Bot 3 should get different prompt than Bot 1"
        assert bot3_prompt_id != bot2_prompt_id, "Bot 3 should get different prompt than Bot 2"
    else:
        # No more prompts available - this is acceptable
        assert bot3_data["evaluation_id"] is None
        assert bot3_data["prompt_text"] is None


@pytest.mark.asyncio
async def test_evaluation_timeout_makes_prompt_available(client, test_session):
    """Test that timed-out IN_PROGRESS evaluations make prompts available again.

    Scenario:
    1. Bot claims a prompt (creates IN_PROGRESS evaluation)
    2. Wait for timeout period to elapse (4 seconds with 0.001 hour timeout)
    3. Same bot polls again with same assistant/plan combination
    4. Bot should get the SAME prompt (because previous evaluation timed out)
    5. Both evaluations should exist in database for same combination

    This tests the retry mechanism when a bot crashes and doesn't report back.
    """
    # Create service with short timeout (0.001 hours = 3.6 seconds)
    service = EvaluationService(
        session=test_session,
        min_days_since_last_evaluation=1,
        evaluation_timeout_hours=0.001
    )

    # Bot: Poll for prompt (first attempt)
    evaluation1 = await service.poll_for_prompt(
        assistant_name="TestBot",
        plan_name="TestPlan"
    )

    assert evaluation1 is not None
    prompt_id_1 = evaluation1.prompt_id
    evaluation_id_1 = evaluation1.id

    # Verify evaluation is IN_PROGRESS
    assert evaluation1.status.value == "in_progress"

    # Wait for timeout to elapse (4 seconds > 3.6 second timeout)
    await asyncio.sleep(4)

    # Bot: Poll again with SAME assistant/plan (retry after crash/timeout)
    evaluation2 = await service.poll_for_prompt(
        assistant_name="TestBot",
        plan_name="TestPlan"
    )

    # Bot should get the SAME prompt (because previous evaluation timed out)
    assert evaluation2 is not None
    assert evaluation2.prompt_id == prompt_id_1, "Bot should get same prompt after timeout"
    assert evaluation2.id != evaluation_id_1, "Bot should have different evaluation ID for retry"

    # Verify both evaluations exist in database for same combination
    result = await test_session.execute(
        select(PromptEvaluation)
        .where(PromptEvaluation.prompt_id == prompt_id_1)
        .where(PromptEvaluation.assistant_name == "TestBot")
        .where(PromptEvaluation.plan_name == "TestPlan")
    )
    evaluations = result.scalars().all()

    assert len(evaluations) == 2, "Both evaluation attempts should exist in database"

    # Verify both are for the same assistant+plan combination
    assert all(e.assistant_name == "TestBot" for e in evaluations)
    assert all(e.plan_name == "TestPlan" for e in evaluations)

    # Verify both are IN_PROGRESS (stale one not auto-marked as FAILED)
    assert all(e.status.value == "in_progress" for e in evaluations)


@pytest.mark.asyncio
async def test_fresh_evaluation_remains_locked(client, test_session):
    """Test that fresh IN_PROGRESS evaluations keep prompts locked.

    Scenario:
    1. Bot 1 claims a prompt
    2. Bot 2 polls immediately (within timeout period)
    3. Bot 2 should get a DIFFERENT prompt (Bot 1's evaluation is still fresh)
    """
    # Create service with normal timeout (2 hours)
    service = EvaluationService(
        session=test_session,
        min_days_since_last_evaluation=1,
        evaluation_timeout_hours=2
    )

    # Bot 1: Poll for prompt
    evaluation1 = await service.poll_for_prompt(
        assistant_name="TestBot",
        plan_name="TestPlan"
    )

    assert evaluation1 is not None
    prompt_id_1 = evaluation1.prompt_id

    # Bot 2: Poll immediately (within 2-hour timeout)
    evaluation2 = await service.poll_for_prompt(
        assistant_name="TestBot",
        plan_name="TestPlan"
    )

    # Bot 2 should get a DIFFERENT prompt (Bot 1's is still locked)
    if evaluation2 is not None:  # If there are more prompts available
        assert evaluation2.prompt_id != prompt_id_1, "Bot 2 should get different prompt while Bot 1's is fresh"
