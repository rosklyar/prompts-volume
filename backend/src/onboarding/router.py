"""API router for onboarding and user preferences."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from src.approval.policies import ApprovalPolicy, get_approval_policy
from src.auth.deps import CurrentUser, UsersSessionDep, SessionDep
from src.embeddings.embeddings_service import EmbeddingsService, get_embeddings_service
from src.geography.services import CountryService, get_country_service
from src.geography.services.country_resolver import CountryResolution
from src.gsc.deps import get_oauth_service, get_token_manager, get_valid_access_token
from src.gsc.exceptions import GSCError, GSCTokenRefreshError
from src.gsc.models import (
    GeneratedPromptResponse,
    GSCFetchKeywordsRequest,
    GSCFetchKeywordsResponse,
    GSCGeneratePromptsRequest,
    GSCGeneratePromptsResponse,
    GSCKeywordExtractRequest,
    GSCKeywordExtractResponse,
    GSCKeywordResponse,
    GSCOnboardingCreateRequest,
    GSCOnboardingCreateResponse,
    GSCPropertyMatchRequest,
    GSCPropertyMatchResponse,
)
from src.businessdomain.services.business_domain_service import BusinessDomainService
from src.keyword_inspiration.services.prompts_generator_service import get_prompts_generator_service
from src.gsc.repository import GSCCredentialRepository
from src.gsc.services import (
    GSCClient,
    KeywordExtractor,
    MinWordCountFilter,
    NoOpFilter,
    PropertyMatcher,
)
from src.gsc.services.oauth_service import OAuthService
from src.gsc.services.token_manager import TokenManager
from src.onboarding.exceptions import OnboardingError, to_http_exception
from src.onboarding.models.api_models import (
    CompleteOnboardingRequest,
    DiscoverCompetitorsRequest,
    DiscoverCompetitorsResponse,
    DiscoveredCompetitorResponse,
    OnboardingStatusResponse,
    SavePreferencesRequest,
    UserPreferencesResponse,
)
from src.onboarding.services import OnboardingServiceDep, PreferencesServiceDep
from src.onboarding.services.competitor_discovery.deps import CompetitorDiscoveryServiceDep
from src.prompt_groups.models.brand_models import BrandModel, CompetitorModel
from src.prompt_groups.services.prompt_group_binding_service import PromptGroupBindingService
from src.prompt_groups.services.prompt_group_service import PromptGroupService
from src.prompts.services.prompt_service import PromptService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding/api/v1", tags=["onboarding"])


@router.get("/favicon")
async def get_favicon(domain: str):
    """Return a Google Favicon URL for the given domain.

    Normalizes the domain (strips protocol, lowercases, trims slashes)
    and constructs a favicon URL via Google's public favicon service.
    No auth required — favicon URLs are public info.
    """
    # Normalize: strip protocol, lowercase, trim slashes
    normalized = domain.strip().lower()
    for prefix in ("https://", "http://", "//"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    normalized = normalized.strip("/")

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="domain is required",
        )

    return {"url": f"https://www.google.com/s2/favicons?domain={normalized}&sz=64"}


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: CurrentUser,
    onboarding_service: OnboardingServiceDep,
):
    """Check if current user has completed onboarding.

    Returns completion status and whether preferences exist.
    Onboarding is required and cannot be skipped.
    """
    try:
        status_data = await onboarding_service.get_onboarding_status(current_user.id)
        return OnboardingStatusResponse(**status_data)
    except OnboardingError as e:
        raise to_http_exception(e)


@router.post(
    "/complete",
    response_model=UserPreferencesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def complete_onboarding(
    request: CompleteOnboardingRequest,
    current_user: CurrentUser,
    onboarding_service: OnboardingServiceDep,
):
    """Complete onboarding with brand/competitor preferences.

    Sets default brand and competitors for future group creation.
    Marks onboarding as completed.
    """
    try:
        # Convert Pydantic models to dicts for storage
        brand_data = request.default_brand.model_dump()
        competitors_data = None
        if request.default_competitors:
            competitors_data = [c.model_dump() for c in request.default_competitors]

        prefs = await onboarding_service.complete_onboarding(
            current_user.id,
            default_country_id=request.default_country_id,
            default_business_domain_id=request.default_business_domain_id,
            default_brand=brand_data,
            default_competitors=competitors_data,
        )

        # Build response
        return _build_preferences_response(prefs)
    except OnboardingError as e:
        raise to_http_exception(e)


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(
    current_user: CurrentUser,
    onboarding_service: OnboardingServiceDep,
):
    """Get user's default preferences for group creation.

    Returns brand and competitor defaults if set.
    Frontend uses this to prefill group creation forms.
    """
    try:
        prefs = await onboarding_service.get_preferences(current_user.id)
        return _build_preferences_response(prefs)
    except OnboardingError as e:
        raise to_http_exception(e)


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    request: SavePreferencesRequest,
    current_user: CurrentUser,
    onboarding_service: OnboardingServiceDep,
):
    """Update user's default preferences.

    Can be called anytime to modify brand/competitor defaults.
    This endpoint is used from the settings page.
    """
    try:
        # Convert Pydantic models to dicts for storage
        brand_data = request.default_brand.model_dump()
        competitors_data = None
        if request.default_competitors:
            competitors_data = [c.model_dump() for c in request.default_competitors]

        prefs = await onboarding_service.update_preferences(
            current_user.id,
            default_country_id=request.default_country_id,
            default_business_domain_id=request.default_business_domain_id,
            default_brand=brand_data,
            default_competitors=competitors_data,
        )

        return _build_preferences_response(prefs)
    except OnboardingError as e:
        raise to_http_exception(e)


def _build_preferences_response(prefs) -> UserPreferencesResponse:
    """Build UserPreferencesResponse from UserPreferences model."""
    # Handle None case (new user with no preferences - shouldn't happen after onboarding)
    if prefs is None or prefs.default_country_id is None:
        # Return a minimal response for users who haven't completed onboarding
        # This should only happen for legacy users
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding not completed. Please complete onboarding first.",
        )

    # Convert JSONB to Pydantic models
    brand = None
    if prefs.default_brand:
        brand = BrandModel(**prefs.default_brand)

    competitors = []
    if prefs.default_competitors:
        competitors = [CompetitorModel(**c) for c in prefs.default_competitors]

    return UserPreferencesResponse(
        default_country_id=prefs.default_country_id,
        default_business_domain_id=prefs.default_business_domain_id,
        default_brand=brand,
        default_competitors=competitors,
        onboarding_status=OnboardingStatusResponse(
            is_completed=prefs.onboarding_completed_at is not None,
            completed_at=prefs.onboarding_completed_at,
            has_preferences=prefs.default_brand is not None,
        ),
    )


# ===== Competitor Discovery Endpoints =====


@router.post("/discover-competitors", response_model=DiscoverCompetitorsResponse)
async def discover_competitors(
    request: DiscoverCompetitorsRequest,
    current_user: CurrentUser,
    prompts_session: SessionDep,
    competitor_service: CompetitorDiscoveryServiceDep,
):
    """Discover competitors using AI-powered web search.

    Uses the brand name and domain to find relevant competitors
    in the specified country. Returns competitors with name variations
    for brand matching.
    """
    # Get country for localized search
    country_service = get_country_service(prompts_session)
    country = await country_service.get_by_id(request.country_id)
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found",
        )

    # Discover competitors
    discovered = await competitor_service.discover_competitors(
        brand_name=request.brand.name,
        brand_domain=request.brand.domain or "",
        country_name=country.name,
        num_competitors=5,
    )

    # Convert to response model
    competitors = [
        DiscoveredCompetitorResponse(
            brand_name=c.brand_name,
            domain=c.domain,
            variations=c.variations,
        )
        for c in discovered
    ]

    return DiscoverCompetitorsResponse(competitors=competitors)


# ===== GSC Onboarding Endpoints =====


@router.post("/gsc/match-property", response_model=GSCPropertyMatchResponse)
async def match_gsc_property(
    request: GSCPropertyMatchRequest,
    current_user: CurrentUser,
    session: UsersSessionDep,
    oauth_service: OAuthService = Depends(get_oauth_service),
    token_manager: TokenManager = Depends(get_token_manager),
) -> Any:
    """Match brand domain to a GSC property.

    Attempts to auto-match the user's brand domain to one of their GSC properties.
    Returns match type and available properties for selection.
    """
    repo = GSCCredentialRepository(session)
    credential = await repo.get_by_user_id(current_user.id)

    if not credential:
        raise HTTPException(status_code=400, detail="GSC is not connected")

    try:
        access_token = await get_valid_access_token(
            credential, repo, session, token_manager, oauth_service
        )
    except GSCTokenRefreshError:
        await repo.delete(credential)
        await session.commit()
        raise HTTPException(status_code=400, detail="GSC connection expired. Please reconnect.")

    # Fetch sites from GSC
    gsc_client = GSCClient()
    try:
        sites = await gsc_client.list_sites(access_token)
    except GSCError as e:
        logger.error(f"Failed to list GSC sites: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch GSC properties")

    # Match property
    matcher = PropertyMatcher()
    match_result = matcher.match(request.brand_domain, sites)

    return GSCPropertyMatchResponse(
        match_type=match_result.match_type,
        matched_property=match_result.matched_property,
        available_properties=match_result.available_properties,
    )


@router.post("/gsc/extract-keywords", response_model=GSCKeywordExtractResponse)
async def extract_gsc_keywords(
    request: GSCKeywordExtractRequest,
    current_user: CurrentUser,
    session: UsersSessionDep,
    prompts_session: SessionDep,
    oauth_service: OAuthService = Depends(get_oauth_service),
    token_manager: TokenManager = Depends(get_token_manager),
) -> Any:
    """Extract long-tail keywords from GSC search analytics.

    Returns filtered keywords (3+ words by default) sorted by performance.
    """
    repo = GSCCredentialRepository(session)
    credential = await repo.get_by_user_id(current_user.id)

    if not credential:
        raise HTTPException(status_code=400, detail="GSC is not connected")

    try:
        access_token = await get_valid_access_token(
            credential, repo, session, token_manager, oauth_service
        )
    except GSCTokenRefreshError:
        await repo.delete(credential)
        await session.commit()
        raise HTTPException(status_code=400, detail="GSC connection expired. Please reconnect.")

    # Extract keywords
    gsc_client = GSCClient()
    keyword_filter = MinWordCountFilter(min_words=request.min_word_count)
    extractor = KeywordExtractor(gsc_client, keyword_filter)

    try:
        result = await extractor.extract(
            access_token,
            request.site_url,
            days_back=28,
            result_limit=request.result_limit,
        )
    except GSCError as e:
        logger.error(f"Failed to extract keywords: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch search analytics")

    # Convert to response format
    keywords = [
        GSCKeywordResponse(
            query=row.keys[0] if row.keys else "",
            clicks=row.clicks,
            impressions=row.impressions,
            ctr=row.ctr,
            position=row.position,
        )
        for row in result.keywords
    ]

    # Generate prompts if requested
    generated_prompts: list[GeneratedPromptResponse] | None = None
    if request.generate_prompts:
        if not request.country_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="country_id is required when generate_prompts=True",
            )

        country_service = CountryService(prompts_session)
        country = await country_service.get_by_id(request.country_id)
        if not country:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Country not found",
            )
        language = country.languages[0].name if country.languages else "English"

        keyword_texts = [kw.query for kw in keywords]
        if keyword_texts:
            generator = get_prompts_generator_service()
            domain_name = "general"
            if request.business_domain_id:
                bd = await BusinessDomainService(prompts_session).get_by_id(
                    request.business_domain_id
                )
                if bd:
                    domain_name = bd.name
            prompt_tuples = await generator.generate_prompts_from_keywords(
                keyword_texts, domain_name, language
            )
            generated_prompts = [
                GeneratedPromptResponse(prompt=prompt, source_keyword=source)
                for prompt, source in prompt_tuples
            ]

    return GSCKeywordExtractResponse(
        keywords=keywords,
        total_fetched=result.total_fetched,
        total_after_filter=result.total_after_filter,
        generated_prompts=generated_prompts,
    )


@router.post(
    "/gsc/create-prompts",
    response_model=GSCOnboardingCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompts_from_gsc(
    request: GSCOnboardingCreateRequest,
    current_user: CurrentUser,
    prompts_session: SessionDep,
    embeddings_service: EmbeddingsService = Depends(get_embeddings_service),
    approval_policy: ApprovalPolicy = Depends(get_approval_policy),
) -> Any:
    """Create prompts and a group from selected GSC keywords.

    Creates prompts with pending approval status (not admin-created),
    creates a group with provided brand/country/competitors, and adds prompts to the group.

    This endpoint is called during onboarding (before onboarding is completed),
    so brand/country/competitors are passed from the frontend state.
    """
    # Create services
    prompt_service = PromptService(prompts_session, embeddings_service, approval_policy)
    group_service = PromptGroupService(prompts_session)
    binding_service = PromptGroupBindingService(prompts_session)

    # Create prompts (pending approval, no topic, user_id set)
    prompt_ids: list[int] = []
    for prompt_text in request.prompts:
        prompt = await prompt_service.add_prompt(
            prompt_text=prompt_text,
            topic_id=None,
            user_id=current_user.id,
            is_admin=False,  # Forces pending status
        )
        prompt_ids.append(prompt.id)

    # Create country resolution (from request, not locked)
    country_resolution = CountryResolution(
        country_id=request.country_id,
        is_locked=False,
        source="explicit",
    )

    # Create group without topic
    group = await group_service.create_group(
        user_id=current_user.id,
        title=request.group_title,
        brand=request.brand,
        country_resolution=country_resolution,
        topic_id=None,
        competitors=request.competitors,
    )

    # Add prompts to group
    await binding_service.add_prompts_to_group(group, prompt_ids)

    return GSCOnboardingCreateResponse(
        group_id=group.id,
        group_title=group.title,
        prompts_created=len(prompt_ids),
        prompt_ids=prompt_ids,
    )


# ===== Two-Step GSC Flow Endpoints =====


@router.post("/gsc/fetch-keywords", response_model=GSCFetchKeywordsResponse)
async def fetch_gsc_keywords(
    request: GSCFetchKeywordsRequest,
    current_user: CurrentUser,
    session: UsersSessionDep,
    oauth_service: OAuthService = Depends(get_oauth_service),
    token_manager: TokenManager = Depends(get_token_manager),
) -> Any:
    """Fetch ALL keywords from GSC (no word count filter).

    Returns up to result_limit keywords sorted by the requested metric.
    This is Step 1 of the two-step GSC flow where users select keywords.
    """
    repo = GSCCredentialRepository(session)
    credential = await repo.get_by_user_id(current_user.id)

    if not credential:
        raise HTTPException(status_code=400, detail="GSC is not connected")

    try:
        access_token = await get_valid_access_token(
            credential, repo, session, token_manager, oauth_service
        )
    except GSCTokenRefreshError:
        await repo.delete(credential)
        await session.commit()
        raise HTTPException(status_code=400, detail="GSC connection expired. Please reconnect.")

    # Fetch keywords from GSC without word count filter
    gsc_client = GSCClient()
    extractor = KeywordExtractor(gsc_client, keyword_filter=NoOpFilter())

    try:
        result = await extractor.extract(
            access_token,
            request.site_url,
            days_back=28,
            result_limit=request.result_limit,
        )
    except GSCError as e:
        logger.error(f"Failed to fetch keywords: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch search analytics")

    # Convert to response format
    keywords = [
        GSCKeywordResponse(
            query=row.keys[0] if row.keys else "",
            clicks=row.clicks,
            impressions=row.impressions,
            ctr=row.ctr,
            position=row.position,
        )
        for row in result.keywords
    ]

    # Sort by requested metric (client can also sort, but we do it server-side for consistency)
    if request.sort_by == "clicks":
        keywords.sort(key=lambda k: k.clicks, reverse=True)
    elif request.sort_by == "impressions":
        keywords.sort(key=lambda k: k.impressions, reverse=True)
    elif request.sort_by == "ctr":
        keywords.sort(key=lambda k: k.ctr, reverse=True)
    elif request.sort_by == "position":
        keywords.sort(key=lambda k: k.position)  # Lower position is better

    return GSCFetchKeywordsResponse(
        keywords=keywords,
        total_fetched=result.total_fetched,
    )


@router.post("/gsc/generate-prompts", response_model=GSCGeneratePromptsResponse)
async def generate_prompts_from_keywords(
    request: GSCGeneratePromptsRequest,
    current_user: CurrentUser,
    prompts_session: SessionDep,
) -> Any:
    """Generate prompts from selected keywords.

    This is Step 2 of the two-step GSC flow. Takes user-selected keywords
    (max 20) and generates 3 prompts per keyword.
    """
    # Enforce max 20 keywords limit
    if len(request.keywords) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 keywords allowed",
        )

    if len(request.keywords) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one keyword is required",
        )

    # Get language from country
    country_service = CountryService(prompts_session)
    country = await country_service.get_by_id(request.country_id)
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found",
        )
    language = country.languages[0].name if country.languages else "English"

    # Generate prompts
    generator = get_prompts_generator_service()
    domain_name = "general"
    if request.business_domain_id:
        bd = await BusinessDomainService(prompts_session).get_by_id(
            request.business_domain_id
        )
        if bd:
            domain_name = bd.name
    prompt_tuples = await generator.generate_prompts_from_keywords(
        request.keywords, domain_name, language
    )

    # Return just the prompt texts (no source keyword)
    prompts = [prompt for prompt, _source in prompt_tuples]

    return GSCGeneratePromptsResponse(prompts=prompts)
