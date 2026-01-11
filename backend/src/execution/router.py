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
    """
    # Check for prompts already in PENDING batches
    batch_service = BrightDataBatchService(evals_session)
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
    batch_id = str(uuid.uuid4())
    total_seconds = len(new_prompt_ids) * settings.brightdata_seconds_per_prompt
    wait_str = _format_wait_time(total_seconds)
    completion_at = datetime.now(timezone.utc) + timedelta(seconds=total_seconds)

    # Trigger Bright Data
    prompt_dict = await prompt_service.get_by_ids(new_prompt_ids)
    brightdata_service = get_brightdata_service(evals_session)
    await brightdata_service.trigger_batch(batch_id, prompt_dict, str(current_user.id))
    await evals_session.commit()

    # Build response items
    items: list[QueuedItemInfo] = []
    for prompt_id in request.prompt_ids:
        if prompt_id in already_pending:
            items.append(
                QueuedItemInfo(prompt_id=prompt_id, status="already_pending", estimated_wait=None)
            )
        else:
            items.append(
                QueuedItemInfo(prompt_id=prompt_id, status="queued", estimated_wait=wait_str)
            )

    return RequestFreshExecutionResponse(
        batch_id=batch_id,
        queued_count=len(new_prompt_ids),
        already_pending_count=len(already_pending),
        estimated_total_wait=wait_str,
        estimated_completion_at=completion_at,
        items=items,
    )
