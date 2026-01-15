"""Service for managing user preferences."""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.users_models import UserPreferences


class UserPreferencesService:
    """Service for managing user default preferences.

    Handles CRUD operations for user brand/competitor defaults.
    These preferences prefill group creation forms.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """Get user preferences, returns None if not set."""
        stmt = select(UserPreferences).where(UserPreferences.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_preferences(self, user_id: str) -> UserPreferences:
        """Get existing preferences or create empty record."""
        prefs = await self.get_preferences(user_id)
        if prefs is None:
            prefs = UserPreferences(user_id=user_id)
            self._session.add(prefs)
            await self._session.flush()
        return prefs

    async def save_preferences(
        self,
        user_id: str,
        *,
        default_country_id: Optional[int] = None,
        default_business_domain_id: Optional[int] = None,
        default_brand: dict,
        default_competitors: Optional[List[dict]] = None,
    ) -> UserPreferences:
        """Save or update user preferences.

        Args:
            user_id: The user ID
            default_country_id: Default country ID for new groups
            default_business_domain_id: Default business domain ID for new groups
            default_brand: Brand dict with name, domain, variations
            default_competitors: Optional list of competitor dicts

        Returns:
            Updated UserPreferences record
        """
        prefs = await self.get_or_create_preferences(user_id)
        prefs.default_country_id = default_country_id
        prefs.default_business_domain_id = default_business_domain_id
        prefs.default_brand = default_brand
        prefs.default_competitors = default_competitors
        prefs.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return prefs

    async def mark_onboarding_completed(self, user_id: str) -> UserPreferences:
        """Mark onboarding as completed for user."""
        prefs = await self.get_or_create_preferences(user_id)
        prefs.onboarding_completed_at = datetime.now(timezone.utc)
        prefs.onboarding_skipped_at = None  # Clear skip if previously set
        prefs.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return prefs

    async def mark_onboarding_skipped(self, user_id: str) -> UserPreferences:
        """Mark onboarding as skipped for user."""
        prefs = await self.get_or_create_preferences(user_id)
        prefs.onboarding_skipped_at = datetime.now(timezone.utc)
        prefs.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return prefs
