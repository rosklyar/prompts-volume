"""Service for managing prompt evaluations."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.database.models import EvaluationStatus, Prompt, PromptEvaluation
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

    async def poll_for_prompt(
        self,
        assistant_name: str,
        plan_name: str,
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
                PromptEvaluation.assistant_name == assistant_name,
                PromptEvaluation.plan_name == plan_name,
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
            assistant_name=assistant_name,
            plan_name=plan_name,
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
