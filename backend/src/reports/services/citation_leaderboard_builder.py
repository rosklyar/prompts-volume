"""Citation leaderboard builder service."""

from collections import Counter, defaultdict
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
    unique_answer_count: int = 0  # answers containing this domain/path
    coverage_percent: float = 0.0  # (unique_answer_count / total_answers) * 100


@dataclass
class CitationLeaderboard:
    """Aggregated citation counts with separate domains and subpaths."""

    domains: List[CitationCountItem]
    subpaths: List[CitationCountItem]
    total_citations: int
    total_answers: int = 0


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

    def aggregate(
        self, citations_by_answer: List[List[CitationInput]]
    ) -> CitationLeaderboard:
        """
        Aggregate citations by domain and sub-path.

        Returns counts for:
        1. Domain level (e.g., "rozetka.com.ua")
        2. Path levels up to max_path_depth (e.g., "rozetka.com.ua/ua/mobile-phones")

        Args:
            citations_by_answer: List of citation lists (one per answer) to track coverage

        Returns:
            CitationLeaderboard with counts per domain and significant paths (separated)
        """
        total_answers = len(citations_by_answer)
        if total_answers == 0:
            return CitationLeaderboard(
                domains=[], subpaths=[], total_citations=0, total_answers=0
            )

        domain_counts: Counter[str] = Counter()
        path_counts: Counter[str] = Counter()

        # Track which answers contain each domain/path for coverage calculation
        domain_to_answers: dict[str, set[int]] = defaultdict(set)
        path_to_answers: dict[str, set[int]] = defaultdict(set)

        for answer_idx, citations in enumerate(citations_by_answer):
            for citation in citations:
                paths = self._extract_paths(citation.url)
                if not paths:
                    continue

                # First path is always domain-level
                domain_counts[paths[0]] += 1
                domain_to_answers[paths[0]].add(answer_idx)

                # Remaining paths are sub-paths
                for path in paths[1:]:
                    path_counts[path] += 1
                    path_to_answers[path].add(answer_idx)

        # Build domain items list with coverage
        domain_items = []
        for path, count in domain_counts.items():
            unique_answer_count = len(domain_to_answers[path])
            coverage = (unique_answer_count / total_answers * 100) if total_answers else 0
            domain_items.append(
                CitationCountItem(
                    path=path,
                    count=count,
                    is_domain=True,
                    unique_answer_count=unique_answer_count,
                    coverage_percent=round(coverage, 1),
                )
            )

        # Build subpath items list with coverage
        subpath_items = []
        for path, count in path_counts.items():
            unique_answer_count = len(path_to_answers[path])
            coverage = (unique_answer_count / total_answers * 100) if total_answers else 0
            subpath_items.append(
                CitationCountItem(
                    path=path,
                    count=count,
                    is_domain=False,
                    unique_answer_count=unique_answer_count,
                    coverage_percent=round(coverage, 1),
                )
            )

        # Sort by count descending, then alphabetically
        domain_items.sort(key=lambda x: (-x.count, x.path))
        subpath_items.sort(key=lambda x: (-x.count, x.path))

        return CitationLeaderboard(
            domains=domain_items,
            subpaths=subpath_items,
            total_citations=sum(domain_counts.values()),
            total_answers=total_answers,
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


# Singleton instance
_citation_leaderboard_builder: CitationLeaderboardBuilder | None = None


def get_citation_leaderboard_builder() -> CitationLeaderboardBuilder:
    """Get the singleton CitationLeaderboardBuilder instance."""
    global _citation_leaderboard_builder
    if _citation_leaderboard_builder is None:
        _citation_leaderboard_builder = CitationLeaderboardBuilder(max_path_depth=2)
    return _citation_leaderboard_builder
