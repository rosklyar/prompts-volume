"""Tests for admin user hard-delete endpoint."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.auth.crud import create_user
from src.auth.models import UserCreate
from src.database import Prompt, PromptApprovalStatus, PromptGroup, Topic
from src.database.evals_models import ConsumedEvaluation, GroupReport
from src.database.users_models import (
    BalanceTransaction,
    CreditGrant,
    CreditSource,
    TransactionType,
    User,
    UserPreferences,
)


class TestHardDeleteUserEndpoint:
    """Integration tests for DELETE /admin/api/v1/users/{user_id}/hard-delete."""

    def test_requires_superuser(self, client, auth_headers):
        """Regular users should not access this endpoint."""
        response = client.delete(
            f"/admin/api/v1/users/{uuid.uuid4()}/hard-delete",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_user_not_found(self, client, superuser_auth_headers):
        """Should return 404 for non-existent user."""
        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/admin/api/v1/users/{fake_id}/hard-delete",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found"

    def test_cannot_delete_superuser(self, client, superuser_auth_headers, test_engine):
        """Should prevent deleting superuser accounts."""
        import asyncio

        # Create another superuser to try to delete
        async def create_another_superuser():
            async_session_maker = async_sessionmaker(
                bind=test_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            async with async_session_maker() as session:
                user = await create_user(
                    session,
                    UserCreate(
                        email=f"superuser-{uuid.uuid4()}@example.com",
                        password="password123",
                        full_name="Another Superuser",
                        is_active=True,
                        is_superuser=True,
                    ),
                )
                return user.id

        target_id = asyncio.get_event_loop().run_until_complete(create_another_superuser())

        response = client.delete(
            f"/admin/api/v1/users/{target_id}/hard-delete",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Cannot delete superuser accounts"

    def test_cannot_delete_self(self, client, superuser_auth_headers, test_superuser):
        """Should prevent admins from deleting themselves."""
        response = client.delete(
            f"/admin/api/v1/users/{test_superuser.id}/hard-delete",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Cannot delete your own account"

    def test_hard_delete_user_with_data(self, client, superuser_auth_headers, test_engine):
        """Should delete user and all associated data across databases."""
        import asyncio
        from decimal import Decimal

        # Create a target user with data across all databases
        async def setup_user_with_data() -> str:
            async_session_maker = async_sessionmaker(
                bind=test_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            async with async_session_maker() as session:
                # Create user
                user = await create_user(
                    session,
                    UserCreate(
                        email=f"delete-me-{uuid.uuid4()}@example.com",
                        password="password123",
                        full_name="Delete Me",
                        is_active=True,
                        is_superuser=False,
                    ),
                )
                user_id = user.id

                # Add users_db data
                session.add(UserPreferences(user_id=user_id))
                session.add(CreditGrant(
                    user_id=user_id,
                    source=CreditSource.SIGNUP_BONUS,
                    original_amount=Decimal("5.0"),
                    remaining_amount=Decimal("5.0"),
                ))
                session.add(BalanceTransaction(
                    user_id=user_id,
                    transaction_type=TransactionType.CREDIT,
                    amount=Decimal("5.0"),
                    balance_after=Decimal("5.0"),
                    reason="Signup bonus",
                ))

                # Get a topic and country for prompts_db data
                topic_result = await session.execute(select(Topic).limit(1))
                topic = topic_result.scalar_one()

                # Add a prompt group
                group = PromptGroup(
                    user_id=user_id,
                    title="Test Group",
                    country_id=topic.country_id,
                    brand={"name": "Test", "domain": "test.com", "variations": []},
                )
                session.add(group)
                await session.flush()

                # Add prompts - one pending, one approved
                # Use unique prompt texts to avoid constraint violations
                unique_suffix = str(uuid.uuid4())[:8]
                pending_text = f"Pending prompt {unique_suffix}"
                approved_text = f"Approved prompt {unique_suffix}"

                pending_prompt = Prompt(
                    prompt_text=pending_text,
                    embedding=[0.1] * 384,
                    topic_id=topic.id,
                    user_id=user_id,
                    approval_status=PromptApprovalStatus.PENDING,
                )
                approved_prompt = Prompt(
                    prompt_text=approved_text,
                    embedding=[0.2] * 384,
                    topic_id=topic.id,
                    user_id=user_id,
                    approval_status=PromptApprovalStatus.APPROVED,
                )
                session.add(pending_prompt)
                session.add(approved_prompt)
                await session.commit()

                return user_id, pending_text, approved_text

        user_id, pending_text, approved_text = asyncio.get_event_loop().run_until_complete(
            setup_user_with_data()
        )

        # Delete the user
        response = client.delete(
            f"/admin/api/v1/users/{user_id}/hard-delete",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["user_id"] == user_id
        assert "user_email" in data
        assert data["total_records_deleted"] > 0
        assert len(data["details"]) == 3

        # Verify evals_db detail
        evals_detail = next(d for d in data["details"] if d["database"] == "evals_db")
        assert "deleted" in evals_detail
        assert "orphaned" in evals_detail

        # Verify prompts_db detail has expected keys
        prompts_detail = next(d for d in data["details"] if d["database"] == "prompts_db")
        assert "prompt_groups" in prompts_detail["deleted"]
        assert "prompts" in prompts_detail["deleted"]
        assert "prompts" in prompts_detail["orphaned"]

        # Verify users_db detail
        users_detail = next(d for d in data["details"] if d["database"] == "users_db")
        assert users_detail["deleted"]["users"] == 1

        # Verify user is actually deleted
        async def verify_deletion():
            async_session_maker = async_sessionmaker(
                bind=test_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            async with async_session_maker() as session:
                # User should not exist
                user = await session.get(User, user_id)
                assert user is None

                # Approved prompt should exist with NULL user_id
                result = await session.execute(
                    select(Prompt).where(
                        Prompt.prompt_text == approved_text,
                        Prompt.user_id.is_(None),
                    )
                )
                orphaned_prompt = result.scalar_one_or_none()
                assert orphaned_prompt is not None

                # Pending prompt should be deleted
                result = await session.execute(
                    select(Prompt).where(Prompt.prompt_text == pending_text)
                )
                deleted_prompt = result.scalar_one_or_none()
                assert deleted_prompt is None

        asyncio.get_event_loop().run_until_complete(verify_deletion())
