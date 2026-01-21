"""Tests for onboarding API endpoints."""

import pytest


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
