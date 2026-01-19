"""Repository for ReportRequest CRUD operations."""

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.evals_models import (
    BrightDataBatch,
    BrightDataBatchStatus,
    ReportRequest,
    ReportRequestStatus,
)


class ReportRequestRepository:
    """Repository for ReportRequest operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        group_id: int,
        user_id: str,
        assistant_id: int,
        batch_ids: list[str],
        fresh_prompt_selections: dict[int, int] | None,
        total_prompts: int,
        prompts_fresh_at_request: int,
        prompts_requested: int,
        timeout_at: datetime,
        daily_batch_id: int | None = None,
    ) -> ReportRequest:
        """Create a new report request."""
        request = ReportRequest(
            group_id=group_id,
            user_id=user_id,
            assistant_id=assistant_id,
            status=ReportRequestStatus.AWAITING,
            batch_ids=batch_ids,
            fresh_prompt_selections=fresh_prompt_selections,
            total_prompts=total_prompts,
            prompts_fresh_at_request=prompts_fresh_at_request,
            prompts_requested=prompts_requested,
            timeout_at=timeout_at,
            daily_batch_id=daily_batch_id,
        )
        self._session.add(request)
        await self._session.flush()
        return request

    async def get_by_id(self, request_id: int) -> ReportRequest | None:
        """Get a report request by ID."""
        query = select(ReportRequest).where(ReportRequest.id == request_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_pending_for_group(
        self,
        group_id: int,
        user_id: str,
    ) -> ReportRequest | None:
        """Get the pending (non-terminal) report request for a group.

        Returns the most recent request that is still in progress.
        """
        active_statuses = [
            ReportRequestStatus.AWAITING,
            ReportRequestStatus.READY,
            ReportRequestStatus.GENERATING,
        ]
        query = (
            select(ReportRequest)
            .where(
                ReportRequest.group_id == group_id,
                ReportRequest.user_id == user_id,
                ReportRequest.status.in_(active_statuses),
            )
            .order_by(ReportRequest.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def find_by_brightdata_id(
        self,
        brightdata_batch_id: str,
    ) -> ReportRequest | None:
        """Find report request containing a BrightData batch ID."""
        query = (
            select(ReportRequest)
            .where(
                ReportRequest.status == ReportRequestStatus.AWAITING,
                ReportRequest.batch_ids.contains([brightdata_batch_id]),
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_awaiting_requests(self) -> Sequence[ReportRequest]:
        """Get all requests in AWAITING status."""
        query = (
            select(ReportRequest)
            .where(ReportRequest.status == ReportRequestStatus.AWAITING)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_timed_out_requests(self, as_of: datetime) -> Sequence[ReportRequest]:
        """Get requests that have exceeded their timeout."""
        query = (
            select(ReportRequest)
            .where(
                ReportRequest.status == ReportRequestStatus.AWAITING,
                ReportRequest.timeout_at <= as_of,
            )
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def get_ready_requests(self) -> Sequence[ReportRequest]:
        """Get requests in READY status awaiting report generation."""
        query = (
            select(ReportRequest)
            .where(ReportRequest.status == ReportRequestStatus.READY)
        )
        result = await self._session.execute(query)
        return result.scalars().all()

    async def update_status(
        self,
        request_id: int,
        status: ReportRequestStatus,
        *,
        completed_at: datetime | None = None,
        report_id: int | None = None,
    ) -> None:
        """Update request status."""
        values: dict = {"status": status}
        if completed_at is not None:
            values["completed_at"] = completed_at
        if report_id is not None:
            values["report_id"] = report_id

        stmt = (
            update(ReportRequest)
            .where(ReportRequest.id == request_id)
            .values(**values)
        )
        await self._session.execute(stmt)

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
        batches = list(result.scalars().all())

        if len(batches) != len(brightdata_batch_ids):
            return False

        terminal_statuses = {
            BrightDataBatchStatus.COMPLETED,
            BrightDataBatchStatus.PARTIAL,
            BrightDataBatchStatus.FAILED,
        }
        return all(b.status in terminal_statuses for b in batches)

    async def cancel_request(self, request_id: int) -> bool:
        """Cancel a pending report request.

        Returns True if cancelled, False if already completed/cancelled.
        """
        request = await self.get_by_id(request_id)
        if request is None:
            return False

        if request.status in (
            ReportRequestStatus.COMPLETED,
            ReportRequestStatus.CANCELLED,
            ReportRequestStatus.TIMED_OUT,
        ):
            return False

        await self.update_status(
            request_id,
            ReportRequestStatus.CANCELLED,
            completed_at=datetime.now(timezone.utc),
        )
        return True
