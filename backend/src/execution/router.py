"""API router for execution endpoints."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.deps import CurrentUser
from src.brightdata.services.batch_service import BrightDataBatchService
from src.brightdata.service_factory import create_brightdata_service
from src.config.settings import settings
from src.database.evals_session import get_evals_session
from src.database.session import get_async_session
from src.execution.models.api_models import (
    QueuedItemInfo,
    RequestFreshExecutionRequest,
    RequestFreshExecutionResponse,
)
from src.geography.services.country_service import CountryService
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


@router.post("/request-fresh", response_model=RequestFreshExecutionResponse)
async def request_fresh_execution(
    request: RequestFreshExecutionRequest,
    current_user: CurrentUser,
    prompt_service: PromptService = Depends(get_prompt_service),
    prompts_session: AsyncSession = Depends(get_async_session),
    evals_session: AsyncSession = Depends(get_evals_session),
) -> RequestFreshExecutionResponse:
    """Request fresh execution for prompts via Bright Data.

    Triggers Bright Data scraper for the specified prompts.
    Results are delivered via webhook when scraping completes.

    Prompts already in PENDING batches are skipped to avoid duplicates.
    Stale PENDING batches (older than eviction timeout) are evicted first.
    Prompts are processed in configurable chunk sizes.
    """
    # Validate and get country
    country_service = CountryService(prompts_session)
    country = await country_service.get_by_id(request.country_id)
    if not country:
        raise HTTPException(status_code=400, detail=f"Invalid country_id: {request.country_id}")

    batch_service = BrightDataBatchService(evals_session)

    # Evict stale PENDING batches before checking for pending prompts
    evicted_batches = await batch_service.evict_stale_batches(
        eviction_timeout_hours=settings.brightdata_batch_eviction_timeout_hours
    )
    if evicted_batches:
        logger.info(f"Evicted {len(evicted_batches)} stale batches before processing request")

    # Check for prompts already in PENDING batches (after eviction)
    already_pending = await batch_service.get_pending_prompt_ids(request.prompt_ids, assistant_id=request.assistant_id)
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

    # Trigger Bright Data with chunked batches
    brightdata_service = create_brightdata_service(evals_session)
    prompt_dict = await prompt_service.get_by_ids(new_prompt_ids)
    batch_ids = await brightdata_service.trigger_batches_chunked(
        prompts=prompt_dict,
        user_id=str(current_user.id),
        country_id=request.country_id,
        country_iso_code=country.iso_code,
        assistant_id=request.assistant_id,
    )

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
