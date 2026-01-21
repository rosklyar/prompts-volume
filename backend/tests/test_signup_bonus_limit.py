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
