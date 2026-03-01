"""DataForSEO API service for fetching ranked keywords."""

import base64
import logging
from dataclasses import dataclass
from typing import List

import httpx
from fastapi import HTTPException

from src.config.settings import settings

logger = logging.getLogger(__name__)


class DataForSEOPaymentError(Exception):
    """Raised when DataForSEO returns 402 (no credits)."""


@dataclass(frozen=True)
class RankedKeywordData:
    """Keyword with search volume and ranking position from DataForSEO."""

    keyword: str
    search_volume: int
    rank_group: int


class DataForSEOService:
    """Service for interacting with DataForSEO Labs Ranked Keywords API."""

    def __init__(
        self,
        username: str,
        password: str,
        base_url: str
    ):
        self.username = username
        self.password = password
        self.base_url = base_url

    def _get_auth_header(self) -> str:
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def _make_api_call(
        self,
        target_domain: str,
        location_name: str,
        language: str,
        limit: int,
        offset: int,
        timeout: float,
    ) -> list[dict]:
        """Make a single API call and return raw items list.

        Returns:
            List of raw item dicts from the API response.

        Raises:
            HTTPException: If API call fails.
        """
        payload = [
            {
                "target": target_domain,
                "location_name": location_name,
                "language_name": language,
                "ignore_synonyms": True,
                "item_types": ["organic"],
                "limit": limit,
                "offset": offset,
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
                elif response.status_code == 402:
                    raise DataForSEOPaymentError(
                        "DataForSEO has no credits (402 Payment Required)"
                    )
                elif response.status_code != 200:
                    raise HTTPException(
                        status_code=500,
                        detail=f"DataForSEO API error: {response.status_code}",
                    )

                data = response.json()

                if (
                    data.get("tasks")
                    and len(data["tasks"]) > 0
                    and data["tasks"][0].get("result")
                    and len(data["tasks"][0]["result"]) > 0
                    and data["tasks"][0]["result"][0].get("items")
                ):
                    return data["tasks"][0]["result"][0]["items"]

                return []

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504, detail="DataForSEO API request timed out"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to connect to DataForSEO API: {str(e)}"
            )
        except HTTPException:
            raise
        except DataForSEOPaymentError:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Unexpected error calling DataForSEO API: {str(e)}"
            )

    async def _fetch_keywords_batch(
        self,
        target_domain: str,
        location_name: str,
        language: str,
        limit: int,
        offset: int,
        timeout: float,
    ) -> List[str]:
        """Fetch a single batch of keyword strings from DataForSEO API."""
        items = await self._make_api_call(
            target_domain, location_name, language, limit, offset, timeout
        )
        keywords = []
        for item in items:
            keyword = item.get("keyword_data", {}).get("keyword")
            if keyword:
                keywords.append(keyword)
        return keywords

    async def _fetch_ranked_keywords_batch(
        self,
        target_domain: str,
        location_name: str,
        language: str,
        limit: int,
        offset: int,
        timeout: float,
    ) -> list[RankedKeywordData]:
        """Fetch a single batch of ranked keywords with search volume and rank."""
        items = await self._make_api_call(
            target_domain, location_name, language, limit, offset, timeout
        )
        ranked = []
        for item in items:
            keyword_data = item.get("keyword_data", {})
            keyword = keyword_data.get("keyword")
            if not keyword:
                continue
            search_volume = keyword_data.get("keyword_info", {}).get("search_volume", 0) or 0
            rank_group = item.get("rank_group", 0) or 0
            ranked.append(RankedKeywordData(
                keyword=keyword,
                search_volume=search_volume,
                rank_group=rank_group,
            ))
        return ranked

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

    async def get_all_ranked_keywords_for_site(
        self,
        target_domain: str,
        location_name: str,
        language: str,
        batch_size: int,
        max_total: int,
        timeout: float,
    ) -> list[RankedKeywordData]:
        """Fetch all ranked keywords with search volume and rank position.

        Same pagination logic as get_all_keywords_for_site but returns
        RankedKeywordData with search_volume and rank_group.
        """
        all_keywords: list[RankedKeywordData] = []
        offset = 0

        logger.info(
            f"Starting ranked keyword fetch for {target_domain} "
            f"(batch_size={batch_size}, max_total={max_total})"
        )

        while len(all_keywords) < max_total:
            batch = await self._fetch_ranked_keywords_batch(
                target_domain=target_domain,
                location_name=location_name,
                language=language,
                limit=batch_size,
                offset=offset,
                timeout=timeout,
            )

            logger.info(
                f"Fetched ranked batch at offset={offset}: {len(batch)} keywords "
                f"(total so far: {len(all_keywords) + len(batch)})"
            )

            if not batch:
                break

            all_keywords.extend(batch)

            if len(batch) < batch_size:
                break

            offset += batch_size

        if len(all_keywords) > max_total:
            all_keywords = all_keywords[:max_total]

        logger.info(f"Ranked fetch complete: {len(all_keywords)} total keywords")
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
