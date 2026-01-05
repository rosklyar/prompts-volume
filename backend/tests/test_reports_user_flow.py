"""Integration test for complete reports user flow.

Tests the complete user journey:
1. Sign up (gets signup credits)
2. Login
3. Create group with prompts
4. Generate report with selections (charges for fresh evaluations)
5. Generating again is free (already consumed)
6. Add more evaluations
7. Compare (shows fresh data with selection options)
8. Generate another report (charges only for new)
9. Verify balance changes correctly
"""

import uuid
from decimal import Decimal

# Default topic input using seeded topic ID 1
DEFAULT_TOPIC = {"existing_topic_id": 1}


def _build_selections_from_compare(compare_response: dict) -> list[dict]:
    """Build selections list from compare response using default selections."""
    selections = []
    for ps in compare_response["prompt_selections"]:
        selections.append({
            "prompt_id": ps["prompt_id"],
            "evaluation_id": ps["default_selection"],
        })
    return selections


def test_complete_report_user_flow(client, eval_auth_headers, create_verified_user):
    """Test complete user journey: signup → reports → billing.

    This test validates the entire reports and billing integration:
    - User signs up and receives 10.00 signup credits
    - Creates a prompt group with prompts
    - Generates reports and is charged for fresh evaluations
    - Subsequent reports for same data are free (already consumed)
    - New evaluations are charged when added
    - Balance decreases correctly with each charge
    """
    # === STEP 1 & 2: Sign up and login ===
    unique_email = f"test-flow-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Flow Test User")

    # === STEP 3: Check initial balance (should be 10.00 from signup credits) ===
    balance_response = client.get("/billing/api/v1/balance", headers=auth_headers)
    assert balance_response.status_code == 200
    initial_balance = Decimal(str(balance_response.json()["available_balance"]))
    assert initial_balance == Decimal("10.00"), f"Expected 10.00, got {initial_balance}"

    # === STEP 4: Create group (brand and topic are required) ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Report Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "testbrand.com", "variations": ["test"]},
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201, f"Group creation failed: {group_response.json()}"
    group_id = group_response.json()["id"]

    # === STEP 5: Poll and complete 2 evaluations ===
    prompt_ids = []

    for i in range(2):
        poll_resp = client.post(
            "/evaluations/api/v1/poll",
            json={"assistant_name": "ChatGPT", "plan_name": "PLUS"},
            headers=eval_auth_headers,
        )
        assert poll_resp.status_code == 200, f"Poll {i} failed: {poll_resp.json()}"
        poll_data = poll_resp.json()
        prompt_id = poll_data["prompt_id"]
        eval_id = poll_data["evaluation_id"]
        prompt_ids.append(prompt_id)

        # Complete the evaluation
        submit_resp = client.post(
            "/evaluations/api/v1/submit",
            json={
                "evaluation_id": eval_id,
                "answer": {
                    "response": f"Test response for prompt {i}",
                    "citations": [],
                    "timestamp": "2024-01-01T00:00:00Z",
                },
            },
            headers=eval_auth_headers,
        )
        assert submit_resp.status_code == 200, f"Submit {i} failed: {submit_resp.json()}"

    # === STEP 6: Add prompts to the group ===
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_response.status_code == 200, f"Add prompts failed: {add_response.json()}"
    assert add_response.json()["added_count"] == 2

    # === STEP 7: Compare (get selection options) ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200, f"Compare failed: {compare_response.json()}"
    compare = compare_response.json()

    # Group has 2 prompts, both should have options
    assert compare["total_prompts"] == 2, f"Expected 2 prompts, got {compare['total_prompts']}"
    assert compare["prompts_with_options"] == 2, f"Expected 2 with options, got {compare['prompts_with_options']}"
    assert compare["prompts_awaiting"] == 0, f"Expected 0 awaiting, got {compare['prompts_awaiting']}"

    # Fresh count based on default selections
    initial_fresh_count = compare["default_fresh_count"]
    assert initial_fresh_count >= 2, f"Expected at least 2 fresh, got {initial_fresh_count}"

    # Build selections from compare response
    selections = _build_selections_from_compare(compare)

    # === STEP 8: Generate first report with selections (charges for fresh) ===
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"selections": selections},
        headers=auth_headers,
    )
    assert report_response.status_code == 200, f"Generate report failed: {report_response.json()}"
    report = report_response.json()

    assert report["total_prompts"] == 2
    assert report["prompts_with_data"] == 2
    assert report["prompts_awaiting"] == 0

    # Cost should match the fresh count (0.01 per evaluation per config)
    first_report_cost = Decimal(str(report["total_cost"]))
    expected_cost = Decimal("0.01") * initial_fresh_count
    assert first_report_cost == expected_cost, \
        f"Expected cost {expected_cost}, got {first_report_cost}"

    # === STEP 9: Check balance after first report ===
    balance_response = client.get("/billing/api/v1/balance", headers=auth_headers)
    assert balance_response.status_code == 200
    balance_after_first = Decimal(str(balance_response.json()["available_balance"]))
    expected_after_first = initial_balance - first_report_cost
    assert balance_after_first == expected_after_first, \
        f"Expected {expected_after_first}, got {balance_after_first}"

    # === STEP 10: Generate same report again - should be FREE ===
    # Get fresh selections (should have no fresh options since we just consumed them)
    compare2_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare2_response.status_code == 200
    compare2 = compare2_response.json()

    # No fresh evaluations since we just consumed them all
    assert compare2["default_fresh_count"] == 0, \
        f"Expected 0 fresh, got {compare2['default_fresh_count']}"

    # Build selections (should use same evaluations but now they're consumed)
    selections2 = _build_selections_from_compare(compare2)

    report2_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"selections": selections2},
        headers=auth_headers,
    )
    assert report2_response.status_code == 200, f"Generate 2nd report failed: {report2_response.json()}"
    report2 = report2_response.json()

    # No fresh evaluations - cost should be 0
    report2_cost = Decimal(str(report2["total_cost"]))
    assert report2_cost == Decimal("0.00"), f"Expected 0.00 (no fresh data), got {report2_cost}"

    # Balance should remain unchanged
    balance_response = client.get("/billing/api/v1/balance", headers=auth_headers)
    balance_after_second = Decimal(str(balance_response.json()["available_balance"]))
    assert balance_after_second == balance_after_first, \
        f"Expected {balance_after_first} (unchanged), got {balance_after_second}"

    # === STEP 11: Poll and complete a 3rd evaluation (new fresh data) ===
    poll_resp = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "PLUS"},
        headers=eval_auth_headers,
    )
    assert poll_resp.status_code == 200, f"Poll for 3rd failed: {poll_resp.json()}"
    poll_data = poll_resp.json()
    new_prompt_id = poll_data["prompt_id"]
    new_eval_id = poll_data["evaluation_id"]

    # Complete it
    submit_resp = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": new_eval_id,
            "answer": {
                "response": "Test response for third prompt",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
        headers=eval_auth_headers,
    )
    assert submit_resp.status_code == 200, f"Submit 3rd failed: {submit_resp.json()}"

    # Add the new prompt to the group
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": [new_prompt_id]},
        headers=auth_headers,
    )
    assert add_response.status_code == 200, f"Add 3rd prompt failed: {add_response.json()}"

    # === STEP 12: Compare - should show fresh evaluations for new prompt ===
    compare3_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare3_response.status_code == 200, f"Compare failed: {compare3_response.json()}"
    compare3 = compare3_response.json()

    # The newly added prompt's evaluations should be fresh
    new_fresh_count = compare3["default_fresh_count"]
    assert new_fresh_count >= 1, f"Expected at least 1 fresh, got {new_fresh_count}"

    # Build selections for third report
    selections3 = _build_selections_from_compare(compare3)

    # === STEP 13: Generate third report (charges for fresh evaluations) ===
    report3_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"selections": selections3},
        headers=auth_headers,
    )
    assert report3_response.status_code == 200, f"Generate 3rd report failed: {report3_response.json()}"
    report3 = report3_response.json()

    assert report3["total_prompts"] == 3
    assert report3["prompts_with_data"] == 3
    assert report3["prompts_awaiting"] == 0

    # Should charge for fresh evaluations (0.01 per evaluation per config)
    third_report_cost = Decimal(str(report3["total_cost"]))
    expected_third_cost = Decimal("0.01") * new_fresh_count
    assert third_report_cost == expected_third_cost, \
        f"Expected {expected_third_cost}, got {third_report_cost}"

    # === STEP 14: Check final balance ===
    balance_response = client.get("/billing/api/v1/balance", headers=auth_headers)
    assert balance_response.status_code == 200
    final_balance = Decimal(str(balance_response.json()["available_balance"]))

    # Total spent = first report + third report
    expected_final = initial_balance - first_report_cost - third_report_cost
    assert final_balance == expected_final, f"Expected {expected_final}, got {final_balance}"

    # Verify spending is correct
    total_spent = initial_balance - final_balance
    expected_spent = first_report_cost + third_report_cost
    assert total_spent == expected_spent, f"Expected to spend {expected_spent}, spent {total_spent}"

    # === STEP 15: Generate one more report - should be FREE again ===
    # Get fresh selections (should have no fresh options)
    compare4_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare4_response.status_code == 200
    compare4 = compare4_response.json()
    selections4 = _build_selections_from_compare(compare4)

    report4_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"selections": selections4},
        headers=auth_headers,
    )
    assert report4_response.status_code == 200
    report4 = report4_response.json()

    report4_cost = Decimal(str(report4["total_cost"]))
    assert report4_cost == Decimal("0.00"), f"Expected 0.00 (no fresh data), got {report4_cost}"

    # Balance should remain unchanged
    balance_response = client.get("/billing/api/v1/balance", headers=auth_headers)
    final_balance_confirmed = Decimal(str(balance_response.json()["available_balance"]))
    assert final_balance_confirmed == final_balance, \
        f"Expected {final_balance} (unchanged), got {final_balance_confirmed}"
