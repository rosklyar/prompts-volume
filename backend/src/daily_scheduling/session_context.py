"""Multi-session context manager for daily scheduling jobs."""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Callable

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class SessionSet:
    """Container for all database sessions."""

    prompts: AsyncSession
    evals: AsyncSession
    users: AsyncSession

    async def commit_all(self) -> None:
        """Commit all sessions in correct order."""
        await self.evals.commit()
        await self.users.commit()
        await self.prompts.commit()

    async def rollback_all(self) -> None:
        """Rollback all sessions."""
        await self.evals.rollback()
        await self.users.rollback()
        await self.prompts.rollback()


@asynccontextmanager
async def multi_session_context(
    prompts_maker: Callable[[], AsyncSession],
    evals_maker: Callable[[], AsyncSession],
    users_maker: Callable[[], AsyncSession],
) -> AsyncIterator[SessionSet]:
    """Context manager for all 3 database sessions.

    Usage:
        async with multi_session_context(
            prompts_maker=get_session_maker(),
            evals_maker=get_evals_session_maker(),
            users_maker=get_users_session_maker(),
        ) as sessions:
            orchestrator = create_daily_batch_orchestrator(sessions)
            ...
    """
    async with prompts_maker() as prompts:
        async with evals_maker() as evals:
            async with users_maker() as users:
                yield SessionSet(prompts=prompts, evals=evals, users=users)
