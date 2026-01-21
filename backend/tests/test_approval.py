"""Tests for prompt approval workflow."""

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.approval.policies import DefaultApprovalPolicy
from src.approval.service import PromptApprovalService
from src.database import Prompt, PromptApprovalStatus, PromptGroup, Topic


class TestDefaultApprovalPolicy:
    """Tests for DefaultApprovalPolicy."""

    def test_admin_gets_approved(self):
        """Admin-created prompts should be approved automatically."""
        policy = DefaultApprovalPolicy()
        status = policy.determine_initial_status(has_topic=True, user_is_admin=True)
        assert status == PromptApprovalStatus.APPROVED

    def test_user_with_topic_gets_pending(self):
        """User prompts with topic should be pending."""
        policy = DefaultApprovalPolicy()
        status = policy.determine_initial_status(has_topic=True, user_is_admin=False)
        assert status == PromptApprovalStatus.PENDING


class TestApprovalServiceUnit:
    """Unit tests for PromptApprovalService."""

    @pytest_asyncio.fixture
    async def service(self, test_session):
        """Create approval service with test session."""
        return PromptApprovalService(test_session)

    @pytest_asyncio.fixture
    async def pending_prompt(self, test_session):
        """Create a pending prompt for testing."""
        # Get a topic for the prompt
        result = await test_session.execute(select(Topic).limit(1))
        topic = result.scalar_one()

        prompt = Prompt(
            prompt_text="Test pending prompt",
            embedding=[0.1] * 384,
            topic_id=topic.id,
            user_id="test-user-id",
            approval_status=PromptApprovalStatus.PENDING,
        )
        test_session.add(prompt)
        await test_session.flush()
        return prompt

    @pytest.mark.asyncio
    async def test_approve_prompt_with_topic(self, service, pending_prompt):
        """Should approve a pending prompt that has a topic."""
        result = await service.approve_prompt(
            pending_prompt.id,
            reviewer_id="admin-user-id",
        )
        assert result.new_status == PromptApprovalStatus.APPROVED
        assert result.reviewed_by == "admin-user-id"


class TestApprovalEndpoints:
    """Integration tests for admin approval endpoints."""

    def test_get_pending_prompts_requires_admin(self, client, auth_headers):
        """Regular users should not access pending prompts."""
        response = client.get(
            "/admin/api/v1/prompts/pending",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_get_pending_prompts_as_admin(self, client, superuser_auth_headers):
        """Admin should be able to get pending prompts."""
        response = client.get(
            "/admin/api/v1/prompts/pending",
            headers=superuser_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data
        assert "total" in data
