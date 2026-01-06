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

    def test_update_password_wrong_current(self, client, create_verified_user):
        """Test password change with incorrect current password."""
        email = f"pwd-wrong-{uuid.uuid4()}@example.com"
        auth_headers = create_verified_user(email=email, password="correctpassword123")

        response = client.patch(
            "/api/v1/users/me/password",
            json={
                "current_password": "wrongpassword123",
                "new_password": "newpassword456",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Incorrect password"

    def test_update_password_same_as_current(self, client, create_verified_user):
        """Test password change when new password is same as current."""
        email = f"pwd-same-{uuid.uuid4()}@example.com"
        same_password = "samepassword123"
        auth_headers = create_verified_user(email=email, password=same_password)

        response = client.patch(
            "/api/v1/users/me/password",
            json={
                "current_password": same_password,
                "new_password": same_password,
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "New password cannot be the same as the current one"

    def test_update_password_too_short(self, client, create_verified_user):
        """Test password change with new password that is too short."""
        email = f"pwd-short-{uuid.uuid4()}@example.com"
        auth_headers = create_verified_user(email=email, password="validpassword123")

        response = client.patch(
            "/api/v1/users/me/password",
            json={
                "current_password": "validpassword123",
                "new_password": "short",  # Less than 8 characters
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

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
