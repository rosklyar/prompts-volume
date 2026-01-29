"""OAuth authentication protocols and data types."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OAuthUserInfo:
    """Validated user information from an OAuth provider.

    Immutable value object containing verified claims from the OAuth token.
    """

    provider: str  # e.g., "google", "apple"
    provider_user_id: str  # Unique ID from provider (sub claim)
    email: str  # Verified email address
    email_verified: bool  # Whether provider verified the email
    full_name: str | None  # Display name if available
    picture_url: str | None  # Profile picture URL if available


class OAuthTokenValidator(Protocol):
    """Protocol for validating OAuth tokens from external providers.

    Implementations must validate the token's signature, expiration,
    and audience claims before extracting user information.

    Each OAuth provider (Google, Apple, GitHub) has a different
    token validation mechanism, so this protocol allows swapping
    implementations without changing the authentication flow.
    """

    @property
    def provider_name(self) -> str:
        """Return the provider identifier (e.g., 'google', 'apple')."""
        ...

    async def validate_token(self, id_token: str) -> OAuthUserInfo:
        """Validate an OAuth ID token and extract user information.

        Args:
            id_token: The raw ID token from the OAuth provider

        Returns:
            OAuthUserInfo with validated claims

        Raises:
            OAuthValidationError: If token is invalid, expired,
                                  or audience mismatch
        """
        ...
