"""Tests for prompt groups API with brand and competitors functionality."""

import pytest


# Default topic input using seeded topic ID 1
DEFAULT_TOPIC = {"existing_topic_id": 1}


def test_create_group_with_brand_and_competitors(client, auth_headers):
    """Test creating a group with brand and competitors."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Tech Companies",
            "topic": DEFAULT_TOPIC,
            "brand": {
                "name": "Apple",
                "domain": "apple.com",
                "variations": ["Apple Inc", "Apple Inc."],
            },
            "competitors": [
                {
                    "name": "Samsung",
                    "domain": "samsung.com",
                    "variations": ["Samsung Electronics"],
                },
                {
                    "name": "Google",
                    "domain": "google.com",
                    "variations": ["Alphabet", "Google LLC"],
                },
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Tech Companies"
    assert data["brand_name"] == "Apple"
    assert data["competitor_count"] == 2


def test_get_group_includes_brand_and_competitors(client, auth_headers):
    """Test that GET group detail endpoint includes brand, topic, and competitors."""
    # Create group with brand and competitors
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Get Details Test",
            "topic": DEFAULT_TOPIC,
            "brand": {
                "name": "Brand1",
                "domain": "brand1.com",
                "variations": ["var1", "var2"],
            },
            "competitors": [
                {"name": "Comp1", "domain": "comp1.com", "variations": ["c1"]},
            ],
        },
        headers=auth_headers,
    )
    group_id = create_response.json()["id"]

    # Get group details
    response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "brand" in data
    assert data["brand"]["name"] == "Brand1"
    assert data["brand"]["domain"] == "brand1.com"
    assert data["brand"]["variations"] == ["var1", "var2"]
    assert "competitors" in data
    assert len(data["competitors"]) == 1
    assert data["competitors"][0]["name"] == "Comp1"
    # Check topic info
    assert data["topic_id"] == 1
    assert "topic_title" in data
    assert "topic_description" in data


def test_update_group_competitors(client, auth_headers):
    """Test updating group competitors."""
    # Create group with initial competitors
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Update Competitors Test",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "MyBrand", "variations": []},
            "competitors": [
                {"name": "OldComp", "variations": []},
            ],
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    group_id = create_response.json()["id"]

    # Update competitors
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={
            "competitors": [
                {"name": "NewComp1", "domain": "new1.com", "variations": []},
                {"name": "NewComp2", "domain": "new2.com", "variations": []},
            ],
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["competitor_count"] == 2

    # Verify competitors were updated
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    competitors = detail_response.json()["competitors"]
    assert len(competitors) == 2
    assert competitors[0]["name"] == "NewComp1"
    assert competitors[1]["name"] == "NewComp2"


def test_get_available_prompts_with_topic(client, auth_headers):
    """Test getting available prompts for a group with topic binding."""
    # Create group with topic (uses topic 1 which has seeded prompts)
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Available Prompts Test",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "variations": []},
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    group_id = create_response.json()["id"]

    # Get available prompts - should return prompts from topic 1
    response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}/available-prompts",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "prompts" in data
    assert "total" in data
    assert data["total"] == len(data["prompts"])
    # Each prompt should have id and prompt_text
    if data["total"] > 0:
        assert "id" in data["prompts"][0]
        assert "prompt_text" in data["prompts"][0]


def test_add_gsc_prompts_to_group(client, auth_headers):
    """Test adding GSC-generated prompts to an existing group."""
    # Create a group first
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "GSC Prompts Test Group",
            "topic": DEFAULT_TOPIC,
            "brand": {"name": "TestBrand", "domain": "test.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    group_id = create_response.json()["id"]

    # Add GSC prompts
    prompts_to_add = [
        "best laptop for programming 2024",
        "how to choose a gaming laptop",
        "macbook vs windows laptop comparison",
    ]
    response = client.post(
        f"/prompt-groups/api/v1/groups/{group_id}/gsc-prompts",
        json={"prompts": prompts_to_add},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["prompts_added"] == 3

    # Verify prompts are in the group
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    group_data = detail_response.json()
    prompt_texts = [p["prompt_text"] for p in group_data["prompts"]]
    for prompt in prompts_to_add:
        assert prompt in prompt_texts
