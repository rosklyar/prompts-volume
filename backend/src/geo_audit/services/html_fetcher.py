"""Service for fetching HTML content from URLs."""

import httpx

from src.geo_audit.exceptions import FetchError


class HtmlFetcher:
    """Fetches raw HTML from a URL using httpx."""

    def __init__(self, *, timeout: float = 15.0):
        self._timeout = timeout

    async def fetch(self, url: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    headers={"User-Agent": "GeoAuditBot/1.0"},
                )
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as e:
            raise FetchError(url=url, reason=str(e)) from e
