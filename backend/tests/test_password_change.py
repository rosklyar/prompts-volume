"""Tests for password change endpoint."""

import uuid


class TestUpdatePassword:
    """Tests for PATCH /api/v1/users/me/password endpoint."""

    def test_update_password_success(self, client, create_verified_user):
        """Test successful password change."""
        email = f"pwd-success-{uuid.uuid4()}@example.com"
        old_password = "oldpassword123"
        new_password = "newpassword456"

        auth_headers = create_verified_user(email=email, password=old_password)

        response = client.patch(
            "/api/v1/users/me/password",
            json={
                "current_password": old_password,
                "new_password": new_password,
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password updated successfully"

        # Verify can login with new password
        login_response = client.post(
            "/api/v1/login/access-token",
            data={"username": email, "password": new_password},
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

        # Verify old password no longer works
        old_login_response = client.post(
            "/api/v1/login/access-token",
            data={"username": email, "password": old_password},
        )
        assert old_login_response.status_code == 400

    def test_update_password_unauthenticated(self, client):
        """Test password change without authentication."""
        response = client.patch(
            "/api/v1/users/me/password",
            json={
                "current_password": "anypassword123",
                "new_password": "newpassword456",
            },
        )

        assert response.status_code == 401
