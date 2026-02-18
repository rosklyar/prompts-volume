"""Tests for admin impersonation and onboarding notification endpoints."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.database.users_models import User, UserPreferences
from src.auth.security import get_password_hash


class TestImpersonateEndpoint:
    """Tests for POST /admin/api/v1/impersonate/{user_id}."""

    def test_requires_superuser(self, client, auth_headers):
        """Regular users should not access this endpoint."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/admin/api/v1/impersonate/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_user_not_found(self, client, superuser_auth_headers):
        """Should return 404 for non-existent user."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/admin/api/v1/impersonate/{fake_id}",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 404

    def test_cannot_impersonate_self(self, client, superuser_auth_headers, test_superuser):
        """Should return 400 when trying to impersonate self."""
        response = client.post(
            f"/admin/api/v1/impersonate/{test_superuser.id}",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()

    def test_cannot_impersonate_superuser(self, client, superuser_auth_headers, test_engine):
        """Should return 403 when trying to impersonate another superuser."""
        async def create_other_superuser() -> str:
            sm = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
            async with sm() as session:
                user = User(
                    id=str(uuid.uuid4()),
                    email=f"other-admin-{uuid.uuid4().hex[:6]}@test.com",
                    hashed_password=get_password_hash("testpass123"),
                    is_superuser=True,
                    is_active=True,
                    email_verified=True,
                )
                session.add(user)
                await session.commit()
                return user.id

        other_id = asyncio.get_event_loop().run_until_complete(create_other_superuser())
        response = client.post(
            f"/admin/api/v1/impersonate/{other_id}",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 403
        assert "superuser" in response.json()["detail"].lower()

    def test_impersonate_success(self, client, superuser_auth_headers, test_user):
        """Happy path: should return a valid impersonation token."""
        response = client.post(
            f"/admin/api/v1/impersonate/{test_user.id}",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Token should authenticate as the target user
        me_response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["id"] == test_user.id


class TestOnboardingNotificationsEndpoint:
    """Tests for onboarding notification endpoints."""

    def test_requires_superuser(self, client, auth_headers):
        """Regular users should not access onboarding notifications."""
        response = client.get(
            "/admin/api/v1/onboarding-notifications",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_empty_list(self, client, superuser_auth_headers):
        """Should return empty list when no users have completed onboarding."""
        response = client.get(
            "/admin/api/v1/onboarding-notifications",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["users"] == []
        assert data["total"] == 0

    def test_count_endpoint(self, client, superuser_auth_headers):
        """Count endpoint should return 0 when no pending onboarding."""
        response = client.get(
            "/admin/api/v1/onboarding-notifications/count",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["count"] == 0

    def test_shows_onboarded_user(self, client, superuser_auth_headers, test_user, test_engine):
        """Should list a user who completed onboarding but hasn't been set up."""
        async def create_onboarded_prefs():
            sm = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
            async with sm() as session:
                prefs = UserPreferences(
                    user_id=test_user.id,
                    onboarding_completed_at=datetime.now(timezone.utc),
                    default_brand={"name": "TestBrand", "domain": "test.com", "variations": []},
                )
                session.add(prefs)
                await session.commit()

        asyncio.get_event_loop().run_until_complete(create_onboarded_prefs())

        response = client.get(
            "/admin/api/v1/onboarding-notifications",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        user_ids = [u["user_id"] for u in data["users"]]
        assert test_user.id in user_ids

        # Count should also reflect
        count_response = client.get(
            "/admin/api/v1/onboarding-notifications/count",
            headers=superuser_auth_headers,
        )
        assert count_response.json()["count"] >= 1


class TestMarkSetupEndpoint:
    """Tests for POST /admin/api/v1/users/{user_id}/mark-setup."""

    def test_requires_superuser(self, client, auth_headers):
        """Regular users should not access this endpoint."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/admin/api/v1/users/{fake_id}/mark-setup",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_user_prefs_not_found(self, client, superuser_auth_headers):
        """Should return 404 when user preferences don't exist."""
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/admin/api/v1/users/{fake_id}/mark-setup",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 404

    def test_mark_setup_success(self, client, superuser_auth_headers, test_user, test_engine):
        """Happy path: marking onboarded user as set up."""
        async def create_onboarded_prefs():
            sm = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
            async with sm() as session:
                prefs = UserPreferences(
                    user_id=test_user.id,
                    onboarding_completed_at=datetime.now(timezone.utc),
                )
                session.add(prefs)
                await session.commit()

        asyncio.get_event_loop().run_until_complete(create_onboarded_prefs())

        response = client.post(
            f"/admin/api/v1/users/{test_user.id}/mark-setup",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200

        # User should no longer appear in onboarding notifications
        notif_response = client.get(
            "/admin/api/v1/onboarding-notifications/count",
            headers=superuser_auth_headers,
        )
        assert notif_response.json()["count"] == 0
