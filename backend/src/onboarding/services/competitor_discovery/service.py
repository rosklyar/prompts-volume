"""Competitor discovery orchestrator service."""

import logging
from typing import List

from src.onboarding.services.competitor_discovery.models import DiscoveredCompetitor
from src.onboarding.services.competitor_discovery.protocols import (
    CompetitorSearcher,
)

logger = logging.getLogger(__name__)


class CompetitorDiscoveryService:
    """Orchestrates competitor discovery."""

    def __init__(self, *, searcher: CompetitorSearcher):
        self._searcher = searcher

    async def discover_competitors(
        self,
        *,
        brand_name: str,
        brand_domain: str,
        country_name: str,
        num_competitors: int = 5,
    ) -> List[DiscoveredCompetitor]:
        """Discover competitors for a brand.

        Args:
            brand_name: The brand name to find competitors for
            brand_domain: The brand's website domain
            country_name: Country name for localized search
            num_competitors: Number of competitors to discover

        Returns:
            List of discovered competitors with empty variations
        """
        raw_competitors = await self._searcher.search(
            brand_name=brand_name,
            brand_domain=brand_domain,
            country_name=country_name,
            num_competitors=num_competitors,
        )

        if not raw_competitors:
            logger.info(f"No competitors found for '{brand_name}'")
            return []

        discovered = [
            DiscoveredCompetitor(
                brand_name=competitor.name,
                domain=competitor.domain,
                variations=[],
            )
            for competitor in raw_competitors
        ]

        logger.info(
            f"Discovered {len(discovered)} competitors for '{brand_name}'"
        )
        return discovered
