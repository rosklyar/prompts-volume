"""DataForSEO API service for fetching keywords."""

import base64
from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Optional

import httpx
from fastapi import HTTPException

from src.config.settings import settings


class DataForSEOService:
    """Service for interacting with DataForSEO Keywords API."""

    BASE_URL = "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_site/live"

    def __init__(self):
        """Initialize DataForSEO service with credentials."""
        self.username = settings.dataforseo_username
        self.password = settings.dataforseo_password

    def _get_auth_header(self) -> str:
        """
        Generate Basic Authentication header.

        Returns:
            Base64 encoded auth header value
        """
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _get_last_month_dates(self) -> tuple[str, str]:
        """
        Calculate date range for last full month.

        Returns:
            Tuple of (date_from, date_to) in YYYY-MM-DD format
        """
        today = datetime.now()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)

        date_from = first_day_last_month.strftime("%Y-%m-%d")
        date_to = last_day_last_month.strftime("%Y-%m-%d")

        return date_from, date_to

    async def get_keywords_for_site(
        self, target_url: str, location_name: Optional[str] = None
    ) -> List[str]:
        """
        Fetch keywords for a given URL from DataForSEO API.

        Args:
            target_url: The website URL to analyze (already validated)
            location_name: Optional location name for geo-targeted results

        Returns:
            List of keywords sorted by search volume (descending)

        Raises:
            HTTPException: If API call fails
        """
        date_from, date_to = self._get_last_month_dates()

        # Build request payload
        payload = [
            {
                "target": target_url,
                "date_from": date_from,
                "date_to": date_to,
                "sort_by": "search_volume",
            }
        ]

        # Add location_name if provided
        if location_name:
            payload[0]["location_name"] = location_name

        # Prepare headers
        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.BASE_URL, json=payload, headers=headers
                )

                # Handle API errors
                if response.status_code == 401:
                    raise HTTPException(
                        status_code=500,
                        detail="DataForSEO authentication failed. Check credentials.",
                    )
                elif response.status_code == 429:
                    raise HTTPException(
                        status_code=429,
                        detail="DataForSEO rate limit exceeded. Please try again later.",
                    )
                elif response.status_code != 200:
                    raise HTTPException(
                        status_code=500,
                        detail=f"DataForSEO API error: {response.status_code}",
                    )

                # Parse response
                data = response.json()

                # Extract keywords from response
                keywords = []
                if (
                    data.get("tasks")
                    and len(data["tasks"]) > 0
                    and data["tasks"][0].get("result")
                ):
                    for item in data["tasks"][0]["result"]:
                        if item.get("keyword"):
                            keywords.append(item["keyword"])

                return keywords

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504, detail="DataForSEO API request timed out"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to connect to DataForSEO API: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error calling DataForSEO API: {str(e)}"
            )


@lru_cache()
def get_dataforseo_service() -> DataForSEOService:
    """
    Dependency injection function for DataForSEO service.

    Uses lru_cache to create a singleton instance - the same instance
    is returned on every call, avoiding unnecessary instantiation.

    Returns:
        Singleton instance of DataForSEOService
    """
    return DataForSEOService()
