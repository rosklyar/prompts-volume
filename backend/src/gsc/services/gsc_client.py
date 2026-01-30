"""Google Search Console API client."""

import logging
from urllib.parse import quote

import httpx

from src.gsc.exceptions import GSCError
from src.gsc.models import GSCSiteInfo, SearchQueryRow

logger = logging.getLogger(__name__)

GSC_API_BASE = "https://www.googleapis.com/webmasters/v3"


class GSCClient:
    """Client for Google Search Console API.

    Uses httpx for async HTTP requests to GSC REST API.
    """

    async def list_sites(self, access_token: str) -> list[GSCSiteInfo]:
        """List all sites the user has access to in GSC.

        Args:
            access_token: Valid OAuth access token

        Returns:
            List of GSCSiteInfo with site URLs and permission levels

        Raises:
            GSCError: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GSC_API_BASE}/sites",
                headers=headers,
            )

        if response.status_code != 200:
            logger.error(f"GSC list sites failed: {response.status_code} - {response.text}")
            raise GSCError(f"Failed to list GSC sites: {response.text}")

        data = response.json()
        sites = []

        for entry in data.get("siteEntry", []):
            sites.append(
                GSCSiteInfo(
                    site_url=entry["siteUrl"],
                    permission_level=entry["permissionLevel"],
                )
            )

        return sites

    async def get_search_analytics(
        self,
        access_token: str,
        *,
        site_url: str,
        start_date: str,
        end_date: str,
        row_limit: int = 100,
    ) -> list[SearchQueryRow]:
        """Get search analytics data for a site.

        Args:
            access_token: Valid OAuth access token
            site_url: The site URL (e.g., "sc-domain:example.com" or "https://example.com/")
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            row_limit: Maximum number of rows to return (default 100)

        Returns:
            List of SearchQueryRow with query metrics

        Raises:
            GSCError: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # URL-encode the site_url for the path
        encoded_site_url = quote(site_url, safe="")

        request_body = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query"],
            "rowLimit": row_limit,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GSC_API_BASE}/sites/{encoded_site_url}/searchAnalytics/query",
                headers=headers,
                json=request_body,
            )

        if response.status_code != 200:
            logger.error(f"GSC search analytics failed: {response.status_code} - {response.text}")
            raise GSCError(f"Failed to get search analytics: {response.text}")

        data = response.json()
        rows = []

        for row in data.get("rows", []):
            rows.append(
                SearchQueryRow(
                    keys=row.get("keys", []),
                    clicks=row.get("clicks", 0),
                    impressions=row.get("impressions", 0),
                    ctr=row.get("ctr", 0.0),
                    position=row.get("position", 0.0),
                )
            )

        return rows
