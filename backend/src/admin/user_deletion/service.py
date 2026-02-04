"""Service and dependency injection for user deletion."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.user_deletion.cleaners import (
    EvalsDbCleaner,
    PromptsDbCleaner,
    UsersDbCleaner,
)
from src.admin.user_deletion.models import DatabaseCleanupDetail, UserDeletionResponse
from src.admin.user_deletion.orchestrator import UserDeletionOrchestrator
from src.database import get_async_session
from src.database.evals_session import get_evals_session
from src.database.users_session import get_users_session


class UserDeletionService:
    """High-level service for user deletion with response formatting."""

    def __init__(
        self,
        *,
        orchestrator: UserDeletionOrchestrator,
        users_session: AsyncSession,
        prompts_session: AsyncSession,
        evals_session: AsyncSession,
    ) -> None:
        self._orchestrator = orchestrator
        self._users_session = users_session
        self._prompts_session = prompts_session
        self._evals_session = evals_session

    async def hard_delete_user(
        self,
        user_id: str,
        *,
        acting_user_id: str,
    ) -> UserDeletionResponse:
        """Permanently delete a user and return formatted response.

        Args:
            user_id: ID of the user to delete.
            acting_user_id: ID of the admin performing the deletion.

        Returns:
            UserDeletionResponse with detailed counts.
        """
        summary = await self._orchestrator.delete_user(
            user_id,
            acting_user_id=acting_user_id,
            users_session=self._users_session,
            prompts_session=self._prompts_session,
            evals_session=self._evals_session,
        )

        # Commit all sessions
        await self._evals_session.commit()
        await self._prompts_session.commit()
        await self._users_session.commit()

        return UserDeletionResponse(
            user_id=summary.user_id,
            user_email=summary.user_email,
            total_records_deleted=summary.total_deleted,
            details=[
                DatabaseCleanupDetail(
                    database=result.database,
                    deleted=result.deleted,
                    orphaned=result.orphaned,
                )
                for result in summary.results
            ],
        )


def get_user_deletion_service(
    users_session: Annotated[AsyncSession, Depends(get_users_session)],
    prompts_session: Annotated[AsyncSession, Depends(get_async_session)],
    evals_session: Annotated[AsyncSession, Depends(get_evals_session)],
) -> UserDeletionService:
    """FastAPI dependency for UserDeletionService."""
    orchestrator = UserDeletionOrchestrator(
        evals_cleaner=EvalsDbCleaner(),
        prompts_cleaner=PromptsDbCleaner(),
        users_cleaner=UsersDbCleaner(),
    )
    return UserDeletionService(
        orchestrator=orchestrator,
        users_session=users_session,
        prompts_session=prompts_session,
        evals_session=evals_session,
    )


UserDeletionServiceDep = Annotated[
    UserDeletionService, Depends(get_user_deletion_service)
]
