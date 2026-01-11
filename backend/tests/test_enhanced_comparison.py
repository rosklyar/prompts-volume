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

    Returns:
        batch_id from the request
    """
    # Request fresh execution
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids},
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


def test_enhanced_comparison_brand_change_detection(client, create_verified_user, simulate_webhook):
    """Test that compare detects brand/competitors changes."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-brand-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Brand Test User")

    # === STEP 2: Create group with brand ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Brand Change Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "OriginalBrand", "domain": "original.com", "variations": []},
            "competitors": [{"name": "Comp1", "domain": "comp1.com", "variations": []}],
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Get prompts and create evaluation via webhook ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    prompt = prompts[0]
    prompt_id = prompt["id"]
    prompts_dict = {prompt["id"]: prompt["prompt_text"]}

    # Add prompt to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # Request fresh and simulate webhook
    _request_fresh_and_webhook(
        client, simulate_webhook, auth_headers,
        [prompt_id], prompts_dict, "Response mentioning OriginalBrand"
    )

    # === STEP 4: Generate first report with selections ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    selections = _build_selections_from_compare(compare_response.json())

    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"selections": selections},
        headers=auth_headers,
    )
    assert report_response.status_code == 200

    # === STEP 5: Compare - no changes yet ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    assert compare["brand_changes"]["brand_changed"] is False
    assert compare["brand_changes"]["competitors_changed"] is False
    assert compare["can_generate"] is False  # No fresh data, no changes

    # === STEP 6: Update brand ===
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={"brand": {"name": "NewBrand", "domain": "newbrand.com", "variations": []}},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    # === STEP 7: Compare again - should detect brand change ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    assert compare["brand_changes"]["brand_changed"] is True
    assert compare["brand_changes"]["current_brand"]["name"] == "NewBrand"
    assert compare["brand_changes"]["previous_brand"]["name"] == "OriginalBrand"
    # Brand change is detected but doesn't enable generation
    # Since stats are recalculated on-the-fly, no new report is needed for brand changes
    assert compare["can_generate"] is False

    # === STEP 8: Update competitors ===
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={
            "brand": {"name": "NewBrand", "domain": "newbrand.com", "variations": []},  # Keep same
            "competitors": [
                {"name": "Comp1", "domain": "comp1.com", "variations": []},
                {"name": "Comp2", "domain": "comp2.com", "variations": []},  # Added
            ],
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    # === STEP 9: Compare - should detect competitors change ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    assert compare["brand_changes"]["competitors_changed"] is True
    assert len(compare["brand_changes"]["current_competitors"]) == 2
    # Competitors changed but doesn't enable generation (stats recalculated on-the-fly)
    assert compare["can_generate"] is False


def test_enhanced_comparison_time_estimations(client, create_verified_user, simulate_webhook):
    """Test that request-fresh returns correct time estimations."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-time-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Time Test User")

    # === STEP 2: Create group ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Time Estimation Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Get prompts ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    prompt = prompts[0]
    prompt_id = prompt["id"]
    prompts_dict = {prompt["id"]: prompt["prompt_text"]}

    # Add prompt to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: Request fresh - get time estimates ===
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200
    data = request_resp.json()
    batch_id = data["batch_id"]

    # Verify time estimation fields if we got a batch (not already pending)
    if batch_id is not None:
        assert data["estimated_total_wait"] is not None
        assert "~" in data["estimated_total_wait"]  # e.g., "~1 minute"
        assert data["estimated_completion_at"] is not None
        assert data["queued_count"] >= 1

        # Complete via webhook
        webhook_items = [{
            "prompt": prompts_dict[prompt_id],
            "answer_text": "Completed response",
            "citations": [],
        }]
        webhook_resp = simulate_webhook(batch_id, webhook_items)
        assert webhook_resp.status_code == 200
    else:
        # Prompt was already pending - verify we got the right response
        assert data["already_pending_count"] >= 1
        assert data["queued_count"] == 0

    # === STEP 5: Compare - prompt should have options now ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    # Should have options available (either from our webhook or previous evaluations)
    assert len(compare["prompt_selections"]) == 1
    ps = compare["prompt_selections"][0]
    assert len(ps["available_options"]) >= 1


def test_enhanced_comparison_cost_estimation(client, create_verified_user, simulate_webhook):
    """Test that compare returns accurate cost estimation."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-cost-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Cost Test User")

    # === STEP 2: Create group ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Cost Estimation Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Get 3 prompts and create evaluations via webhook ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    assert len(prompts) >= 3, "Need at least 3 prompts for test"
    test_prompts = prompts[:3]
    prompt_ids = [p["id"] for p in test_prompts]
    prompts_dict = {p["id"]: p["prompt_text"] for p in test_prompts}

    # Add prompts to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # Request fresh and simulate webhook
    _request_fresh_and_webhook(
        client, simulate_webhook, auth_headers,
        prompt_ids, prompts_dict, "Response"
    )

    # === STEP 4: Compare - should show cost for 3 fresh default selections ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    fresh_count = compare["default_fresh_count"]
    assert fresh_count >= 3, f"Expected at least 3 fresh, got {fresh_count}"

    # Cost should be 0.01 per evaluation
    expected_cost = Decimal("0.01") * fresh_count
    actual_cost = Decimal(str(compare["default_estimated_cost"]))
    assert actual_cost == expected_cost, f"Expected {expected_cost}, got {actual_cost}"

    # User balance from signup credits
    assert Decimal(str(compare["user_balance"])) == Decimal("10.00")


def test_enhanced_comparison_can_generate_logic(client, create_verified_user, simulate_webhook):
    """Test can_generate logic with various scenarios."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-gen-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Generate Test User")

    # === STEP 2: Create group ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Generate Logic Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # === STEP 3: Empty group - compare ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    # Empty group - no data to generate
    assert compare["can_generate"] is False
    assert compare["prompts_with_options"] == 0
    assert compare["default_fresh_count"] == 0

    # === STEP 4: Get prompts and add to group with evaluation ===
    prompts = _get_prompts_for_topic(client, auth_headers)
    prompt = prompts[0]
    prompt_id = prompt["id"]
    prompts_dict = {prompt["id"]: prompt["prompt_text"]}

    # Add prompt to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # Request fresh and simulate webhook
    _request_fresh_and_webhook(
        client, simulate_webhook, auth_headers,
        [prompt_id], prompts_dict, "Response"
    )

    # === STEP 5: Compare - should be able to generate ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    assert compare["can_generate"] is True
    assert compare["default_fresh_count"] >= 1

    # === STEP 6: Generate report with selections ===
    selections = _build_selections_from_compare(compare)
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"selections": selections},
        headers=auth_headers,
    )
    assert report_response.status_code == 200

    # === STEP 7: Compare - should NOT be able to generate ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    assert compare["can_generate"] is False
    assert compare["generation_disabled_reason"] == "no_new_data"

    # === STEP 8: Change brand - brand change is detected but doesn't enable generation ===
    # Stats are recalculated on-the-fly, so no new report needed for brand changes
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={"brand": {"name": "NewBrand", "domain": "newbrand.com", "variations": []}},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    # Brand change is detected but doesn't enable generation (no fresh data)
    assert compare["can_generate"] is False
    assert compare["brand_changes"]["brand_changed"] is True
