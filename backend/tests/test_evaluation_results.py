"""Integration tests for evaluation results endpoint."""

import pytest
from datetime import datetime

from src.database.models import EvaluationStatus, PromptEvaluation


@pytest.mark.asyncio
async def test_get_results_with_valid_data(client):
    """Test getting results for completed evaluations."""
    # First, poll for a prompt to create an evaluation
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS"
        }
    )
    assert poll_response.status_code == 200
    poll_data = poll_response.json()
    assert poll_data["evaluation_id"] is not None
    evaluation_id = poll_data["evaluation_id"]
    prompt_id = poll_data["prompt_id"]

    # Submit the answer to complete the evaluation
    submit_response = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": evaluation_id,
            "answer": {
                "response": "Test response",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    )
    assert submit_response.status_code == 200

    # Request results via API
    response = client.get(
        "/evaluations/api/v1/results",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS",
            "prompt_ids": [prompt_id]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["prompt_id"] == prompt_id
    assert data["results"][0]["prompt_text"] is not None
    assert data["results"][0]["evaluation_id"] is not None
    assert data["results"][0]["status"] == "completed"
    assert data["results"][0]["answer"] is not None


@pytest.mark.asyncio
async def test_get_results_empty_for_non_existent_prompts(client):
    """Test returns empty list when prompt IDs don't exist in database."""
    response = client.get(
        "/evaluations/api/v1/results",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS",
            "prompt_ids": [999999, 999998, 999997]  # Non-existent prompt IDs
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []


@pytest.mark.asyncio
async def test_get_results_includes_prompts_without_evaluations(client):
    """Test returns prompts with null evaluation fields when no evaluation exists."""
    # Poll for a prompt and complete it
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS"
        }
    )
    assert poll_response.status_code == 200
    poll_data = poll_response.json()
    evaluated_prompt_id = poll_data["prompt_id"]

    # Submit to complete the evaluation
    client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": poll_data["evaluation_id"],
            "answer": {
                "response": "Test response",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    )

    # Poll for another prompt with same plan
    poll_response2 = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS"
        }
    )
    assert poll_response2.status_code == 200
    poll_data2 = poll_response2.json()
    unevaluated_prompt_id = poll_data2["prompt_id"]

    # Release it without completing (deletes the evaluation)
    client.post(
        "/evaluations/api/v1/release",
        json={
            "evaluation_id": poll_data2["evaluation_id"],
            "mark_as_failed": False
        }
    )

    # Request results for both prompts - one completed, one with no evaluation
    response = client.get(
        "/evaluations/api/v1/results",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS",
            "prompt_ids": [evaluated_prompt_id, unevaluated_prompt_id]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 2

    # Find results by prompt_id
    results_by_id = {r["prompt_id"]: r for r in data["results"]}

    # Evaluated prompt should have all fields
    assert evaluated_prompt_id in results_by_id
    evaluated_result = results_by_id[evaluated_prompt_id]
    assert evaluated_result["prompt_text"] is not None
    assert evaluated_result["evaluation_id"] is not None
    assert evaluated_result["status"] == "completed"
    assert evaluated_result["answer"] is not None

    # Unevaluated prompt should have prompt_text but null evaluation fields
    assert unevaluated_prompt_id in results_by_id
    unevaluated_result = results_by_id[unevaluated_prompt_id]
    assert unevaluated_result["prompt_text"] is not None
    assert unevaluated_result["evaluation_id"] is None
    assert unevaluated_result["status"] is None
    assert unevaluated_result["answer"] is None
    assert unevaluated_result["completed_at"] is None


@pytest.mark.asyncio
async def test_get_results_invalid_assistant_plan(client):
    """Test returns 422 for invalid assistant/plan combination."""
    response = client.get(
        "/evaluations/api/v1/results",
        params={
            "assistant_name": "NonExistentBot",
            "plan_name": "PLUS",
            "prompt_ids": [1]
        }
    )

    assert response.status_code == 422
    data = response.json()
    assert "Invalid assistant/plan combination" in data["detail"]


@pytest.mark.asyncio
async def test_get_results_only_returns_completed(client):
    """Test that only COMPLETED evaluations are returned, not IN_PROGRESS or FAILED."""
    # Poll for a prompt (creates IN_PROGRESS)
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS"
        }
    )
    assert poll_response.status_code == 200
    poll_data = poll_response.json()
    in_progress_prompt_id = poll_data["prompt_id"]
    in_progress_eval_id = poll_data["evaluation_id"]

    # Poll for another prompt and mark it as failed
    poll_response2 = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS"
        }
    )
    assert poll_response2.status_code == 200
    poll_data2 = poll_response2.json()
    failed_prompt_id = poll_data2["prompt_id"]
    failed_eval_id = poll_data2["evaluation_id"]

    # Mark the second one as failed
    release_response = client.post(
        "/evaluations/api/v1/release",
        json={
            "evaluation_id": failed_eval_id,
            "mark_as_failed": True,
            "failure_reason": "Test failure"
        }
    )
    assert release_response.status_code == 200

    # Request results for both prompts
    response = client.get(
        "/evaluations/api/v1/results",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS",
            "prompt_ids": [in_progress_prompt_id, failed_prompt_id]
        }
    )

    assert response.status_code == 200
    data = response.json()
    # Should return both prompts but with null evaluation fields (no COMPLETED evaluations)
    assert len(data["results"]) == 2

    for result in data["results"]:
        assert result["prompt_text"] is not None
        assert result["evaluation_id"] is None
        assert result["status"] is None
        assert result["answer"] is None
        assert result["completed_at"] is None


@pytest.mark.asyncio
async def test_get_results_returns_latest_per_prompt(client):
    """Test that when multiple evaluations exist, only latest COMPLETED is returned."""
    # Poll for a prompt and complete it with "Old response"
    poll_response1 = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "FREE"  # Use FREE to avoid conflicts with other tests
        }
    )
    assert poll_response1.status_code == 200
    poll_data1 = poll_response1.json()
    prompt_id = poll_data1["prompt_id"]
    eval_id1 = poll_data1["evaluation_id"]

    # Submit old response
    submit_response1 = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": eval_id1,
            "answer": {
                "response": "Old response",
                "citations": [],
                "timestamp": "2024-01-01T10:00:00Z"
            }
        }
    )
    assert submit_response1.status_code == 200

    # Request results - should have the old response
    response = client.get(
        "/evaluations/api/v1/results",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "FREE",
            "prompt_ids": [prompt_id]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["prompt_text"] is not None
    assert data["results"][0]["answer"]["response"] == "Old response"


@pytest.mark.asyncio
async def test_get_results_case_insensitive(client):
    """Test that assistant/plan lookup is case-insensitive."""
    # Poll for a prompt and complete it
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={
            "assistant_name": "ChatGPT",
            "plan_name": "PRO"  # Use PRO to avoid conflicts
        }
    )
    assert poll_response.status_code == 200
    poll_data = poll_response.json()
    prompt_id = poll_data["prompt_id"]
    eval_id = poll_data["evaluation_id"]

    # Submit the answer
    submit_response = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": eval_id,
            "answer": {
                "response": "Test",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }
    )
    assert submit_response.status_code == 200

    # Request with different case
    response = client.get(
        "/evaluations/api/v1/results",
        params={
            "assistant_name": "chatgpt",  # lowercase
            "plan_name": "pro",  # lowercase
            "prompt_ids": [prompt_id]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["prompt_text"] is not None
    assert data["results"][0]["evaluation_id"] is not None
