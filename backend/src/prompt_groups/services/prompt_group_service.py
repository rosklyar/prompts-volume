"""Service for managing prompt groups."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import PromptGroup, PromptGroupBinding
from src.geography.services.country_resolver import (
    CountryLockedError,
    CountryResolution,
    CountryResolver,
)
from src.prompt_groups.exceptions import (
    GroupAccessDeniedError,
    GroupNotFoundError,
)


class PromptGroupService:
    """Service for managing prompt groups."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_group(
        self,
        user_id: str,
        title: str,
        brand: dict,
        country_resolution: CountryResolution,
        *,
        topic_id: Optional[int] = None,
        competitors: Optional[List[dict]] = None,
    ) -> PromptGroup:
        """Create a new prompt group with mandatory country binding.

        Args:
            user_id: The user ID who owns the group
            title: The group title
            brand: Brand dict with name, domain, variations
            country_resolution: Resolved country (from CountryResolver)
            topic_id: The topic ID to bind (optional, immutable after creation)
            competitors: Optional list of competitor dicts

        Returns:
            Created PromptGroup with topic and country relationships loaded.
        """
        group = PromptGroup(
            user_id=user_id,
            title=title,
            topic_id=topic_id,
            country_id=country_resolution.country_id,
            country_locked=country_resolution.is_locked,
            brand=brand,
            competitors=competitors,
        )
        self._session.add(group)
        await self._session.flush()

        # Reload with relationships for the response
        return await self.get_by_id(group.id)

    async def get_by_id(self, group_id: int) -> Optional[PromptGroup]:
        """Get a group by ID with topic and country eagerly loaded."""
        stmt = (
            select(PromptGroup)
            .options(
                selectinload(PromptGroup.topic),
                selectinload(PromptGroup.country),
            )
            .where(PromptGroup.id == group_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, group_id: int, user_id: str) -> PromptGroup:
        """Get a group by ID, verifying ownership.

        Raises:
            GroupNotFoundError: If group doesn't exist
            GroupAccessDeniedError: If user doesn't own the group
        """
        group = await self.get_by_id(group_id)
        if group is None:
            raise GroupNotFoundError(group_id)
        if group.user_id != user_id:
            raise GroupAccessDeniedError(group_id, user_id)
        return group

    async def get_user_groups(self, user_id: str) -> List[Tuple[PromptGroup, int]]:
        """Get all groups for a user with prompt counts.

        Returns list of (group, prompt_count) tuples, ordered by creation date.
        Eagerly loads topic and country relationships.
        """
        stmt = (
            select(PromptGroup, func.count(PromptGroupBinding.id).label("prompt_count"))
            .options(
                selectinload(PromptGroup.topic),
                selectinload(PromptGroup.country),
            )
            .outerjoin(
                PromptGroupBinding, PromptGroup.id == PromptGroupBinding.group_id
            )
            .where(PromptGroup.user_id == user_id)
            .group_by(PromptGroup.id)
            .order_by(PromptGroup.created_at)
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def update_group(
        self,
        group_id: int,
        user_id: str,
        title: Optional[str] = None,
        brand: Optional[dict] = None,
        competitors: Optional[List[dict]] = None,
        country_id: Optional[int] = None,
    ) -> PromptGroup:
        """Update a group's title, brand, competitors, and/or country.

        Args:
            group_id: The group ID to update
            user_id: The user ID who owns the group
            title: Optional new title (None = no change)
            brand: Optional brand dict (None = no change)
            competitors: Optional competitors list (None = no change, [] = clear)
            country_id: Optional new country ID (None = no change)

        Raises:
            GroupNotFoundError: If group doesn't exist
            GroupAccessDeniedError: If user doesn't own the group
            CountryLockedError: If trying to change a locked country
        """
        group = await self.get_by_id_for_user(group_id, user_id)

        if title is not None:
            group.title = title

        if brand is not None:
            group.brand = brand

        if competitors is not None:
            group.competitors = competitors if competitors else None

        if country_id is not None:
            if group.country_locked:
                raise CountryLockedError(group_id)
            group.country_id = country_id

        group.updated_at = datetime.now(timezone.utc)
        await self._session.flush()

        # Reload with relationships for the response
        return await self.get_by_id(group.id)

    async def delete_group(self, group_id: int, user_id: str) -> None:
        """Delete a group.

        Raises:
            GroupNotFoundError: If group doesn't exist
            GroupAccessDeniedError: If user doesn't own the group
        """
        group = await self.get_by_id_for_user(group_id, user_id)

        await self._session.delete(group)
        await self._session.flush()

    async def update_schedule(self, group_id: int, enabled: bool) -> None:
        """Update schedule_enabled for a group.

        Args:
            group_id: The group ID to update
            enabled: Whether daily scheduled reports are enabled
        """
        from sqlalchemy import update
        stmt = (
            update(PromptGroup)
            .where(PromptGroup.id == group_id)
            .values(schedule_enabled=enabled)
        )
        await self._session.execute(stmt)
        await self._session.flush()
