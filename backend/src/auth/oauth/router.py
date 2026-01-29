"""OAuth authentication endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.auth.deps import CurrentUser, UsersSessionDep
from src.auth.models import GoogleLoginRequest, Message, OAuthConnectionPublic, OAuthLoginResponse
from src.auth.oauth.exceptions import OAuthValidationError
from src.auth.oauth.google import GoogleTokenValidator
from src.auth.oauth.repository import OAuthConnectionRepository
from src.auth.oauth.service import OAuthAuthenticationService
from src.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])


def get_google_validator() -> GoogleTokenValidator:
    """Factory for Google token validator."""
    if not settings.google_oauth_client_id:
        raise HTTPException(
            status_code=503,
            detail="Google Sign-In is not configured",
        )
    return GoogleTokenValidator(client_id=settings.google_oauth_client_id)


def get_oauth_service(
    session: UsersSessionDep,
    validator: GoogleTokenValidator = Depends(get_google_validator),
) -> OAuthAuthenticationService:
    """Factory for OAuth authentication service."""
    return OAuthAuthenticationService(
        session,
        validator,
        access_token_expire_minutes=settings.access_token_expire_minutes,
        signup_credits=settings.billing_signup_credits,
        signup_credits_expiry_days=settings.billing_signup_credits_expiry_days,
        max_signup_bonuses=settings.billing_max_signup_bonuses,
    )


@router.post("/google", response_model=OAuthLoginResponse)
async def google_login(
    request: GoogleLoginRequest,
    service: OAuthAuthenticationService = Depends(get_oauth_service),
) -> Any:
    """Sign in with Google.

    Accepts a Google ID token from the frontend (obtained after user
    completes Google Sign-In). Validates the token, creates or links
    the user account, and returns a JWT for API access.

    - If the Google account is already linked, logs in the user
    - If the email matches an existing user, links Google and logs in
    - If new user, creates account (no password, email pre-verified)
    """
    try:
        token, resolution = await service.authenticate(request.id_token)
        return OAuthLoginResponse(
            access_token=token.access_token,
            token_type=token.token_type,
            is_new_user=(resolution.action == "created"),
        )
    except OAuthValidationError as e:
        logger.warning(f"OAuth validation failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/connections", response_model=list[OAuthConnectionPublic])
async def list_oauth_connections(
    session: UsersSessionDep,
    current_user: CurrentUser,
) -> Any:
    """List OAuth connections for current user."""
    repo = OAuthConnectionRepository(session)
    connections = await repo.list_by_user(current_user.id)
    return connections


@router.delete("/connections/{provider}", response_model=Message)
async def unlink_oauth_provider(
    provider: str,
    session: UsersSessionDep,
    current_user: CurrentUser,
) -> Any:
    """Unlink an OAuth provider from current user.

    Cannot unlink if:
    - User has no password and this is their only OAuth connection
    """
    repo = OAuthConnectionRepository(session)

    connection = await repo.find_by_user_and_provider(current_user.id, provider)
    if not connection:
        raise HTTPException(status_code=404, detail=f"No {provider} connection found")

    # Check if user can unlink
    all_connections = await repo.list_by_user(current_user.id)
    has_password = current_user.hashed_password is not None

    if not has_password and len(all_connections) == 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot unlink your only sign-in method. Set a password first.",
        )

    await repo.delete(connection)
    await session.commit()

    return Message(message=f"{provider.title()} account unlinked successfully")
