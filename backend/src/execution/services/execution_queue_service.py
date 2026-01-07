"""Service for managing the unified execution queue."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.evals_models import (
    ExecutionQueue,
    ExecutionQueueStatus,
    PromptEvaluation,
    EvaluationStatus,
)
from src.database.models import Prompt
from src.execution.protocols.queue_operations import (
    AddToQueueResult,
    QueueEntry,
    QueuePoller,
    QueueReader,
    QueueWriter,
)


class ExecutionQueueService(QueueReader, QueueWriter, QueuePoller):
    """Service for managing the unified execution queue.

    Implements QueueReader, QueueWriter, and QueuePoller protocols.

    Uses dual session pattern:
    - evals_session: for ExecutionQueue, PromptEvaluation (evals_db)
    - prompts_session: for Prompt lookups (prompts_db)
    """

    def __init__(
        self,
        evals_session: AsyncSession,
        prompts_session: AsyncSession,
        execution_timeout_hours: int = 2,
    ):
        self._evals_session = evals_session
        self._prompts_session = prompts_session
        self._timeout_hours = execution_timeout_hours

    def _to_queue_entry(self, db_entry: ExecutionQueue) -> QueueEntry:
        """Convert database model to domain model."""
        return QueueEntry(
            id=db_entry.id,
            prompt_id=db_entry.prompt_id,
            requested_by=db_entry.requested_by,
            request_batch_id=db_entry.request_batch_id,
            requested_at=db_entry.requested_at,
            status=db_entry.status,
            claimed_at=db_entry.claimed_at,
            completed_at=db_entry.completed_at,
            evaluation_id=db_entry.evaluation_id,
        )

    # =========================================================================
    # QueueReader implementation
    # =========================================================================

    async def get_pending_count(self) -> int:
        """Get total number of pending items in queue."""
        result = await self._evals_session.execute(
            select(func.count(ExecutionQueue.id))
            .where(ExecutionQueue.status == ExecutionQueueStatus.PENDING)
        )
        return result.scalar_one()

    async def get_user_pending_items(self, user_id: str) -> list[QueueEntry]:
        """Get all pending/in_progress items for a user."""
        result = await self._evals_session.execute(
            select(ExecutionQueue)
            .where(
                ExecutionQueue.requested_by == user_id,
                ExecutionQueue.status.in_([
                    ExecutionQueueStatus.PENDING,
                    ExecutionQueueStatus.IN_PROGRESS,
                ]),
            )
            .order_by(ExecutionQueue.requested_at.asc())
        )
        return [self._to_queue_entry(e) for e in result.scalars().all()]

    async def is_prompt_in_queue(self, prompt_id: int) -> bool:
        """Check if prompt is already in queue (pending or in_progress)."""
        result = await self._evals_session.execute(
            select(func.count(ExecutionQueue.id))
            .where(
                ExecutionQueue.prompt_id == prompt_id,
                ExecutionQueue.status.in_([
                    ExecutionQueueStatus.PENDING,
                    ExecutionQueueStatus.IN_PROGRESS,
                ]),
            )
        )
        return result.scalar_one() > 0

    # =========================================================================
    # QueueWriter implementation
    # =========================================================================

    async def add_to_queue(
        self,
        prompt_ids: list[int],
        user_id: str,
        batch_id: str | None = None,
    ) -> AddToQueueResult:
        """Add prompts to execution queue.

        Skips prompts that are already in queue (global uniqueness).
        Returns result with queued_count, skipped_count, total_queue_size.
        """
        if not prompt_ids:
            total = await self.get_pending_count()
            return AddToQueueResult(
                queued_count=0,
                skipped_count=0,
                total_queue_size=total,
                queued_entries=[],
            )

        batch_id = batch_id or str(uuid.uuid4())
        queued_entries: list[QueueEntry] = []
        skipped_count = 0

        # Check which prompts are already in queue
        already_in_queue = await self._evals_session.execute(
            select(ExecutionQueue.prompt_id)
            .where(
                ExecutionQueue.prompt_id.in_(prompt_ids),
                ExecutionQueue.status.in_([
                    ExecutionQueueStatus.PENDING,
                    ExecutionQueueStatus.IN_PROGRESS,
                ]),
            )
        )
        already_queued_ids = set(already_in_queue.scalars().all())

        # Add new entries for prompts not already in queue
        for prompt_id in prompt_ids:
            if prompt_id in already_queued_ids:
                skipped_count += 1
                continue

            entry = ExecutionQueue(
                prompt_id=prompt_id,
                requested_by=user_id,
                request_batch_id=batch_id,
                status=ExecutionQueueStatus.PENDING,
            )
            self._evals_session.add(entry)
            await self._evals_session.flush()
            await self._evals_session.refresh(entry)
            queued_entries.append(self._to_queue_entry(entry))

        total = await self.get_pending_count()

        return AddToQueueResult(
            queued_count=len(queued_entries),
            skipped_count=skipped_count,
            total_queue_size=total,
            queued_entries=queued_entries,
        )

    async def cancel_pending(
        self,
        prompt_ids: list[int],
        user_id: str,
    ) -> int:
        """Cancel pending items for user.

        Only cancels PENDING items (not IN_PROGRESS).
        Returns count cancelled.
        """
        if not prompt_ids:
            return 0

        result = await self._evals_session.execute(
            update(ExecutionQueue)
            .where(
                ExecutionQueue.prompt_id.in_(prompt_ids),
                ExecutionQueue.requested_by == user_id,
                ExecutionQueue.status == ExecutionQueueStatus.PENDING,
            )
            .values(status=ExecutionQueueStatus.CANCELLED)
        )

        return result.rowcount

    # =========================================================================
    # QueuePoller implementation
    # =========================================================================

    async def poll_next(
        self,
        assistant_plan_id: int,
    ) -> tuple[QueueEntry, Prompt] | None:
        """Atomically claim next item from queue (FIFO order).

        Uses SELECT FOR UPDATE SKIP LOCKED for concurrency.
        Also handles timeout cleanup (IN_PROGRESS > timeout reset to PENDING).

        Returns (queue_entry, prompt) or None if queue empty.
        """
        now = datetime.now(timezone.utc)
        timeout_cutoff = now - timedelta(hours=self._timeout_hours)

        # First, reset any timed-out items back to PENDING
        await self._evals_session.execute(
            update(ExecutionQueue)
            .where(
                ExecutionQueue.status == ExecutionQueueStatus.IN_PROGRESS,
                ExecutionQueue.claimed_at < timeout_cutoff,
            )
            .values(
                status=ExecutionQueueStatus.PENDING,
                claimed_at=None,
            )
        )

        # Query for next pending item (FIFO order)
        query = (
            select(ExecutionQueue)
            .where(ExecutionQueue.status == ExecutionQueueStatus.PENDING)
            .order_by(ExecutionQueue.requested_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        result = await self._evals_session.execute(query)
        queue_entry = result.scalar_one_or_none()

        if not queue_entry:
            return None

        # Fetch the prompt from prompts_db
        prompt_result = await self._prompts_session.execute(
            select(Prompt).where(Prompt.id == queue_entry.prompt_id)
        )
        prompt = prompt_result.scalar_one_or_none()

        if not prompt:
            # Prompt was deleted from prompts_db, mark as failed
            queue_entry.status = ExecutionQueueStatus.FAILED
            queue_entry.completed_at = now
            await self._evals_session.flush()
            return None

        # Claim the queue entry
        queue_entry.status = ExecutionQueueStatus.IN_PROGRESS
        queue_entry.claimed_at = now

        # Create evaluation for this prompt
        evaluation = PromptEvaluation(
            prompt_id=queue_entry.prompt_id,
            assistant_plan_id=assistant_plan_id,
            status=EvaluationStatus.IN_PROGRESS,
            claimed_at=now,
        )
        self._evals_session.add(evaluation)
        await self._evals_session.flush()
        await self._evals_session.refresh(evaluation)

        # Link queue entry to evaluation
        queue_entry.evaluation_id = evaluation.id
        await self._evals_session.flush()
        await self._evals_session.refresh(queue_entry)

        return (self._to_queue_entry(queue_entry), prompt)

    async def mark_completed(
        self,
        queue_entry_id: int,
        evaluation_id: int,
    ) -> None:
        """Mark queue entry as completed with evaluation reference."""
        result = await self._evals_session.execute(
            select(ExecutionQueue).where(ExecutionQueue.id == queue_entry_id)
        )
        entry = result.scalar_one_or_none()

        if entry:
            entry.status = ExecutionQueueStatus.COMPLETED
            entry.completed_at = datetime.now(timezone.utc)
            entry.evaluation_id = evaluation_id
            await self._evals_session.flush()

    async def mark_failed(
        self,
        queue_entry_id: int,
        reason: str,
    ) -> None:
        """Mark queue entry as failed."""
        result = await self._evals_session.execute(
            select(ExecutionQueue).where(ExecutionQueue.id == queue_entry_id)
        )
        entry = result.scalar_one_or_none()

        if entry:
            entry.status = ExecutionQueueStatus.FAILED
            entry.completed_at = datetime.now(timezone.utc)
            await self._evals_session.flush()

    # =========================================================================
    # Additional helper methods
    # =========================================================================

    async def get_queue_entry_by_evaluation_id(
        self,
        evaluation_id: int,
    ) -> Optional[QueueEntry]:
        """Get queue entry by evaluation ID."""
        result = await self._evals_session.execute(
            select(ExecutionQueue)
            .where(ExecutionQueue.evaluation_id == evaluation_id)
        )
        entry = result.scalar_one_or_none()
        return self._to_queue_entry(entry) if entry else None
