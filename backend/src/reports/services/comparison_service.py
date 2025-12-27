"""Service for comparing current data with previous reports."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    ConsumedEvaluation,
    EvaluationStatus,
    GroupReport,
    Prompt,
    PromptEvaluation,
    PromptGroupBinding,
)


class ComparisonService:
    """Service for comparing current data with previous reports."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_latest_report(
        self, group_id: int, user_id: str
    ) -> GroupReport | None:
        """Get the most recent report for a group."""
        query = (
            select(GroupReport)
            .where(
                GroupReport.group_id == group_id,
                GroupReport.user_id == user_id,
            )
            .order_by(GroupReport.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_prompt_ids_in_group(self, group_id: int) -> list[int]:
        """Get all prompt IDs in a group."""
        query = select(PromptGroupBinding.prompt_id).where(
            PromptGroupBinding.group_id == group_id
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def count_completed_evaluations(self, prompt_ids: list[int]) -> int:
        """Count completed evaluations for given prompts."""
        if not prompt_ids:
            return 0

        query = select(func.count(PromptEvaluation.id)).where(
            PromptEvaluation.prompt_id.in_(prompt_ids),
            PromptEvaluation.status == EvaluationStatus.COMPLETED,
        )
        result = await self._session.execute(query)
        return result.scalar() or 0

    async def get_evaluation_ids_for_prompts(self, prompt_ids: list[int]) -> list[int]:
        """Get all completed evaluation IDs for given prompts."""
        if not prompt_ids:
            return []

        query = select(PromptEvaluation.id).where(
            PromptEvaluation.prompt_id.in_(prompt_ids),
            PromptEvaluation.status == EvaluationStatus.COMPLETED,
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_consumed_evaluation_ids(
        self, user_id: str, evaluation_ids: list[int]
    ) -> set[int]:
        """Get which evaluations the user has already consumed."""
        if not evaluation_ids:
            return set()

        query = select(ConsumedEvaluation.evaluation_id).where(
            ConsumedEvaluation.user_id == user_id,
            ConsumedEvaluation.evaluation_id.in_(evaluation_ids),
        )
        result = await self._session.execute(query)
        return set(result.scalars().all())

    async def get_prompts_with_evaluations(
        self, prompt_ids: list[int]
    ) -> set[int]:
        """Get which prompts have at least one completed evaluation."""
        if not prompt_ids:
            return set()

        query = (
            select(PromptEvaluation.prompt_id)
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
            .distinct()
        )
        result = await self._session.execute(query)
        return set(result.scalars().all())

    async def get_fresh_evaluation_count(
        self,
        user_id: str,
        prompt_ids: list[int],
        since: datetime | None = None,
    ) -> int:
        """Count evaluations that are 'fresh' (not consumed by user).

        If since is provided, also includes re-evaluations after that date.
        """
        if not prompt_ids:
            return 0

        # Get all completed evaluation IDs for these prompts
        evaluation_ids = await self.get_evaluation_ids_for_prompts(prompt_ids)

        if not evaluation_ids:
            return 0

        # Get consumed ones
        consumed = await self.get_consumed_evaluation_ids(user_id, evaluation_ids)

        # Fresh = not consumed
        return len(evaluation_ids) - len(consumed)
