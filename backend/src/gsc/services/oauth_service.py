"""OAuth service for Google Search Console authorization flow."""

import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt

from src.gsc.exceptions import GSCInvalidStateError, GSCTokenRefreshError
from src.gsc.models import TokenResponse

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

# State JWT expires after 10 minutes
STATE_EXPIRY_MINUTES = 10


class OAuthService:
    """Handles OAuth 2.0 authorization code flow for GSC.

    Responsibilities:
    - Generate authorization URL with state parameter
    - Exchange authorization code for tokens
    - Refresh expired access tokens
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        secret_key: str,
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._secret_key = secret_key

    def generate_auth_url(self, user_id: str, redirect_uri: str | None = None) -> str:
        """Generate OAuth authorization URL with signed state.

        Args:
            user_id: User ID to encode in state JWT
            redirect_uri: Optional URL to redirect to after OAuth completes

        Returns:
            Full authorization URL to redirect user to
        """
        state = self._create_state_jwt(user_id, redirect_uri)

        params = {
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": GSC_SCOPE,
            "access_type": "offline",  # Required for refresh token
            "prompt": "consent",  # Force consent to always get refresh token
            "state": state,
        }

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    def validate_state(self, state: str) -> tuple[str, str | None]:
        """Validate state JWT and extract user_id and redirect_uri.

        Args:
            state: State JWT from OAuth callback

        Returns:
            Tuple of (user_id, redirect_uri) extracted from valid state

        Raises:
            GSCInvalidStateError: If state is invalid, expired, or tampered
        """
        try:
            payload = jwt.decode(
                state,
                self._secret_key,
                algorithms=["HS256"],
            )
            user_id = payload.get("sub")
            if not user_id:
                raise GSCInvalidStateError("State missing user ID")
            redirect_uri = payload.get("redirect_uri")
            return user_id, redirect_uri
        except jwt.ExpiredSignatureError:
            raise GSCInvalidStateError("OAuth state has expired")
        except jwt.InvalidTokenError as e:
            raise GSCInvalidStateError(f"Invalid OAuth state: {e}")

    async def exchange_code(self, code: str) -> TokenResponse:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            TokenResponse with access_token, refresh_token, expires_in, etc.

        Raises:
            GSCTokenRefreshError: If token exchange fails
        """
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=data)

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
            raise GSCTokenRefreshError(f"Token exchange failed: {response.text}")

        result = response.json()
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_in=result["expires_in"],
            token_type=result["token_type"],
            scope=result.get("scope", GSC_SCOPE),
        )

    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh an expired access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            TokenResponse with new access_token (refresh_token may be None)

        Raises:
            GSCTokenRefreshError: If refresh fails
        """
        data = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=data)

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
            raise GSCTokenRefreshError(f"Token refresh failed: {response.text}")

        result = response.json()
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),  # May not be returned on refresh
            expires_in=result["expires_in"],
            token_type=result["token_type"],
            scope=result.get("scope", GSC_SCOPE),
        )

    def _create_state_jwt(self, user_id: str, redirect_uri: str | None = None) -> str:
        """Create a signed JWT for OAuth state parameter."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=STATE_EXPIRY_MINUTES)
        payload = {
            "sub": user_id,
            "exp": expire,
            "purpose": "gsc_oauth",
            "redirect_uri": redirect_uri,
        }
        return jwt.encode(payload, self._secret_key, algorithm="HS256")
