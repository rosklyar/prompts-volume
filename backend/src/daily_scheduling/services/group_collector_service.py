"""Service for collecting groups with scheduling enabled."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.daily_scheduling.models.domain import EnabledGroup
from src.database.models import Prompt, PromptGroup, PromptGroupBinding


class GroupCollectorService:
    """Collects all groups with schedule_enabled=true.

    Single Responsibility: Collect enabled groups and their prompts.
    """

    def __init__(self, prompts_session: AsyncSession) -> None:
        self._session = prompts_session

    async def get_enabled_groups(self) -> Sequence[EnabledGroup]:
        """Get all groups with scheduling enabled.

        Returns list of EnabledGroup with group_id, user_id, title.
        """
        query = (
            select(PromptGroup)
            .where(PromptGroup.schedule_enabled == True)  # noqa: E712
        )
        result = await self._session.execute(query)
        groups = result.scalars().all()

        return [
            EnabledGroup(
                group_id=g.id,
                user_id=g.user_id,
                title=g.title,
            )
            for g in groups
        ]

    async def get_prompt_ids_for_group(self, group_id: int) -> list[int]:
        """Get all prompt IDs in a group."""
        query = (
            select(PromptGroupBinding.prompt_id)
            .where(PromptGroupBinding.group_id == group_id)
        )
        result = await self._session.execute(query)
        return [row[0] for row in result.all()]

    async def get_prompts_for_group(self, group_id: int) -> list[dict]:
        """Get all prompts in a group with their text.

        Returns list of {prompt_id, prompt_text}.
        """
        query = (
            select(PromptGroupBinding)
            .options(joinedload(PromptGroupBinding.prompt))
            .where(PromptGroupBinding.group_id == group_id)
        )
        result = await self._session.execute(query)
        bindings = result.scalars().unique().all()

        return [
            {
                "prompt_id": b.prompt_id,
                "prompt_text": b.prompt.prompt_text,
            }
            for b in bindings
        ]

    async def get_all_prompts_for_groups(
        self,
        group_ids: list[int],
    ) -> dict[int, list[dict]]:
        """Get prompts for multiple groups efficiently.

        Returns dict mapping group_id -> list of {prompt_id, prompt_text}.
        """
        if not group_ids:
            return {}

        query = (
            select(PromptGroupBinding)
            .options(joinedload(PromptGroupBinding.prompt))
            .where(PromptGroupBinding.group_id.in_(group_ids))
        )
        result = await self._session.execute(query)
        bindings = result.scalars().unique().all()

        groups_prompts: dict[int, list[dict]] = {gid: [] for gid in group_ids}
        for b in bindings:
            groups_prompts[b.group_id].append({
                "prompt_id": b.prompt_id,
                "prompt_text": b.prompt.prompt_text,
            })

        return groups_prompts
