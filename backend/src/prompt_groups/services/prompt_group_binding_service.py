"""Service for managing prompt-group bindings."""

from typing import List, Set

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database.models import Prompt, PromptGroup, PromptGroupBinding
from src.prompt_groups.exceptions import GroupHasNoTopicError, PromptNotFoundError


class PromptGroupBindingService:
    """Service for managing prompt-group bindings.

    Handles:
    - Adding/removing prompts from groups
    - Fetching group details with prompts
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def add_prompts_to_group(
        self,
        group: PromptGroup,
        prompt_ids: List[int],
    ) -> tuple[List[PromptGroupBinding], int]:
        """Add prompts to a group.

        Returns:
            Tuple of (created bindings, skipped count)
            Skipped are prompts already in the group.
        """
        existing_prompts = await self._get_existing_prompt_ids(prompt_ids)
        missing = set(prompt_ids) - existing_prompts
        if missing:
            raise PromptNotFoundError(list(missing)[0])

        existing_bindings = await self._get_existing_bindings(group.id, prompt_ids)
        existing_prompt_ids = {b.prompt_id for b in existing_bindings}

        created_bindings: List[PromptGroupBinding] = []
        for prompt_id in prompt_ids:
            if prompt_id in existing_prompt_ids:
                continue

            binding = PromptGroupBinding(
                group_id=group.id,
                prompt_id=prompt_id,
            )
            self._session.add(binding)
            created_bindings.append(binding)

        await self._session.flush()

        skipped_count = len(prompt_ids) - len(created_bindings)
        return created_bindings, skipped_count

    async def remove_prompts_from_group(
        self,
        group: PromptGroup,
        prompt_ids: List[int],
    ) -> int:
        """Remove prompts from a group.

        Returns count of removed bindings.
        """
        stmt = delete(PromptGroupBinding).where(
            PromptGroupBinding.group_id == group.id,
            PromptGroupBinding.prompt_id.in_(prompt_ids),
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def get_group_with_prompts(self, group: PromptGroup) -> List[dict]:
        """Get all prompts in a group with their data.

        Returns list of dicts containing:
        - binding info
        - prompt info
        """
        stmt = (
            select(PromptGroupBinding)
            .options(joinedload(PromptGroupBinding.prompt))
            .where(PromptGroupBinding.group_id == group.id)
            .order_by(PromptGroupBinding.added_at.desc())
        )
        result = await self._session.execute(stmt)
        bindings = result.scalars().unique().all()

        prompts_data = []
        for binding in bindings:
            prompts_data.append(
                {
                    "binding_id": binding.id,
                    "prompt_id": binding.prompt_id,
                    "prompt_text": binding.prompt.prompt_text,
                    "added_at": binding.added_at,
                }
            )

        return prompts_data

    async def get_available_prompts_for_group(
        self,
        group: PromptGroup,
    ) -> List[dict]:
        """Get prompts from the group's topic that aren't already in the group.

        Args:
            group: The prompt group (must have topic_id)

        Returns:
            List of dicts containing prompt id and text

        Raises:
            GroupHasNoTopicError: If group has no topic binding
        """
        if group.topic_id is None:
            raise GroupHasNoTopicError(group.id)

        # Get existing prompt IDs in this group
        existing_stmt = select(PromptGroupBinding.prompt_id).where(
            PromptGroupBinding.group_id == group.id
        )
        existing_result = await self._session.execute(existing_stmt)
        existing_prompt_ids = {row[0] for row in existing_result.all()}

        # Get prompts from topic that aren't in the group
        prompts_stmt = select(Prompt).where(
            Prompt.topic_id == group.topic_id,
            ~Prompt.id.in_(existing_prompt_ids) if existing_prompt_ids else True,
        )
        prompts_result = await self._session.execute(prompts_stmt)
        prompts = prompts_result.scalars().all()

        return [
            {"id": p.id, "prompt_text": p.prompt_text}
            for p in prompts
        ]

    async def _get_existing_prompt_ids(self, prompt_ids: List[int]) -> Set[int]:
        """Get set of prompt IDs that exist in database."""
        stmt = select(Prompt.id).where(Prompt.id.in_(prompt_ids))
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def _get_existing_bindings(
        self, group_id: int, prompt_ids: List[int]
    ) -> List[PromptGroupBinding]:
        """Get existing bindings for group and prompt IDs."""
        stmt = select(PromptGroupBinding).where(
            PromptGroupBinding.group_id == group_id,
            PromptGroupBinding.prompt_id.in_(prompt_ids),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
