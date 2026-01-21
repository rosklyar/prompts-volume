"""Service for onboarding workflow orchestration."""

from typing import List, Optional

from src.database.users_models import UserPreferences
from src.onboarding.services.preferences_service import UserPreferencesService


class OnboardingService:
    """Service for onboarding workflow orchestration.

    Coordinates preference saving with onboarding status tracking.
    Country selection is mandatory during onboarding.
    """

    def __init__(self, preferences_service: UserPreferencesService):
        self._preferences = preferences_service

    async def get_onboarding_status(self, user_id: str) -> dict:
        """Get current onboarding status for user.

        Returns:
            {
                "is_completed": bool,
                "completed_at": datetime | None,
                "has_preferences": bool,
            }
        """
        prefs = await self._preferences.get_preferences(user_id)

        if prefs is None:
            return {
                "is_completed": False,
                "completed_at": None,
                "has_preferences": False,
            }

        return {
            "is_completed": prefs.onboarding_completed_at is not None,
            "completed_at": prefs.onboarding_completed_at,
            "has_preferences": prefs.default_brand is not None,
        }

    async def complete_onboarding(
        self,
        user_id: str,
        *,
        default_country_id: int,
        default_business_domain_id: Optional[int] = None,
        default_brand: dict,
        default_competitors: Optional[List[dict]] = None,
    ) -> UserPreferences:
        """Complete onboarding by saving preferences and marking complete.

        Args:
            user_id: The user ID
            default_country_id: Default country ID for new groups (REQUIRED)
            default_business_domain_id: Default business domain ID for new groups
            default_brand: Brand dict with name, domain, variations
            default_competitors: Optional list of competitor dicts

        Returns:
            Updated UserPreferences record
        """
        # Save preferences
        prefs = await self._preferences.save_preferences(
            user_id,
            default_country_id=default_country_id,
            default_business_domain_id=default_business_domain_id,
            default_brand=default_brand,
            default_competitors=default_competitors,
        )
        # Mark as completed
        prefs = await self._preferences.mark_onboarding_completed(user_id)
        return prefs

    async def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences (delegates to preferences service)."""
        return await self._preferences.get_preferences(user_id)

    async def update_preferences(
        self,
        user_id: str,
        *,
        default_country_id: int,
        default_business_domain_id: Optional[int] = None,
        default_brand: dict,
        default_competitors: Optional[List[dict]] = None,
    ) -> UserPreferences:
        """Update user preferences (can be done anytime via settings).

        Args:
            user_id: The user ID
            default_country_id: Default country ID for new groups (REQUIRED)
            default_business_domain_id: Default business domain ID for new groups
            default_brand: Brand dict with name, domain, variations
            default_competitors: Optional list of competitor dicts

        Returns:
            Updated UserPreferences record
        """
        return await self._preferences.save_preferences(
            user_id,
            default_country_id=default_country_id,
            default_business_domain_id=default_business_domain_id,
            default_brand=default_brand,
            default_competitors=default_competitors,
        )
