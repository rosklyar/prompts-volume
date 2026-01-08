"""Service for analyzing available evaluation options per prompt."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.evals_models import (
    AIAssistant,
    AIAssistantPlan,
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
    ) -> list[PromptSelectionInfo]:
        """Analyze available options for each prompt in the group.

        For each prompt:
        1. Get last report's evaluation timestamp (cutoff for freshness)
        2. Find all evaluations newer than that cutoff
        3. Check which are fresh (not consumed by user)
        4. Apply default selection strategy
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

        # Build cutoff map: prompt_id -> cutoff_timestamp (or None if no previous)
        cutoff_map: dict[int, datetime | None] = {}
        for prompt_id in prompt_ids:
            eval_info = last_report_evals.get(prompt_id)
            cutoff_map[prompt_id] = eval_info[1] if eval_info else None

        # Collect last report's evaluation IDs (to include them in available options)
        last_report_eval_ids: set[int] = {
            eval_info[0]
            for eval_info in last_report_evals.values()
            if eval_info[0] is not None
        }

        # Get all fresher evaluations with assistant info (+ last report's evals)
        fresher_evals = await self._get_fresher_evaluations_with_assistants(
            prompt_ids, cutoff_map, last_report_eval_ids
        )

        # Get consumed evaluation IDs for this user
        all_eval_ids = [e["id"] for evals in fresher_evals.values() for e in evals]
        consumed_ids = await self._get_consumed_evaluation_ids(user_id, all_eval_ids)

        # Get in-progress prompts
        in_progress_prompts = await self._get_in_progress_prompts(prompt_ids)

        # Build selection info for each prompt
        result = []
        for prompt_id in prompt_ids:
            evals_for_prompt = fresher_evals.get(prompt_id, [])
            last_eval_info = last_report_evals.get(prompt_id)
            was_awaiting = last_report is not None and last_eval_info is None

            # Build options
            options = []
            for eval_data in evals_for_prompt:
                is_fresh = eval_data["id"] not in consumed_ids
                options.append(
                    EvaluationOption(
                        evaluation_id=eval_data["id"],
                        assistant_plan_id=eval_data["assistant_plan_id"],
                        assistant_plan_name=eval_data["plan_name"],
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

    async def _get_fresher_evaluations_with_assistants(
        self,
        prompt_ids: list[int],
        cutoff_map: dict[int, datetime | None],
        last_report_eval_ids: set[int],
    ) -> dict[int, list[dict]]:
        """Get evaluations fresher than cutoff for each prompt, with assistant info.

        Includes evaluations that are either:
        - Strictly newer than cutoff (completed_at > cutoff)
        - OR were in the last report (id in last_report_eval_ids)
        """
        if not prompt_ids:
            return {}

        # Get all completed evaluations for these prompts with assistant info
        query = (
            select(
                PromptEvaluation.id,
                PromptEvaluation.prompt_id,
                PromptEvaluation.assistant_plan_id,
                PromptEvaluation.completed_at,
                AIAssistantPlan.name.label("plan_name"),
                AIAssistant.name.label("assistant_name"),
            )
            .join(
                AIAssistantPlan,
                PromptEvaluation.assistant_plan_id == AIAssistantPlan.id,
            )
            .join(AIAssistant, AIAssistantPlan.assistant_id == AIAssistant.id)
            .where(
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
            .order_by(PromptEvaluation.completed_at.desc())
        )
        result = await self._evals_session.execute(query)

        # Filter by cutoff per prompt
        evaluations_by_prompt: dict[int, list[dict]] = {}
        for row in result.all():
            cutoff = cutoff_map.get(row.prompt_id)
            # Include if: no cutoff, OR newer than cutoff, OR was in last report
            is_fresher = cutoff is None or (row.completed_at and row.completed_at > cutoff)
            was_in_last_report = row.id in last_report_eval_ids
            if is_fresher or was_in_last_report:
                if row.prompt_id not in evaluations_by_prompt:
                    evaluations_by_prompt[row.prompt_id] = []
                evaluations_by_prompt[row.prompt_id].append({
                    "id": row.id,
                    "prompt_id": row.prompt_id,
                    "assistant_plan_id": row.assistant_plan_id,
                    "completed_at": row.completed_at,
                    "plan_name": row.plan_name,
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
