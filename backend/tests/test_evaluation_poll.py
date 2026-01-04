"""Integration test for evaluation poll endpoint."""

import asyncio
import time
from datetime import datetime

import pytest
from sqlalchemy import select

from src.database.evals_models import PromptEvaluation
from src.evaluations.services.evaluation_service import EvaluationService


@pytest.mark.asyncio
async def test_poll_for_evaluation_success(client, eval_auth_headers):
    """Test successfully polling for a prompt evaluation."""
    # Poll for a prompt
    response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "Plus"
        },
        headers=eval_auth_headers,
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
async def test_concurrent_bot_polling(client, eval_auth_headers):
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
        },
        headers=eval_auth_headers,
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
        },
        headers=eval_auth_headers,
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
        },
        headers=eval_auth_headers,
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
        },
        headers=eval_auth_headers,
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
        },
        headers=eval_auth_headers,
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

@pytest.mark.skip
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
        evals_session=test_session,
        prompts_session=test_session,
        min_days_since_last_evaluation=1,
        evaluation_timeout_hours=0.001
    )

    # Get assistant_plan_id for ChatGPT/PLUS (seeded plan)
    assistant_plan_id = await service.get_assistant_plan_id("ChatGPT", "PLUS")
    assert assistant_plan_id is not None

    # Bot: Poll for prompt (first attempt)
    evaluation1 = await service.poll_for_prompt(
        assistant_plan_id=assistant_plan_id
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
        assistant_plan_id=assistant_plan_id
    )

    # Bot should get the SAME prompt (because previous evaluation timed out)
    assert evaluation2 is not None
    assert evaluation2.prompt_id == prompt_id_1, "Bot should get same prompt after timeout"
    assert evaluation2.id != evaluation_id_1, "Bot should have different evaluation ID for retry"

    # Verify both evaluations from this test exist in database
    result = await test_session.execute(
        select(PromptEvaluation)
        .where(PromptEvaluation.id.in_([evaluation_id_1, evaluation2.id]))
    )
    evaluations = result.scalars().all()

    assert len(evaluations) == 2, "Both evaluation attempts from this test should exist in database"

    # Verify both are for the same assistant+plan combination
    assert all(e.assistant_plan_id == assistant_plan_id for e in evaluations)

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
        evals_session=test_session,
        prompts_session=test_session,
        min_days_since_last_evaluation=1,
        evaluation_timeout_hours=2
    )

    # Get assistant_plan_id for ChatGPT/PLUS (seeded plan)
    assistant_plan_id = await service.get_assistant_plan_id("ChatGPT", "PLUS")
    assert assistant_plan_id is not None

    # Bot 1: Poll for prompt
    result1 = await service.poll_for_prompt(
        assistant_plan_id=assistant_plan_id
    )

    assert result1 is not None
    evaluation1, prompt1 = result1
    prompt_id_1 = evaluation1.prompt_id

    # Bot 2: Poll immediately (within 2-hour timeout)
    result2 = await service.poll_for_prompt(
        assistant_plan_id=assistant_plan_id
    )

    # Bot 2 should get a DIFFERENT prompt (Bot 1's is still locked)
    if result2 is not None:  # If there are more prompts available
        evaluation2, prompt2 = result2
        assert evaluation2.prompt_id != prompt_id_1, "Bot 2 should get different prompt while Bot 1's is fresh"


@pytest.mark.asyncio
async def test_poll_with_valid_assistant_plan(client, eval_auth_headers):
    """Test polling with valid assistant/plan combination."""
    response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS"
        },
        headers=eval_auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Should successfully return a prompt (or null if none available)
    assert "evaluation_id" in data
    assert "prompt_id" in data


@pytest.mark.asyncio
async def test_poll_with_invalid_assistant(client, eval_auth_headers):
    """Test polling with non-existent assistant returns 422."""
    response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "NonExistentBot",
            "plan_name": "PLUS"
        },
        headers=eval_auth_headers,
    )

    assert response.status_code == 422
    data = response.json()
    assert "Invalid assistant/plan combination" in data["detail"]
    assert "NonExistentBot" in data["detail"]
    assert "PLUS" in data["detail"]


@pytest.mark.asyncio
async def test_poll_with_invalid_plan(client, eval_auth_headers):
    """Test polling with valid assistant but invalid plan returns 422."""
    response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "ENTERPRISE"  # Not seeded
        },
        headers=eval_auth_headers,
    )

    assert response.status_code == 422
    data = response.json()
    assert "Invalid assistant/plan combination" in data["detail"]
    assert "ChatGPT" in data["detail"]
    assert "ENTERPRISE" in data["detail"]


@pytest.mark.asyncio
async def test_poll_with_invalid_assistant_and_plan(client, eval_auth_headers):
    """Test polling with both invalid assistant and plan returns 422."""
    response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "RandomBot",
            "plan_name": "RandomPlan"
        },
        headers=eval_auth_headers,
    )

    assert response.status_code == 422
    data = response.json()
    assert "Invalid assistant/plan combination" in data["detail"]


@pytest.mark.asyncio
async def test_poll_case_insensitive_validation(client, eval_auth_headers):
    """Test that validation is case-insensitive."""
    # Test lowercase
    response1 = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "chatgpt",  # lowercase
            "plan_name": "plus"          # lowercase
        },
        headers=eval_auth_headers,
    )
    assert response1.status_code == 200

    # Test mixed case
    response2 = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",  # exact case
            "plan_name": "Plus"           # mixed case
        },
        headers=eval_auth_headers,
    )
    assert response2.status_code == 200

    # Test uppercase
    response3 = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "CHATGPT",  # uppercase
            "plan_name": "FREE"           # uppercase
        },
        headers=eval_auth_headers,
    )
    assert response3.status_code == 200


@pytest.mark.asyncio
async def test_poll_all_chatgpt_plans(client, eval_auth_headers):
    """Test polling with all seeded ChatGPT plans."""
    plans = ["FREE", "PLUS", "PRO"]

    for plan in plans:
        response = client.post(
            "/evaluations/api/v1/poll",
            json={
                "assistant_name": "ChatGPT",
                "plan_name": plan
            },
            headers=eval_auth_headers,
        )
        assert response.status_code == 200, f"Plan {plan} should be valid"


@pytest.mark.asyncio
async def test_validation_service_method_directly(test_session):
    """Test the validation service method directly."""
    service = EvaluationService(
        evals_session=test_session,
        prompts_session=test_session,
        min_days_since_last_evaluation=1,
        evaluation_timeout_hours=2
    )

    # Valid combinations - should return assistant_plan_id
    assert await service.get_assistant_plan_id("ChatGPT", "FREE") is not None
    assert await service.get_assistant_plan_id("ChatGPT", "PLUS") is not None
    assert await service.get_assistant_plan_id("ChatGPT", "PRO") is not None

    # Case insensitive
    assert await service.get_assistant_plan_id("chatgpt", "plus") is not None
    assert await service.get_assistant_plan_id("CHATGPT", "free") is not None

    # Invalid combinations - should return None
    assert await service.get_assistant_plan_id("Claude", "PLUS") is None
    assert await service.get_assistant_plan_id("ChatGPT", "MAX") is None
    assert await service.get_assistant_plan_id("Perplexity", "FREE") is None
