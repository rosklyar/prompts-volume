"""Shared GSC dependencies for OAuth and token management."""

from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.gsc.repository import GSCCredentialRepository
from src.gsc.services.oauth_service import OAuthService
from src.gsc.services.token_manager import TokenManager


def get_oauth_service() -> OAuthService:
    """Factory for OAuth service."""
    if not settings.google_gsc_client_id or not settings.google_gsc_client_secret:
        raise HTTPException(
            status_code=503,
            detail="Google Search Console integration is not configured",
        )
    return OAuthService(
        client_id=settings.google_gsc_client_id,
        client_secret=settings.google_gsc_client_secret,
        redirect_uri=settings.google_gsc_redirect_uri,
        secret_key=settings.secret_key,
    )


def get_token_manager() -> TokenManager:
    """Factory for token manager."""
    if not settings.gsc_token_encryption_key:
        raise HTTPException(
            status_code=503,
            detail="GSC token encryption is not configured",
        )
    return TokenManager(encryption_key=settings.gsc_token_encryption_key)


async def get_valid_access_token(
    credential: Any,
    repo: GSCCredentialRepository,
    session: AsyncSession,
    token_manager: TokenManager,
    oauth_service: OAuthService,
) -> str:
    """Get a valid access token, refreshing if necessary.

    Returns:
        Valid access token

    Raises:
        GSCTokenRefreshError: If token refresh fails
    """
    if not token_manager.is_token_expired(credential.token_expires_at):
        return token_manager.decrypt(credential.access_token_encrypted)

    # Token expired, refresh it
    refresh_token = token_manager.decrypt(credential.refresh_token_encrypted)
    tokens = await oauth_service.refresh_access_token(refresh_token)

    # Update stored tokens
    new_access_encrypted = token_manager.encrypt(tokens.access_token)
    new_expires_at = token_manager.calculate_expiry(tokens.expires_in)

    # Google may return a new refresh token on refresh
    new_refresh_encrypted = None
    if tokens.refresh_token:
        new_refresh_encrypted = token_manager.encrypt(tokens.refresh_token)

    await repo.update_tokens(
        credential,
        access_token_encrypted=new_access_encrypted,
        token_expires_at=new_expires_at,
        refresh_token_encrypted=new_refresh_encrypted,
    )
    await session.commit()

    return tokens.access_token
