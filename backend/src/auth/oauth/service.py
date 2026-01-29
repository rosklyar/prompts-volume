"""OAuth authentication orchestration service."""

from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import security
from src.auth.models import Token
from src.auth.oauth.protocols import OAuthTokenValidator
from src.auth.oauth.resolver import OAuthResolution, OAuthUserResolver


class OAuthAuthenticationService:
    """Orchestrates OAuth authentication flow.

    Coordinates:
    1. Token validation (delegated to provider-specific validator)
    2. User resolution (find/create/link user)
    3. JWT generation (same as password login)

    Single Responsibility: Orchestration only, delegates specifics.
    Open/Closed: Add new providers by injecting new validators.
    """

    def __init__(
        self,
        session: AsyncSession,
        validator: OAuthTokenValidator,
        *,
        access_token_expire_minutes: int,
        signup_credits: float,
        signup_credits_expiry_days: int,
        max_signup_bonuses: int | None,
    ):
        self._session = session
        self._validator = validator
        self._access_token_expire_minutes = access_token_expire_minutes
        self._resolver = OAuthUserResolver(
            session,
            signup_credits=signup_credits,
            signup_credits_expiry_days=signup_credits_expiry_days,
            max_signup_bonuses=max_signup_bonuses,
        )

    async def authenticate(self, id_token: str) -> tuple[Token, OAuthResolution]:
        """Authenticate via OAuth and return JWT.

        Args:
            id_token: OAuth ID token from frontend

        Returns:
            Tuple of (JWT Token, resolution details)

        Raises:
            OAuthValidationError: If token validation fails
            HTTPException: If user is inactive/deleted
        """
        # 1. Validate OAuth token
        oauth_info = await self._validator.validate_token(id_token)

        # 2. Resolve to local user
        resolution = await self._resolver.resolve(oauth_info)
        user = resolution.user

        # 3. Check user status
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        if user.is_deleted:
            raise HTTPException(status_code=400, detail="User account deleted")

        # 4. Commit changes (new user or updated connection)
        await self._session.commit()
        await self._session.refresh(user)

        # 5. Generate JWT (same as password login)
        access_token_expires = timedelta(minutes=self._access_token_expire_minutes)
        token = Token(
            access_token=security.create_access_token(
                user.id, expires_delta=access_token_expires
            )
        )

        return token, resolution
