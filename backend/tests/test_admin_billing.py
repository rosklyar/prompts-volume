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


class TestAdminTopUpUser:
    """Tests for POST /billing/api/v1/admin/users/{user_id}/top-up endpoint."""

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
