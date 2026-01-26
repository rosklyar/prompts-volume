"""Repository for evaluation queries shared across services."""

from datetime import datetime, timedelta, timezone
from enum import Enum

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.evals_models import EvaluationStatus, PromptEvaluation


class LatestStrategy(Enum):
    """Strategy for determining latest evaluation."""

    BY_ID = "by_id"  # max(id) - used by batch_report_generator
    BY_COMPLETED_AT = "by_completed_at"  # max(completed_at) - used by prompt_aggregator


class EvaluationQueryRepository:
    """Shared repository for evaluation queries.

    Consolidates duplicated evaluation query logic from:
    - BatchReportGenerator._get_latest_evaluations (uses BY_ID)
    - PromptAggregatorService._get_latest_evaluations (uses BY_COMPLETED_AT)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest_evaluation_ids(
        self,
        prompt_ids: list[int],
        *,
        assistant_id: int = 1,
        strategy: LatestStrategy = LatestStrategy.BY_ID,
    ) -> dict[int, int]:
        """Get latest completed evaluation ID for each prompt.

        Args:
            prompt_ids: List of prompt IDs to look up
            assistant_id: AI assistant ID to filter evaluations
            strategy: How to determine "latest" (BY_ID or BY_COMPLETED_AT)

        Returns:
            Dict mapping prompt_id -> evaluation_id.
        """
        if not prompt_ids:
            return {}

        if strategy == LatestStrategy.BY_ID:
            return await self._get_latest_by_id(prompt_ids, assistant_id)
        else:
            return await self._get_latest_by_completed_at(prompt_ids, assistant_id)

    async def get_latest_evaluations_with_timestamp(
        self,
        prompt_ids: list[int],
        *,
        assistant_id: int = 1,
    ) -> dict[int, dict]:
        """Get latest evaluation with completed_at for each prompt.

        Args:
            prompt_ids: List of prompt IDs to look up
            assistant_id: AI assistant ID to filter evaluations

        Returns:
            Dict mapping prompt_id -> {id, completed_at}.
            Used by prompt_aggregator for freshness calculation.
        """
        if not prompt_ids:
            return {}

        subq = (
            select(
                PromptEvaluation.prompt_id,
                func.max(PromptEvaluation.completed_at).label("max_completed"),
            )
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
                PromptEvaluation.assistant_id == assistant_id,
            )
            .group_by(PromptEvaluation.prompt_id)
            .subquery()
        )

        query = (
            select(
                PromptEvaluation.prompt_id,
                PromptEvaluation.id,
                PromptEvaluation.completed_at,
            )
            .join(
                subq,
                (PromptEvaluation.prompt_id == subq.c.prompt_id)
                & (PromptEvaluation.completed_at == subq.c.max_completed),
            )
            .where(PromptEvaluation.assistant_id == assistant_id)
        )

        result = await self._session.execute(query)
        return {row[0]: {"id": row[1], "completed_at": row[2]} for row in result.all()}

    async def _get_latest_by_id(
        self, prompt_ids: list[int], assistant_id: int
    ) -> dict[int, int]:
        """Get latest evaluation by max(id)."""
        subq = (
            select(
                PromptEvaluation.prompt_id,
                func.max(PromptEvaluation.id).label("max_id"),
            )
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
                PromptEvaluation.assistant_id == assistant_id,
            )
            .group_by(PromptEvaluation.prompt_id)
            .subquery()
        )

        query = (
            select(PromptEvaluation.prompt_id, PromptEvaluation.id)
            .join(
                subq,
                (PromptEvaluation.prompt_id == subq.c.prompt_id)
                & (PromptEvaluation.id == subq.c.max_id),
            )
            .where(PromptEvaluation.assistant_id == assistant_id)
        )

        result = await self._session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def _get_latest_by_completed_at(
        self, prompt_ids: list[int], assistant_id: int
    ) -> dict[int, int]:
        """Get latest evaluation by max(completed_at)."""
        evals = await self.get_latest_evaluations_with_timestamp(
            prompt_ids, assistant_id=assistant_id
        )
        return {pid: info["id"] for pid, info in evals.items()}

    async def get_latest_evaluation_ids_within_window(
        self,
        prompt_ids: list[int],
        *,
        assistant_id: int = 1,
        window_hours: int = 24,
    ) -> dict[int, int]:
        """Get latest completed evaluation ID for each prompt within a time window.

        This is used at report generation time to find the most recent evaluation
        within the freshness window (e.g., 24 hours).

        Args:
            prompt_ids: List of prompt IDs to look up
            assistant_id: AI assistant ID to filter evaluations
            window_hours: Look back window in hours (default: 24)

        Returns:
            Dict mapping prompt_id -> evaluation_id for prompts with recent evaluations.
        """
        if not prompt_ids:
            return {}

        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Subquery to get max completed_at within window for each prompt
        subq = (
            select(
                PromptEvaluation.prompt_id,
                func.max(PromptEvaluation.completed_at).label("max_completed"),
            )
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
                PromptEvaluation.assistant_id == assistant_id,
                PromptEvaluation.completed_at >= cutoff,
            )
            .group_by(PromptEvaluation.prompt_id)
            .subquery()
        )

        # Join to get the actual evaluation IDs
        query = (
            select(PromptEvaluation.prompt_id, PromptEvaluation.id)
            .join(
                subq,
                (PromptEvaluation.prompt_id == subq.c.prompt_id)
                & (PromptEvaluation.completed_at == subq.c.max_completed),
            )
            .where(PromptEvaluation.assistant_id == assistant_id)
        )

        result = await self._session.execute(query)
        return {row[0]: row[1] for row in result.all()}
