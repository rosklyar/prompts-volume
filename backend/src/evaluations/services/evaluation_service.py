"""Service for managing prompt evaluations."""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from fastapi import Depends, HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database.evals_models import (
    AIAssistant,
    AIAssistantPlan,
    EvaluationStatus,
    PromptEvaluation,
    PriorityPromptQueue,
)
from src.database.evals_session import get_evals_session
from src.database.models import Prompt
from src.database.session import get_async_session


class EvaluationService:
    """Service for managing prompt evaluations.

    Uses dual session pattern:
    - evals_session: for evaluations, AI assistants, priority queue (evals_db)
    - prompts_session: for Prompt lookups (prompts_db)
    """

    def __init__(
        self,
        evals_session: AsyncSession,
        prompts_session: AsyncSession,
        min_days_since_last_evaluation: int,
        evaluation_timeout_hours: int,
    ):
        self.evals_session = evals_session
        self.prompts_session = prompts_session
        self.min_days_since_last_evaluation = min_days_since_last_evaluation
        self.evaluation_timeout_hours = evaluation_timeout_hours

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

        NEW: Checks priority queue FIRST, then falls back to regular prompts.

        Returns tuple of (PromptEvaluation, Prompt) for the first available prompt
        that meets criteria:
        - Priority prompts are returned before regular prompts
        - No evaluation exists for this assistant+plan, OR
        - Last evaluation completed >= configured days ago, OR
        - IN_PROGRESS evaluation timed out (claimed > configured hours ago)

        Uses SELECT FOR UPDATE SKIP LOCKED for lock-free concurrency.
        """
        # Step 1: Try to get from priority queue
        result = await self._poll_priority_queue(assistant_plan_id)
        if result:
            return result

        # Step 2: Fall back to regular polling (existing logic)
        return await self._poll_regular_prompts(assistant_plan_id)

    async def _poll_priority_queue(
        self,
        assistant_plan_id: int,
    ) -> Optional[Tuple[PromptEvaluation, Prompt]]:
        """
        Poll for priority prompts first.

        Uses same locking logic but queries PriorityPromptQueue.
        Removes from queue after claiming.
        """
        now = datetime.now()
        timeout_cutoff = now - timedelta(hours=self.evaluation_timeout_hours)

        # Find prompt_ids that are currently locked for this assistant
        locked_subquery = (
            select(PromptEvaluation.prompt_id)
            .where(
                PromptEvaluation.assistant_plan_id == assistant_plan_id,
                or_(
                    # Locked if in_progress AND claimed recently (not timed out)
                    and_(
                        PromptEvaluation.status == EvaluationStatus.IN_PROGRESS,
                        PromptEvaluation.claimed_at > timeout_cutoff
                    ),
                )
            )
        )

        # Query priority queue for first available prompt (not locked, FIFO order)
        query = (
            select(PriorityPromptQueue)
            .where(PriorityPromptQueue.prompt_id.not_in(locked_subquery))
            .order_by(PriorityPromptQueue.created_at.asc())  # FIFO
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        result = await self.evals_session.execute(query)
        queue_entry = result.scalar_one_or_none()

        if not queue_entry:
            return None  # No priority prompts available

        # Fetch the prompt from prompts_db
        prompt = await self._get_prompt_by_id(queue_entry.prompt_id)
        if not prompt:
            # Prompt was deleted from prompts_db, remove orphan queue entry
            await self.evals_session.delete(queue_entry)
            await self.evals_session.flush()
            return None

        # Create evaluation for this prompt
        evaluation = PromptEvaluation(
            prompt_id=queue_entry.prompt_id,
            assistant_plan_id=assistant_plan_id,
            status=EvaluationStatus.IN_PROGRESS,
            claimed_at=now,
        )
        self.evals_session.add(evaluation)

        # Remove from priority queue
        await self.evals_session.delete(queue_entry)
        await self.evals_session.flush()

        # Reload evaluation to get generated ID
        await self.evals_session.refresh(evaluation)

        return (evaluation, prompt)

    async def _poll_regular_prompts(
        self,
        assistant_plan_id: int,
    ) -> Optional[Tuple[PromptEvaluation, Prompt]]:
        """
        Original polling logic for regular prompts.

        Returns tuple of (PromptEvaluation, Prompt) for the first available prompt
        that meets criteria:
        - No evaluation exists for this assistant+plan, OR
        - Last evaluation completed >= configured days ago, OR
        - IN_PROGRESS evaluation timed out (claimed > configured hours ago)
        """
        now = datetime.now()
        completed_cutoff = now - timedelta(days=self.min_days_since_last_evaluation)
        timeout_cutoff = now - timedelta(hours=self.evaluation_timeout_hours)

        # Subquery: prompt_ids that are currently locked in evals_db
        locked_subquery = (
            select(PromptEvaluation.prompt_id)
            .where(
                PromptEvaluation.assistant_plan_id == assistant_plan_id,
            )
            .where(
                or_(
                    # Locked if in_progress AND claimed recently (not timed out)
                    and_(
                        PromptEvaluation.status == EvaluationStatus.IN_PROGRESS,
                        PromptEvaluation.claimed_at > timeout_cutoff
                    ),
                    # Locked if completed recently
                    and_(
                        PromptEvaluation.status == EvaluationStatus.COMPLETED,
                        PromptEvaluation.completed_at > completed_cutoff
                    )
                )
            )
        )

        # Get all locked prompt_ids first
        locked_result = await self.evals_session.execute(locked_subquery)
        locked_prompt_ids = list(locked_result.scalars().all())

        # Query prompts_db for available prompts
        query = select(Prompt).limit(1).with_for_update(skip_locked=True)
        if locked_prompt_ids:
            query = query.where(Prompt.id.not_in(locked_prompt_ids))

        result = await self.prompts_session.execute(query)
        prompt = result.scalar_one_or_none()

        if not prompt:
            return None

        # Create evaluation in evals_db
        evaluation = PromptEvaluation(
            prompt_id=prompt.id,
            assistant_plan_id=assistant_plan_id,
            status=EvaluationStatus.IN_PROGRESS,
            claimed_at=now,
        )
        self.evals_session.add(evaluation)
        await self.evals_session.flush()

        # Reload evaluation to get generated ID
        await self.evals_session.refresh(evaluation)

        return (evaluation, prompt)

    async def submit_answer(
        self,
        evaluation_id: int,
        answer: dict,
    ) -> PromptEvaluation:
        """Submit evaluation answer and mark as completed."""
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
        """Release evaluation - delete or mark as failed."""
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

        if mark_as_failed:
            # Mark as failed
            evaluation.status = EvaluationStatus.FAILED
            evaluation.answer = {"error": failure_reason} if failure_reason else None
            evaluation.completed_at = datetime.now()
            await self.evals_session.flush()
            return (evaluation_id, "marked_failed")
        else:
            # Delete evaluation (makes prompt available again)
            await self.evals_session.delete(evaluation)
            await self.evals_session.flush()
            return (evaluation_id, "deleted")


def get_evaluation_service(
    evals_session: AsyncSession = Depends(get_evals_session),
    prompts_session: AsyncSession = Depends(get_async_session),
) -> EvaluationService:
    """Dependency injection for EvaluationService."""
    return EvaluationService(
        evals_session,
        prompts_session,
        settings.min_days_since_last_evaluation,
        settings.evaluation_timeout_hours,
    )
