"""DataForSEO API service for fetching ranked keywords."""

import base64
import logging
from typing import List

import httpx
from fastapi import HTTPException

from src.config.settings import settings

logger = logging.getLogger(__name__)


class DataForSEOService:
    """Service for interacting with DataForSEO Labs Ranked Keywords API."""

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str
    ):
        """Initialize DataForSEO service with credentials.

        Args:
            username: DataForSEO API username
            password: DataForSEO API password
            base_url: DataForSEO API base URL
        """
        self.username = username
        self.password = password
        self.base_url = base_url

    def _get_auth_header(self) -> str:
        """
        Generate Basic Authentication header.

        Returns:
            Base64 encoded auth header value
        """
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def _fetch_keywords_batch(
        self,
        target_domain: str,
        location_name: str,
        language: str,
        limit: int,
        offset: int,
        timeout: float
    ) -> List[str]:
        """
        Fetch a single batch of keywords from DataForSEO API.

        Args:
            target_domain: Domain to analyze (e.g., "moyo.ua", "example.com")
            location_name: Location name for geo-targeting
            language: Language name
            limit: Number of keywords to fetch in this batch
            offset: Starting offset for pagination
            timeout: Request timeout in seconds

        Returns:
            List of keywords from this batch

        Raises:
            HTTPException: If API call fails
        """
        # Build request payload
        payload = [
            {
                "target": target_domain,
                "location_name": location_name,
                "language_name": language,
                "ignore_synonyms": True,
                "item_types": ["organic"],
                "limit": limit,
                "offset": offset
            }
        ]

        headers = {
            "Authorization": self._get_auth_header(),
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.base_url, json=payload, headers=headers
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
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error calling DataForSEO API: {str(e)}"
            )

    async def get_all_keywords_for_site(
        self,
        target_domain: str,
        location_name: str,
        language: str,
        batch_size: int,
        max_total: int,
        timeout: float
    ) -> List[str]:
        """
        Fetch ALL keywords with pagination using offset-based approach.

        Makes multiple API calls with offset/limit until:
        - No more keywords available (batch returns less than batch_size)
        - OR max_total limit reached

        Args:
            target_domain: Bare domain to analyze (e.g., "moyo.ua", "example.com")
            location_name: Location name for geo-targeted results
            language: Language name for language-specific results
            batch_size: Keywords per request (max: 1000)
            max_total: Maximum total keywords to fetch
            timeout: Request timeout in seconds

        Returns:
            List of all keywords (up to max_total)

        Raises:
            HTTPException: If API call fails
        """
        all_keywords = []
        offset = 0

        logger.info(
            f"Starting paginated keyword fetch for {target_domain} "
            f"(batch_size={batch_size}, max_total={max_total})"
        )

        while len(all_keywords) < max_total:
            batch_keywords = await self._fetch_keywords_batch(
                target_domain=target_domain,
                location_name=location_name,
                language=language,
                limit=batch_size,
                offset=offset,
                timeout=timeout
            )

            logger.info(
                f"Fetched batch at offset={offset}: {len(batch_keywords)} keywords "
                f"(total so far: {len(all_keywords) + len(batch_keywords)})"
            )

            # No more keywords available
            if not batch_keywords:
                logger.info("No more keywords available, stopping pagination")
                break

            # Add batch to results
            all_keywords.extend(batch_keywords)

            # Stop if we got less than batch_size (last page)
            if len(batch_keywords) < batch_size:
                logger.info(
                    f"Received partial batch ({len(batch_keywords)} < {batch_size}), "
                    "assuming last page"
                )
                break

            # Move to next batch
            offset += batch_size

            # Stop if we've reached max_total
            if len(all_keywords) >= max_total:
                logger.info(f"Reached max_total limit ({max_total}), stopping pagination")
                break

        # Trim to max_total if we exceeded
        if len(all_keywords) > max_total:
            all_keywords = all_keywords[:max_total]

        logger.info(f"Pagination complete: fetched {len(all_keywords)} total keywords")
        return all_keywords


# Global instance for dependency injection
_dataforseo_service = None


def get_dataforseo_service() -> DataForSEOService:
    """
    Get the global DataForSEOService instance.
    Creates one if it doesn't exist yet.

    Configuration is loaded from settings on first instantiation.

    Returns:
        DataForSEOService instance
    """
    global _dataforseo_service
    if _dataforseo_service is None:
        _dataforseo_service = DataForSEOService(
            username=settings.dataforseo_username,
            password=settings.dataforseo_password,
            base_url=settings.dataforseo_base_url
        )
    return _dataforseo_service
