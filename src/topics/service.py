"""DataForSEO API service for fetching ranked keywords."""

import base64
from functools import lru_cache
from typing import List

import httpx
from fastapi import HTTPException

from src.config.settings import settings


class DataForSEOService:
    """Service for interacting with DataForSEO Labs Ranked Keywords API."""

    BASE_URL = "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"

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

    async def get_keywords_for_site(
        self,
        target_domain: str,
        location_name: str,
        language: str,
        limit: int = 1000
    ) -> List[str]:
        """
        Fetch keywords where the domain currently ranks in Google organic search.

        Uses DataForSEO Labs Ranked Keywords API to get actual ranking keywords.

        Args:
            target_domain: Bare domain to analyze (e.g., "moyo.ua", "example.com")
            location_name: Optional location name for geo-targeted results
            language: Optional language name for language-specific results

        Returns:
            List of keywords where the domain ranks in organic search

        Raises:
            HTTPException: If API call fails
        """

        # Build request payload for ranked_keywords API
        payload = [
            {
                "target": target_domain,
                "location_name": location_name,
                "language_name": language,
                "ignore_synonyms": True,
                "item_types": ["organic"],
                "limit": limit 
            }
        ]
        
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

                # Extract keywords from ranked_keywords response structure
                # Structure: tasks[0].result[0].items[].keyword_data.keyword
                keywords = []
                if (
                    data.get("tasks")
                    and len(data["tasks"]) > 0
                    and data["tasks"][0].get("result")
                    and len(data["tasks"][0]["result"]) > 0
                    and data["tasks"][0]["result"][0].get("items")
                ):
                    for item in data["tasks"][0]["result"][0]["items"]:
                        keyword_data = item.get("keyword_data", {})
                        keyword = keyword_data.get("keyword")
                        if keyword:
                            keywords.append(keyword)

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
