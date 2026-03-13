"""API router for keyword inspiration endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.deps import CurrentUser, SessionDep
from src.businessdomain.services.business_domain_service import BusinessDomainService
from src.geography.services.country_service import CountryService
from src.keyword_inspiration.models.api_models import (
    ClusterKeywordsResponse,
    ConfirmGroupsRequest,
    CreateGroupsResponse,
    DiscoverClustersRequest,
    GeneratePromptsRequest,
    GeneratePromptsResponse,
)
from src.keyword_inspiration.services import (
    ClusterScoringService,
    InspirationOrchestrator,
    get_cluster_scoring_service,
    get_inspiration_orchestrator,
)

router = APIRouter(prefix="/keyword-inspiration/api/v1", tags=["keyword-inspiration"])

ClusterScoringServiceDep = Annotated[
    ClusterScoringService, Depends(get_cluster_scoring_service)
]
InspirationOrchestratorDep = Annotated[
    InspirationOrchestrator, Depends(get_inspiration_orchestrator)
]


@router.post("/discover-clusters", response_model=ClusterKeywordsResponse)
async def discover_clusters(
    request: DiscoverClustersRequest,
    current_user: CurrentUser,
    service: ClusterScoringServiceDep,
    session: SessionDep,
):
    """Step 1: Fetch keywords (cached) + cluster + return top clusters."""
    country = await CountryService(session).get_by_iso_code(request.country_code)
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Country not found for code: {request.country_code}",
        )

    keyword_filter_config = None
    if request.business_domain_id is not None:
        bd = await BusinessDomainService(session).get_by_id(request.business_domain_id)
        if bd:
            keyword_filter_config = bd.keyword_filter_config

    return await service.discover_clusters(
        domains=request.domains,
        country_code=request.country_code,
        country_name=country.name,
        language_name=request.language_name,
        brand_names=request.brand_names,
        keyword_filter_config=keyword_filter_config,
    )


@router.post("/generate-prompts", response_model=GeneratePromptsResponse)
async def generate_prompts(
    request: GeneratePromptsRequest,
    current_user: CurrentUser,
    orchestrator: InspirationOrchestratorDep,
):
    """Step 2: Generate prompt previews from selected clusters. No DB writes."""
    return await orchestrator.generate_prompts_preview(
        request, business_domain_name=request.business_domain
    )


@router.post(
    "/create-groups",
    response_model=CreateGroupsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_groups(
    request: ConfirmGroupsRequest,
    current_user: CurrentUser,
    orchestrator: InspirationOrchestratorDep,
):
    """Step 3: Confirm selection, create groups with only chosen prompts."""
    return await orchestrator.confirm_and_create_groups(request, user_id=current_user.id)
