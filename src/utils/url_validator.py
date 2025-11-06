"""URL validation and normalization utilities."""

import httpx
from fastapi import HTTPException
from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    """
    Extract bare domain from URL (without protocol, www, or path).

    Args:
        url: The URL to extract domain from (can include or exclude scheme)

    Returns:
        Bare domain (e.g., "example.com", "moyo.ua")

    Examples:
        >>> extract_domain("https://www.example.com/path")
        "example.com"
        >>> extract_domain("moyo.ua")
        "moyo.ua"
        >>> extract_domain("https://subdomain.example.com")
        "subdomain.example.com"
    """
    # Add scheme if missing for urlparse to work correctly
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path

    # Remove www. prefix if present
    if domain.startswith("www."):
        domain = domain[4:]

    return domain


async def validate_url(url: str) -> str:
    """
    Validate and normalize a URL.

    Args:
        url: The URL to validate (with or without scheme)

    Returns:
        The normalized URL with scheme

    Raises:
        HTTPException: If URL is invalid or unreachable
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")

    # Add scheme if missing
    normalized_url = url
    if not url.startswith(("http://", "https://")):
        normalized_url = f"https://{url}"

    # Parse URL to validate format
    try:
        parsed = urlparse(normalized_url)
        if not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format")

    # Verify domain is reachable
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.head(normalized_url, follow_redirects=True)
            # Accept any response that means the server exists (2xx, 3xx, 4xx, but not connection errors)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.UnsupportedProtocol):
        raise HTTPException(status_code=400, detail="Domain is unreachable or does not exist")
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to validate domain")

    return url
