"""API router for prompt groups."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.auth.deps import CurrentUser
from src.prompt_groups.exceptions import PromptGroupError, to_http_exception
from src.prompt_groups.models.api_models import (
    AddPromptsResultResponse,
    AddPromptsToGroupRequest,
    CreateGroupRequest,
    GroupDetailResponse,
    GroupListResponse,
    GroupSummaryResponse,
    PromptInGroupResponse,
    RemovePromptsFromGroupRequest,
    UpdateGroupRequest,
)
from src.prompt_groups.models.batch_models import (
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    BatchConfirmRequest,
    BatchConfirmResponse,
)
from src.prompt_groups.models.brand_models import BrandModel, CompetitorModel
from src.prompt_groups.services import (
    BatchUploadService,
    PromptGroupBindingService,
    PromptGroupService,
    get_batch_upload_service,
    get_prompt_group_binding_service,
    get_prompt_group_service,
)

router = APIRouter(prefix="/prompt-groups/api/v1", tags=["prompt-groups"])

PromptGroupServiceDep = Annotated[
    PromptGroupService, Depends(get_prompt_group_service)
]
PromptGroupBindingServiceDep = Annotated[
    PromptGroupBindingService, Depends(get_prompt_group_binding_service)
]
BatchUploadServiceDep = Annotated[
    BatchUploadService, Depends(get_batch_upload_service)
]


@router.get("/groups", response_model=GroupListResponse)
async def get_user_groups(
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
):
    """Get all prompt groups for the current user.

    Returns groups with prompt counts and brand info, ordered by creation date.
    """
    try:
        groups_with_counts = await group_service.get_user_groups(current_user.id)

        summaries = [
            GroupSummaryResponse(
                id=group.id,
                title=group.title,
                prompt_count=prompt_count,
                brand_name=group.brand.get("name", "") if group.brand else "",
                competitor_count=len(group.competitors) if group.competitors else 0,
                created_at=group.created_at,
                updated_at=group.updated_at,
            )
            for group, prompt_count in groups_with_counts
        ]

        return GroupListResponse(groups=summaries, total=len(summaries))
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.post(
    "/groups", response_model=GroupSummaryResponse, status_code=status.HTTP_201_CREATED
)
async def create_group(
    request: CreateGroupRequest,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
):
    """Create a new prompt group with brand and optional competitors."""
    try:
        # Convert Pydantic models to dicts for storage
        brand_data = request.brand.model_dump()
        competitors_data = None
        if request.competitors:
            competitors_data = [c.model_dump() for c in request.competitors]

        group = await group_service.create_group(
            current_user.id,
            request.title,
            brand=brand_data,
            competitors=competitors_data
        )
        return GroupSummaryResponse(
            id=group.id,
            title=group.title,
            prompt_count=0,
            brand_name=request.brand.name,
            competitor_count=len(request.competitors) if request.competitors else 0,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.get("/groups/{group_id}", response_model=GroupDetailResponse)
async def get_group_details(
    group_id: int,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
    binding_service: PromptGroupBindingServiceDep,
):
    """Get detailed information about a group including brand, competitors, and prompts."""
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
        prompts_data = await binding_service.get_group_with_prompts(group)

        # Convert brand from JSONB to Pydantic model
        brand = BrandModel(**group.brand)

        # Convert competitors from JSONB to Pydantic models
        competitors = []
        if group.competitors:
            competitors = [CompetitorModel(**c) for c in group.competitors]

        return GroupDetailResponse(
            id=group.id,
            title=group.title,
            created_at=group.created_at,
            updated_at=group.updated_at,
            brand=brand,
            competitors=competitors,
            prompts=[PromptInGroupResponse(**p) for p in prompts_data],
        )
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.patch("/groups/{group_id}", response_model=GroupSummaryResponse)
async def update_group(
    group_id: int,
    request: UpdateGroupRequest,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
):
    """Update a group's title, brand, and/or competitors."""
    try:
        # Convert models to dict format if provided
        brand_data = None
        if request.brand is not None:
            brand_data = request.brand.model_dump()

        competitors_data = None
        if request.competitors is not None:
            competitors_data = [c.model_dump() for c in request.competitors]

        group = await group_service.update_group(
            group_id,
            current_user.id,
            title=request.title,
            brand=brand_data,
            competitors=competitors_data
        )

        # Fetch prompt count by getting user groups
        groups_with_counts = await group_service.get_user_groups(current_user.id)
        prompt_count = next(
            (pc for g, pc in groups_with_counts if g.id == group_id), 0
        )

        return GroupSummaryResponse(
            id=group.id,
            title=group.title,
            prompt_count=prompt_count,
            brand_name=group.brand.get("name", "") if group.brand else "",
            competitor_count=len(group.competitors) if group.competitors else 0,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
):
    """Delete a prompt group. Bindings are cascade deleted."""
    try:
        await group_service.delete_group(group_id, current_user.id)
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.post("/groups/{group_id}/prompts", response_model=AddPromptsResultResponse)
async def add_prompts_to_group(
    group_id: int,
    request: AddPromptsToGroupRequest,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
    binding_service: PromptGroupBindingServiceDep,
):
    """Add prompts to a group.

    Prompts already in the group are skipped.
    """
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)

        bindings, skipped = await binding_service.add_prompts_to_group(
            group=group,
            prompt_ids=request.prompt_ids,
        )

        prompts_data = await binding_service.get_group_with_prompts(group)
        binding_ids = {b.id for b in bindings}
        new_prompts = [p for p in prompts_data if p["binding_id"] in binding_ids]

        return AddPromptsResultResponse(
            added_count=len(bindings),
            skipped_count=skipped,
            bindings=[PromptInGroupResponse(**p) for p in new_prompts],
        )
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.delete("/groups/{group_id}/prompts")
async def remove_prompts_from_group(
    group_id: int,
    request: RemovePromptsFromGroupRequest,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
    binding_service: PromptGroupBindingServiceDep,
):
    """Remove prompts from a group."""
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
        removed_count = await binding_service.remove_prompts_from_group(
            group, request.prompt_ids
        )
        return {"removed_count": removed_count}
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.post("/groups/{group_id}/batch/analyze", response_model=BatchAnalyzeResponse)
async def analyze_batch(
    group_id: int,
    request: BatchAnalyzeRequest,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
    batch_service: BatchUploadServiceDep,
):
    """Analyze batch of prompts and find similarity matches.

    For each prompt in the batch, returns top 3 similar prompts from the database
    (if similarity >= 0.75 threshold). Use this to preview matches before confirming.
    """
    try:
        # Verify group ownership
        await group_service.get_by_id_for_user(group_id, current_user.id)

        # Analyze batch
        return await batch_service.analyze_batch(request.prompts)
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.post("/groups/{group_id}/batch/confirm", response_model=BatchConfirmResponse)
async def confirm_batch(
    group_id: int,
    request: BatchConfirmRequest,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
    batch_service: BatchUploadServiceDep,
):
    """Confirm batch selections and add prompts to group.

    For each selection:
    - If use_existing=True: binds the selected existing prompt to the group
    - If use_existing=False: creates a new prompt via priority pipeline and binds to group

    New prompts go through deduplication (99% similarity check) and are added to
    the evaluation priority queue.
    """
    try:
        # Verify group ownership
        group = await group_service.get_by_id_for_user(group_id, current_user.id)

        # Process batch
        return await batch_service.confirm_batch(group, request)
    except PromptGroupError as e:
        raise to_http_exception(e)
