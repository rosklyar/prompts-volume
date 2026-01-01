"""Tests for prompt groups API with brand and competitors functionality."""

import pytest


def test_create_group_with_brand_only(client, auth_headers):
    """Test creating a group with brand only (no competitors)."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Electronics Retailers",
            "brand": {
                "name": "Rozetka",
                "domain": "rozetka.com.ua",
                "variations": ["Rozetka", "Розетка"],
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Electronics Retailers"
    assert data["brand_name"] == "Rozetka"
    assert data["competitor_count"] == 0
    assert data["prompt_count"] == 0


def test_create_group_with_brand_and_competitors(client, auth_headers):
    """Test creating a group with brand and competitors."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Tech Companies",
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


def test_create_group_without_brand_fails(client, auth_headers):
    """Test that creating a group without brand fails validation."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={"title": "No Brand Group"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]


def test_empty_brand_name_validation(client, auth_headers):
    """Test that empty brand names are rejected."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Empty Brand Name Test",
            "brand": {"name": "  ", "variations": ["test"]},
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_competitor_name_uniqueness_validation(client, auth_headers):
    """Test that duplicate competitor names within a group are rejected."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Duplicate Competitors Test",
            "brand": {"name": "MyBrand", "variations": []},
            "competitors": [
                {"name": "CompetitorA", "variations": ["a"]},
                {"name": "competitora", "variations": ["b"]},  # Duplicate (case-insensitive)
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "Competitor names must be unique" in response.json()["detail"][0]["msg"]


def test_brand_variations_filter_empty_strings(client, auth_headers):
    """Test that empty variation strings are filtered out."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Filter Variations Test",
            "brand": {
                "name": "TestBrand",
                "variations": ["valid", "  ", "", "also_valid"],
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 201

    # Fetch the group details to verify variations were filtered
    group_id = response.json()["id"]
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    brand = detail_response.json()["brand"]
    assert brand["name"] == "TestBrand"
    assert brand["variations"] == ["valid", "also_valid"]


def test_domain_normalization(client, auth_headers):
    """Test that domain URLs are normalized."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Domain Normalization Test",
            "brand": {
                "name": "TestBrand",
                "domain": "https://www.EXAMPLE.COM/",
                "variations": [],
            },
            "competitors": [
                {
                    "name": "Competitor",
                    "domain": "HTTP://test.COM/path/",
                    "variations": [],
                },
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201

    # Fetch the group details to verify domain was normalized
    group_id = response.json()["id"]
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    data = detail_response.json()
    assert data["brand"]["domain"] == "www.example.com"
    assert data["competitors"][0]["domain"] == "test.com/path"


def test_get_group_includes_brand_and_competitors(client, auth_headers):
    """Test that GET group detail endpoint includes brand and competitors."""
    # Create group with brand and competitors
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Get Details Test",
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


def test_get_groups_includes_brand_name_and_competitor_count(client, auth_headers):
    """Test that GET groups list includes brand_name and competitor_count."""
    # Create group with brand and competitors
    client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "List Test",
            "brand": {"name": "MyBrand", "variations": []},
            "competitors": [
                {"name": "Comp1", "variations": []},
                {"name": "Comp2", "variations": []},
                {"name": "Comp3", "variations": []},
            ],
        },
        headers=auth_headers,
    )

    # Get all groups
    response = client.get(
        "/prompt-groups/api/v1/groups",
        headers=auth_headers,
    )
    assert response.status_code == 200
    groups = response.json()["groups"]

    # Find our test group
    test_group = next(g for g in groups if g["title"] == "List Test")
    assert test_group["brand_name"] == "MyBrand"
    assert test_group["competitor_count"] == 3


def test_update_group_brand(client, auth_headers):
    """Test updating group brand."""
    # Create group with initial brand
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Update Brand Test",
            "brand": {"name": "InitialBrand", "domain": "initial.com", "variations": ["initial"]},
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    group_id = create_response.json()["id"]

    # Update with different brand
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={
            "brand": {"name": "NewBrand", "domain": "new.com", "variations": ["new1", "new2"]},
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["brand_name"] == "NewBrand"

    # Verify brand was updated
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    brand = detail_response.json()["brand"]
    assert brand["name"] == "NewBrand"
    assert brand["domain"] == "new.com"


def test_update_group_competitors(client, auth_headers):
    """Test updating group competitors."""
    # Create group with initial competitors
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Update Competitors Test",
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


def test_clear_group_competitors(client, auth_headers):
    """Test clearing group competitors with empty array."""
    # Create group with competitors
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Clear Competitors Test",
            "brand": {"name": "MyBrand", "variations": []},
            "competitors": [
                {"name": "TempComp", "variations": []},
            ],
        },
        headers=auth_headers,
    )
    group_id = create_response.json()["id"]

    # Clear competitors with empty array
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={"competitors": []},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["competitor_count"] == 0

    # Verify competitors were cleared
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    competitors = detail_response.json()["competitors"]
    assert competitors == []


def test_update_group_title_only(client, auth_headers):
    """Test updating only the title without changing brand or competitors."""
    # Create group with brand
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Original Title",
            "brand": {"name": "OriginalBrand", "domain": "original.com", "variations": ["var1"]},
            "competitors": [{"name": "Comp1", "variations": []}],
        },
        headers=auth_headers,
    )
    group_id = create_response.json()["id"]

    # Update only title
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={"title": "New Title"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "New Title"
    assert update_response.json()["brand_name"] == "OriginalBrand"
    assert update_response.json()["competitor_count"] == 1

    # Verify brand unchanged
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    assert detail_response.json()["title"] == "New Title"
    assert detail_response.json()["brand"]["name"] == "OriginalBrand"
    assert len(detail_response.json()["competitors"]) == 1


def test_update_both_title_and_brand(client, auth_headers):
    """Test updating both title and brand simultaneously."""
    # Create group
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Old Title",
            "brand": {"name": "OldBrand", "variations": []},
        },
        headers=auth_headers,
    )
    group_id = create_response.json()["id"]

    # Update both
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={
            "title": "Updated Title",
            "brand": {"name": "UpdatedBrand", "domain": "updated.com", "variations": ["new_var"]},
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Title"
    assert update_response.json()["brand_name"] == "UpdatedBrand"

    # Verify both updated
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    data = detail_response.json()
    assert data["title"] == "Updated Title"
    assert data["brand"]["name"] == "UpdatedBrand"
    assert data["brand"]["domain"] == "updated.com"
    assert data["brand"]["variations"] == ["new_var"]


def test_optional_domain_field(client, auth_headers):
    """Test that domain field is optional for both brand and competitors."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "No Domain Test",
            "brand": {"name": "BrandWithoutDomain", "variations": ["var"]},
            "competitors": [
                {"name": "CompWithoutDomain", "variations": []},
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201

    # Verify domain is null
    group_id = response.json()["id"]
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    data = detail_response.json()
    assert data["brand"]["domain"] is None
    assert data["competitors"][0]["domain"] is None
