"""Service for managing prompt approval workflow."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, List, Optional, Tuple

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.approval.exceptions import (
    PromptNotFoundError,
    PromptNotPendingError,
    TopicNotFoundError,
    TopicRequiredError,
)
from src.database import (
    Prompt,
    PromptApprovalStatus,
    PromptGroup,
    PromptGroupBinding,
    Topic,
    get_async_session,
)


@dataclass
class PendingPromptInfo:
    """Information about a pending prompt for admin review."""

    id: int
    prompt_text: str
    topic_id: Optional[int]
    topic_title: Optional[str]
    user_id: Optional[str]
    group_ids: List[int]
    group_titles: List[str]


@dataclass
class ApprovalResult:
    """Result of an approval/rejection action."""

    prompt_id: int
    new_status: PromptApprovalStatus
    reviewed_by: str
    reviewed_at: datetime


class PromptApprovalService:
    """Service for managing prompt approval workflow."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_pending_prompts(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        topic_id: Optional[int] = None,
    ) -> Tuple[List[PendingPromptInfo], int]:
        """Get prompts awaiting approval with pagination.

        Args:
            limit: Max prompts to return
            offset: Number of prompts to skip
            topic_id: Optional filter by topic

        Returns:
            Tuple of (prompts, total_count)
        """
        # Base query for pending prompts
        base_query = select(Prompt).where(
            Prompt.approval_status == PromptApprovalStatus.PENDING
        )

        if topic_id is not None:
            base_query = base_query.where(Prompt.topic_id == topic_id)

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self._session.execute(count_query)
        total = total_result.scalar() or 0

        # Get prompts with topic info
        prompts_query = (
            base_query.options(selectinload(Prompt.topic))
            .order_by(Prompt.id)
            .limit(limit)
            .offset(offset)
        )
        prompts_result = await self._session.execute(prompts_query)
        prompts = list(prompts_result.scalars().all())

        # Get group info for each prompt
        if prompts:
            prompt_ids = [p.id for p in prompts]
            bindings_query = (
                select(PromptGroupBinding)
                .options(selectinload(PromptGroupBinding.group))
                .where(PromptGroupBinding.prompt_id.in_(prompt_ids))
            )
            bindings_result = await self._session.execute(bindings_query)
            bindings = list(bindings_result.scalars().all())

            # Group bindings by prompt_id
            prompt_groups: dict[int, list[PromptGroup]] = {}
            for binding in bindings:
                if binding.prompt_id not in prompt_groups:
                    prompt_groups[binding.prompt_id] = []
                prompt_groups[binding.prompt_id].append(binding.group)
        else:
            prompt_groups = {}

        # Build result
        result = []
        for prompt in prompts:
            groups = prompt_groups.get(prompt.id, [])
            result.append(
                PendingPromptInfo(
                    id=prompt.id,
                    prompt_text=prompt.prompt_text,
                    topic_id=prompt.topic_id,
                    topic_title=prompt.topic.title if prompt.topic else None,
                    user_id=prompt.user_id,
                    group_ids=[g.id for g in groups],
                    group_titles=[g.title for g in groups],
                )
            )

        return result, total

    async def approve_prompt(
        self,
        prompt_id: int,
        *,
        reviewer_id: str,
        topic_id: Optional[int] = None,
    ) -> ApprovalResult:
        """Approve a pending prompt.

        Args:
            prompt_id: ID of prompt to approve
            reviewer_id: ID of admin approving
            topic_id: Topic to assign if prompt has none

        Returns:
            ApprovalResult with new status

        Raises:
            PromptNotFoundError: Prompt doesn't exist
            PromptNotPendingError: Prompt is not in pending status
            TopicRequiredError: Prompt has no topic and topic_id not provided
            TopicNotFoundError: Provided topic_id doesn't exist
        """
        prompt = await self._get_prompt_or_raise(prompt_id)

        if prompt.approval_status != PromptApprovalStatus.PENDING:
            raise PromptNotPendingError(prompt_id, prompt.approval_status.value)

        # Handle topic assignment
        if prompt.topic_id is None:
            if topic_id is None:
                raise TopicRequiredError(prompt_id)
            await self._validate_topic_exists(topic_id)
            prompt.topic_id = topic_id
        elif topic_id is not None and topic_id != prompt.topic_id:
            # Allow changing topic during approval
            await self._validate_topic_exists(topic_id)
            prompt.topic_id = topic_id

        now = datetime.now(timezone.utc)
        prompt.approval_status = PromptApprovalStatus.APPROVED
        prompt.reviewed_at = now
        prompt.reviewed_by = reviewer_id

        await self._session.flush()

        return ApprovalResult(
            prompt_id=prompt.id,
            new_status=prompt.approval_status,
            reviewed_by=reviewer_id,
            reviewed_at=now,
        )

    async def reject_prompt(
        self,
        prompt_id: int,
        *,
        reviewer_id: str,
    ) -> ApprovalResult:
        """Reject a pending prompt.

        Args:
            prompt_id: ID of prompt to reject
            reviewer_id: ID of admin rejecting

        Returns:
            ApprovalResult with new status

        Raises:
            PromptNotFoundError: Prompt doesn't exist
            PromptNotPendingError: Prompt is not in pending status
        """
        prompt = await self._get_prompt_or_raise(prompt_id)

        if prompt.approval_status != PromptApprovalStatus.PENDING:
            raise PromptNotPendingError(prompt_id, prompt.approval_status.value)

        now = datetime.now(timezone.utc)
        prompt.approval_status = PromptApprovalStatus.REJECTED
        prompt.reviewed_at = now
        prompt.reviewed_by = reviewer_id

        await self._session.flush()

        return ApprovalResult(
            prompt_id=prompt.id,
            new_status=prompt.approval_status,
            reviewed_by=reviewer_id,
            reviewed_at=now,
        )

    async def batch_approve(
        self,
        prompt_ids: List[int],
        *,
        reviewer_id: str,
        topic_id: Optional[int] = None,
    ) -> Tuple[List[ApprovalResult], List[int]]:
        """Approve multiple prompts at once.

        Args:
            prompt_ids: IDs of prompts to approve
            reviewer_id: ID of admin approving
            topic_id: Topic to assign to prompts without topic

        Returns:
            Tuple of (successful results, failed prompt IDs)
        """
        results: List[ApprovalResult] = []
        failed_ids: List[int] = []

        for pid in prompt_ids:
            try:
                result = await self.approve_prompt(
                    pid, reviewer_id=reviewer_id, topic_id=topic_id
                )
                results.append(result)
            except Exception:
                failed_ids.append(pid)

        return results, failed_ids

    async def batch_reject(
        self,
        prompt_ids: List[int],
        *,
        reviewer_id: str,
    ) -> Tuple[List[ApprovalResult], List[int]]:
        """Reject multiple prompts at once.

        Args:
            prompt_ids: IDs of prompts to reject
            reviewer_id: ID of admin rejecting

        Returns:
            Tuple of (successful results, failed prompt IDs)
        """
        results: List[ApprovalResult] = []
        failed_ids: List[int] = []

        for pid in prompt_ids:
            try:
                result = await self.reject_prompt(pid, reviewer_id=reviewer_id)
                results.append(result)
            except Exception:
                failed_ids.append(pid)

        return results, failed_ids

    async def _get_prompt_or_raise(self, prompt_id: int) -> Prompt:
        """Get prompt by ID or raise PromptNotFoundError."""
        prompt = await self._session.get(Prompt, prompt_id)
        if prompt is None:
            raise PromptNotFoundError(prompt_id)
        return prompt

    async def _validate_topic_exists(self, topic_id: int) -> None:
        """Validate that topic exists or raise TopicNotFoundError."""
        topic = await self._session.get(Topic, topic_id)
        if topic is None:
            raise TopicNotFoundError(topic_id)


def get_prompt_approval_service(
    session: AsyncSession = Depends(get_async_session),
) -> PromptApprovalService:
    """Dependency injection for PromptApprovalService."""
    return PromptApprovalService(session)


PromptApprovalServiceDep = Annotated[
    PromptApprovalService, Depends(get_prompt_approval_service)
]
