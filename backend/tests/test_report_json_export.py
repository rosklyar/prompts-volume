"""Integration test for report JSON export feature.

Tests the JSON export endpoint returns properly structured data with all statistics.
"""

import json
import uuid


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


def test_json_export_happy_path(client, eval_auth_headers, create_verified_user):
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

    # === STEP 3: Poll and complete 2 evaluations with citations and brand mentions ===
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

        # Complete the evaluation with brand mentions and citations
        submit_resp = client.post(
            "/evaluations/api/v1/submit",
            json={
                "evaluation_id": eval_id,
                "answer": {
                    "response": f"TestBrand is a great option. You should also check testbrand.com for more info. CompetitorA is another alternative available at competitor-a.com.",
                    "citations": [
                        {"url": "https://testbrand.com/products", "text": "TestBrand product page"},
                        {"url": "https://example.com/reviews", "text": "Reviews"},
                        {"url": "https://competitor-a.com/about", "text": "CompetitorA about"},
                    ],
                    "timestamp": "2024-01-01T00:00:00Z",
                },
            },
            headers=eval_auth_headers,
        )
        assert submit_resp.status_code == 200, f"Submit {i} failed: {submit_resp.json()}"

    # === STEP 4: Add prompts to the group ===
    add_response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/prompts",
        json={"prompt_ids": prompt_ids},
        headers=auth_headers,
    )
    assert add_response.status_code == 200, f"Add prompts failed: {add_response.json()}"

    # === STEP 5: Get compare and build selections ===
    compare_response = client.get(
        f"/reports/api/v1/groups/{group_id}/compare",
        headers=auth_headers,
    )
    assert compare_response.status_code == 200, f"Compare failed: {compare_response.json()}"
    selections = _build_selections_from_compare(compare_response.json())

    # === STEP 6: Generate report ===
    report_response = client.post(
        f"/reports/api/v1/groups/{group_id}/generate",
        json={"selections": selections},
        headers=auth_headers,
    )
    assert report_response.status_code == 200, f"Generate report failed: {report_response.json()}"
    report = report_response.json()
    report_id = report["id"]

    # === STEP 7: Export as JSON ===
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

    # === STEP 8: Verify export structure ===

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
    prompts = export_data["prompts"]
    assert len(prompts) == 2

    for prompt_item in prompts:
        assert "prompt_id" in prompt_item
        assert "prompt_text" in prompt_item
        assert "status" in prompt_item
        assert "answer" in prompt_item

        # Verify answer structure
        if prompt_item["answer"]:
            answer = prompt_item["answer"]
            assert "response" in answer
            assert "citations" in answer
            assert len(answer["citations"]) == 3  # We added 3 citations

            for citation in answer["citations"]:
                assert "url" in citation
                assert "text" in citation

    # Statistics
    assert "statistics" in export_data
    stats = export_data["statistics"]

    # Brand visibility
    assert "brand_visibility" in stats
    brand_vis = stats["brand_visibility"]
    assert len(brand_vis) == 2  # TestBrand + CompetitorA

    # Find TestBrand visibility (should be target)
    testbrand_vis = next((v for v in brand_vis if v["brand_name"] == "TestBrand"), None)
    assert testbrand_vis is not None
    assert testbrand_vis["is_target_brand"] is True
    assert testbrand_vis["total_prompts"] == 2
    # TestBrand is mentioned in both responses
    assert testbrand_vis["prompts_with_mentions"] == 2
    assert testbrand_vis["visibility_percentage"] == 100.0

    # Domain mentions
    assert "domain_mentions" in stats
    domain_mentions = stats["domain_mentions"]
    assert len(domain_mentions) == 2  # testbrand.com + competitor-a.com

    testbrand_dm = next((d for d in domain_mentions if d["domain"] == "testbrand.com"), None)
    assert testbrand_dm is not None
    assert testbrand_dm["is_target_brand"] is True
    # Domain testbrand.com is mentioned in both responses
    assert testbrand_dm["prompts_with_mentions"] == 2

    # Citation domains
    assert "citation_domains" in stats
    citation_domains = stats["citation_domains"]
    assert len(citation_domains) == 2

    testbrand_cd = next((c for c in citation_domains if c["domain"] == "testbrand.com"), None)
    assert testbrand_cd is not None
    assert testbrand_cd["is_target_brand"] is True
    # 2 prompts × 1 citation each with testbrand.com
    assert testbrand_cd["citation_count"] == 2

    # Domain sources leaderboard
    assert "domain_sources_leaderboard" in stats
    domain_sources = stats["domain_sources_leaderboard"]
    assert len(domain_sources) > 0

    for item in domain_sources:
        assert "path" in item
        assert "count" in item
        assert "is_domain" in item

    # Page paths leaderboard
    assert "page_paths_leaderboard" in stats

    # Total citations
    assert "total_citations" in stats
    # 2 prompts × 3 citations each = 6 total
    assert stats["total_citations"] == 6
