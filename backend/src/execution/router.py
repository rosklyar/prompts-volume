"""API router for execution endpoints."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.deps import CurrentUser
from src.brightdata.services.batch_service import BrightDataBatchService
from src.brightdata.services.brightdata_service import get_brightdata_service
from src.config.settings import settings
from src.database.evals_session import get_evals_session
from src.execution.models.api_models import (
    QueuedItemInfo,
    RequestFreshExecutionRequest,
    RequestFreshExecutionResponse,
)
from src.prompts.services.prompt_service import PromptService, get_prompt_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/execution/api/v1", tags=["execution"])


def _format_wait_time(seconds: int) -> str:
    """Format seconds into human-readable wait time."""
    minutes = seconds // 60
    if minutes < 1:
        return "~1 minute"
    elif minutes < 60:
        return f"~{minutes} minutes"
    else:
        hours = minutes // 60
        return f"~{hours} hour{'s' if hours > 1 else ''}"


def _chunk_list(lst: list, chunk_size: int) -> list[list]:
    """Split a list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


@router.post("/request-fresh", response_model=RequestFreshExecutionResponse)
async def request_fresh_execution(
    request: RequestFreshExecutionRequest,
    current_user: CurrentUser,
    prompt_service: PromptService = Depends(get_prompt_service),
    evals_session: AsyncSession = Depends(get_evals_session),
) -> RequestFreshExecutionResponse:
    """Request fresh execution for prompts via Bright Data.

    Triggers Bright Data scraper for the specified prompts.
    Results are delivered via webhook when scraping completes.

    Prompts already in PENDING batches are skipped to avoid duplicates.
    Stale PENDING batches (older than eviction timeout) are evicted first.
    Prompts are processed in configurable chunk sizes.
    """
    batch_service = BrightDataBatchService(evals_session)

    # Evict stale PENDING batches before checking for pending prompts
    evicted_batches = await batch_service.evict_stale_batches(
        eviction_timeout_hours=settings.brightdata_batch_eviction_timeout_hours
    )
    if evicted_batches:
        logger.info(f"Evicted {len(evicted_batches)} stale batches before processing request")

    # Check for prompts already in PENDING batches (after eviction)
    already_pending = await batch_service.get_pending_prompt_ids(request.prompt_ids)
    new_prompt_ids = [p for p in request.prompt_ids if p not in already_pending]

    if not new_prompt_ids:
        # All prompts already pending - nothing to do
        return RequestFreshExecutionResponse(
            batch_id=None,
            queued_count=0,
            already_pending_count=len(request.prompt_ids),
            estimated_total_wait=None,
            estimated_completion_at=None,
            items=[
                QueuedItemInfo(prompt_id=p, status="already_pending", estimated_wait=None)
                for p in request.prompt_ids
            ],
        )

    # Calculate time estimate
    total_seconds = len(new_prompt_ids) * settings.brightdata_seconds_per_prompt
    wait_str = _format_wait_time(total_seconds)
    completion_at = datetime.now(timezone.utc) + timedelta(seconds=total_seconds)

    # Process prompts in chunks
    chunk_size = settings.brightdata_chunk_size
    prompt_id_chunks = _chunk_list(new_prompt_ids, chunk_size)
    batch_ids: list[str] = []

    brightdata_service = get_brightdata_service(evals_session)

    for chunk in prompt_id_chunks:
        batch_id = str(uuid.uuid4())
        batch_ids.append(batch_id)

        # Trigger Bright Data with selected assistant for this chunk
        prompt_dict = await prompt_service.get_by_ids(chunk)
        await brightdata_service.trigger_batch(
            batch_id,
            prompt_dict,
            str(current_user.id),
            assistant_id=request.assistant_id,
        )
        logger.info(f"Triggered batch {batch_id} with {len(chunk)} prompts")

    await evals_session.commit()

    # Build response items
    items = [
        QueuedItemInfo(
            prompt_id=prompt_id,
            status="already_pending" if prompt_id in already_pending else "queued",
            estimated_wait=None if prompt_id in already_pending else wait_str,
        )
        for prompt_id in request.prompt_ids
    ]

    # Return first batch_id for backward compatibility (multiple batches created)
    primary_batch_id = batch_ids[0] if batch_ids else None

    return RequestFreshExecutionResponse(
        batch_id=primary_batch_id,
        queued_count=len(new_prompt_ids),
        already_pending_count=len(already_pending),
        estimated_total_wait=wait_str,
        estimated_completion_at=completion_at,
        items=items,
    )
