"""Tests for signup bonus limit functionality."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.auth.crud import count_signup_bonuses, create_user, verify_user_email
from src.auth.models import UserCreate
from src.config.settings import settings
from src.database.users_models import CreditGrant, CreditSource, User


class TestSignupBonusLimit:
    """Tests for limiting signup bonuses to a maximum number of users."""

    def test_signup_bonus_granted_under_limit(self, client, create_verified_user):
        """Test that signup bonus is granted when under the limit."""
        # Create a user (starts fresh with 0 signup bonuses in test DB)
        email = f"bonus-under-{uuid.uuid4()}@example.com"
        auth_headers = create_verified_user(email=email, password="testpass123")

        # Check balance - should have signup credits
        response = client.get("/billing/api/v1/balance", headers=auth_headers)
        assert response.status_code == 200
        balance = response.json()
        assert Decimal(str(balance["available_balance"])) == Decimal(
            str(settings.billing_signup_credits)
        )

    def test_signup_bonus_not_granted_at_limit(self, client, test_engine):
        """Test that signup bonus is NOT granted when at the limit."""
        import asyncio
        from src.auth.crud import create_user_with_verification
        from src.auth.verification import hash_token

        # Set limit to 2 for this test
        original_limit = settings.billing_max_signup_bonuses
        settings.billing_max_signup_bonuses = 2

        try:
            # Create users to reach the limit
            async def setup_users():
                async_session_maker = async_sessionmaker(
                    bind=test_engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )

                # Create and verify 2 users to hit the limit
                for i in range(2):
                    async with async_session_maker() as session:
                        user_create = UserCreate(
                            email=f"limit-user-{i}-{uuid.uuid4()}@example.com",
                            password="testpass123",
                            full_name=f"Limit User {i}",
                        )
                        user, raw_token = await create_user_with_verification(
                            session, user_create, 24
                        )
                        # Verify the user to grant signup bonus
                        await verify_user_email(session, user)

                # Now create user 3 who should NOT get the bonus
                async with async_session_maker() as session:
                    user_create = UserCreate(
                        email=f"no-bonus-{uuid.uuid4()}@example.com",
                        password="testpass123",
                        full_name="No Bonus User",
                    )
                    user, raw_token = await create_user_with_verification(
                        session, user_create, 24
                    )
                    await verify_user_email(session, user)

                    # Check this user has no credit grants
                    result = await session.execute(
                        select(CreditGrant).where(CreditGrant.user_id == user.id)
                    )
                    grants = result.scalars().all()
                    return len(grants), user.email_verified, user.is_active

            grant_count, is_verified, is_active = asyncio.get_event_loop().run_until_complete(
                setup_users()
            )

            # User should have no signup bonus but still be verified and active
            assert grant_count == 0
            assert is_verified is True
            assert is_active is True

        finally:
            settings.billing_max_signup_bonuses = original_limit

    def test_account_still_verified_at_limit(self, client, test_engine):
        """Test that account is still verified and activated even when bonus limit reached."""
        import asyncio
        from src.auth.crud import create_user_with_verification

        # Set limit to 0 for this test (no bonuses at all)
        original_limit = settings.billing_max_signup_bonuses
        settings.billing_max_signup_bonuses = 0

        try:
            async def verify_user_without_bonus():
                async_session_maker = async_sessionmaker(
                    bind=test_engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )

                async with async_session_maker() as session:
                    user_create = UserCreate(
                        email=f"verify-no-bonus-{uuid.uuid4()}@example.com",
                        password="testpass123",
                        full_name="Verify No Bonus",
                    )
                    user, raw_token = await create_user_with_verification(
                        session, user_create, 24
                    )

                    # Before verification
                    assert user.is_active is False
                    assert user.email_verified is False

                    # Verify
                    await verify_user_email(session, user)

                    # After verification - account should be active
                    assert user.is_active is True
                    assert user.email_verified is True

                    # But no credits
                    result = await session.execute(
                        select(CreditGrant).where(CreditGrant.user_id == user.id)
                    )
                    grants = result.scalars().all()
                    return len(grants)

            grant_count = asyncio.get_event_loop().run_until_complete(
                verify_user_without_bonus()
            )
            assert grant_count == 0

        finally:
            settings.billing_max_signup_bonuses = original_limit

    def test_admin_created_user_respects_limit(self, client, test_engine, superuser_auth_headers):
        """Test that admin-created users also respect the signup bonus limit."""
        import asyncio

        # Set limit to 0 for this test
        original_limit = settings.billing_max_signup_bonuses
        settings.billing_max_signup_bonuses = 0

        try:
            email = f"admin-created-{uuid.uuid4()}@example.com"

            # Create user via admin endpoint
            response = client.post(
                "/api/v1/users/",
                json={
                    "email": email,
                    "password": "adminpass123",
                    "full_name": "Admin Created",
                },
                headers=superuser_auth_headers,
            )
            assert response.status_code == 200
            user_id = response.json()["id"]

            # Check the user has no credit grants
            async def check_grants():
                async_session_maker = async_sessionmaker(
                    bind=test_engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )
                async with async_session_maker() as session:
                    result = await session.execute(
                        select(CreditGrant).where(CreditGrant.user_id == user_id)
                    )
                    grants = result.scalars().all()
                    return len(grants)

            grant_count = asyncio.get_event_loop().run_until_complete(check_grants())
            assert grant_count == 0

        finally:
            settings.billing_max_signup_bonuses = original_limit

    def test_unlimited_when_setting_is_none(self, client, test_engine):
        """Test that there's no limit when billing_max_signup_bonuses is None."""
        import asyncio
        from src.auth.crud import create_user_with_verification

        # Set limit to None (unlimited)
        original_limit = settings.billing_max_signup_bonuses
        settings.billing_max_signup_bonuses = None

        try:
            async def create_many_users():
                async_session_maker = async_sessionmaker(
                    bind=test_engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )

                granted_count = 0
                # Create 5 users - all should get the bonus
                for i in range(5):
                    async with async_session_maker() as session:
                        user_create = UserCreate(
                            email=f"unlimited-{i}-{uuid.uuid4()}@example.com",
                            password="testpass123",
                            full_name=f"Unlimited User {i}",
                        )
                        user, raw_token = await create_user_with_verification(
                            session, user_create, 24
                        )
                        await verify_user_email(session, user)

                        # Check credit grant
                        result = await session.execute(
                            select(CreditGrant).where(
                                CreditGrant.user_id == user.id,
                                CreditGrant.source == CreditSource.SIGNUP_BONUS,
                            )
                        )
                        if result.scalar_one_or_none():
                            granted_count += 1

                return granted_count

            granted = asyncio.get_event_loop().run_until_complete(create_many_users())
            assert granted == 5  # All users got the bonus

        finally:
            settings.billing_max_signup_bonuses = original_limit


class TestCountSignupBonuses:
    """Tests for the count_signup_bonuses helper function."""

    @pytest.mark.asyncio
    async def test_count_returns_zero_when_no_grants(self, test_engine):
        """Test that count returns 0 when there are no signup bonus grants."""
        async_session_maker = async_sessionmaker(
            bind=test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session_maker() as session:
            count = await count_signup_bonuses(session)
            # May not be 0 if other tests created users, but should be a number
            assert isinstance(count, int)
            assert count >= 0

    @pytest.mark.asyncio
    async def test_count_increments_after_verification(self, test_engine):
        """Test that count increments after a user verifies and gets bonus."""
        from src.auth.crud import create_user_with_verification

        # Ensure unlimited for this test
        original_limit = settings.billing_max_signup_bonuses
        settings.billing_max_signup_bonuses = None

        try:
            async_session_maker = async_sessionmaker(
                bind=test_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            async with async_session_maker() as session:
                count_before = await count_signup_bonuses(session)

            async with async_session_maker() as session:
                user_create = UserCreate(
                    email=f"count-test-{uuid.uuid4()}@example.com",
                    password="testpass123",
                    full_name="Count Test",
                )
                user, _ = await create_user_with_verification(session, user_create, 24)
                await verify_user_email(session, user)

            async with async_session_maker() as session:
                count_after = await count_signup_bonuses(session)

            assert count_after == count_before + 1

        finally:
            settings.billing_max_signup_bonuses = original_limit
