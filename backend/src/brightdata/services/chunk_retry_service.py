"""Service for managing chunk-level retries of BrightData batches."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.brightdata.services.batch_service import BrightDataBatchService
from src.brightdata.services.brightdata_service import BrightDataService
from src.config.settings import settings
from src.database.evals_models import BrightDataBatch
from src.database.models import Country, Prompt

logger = logging.getLogger(__name__)


class ChunkRetryService:
    """Service for managing chunk-level retries.

    Checks for timed-out PENDING chunks and either retries them
    or marks them as FAILED if max retries exceeded.

    The chunk retry mechanism naturally creates a ~6h max wait window:
    - First attempt: 2 hours
    - First retry: 2 hours
    - Second retry: 2 hours
    - Total: 6 hours max
    """

    def __init__(
        self,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
        *,
        batch_service: BrightDataBatchService | None = None,
        brightdata_service: BrightDataService | None = None,
    ) -> None:
        self._prompts_session = prompts_session
        self._evals_session = evals_session
        self._batch_service = batch_service or BrightDataBatchService(evals_session)
        self._brightdata_service = brightdata_service

    async def check_and_retry_timed_out_chunks(self) -> tuple[int, int]:
        """Check for timed-out chunks and retry or fail them.

        Returns:
            Tuple of (retried_count, failed_count)
        """
        timed_out_batches = await self._batch_service.get_timed_out_pending_batches(
            chunk_timeout_hours=settings.chunk_timeout_hours
        )

        if not timed_out_batches:
            return 0, 0

        retried_count = 0
        failed_count = 0

        for batch in timed_out_batches:
            try:
                if batch.retry_count < batch.max_retries:
                    await self._retry_chunk(batch)
                    retried_count += 1
                else:
                    await self._mark_chunk_failed(batch)
                    failed_count += 1
            except Exception:
                logger.exception(f"Failed to process timed-out chunk {batch.batch_id}")

        if retried_count > 0 or failed_count > 0:
            await self._evals_session.commit()
            logger.info(
                f"Chunk retry check: {retried_count} retried, {failed_count} failed"
            )

        return retried_count, failed_count

    async def _retry_chunk(self, batch: BrightDataBatch) -> None:
        """Re-submit a chunk to BrightData.

        Args:
            batch: The batch to retry
        """
        # Increment retry count and update timestamp first
        await self._batch_service.increment_retry_and_update_timestamp(batch)

        # Re-trigger BrightData if service is available
        if self._brightdata_service:
            # Fetch prompt texts for the retry
            prompts = await self._fetch_prompts(batch.prompt_ids)
            if not prompts:
                logger.warning(
                    f"No prompt texts found for batch {batch.batch_id}, skipping retry"
                )
                return

            # Fetch country ISO code
            country_iso_code = await self._fetch_country_iso_code(batch.country_id)
            if not country_iso_code:
                logger.warning(
                    f"Country {batch.country_id} not found for batch {batch.batch_id}, "
                    "using default"
                )
                country_iso_code = settings.brightdata_default_country

            await self._brightdata_service.re_trigger_batch(
                batch,
                prompts,
                country_iso_code,
            )
            logger.info(
                f"Retried batch {batch.batch_id} (retry #{batch.retry_count})"
            )
        else:
            logger.warning(
                f"BrightData service not available for retry of batch {batch.batch_id}"
            )

    async def _mark_chunk_failed(self, batch: BrightDataBatch) -> None:
        """Mark a chunk as FAILED when max retries exceeded.

        Args:
            batch: The batch to mark as failed
        """
        await self._batch_service.mark_batch_failed(batch)
        logger.warning(
            f"Batch {batch.batch_id} marked FAILED after {batch.retry_count} retries "
            f"(prompt_ids={batch.prompt_ids})"
        )

    async def _fetch_prompts(self, prompt_ids: list[int]) -> dict[int, str]:
        """Fetch prompt texts from the database.

        Args:
            prompt_ids: List of prompt IDs to fetch

        Returns:
            Dict mapping prompt_id to prompt_text
        """
        if not prompt_ids:
            return {}

        result = await self._prompts_session.execute(
            select(Prompt.id, Prompt.prompt_text).where(Prompt.id.in_(prompt_ids))
        )
        return {row[0]: row[1] for row in result.all()}

    async def _fetch_country_iso_code(self, country_id: int) -> str | None:
        """Fetch country ISO code from the database.

        Args:
            country_id: Country ID to fetch

        Returns:
            ISO code string or None if not found
        """
        result = await self._prompts_session.execute(
            select(Country.iso_code).where(Country.id == country_id)
        )
        row = result.first()
        return row[0] if row else None
