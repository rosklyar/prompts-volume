"""Services for onboarding module with dependency injection providers."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.users_session import get_users_session
from src.onboarding.services.onboarding_service import OnboardingService
from src.onboarding.services.preferences_service import UserPreferencesService


def get_preferences_service(
    session: AsyncSession = Depends(get_users_session),
) -> UserPreferencesService:
    """Dependency injection for UserPreferencesService."""
    return UserPreferencesService(session)


def get_onboarding_service(
    preferences_service: UserPreferencesService = Depends(get_preferences_service),
) -> OnboardingService:
    """Dependency injection for OnboardingService."""
    return OnboardingService(preferences_service)


# Type aliases for cleaner router signatures
PreferencesServiceDep = Annotated[UserPreferencesService, Depends(get_preferences_service)]
OnboardingServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]


__all__ = [
    "UserPreferencesService",
    "OnboardingService",
    "get_preferences_service",
    "get_onboarding_service",
    "PreferencesServiceDep",
    "OnboardingServiceDep",
]
