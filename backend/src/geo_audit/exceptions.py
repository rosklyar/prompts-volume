"""GEO audit domain exceptions."""


class GeoAuditError(Exception):
    """Base exception for GEO audit module."""


class FetchError(GeoAuditError):
    """Raised when HTML cannot be fetched from the target URL."""

    def __init__(self, *, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to fetch {url}: {reason}")
