"""Competitor discovery orchestrator service."""

import logging
from typing import List

from src.onboarding.services.competitor_discovery.models import DiscoveredCompetitor
from src.onboarding.services.competitor_discovery.protocols import (
    BrandVariationGenerator,
    CompetitorSearcher,
)

logger = logging.getLogger(__name__)


class CompetitorDiscoveryService:
    """Orchestrates competitor discovery and variation generation."""

    def __init__(
        self,
        *,
        searcher: CompetitorSearcher,
        variation_generator: BrandVariationGenerator,
    ):
        self._searcher = searcher
        self._variation_generator = variation_generator

    async def discover_competitors(
        self,
        *,
        brand_name: str,
        brand_domain: str,
        country_name: str,
        languages: List[str],
        num_competitors: int = 5,
    ) -> List[DiscoveredCompetitor]:
        """Discover competitors and generate variations for each.

        Args:
            brand_name: The brand name to find competitors for
            brand_domain: The brand's website domain
            country_name: Country name for localized search
            languages: Languages for variation generation
            num_competitors: Number of competitors to discover

        Returns:
            List of discovered competitors with variations
        """
        # Ensure English is always included
        if "English" not in languages:
            languages = ["English"] + list(languages)

        # Search for competitors
        raw_competitors = await self._searcher.search(
            brand_name=brand_name,
            brand_domain=brand_domain,
            country_name=country_name,
            num_competitors=num_competitors,
        )

        if not raw_competitors:
            logger.info(f"No competitors found for '{brand_name}'")
            return []

        # Generate variations for all competitors in a single batch call
        competitor_names = [c.name for c in raw_competitors]
        variations_map = await self._variation_generator.generate_batch(
            brand_names=competitor_names,
            languages=languages,
        )

        # Build discovered competitors with variations
        discovered = [
            DiscoveredCompetitor(
                brand_name=competitor.name,
                domain=competitor.domain,
                variations=variations_map.get(competitor.name, []),
            )
            for competitor in raw_competitors
        ]

        logger.info(
            f"Discovered {len(discovered)} competitors for '{brand_name}'"
        )
        return discovered
