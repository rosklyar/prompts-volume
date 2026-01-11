"""Integration test for report JSON export feature.

Tests the JSON export endpoint returns properly structured data with all statistics.

Uses Bright Data webhook simulation for creating evaluations.
"""

import json
import uuid

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


def _build_selections_from_compare(compare_response: dict) -> list[dict]:
    """Build selections list from compare response using default selections."""
    selections = []
    for ps in compare_response["prompt_selections"]:
        selections.append({
            "prompt_id": ps["prompt_id"],
            "evaluation_id": ps["default_selection"],
        })
    return selections


def test_json_export_happy_path(client, create_verified_user, simulate_webhook):
    """Test JSON export returns complete data with all statistics.

    This test validates the JSON export feature:
    - Creates a group with brand and competitors
    - Generates evaluations with citations (for leaderboards)
    - Generates a report
    - Exports as JSON
    - Verifies all expected fields are present:
      - export_version, exported_at
      - report metadata
      - brand_info with brand and competitors
      - prompts with answers and citations
      - statistics: brand_visibility, domain_mentions, citation_domains, leaderboards
    """
    # === STEP 1: Sign up ===
    unique_email = f"test-export-{uuid.uuid4()}@example.com"
    auth_headers = create_verified_user(unique_email, "testpassword123", "Export Test User")

    # === STEP 2: Create group with brand and competitors ===
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Export Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {
                "name": "TestBrand",
                "domain": "testbrand.com",
                "variations": ["TestBrand", "Test Brand"],
            },
            "competitors": [
                {
                    "name": "CompetitorA",
                    "domain": "competitor-a.com",
                    "variations": ["CompetitorA", "Competitor A"],
                },
            ],
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201, f"Group creation failed: {group_response.json()}"
    group_id = group_response.json()["id"]

    # === STEP 3: Get 2 prompts and create evaluations with citations via webhook ===
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
    assert add_response.status_code == 200, f"Add prompts failed: {add_response.json()}"

    # Request fresh execution
    request_resp = client.post(
        "/execution/api/v1/request-fresh",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert request_resp.status_code == 200, f"Request fresh failed: {request_resp.json()}"
    request_data = request_resp.json()
    batch_id = request_data["batch_id"]

    # Determine which prompts were actually queued (not already pending)
    queued_prompt_ids = [
        item["prompt_id"]
        for item in request_data["items"]
        if item["status"] == "queued"
    ]

    # If we have a batch, simulate webhook for queued prompts
    if batch_id is not None and queued_prompt_ids:
        webhook_items = []
        for pid in queued_prompt_ids:
            if pid in prompts_dict:
                item = {
                    "prompt": prompts_dict[pid],
                    "answer_text": f"TestBrand is a great option. You should also check testbrand.com for more info. CompetitorA is another alternative available at competitor-a.com.",
                    "citations": [
                        {"url": "https://testbrand.com/products", "title": "TestBrand product page", "domain": "testbrand.com", "cited": True},
                        {"url": "https://example.com/reviews", "title": "Reviews", "domain": "example.com", "cited": True},
                        {"url": "https://competitor-a.com/about", "title": "CompetitorA about", "domain": "competitor-a.com", "cited": True},
                    ],
                }
                webhook_items.append(item)

        if webhook_items:
            webhook_resp = simulate_webhook(batch_id, webhook_items)
            assert webhook_resp.status_code == 200, f"Webhook failed: {webhook_resp.json()}"

    # === STEP 4: Get compare and build selections ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200, f"Compare failed: {compare_response.json()}"
    compare_data = compare_response.json()
    selections = _build_selections_from_compare(compare_data)

    # Make sure we have at least 1 prompt with data
    prompts_with_options = compare_data["prompts_with_options"]
    assert prompts_with_options >= 1, "Need at least 1 prompt with evaluation options"

    # === STEP 5: Generate report ===
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"selections": selections},
        headers=auth_headers,
    )
    assert report_response.status_code == 200, f"Generate report failed: {report_response.json()}"
    report = report_response.json()
    report_id = report["id"]

    # === STEP 6: Export as JSON ===
    export_response = client.get(
        f"/reports/api/v1/groups/{group_id}/reports/{report_id}/export/json",
        headers=auth_headers,
    )
    assert export_response.status_code == 200, f"Export failed: {export_response.text}"

    # Verify Content-Disposition header
    content_disposition = export_response.headers.get("Content-Disposition", "")
    assert "attachment" in content_disposition
    assert f"report_{report_id}_" in content_disposition
    assert ".json" in content_disposition

    # Parse JSON content
    export_data = json.loads(export_response.content)

    # === STEP 7: Verify export structure ===

    # Root fields
    assert "export_version" in export_data
    assert export_data["export_version"] == "1.0"
    assert "exported_at" in export_data

    # Report metadata
    assert "report" in export_data
    report_meta = export_data["report"]
    assert report_meta["id"] == report_id
    assert report_meta["group_id"] == group_id
    assert "created_at" in report_meta
    assert "total_prompts" in report_meta
    assert "prompts_with_data" in report_meta
    assert "prompts_awaiting" in report_meta
    assert "total_cost" in report_meta

    # Brand info
    assert "brand_info" in export_data
    brand_info = export_data["brand_info"]
    assert brand_info["brand"]["name"] == "TestBrand"
    assert brand_info["brand"]["domain"] == "testbrand.com"
    assert len(brand_info["competitors"]) == 1
    assert brand_info["competitors"][0]["name"] == "CompetitorA"

    # Prompts
    assert "prompts" in export_data
    prompts_export = export_data["prompts"]
    assert len(prompts_export) == 2  # We added 2 prompts to the group

    # Check structure of prompts (don't assume specific citation counts since
    # prompts may have pre-existing evaluations from seeded data)
    for prompt_item in prompts_export:
        assert "prompt_id" in prompt_item
        assert "prompt_text" in prompt_item
        assert "status" in prompt_item
        assert "answer" in prompt_item

        if prompt_item["answer"]:
            answer = prompt_item["answer"]
            assert "response" in answer
            assert "citations" in answer

    # Statistics
    assert "statistics" in export_data
    stats = export_data["statistics"]

    # Brand visibility (at least 1 brand should be visible)
    assert "brand_visibility" in stats
    brand_vis = stats["brand_visibility"]
    assert len(brand_vis) >= 1  # At least target brand

    # Check that TestBrand is in visibility (it's the target brand)
    testbrand_vis = next((v for v in brand_vis if v["brand_name"] == "TestBrand"), None)
    assert testbrand_vis is not None
    assert testbrand_vis["is_target_brand"] is True

    # Domain mentions
    assert "domain_mentions" in stats

    # Citation domains
    assert "citation_domains" in stats

    # Domain sources leaderboard
    assert "domain_sources_leaderboard" in stats

    # Page paths leaderboard
    assert "page_paths_leaderboard" in stats

    # Total citations (just check it exists, actual count depends on data)
    assert "total_citations" in stats
