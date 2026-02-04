"""Protocol and value objects for user data cleanup."""

from dataclasses import dataclass, field
from typing import Literal, Protocol

from sqlalchemy.ext.asyncio import AsyncSession


DatabaseName = Literal["users_db", "prompts_db", "evals_db"]


@dataclass(frozen=True, slots=True)
class CleanupResult:
    """Immutable value object representing cleanup results for a single database."""

    database: DatabaseName
    deleted: dict[str, int] = field(default_factory=dict)
    orphaned: dict[str, int] = field(default_factory=dict)

    @property
    def total_deleted(self) -> int:
        """Return total count of deleted records."""
        return sum(self.deleted.values())

    @property
    def total_orphaned(self) -> int:
        """Return total count of orphaned records."""
        return sum(self.orphaned.values())


class UserDataCleaner(Protocol):
    """Protocol for cleaning user data from a specific database."""

    async def cleanup(self, user_id: str, session: AsyncSession) -> CleanupResult:
        """Clean up all user data from the database.

        Args:
            user_id: The ID of the user whose data should be cleaned.
            session: Database session for the specific database.

        Returns:
            CleanupResult with counts of deleted and orphaned records.
        """
        ...
