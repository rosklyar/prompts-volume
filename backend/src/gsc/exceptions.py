"""GSC-specific exceptions."""


class GSCError(Exception):
    """Base exception for GSC module."""


class GSCNotConnectedError(GSCError):
    """User has not connected their GSC account."""


class GSCTokenExpiredError(GSCError):
    """OAuth token has expired and refresh failed."""


class GSCTokenRefreshError(GSCError):
    """Failed to refresh OAuth token."""


class GSCInvalidStateError(GSCError):
    """Invalid or expired OAuth state parameter."""


class GSCConfigurationError(GSCError):
    """GSC is not properly configured."""
