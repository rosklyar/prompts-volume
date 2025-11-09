"""Utility functions for filtering keywords."""

import logging
from typing import List

logger = logging.getLogger(__name__)


def filter_by_word_count(keywords: List[str], min_words: int = 3) -> List[str]:
    """
    Filter keywords by minimum word count.

    Args:
        keywords: List of keywords to filter
        min_words: Minimum number of words required (default: 3)

    Returns:
        Filtered list of keywords with at least min_words

    Example:
        >>> filter_by_word_count(["tv", "smart tv 4k", "laptop"], min_words=2)
        ['smart tv 4k', 'laptop']
    """
    return [kw for kw in keywords if len(kw.split()) >= min_words]


def filter_by_brand_exclusion(
    keywords: List[str], brand_variations: List[str]
) -> List[str]:
    """
    Filter out keywords containing any brand name variations.

    Args:
        keywords: List of keywords to filter
        brand_variations: List of brand name variations to exclude (case-insensitive)

    Returns:
        Filtered list of keywords without brand mentions

    Example:
        >>> filter_by_brand_exclusion(
        ...     ["laptop dell", "moyo київ", "мойо доставка", "smart tv"],
        ...     ["moyo", "мойо"]
        ... )
        ['laptop dell', 'smart tv']
    """
    brand_variations_lower = [v.lower() for v in brand_variations]
    return [
        kw
        for kw in keywords
        if not any(brand in kw.lower() for brand in brand_variations_lower)
    ]


def deduplicate_keywords(keywords: List[str]) -> List[str]:
    """
    Remove duplicate keywords while preserving order.

    Uses case-sensitive comparison (preserves first occurrence).

    Args:
        keywords: List of keywords (may contain duplicates)

    Returns:
        List of unique keywords in original order

    Example:
        >>> deduplicate_keywords(["laptop", "phone", "laptop", "tv"])
        ['laptop', 'phone', 'tv']
    """
    seen = set()
    result = []
    duplicates = 0

    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
        else:
            duplicates += 1

    if duplicates > 0:
        logger.info(
            f"Removed {duplicates} duplicate keywords ({len(result)} unique remaining)"
        )

    return result
