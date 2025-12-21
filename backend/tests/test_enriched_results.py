"""Integration tests for enriched results endpoint."""

import pytest


@pytest.mark.asyncio
async def test_get_enriched_results_with_brand_mentions(client, auth_headers):
    """Test enriched results with brand detection."""
    # First, poll for a prompt to create an evaluation
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "PLUS"},
    )
    assert poll_response.status_code == 200
    poll_data = poll_response.json()
    assert poll_data["evaluation_id"] is not None
    evaluation_id = poll_data["evaluation_id"]
    prompt_id = poll_data["prompt_id"]

    # Submit the answer with a response containing brand mentions
    submit_response = client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": evaluation_id,
            "answer": {
                "response": "Магазин Moyo пропонує найкращі ціни. Також перевірте Rozetka.",
                "citations": [
                    {"url": "https://moyo.ua/phones/123", "text": "Moyo Phones"},
                    {"url": "https://rozetka.com.ua/ua/mobile-phones/456", "text": "Rozetka Mobile"},
                ],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
    )
    assert submit_response.status_code == 200

    # Request enriched results with brand detection
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS",
            "prompt_ids": [prompt_id],
        },
        json={
            "brands": [
                {"name": "Moyo", "variations": ["Moyo", "Мойо"]},
                {"name": "Rozetka", "variations": ["Rozetka", "Розетка"]},
            ]
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check results structure
    assert "results" in data
    assert "citation_leaderboard" in data
    assert len(data["results"]) == 1

    result = data["results"][0]
    assert result["prompt_id"] == prompt_id
    assert result["brand_mentions"] is not None

    # Check brand mentions
    brand_names = [bm["brand_name"] for bm in result["brand_mentions"]]
    assert "Moyo" in brand_names
    assert "Rozetka" in brand_names

    # Check Moyo mention positions
    moyo_mention = next(bm for bm in result["brand_mentions"] if bm["brand_name"] == "Moyo")
    assert len(moyo_mention["mentions"]) >= 1
    assert moyo_mention["mentions"][0]["matched_text"] == "Moyo"
    assert moyo_mention["mentions"][0]["start"] >= 0
    assert moyo_mention["mentions"][0]["end"] > moyo_mention["mentions"][0]["start"]


@pytest.mark.asyncio
async def test_get_enriched_results_citation_leaderboard(client, auth_headers):
    """Test citation leaderboard aggregation."""
    # Create multiple evaluations with citations
    prompt_ids = []

    for i in range(2):
        poll_response = client.post(
            "/evaluations/api/v1/poll",
            json={"assistant_name": "ChatGPT", "plan_name": "FREE"},
        )
        assert poll_response.status_code == 200
        poll_data = poll_response.json()

        if poll_data["evaluation_id"] is None:
            break

        prompt_ids.append(poll_data["prompt_id"])

        # Submit with citations
        client.post(
            "/evaluations/api/v1/submit",
            json={
                "evaluation_id": poll_data["evaluation_id"],
                "answer": {
                    "response": f"Response {i}",
                    "citations": [
                        {"url": "https://rozetka.com.ua/ua/phones/item1", "text": "Phone"},
                        {"url": "https://rozetka.com.ua/ua/phones/item2", "text": "Phone 2"},
                        {"url": "https://moyo.ua/products/phone", "text": "Moyo Phone"},
                    ],
                    "timestamp": "2024-01-01T00:00:00Z",
                },
            },
        )

    if not prompt_ids:
        pytest.skip("No prompts available for testing")

    # Request enriched results
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "FREE",
            "prompt_ids": prompt_ids,
        },
        json={},  # No brands, just leaderboard
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    leaderboard = data["citation_leaderboard"]
    assert leaderboard["total_citations"] > 0
    assert len(leaderboard["items"]) > 0

    # Check that domains are present
    paths = [item["path"] for item in leaderboard["items"]]
    assert any("rozetka.com.ua" in p for p in paths)

    # Check domain-level items exist
    domain_items = [item for item in leaderboard["items"] if item["is_domain"]]
    assert len(domain_items) > 0


@pytest.mark.asyncio
async def test_get_enriched_results_without_brands(client, auth_headers):
    """Test enriched results without brand detection (just leaderboard)."""
    # Poll and complete an evaluation
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "PRO"},
    )
    assert poll_response.status_code == 200
    poll_data = poll_response.json()

    if poll_data["evaluation_id"] is None:
        pytest.skip("No prompts available")

    prompt_id = poll_data["prompt_id"]

    client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": poll_data["evaluation_id"],
            "answer": {
                "response": "Test response mentioning Moyo",
                "citations": [{"url": "https://example.com/page", "text": "Example"}],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
    )

    # Request without brands
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PRO",
            "prompt_ids": [prompt_id],
        },
        json={},  # No brands
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # brand_mentions should be null when no brands requested
    assert data["results"][0]["brand_mentions"] is None

    # Leaderboard should still be present
    assert "citation_leaderboard" in data


@pytest.mark.asyncio
async def test_get_enriched_results_invalid_assistant_plan(client, auth_headers):
    """Test returns 422 for invalid assistant/plan combination."""
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "NonExistentBot",
            "plan_name": "PLUS",
            "prompt_ids": [1],
        },
        json={},
        headers=auth_headers,
    )

    assert response.status_code == 422
    data = response.json()
    assert "Invalid assistant/plan combination" in data["detail"]


@pytest.mark.asyncio
async def test_get_enriched_results_requires_auth(client):
    """Test that endpoint requires authentication."""
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS",
            "prompt_ids": [1],
        },
        json={},
        # No auth headers
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_enriched_results_empty_prompts(client, auth_headers):
    """Test with prompt IDs that don't exist."""
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS",
            "prompt_ids": [999999, 999998],
        },
        json={"brands": [{"name": "Test", "variations": ["Test"]}]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []
    assert data["citation_leaderboard"]["total_citations"] == 0


@pytest.mark.asyncio
async def test_get_enriched_results_cyrillic_brand_detection(client, auth_headers):
    """Test detecting Cyrillic brand variations."""
    # Poll for a prompt
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "FREE"},
    )
    assert poll_response.status_code == 200
    poll_data = poll_response.json()

    if poll_data["evaluation_id"] is None:
        pytest.skip("No prompts available")

    prompt_id = poll_data["prompt_id"]

    # Submit with Cyrillic text
    client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": poll_data["evaluation_id"],
            "answer": {
                "response": "Рекомендую магазин Мойо для покупки телефонів",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
    )

    # Request with Cyrillic variation
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "FREE",
            "prompt_ids": [prompt_id],
        },
        json={"brands": [{"name": "Moyo", "variations": ["Moyo", "Мойо"]}]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    result = data["results"][0]
    assert result["brand_mentions"] is not None
    assert len(result["brand_mentions"]) == 1
    assert result["brand_mentions"][0]["brand_name"] == "Moyo"
    assert result["brand_mentions"][0]["mentions"][0]["matched_text"] == "Мойо"


def test_enriched_results_with_group_brands(client, auth_headers):
    """Test fetching brands from a prompt group via group_id."""
    # Create a prompt group with brands
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Test Group for Enriched Results",
            "brands": [
                {"name": "Rozetka", "variations": ["Rozetka", "Розетка"]},
                {"name": "Moyo", "variations": ["Moyo", "Мойо"]},
            ],
        },
        headers=auth_headers,
    )
    assert group_response.status_code == 201
    group_id = group_response.json()["id"]

    # Poll and complete an evaluation
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "PLUS"},
    )
    assert poll_response.status_code == 200
    poll_data = poll_response.json()

    if poll_data["evaluation_id"] is None:
        pytest.skip("No prompts available")

    prompt_id = poll_data["prompt_id"]

    # Submit with brand mentions
    client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": poll_data["evaluation_id"],
            "answer": {
                "response": "Купуйте телефони в Rozetka та Мойо",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
    )

    # Request enriched results with group_id (no explicit brands)
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PLUS",
            "prompt_ids": [prompt_id],
        },
        json={"group_id": group_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify brand mentions were detected using group brands
    result = data["results"][0]
    assert result["brand_mentions"] is not None
    brand_names = [bm["brand_name"] for bm in result["brand_mentions"]]
    assert "Rozetka" in brand_names
    assert "Moyo" in brand_names


def test_enriched_results_request_brands_override_group(client, auth_headers):
    """Test that request brands take precedence over group brands."""
    # Create a prompt group with brands
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Override Test Group",
            "brands": [
                {"name": "GroupBrand", "variations": ["GroupBrand"]},
            ],
        },
        headers=auth_headers,
    )
    group_id = group_response.json()["id"]

    # Poll and complete an evaluation
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "FREE"},
    )
    poll_data = poll_response.json()

    if poll_data["evaluation_id"] is None:
        pytest.skip("No prompts available")

    prompt_id = poll_data["prompt_id"]

    client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": poll_data["evaluation_id"],
            "answer": {
                "response": "Mention GroupBrand and RequestBrand",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
    )

    # Request with both group_id and explicit brands
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "FREE",
            "prompt_ids": [prompt_id],
        },
        json={
            "group_id": group_id,
            "brands": [
                {"name": "RequestBrand", "variations": ["RequestBrand"]},
            ],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Verify only RequestBrand was detected (not GroupBrand)
    result = data["results"][0]
    brand_names = [bm["brand_name"] for bm in result["brand_mentions"]]
    assert "RequestBrand" in brand_names
    assert "GroupBrand" not in brand_names


def test_enriched_results_invalid_group_id(client, auth_headers):
    """Test that invalid group_id is handled gracefully."""
    # Poll and complete an evaluation
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "PRO"},
    )
    poll_data = poll_response.json()

    if poll_data["evaluation_id"] is None:
        pytest.skip("No prompts available")

    prompt_id = poll_data["prompt_id"]

    client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": poll_data["evaluation_id"],
            "answer": {
                "response": "Test response",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
    )

    # Request with non-existent group_id
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "PRO",
            "prompt_ids": [prompt_id],
        },
        json={"group_id": 999999},
        headers=auth_headers,
    )

    # Should succeed but with no brand mentions
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["brand_mentions"] is None


def test_enriched_results_group_without_brands(client, auth_headers):
    """Test that group without brands works correctly."""
    # Create a group without brands
    group_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={"title": "No Brands Group"},
        headers=auth_headers,
    )
    group_id = group_response.json()["id"]

    # Poll and complete an evaluation
    poll_response = client.post(
        "/evaluations/api/v1/poll",
        json={"assistant_name": "ChatGPT", "plan_name": "FREE"},
    )
    poll_data = poll_response.json()

    if poll_data["evaluation_id"] is None:
        pytest.skip("No prompts available")

    prompt_id = poll_data["prompt_id"]

    client.post(
        "/evaluations/api/v1/submit",
        json={
            "evaluation_id": poll_data["evaluation_id"],
            "answer": {
                "response": "Test response",
                "citations": [],
                "timestamp": "2024-01-01T00:00:00Z",
            },
        },
    )

    # Request with group_id that has no brands
    response = client.post(
        "/evaluations/api/v1/results/enriched",
        params={
            "assistant_name": "ChatGPT",
            "plan_name": "FREE",
            "prompt_ids": [prompt_id],
        },
        json={"group_id": group_id},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # No brands in group, so brand_mentions should be None
    assert data["results"][0]["brand_mentions"] is None
