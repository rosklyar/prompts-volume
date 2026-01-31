"""Service for extracting keywords from GSC."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from src.gsc.models import SearchQueryRow
from src.gsc.services.gsc_client import GSCClient
from src.gsc.services.keyword_filter import KeywordFilter


@dataclass(frozen=True)
class ExtractedKeywords:
    """Result of keyword extraction.

    Attributes:
        keywords: Filtered keyword rows
        total_fetched: Number of rows fetched from GSC
        total_after_filter: Number of rows after filtering
    """

    keywords: list[SearchQueryRow]
    total_fetched: int
    total_after_filter: int


class KeywordExtractor:
    """Extracts and filters keywords from GSC search analytics.

    Combines GSC API calls with keyword filtering to extract
    long-tail keywords suitable for prompt creation.
    """

    def __init__(
        self,
        gsc_client: GSCClient,
        keyword_filter: KeywordFilter,
    ):
        """Initialize extractor with dependencies.

        Args:
            gsc_client: GSC API client
            keyword_filter: Filter to apply to extracted keywords
        """
        self._gsc_client = gsc_client
        self._keyword_filter = keyword_filter

    async def extract(
        self,
        access_token: str,
        site_url: str,
        *,
        days_back: int = 28,
        fetch_limit: int = 500,
        result_limit: int = 10,
    ) -> ExtractedKeywords:
        """Extract and filter keywords from GSC.

        Args:
            access_token: Valid OAuth access token
            site_url: GSC property URL
            days_back: Number of days of data to fetch (default: 28)
            fetch_limit: Max rows to fetch from GSC API (default: 500)
            result_limit: Max filtered keywords to return (default: 10)

        Returns:
            ExtractedKeywords with filtered results and counts
        """
        # Calculate date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)

        # Fetch from GSC
        rows = await self._gsc_client.get_search_analytics(
            access_token,
            site_url=site_url,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            row_limit=fetch_limit,
        )

        total_fetched = len(rows)

        # Apply filter
        filtered = self._keyword_filter.filter(rows)
        total_after_filter = len(filtered)

        # Apply result limit
        limited = filtered[:result_limit]

        return ExtractedKeywords(
            keywords=limited,
            total_fetched=total_fetched,
            total_after_filter=total_after_filter,
        )
