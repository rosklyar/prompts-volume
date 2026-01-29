"""OAuth-specific exceptions."""


class OAuthError(Exception):
    """Base exception for OAuth operations."""

    pass


class OAuthValidationError(OAuthError):
    """Raised when OAuth token validation fails.

    This covers:
    - Invalid token signature
    - Expired token
    - Wrong audience (client ID mismatch)
    - Missing required claims
    """

    def __init__(self, message: str, provider: str):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class OAuthProviderError(OAuthError):
    """Raised when OAuth provider communication fails."""

    def __init__(self, message: str, provider: str):
        self.provider = provider
        super().__init__(f"[{provider}] {message}")
