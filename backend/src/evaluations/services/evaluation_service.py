"""Service for managing prompt evaluations."""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database.evals_models import (
    AIAssistant,
    AIAssistantPlan,
    EvaluationStatus,
    PromptEvaluation,
)
from src.database.evals_session import get_evals_session
from src.database.models import Prompt
from src.database.session import get_async_session
from src.execution.services.execution_queue_service import ExecutionQueueService


class EvaluationService:
    """Service for managing prompt evaluations.

    Uses dual session pattern:
    - evals_session: for evaluations, AI assistants (evals_db)
    - prompts_session: for Prompt lookups (prompts_db)

    Polls from ExecutionQueue only - no periodic all-prompts execution.
    """

    def __init__(
        self,
        evals_session: AsyncSession,
        prompts_session: AsyncSession,
        execution_timeout_hours: int,
    ):
        self.evals_session = evals_session
        self.prompts_session = prompts_session
        self.execution_timeout_hours = execution_timeout_hours
        self._queue_service = ExecutionQueueService(
            evals_session,
            prompts_session,
            execution_timeout_hours,
        )

    async def _get_prompt_by_id(self, prompt_id: int) -> Optional[Prompt]:
        """Fetch a single prompt from prompts_db."""
        result = await self.prompts_session.execute(
            select(Prompt).where(Prompt.id == prompt_id)
        )
        return result.scalar_one_or_none()

    async def _get_prompts_by_ids(self, prompt_ids: List[int]) -> dict[int, Prompt]:
        """Fetch multiple prompts from prompts_db, returns dict keyed by prompt_id."""
        if not prompt_ids:
            return {}
        result = await self.prompts_session.execute(
            select(Prompt).where(Prompt.id.in_(prompt_ids))
        )
        return {p.id: p for p in result.scalars().all()}

    async def get_assistant_plan_id(
        self,
        assistant_name: str,
        plan_name: str,
    ) -> Optional[int]:
        """
        Get assistant_plan_id for the given assistant and plan names.

        Performs case-insensitive lookup using UPPER() SQL function.

        Returns:
            assistant_plan_id if valid combination exists, None otherwise
        """
        # Single query with JOIN for efficiency (both tables in evals_db)
        query = (
            select(AIAssistantPlan.id)
            .join(AIAssistant, AIAssistantPlan.assistant_id == AIAssistant.id)
            .where(
                func.upper(AIAssistant.name) == assistant_name.upper(),
                func.upper(AIAssistantPlan.name) == plan_name.upper(),
            )
            .limit(1)
        )

        result = await self.evals_session.execute(query)
        return result.scalar_one_or_none()

    async def poll_for_prompt(
        self,
        assistant_plan_id: int,
    ) -> Optional[Tuple[PromptEvaluation, Prompt]]:
        """
        Atomically find and claim a prompt for evaluation.

        ONLY polls from ExecutionQueue - no periodic all-prompts execution.
        Uses FIFO order with SELECT FOR UPDATE SKIP LOCKED for concurrency.

        Returns tuple of (PromptEvaluation, Prompt) or None if queue empty.
        """
        result = await self._queue_service.poll_next(assistant_plan_id)

        if not result:
            return None

        queue_entry, prompt = result

        # Get the evaluation that was created by poll_next
        eval_result = await self.evals_session.execute(
            select(PromptEvaluation).where(
                PromptEvaluation.id == queue_entry.evaluation_id
            )
        )
        evaluation = eval_result.scalar_one_or_none()

        if not evaluation:
            return None

        return (evaluation, prompt)

    async def submit_answer(
        self,
        evaluation_id: int,
        answer: dict,
    ) -> PromptEvaluation:
        """Submit evaluation answer and mark as completed.

        Also updates the corresponding ExecutionQueue entry to COMPLETED.
        """
        result = await self.evals_session.execute(
            select(PromptEvaluation).where(PromptEvaluation.id == evaluation_id)
        )
        evaluation = result.scalar_one_or_none()

        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        if evaluation.status == EvaluationStatus.COMPLETED:
            raise HTTPException(
                status_code=409,
                detail="Evaluation already completed"
            )

        # Update evaluation
        evaluation.status = EvaluationStatus.COMPLETED
        evaluation.answer = answer
        evaluation.completed_at = datetime.now()

        await self.evals_session.flush()
        await self.evals_session.refresh(evaluation)

        # Update queue entry status
        queue_entry = await self._queue_service.get_queue_entry_by_evaluation_id(
            evaluation_id
        )
        if queue_entry:
            await self._queue_service.mark_completed(queue_entry.id, evaluation_id)

        return evaluation

    async def get_latest_results(
        self,
        assistant_plan_id: int,
        prompt_ids: List[int],
    ) -> List[Tuple[Prompt, Optional[PromptEvaluation]]]:
        """
        Get latest completed evaluation results for given prompt IDs.

        Returns tuple of (Prompt, PromptEvaluation) for each requested prompt_id.
        PromptEvaluation will be None if no completed evaluation exists.

        Uses PostgreSQL DISTINCT ON to get latest per prompt.
        """
        if not prompt_ids:
            return []

        # Step 1: Fetch all prompts by ID from prompts_db
        prompts = await self._get_prompts_by_ids(prompt_ids)

        # Step 2: Fetch latest completed evaluations from evals_db using DISTINCT ON
        evals_query = (
            select(PromptEvaluation)
            .where(
                PromptEvaluation.assistant_plan_id == assistant_plan_id,
                PromptEvaluation.prompt_id.in_(prompt_ids),
                PromptEvaluation.status == EvaluationStatus.COMPLETED,
            )
            .order_by(
                PromptEvaluation.prompt_id,
                PromptEvaluation.completed_at.desc(),
            )
            .distinct(PromptEvaluation.prompt_id)
        )

        result = await self.evals_session.execute(evals_query)
        evaluations = {e.prompt_id: e for e in result.scalars().all()}

        # Step 3: Merge results - return all prompts with their evaluations (or None)
        return [
            (prompts[pid], evaluations.get(pid))
            for pid in prompt_ids
            if pid in prompts  # Skip non-existent prompt IDs
        ]

    async def release_evaluation(
        self,
        evaluation_id: int,
        mark_as_failed: bool,
        failure_reason: Optional[str] = None,
    ) -> tuple[int, str]:
        """Release evaluation - delete or mark as failed.

        Also updates the corresponding ExecutionQueue entry.
        """
        result = await self.evals_session.execute(
            select(PromptEvaluation).where(PromptEvaluation.id == evaluation_id)
        )
        evaluation = result.scalar_one_or_none()

        if not evaluation:
            raise HTTPException(status_code=404, detail="Evaluation not found")

        if evaluation.status == EvaluationStatus.COMPLETED:
            raise HTTPException(
                status_code=409,
                detail="Cannot release completed evaluation"
            )

        # Get queue entry before modifying evaluation
        queue_entry = await self._queue_service.get_queue_entry_by_evaluation_id(
            evaluation_id
        )

        if mark_as_failed:
            # Mark evaluation as failed
            evaluation.status = EvaluationStatus.FAILED
            evaluation.answer = {"error": failure_reason} if failure_reason else None
            evaluation.completed_at = datetime.now()
            await self.evals_session.flush()

            # Mark queue entry as failed
            if queue_entry:
                await self._queue_service.mark_failed(
                    queue_entry.id,
                    failure_reason or "Released by bot",
                )

            return (evaluation_id, "marked_failed")
        else:
            # Delete evaluation (makes prompt available again)
            await self.evals_session.delete(evaluation)
            await self.evals_session.flush()

            # Mark queue entry as failed (since evaluation was deleted)
            if queue_entry:
                await self._queue_service.mark_failed(
                    queue_entry.id,
                    failure_reason or "Evaluation deleted",
                )

            return (evaluation_id, "deleted")


def get_evaluation_service(
    evals_session: AsyncSession = Depends(get_evals_session),
    prompts_session: AsyncSession = Depends(get_async_session),
) -> EvaluationService:
    """Dependency injection for EvaluationService."""
    return EvaluationService(
        evals_session,
        prompts_session,
        settings.evaluation_timeout_hours,
    )
