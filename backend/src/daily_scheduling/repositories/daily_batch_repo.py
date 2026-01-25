"""Repository for DailyScheduleBatch CRUD operations."""

from datetime import date, datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.evals_models import (
    BrightDataBatch,
    BrightDataBatchStatus,
    DailyBatchGroupResult,
    DailyBatchGroupStatus,
    DailyBatchStatus,
    DailyScheduleBatch,
)


class DailyBatchRepository:
    """Repository for DailyScheduleBatch and DailyBatchGroupResult."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_batch_for_date(self, scheduled_date: date) -> DailyScheduleBatch | None:
        """Get batch for a specific date."""
        query = select(DailyScheduleBatch).where(
            DailyScheduleBatch.scheduled_date == scheduled_date
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_batch_by_id(self, batch_id: int) -> DailyScheduleBatch | None:
        """Get batch by ID with group results."""
        query = (
            select(DailyScheduleBatch)
            .options(selectinload(DailyScheduleBatch.group_results))
            .where(DailyScheduleBatch.id == batch_id)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_awaiting_batches(self) -> Sequence[DailyScheduleBatch]:
        """Get all batches in AWAITING status."""
        query = (
            select(DailyScheduleBatch)
            .where(DailyScheduleBatch.status == DailyBatchStatus.AWAITING)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_timed_out_batches(self, as_of: datetime) -> Sequence[DailyScheduleBatch]:
        """Get batches that have exceeded their timeout."""
        query = (
            select(DailyScheduleBatch)
            .where(
                DailyScheduleBatch.status == DailyBatchStatus.AWAITING,
                DailyScheduleBatch.timeout_at <= as_of,
            )
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def create_batch(
        self,
        *,
        scheduled_date: date,
        timeout_at: datetime,
    ) -> DailyScheduleBatch:
        """Create a new daily batch."""
        batch = DailyScheduleBatch(
            scheduled_date=scheduled_date,
            status=DailyBatchStatus.COLLECTING,
            batch_ids=[],
            group_ids=[],
            total_prompts=0,
            prompts_needing_refresh=0,
            prompts_already_fresh=0,
            timeout_at=timeout_at,
        )
        self._session.add(batch)
        await self._session.flush()
        return batch

    async def update_batch_status(
        self,
        batch_id: int,
        status: DailyBatchStatus,
        *,
        completed_at: datetime | None = None,
    ) -> None:
        """Update batch status."""
        values: dict = {"status": status}
        if completed_at:
            values["completed_at"] = completed_at

        stmt = (
            update(DailyScheduleBatch)
            .where(DailyScheduleBatch.id == batch_id)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def set_batch_brightdata_ids(
        self,
        batch_id: int,
        brightdata_batch_ids: list[str],
    ) -> None:
        """Set the BrightData batch IDs for webhook correlation."""
        stmt = (
            update(DailyScheduleBatch)
            .where(DailyScheduleBatch.id == batch_id)
            .values(batch_ids=brightdata_batch_ids)
        )
        await self._session.execute(stmt)

    async def set_batch_group_ids(
        self,
        batch_id: int,
        group_ids: list[int],
    ) -> None:
        """Set the group IDs included in this batch."""
        stmt = (
            update(DailyScheduleBatch)
            .where(DailyScheduleBatch.id == batch_id)
            .values(group_ids=group_ids)
        )
        await self._session.execute(stmt)

    async def set_batch_prompt_stats(
        self,
        batch_id: int,
        *,
        total_prompts: int,
        prompts_needing_refresh: int,
        prompts_already_fresh: int,
    ) -> None:
        """Set prompt statistics for the batch."""
        stmt = (
            update(DailyScheduleBatch)
            .where(DailyScheduleBatch.id == batch_id)
            .values(
                total_prompts=total_prompts,
                prompts_needing_refresh=prompts_needing_refresh,
                prompts_already_fresh=prompts_already_fresh,
            )
        )
        await self._session.execute(stmt)

    async def create_group_result(
        self,
        *,
        batch_id: int,
        group_id: int,
        user_id: str,
        assistant_id: int = 1,
        prompts_in_group: int,
        prompts_needing_refresh: int,
        prompts_already_fresh: int,
        fresh_prompt_selections: dict[int, int] | None,
    ) -> DailyBatchGroupResult:
        """Create a group result record.

        Args:
            batch_id: The daily batch ID
            group_id: The prompt group ID
            user_id: The user ID
            assistant_id: The AI assistant ID for this result
            prompts_in_group: Total prompts in group
            prompts_needing_refresh: Count of prompts needing refresh
            prompts_already_fresh: Count of already fresh prompts
            fresh_prompt_selections: Map of prompt_id -> evaluation_id for fresh prompts
        """
        result = DailyBatchGroupResult(
            batch_id=batch_id,
            group_id=group_id,
            user_id=user_id,
            assistant_id=assistant_id,
            status=DailyBatchGroupStatus.PENDING,
            prompts_in_group=prompts_in_group,
            prompts_needing_refresh=prompts_needing_refresh,
            prompts_already_fresh=prompts_already_fresh,
            fresh_prompt_selections=fresh_prompt_selections,
        )
        self._session.add(result)
        await self._session.flush()
        return result

    async def get_group_results_for_batch(
        self,
        batch_id: int,
    ) -> Sequence[DailyBatchGroupResult]:
        """Get all group results for a batch."""
        query = (
            select(DailyBatchGroupResult)
            .where(DailyBatchGroupResult.batch_id == batch_id)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def update_group_result_status(
        self,
        result_id: int,
        status: DailyBatchGroupStatus,
        *,
        report_id: int | None = None,
    ) -> None:
        """Update group result status."""
        values: dict = {"status": status}
        if report_id is not None:
            values["report_id"] = report_id

        stmt = (
            update(DailyBatchGroupResult)
            .where(DailyBatchGroupResult.id == result_id)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def find_batch_by_brightdata_id(
        self,
        brightdata_batch_id: str,
    ) -> DailyScheduleBatch | None:
        """Find daily batch containing a BrightData batch ID."""
        query = (
            select(DailyScheduleBatch)
            .where(
                DailyScheduleBatch.status == DailyBatchStatus.AWAITING,
                DailyScheduleBatch.batch_ids.contains([brightdata_batch_id]),
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def are_all_brightdata_batches_complete(
        self,
        brightdata_batch_ids: list[str],
    ) -> bool:
        """Check if all BrightData batches are in terminal state."""
        if not brightdata_batch_ids:
            return True

        query = (
            select(BrightDataBatch)
            .where(BrightDataBatch.batch_id.in_(brightdata_batch_ids))
        )
        result = await self._session.execute(query)
        batches = result.scalars().all()

        if len(batches) != len(brightdata_batch_ids):
            return False

        terminal_statuses = {
            BrightDataBatchStatus.COMPLETED,
            BrightDataBatchStatus.PARTIAL,
            BrightDataBatchStatus.FAILED,
        }
        return all(b.status in terminal_statuses for b in batches)
