"""Service for managing prompt-group bindings."""

from typing import List, Set

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.database.models import Prompt, PromptGroup, PromptGroupBinding
from src.prompt_groups.exceptions import PromptNotFoundError


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
