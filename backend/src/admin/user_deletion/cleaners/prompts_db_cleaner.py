"""Cleaner for prompts_db tables."""

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.user_deletion.protocol import CleanupResult
from src.database.models import Prompt, PromptApprovalStatus, PromptGroup


class PromptsDbCleaner:
    """Cleans user data from prompts_db.

    Handles prompts conditionally:
    - Non-approved prompts (pending/rejected): hard delete
    - Approved prompts: set user_id = NULL (orphan)
    """

    async def cleanup(self, user_id: str, session: AsyncSession) -> CleanupResult:
        """Delete user's prompt groups and handle prompts conditionally.

        Deletes:
        - PromptGroup (cascades to prompt_group_bindings via FK)
        - Prompt (non-approved only)

        Orphans:
        - Prompt (approved: sets user_id = NULL)
        """
        deleted: dict[str, int] = {}
        orphaned: dict[str, int] = {}

        # Delete prompt groups (bindings cascade automatically)
        groups_result = await session.execute(
            delete(PromptGroup).where(PromptGroup.user_id == user_id)
        )
        deleted["prompt_groups"] = groups_result.rowcount

        # Delete non-approved prompts (pending or rejected)
        prompts_delete_result = await session.execute(
            delete(Prompt).where(
                Prompt.user_id == user_id,
                Prompt.approval_status != PromptApprovalStatus.APPROVED,
            )
        )
        deleted["prompts"] = prompts_delete_result.rowcount

        # Orphan approved prompts (set user_id = NULL)
        prompts_orphan_result = await session.execute(
            update(Prompt)
            .where(
                Prompt.user_id == user_id,
                Prompt.approval_status == PromptApprovalStatus.APPROVED,
            )
            .values(user_id=None)
        )
        orphaned["prompts"] = prompts_orphan_result.rowcount

        return CleanupResult(database="prompts_db", deleted=deleted, orphaned=orphaned)
