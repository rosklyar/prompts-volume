"""Service for analyzing per-prompt freshness compared to last report."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.evals_models import (
    EvaluationStatus,
    GroupReport,
    GroupReportItem,
    PromptEvaluation,
)
from src.database.models import Prompt, PromptGroupBinding
from src.reports.models.api_models import PromptFreshnessInfo


class FreshnessAnalyzerService:
    """Analyzes per-prompt freshness compared to last report."""

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        in_progress_estimate: str,
        next_refresh_estimate: str,
    ):
        self._prompts_session = prompts_session
        self._evals_session = evals_session
        self._in_progress_estimate = in_progress_estimate
        self._next_refresh_estimate = next_refresh_estimate

    async def analyze_freshness(
        self,
        group_id: int,
        last_report: GroupReport | None,
    ) -> list[PromptFreshnessInfo]:
        """Analyze freshness for all prompts in a group.

        For each prompt:
        1. Get latest completed evaluation
        2. Get evaluation used in last report (from GroupReportItem)
        3. Compare completed_at timestamps
        4. Check if any IN_PROGRESS evaluation exists
        5. Return time estimate based on in_progress status
        """
        # Get all prompts in the group with their text
        prompts_data = await self._get_prompts_in_group(group_id)
        if not prompts_data:
            return []

        prompt_ids = [p["id"] for p in prompts_data]
        prompts_map = {p["id"]: p["text"] for p in prompts_data}

        # Get latest completed evaluation for each prompt
        latest_evals = await self._get_latest_evaluations(prompt_ids)

        # Get evaluations used in last report (if exists)
        report_evals: dict[int, datetime | None] = {}
        if last_report:
            report_evals = await self._get_report_evaluations(last_report.id)

        # Get prompts with in-progress evaluations
        in_progress_prompts = await self._get_in_progress_prompts(prompt_ids)

        # Build freshness info for each prompt
        result = []
        for prompt_id in prompt_ids:
            latest_eval = latest_evals.get(prompt_id)
            previous_answer_at = report_evals.get(prompt_id)
            has_in_progress = prompt_id in in_progress_prompts

            # Determine freshness
            has_fresher_answer = False
            if latest_eval and latest_eval.completed_at:
                if previous_answer_at:
                    has_fresher_answer = latest_eval.completed_at > previous_answer_at
                else:
                    # No previous report or prompt wasn't in last report
                    # If there's a latest evaluation, it's considered "fresh"
                    has_fresher_answer = True

            # Determine time estimate
            if has_in_progress:
                next_refresh = self._in_progress_estimate
            else:
                next_refresh = self._next_refresh_estimate

            result.append(
                PromptFreshnessInfo(
                    prompt_id=prompt_id,
                    prompt_text=prompts_map.get(prompt_id, ""),
                    has_fresher_answer=has_fresher_answer,
                    latest_answer_at=latest_eval.completed_at if latest_eval else None,
                    previous_answer_at=previous_answer_at,
                    next_refresh_estimate=next_refresh,
                    has_in_progress_evaluation=has_in_progress,
                )
            )

        return result

    async def _get_prompts_in_group(self, group_id: int) -> list[dict]:
        """Get all prompts in a group with their text."""
        query = (
            select(Prompt.id, Prompt.prompt_text)
            .join(PromptGroupBinding, PromptGroupBinding.prompt_id == Prompt.id)
            .where(PromptGroupBinding.group_id == group_id)
        )
        result = await self._prompts_session.execute(query)
        return [{"id": row.id, "text": row.prompt_text} for row in result.all()]

    async def _get_latest_evaluations(
        self, prompt_ids: list[int]
    ) -> dict[int, PromptEvaluation]:
        """Get the latest COMPLETED evaluation for each prompt."""
        if not prompt_ids:
            return {}

        # Subquery to get max completed_at per prompt_id
        subq = (
            select(
                PromptEvaluation.prompt_id,
                func.max(PromptEvaluation.completed_at).label("max_completed_at"),
            )
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
            .group_by(PromptEvaluation.prompt_id)
            .subquery()
        )

        # Join back to get full evaluation records
        query = select(PromptEvaluation).join(
            subq,
            (PromptEvaluation.prompt_id == subq.c.prompt_id)
            & (PromptEvaluation.completed_at == subq.c.max_completed_at),
        )

        result = await self._evals_session.execute(query)
        evals = result.scalars().all()

        return {e.prompt_id: e for e in evals}

    async def _get_report_evaluations(
        self, report_id: int
    ) -> dict[int, datetime | None]:
        """Get mapping of prompt_id to evaluation completed_at from a report."""
        query = (
            select(GroupReportItem.prompt_id, PromptEvaluation.completed_at)
            .outerjoin(
                PromptEvaluation,
                GroupReportItem.evaluation_id == PromptEvaluation.id,
            )
            .where(GroupReportItem.report_id == report_id)
        )

        result = await self._evals_session.execute(query)
        return {row.prompt_id: row.completed_at for row in result.all()}

    async def _get_in_progress_prompts(self, prompt_ids: list[int]) -> set[int]:
        """Get prompt IDs that have IN_PROGRESS evaluations."""
        if not prompt_ids:
            return set()

        query = (
            select(PromptEvaluation.prompt_id)
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.IN_PROGRESS,
            )
            .distinct()
        )

        result = await self._evals_session.execute(query)
        return set(result.scalars().all())
