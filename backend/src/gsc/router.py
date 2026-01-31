"""GSC API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from src.auth.deps import CurrentUser, UsersSessionDep
from src.config.settings import settings
from src.gsc.deps import get_oauth_service, get_token_manager, get_valid_access_token
from src.gsc.exceptions import (
    GSCError,
    GSCInvalidStateError,
    GSCTokenRefreshError,
)
from src.gsc.models import (
    GSCAuthInitResponse,
    GSCConnectionStatus,
    GSCDisconnectResponse,
    SearchAnalyticsRequest,
    SearchAnalyticsResponse,
)
from src.gsc.repository import GSCCredentialRepository
from src.gsc.services.gsc_client import GSCClient
from src.gsc.services.oauth_service import OAuthService
from src.gsc.services.token_manager import TokenManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gsc", tags=["gsc"])


@router.get("/auth/initiate", response_model=GSCAuthInitResponse)
async def initiate_gsc_auth(
    current_user: CurrentUser,
    redirect_uri: str | None = None,
    oauth_service: OAuthService = Depends(get_oauth_service),
) -> Any:
    """Initiate GSC OAuth flow.

    Returns an authorization URL that the frontend should redirect the user to.
    After user authorizes, Google will redirect back to /auth/callback.

    Args:
        redirect_uri: Optional URL to redirect to after OAuth completes.
                      If not provided, defaults to settings page.
    """
    auth_url = oauth_service.generate_auth_url(current_user.id, redirect_uri)
    return GSCAuthInitResponse(auth_url=auth_url)


@router.get("/auth/callback")
async def gsc_oauth_callback(
    code: str,
    state: str,
    session: UsersSessionDep,
    oauth_service: OAuthService = Depends(get_oauth_service),
    token_manager: TokenManager = Depends(get_token_manager),
) -> RedirectResponse:
    """OAuth callback endpoint.

    Google redirects here after user authorizes. This endpoint:
    1. Validates the state JWT
    2. Exchanges code for tokens
    3. Encrypts and stores tokens
    4. Redirects to frontend settings page

    This endpoint doesn't use CurrentUser dependency because we need to
    extract user_id from the state parameter (user may not have auth cookie).
    """
    # Validate state and extract user_id and redirect_uri
    try:
        user_id, redirect_uri = oauth_service.validate_state(state)
    except GSCInvalidStateError as e:
        logger.warning(f"GSC OAuth callback - invalid state: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?gsc=error&reason=invalid_state"
        )

    # Exchange code for tokens
    try:
        tokens = await oauth_service.exchange_code(code)
    except GSCTokenRefreshError as e:
        logger.error(f"GSC OAuth callback - token exchange failed: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?gsc=error&reason=token_exchange_failed"
        )

    if not tokens.refresh_token:
        logger.error("GSC OAuth callback - no refresh token received")
        return RedirectResponse(
            url=f"{settings.frontend_url}/settings?gsc=error&reason=no_refresh_token"
        )

    # Encrypt tokens for storage
    access_token_encrypted = token_manager.encrypt(tokens.access_token)
    refresh_token_encrypted = token_manager.encrypt(tokens.refresh_token)
    expires_at = token_manager.calculate_expiry(tokens.expires_in)

    # Store or update credentials
    repo = GSCCredentialRepository(session)
    existing = await repo.get_by_user_id(user_id)

    if existing:
        # Update existing credentials
        await repo.update_tokens(
            existing,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expires_at=expires_at,
        )
    else:
        # Create new credentials
        await repo.create(
            user_id=user_id,
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expires_at=expires_at,
            scopes=tokens.scope,
        )

    await session.commit()

    logger.info(f"GSC connected successfully for user {user_id}")
    # Use provided redirect_uri or default to settings page
    final_redirect = redirect_uri or f"{settings.frontend_url}/settings"
    return RedirectResponse(url=f"{final_redirect}?gsc=connected")


@router.get("/status", response_model=GSCConnectionStatus)
async def get_gsc_status(
    current_user: CurrentUser,
    session: UsersSessionDep,
    token_manager: TokenManager = Depends(get_token_manager),
    oauth_service: OAuthService = Depends(get_oauth_service),
) -> Any:
    """Get GSC connection status and list of properties.

    If connected, returns list of GSC sites the user has access to.
    Automatically refreshes token if expired.
    """
    repo = GSCCredentialRepository(session)
    credential = await repo.get_by_user_id(current_user.id)

    if not credential:
        return GSCConnectionStatus(is_connected=False)

    # Get or refresh access token
    try:
        access_token = await get_valid_access_token(
            credential, repo, session, token_manager, oauth_service
        )
    except GSCTokenRefreshError:
        # Token refresh failed - credential is stale, delete it
        await repo.delete(credential)
        await session.commit()
        return GSCConnectionStatus(is_connected=False)

    # Fetch sites from GSC API
    gsc_client = GSCClient()
    try:
        sites = await gsc_client.list_sites(access_token)
    except GSCError as e:
        logger.error(f"Failed to list GSC sites: {e}")
        # Return connected but without sites if API fails
        return GSCConnectionStatus(
            is_connected=True,
            connected_at=credential.connected_at,
            sites=None,
        )

    # Update last_used_at
    await repo.update_last_used(credential)
    await session.commit()

    return GSCConnectionStatus(
        is_connected=True,
        connected_at=credential.connected_at,
        sites=sites,
    )


@router.delete("/disconnect", response_model=GSCDisconnectResponse)
async def disconnect_gsc(
    current_user: CurrentUser,
    session: UsersSessionDep,
) -> Any:
    """Disconnect GSC account.

    Removes stored OAuth credentials. User will need to re-authorize to reconnect.
    """
    repo = GSCCredentialRepository(session)
    credential = await repo.get_by_user_id(current_user.id)

    if not credential:
        raise HTTPException(status_code=404, detail="GSC is not connected")

    await repo.delete(credential)
    await session.commit()

    logger.info(f"GSC disconnected for user {current_user.id}")
    return GSCDisconnectResponse(message="Google Search Console disconnected successfully")


@router.post("/search-analytics", response_model=SearchAnalyticsResponse)
async def get_search_analytics(
    request: SearchAnalyticsRequest,
    current_user: CurrentUser,
    session: UsersSessionDep,
    token_manager: TokenManager = Depends(get_token_manager),
    oauth_service: OAuthService = Depends(get_oauth_service),
) -> Any:
    """Get search analytics data for a GSC property.

    Returns search queries with clicks, impressions, CTR, and position metrics.
    """
    repo = GSCCredentialRepository(session)
    credential = await repo.get_by_user_id(current_user.id)

    if not credential:
        raise HTTPException(status_code=400, detail="GSC is not connected")

    # Get or refresh access token
    try:
        access_token = await get_valid_access_token(
            credential, repo, session, token_manager, oauth_service
        )
    except GSCTokenRefreshError:
        await repo.delete(credential)
        await session.commit()
        raise HTTPException(status_code=400, detail="GSC connection expired. Please reconnect.")

    # Fetch search analytics from GSC API
    gsc_client = GSCClient()
    try:
        rows = await gsc_client.get_search_analytics(
            access_token,
            site_url=request.site_url,
            start_date=request.start_date,
            end_date=request.end_date,
            row_limit=request.row_limit,
        )
    except GSCError as e:
        logger.error(f"Failed to get search analytics: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch search analytics from Google")

    # Update last_used_at
    await repo.update_last_used(credential)
    await session.commit()

    return SearchAnalyticsResponse(rows=rows)
