"""API router for onboarding and user preferences."""

from fastapi import APIRouter, status

from src.auth.deps import CurrentUser
from src.onboarding.exceptions import OnboardingError, to_http_exception
from src.onboarding.models.api_models import (
    CompleteOnboardingRequest,
    OnboardingStatusResponse,
    SavePreferencesRequest,
    UserPreferencesResponse,
)
from src.onboarding.services import OnboardingServiceDep
from src.prompt_groups.models.brand_models import BrandModel, CompetitorModel

router = APIRouter(prefix="/onboarding/api/v1", tags=["onboarding"])


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: CurrentUser,
    onboarding_service: OnboardingServiceDep,
):
    """Check if current user has completed onboarding.

    Returns completion status, skip status, and whether preferences exist.
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


@router.post("/skip", response_model=OnboardingStatusResponse)
async def skip_onboarding(
    current_user: CurrentUser,
    onboarding_service: OnboardingServiceDep,
):
    """Skip onboarding for now (can complete later via settings).

    User can still set preferences later through the settings page.
    """
    try:
        prefs = await onboarding_service.skip_onboarding(current_user.id)
        return OnboardingStatusResponse(
            is_completed=prefs.onboarding_completed_at is not None,
            is_skipped=prefs.onboarding_skipped_at is not None,
            completed_at=prefs.onboarding_completed_at,
            skipped_at=prefs.onboarding_skipped_at,
            has_preferences=prefs.default_brand is not None,
        )
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
    # Handle None case (new user with no preferences)
    if prefs is None:
        return UserPreferencesResponse(
            default_country_id=None,
            default_business_domain_id=None,
            default_brand=None,
            default_competitors=[],
            onboarding_status=OnboardingStatusResponse(
                is_completed=False,
                is_skipped=False,
                completed_at=None,
                skipped_at=None,
                has_preferences=False,
            ),
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
            is_skipped=prefs.onboarding_skipped_at is not None,
            completed_at=prefs.onboarding_completed_at,
            skipped_at=prefs.onboarding_skipped_at,
            has_preferences=prefs.default_brand is not None,
        ),
    )
