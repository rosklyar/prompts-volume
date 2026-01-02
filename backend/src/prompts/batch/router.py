"""API router for batch prompts operations."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.auth.deps import CurrentUser
from src.prompts.batch.models import (
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    BatchCreateRequest,
    BatchCreateResponse,
)
from src.prompts.batch.service import BatchPromptsService, get_batch_prompts_service

router = APIRouter(
    prefix="/prompts/api/v1/batch",
    tags=["prompts-batch"],
)

BatchPromptsServiceDep = Annotated[BatchPromptsService, Depends(get_batch_prompts_service)]


@router.post("/analyze", response_model=BatchAnalyzeResponse)
async def analyze_batch(
    request: BatchAnalyzeRequest,
    current_user: CurrentUser,
    batch_service: BatchPromptsServiceDep,
):
    """Analyze prompts for similarity matches.

    Returns top 3 matches for each prompt if similarity >= 90%.
    Marks prompts as duplicates if similarity >= 99.5%.

    Use this endpoint before creating prompts to identify potential duplicates.
    """
    return await batch_service.analyze_batch(request.prompts)


@router.post("/create", response_model=BatchCreateResponse)
async def create_prompts(
    request: BatchCreateRequest,
    current_user: CurrentUser,
    batch_service: BatchPromptsServiceDep,
):
    """Create new prompts via priority pipeline.

    Creates prompts for selected indices only. Each prompt is:
    - Checked for duplicates (>= 99.5% similarity = reuse existing)
    - Created with optional topic_id
    - Added to priority evaluation queue

    Returns IDs of all prompts (new and reused) for binding to groups.
    """
    return await batch_service.create_prompts(
        request.prompts,
        request.selected_indices,
        request.topic_id,
    )
