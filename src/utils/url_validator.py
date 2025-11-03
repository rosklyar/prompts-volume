"""URL validation and normalization utilities."""

import httpx
from fastapi import HTTPException
from urllib.parse import urlparse


async def validate_and_normalize_url(url: str) -> str:
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

    return normalized_url
