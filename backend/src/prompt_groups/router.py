"""API router for prompt groups."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.auth.deps import CurrentUser
from src.geography.services.country_resolver import (
    CountryLockedError as ResolverCountryLockedError,
    CountryResolutionError as ResolverCountryResolutionError,
    CountryResolver,
    InvalidCountryError as ResolverInvalidCountryError,
)
from src.prompt_groups.exceptions import (
    CountryLockedError,
    CountryResolutionError,
    InvalidCountryError,
    PromptGroupError,
    to_http_exception,
)
from src.prompt_groups.models.api_models import (
    AddPromptsResultResponse,
    AddPromptsToGroupRequest,
    AvailablePromptResponse,
    AvailablePromptsListResponse,
    CountryInfo,
    CreateGroupRequest,
    GroupDetailResponse,
    GroupListResponse,
    GroupSummaryResponse,
    PromptInGroupResponse,
    RemovePromptsFromGroupRequest,
    UpdateGroupRequest,
)
from src.prompt_groups.models.brand_models import BrandModel, CompetitorModel
from src.prompt_groups.services import (
    PromptGroupBindingService,
    PromptGroupService,
    TopicResolutionService,
    get_country_resolver,
    get_prompt_group_binding_service,
    get_prompt_group_service,
    get_topic_resolution_service,
)

router = APIRouter(prefix="/prompt-groups/api/v1", tags=["prompt-groups"])

PromptGroupServiceDep = Annotated[
    PromptGroupService, Depends(get_prompt_group_service)
]
PromptGroupBindingServiceDep = Annotated[
    PromptGroupBindingService, Depends(get_prompt_group_binding_service)
]
TopicResolutionServiceDep = Annotated[
    TopicResolutionService, Depends(get_topic_resolution_service)
]
CountryResolverDep = Annotated[
    CountryResolver, Depends(get_country_resolver)
]


@router.get("/groups", response_model=GroupListResponse)
async def get_user_groups(
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
):
    """Get all prompt groups for the current user.

    Returns groups with prompt counts, brand, topic, and country info, ordered by creation date.
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
                topic_id=group.topic_id,
                topic_title=group.topic.title if group.topic else None,
                country=CountryInfo(
                    id=group.country.id,
                    name=group.country.name,
                    iso_code=group.country.iso_code,
                ),
                country_locked=group.country_locked,
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
    topic_resolver: TopicResolutionServiceDep,
    country_resolver: CountryResolverDep,
):
    """Create a new prompt group with mandatory country, optional topic binding, brand, and competitors.

    Country resolution:
    - If topic is provided: country is taken from the topic (locked)
    - If no topic: country_id must be provided or will use user's default preference
    """
    try:
        # Resolve topic if provided (validates existing or creates new)
        topic_id = None
        topic_title = None
        if request.topic is not None:
            topic_id = await topic_resolver.resolve(request.topic)
            topic = await topic_resolver.get_topic(topic_id)
            topic_title = topic.title

        # Resolve country (topic > explicit > user preference)
        country_resolution = await country_resolver.resolve_for_group(
            topic_id=topic_id,
            explicit_country_id=request.country_id,
            user_id=current_user.id,
        )

        # Convert Pydantic models to dicts for storage
        brand_data = request.brand.model_dump()
        competitors_data = None
        if request.competitors:
            competitors_data = [c.model_dump() for c in request.competitors]

        group = await group_service.create_group(
            current_user.id,
            request.title,
            brand=brand_data,
            country_resolution=country_resolution,
            topic_id=topic_id,
            competitors=competitors_data,
        )
        return GroupSummaryResponse(
            id=group.id,
            title=group.title,
            prompt_count=0,
            brand_name=request.brand.name,
            competitor_count=len(request.competitors) if request.competitors else 0,
            topic_id=topic_id,
            topic_title=topic_title,
            country=CountryInfo(
                id=group.country.id,
                name=group.country.name,
                iso_code=group.country.iso_code,
            ),
            country_locked=group.country_locked,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
    except ResolverCountryResolutionError as e:
        raise to_http_exception(CountryResolutionError(str(e)))
    except ResolverInvalidCountryError as e:
        raise to_http_exception(InvalidCountryError(e.country_id))
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.get("/groups/{group_id}", response_model=GroupDetailResponse)
async def get_group_details(
    group_id: int,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
    binding_service: PromptGroupBindingServiceDep,
):
    """Get detailed information about a group including topic, country, brand, competitors, and prompts."""
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
            topic_id=group.topic_id,
            topic_title=group.topic.title if group.topic else None,
            topic_description=group.topic.description if group.topic else None,
            country=CountryInfo(
                id=group.country.id,
                name=group.country.name,
                iso_code=group.country.iso_code,
            ),
            country_locked=group.country_locked,
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
    country_resolver: CountryResolverDep,
):
    """Update a group's title, brand, competitors, and/or country (topic cannot be changed).

    Country can only be changed if country_locked is false.
    """
    try:
        # Validate country if provided
        if request.country_id is not None:
            # Get current group to check if locked
            current_group = await group_service.get_by_id_for_user(group_id, current_user.id)
            await country_resolver.validate_country_update(
                request.country_id,
                current_group.country_locked,
                group_id,
            )

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
            competitors=competitors_data,
            country_id=request.country_id,
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
            topic_id=group.topic_id,
            topic_title=group.topic.title if group.topic else None,
            country=CountryInfo(
                id=group.country.id,
                name=group.country.name,
                iso_code=group.country.iso_code,
            ),
            country_locked=group.country_locked,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )
    except ResolverCountryLockedError as e:
        raise to_http_exception(CountryLockedError(e.group_id))
    except ResolverInvalidCountryError as e:
        raise to_http_exception(InvalidCountryError(e.country_id))
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


@router.get(
    "/groups/{group_id}/available-prompts",
    response_model=AvailablePromptsListResponse,
)
async def get_available_prompts(
    group_id: int,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
    binding_service: PromptGroupBindingServiceDep,
):
    """Get prompts from the group's topic that aren't already in the group.

    Returns 404 if the group has no topic binding.
    """
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)
        prompts_data = await binding_service.get_available_prompts_for_group(group)

        return AvailablePromptsListResponse(
            prompts=[AvailablePromptResponse(**p) for p in prompts_data],
            total=len(prompts_data),
        )
    except PromptGroupError as e:
        raise to_http_exception(e)


# Note: Batch analyze/confirm endpoints moved to shared /prompts/api/v1/batch/* endpoints.
# Use POST /prompts/api/v1/batch/analyze and POST /prompts/api/v1/batch/create
# then POST /prompt-groups/api/v1/groups/{id}/prompts to bind.


# ============================================================================
# Schedule endpoints
# ============================================================================


from src.daily_scheduling.models.api_models import ScheduleConfigRequest, ScheduleConfigResponse


@router.put("/groups/{group_id}/schedule", response_model=ScheduleConfigResponse)
async def set_group_schedule(
    group_id: int,
    request: ScheduleConfigRequest,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
):
    """Enable or disable daily scheduled reports for a group.

    When enabled, reports will be generated automatically at 6 AM UTC.
    """
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)

        # Update schedule_enabled
        await group_service.update_schedule(group_id, request.enabled)

        return ScheduleConfigResponse(
            group_id=group_id,
            enabled=request.enabled,
            last_run_at=group.schedule_last_run_at,
        )
    except PromptGroupError as e:
        raise to_http_exception(e)


@router.get("/groups/{group_id}/schedule", response_model=ScheduleConfigResponse)
async def get_group_schedule(
    group_id: int,
    current_user: CurrentUser,
    group_service: PromptGroupServiceDep,
):
    """Get current schedule configuration for a group."""
    try:
        group = await group_service.get_by_id_for_user(group_id, current_user.id)

        return ScheduleConfigResponse(
            group_id=group_id,
            enabled=group.schedule_enabled,
            last_run_at=group.schedule_last_run_at,
        )
    except PromptGroupError as e:
        raise to_http_exception(e)
