"""GSC credentials database operations."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.users_models import GSCCredential


class GSCCredentialRepository:
    """Repository for GSC credential persistence.

    Handles CRUD operations for gsc_credentials table.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_user_id(self, user_id: str) -> GSCCredential | None:
        """Get GSC credentials for a user."""
        result = await self._session.execute(
            select(GSCCredential).where(GSCCredential.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: str,
        access_token_encrypted: str,
        refresh_token_encrypted: str,
        token_expires_at: datetime,
        scopes: str,
    ) -> GSCCredential:
        """Create new GSC credentials for a user."""
        credential = GSCCredential(
            user_id=user_id,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expires_at=token_expires_at,
            scopes=scopes,
            connected_at=datetime.now(timezone.utc),
        )
        self._session.add(credential)
        await self._session.flush()
        return credential

    async def update_tokens(
        self,
        credential: GSCCredential,
        *,
        access_token_encrypted: str,
        token_expires_at: datetime,
        refresh_token_encrypted: str | None = None,
    ) -> None:
        """Update access token (and optionally refresh token) after refresh."""
        credential.access_token_encrypted = access_token_encrypted
        credential.token_expires_at = token_expires_at
        if refresh_token_encrypted is not None:
            credential.refresh_token_encrypted = refresh_token_encrypted
        self._session.add(credential)

    async def update_last_used(self, credential: GSCCredential) -> None:
        """Update the last_used_at timestamp."""
        credential.last_used_at = datetime.now(timezone.utc)
        self._session.add(credential)

    async def delete(self, credential: GSCCredential) -> None:
        """Delete GSC credentials."""
        await self._session.delete(credential)
