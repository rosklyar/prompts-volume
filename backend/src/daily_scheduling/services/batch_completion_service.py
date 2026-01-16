"""Service for checking batch completion and triggering report generation."""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.daily_scheduling.repositories.daily_batch_repo import DailyBatchRepository
from src.database.evals_models import DailyBatchStatus

logger = logging.getLogger(__name__)


class BatchCompletionService:
    """Checks if daily batch is complete and triggers report generation.

    Single Responsibility: Determine when a batch is ready for reports.

    Called from:
    1. Webhook handler (after BrightData batch completes)
    2. Timeout checker job (for timed-out batches)
    """

    def __init__(
        self,
        evals_session: AsyncSession,
        *,
        batch_repo: DailyBatchRepository | None = None,
    ) -> None:
        self._session = evals_session
        self._batch_repo = batch_repo or DailyBatchRepository(evals_session)

    async def on_brightdata_batch_completed(self, brightdata_batch_id: str) -> bool:
        """Called when a BrightData batch webhook is received.

        Checks if this batch is part of a daily scheduled batch,
        and if all batches are now complete.

        Returns True if report generation should be triggered.
        """
        # Find daily batch containing this BrightData batch ID
        daily_batch = await self._batch_repo.find_batch_by_brightdata_id(
            brightdata_batch_id
        )
        if daily_batch is None:
            # Not part of a scheduled batch
            return False

        return await self._check_and_trigger_completion(daily_batch.id)

    async def check_timed_out_batches(self) -> int:
        """Check for timed-out batches and mark them for report generation.

        Returns count of batches that need report generation.
        """
        now = datetime.now(timezone.utc)
        timed_out = await self._batch_repo.get_timed_out_batches(now)

        triggered_count = 0
        for batch in timed_out:
            try:
                if await self._check_and_trigger_completion(batch.id, is_timeout=True):
                    triggered_count += 1
            except Exception:
                logger.exception(f"Failed to process timed-out batch {batch.id}")

        return triggered_count

    async def _check_and_trigger_completion(
        self,
        batch_id: int,
        *,
        is_timeout: bool = False,
    ) -> bool:
        """Check if batch is ready for completion and trigger if so.

        Returns True if ready for report generation.
        """
        batch = await self._batch_repo.get_batch_by_id(batch_id)
        if batch is None:
            return False

        if batch.status != DailyBatchStatus.AWAITING:
            return False

        now = datetime.now(timezone.utc)

        # Check if all BrightData batches are complete
        all_complete = await self._batch_repo.are_all_brightdata_batches_complete(
            list(batch.batch_ids)
        )

        # Check if timed out
        timed_out = now >= batch.timeout_at

        if not all_complete and not timed_out:
            return False

        # Ready for report generation
        await self._batch_repo.update_batch_status(
            batch_id,
            DailyBatchStatus.GENERATING,
        )
        await self._session.commit()

        logger.info(
            f"Daily batch {batch_id} ready for report generation "
            f"(all_complete={all_complete}, timed_out={timed_out})"
        )

        return True

    async def is_batch_ready_for_reports(self, batch_id: int) -> bool:
        """Check if a batch is in GENERATING status."""
        batch = await self._batch_repo.get_batch_by_id(batch_id)
        return batch is not None and batch.status == DailyBatchStatus.GENERATING
