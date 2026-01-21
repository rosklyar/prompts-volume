"""Integration tests for selectable comparison endpoint.

Tests the SelectableComparisonResponse with:
- Per-prompt selection options
- Brand/competitors change detection
- Time estimations
- can_generate logic

Uses Bright Data webhook simulation for creating evaluations.
"""

import uuid
from decimal import Decimal

import pytest

# Default topic input using seeded topic ID 1
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


def _request_fresh_and_webhook(
    client, simulate_webhook, auth_headers, prompt_ids: list[int], prompts_dict: dict[int, str],
    response_template: str = "Response mentioning TestBrand",
    citations: list[dict] | None = None,
    country_id: int = 1,  # Default to Ukraine (from seed data)
) -> str:
    """Request fresh execution and simulate webhook completion.

    Args:
        client: Test client
        simulate_webhook: Webhook simulation fixture
        auth_headers: User auth headers
        prompt_ids: List of prompt IDs to process
        prompts_dict: Dict mapping prompt_id -> prompt_text
        response_template: Template for response text (will have prompt_id appended)
        citations: Optional citations to include
        country_id: Country ID for scraping (default: 1 = Ukraine)

    Returns:
        batch_id from the request
    """
    # Request fresh execution
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids, "country_id": country_id},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200, f"Request fresh failed: {request_resp.json()}"
    batch_id = request_resp.json()["batch_id"]

    if batch_id is None:
        # All prompts already pending
        return None

    # Build webhook items
    webhook_items = []
    for pid in prompt_ids:
        if pid in prompts_dict:
            item = {
                "prompt": prompts_dict[pid],
                "answer_text": f"{response_template} for prompt {pid}",
                "citations": citations or [],
            }
            webhook_items.append(item)

    # Simulate webhook
    webhook_resp = simulate_webhook(batch_id, webhook_items)
    assert webhook_resp.status_code == 200, f"Webhook failed: {webhook_resp.json()}"

    return batch_id


def _build_selections_from_compare(compare_response: dict) -> list[dict]:
    """Build selections list from compare response using default selections."""
    selections = []
    for ps in compare_response["prompt_selections"]:
        selections.append({
            "prompt_id": ps["prompt_id"],
            "evaluation_id": ps["default_selection"],
        })
    return selections


def test_enhanced_comparison_fresh_data_detection(client, create_verified_user, simulate_webhook):
    """Test that compare detects prompts with available selection options."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-fresh-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Fresh Test User")

    # === STEP 2: Create group with brand ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Fresh Data Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Get prompts from database ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 1, "Need at least 1 prompt for test"
    prompt = prompts[0]
    prompt_id = prompt["id"]
    prompts_dict = {prompt["id"]: prompt["prompt_text"] for prompt in prompts[:1]}

    # === STEP 4: Add prompt to group ===
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 5: Request fresh and simulate webhook to create evaluation ===
    _request_fresh_and_webhook(
        client, simulate_webhook, auth_headers,
        [prompt_id], prompts_dict, "First response"
    )

    # === STEP 6: Compare before first report ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    # Should have prompt selection info
    assert "prompt_selections" in compare
    assert len(compare["prompt_selections"]) == 1

    # First prompt should have available options (fresh since no previous report)
    ps = compare["prompt_selections"][0]
    assert ps["prompt_id"] == prompt_id
    assert len(ps["available_options"]) >= 1  # Has options
    assert ps["default_selection"] is not None  # Has default

    # Should be able to generate
    assert compare["can_generate"] is True
    assert compare["generation_disabled_reason"] is None

    # === STEP 7: Generate first report with selections ===
    selections = _build_selections_from_compare(compare)
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"selections": selections},
        headers=auth_headers,
    )
    assert report_response.status_code == 200

    # === STEP 8: Compare after first report (same data, no changes) ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    # Prompt should NOT have fresh options (no fresher answers than report)
    # Options are only fresher evaluations, so after consuming, no fresh options
    assert compare["default_fresh_count"] == 0

    # Should NOT be able to generate (no new data)
    # Note: Brand changes don't enable generation since stats are recalculated on-the-fly
    assert compare["can_generate"] is False
    assert compare["generation_disabled_reason"] == "no_new_data"
