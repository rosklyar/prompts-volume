"""Integration tests for enhanced comparison endpoint.

Tests the new EnhancedComparisonResponse with:
- Per-prompt freshness detection
- Brand/competitors change detection
- Time estimations
- can_generate logic
"""

import uuid
from decimal import Decimal

# Default topic input using seeded topic ID 1
DEFAULT_TOPIC = {"existing_topic_id": 1}


def test_enhanced_comparison_fresh_data_detection(client, eval_auth_headers):
    """Test that compare detects prompts with fresher answers than last report."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-fresh-{uuid.uuid4()}@example.com"
    signup_response = client.post(
        "/api/v1/users/signup",
        json={
            "email": unique_email,
            "password": "testpassword123",
            "full_name": "Fresh Test User",
        },
    )
    assert signup_response.status_code == 200

    login_response = client.post(
        "/api/v1/login/access-token",
        data={"username": unique_email, "password": "testpassword123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

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

    # === STEP 3: Poll and complete an evaluation ===
    poll_resp = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "PLUS"},
        headers=eval_auth_headers,
    )
    assert poll_resp.status_code == 200
    prompt_id = poll_resp.json()["prompt_id"]
    eval_id = poll_resp.json()["evaluation_id"]

    submit_resp = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": eval_id,
            "answer": {
                "response": "First response",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
        headers=eval_auth_headers,
    )
    assert submit_resp.status_code == 200

    # === STEP 4: Add prompt to group ===
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 5: Compare before first report ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    # Should have prompt freshness info
    assert "prompt_freshness" in compare
    assert len(compare["prompt_freshness"]) == 1

    # First prompt should show as fresh (no previous report to compare to)
    pf = compare["prompt_freshness"][0]
    assert pf["prompt_id"] == prompt_id
    assert pf["has_fresher_answer"] is True  # Fresh since no previous report
    assert pf["latest_answer_at"] is not None

    # Should be able to generate
    assert compare["can_generate"] is True
    assert compare["generation_disabled_reason"] is None

    # === STEP 6: Generate first report ===
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"include_previous": True},
        headers=auth_headers,
    )
    assert report_response.status_code == 200

    # === STEP 7: Compare after first report (same data, no changes) ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    # Prompt should NOT show as fresh (same answer as in report)
    pf = compare["prompt_freshness"][0]
    assert pf["has_fresher_answer"] is False

    # No fresh evaluations (already consumed)
    assert compare["fresh_evaluations"] == 0

    # Should NOT be able to generate (no new data, no brand changes)
    assert compare["can_generate"] is False
    assert compare["generation_disabled_reason"] == "no_new_data_or_changes"


def test_enhanced_comparison_brand_change_detection(client, eval_auth_headers):
    """Test that compare detects brand/competitors changes."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-brand-{uuid.uuid4()}@example.com"
    signup_response = client.post(
        "/api/v1/users/signup",
        json={
            "email": unique_email,
            "password": "testpassword123",
            "full_name": "Brand Test User",
        },
    )
    assert signup_response.status_code == 200

    login_response = client.post(
        "/api/v1/login/access-token",
        data={"username": unique_email, "password": "testpassword123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

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

    # === STEP 3: Add a prompt with completed evaluation ===
    poll_resp = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "PLUS"},
        headers=eval_auth_headers,
    )
    assert poll_resp.status_code == 200
    prompt_id = poll_resp.json()["prompt_id"]
    eval_id = poll_resp.json()["evaluation_id"]

    submit_resp = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": eval_id,
            "answer": {
                "response": "Response mentioning OriginalBrand",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
        headers=eval_auth_headers,
    )
    assert submit_resp.status_code == 200

    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: Generate first report ===
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"include_previous": True},
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
    assert compare["can_generate"] is True  # Brand changed, can regenerate

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
    assert compare["can_generate"] is True


def test_enhanced_comparison_time_estimations(client, eval_auth_headers):
    """Test that compare returns correct time estimations."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-time-{uuid.uuid4()}@example.com"
    signup_response = client.post(
        "/api/v1/users/signup",
        json={
            "email": unique_email,
            "password": "testpassword123",
            "full_name": "Time Test User",
        },
    )
    assert signup_response.status_code == 200

    login_response = client.post(
        "/api/v1/login/access-token",
        data={"username": unique_email, "password": "testpassword123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

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

    # === STEP 3: Poll evaluation (starts IN_PROGRESS) ===
    poll_resp = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "PLUS"},
        headers=eval_auth_headers,
    )
    assert poll_resp.status_code == 200
    prompt_id = poll_resp.json()["prompt_id"]
    eval_id = poll_resp.json()["evaluation_id"]

    # Add prompt to group before completing
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: Compare with IN_PROGRESS evaluation ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    # Should show in_progress estimation
    assert len(compare["prompt_freshness"]) == 1
    pf = compare["prompt_freshness"][0]
    assert pf["has_in_progress_evaluation"] is True
    assert pf["next_refresh_estimate"] == "~15 minutes"

    # === STEP 5: Complete the evaluation ===
    submit_resp = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": eval_id,
            "answer": {
                "response": "Completed response",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
        headers=eval_auth_headers,
    )
    assert submit_resp.status_code == 200

    # === STEP 6: Generate report and compare again ===
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"include_previous": True},
        headers=auth_headers,
    )
    assert report_response.status_code == 200

    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    # Should show next refresh estimation (no in_progress)
    pf = compare["prompt_freshness"][0]
    assert pf["has_in_progress_evaluation"] is False
    assert pf["next_refresh_estimate"] == "up to 6 hours"


def test_enhanced_comparison_cost_estimation(client, eval_auth_headers):
    """Test that compare returns accurate cost estimation."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-cost-{uuid.uuid4()}@example.com"
    signup_response = client.post(
        "/api/v1/users/signup",
        json={
            "email": unique_email,
            "password": "testpassword123",
            "full_name": "Cost Test User",
        },
    )
    assert signup_response.status_code == 200

    login_response = client.post(
        "/api/v1/login/access-token",
        data={"username": unique_email, "password": "testpassword123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

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

    # === STEP 3: Poll and complete 3 evaluations ===
    prompt_ids = []
    for i in range(3):
        poll_resp = client.post(
            "/evaluations/api/v1/poll",
            json={"assistant_name": "ChatGPT", "plan_name": "PLUS"},
            headers=eval_auth_headers,
        )
        assert poll_resp.status_code == 200
        prompt_id = poll_resp.json()["prompt_id"]
        eval_id = poll_resp.json()["evaluation_id"]
        prompt_ids.append(prompt_id)

        submit_resp = client.post(
            "/evaluations/api/v1/submit",
            json={
                "evaluation_id": eval_id,
                "answer": {
                    "response": f"Response {i}",
                    "citations": [],
                    "timestamp": "2024-01-01T00:00:00Z",
                },
            },
            headers=eval_auth_headers,
        )
        assert submit_resp.status_code == 200

    # Add prompts to group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 4: Compare - should show cost for 3 fresh evaluations ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    fresh_count = compare["fresh_evaluations"]
    assert fresh_count >= 3, f"Expected at least 3 fresh, got {fresh_count}"

    # Cost should be 0.01 per evaluation
    expected_cost = Decimal("0.01") * fresh_count
    actual_cost = Decimal(str(compare["estimated_cost"]))
    assert actual_cost == expected_cost, f"Expected {expected_cost}, got {actual_cost}"

    # User balance from signup credits
    assert Decimal(str(compare["user_balance"])) == Decimal("10.00")

    # Should be able to afford all
    assert compare["affordable_count"] >= fresh_count
    assert compare["needs_top_up"] is False


def test_enhanced_comparison_can_generate_logic(client, eval_auth_headers):
    """Test can_generate logic with various scenarios."""
    # === STEP 1: Sign up and login ===
    unique_email = f"test-gen-{uuid.uuid4()}@example.com"
    signup_response = client.post(
        "/api/v1/users/signup",
        json={
            "email": unique_email,
            "password": "testpassword123",
            "full_name": "Generate Test User",
        },
    )
    assert signup_response.status_code == 200

    login_response = client.post(
        "/api/v1/login/access-token",
        data={"username": unique_email, "password": "testpassword123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

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
    assert compare["prompts_with_fresher_answers"] == 0
    assert compare["fresh_evaluations"] == 0

    # === STEP 4: Add prompt with evaluation ===
    poll_resp = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "PLUS"},
        headers=eval_auth_headers,
    )
    assert poll_resp.status_code == 200
    prompt_id = poll_resp.json()["prompt_id"]
    eval_id = poll_resp.json()["evaluation_id"]

    submit_resp = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": eval_id,
            "answer": {
                "response": "Response",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
        headers=eval_auth_headers,
    )
    assert submit_resp.status_code == 200

    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200

    # === STEP 5: Compare - should be able to generate ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()

    assert compare["can_generate"] is True
    assert compare["fresh_evaluations"] >= 1

    # === STEP 6: Generate report ===
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"include_previous": True},
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
    assert compare["generation_disabled_reason"] == "no_new_data_or_changes"

    # === STEP 8: Change brand - should be able to generate again ===
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

    assert compare["can_generate"] is True
    assert compare["brand_changes"]["brand_changed"] is True
