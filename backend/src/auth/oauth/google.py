"""Google OAuth token validation."""

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from src.auth.oauth.exceptions import OAuthValidationError
from src.auth.oauth.protocols import OAuthUserInfo


class GoogleTokenValidator:
    """Validates Google ID tokens using Google's public keys.

    Uses google-auth library to verify:
    - Token signature against Google's public keys
    - Token expiration
    - Audience matches our client ID
    - Issuer is accounts.google.com

    Thread-safe and cacheable - Google's library handles key caching.
    """

    def __init__(self, *, client_id: str):
        """Initialize with Google OAuth client ID.

        Args:
            client_id: Google OAuth 2.0 Client ID from Google Cloud Console
        """
        self._client_id = client_id

    @property
    def provider_name(self) -> str:
        return "google"

    async def validate_token(self, id_token: str) -> OAuthUserInfo:
        """Validate Google ID token and extract user claims.

        Args:
            id_token: JWT from Google Sign-In (from frontend)

        Returns:
            OAuthUserInfo with Google account details

        Raises:
            OAuthValidationError: If token invalid or audience mismatch
        """
        try:
            # Google's library handles signature verification, expiry, and issuer
            idinfo = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                self._client_id,
            )

            # Verify email is present and verified
            email = idinfo.get("email")
            if not email:
                raise OAuthValidationError("Token missing email claim", self.provider_name)

            email_verified = idinfo.get("email_verified", False)
            if not email_verified:
                raise OAuthValidationError(
                    "Email not verified by Google", self.provider_name
                )

            return OAuthUserInfo(
                provider=self.provider_name,
                provider_user_id=idinfo["sub"],
                email=email.lower(),
                email_verified=True,  # Google verified it
                full_name=idinfo.get("name"),
                picture_url=idinfo.get("picture"),
            )

        except ValueError as e:
            raise OAuthValidationError(str(e), self.provider_name) from e
