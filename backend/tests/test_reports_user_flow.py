"""Integration test for complete reports user flow.

Tests the complete user journey:
1. Sign up (gets signup credits)
2. Login
3. Create group with prompts
4. Generate report (charges for fresh evaluations)
5. Generating again is free (already consumed)
6. Add more evaluations
7. Compare (shows fresh data)
8. Generate another report (charges only for new)
9. Verify balance changes correctly
"""

import uuid
from decimal import Decimal


def test_complete_report_user_flow(client):
    """Test complete user journey: signup → reports → billing.

    This test validates the entire reports and billing integration:
    - User signs up and receives 10.00 signup credits
    - Creates a prompt group with prompts
    - Generates reports and is charged for fresh evaluations
    - Subsequent reports for same data are free (already consumed)
    - New evaluations are charged when added
    - Balance decreases correctly with each charge
    """
    # === STEP 1: Sign up ===
    unique_email = f"test-flow-{uuid.uuid4()}@example.com"
    signup_response = client.post(
        "/api/v1/users/signup",
        json={
            "email": unique_email,
            "password": "testpassword123",
            "full_name": "Flow Test User",
        },
    )
    assert signup_response.status_code == 200, f"Signup failed: {signup_response.json()}"

    # === STEP 2: Login ===
    login_response = client.post(
        "/api/v1/login/access-token",
        data={
            "username": unique_email,
            "password": "testpassword123",
        },
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.json()}"
    token = login_response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # === STEP 3: Check initial balance (should be 10.00 from signup credits) ===
    balance_response = client.get("/billing/api/v1/balance", headers=auth_headers)
    assert balance_response.status_code == 200
    initial_balance = Decimal(str(balance_response.json()["available_balance"]))
    assert initial_balance == Decimal("10.00"), f"Expected 10.00, got {initial_balance}"

    # === STEP 4: Create group (brands are required) ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Report Test Group",
            "brands": [{"name": "TestBrand", "variations": ["test"]}],
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

    # === STEP 7: Preview report ===
    preview_response = client.get(
        f"/reports/api/v1/groups/{group_id}/preview",
        headers=auth_headers,
    )
    assert preview_response.status_code == 200, f"Preview failed: {preview_response.json()}"
    preview = preview_response.json()

    # Group has 2 prompts, both should have data
    assert preview["total_prompts"] == 2, f"Expected 2 prompts, got {preview['total_prompts']}"
    assert preview["prompts_with_data"] == 2, f"Expected 2 with data, got {preview['prompts_with_data']}"
    assert preview["prompts_awaiting"] == 0, f"Expected 0 awaiting, got {preview['prompts_awaiting']}"

    # Fresh evaluations count includes ALL evaluations user hasn't consumed
    # (including any from seed data for these prompts)
    initial_fresh_count = preview["fresh_evaluations"]
    assert initial_fresh_count >= 2, f"Expected at least 2 fresh, got {initial_fresh_count}"

    # === STEP 8: Generate first report (charges for all fresh evaluations) ===
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"include_previous": True},
        headers=auth_headers,
    )
    assert report_response.status_code == 200, f"Generate report failed: {report_response.json()}"
    report = report_response.json()

    assert report["total_prompts"] == 2
    assert report["prompts_with_data"] == 2
    assert report["prompts_awaiting"] == 0

    # Cost should match the fresh count (1.00 per evaluation)
    first_report_cost = Decimal(str(report["total_cost"]))
    assert first_report_cost == Decimal(str(initial_fresh_count)), \
        f"Expected cost {initial_fresh_count}.00, got {first_report_cost}"

    # === STEP 9: Check balance after first report ===
    balance_response = client.get("/billing/api/v1/balance", headers=auth_headers)
    assert balance_response.status_code == 200
    balance_after_first = Decimal(str(balance_response.json()["available_balance"]))
    expected_after_first = initial_balance - first_report_cost
    assert balance_after_first == expected_after_first, \
        f"Expected {expected_after_first}, got {balance_after_first}"

    # === STEP 10: Generate same report again - should be FREE ===
    report2_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"include_previous": True},
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
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200, f"Compare failed: {compare_response.json()}"
    compare = compare_response.json()

    # The newly added prompt's evaluations should be fresh
    new_fresh_count = compare["fresh_data_count"]
    assert new_fresh_count >= 1, f"Expected at least 1 fresh, got {new_fresh_count}"

    # === STEP 13: Generate third report (charges for fresh evaluations) ===
    report3_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"include_previous": True},
        headers=auth_headers,
    )
    assert report3_response.status_code == 200, f"Generate 3rd report failed: {report3_response.json()}"
    report3 = report3_response.json()

    assert report3["total_prompts"] == 3
    assert report3["prompts_with_data"] == 3
    assert report3["prompts_awaiting"] == 0

    # Should charge for fresh evaluations
    third_report_cost = Decimal(str(report3["total_cost"]))
    assert third_report_cost == Decimal(str(new_fresh_count)), \
        f"Expected {new_fresh_count}.00, got {third_report_cost}"

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
    report4_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"include_previous": True},
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
