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

    def test_admin_no_topic_gets_approved(self):
        """Admin prompts without topic should also be approved."""
        policy = DefaultApprovalPolicy()
        status = policy.determine_initial_status(has_topic=False, user_is_admin=True)
        assert status == PromptApprovalStatus.APPROVED

    def test_user_with_topic_gets_pending(self):
        """User prompts with topic should be pending."""
        policy = DefaultApprovalPolicy()
        status = policy.determine_initial_status(has_topic=True, user_is_admin=False)
        assert status == PromptApprovalStatus.PENDING

    def test_user_no_topic_gets_pending(self):
        """User prompts without topic should be pending."""
        policy = DefaultApprovalPolicy()
        status = policy.determine_initial_status(has_topic=False, user_is_admin=False)
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

    @pytest_asyncio.fixture
    async def pending_prompt_no_topic(self, test_session):
        """Create a pending prompt without topic for testing."""
        prompt = Prompt(
            prompt_text="Test pending prompt no topic",
            embedding=[0.1] * 384,
            topic_id=None,
            user_id="test-user-id",
            approval_status=PromptApprovalStatus.PENDING,
        )
        test_session.add(prompt)
        await test_session.flush()
        return prompt

    @pytest.mark.asyncio
    async def test_get_pending_prompts_empty(self, service):
        """Should return empty list when no pending prompts."""
        prompts, total = await service.get_pending_prompts()
        # Filter out any existing pending prompts from seed data
        pending_user_prompts = [p for p in prompts if p.user_id is not None]
        assert len(pending_user_prompts) == 0

    @pytest.mark.asyncio
    async def test_approve_prompt_with_topic(self, service, pending_prompt):
        """Should approve a pending prompt that has a topic."""
        result = await service.approve_prompt(
            pending_prompt.id,
            reviewer_id="admin-user-id",
        )
        assert result.new_status == PromptApprovalStatus.APPROVED
        assert result.reviewed_by == "admin-user-id"

    @pytest.mark.asyncio
    async def test_approve_prompt_without_topic_requires_topic_id(
        self, service, pending_prompt_no_topic, test_session
    ):
        """Should require topic_id when approving prompt without topic."""
        from src.approval.exceptions import TopicRequiredError

        with pytest.raises(TopicRequiredError):
            await service.approve_prompt(
                pending_prompt_no_topic.id,
                reviewer_id="admin-user-id",
                topic_id=None,
            )

    @pytest.mark.asyncio
    async def test_approve_prompt_with_topic_assignment(
        self, service, pending_prompt_no_topic, test_session
    ):
        """Should assign topic when approving prompt without topic."""
        # Get a topic
        result = await test_session.execute(select(Topic).limit(1))
        topic = result.scalar_one()

        approval_result = await service.approve_prompt(
            pending_prompt_no_topic.id,
            reviewer_id="admin-user-id",
            topic_id=topic.id,
        )
        assert approval_result.new_status == PromptApprovalStatus.APPROVED

        # Verify topic was assigned
        await test_session.refresh(pending_prompt_no_topic)
        assert pending_prompt_no_topic.topic_id == topic.id

    @pytest.mark.asyncio
    async def test_reject_prompt(self, service, pending_prompt):
        """Should reject a pending prompt."""
        result = await service.reject_prompt(
            pending_prompt.id,
            reviewer_id="admin-user-id",
        )
        assert result.new_status == PromptApprovalStatus.REJECTED
        assert result.reviewed_by == "admin-user-id"

    @pytest.mark.asyncio
    async def test_cannot_approve_already_approved(self, service, test_session):
        """Should not allow approving an already approved prompt."""
        from src.approval.exceptions import PromptNotPendingError

        # Get any existing approved prompt from seed data
        result = await test_session.execute(
            select(Prompt).where(
                Prompt.approval_status == PromptApprovalStatus.APPROVED
            ).limit(1)
        )
        approved_prompt = result.scalar_one_or_none()
        if approved_prompt is None:
            pytest.skip("No approved prompts in seed data")

        with pytest.raises(PromptNotPendingError):
            await service.approve_prompt(
                approved_prompt.id,
                reviewer_id="admin-user-id",
            )


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

    def test_approve_prompt_requires_admin(self, client, auth_headers):
        """Regular users should not approve prompts."""
        response = client.post(
            "/admin/api/v1/prompts/1/approve",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_reject_prompt_requires_admin(self, client, auth_headers):
        """Regular users should not reject prompts."""
        response = client.post(
            "/admin/api/v1/prompts/1/reject",
            headers=auth_headers,
        )
        assert response.status_code == 403


class TestPromptGroupWithoutTopic:
    """Tests for creating groups without topic."""

    def test_create_group_without_topic(
        self, client, auth_headers, test_user
    ):
        """Should allow creating a group without topic binding."""
        response = client.post(
            "/prompt-groups/api/v1/groups",
            json={
                "title": "Group Without Topic",
                "brand": {
                    "name": "Test Brand",
                    "domain": "testbrand.com",
                    "variations": ["test brand", "testbrand"],
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Group Without Topic"
        assert data["topic_id"] is None
        assert data["topic_title"] is None

    def test_create_group_with_existing_topic(
        self, client, auth_headers, test_user
    ):
        """Should allow creating a group with existing topic."""
        response = client.post(
            "/prompt-groups/api/v1/groups",
            json={
                "title": "Group With Topic",
                "topic": {
                    "existing_topic_id": 1,
                },
                "brand": {
                    "name": "Test Brand",
                    "domain": "testbrand.com",
                    "variations": ["test brand", "testbrand"],
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Group With Topic"
        assert data["topic_id"] == 1
        assert data["topic_title"] is not None


class TestSearchFiltersUnapproved:
    """Tests that search filters out unapproved prompts."""

    @pytest.mark.asyncio
    async def test_find_similar_excludes_pending(self, test_session):
        """Pending prompts should not appear in search results."""
        from src.approval.policies import DefaultApprovalPolicy
        from src.embeddings.embeddings_service import get_embeddings_service
        from src.prompts.services.prompt_service import PromptService

        # Get a topic
        result = await test_session.execute(select(Topic).limit(1))
        topic = result.scalar_one()

        # Create embeddings service
        embeddings_service = get_embeddings_service()
        policy = DefaultApprovalPolicy()
        prompt_service = PromptService(test_session, embeddings_service, policy)

        # Add a pending prompt
        pending_prompt = await prompt_service.add_prompt(
            "This is a very unique pending test prompt for search",
            topic_id=topic.id,
            user_id="test-user",
            is_admin=False,  # Will be PENDING
        )
        assert pending_prompt.approval_status == PromptApprovalStatus.PENDING

        # Search should not find the pending prompt
        results = await prompt_service.find_similar(
            "very unique pending test prompt",
            limit=10,
            min_similarity=0.5,
        )

        found_ids = [r.id for r in results]
        assert pending_prompt.id not in found_ids

    @pytest.mark.asyncio
    async def test_get_by_topic_ids_excludes_pending(self, test_session):
        """Pending prompts should not appear in topic prompt lists."""
        from src.approval.policies import DefaultApprovalPolicy
        from src.embeddings.embeddings_service import get_embeddings_service
        from src.prompts.services.prompt_service import PromptService

        # Get a topic
        result = await test_session.execute(select(Topic).limit(1))
        topic = result.scalar_one()

        # Create service
        embeddings_service = get_embeddings_service()
        policy = DefaultApprovalPolicy()
        prompt_service = PromptService(test_session, embeddings_service, policy)

        # Add a pending prompt
        pending_prompt = await prompt_service.add_prompt(
            "Pending prompt for topic list test",
            topic_id=topic.id,
            user_id="test-user",
            is_admin=False,
        )

        # Get prompts by topic
        prompts = await prompt_service.get_by_topic_ids([topic.id])

        found_ids = [p.id for p in prompts]
        assert pending_prompt.id not in found_ids
