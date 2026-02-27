"""Domain models for keyword inspiration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RankedKeyword:
    """A keyword with search volume and ranking position."""

    keyword: str
    search_volume: int
    rank_group: int


@dataclass(frozen=True)
class ScoredCluster:
    """A cluster of keywords scored by SEO relevance."""

    cluster_id: int
    keywords: list[str]
    score: float  # sum(search_volume) for keywords where rank_group <= 3
    title: str  # keyword with highest search_volume
    keyword_count: int
