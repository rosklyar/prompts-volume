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
from src.prompt_groups.services import (
    PromptGroupService,
    get_prompt_group_service,
)
from src.prompt_groups.exceptions import PromptGroupError, to_http_exception

router = APIRouter(
    prefix="/prompts/api/v1/batch",
    tags=["prompts-batch"],
)

BatchPromptsServiceDep = Annotated[BatchPromptsService, Depends(get_batch_prompts_service)]
PromptGroupServiceDep = Annotated[PromptGroupService, Depends(get_prompt_group_service)]


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
    group_service: PromptGroupServiceDep,
):
    """Create new prompts via priority pipeline.

    Creates prompts for selected indices only. Each prompt is:
    - Checked for duplicates (>= 99.5% similarity = reuse existing)
    - Created with topic_id (derived from group_id if provided, else explicit topic_id)
    - Added to priority evaluation queue

    Returns IDs of all prompts (new and reused) for binding to groups.
    """
    # Resolve effective topic_id
    effective_topic_id = request.topic_id
    if request.group_id is not None:
        try:
            group = await group_service.get_by_id_for_user(
                request.group_id, current_user.id
            )
            effective_topic_id = group.topic_id
        except PromptGroupError as e:
            raise to_http_exception(e)

    return await batch_service.create_prompts(
        request.prompts,
        request.selected_indices,
        effective_topic_id,
    )
