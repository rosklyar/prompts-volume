"""Service for analyzing available evaluation options per prompt."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.evals_models import (
    AIAssistant,
    ConsumedEvaluation,
    EvaluationStatus,
    GroupReport,
    GroupReportItem,
    PromptEvaluation,
)
from src.database.models import Prompt, PromptGroupBinding
from src.reports.models.api_models import EvaluationOption, PromptSelectionInfo


class DefaultSelectionStrategy(Protocol):
    """Strategy for determining default selection for a prompt."""

    def select_default(
        self,
        available_options: list[EvaluationOption],
        was_awaiting: bool,
    ) -> int | None:
        """Return evaluation_id to select by default, or None."""
        ...


class MostRecentSelectionStrategy:
    """Default strategy: select the most recent evaluation."""

    def select_default(
        self,
        available_options: list[EvaluationOption],
        was_awaiting: bool,
    ) -> int | None:
        if not available_options:
            return None
        sorted_options = sorted(
            available_options,
            key=lambda o: o.completed_at,
            reverse=True,
        )
        return sorted_options[0].evaluation_id


# Singleton instance for MostRecentSelectionStrategy
_most_recent_selection_strategy: MostRecentSelectionStrategy | None = None


def get_most_recent_selection_strategy() -> MostRecentSelectionStrategy:
    """Get the singleton MostRecentSelectionStrategy instance."""
    global _most_recent_selection_strategy
    if _most_recent_selection_strategy is None:
        _most_recent_selection_strategy = MostRecentSelectionStrategy()
    return _most_recent_selection_strategy


class SelectionAnalyzerService:
    """Analyzes available evaluation options for each prompt in a group."""

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        price_per_evaluation: Decimal,
        selection_strategy: DefaultSelectionStrategy | None = None,
    ):
        self._prompts_session = prompts_session
        self._evals_session = evals_session
        self._price_per_evaluation = price_per_evaluation
        self._selection_strategy = selection_strategy or MostRecentSelectionStrategy()

    async def analyze_selections(
        self,
        group_id: int,
        user_id: str,
        last_report: GroupReport | None,
        *,
        country_id: int | None = None,
    ) -> list[PromptSelectionInfo]:
        """Analyze available options for each prompt in the group.

        For each prompt:
        1. Get last report's evaluation timestamp (cutoff for freshness)
        2. Find all evaluations newer than that cutoff
        3. Check which are fresh (not consumed by user)
        4. Apply default selection strategy

        Args:
            group_id: The prompt group ID
            user_id: The user ID
            last_report: The most recent report for the group (if any)
            country_id: Optional country filter. If provided, only returns
                       evaluations for that specific country.
        """
        # Get all prompts in the group
        prompts_data = await self._get_prompts_in_group(group_id)
        if not prompts_data:
            return []

        prompt_ids = [p["id"] for p in prompts_data]
        prompts_map = {p["id"]: p["text"] for p in prompts_data}

        # Get last report's evaluation info per prompt
        last_report_evals: dict[int, tuple[int | None, datetime | None]] = {}
        if last_report:
            last_report_evals = await self._get_report_evaluation_info(last_report.id)

        # Get ALL completed evaluations - any can be selected for report generation
        all_evals = await self._get_all_evaluations_with_assistants(
            prompt_ids, country_id=country_id
        )

        # Get consumed evaluation IDs for this user
        all_eval_ids = [e["id"] for evals in all_evals.values() for e in evals]
        consumed_ids = await self._get_consumed_evaluation_ids(user_id, all_eval_ids)

        # Get in-progress prompts
        in_progress_prompts = await self._get_in_progress_prompts(
            prompt_ids, country_id=country_id
        )

        # Build selection info for each prompt
        result = []
        for prompt_id in prompt_ids:
            evals_for_prompt = all_evals.get(prompt_id, [])
            last_eval_info = last_report_evals.get(prompt_id)
            was_awaiting = last_report is not None and last_eval_info is None

            # Build options
            options = []
            for eval_data in evals_for_prompt:
                is_fresh = eval_data["id"] not in consumed_ids
                options.append(
                    EvaluationOption(
                        evaluation_id=eval_data["id"],
                        assistant_id=eval_data["assistant_id"],
                        assistant_name=eval_data["assistant_name"],
                        completed_at=eval_data["completed_at"],
                        is_fresh=is_fresh,
                        unit_price=self._price_per_evaluation if is_fresh else Decimal("0"),
                    )
                )

            # Apply default selection
            default_selection = self._selection_strategy.select_default(
                options, was_awaiting
            )

            result.append(
                PromptSelectionInfo(
                    prompt_id=prompt_id,
                    prompt_text=prompts_map.get(prompt_id, ""),
                    available_options=options,
                    default_selection=default_selection,
                    was_awaiting_in_last_report=was_awaiting,
                    last_report_evaluation_id=last_eval_info[0] if last_eval_info else None,
                    last_report_evaluation_at=last_eval_info[1] if last_eval_info else None,
                    has_in_progress_evaluation=prompt_id in in_progress_prompts,
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

    async def _get_report_evaluation_info(
        self, report_id: int
    ) -> dict[int, tuple[int | None, datetime | None]]:
        """Get mapping of prompt_id to (evaluation_id, completed_at) from a report."""
        query = (
            select(
                GroupReportItem.prompt_id,
                GroupReportItem.evaluation_id,
                PromptEvaluation.completed_at,
            )
            .outerjoin(
                PromptEvaluation,
                GroupReportItem.evaluation_id == PromptEvaluation.id,
            )
            .where(GroupReportItem.report_id == report_id)
        )
        result = await self._evals_session.execute(query)
        return {
            row.prompt_id: (row.evaluation_id, row.completed_at)
            for row in result.all()
        }

    async def _get_all_evaluations_with_assistants(
        self,
        prompt_ids: list[int],
        *,
        country_id: int | None = None,
    ) -> dict[int, list[dict]]:
        """Get all completed evaluations for each prompt, with assistant info.

        Args:
            prompt_ids: List of prompt IDs to check
            country_id: Optional country filter. If provided, only returns
                       evaluations for that specific country.

        Returns ALL completed evaluations - any can be selected for report generation.
        """
        if not prompt_ids:
            return {}

        # Get all completed evaluations for these prompts with assistant info
        conditions = [
            PromptEvaluation.prompt_id.in_(prompt_ids),
            PromptEvaluation.status == EvaluationStatus.COMPLETED,
        ]
        if country_id is not None:
            conditions.append(PromptEvaluation.country_id == country_id)

        query = (
            select(
                PromptEvaluation.id,
                PromptEvaluation.prompt_id,
                PromptEvaluation.assistant_id,
                PromptEvaluation.completed_at,
                AIAssistant.name.label("assistant_name"),
            )
            .join(AIAssistant, PromptEvaluation.assistant_id == AIAssistant.id)
            .where(*conditions)
            .order_by(PromptEvaluation.completed_at.desc())
        )
        result = await self._evals_session.execute(query)

        # Group all evaluations by prompt - no filtering
        evaluations_by_prompt: dict[int, list[dict]] = {}
        for row in result.all():
            if row.prompt_id not in evaluations_by_prompt:
                evaluations_by_prompt[row.prompt_id] = []
            evaluations_by_prompt[row.prompt_id].append({
                "id": row.id,
                "prompt_id": row.prompt_id,
                "assistant_id": row.assistant_id,
                "completed_at": row.completed_at,
                "assistant_name": row.assistant_name,
            })

        return evaluations_by_prompt

    async def _get_consumed_evaluation_ids(
        self, user_id: str, evaluation_ids: list[int]
    ) -> set[int]:
        """Get which evaluations the user has already paid for."""
        if not evaluation_ids:
            return set()

        query = select(ConsumedEvaluation.evaluation_id).where(
            ConsumedEvaluation.user_id == user_id,
            ConsumedEvaluation.evaluation_id.in_(evaluation_ids),
        )
        result = await self._evals_session.execute(query)
        return set(result.scalars().all())

    async def _get_in_progress_prompts(
        self,
        prompt_ids: list[int],
        *,
        country_id: int | None = None,
    ) -> set[int]:
        """Get prompt IDs that have IN_PROGRESS evaluations.

        Args:
            prompt_ids: List of prompt IDs to check
            country_id: Optional country filter. If provided, only considers
                       in-progress evaluations for that specific country.
        """
        if not prompt_ids:
            return set()

        conditions = [
            PromptEvaluation.prompt_id.in_(prompt_ids),
            PromptEvaluation.status == EvaluationStatus.IN_PROGRESS,
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
