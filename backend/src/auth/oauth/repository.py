"""OAuth connection database operations."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.users_models import OAuthConnection


class OAuthConnectionRepository:
    """Repository for OAuth connection persistence.

    Handles CRUD operations for oauth_connections table.
    Single Responsibility: Only database operations, no business logic.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_by_provider_user_id(
        self,
        provider: str,
        provider_user_id: str,
    ) -> OAuthConnection | None:
        """Find an OAuth connection by provider and provider's user ID."""
        result = await self._session.execute(
            select(OAuthConnection).where(
                OAuthConnection.provider == provider,
                OAuthConnection.provider_user_id == provider_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_user_and_provider(
        self,
        user_id: str,
        provider: str,
    ) -> OAuthConnection | None:
        """Find an OAuth connection for a specific user and provider."""
        result = await self._session.execute(
            select(OAuthConnection).where(
                OAuthConnection.user_id == user_id,
                OAuthConnection.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[OAuthConnection]:
        """List all OAuth connections for a user."""
        result = await self._session.execute(
            select(OAuthConnection).where(OAuthConnection.user_id == user_id)
        )
        return list(result.scalars().all())

    async def create(
        self,
        *,
        user_id: str,
        provider: str,
        provider_user_id: str,
        provider_email: str | None = None,
    ) -> OAuthConnection:
        """Create a new OAuth connection."""
        connection = OAuthConnection(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            connected_at=datetime.now(timezone.utc),
            last_login_at=datetime.now(timezone.utc),
        )
        self._session.add(connection)
        await self._session.flush()
        return connection

    async def update_last_login(self, connection: OAuthConnection) -> None:
        """Update the last login timestamp."""
        connection.last_login_at = datetime.now(timezone.utc)
        self._session.add(connection)

    async def delete(self, connection: OAuthConnection) -> None:
        """Delete an OAuth connection."""
        await self._session.delete(connection)
