"""Service for managing prompt groups."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import PromptGroup, PromptGroupBinding
from src.prompt_groups.exceptions import (
    DuplicateGroupTitleError,
    GroupAccessDeniedError,
    GroupNotFoundError,
)


class PromptGroupService:
    """Service for managing prompt groups.

    Handles CRUD operations for groups and ensures business rules:
    - Group titles must be unique per user
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_group(
        self,
        user_id: str,
        title: str,
        brand: dict,
        competitors: Optional[List[dict]] = None
    ) -> PromptGroup:
        """Create a new prompt group.

        Args:
            user_id: The user ID who owns the group
            title: The group title
            brand: Brand dict with name, domain, variations
            competitors: Optional list of competitor dicts

        Raises:
            DuplicateGroupTitleError: If user already has a group with this title
        """
        existing = await self._get_by_user_and_title(user_id, title)
        if existing is not None:
            raise DuplicateGroupTitleError(title)

        group = PromptGroup(
            user_id=user_id,
            title=title,
            brand=brand,
            competitors=competitors
        )
        self._session.add(group)
        await self._session.flush()
        return group

    async def get_by_id(self, group_id: int) -> Optional[PromptGroup]:
        """Get a group by ID."""
        stmt = select(PromptGroup).where(PromptGroup.id == group_id)
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
        """
        stmt = (
            select(PromptGroup, func.count(PromptGroupBinding.id).label("prompt_count"))
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
        competitors: Optional[List[dict]] = None
    ) -> PromptGroup:
        """Update a group's title, brand, and/or competitors.

        Args:
            group_id: The group ID to update
            user_id: The user ID who owns the group
            title: Optional new title (None = no change)
            brand: Optional brand dict (None = no change)
            competitors: Optional competitors list (None = no change, [] = clear)

        Raises:
            GroupNotFoundError: If group doesn't exist
            GroupAccessDeniedError: If user doesn't own the group
            DuplicateGroupTitleError: If new title already exists
        """
        group = await self.get_by_id_for_user(group_id, user_id)

        # Only check title uniqueness if title is being changed
        if title is not None and title != group.title:
            existing = await self._get_by_user_and_title(user_id, title)
            if existing is not None and existing.id != group_id:
                raise DuplicateGroupTitleError(title)
            group.title = title

        if brand is not None:
            group.brand = brand

        if competitors is not None:
            group.competitors = competitors if competitors else None

        group.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return group

    async def delete_group(self, group_id: int, user_id: str) -> None:
        """Delete a group.

        Raises:
            GroupNotFoundError: If group doesn't exist
            GroupAccessDeniedError: If user doesn't own the group
        """
        group = await self.get_by_id_for_user(group_id, user_id)

        await self._session.delete(group)
        await self._session.flush()

    async def _get_by_user_and_title(
        self, user_id: str, title: str
    ) -> Optional[PromptGroup]:
        """Get a group by user and title."""
        stmt = select(PromptGroup).where(
            PromptGroup.user_id == user_id, PromptGroup.title == title
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
