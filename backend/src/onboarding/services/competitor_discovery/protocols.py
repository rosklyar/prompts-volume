"""Protocols for competitor discovery components."""

from typing import List, Protocol

from src.onboarding.services.competitor_discovery.models import RawCompetitor


class CompetitorSearcher(Protocol):
    """Protocol for searching competitors."""

    async def search(
        self,
        *,
        brand_name: str,
        brand_domain: str,
        country_name: str,
        num_competitors: int = 5,
    ) -> List[RawCompetitor]:
        """Search for competitors of a brand."""
        ...
