"""Filters for GSC keyword extraction."""

from typing import Protocol

from src.gsc.models import SearchQueryRow


class KeywordFilter(Protocol):
    """Protocol for keyword filtering strategies."""

    def filter(self, rows: list[SearchQueryRow]) -> list[SearchQueryRow]:
        """Filter search query rows based on implementation-specific criteria."""
        ...


class MinWordCountFilter:
    """Filter keywords by minimum word count.

    Long-tail keywords (3+ words) typically indicate higher intent
    and are more valuable for prompt tracking.
    """

    def __init__(self, min_words: int = 3):
        """Initialize filter with minimum word count.

        Args:
            min_words: Minimum number of words required (default: 3)
        """
        if min_words < 1:
            raise ValueError("min_words must be at least 1")
        self._min_words = min_words

    def filter(self, rows: list[SearchQueryRow]) -> list[SearchQueryRow]:
        """Filter rows to only include queries with enough words.

        Args:
            rows: List of search query rows from GSC

        Returns:
            Filtered list with only long-tail keywords
        """
        result = []
        for row in rows:
            # Get the query text (first key)
            if not row.keys:
                continue
            query = row.keys[0]
            word_count = len(query.split())
            if word_count >= self._min_words:
                result.append(row)
        return result


class CompositeFilter:
    """Combines multiple filters with AND logic."""

    def __init__(self, filters: list[KeywordFilter]):
        """Initialize with list of filters to apply.

        Args:
            filters: List of KeywordFilter instances
        """
        self._filters = filters

    def filter(self, rows: list[SearchQueryRow]) -> list[SearchQueryRow]:
        """Apply all filters sequentially.

        Args:
            rows: List of search query rows

        Returns:
            Rows that pass all filters
        """
        result = rows
        for f in self._filters:
            result = f.filter(result)
        return result
