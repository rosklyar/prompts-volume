"""Service for resolving country for prompt groups."""

from dataclasses import dataclass
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Country, Topic
from src.database.users_models import UserPreferences


class CountryResolutionError(Exception):
    """Raised when country cannot be resolved."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CountryLockedError(Exception):
    """Raised when trying to change a locked country."""

    def __init__(self, group_id: int):
        self.group_id = group_id
        super().__init__(f"Country is locked for group {group_id} (bound to topic)")


class InvalidCountryError(Exception):
    """Raised when country doesn't exist."""

    def __init__(self, country_id: int):
        self.country_id = country_id
        super().__init__(f"Country with id {country_id} not found")


@dataclass(frozen=True)
class CountryResolution:
    """Result of country resolution.

    Attributes:
        country_id: The resolved country ID
        is_locked: True if country comes from topic (cannot be changed)
        source: Where the country was resolved from
    """

    country_id: int
    is_locked: bool
    source: Literal["topic", "explicit", "user_preference"]


class CountryResolver:
    """Resolves which country to use for a prompt group.

    Priority chain:
    1. Topic's country (locked=True) - when topic is bound
    2. Explicit country_id (locked=False) - user-specified
    3. User preference (locked=False) - from user's default settings
    4. Error if none available

    Single Responsibility: Country resolution logic only.
    """

    def __init__(
        self,
        prompts_session: AsyncSession,
        users_session: AsyncSession,
    ):
        """Initialize with separate sessions for cross-database access.

        Args:
            prompts_session: Session for prompts_db (topics, countries)
            users_session: Session for users_db (user preferences)
        """
        self._prompts_session = prompts_session
        self._users_session = users_session

    async def resolve_for_group(
        self,
        topic_id: Optional[int],
        explicit_country_id: Optional[int],
        user_id: str,
    ) -> CountryResolution:
        """Resolve country for a new or updated prompt group.

        Args:
            topic_id: Optional topic ID (if bound, country comes from topic)
            explicit_country_id: Optional user-specified country ID
            user_id: User ID for fetching preferences

        Returns:
            CountryResolution with country_id, is_locked flag, and source

        Raises:
            CountryResolutionError: If country cannot be resolved
            InvalidCountryError: If explicit country_id is invalid
        """
        # Priority 1: Topic's country (locked)
        if topic_id is not None:
            country_id = await self._get_topic_country(topic_id)
            return CountryResolution(
                country_id=country_id,
                is_locked=True,
                source="topic",
            )

        # Priority 2: Explicit country_id
        if explicit_country_id is not None:
            await self._validate_country(explicit_country_id)
            return CountryResolution(
                country_id=explicit_country_id,
                is_locked=False,
                source="explicit",
            )

        # Priority 3: User preference
        user_country_id = await self._get_user_preference_country(user_id)
        if user_country_id is not None:
            return CountryResolution(
                country_id=user_country_id,
                is_locked=False,
                source="user_preference",
            )

        # No country available
        raise CountryResolutionError(
            "Country must be specified: either bind a topic, provide country_id, "
            "or set default country in user preferences"
        )

    async def validate_country_update(
        self,
        new_country_id: int,
        current_locked: bool,
        group_id: int,
    ) -> None:
        """Validate a country update for an existing group.

        Args:
            new_country_id: The new country ID to set
            current_locked: Whether the current country is locked
            group_id: The group ID (for error message)

        Raises:
            CountryLockedError: If trying to change a locked country
            InvalidCountryError: If new country_id is invalid
        """
        if current_locked:
            raise CountryLockedError(group_id)
        await self._validate_country(new_country_id)

    async def _get_topic_country(self, topic_id: int) -> int:
        """Get country_id from topic."""
        result = await self._prompts_session.execute(
            select(Topic.country_id).where(Topic.id == topic_id)
        )
        country_id = result.scalar_one_or_none()
        if country_id is None:
            raise CountryResolutionError(f"Topic {topic_id} not found")
        return country_id

    async def _get_user_preference_country(self, user_id: str) -> Optional[int]:
        """Get default country_id from user preferences."""
        result = await self._users_session.execute(
            select(UserPreferences.default_country_id).where(
                UserPreferences.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def _validate_country(self, country_id: int) -> None:
        """Validate that country exists."""
        result = await self._prompts_session.execute(
            select(Country.id).where(Country.id == country_id)
        )
        if result.scalar_one_or_none() is None:
            raise InvalidCountryError(country_id)
