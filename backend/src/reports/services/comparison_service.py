"""Service for comparing current data with previous reports."""

from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.evals_models import (
    ConsumedEvaluation,
    EvaluationStatus,
    GroupReport,
    GroupReportItem,
    PromptEvaluation,
)
from src.database.models import PromptGroupBinding


class ComparisonService:
    """Service for comparing current data with previous reports.

    Uses dual session pattern:
    - prompts_session: for PromptGroupBinding (prompts_db)
    - evals_session: for GroupReport, PromptEvaluation, ConsumedEvaluation (evals_db)
    """

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
    ):
        self._prompts_session = prompts_session
        self._evals_session = evals_session

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
        result = await self._evals_session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_report_evaluation_ids(
        self, group_id: int, user_id: str
    ) -> set[int] | None:
        """Get evaluation IDs from user's latest report for the group.

        Returns None if no previous report exists.
        Returns set of evaluation_ids (excluding None values).
        """
        latest = await self.get_latest_report(group_id, user_id)
        if not latest:
            return None

        query = select(GroupReportItem.evaluation_id).where(
            GroupReportItem.report_id == latest.id,
            GroupReportItem.evaluation_id.isnot(None),
        )
        result = await self._evals_session.execute(query)
        return set(result.scalars().all())

    async def get_prompt_ids_in_group(self, group_id: int) -> list[int]:
        """Get all prompt IDs in a group."""
        query = select(PromptGroupBinding.prompt_id).where(
            PromptGroupBinding.group_id == group_id
        )
        result = await self._prompts_session.execute(query)
        return list(result.scalars().all())

    async def count_completed_evaluations(
        self,
        prompt_ids: list[int],
        *,
        country_id: int | None = None,
    ) -> int:
        """Count completed evaluations for given prompts.

        Args:
            prompt_ids: List of prompt IDs to check
            country_id: Optional country filter. If provided, only counts
                       evaluations for that country.
        """
        if not prompt_ids:
            return 0

        conditions = [
            PromptEvaluation.prompt_id.in_(prompt_ids),
            PromptEvaluation.status == EvaluationStatus.COMPLETED,
        ]
        if country_id is not None:
            conditions.append(PromptEvaluation.country_id == country_id)

        query = select(func.count(PromptEvaluation.id)).where(*conditions)
        result = await self._evals_session.execute(query)
        return result.scalar() or 0

    async def get_evaluation_ids_for_prompts(
        self,
        prompt_ids: list[int],
        *,
        country_id: int | None = None,
    ) -> list[int]:
        """Get all completed evaluation IDs for given prompts.

        Args:
            prompt_ids: List of prompt IDs to check
            country_id: Optional country filter. If provided, only returns
                       evaluations for that country.
        """
        if not prompt_ids:
            return []

        conditions = [
            PromptEvaluation.prompt_id.in_(prompt_ids),
            PromptEvaluation.status == EvaluationStatus.COMPLETED,
        ]
        if country_id is not None:
            conditions.append(PromptEvaluation.country_id == country_id)

        query = select(PromptEvaluation.id).where(*conditions)
        result = await self._evals_session.execute(query)
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
        result = await self._evals_session.execute(query)
        return set(result.scalars().all())

    async def get_prompts_with_evaluations(
        self,
        prompt_ids: list[int],
        *,
        country_id: int | None = None,
    ) -> set[int]:
        """Get which prompts have at least one completed evaluation.

        Args:
            prompt_ids: List of prompt IDs to check
            country_id: Optional country filter. If provided, only considers
                       evaluations for that country.
        """
        if not prompt_ids:
            return set()

        conditions = [
            PromptEvaluation.prompt_id.in_(prompt_ids),
            PromptEvaluation.status == EvaluationStatus.COMPLETED,
        ]
        if country_id is not None:
            conditions.append(PromptEvaluation.country_id == country_id)

        query = (
            select(PromptEvaluation.prompt_id)
            .where(*conditions)
            .distinct()
        )
        result = await self._evals_session.execute(query)
        return set(result.scalars().all())

    async def get_fresh_evaluation_count(
        self,
        user_id: str,
        prompt_ids: list[int],
        since: datetime | None = None,
        *,
        country_id: int | None = None,
    ) -> int:
        """Count evaluations that are 'fresh' (not consumed by user).

        If since is provided, also includes re-evaluations after that date.

        Args:
            user_id: User ID to check consumption for
            prompt_ids: List of prompt IDs to check
            since: Optional date filter (unused in current implementation)
            country_id: Optional country filter. If provided, only considers
                       evaluations for that country.
        """
        if not prompt_ids:
            return 0

        # Get all completed evaluation IDs for these prompts
        evaluation_ids = await self.get_evaluation_ids_for_prompts(
            prompt_ids, country_id=country_id
        )

        if not evaluation_ids:
            return 0

        # Get consumed ones
        consumed = await self.get_consumed_evaluation_ids(user_id, evaluation_ids)

        # Fresh = not consumed
        return len(evaluation_ids) - len(consumed)
