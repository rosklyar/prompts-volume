"""API router for execution queue endpoints."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.deps import CurrentUser
from src.config.settings import settings
from src.database.evals_models import ExecutionQueue, ExecutionQueueStatus
from src.database.evals_session import get_evals_session
from src.database.session import get_async_session
from src.execution.models.api_models import (
    CancelExecutionRequest,
    CancelExecutionResponse,
    CompletedItemInfo,
    QueuedItemInfo,
    QueueStatusItem,
    QueueStatusResponse,
    RequestFreshExecutionRequest,
    RequestFreshExecutionResponse,
)
from src.execution.services.execution_queue_service import ExecutionQueueService
from src.execution.services.freshness_service import FreshnessService

router = APIRouter(prefix="/execution/api/v1", tags=["execution"])


def get_execution_queue_service(
    evals_session: AsyncSession = Depends(get_evals_session),
    prompts_session: AsyncSession = Depends(get_async_session),
) -> ExecutionQueueService:
    """Dependency injection for ExecutionQueueService."""
    return ExecutionQueueService(
        evals_session,
        prompts_session,
        settings.evaluation_timeout_hours,
    )


def get_freshness_service() -> FreshnessService:
    """Dependency injection for FreshnessService."""
    return FreshnessService(
        fresh_threshold_hours=settings.freshness_fresh_threshold_hours,
        stale_threshold_hours=settings.freshness_stale_threshold_hours,
    )


@router.post("/request-fresh", response_model=RequestFreshExecutionResponse)
async def request_fresh_execution(
    request: RequestFreshExecutionRequest,
    current_user: CurrentUser,
    queue_service: ExecutionQueueService = Depends(get_execution_queue_service),
    freshness_service: FreshnessService = Depends(get_freshness_service),
) -> RequestFreshExecutionResponse:
    """Request fresh execution for prompts.

    Adds prompts to execution queue. Skips prompts already in queue.
    Returns estimated wait time based on queue size.
    """
    batch_id = str(uuid.uuid4())

    result = await queue_service.add_to_queue(
        prompt_ids=request.prompt_ids,
        user_id=str(current_user.id),
        batch_id=batch_id,
    )

    # Calculate time estimate
    wait_seconds = freshness_service.estimate_wait_time_seconds(result.total_queue_size)
    wait_str = freshness_service.format_wait_time(wait_seconds)
    completion_at = datetime.now(timezone.utc) + timedelta(seconds=wait_seconds)

    # Build item list
    queued_prompt_ids = {e.prompt_id for e in result.queued_entries}
    items: list[QueuedItemInfo] = []

    for prompt_id in request.prompt_ids:
        if prompt_id in queued_prompt_ids:
            items.append(QueuedItemInfo(
                prompt_id=prompt_id,
                status="queued",
                estimated_wait=wait_str,
            ))
        else:
            items.append(QueuedItemInfo(
                prompt_id=prompt_id,
                status="already_pending",
                estimated_wait=None,
            ))

    return RequestFreshExecutionResponse(
        batch_id=batch_id,
        queued_count=result.queued_count,
        already_pending_count=result.skipped_count,
        estimated_total_wait=wait_str,
        estimated_completion_at=completion_at,
        items=items,
    )


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status(
    current_user: CurrentUser,
    queue_service: ExecutionQueueService = Depends(get_execution_queue_service),
    freshness_service: FreshnessService = Depends(get_freshness_service),
    evals_session: AsyncSession = Depends(get_evals_session),
) -> QueueStatusResponse:
    """Get current queue status for the user."""
    from sqlalchemy import select

    user_id = str(current_user.id)

    # Get user's pending/in_progress items
    user_items = await queue_service.get_user_pending_items(user_id)

    pending_items: list[QueueStatusItem] = []
    in_progress_items: list[QueueStatusItem] = []

    global_queue_size = await queue_service.get_pending_count()
    wait_str = freshness_service.format_wait_time(
        freshness_service.estimate_wait_time_seconds(global_queue_size)
    )

    for item in user_items:
        status_item = QueueStatusItem(
            prompt_id=item.prompt_id,
            status=item.status.value,
            requested_at=item.requested_at,
            estimated_wait=wait_str if item.status == ExecutionQueueStatus.PENDING else None,
        )
        if item.status == ExecutionQueueStatus.PENDING:
            pending_items.append(status_item)
        else:
            in_progress_items.append(status_item)

    # Get recently completed (last 24h)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    result = await evals_session.execute(
        select(ExecutionQueue)
        .where(
            ExecutionQueue.requested_by == user_id,
            ExecutionQueue.status == ExecutionQueueStatus.COMPLETED,
            ExecutionQueue.completed_at > cutoff,
        )
        .order_by(ExecutionQueue.completed_at.desc())
        .limit(50)
    )
    completed_entries = result.scalars().all()

    recently_completed = [
        CompletedItemInfo(
            prompt_id=e.prompt_id,
            evaluation_id=e.evaluation_id,
            completed_at=e.completed_at,
        )
        for e in completed_entries
        if e.evaluation_id is not None
    ]

    return QueueStatusResponse(
        pending_items=pending_items,
        in_progress_items=in_progress_items,
        recently_completed=recently_completed,
        total_pending=len(pending_items),
        global_queue_size=global_queue_size,
    )


@router.delete("/queue/{prompt_id}")
async def cancel_execution(
    prompt_id: int,
    current_user: CurrentUser,
    queue_service: ExecutionQueueService = Depends(get_execution_queue_service),
) -> CancelExecutionResponse:
    """Cancel a pending execution request.

    Only cancels PENDING items (not IN_PROGRESS).
    """
    cancelled = await queue_service.cancel_pending(
        prompt_ids=[prompt_id],
        user_id=str(current_user.id),
    )

    if cancelled == 0:
        raise HTTPException(
            status_code=404,
            detail="Pending execution not found or already in progress",
        )

    return CancelExecutionResponse(
        cancelled_count=cancelled,
        prompt_ids=[prompt_id],
    )


@router.post("/queue/cancel", response_model=CancelExecutionResponse)
async def cancel_executions_batch(
    request: CancelExecutionRequest,
    current_user: CurrentUser,
    queue_service: ExecutionQueueService = Depends(get_execution_queue_service),
) -> CancelExecutionResponse:
    """Cancel multiple pending execution requests.

    Only cancels PENDING items (not IN_PROGRESS).
    """
    cancelled = await queue_service.cancel_pending(
        prompt_ids=request.prompt_ids,
        user_id=str(current_user.id),
    )

    return CancelExecutionResponse(
        cancelled_count=cancelled,
        prompt_ids=request.prompt_ids[:cancelled],  # Best effort
    )
