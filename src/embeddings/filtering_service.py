"""Service for filtering keywords before embeddings/clustering."""

import logging
from typing import List

logger = logging.getLogger(__name__)


class KeywordFilteringService:
    """
    Service for preparing keywords for embedding and clustering.

    Filters out:
    - Keywords with less than 3 words (too short for semantic analysis)
    - Keywords containing brand name (we want generic search terms)
    """

    def __init__(self, brand_name: str):
        """
        Initialize filtering service.

        Args:
            brand_name: Brand name to exclude (case-insensitive)
        """
        self.brand_name = brand_name.lower()
        logger.info(f"Initialized KeywordFilteringService with brand_name='{brand_name}'")

    def filter_keywords(self, keywords: List[str], min_words: int = 3) -> List[str]:
        """
        Filter keywords for embedding preparation.

        Args:
            keywords: List of keywords to filter
            min_words: Minimum number of words required (default: 3)

        Returns:
            List of filtered keywords

        Example:
            >>> service = KeywordFilteringService("moyo")
            >>> keywords = ["телевізор", "moyo київ", "смартфон самсунг 5g", "ноутбук для роботи"]
            >>> service.filter_keywords(keywords)
            ['смартфон самсунг 5g', 'ноутбук для роботи']  # Filtered: short + brand mention
        """
        filtered = []

        for keyword in keywords:
            # Check word count
            word_count = len(keyword.split())
            if word_count < min_words:
                continue

            # Check brand name (case-insensitive)
            if self.brand_name in keyword.lower():
                continue

            filtered.append(keyword)

        logger.info(
            f"Filtered {len(keywords)} keywords → {len(filtered)} "
            f"(removed {len(keywords) - len(filtered)}: "
            f"{len(keywords) - len(filtered) - self._count_brand_mentions(keywords)} short, "
            f"{self._count_brand_mentions(keywords)} with brand)"
        )

        return filtered

    def _count_brand_mentions(self, keywords: List[str]) -> int:
        """Count how many keywords contain the brand name."""
        return sum(1 for kw in keywords if self.brand_name in kw.lower())

    def get_filter_stats(self, keywords: List[str], min_words: int = 3) -> dict:
        """
        Get statistics about what would be filtered.

        Args:
            keywords: List of keywords to analyze
            min_words: Minimum word count threshold

        Returns:
            Dictionary with filtering statistics
        """
        total = len(keywords)
        short_keywords = sum(1 for kw in keywords if len(kw.split()) < min_words)
        brand_keywords = self._count_brand_mentions(keywords)
        both = sum(
            1 for kw in keywords
            if len(kw.split()) < min_words and self.brand_name in kw.lower()
        )

        filtered = self.filter_keywords(keywords, min_words)

        return {
            "total": total,
            "filtered": len(filtered),
            "removed_total": total - len(filtered),
            "removed_short": short_keywords,
            "removed_brand": brand_keywords,
            "removed_both": both,
            "min_words": min_words,
            "brand_name": self.brand_name,
        }
