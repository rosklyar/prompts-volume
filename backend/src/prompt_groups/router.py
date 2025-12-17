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
from src.prompt_groups.services import (
    PromptGroupBindingService,
    PromptGroupService,
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


@router.get("/groups", response_model=GroupListResponse)
async def get_user_groups(
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
):
    """Get all prompt groups for the current user.

    Includes the common group (auto-created if missing) and all named groups.
    Returns groups with prompt counts.
    """
    try:
        groups_with_counts = await group_service.get_user_groups(current_user.id)

        summaries = [
            GroupSummaryResponse(
                id=group.id,
                title=group.title,
                is_common=group.is_common,
                prompt_count=count,
                created_at=group.created_at,
                updated_at=group.updated_at,
            )
            for group, count in groups_with_counts
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
    """Create a new named prompt group.

    The common group is auto-created and cannot be created manually.
    """
    try:
        group = await group_service.create_group(current_user.id, request.title)
        return GroupSummaryResponse(
            id=group.id,
            title=group.title,
            is_common=group.is_common,
            prompt_count=0,
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
    """Get detailed information about a group including all prompts."""
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
        prompts_data = await binding_service.get_group_with_prompts(group)

        return GroupDetailResponse(
            id=group.id,
            title=group.title,
            is_common=group.is_common,
            created_at=group.created_at,
            updated_at=group.updated_at,
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
    """Update a group's title.

    Cannot update the common group.
    """
    try:
        group = await group_service.update_group(
            group_id, current_user.id, request.title
        )

        groups_with_counts = await group_service.get_user_groups(current_user.id)
        count = next((c for g, c in groups_with_counts if g.id == group_id), 0)

        return GroupSummaryResponse(
            id=group.id,
            title=group.title,
            is_common=group.is_common,
            prompt_count=count,
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
    """Delete a prompt group.

    Cannot delete the common group.
    Bindings are cascade deleted.
    """
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
