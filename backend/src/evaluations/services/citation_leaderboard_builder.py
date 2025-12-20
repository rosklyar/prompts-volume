"""Citation leaderboard builder service."""

from collections import Counter
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse


@dataclass
class CitationInput:
    """Single citation from evaluation answer."""

    url: str
    text: str


@dataclass
class CitationCountItem:
    """Count for a domain or path."""

    path: str
    count: int
    is_domain: bool


@dataclass
class CitationLeaderboard:
    """Aggregated citation counts."""

    items: List[CitationCountItem]
    total_citations: int


class CitationLeaderboardBuilder:
    """Builds citation leaderboard by aggregating URL patterns."""

    def __init__(self, max_path_depth: int = 2):
        """
        Initialize the builder.

        Args:
            max_path_depth: Maximum path segments to include in aggregation.
                           e.g., depth=2 for "domain.com/a/b" from "domain.com/a/b/c/d"
        """
        self.max_path_depth = max_path_depth

    def aggregate(self, citations: List[CitationInput]) -> CitationLeaderboard:
        """
        Aggregate citations by domain and sub-path.

        Returns counts for:
        1. Domain level (e.g., "rozetka.com.ua")
        2. Path levels up to max_path_depth (e.g., "rozetka.com.ua/ua/mobile-phones")

        Args:
            citations: List of citation URLs from evaluation results

        Returns:
            CitationLeaderboard with counts per domain and significant paths
        """
        if not citations:
            return CitationLeaderboard(items=[], total_citations=0)

        domain_counts: Counter[str] = Counter()
        path_counts: Counter[str] = Counter()

        for citation in citations:
            paths = self._extract_paths(citation.url)
            if not paths:
                continue

            # First path is always domain-level
            domain_counts[paths[0]] += 1

            # Remaining paths are sub-paths
            for path in paths[1:]:
                path_counts[path] += 1

        # Build items list
        items = []

        # Add domain-level counts
        for path, count in domain_counts.items():
            items.append(CitationCountItem(path=path, count=count, is_domain=True))

        # Add path-level counts
        for path, count in path_counts.items():
            items.append(CitationCountItem(path=path, count=count, is_domain=False))

        # Sort by count descending, then alphabetically
        items.sort(key=lambda x: (-x.count, x.path))

        return CitationLeaderboard(
            items=items, total_citations=sum(domain_counts.values())
        )

    def _extract_paths(self, url: str) -> List[str]:
        """
        Extract domain and path prefixes from URL.

        Returns list like:
        ["rozetka.com.ua", "rozetka.com.ua/ua", "rozetka.com.ua/ua/mobile-phones"]
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            if not domain:
                return []

            paths = [domain]

            # Extract path segments
            path_parts = [p for p in parsed.path.split("/") if p]

            # Build hierarchical paths up to max depth
            current_path = domain
            for part in path_parts[: self.max_path_depth]:
                current_path = f"{current_path}/{part}"
                paths.append(current_path)

            return paths

        except Exception:
            return []


def get_citation_leaderboard_builder() -> CitationLeaderboardBuilder:
    """Dependency injection for CitationLeaderboardBuilder."""
    return CitationLeaderboardBuilder(max_path_depth=2)
