"""Tests for onboarding API endpoints."""

import pytest


def test_get_onboarding_status_new_user(client, auth_headers):
    """Test that a new user has not completed onboarding."""
    response = client.get(
        "/onboarding/api/v1/status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_completed"] is False
    assert data["is_skipped"] is False
    assert data["completed_at"] is None
    assert data["skipped_at"] is None
    assert data["has_preferences"] is False


def test_complete_onboarding_with_brand_only(client, auth_headers):
    """Test completing onboarding with brand only."""
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_brand": {
                "name": "Acme Corp",
                "domain": "acme.com",
                "variations": ["Acme", "ACME Inc"],
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["default_brand"]["name"] == "Acme Corp"
    assert data["default_brand"]["domain"] == "acme.com"
    assert data["default_competitors"] == []
    assert data["onboarding_status"]["is_completed"] is True
    assert data["onboarding_status"]["is_skipped"] is False
    assert data["onboarding_status"]["has_preferences"] is True


def test_complete_onboarding_with_brand_and_competitors(client, auth_headers):
    """Test completing onboarding with brand and competitors."""
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_brand": {
                "name": "MyCompany",
                "domain": "mycompany.com",
                "variations": ["My Company"],
            },
            "default_competitors": [
                {
                    "name": "Competitor One",
                    "domain": "competitor1.com",
                    "variations": ["Comp1"],
                },
                {
                    "name": "Competitor Two",
                    "domain": "competitor2.com",
                    "variations": ["Comp2"],
                },
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["default_brand"]["name"] == "MyCompany"
    assert len(data["default_competitors"]) == 2
    assert data["default_competitors"][0]["name"] == "Competitor One"
    assert data["default_competitors"][1]["name"] == "Competitor Two"
    assert data["onboarding_status"]["is_completed"] is True


def test_skip_onboarding(client, auth_headers):
    """Test skipping onboarding."""
    response = client.post(
        "/onboarding/api/v1/skip",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_completed"] is False
    assert data["is_skipped"] is True
    assert data["skipped_at"] is not None
    assert data["has_preferences"] is False


def test_get_preferences_after_onboarding(client, auth_headers):
    """Test getting preferences after completing onboarding."""
    # Complete onboarding first
    client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_brand": {
                "name": "TestBrand",
                "domain": "testbrand.com",
                "variations": [],
            },
            "default_competitors": [
                {"name": "TestComp", "domain": "testcomp.com", "variations": []},
            ],
        },
        headers=auth_headers,
    )

    # Get preferences
    response = client.get(
        "/onboarding/api/v1/preferences",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["default_brand"]["name"] == "TestBrand"
    assert len(data["default_competitors"]) == 1
    assert data["onboarding_status"]["is_completed"] is True


def test_get_preferences_new_user(client, auth_headers):
    """Test getting preferences for a new user without onboarding."""
    response = client.get(
        "/onboarding/api/v1/preferences",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["default_brand"] is None
    assert data["default_competitors"] == []
    assert data["onboarding_status"]["is_completed"] is False


def test_update_preferences(client, auth_headers):
    """Test updating preferences via settings."""
    # Complete onboarding first
    client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_brand": {
                "name": "OldBrand",
                "domain": "old.com",
                "variations": [],
            },
        },
        headers=auth_headers,
    )

    # Update preferences
    response = client.put(
        "/onboarding/api/v1/preferences",
        json={
            "default_brand": {
                "name": "NewBrand",
                "domain": "new.com",
                "variations": ["New", "Brand"],
            },
            "default_competitors": [
                {"name": "NewComp", "domain": "newcomp.com", "variations": []},
            ],
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["default_brand"]["name"] == "NewBrand"
    assert data["default_brand"]["domain"] == "new.com"
    assert len(data["default_competitors"]) == 1


def test_update_preferences_without_prior_onboarding(client, auth_headers):
    """Test updating preferences without completing onboarding first."""
    response = client.put(
        "/onboarding/api/v1/preferences",
        json={
            "default_brand": {
                "name": "DirectBrand",
                "domain": "direct.com",
                "variations": [],
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["default_brand"]["name"] == "DirectBrand"
    # Onboarding status should still show not completed
    assert data["onboarding_status"]["is_completed"] is False


def test_competitors_limit_validation(client, auth_headers):
    """Test that more than 10 competitors are rejected."""
    competitors = [
        {"name": f"Competitor {i}", "domain": f"comp{i}.com", "variations": []}
        for i in range(11)  # 11 competitors should fail
    ]
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_brand": {"name": "Brand", "variations": []},
            "default_competitors": competitors,
        },
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "10" in str(response.json())  # Should mention the limit


def test_domain_normalization_in_preferences(client, auth_headers):
    """Test that domains are normalized in preferences."""
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_brand": {
                "name": "TestBrand",
                "domain": "HTTPS://WWW.EXAMPLE.COM/",
                "variations": [],
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["default_brand"]["domain"] == "www.example.com"


def test_empty_brand_name_validation(client, auth_headers):
    """Test that empty brand names are rejected."""
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_brand": {"name": "  ", "variations": []},
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_onboarding_status_after_skip_then_complete(client, auth_headers):
    """Test that completing onboarding clears skip status."""
    # Skip first
    client.post("/onboarding/api/v1/skip", headers=auth_headers)

    # Then complete
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_brand": {"name": "Brand", "domain": "brand.com", "variations": []},
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["onboarding_status"]["is_completed"] is True
    assert data["onboarding_status"]["is_skipped"] is False


def test_unauthorized_access(client):
    """Test that endpoints require authentication."""
    # Status endpoint
    response = client.get("/onboarding/api/v1/status")
    assert response.status_code == 401

    # Complete endpoint
    response = client.post(
        "/onboarding/api/v1/complete",
        json={"default_brand": {"name": "Brand", "variations": []}},
    )
    assert response.status_code == 401

    # Skip endpoint
    response = client.post("/onboarding/api/v1/skip")
    assert response.status_code == 401

    # Preferences get
    response = client.get("/onboarding/api/v1/preferences")
    assert response.status_code == 401

    # Preferences put
    response = client.put(
        "/onboarding/api/v1/preferences",
        json={"default_brand": {"name": "Brand", "variations": []}},
    )
    assert response.status_code == 401
