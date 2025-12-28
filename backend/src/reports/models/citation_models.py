"""Models for citation aggregation."""

from typing import List
from pydantic import BaseModel, Field


class CitationCountItemModel(BaseModel):
    """Count for a domain or path."""

    path: str = Field(
        ..., description="Domain or path (e.g., 'rozetka.com.ua/ua/mobile-phones')"
    )
    count: int = Field(..., description="Number of citations")
    is_domain: bool = Field(
        ..., description="True if domain-level, False if sub-path"
    )


class CitationLeaderboardModel(BaseModel):
    """Aggregated citation counts with separate domains and subpaths."""

    domains: List[CitationCountItemModel] = Field(
        ..., description="Domain-level citation counts, sorted by count descending"
    )
    subpaths: List[CitationCountItemModel] = Field(
        ..., description="Subpath-level citation counts, sorted by count descending"
    )
    total_citations: int = Field(..., description="Total citations processed")
