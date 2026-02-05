"""Protocols for competitor discovery components."""

from typing import Dict, List, Protocol

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


class BrandVariationGenerator(Protocol):
    """Protocol for generating brand name variations."""

    async def generate_batch(
        self,
        *,
        brand_names: List[str],
        languages: List[str],
    ) -> Dict[str, List[str]]:
        """Generate variations for multiple brand names in a single call.

        Args:
            brand_names: List of brand names to generate variations for
            languages: Languages for variation generation

        Returns:
            Dictionary mapping brand names to their variations
        """
        ...
