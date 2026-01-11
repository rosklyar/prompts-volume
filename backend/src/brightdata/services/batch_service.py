"""Database-backed service for tracking Bright Data batches."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.evals_models import BrightDataBatch, BrightDataBatchStatus

logger = logging.getLogger(__name__)


class BrightDataBatchService:
    """Service for managing Bright Data batch records in the database.

    Replaces InMemoryBatchRegistry with persistent database storage.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def register_batch(
        self,
        batch_id: str,
        prompt_ids: list[int],
        user_id: str,
    ) -> BrightDataBatch:
        """Register a new batch for webhook correlation.

        Args:
            batch_id: Unique batch identifier (UUID)
            prompt_ids: List of prompt IDs included in the batch
            user_id: User who requested the batch

        Returns:
            Created BrightDataBatch record
        """
        batch = BrightDataBatch(
            batch_id=batch_id,
            user_id=user_id,
            prompt_ids=prompt_ids,
            status=BrightDataBatchStatus.PENDING,
        )
        self._session.add(batch)
        await self._session.flush()
        logger.info(f"Registered batch {batch_id} with {len(prompt_ids)} prompts")
        return batch

    async def get_batch(self, batch_id: str) -> BrightDataBatch | None:
        """Get batch by batch_id.

        Args:
            batch_id: Unique batch identifier

        Returns:
            BrightDataBatch if found, None otherwise
        """
        result = await self._session.execute(
            select(BrightDataBatch).where(BrightDataBatch.batch_id == batch_id)
        )
        return result.scalar_one_or_none()

    async def complete_batch(
        self,
        batch_id: str,
        status: BrightDataBatchStatus,
    ) -> BrightDataBatch | None:
        """Mark batch as completed with given status.

        Args:
            batch_id: Unique batch identifier
            status: Final status (COMPLETED, PARTIAL, FAILED)

        Returns:
            Updated BrightDataBatch if found, None otherwise
        """
        batch = await self.get_batch(batch_id)
        if not batch:
            logger.warning(f"Batch {batch_id} not found for completion")
            return None

        batch.status = status
        batch.completed_at = datetime.now(timezone.utc)
        await self._session.flush()
        logger.info(f"Batch {batch_id} completed with status {status.value}")
        return batch

    async def get_pending_prompt_ids(self, prompt_ids: list[int]) -> set[int]:
        """Get subset of prompt_ids that are already in PENDING batches.

        Used to prevent duplicate requests for prompts already being processed.

        Args:
            prompt_ids: List of prompt IDs to check

        Returns:
            Set of prompt IDs that are already in PENDING batches
        """
        result = await self._session.execute(
            select(BrightDataBatch.prompt_ids).where(
                BrightDataBatch.status == BrightDataBatchStatus.PENDING
            )
        )
        pending_batches = result.scalars().all()

        all_pending: set[int] = set()
        for batch_prompt_ids in pending_batches:
            all_pending.update(batch_prompt_ids)

        return set(prompt_ids) & all_pending
