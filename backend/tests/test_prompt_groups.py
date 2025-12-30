"""Tests for prompt groups API with brands functionality."""

import pytest


def test_create_group_with_brands(client, auth_headers):
    """Test creating a group with brands."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Electronics Retailers",
            "brands": [
                {"name": "Rozetka", "variations": ["Rozetka", "Розетка", "rozetka.com.ua"]},
                {"name": "Moyo", "variations": ["Moyo", "Мойо"]},
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Electronics Retailers"
    assert data["brand_count"] == 2
    assert data["prompt_count"] == 0


def test_create_group_without_brands_fails(client, auth_headers):
    """Test that creating a group without brands fails validation."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={"title": "No Brands Group"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "Field required" in response.json()["detail"][0]["msg"]


def test_create_group_with_empty_brands_fails(client, auth_headers):
    """Test that creating a group with empty brands list fails validation."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={"title": "Empty Brands Group", "brands": []},
        headers=auth_headers,
    )
    assert response.status_code == 422
    # Should have at least one brand


def test_brand_name_uniqueness_validation(client, auth_headers):
    """Test that duplicate brand names within a group are rejected."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Duplicate Brands Test",
            "brands": [
                {"name": "Rozetka", "variations": ["rozetka"]},
                {"name": "Rozetka", "variations": ["розетка"]},  # Duplicate
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "Brand names must be unique" in response.json()["detail"][0]["msg"]


def test_empty_brand_name_validation(client, auth_headers):
    """Test that empty brand names are rejected."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Empty Brand Name Test",
            "brands": [
                {"name": "  ", "variations": ["test"]},
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_brand_variations_filter_empty_strings(client, auth_headers):
    """Test that empty variation strings are filtered out."""
    response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Filter Variations Test",
            "brands": [
                {"name": "TestBrand", "variations": ["valid", "  ", "", "also_valid"]},
            ],
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
    brands = detail_response.json()["brands"]
    assert len(brands) == 1
    assert brands[0]["name"] == "TestBrand"
    assert brands[0]["variations"] == ["valid", "also_valid"]


def test_get_group_includes_brands(client, auth_headers):
    """Test that GET group detail endpoint includes brands."""
    # Create group with brands
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Get Brands Test",
            "brands": [
                {"name": "Brand1", "variations": ["var1", "var2"]},
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
    assert "brands" in data
    assert len(data["brands"]) == 1
    assert data["brands"][0]["name"] == "Brand1"
    assert data["brands"][0]["variations"] == ["var1", "var2"]


def test_get_groups_includes_brand_count(client, auth_headers):
    """Test that GET groups list includes brand_count."""
    # Create group with brands
    client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Brand Count Test",
            "brands": [
                {"name": "Brand1", "variations": []},
                {"name": "Brand2", "variations": []},
                {"name": "Brand3", "variations": []},
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
    test_group = next(g for g in groups if g["title"] == "Brand Count Test")
    assert test_group["brand_count"] == 3


def test_update_group_brands(client, auth_headers):
    """Test updating group brands."""
    # Create group with initial brands
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Update Brands Test",
            "brands": [{"name": "InitialBrand", "variations": ["initial"]}],
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 201
    group_id = create_response.json()["id"]

    # Update with different brands
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={
            "brands": [
                {"name": "NewBrand", "variations": ["new1", "new2"]},
            ],
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["brand_count"] == 1

    # Verify brands were updated
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    brands = detail_response.json()["brands"]
    assert len(brands) == 1
    assert brands[0]["name"] == "NewBrand"


def test_clear_group_brands(client, auth_headers):
    """Test clearing group brands with empty array."""
    # Create group with brands
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Clear Brands Test",
            "brands": [
                {"name": "TempBrand", "variations": []},
            ],
        },
        headers=auth_headers,
    )
    group_id = create_response.json()["id"]

    # Clear brands with empty array
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={"brands": []},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["brand_count"] == 0

    # Verify brands were cleared
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    brands = detail_response.json()["brands"]
    assert brands == []


def test_update_group_title_only(client, auth_headers):
    """Test updating only the title without changing brands."""
    # Create group with brands
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Original Title",
            "brands": [
                {"name": "OriginalBrand", "variations": ["var1"]},
            ],
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
    assert update_response.json()["brand_count"] == 1

    # Verify brands unchanged
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    assert detail_response.json()["title"] == "New Title"
    assert detail_response.json()["brands"][0]["name"] == "OriginalBrand"


def test_update_both_title_and_brands(client, auth_headers):
    """Test updating both title and brands simultaneously."""
    # Create group
    create_response = client.post(
        "/prompt-groups/api/v1/groups",
        json={
            "title": "Old Title",
            "brands": [{"name": "OldBrand", "variations": []}],
        },
        headers=auth_headers,
    )
    group_id = create_response.json()["id"]

    # Update both
    update_response = client.patch(
        f"/prompt-groups/api/v1/groups/{group_id}",
        json={
            "title": "Updated Title",
            "brands": [{"name": "UpdatedBrand", "variations": ["new_var"]}],
        },
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Title"
    assert update_response.json()["brand_count"] == 1

    # Verify both updated
    detail_response = client.get(
        f"/prompt-groups/api/v1/groups/{group_id}",
        headers=auth_headers,
    )
    data = detail_response.json()
    assert data["title"] == "Updated Title"
    assert data["brands"][0]["name"] == "UpdatedBrand"
    assert data["brands"][0]["variations"] == ["new_var"]
