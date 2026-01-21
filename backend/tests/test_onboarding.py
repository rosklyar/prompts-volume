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
    assert data["completed_at"] is None
    assert data["has_preferences"] is False


def test_complete_onboarding_with_brand_only(client, auth_headers):
    """Test completing onboarding with brand only."""
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_country_id": 1,  # Ukraine (from seed data)
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
    assert data["default_country_id"] == 1
    assert data["default_brand"]["name"] == "Acme Corp"
    assert data["default_brand"]["domain"] == "acme.com"
    assert data["default_competitors"] == []
    assert data["onboarding_status"]["is_completed"] is True
    assert data["onboarding_status"]["has_preferences"] is True


def test_complete_onboarding_with_brand_and_competitors(client, auth_headers):
    """Test completing onboarding with brand and competitors."""
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_country_id": 1,  # Ukraine (from seed data)
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
    assert data["default_country_id"] == 1
    assert data["default_brand"]["name"] == "MyCompany"
    assert len(data["default_competitors"]) == 2
    assert data["default_competitors"][0]["name"] == "Competitor One"
    assert data["default_competitors"][1]["name"] == "Competitor Two"
    assert data["onboarding_status"]["is_completed"] is True


def test_complete_onboarding_requires_country(client, auth_headers):
    """Test that completing onboarding requires country_id."""
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_brand": {
                "name": "Acme Corp",
                "domain": "acme.com",
                "variations": [],
            },
        },
        headers=auth_headers,
    )
    # Should fail with 422 because country_id is required
    assert response.status_code == 422
    assert "default_country_id" in str(response.json())


def test_get_preferences_after_onboarding(client, auth_headers):
    """Test getting preferences after completing onboarding."""
    # Complete onboarding first
    client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_country_id": 1,
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
    assert data["default_country_id"] == 1
    assert data["default_brand"]["name"] == "TestBrand"
    assert len(data["default_competitors"]) == 1
    assert data["onboarding_status"]["is_completed"] is True


def test_get_preferences_new_user(client, auth_headers):
    """Test getting preferences for a new user without onboarding returns 400."""
    response = client.get(
        "/onboarding/api/v1/preferences",
        headers=auth_headers,
    )
    # New users without onboarding should get 400 (onboarding required)
    assert response.status_code == 400
    assert "onboarding" in response.json()["detail"].lower()


def test_update_preferences(client, auth_headers):
    """Test updating preferences via settings."""
    # Complete onboarding first
    client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_country_id": 1,
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
            "default_country_id": 1,  # Country is required for update too
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
    """Test updating preferences without completing onboarding first.

    Users can update preferences via settings anytime, even before formal onboarding.
    The preferences will be saved but onboarding is still not marked complete.
    """
    response = client.put(
        "/onboarding/api/v1/preferences",
        json={
            "default_country_id": 1,
            "default_brand": {
                "name": "DirectBrand",
                "domain": "direct.com",
                "variations": [],
            },
        },
        headers=auth_headers,
    )
    # Update works but onboarding status shows not completed
    assert response.status_code == 200
    data = response.json()
    assert data["default_brand"]["name"] == "DirectBrand"
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
            "default_country_id": 1,
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
            "default_country_id": 1,
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
            "default_country_id": 1,
            "default_brand": {"name": "  ", "variations": []},
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_invalid_country_id_accepted(client, auth_headers):
    """Test that invalid country_id is accepted (validation at use-time).

    Note: Country validation happens when the user actually tries to use the
    preferences (e.g., creating a group), not during onboarding. This is
    acceptable because the country list rarely changes.
    """
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_country_id": 99999,  # Non-existent country
            "default_brand": {"name": "Brand", "domain": "brand.com", "variations": []},
        },
        headers=auth_headers,
    )
    # Onboarding completes but using this preference for groups will fail
    assert response.status_code == 201


def test_unauthorized_access(client):
    """Test that endpoints require authentication."""
    # Status endpoint
    response = client.get("/onboarding/api/v1/status")
    assert response.status_code == 401

    # Complete endpoint
    response = client.post(
        "/onboarding/api/v1/complete",
        json={
            "default_country_id": 1,
            "default_brand": {"name": "Brand", "variations": []},
        },
    )
    assert response.status_code == 401

    # Preferences get
    response = client.get("/onboarding/api/v1/preferences")
    assert response.status_code == 401

    # Preferences put
    response = client.put(
        "/onboarding/api/v1/preferences",
        json={
            "default_country_id": 1,
            "default_brand": {"name": "Brand", "variations": []},
        },
    )
    assert response.status_code == 401
