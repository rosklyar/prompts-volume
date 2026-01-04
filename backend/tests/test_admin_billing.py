"""Tests for admin billing endpoints (superuser top-up functionality)."""

import pytest


class TestAdminListUsers:
    """Tests for GET /billing/api/v1/admin/users endpoint."""

    def test_admin_list_users_success(self, client, superuser_auth_headers, test_user):
        """Test that superuser can list users with balances."""
        response = client.get(
            "/billing/api/v1/admin/users",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] >= 1  # At least the test user exists

        # Check that user objects have expected fields
        if data["users"]:
            user = data["users"][0]
            assert "id" in user
            assert "email" in user
            assert "full_name" in user
            assert "is_active" in user
            assert "available_balance" in user
            assert "expiring_soon_amount" in user
            assert "expiring_soon_at" in user

    def test_admin_list_users_search(
        self, client, superuser_auth_headers, test_user, test_superuser
    ):
        """Test searching users by email."""
        # Search for a specific user
        response = client.get(
            f"/billing/api/v1/admin/users?search={test_user.email}",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should find at least the searched user
        assert data["total"] >= 1
        emails = [u["email"] for u in data["users"]]
        assert test_user.email in emails

    def test_admin_list_users_pagination(self, client, superuser_auth_headers):
        """Test pagination parameters."""
        response = client.get(
            "/billing/api/v1/admin/users?limit=1&skip=0",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) <= 1

    def test_admin_list_users_forbidden_for_regular_user(
        self, client, auth_headers
    ):
        """Test that regular users cannot access admin endpoint."""
        response = client.get(
            "/billing/api/v1/admin/users",
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "privileges" in response.json()["detail"].lower()

    def test_admin_list_users_unauthorized(self, client):
        """Test that unauthenticated requests are rejected."""
        response = client.get("/billing/api/v1/admin/users")
        assert response.status_code == 401


class TestAdminTopUpUser:
    """Tests for POST /billing/api/v1/admin/users/{user_id}/top-up endpoint."""

    def test_admin_top_up_user_success(
        self, client, superuser_auth_headers, test_user
    ):
        """Test that superuser can top up another user's balance."""
        response = client.post(
            f"/billing/api/v1/admin/users/{test_user.id}/top-up",
            json={"amount": 50.00, "note": "Test top-up"},
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert float(data["amount_added"]) == 50.00
        assert float(data["new_balance"]) >= 50.00
        assert "transaction_id" in data

    def test_admin_top_up_without_note(
        self, client, superuser_auth_headers, test_user
    ):
        """Test top-up without optional note."""
        response = client.post(
            f"/billing/api/v1/admin/users/{test_user.id}/top-up",
            json={"amount": 25.00},
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert float(data["amount_added"]) == 25.00

    def test_admin_top_up_user_not_found(self, client, superuser_auth_headers):
        """Test top-up for non-existent user returns 404."""
        response = client.post(
            "/billing/api/v1/admin/users/nonexistent-user-id/top-up",
            json={"amount": 10.00},
            headers=superuser_auth_headers,
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_admin_top_up_invalid_amount(
        self, client, superuser_auth_headers, test_user
    ):
        """Test top-up with invalid amount."""
        # Zero amount
        response = client.post(
            f"/billing/api/v1/admin/users/{test_user.id}/top-up",
            json={"amount": 0},
            headers=superuser_auth_headers,
        )
        assert response.status_code == 422

        # Negative amount
        response = client.post(
            f"/billing/api/v1/admin/users/{test_user.id}/top-up",
            json={"amount": -10.00},
            headers=superuser_auth_headers,
        )
        assert response.status_code == 422

    def test_admin_top_up_forbidden_for_regular_user(
        self, client, auth_headers, test_user
    ):
        """Test that regular users cannot use admin top-up endpoint."""
        response = client.post(
            f"/billing/api/v1/admin/users/{test_user.id}/top-up",
            json={"amount": 10.00},
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "privileges" in response.json()["detail"].lower()

    def test_admin_top_up_unauthorized(self, client, test_user):
        """Test that unauthenticated requests are rejected."""
        response = client.post(
            f"/billing/api/v1/admin/users/{test_user.id}/top-up",
            json={"amount": 10.00},
        )
        assert response.status_code == 401

    def test_admin_top_up_updates_balance(
        self, client, superuser_auth_headers, test_user
    ):
        """Test that top-up actually updates user's balance in list."""
        # First top-up
        top_up_response = client.post(
            f"/billing/api/v1/admin/users/{test_user.id}/top-up",
            json={"amount": 100.00, "note": "Initial top-up"},
            headers=superuser_auth_headers,
        )
        assert top_up_response.status_code == 200
        new_balance = top_up_response.json()["new_balance"]

        # Verify in user list
        list_response = client.get(
            f"/billing/api/v1/admin/users?search={test_user.email}",
            headers=superuser_auth_headers,
        )
        assert list_response.status_code == 200
        users = list_response.json()["users"]
        user_in_list = next(u for u in users if u["id"] == test_user.id)
        assert float(user_in_list["available_balance"]) == float(new_balance)
