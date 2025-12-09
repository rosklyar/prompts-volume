"""Service for managing prompt evaluations."""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.database.models import AIAssistant, AIAssistantPlan, EvaluationStatus, Prompt, PromptEvaluation
from src.database.session import get_async_session


class EvaluationService:
    """Service for managing prompt evaluations."""

    def __init__(
        self,
        session: AsyncSession,
        min_days_since_last_evaluation: int,
        evaluation_timeout_hours: int,
    ):
        self.session = session
        self.min_days_since_last_evaluation = min_days_since_last_evaluation
        self.evaluation_timeout_hours = evaluation_timeout_hours

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
        # Single query with JOIN for efficiency
        query = (
            select(AIAssistantPlan.id)
            .join(AIAssistant, AIAssistantPlan.assistant_id == AIAssistant.id)
            .where(
                func.upper(AIAssistant.name) == assistant_name.upper(),
                func.upper(AIAssistantPlan.name) == plan_name.upper(),
            )
            .limit(1)
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def poll_for_prompt(
        self,
        assistant_plan_id: int,
    ) -> Optional[PromptEvaluation]:
        """
        Atomically find and claim a prompt for evaluation.

        Returns the first available prompt that meets criteria:
        - No evaluation exists for this assistant+plan, OR
        - Last evaluation completed >= configured days ago, OR
        - IN_PROGRESS evaluation timed out (claimed > configured hours ago)

        Uses SELECT FOR UPDATE SKIP LOCKED for lock-free concurrency.
        """
        # Step 1: Build subquery to find prompts that are currently locked
        now = datetime.now()
        completed_cutoff = now - timedelta(days=self.min_days_since_last_evaluation)
        timeout_cutoff = now - timedelta(hours=self.evaluation_timeout_hours)

        subquery = (
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

        # Step 2: Find first available prompt (not in locked set)
        query = (
            select(Prompt)
            .where(Prompt.id.not_in(subquery))
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        # Execute and get single prompt
        result = await self.session.execute(query)
        prompt = result.scalar_one_or_none()

        if not prompt:
            return None  # No prompts available

        # Step 3: Create PromptEvaluation record atomically (CAS)
        now = datetime.now()

        evaluation = PromptEvaluation(
            prompt_id=prompt.id,
            assistant_plan_id=assistant_plan_id,
            status=EvaluationStatus.IN_PROGRESS,
            claimed_at=now,
        )
        self.session.add(evaluation)
        await self.session.flush()

        # Reload evaluation with eager loaded prompt relationship
        result = await self.session.execute(
            select(PromptEvaluation)
            .where(PromptEvaluation.id == evaluation.id)
            .options(selectinload(PromptEvaluation.prompt))
        )
        evaluation = result.scalar_one()

        return evaluation

    async def submit_answer(
        self,
        evaluation_id: int,
        answer: dict,
    ) -> PromptEvaluation:
        """Submit evaluation answer and mark as completed."""
        result = await self.session.execute(
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

        await self.session.flush()
        await self.session.refresh(evaluation)

        return evaluation

    async def get_latest_results(
        self,
        assistant_plan_id: int,
        prompt_ids: List[int],
    ) -> List[PromptEvaluation]:
        """
        Get latest completed evaluation results for given prompt IDs.

        Returns the most recent COMPLETED evaluation for each prompt_id
        that has been evaluated with the specified assistant/plan.

        Uses PostgreSQL DISTINCT ON to get latest per prompt.
        """
        if not prompt_ids:
            return []

        # Use DISTINCT ON (PostgreSQL-specific) to get latest per prompt_id
        query = (
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

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def release_evaluation(
        self,
        evaluation_id: int,
        mark_as_failed: bool,
        failure_reason: Optional[str] = None,
    ) -> tuple[int, str]:
        """Release evaluation - delete or mark as failed."""
        result = await self.session.execute(
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
            await self.session.flush()
            return (evaluation_id, "marked_failed")
        else:
            # Delete evaluation (makes prompt available again)
            await self.session.delete(evaluation)
            await self.session.flush()
            return (evaluation_id, "deleted")


def get_evaluation_service(
    session: AsyncSession = Depends(get_async_session),
) -> EvaluationService:
    """Dependency injection for EvaluationService."""
    return EvaluationService(
        session,
        settings.min_days_since_last_evaluation,
        settings.evaluation_timeout_hours,
    )
