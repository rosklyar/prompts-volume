"""Orchestrator for coordinating user deletion across all databases."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.user_deletion.cleaners import (
    EvalsDbCleaner,
    PromptsDbCleaner,
    UsersDbCleaner,
)
from src.admin.user_deletion.exceptions import (
    CannotDeleteSelfError,
    CannotDeleteSuperuserError,
    UserNotFoundError,
)
from src.admin.user_deletion.protocol import CleanupResult
from src.database.users_models import User


@dataclass(frozen=True, slots=True)
class DeletionSummary:
    """Summary of a user deletion operation."""

    user_id: str
    user_email: str
    results: tuple[CleanupResult, ...]

    @property
    def total_deleted(self) -> int:
        """Total records deleted across all databases."""
        return sum(r.total_deleted for r in self.results)


class UserDeletionOrchestrator:
    """Orchestrates user deletion across all 3 databases.

    Order of cleanup:
    1. evals_db - reports, consumed evaluations, batches
    2. prompts_db - groups, prompts
    3. users_db - user record and related data
    """

    def __init__(
        self,
        *,
        evals_cleaner: EvalsDbCleaner,
        prompts_cleaner: PromptsDbCleaner,
        users_cleaner: UsersDbCleaner,
    ) -> None:
        self._evals_cleaner = evals_cleaner
        self._prompts_cleaner = prompts_cleaner
        self._users_cleaner = users_cleaner

    async def delete_user(
        self,
        user_id: str,
        *,
        acting_user_id: str,
        users_session: AsyncSession,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
    ) -> DeletionSummary:
        """Permanently delete a user and all their data.

        Args:
            user_id: ID of the user to delete.
            acting_user_id: ID of the admin performing the deletion.
            users_session: Session for users_db.
            prompts_session: Session for prompts_db.
            evals_session: Session for evals_db.

        Returns:
            DeletionSummary with counts per database.

        Raises:
            UserNotFoundError: If user doesn't exist.
            CannotDeleteSuperuserError: If target user is a superuser.
            CannotDeleteSelfError: If admin tries to delete themselves.
        """
        # Validate user exists and can be deleted
        user = await self._validate_deletion(
            user_id, acting_user_id, users_session
        )

        # Clean up in order: evals -> prompts -> users
        evals_result = await self._evals_cleaner.cleanup(user_id, evals_session)
        prompts_result = await self._prompts_cleaner.cleanup(user_id, prompts_session)
        users_result = await self._users_cleaner.cleanup(user_id, users_session)

        return DeletionSummary(
            user_id=user_id,
            user_email=user.email,
            results=(evals_result, prompts_result, users_result),
        )

    async def _validate_deletion(
        self,
        user_id: str,
        acting_user_id: str,
        session: AsyncSession,
    ) -> User:
        """Validate that the user can be deleted.

        Returns the User object if valid.
        """
        # Check self-deletion
        if user_id == acting_user_id:
            raise CannotDeleteSelfError(user_id)

        # Fetch user
        user = await session.get(User, user_id)
        if user is None:
            raise UserNotFoundError(user_id)

        # Check superuser
        if user.is_superuser:
            raise CannotDeleteSuperuserError(user_id)

        return user
