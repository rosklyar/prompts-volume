"""Dependency injection for competitor discovery service."""

from typing import Annotated

from fastapi import Depends

from src.config.settings import settings
from src.onboarding.services.competitor_discovery.openai_client import (
    OpenAIBrandVariationGenerator,
    OpenAICompetitorSearcher,
)
from src.onboarding.services.competitor_discovery.service import (
    CompetitorDiscoveryService,
)


def get_competitor_discovery_service() -> CompetitorDiscoveryService:
    """Dependency injection for CompetitorDiscoveryService."""
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    searcher = OpenAICompetitorSearcher(
        api_key=settings.openai_api_key,
        model=settings.pg_openai_model,
    )
    variation_generator = OpenAIBrandVariationGenerator(
        api_key=settings.openai_api_key,
        model=settings.pg_openai_model,
    )

    return CompetitorDiscoveryService(
        searcher=searcher,
        variation_generator=variation_generator,
    )


CompetitorDiscoveryServiceDep = Annotated[
    CompetitorDiscoveryService, Depends(get_competitor_discovery_service)
]
