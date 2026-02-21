"""Pydantic models for admin onboarding notifications."""

from datetime import datetime

from pydantic import BaseModel


class OnboardingUserInfo(BaseModel):
    """User info for onboarding notification list."""

    user_id: str
    email: str
    full_name: str | None
    onboarding_completed_at: datetime
    # Preferences
    default_brand: dict | None = None
    default_competitors: list | None = None
    country_name: str | None = None
    business_domain_name: str | None = None


class OnboardingNotificationsResponse(BaseModel):
    """Paginated onboarding notifications list."""

    users: list[OnboardingUserInfo]
    total: int


class OnboardingNotificationsCountResponse(BaseModel):
    """Lightweight count-only response for badge."""

    count: int
