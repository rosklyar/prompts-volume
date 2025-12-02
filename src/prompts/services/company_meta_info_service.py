"""Service for retrieving company metadata (orchestrator)."""

import logging

from fastapi import Depends

from src.database import Country
from src.prompts.models import CompanyMetaInfo, TopicMatchResult
from src.prompts.services.business_domain_detection_service import (
    BusinessDomainDetectionService,
    get_business_domain_detection_service,
)
from src.prompts.services.topics_provider import (
    TopicsProvider,
    get_topics_provider,
)

logger = logging.getLogger(__name__)


class CompanyMetaInfoService:
    """Orchestrates company metadata retrieval using specialized services."""

    def __init__(
        self,
        domain_detection_service: BusinessDomainDetectionService,
        topics_provider: TopicsProvider,
    ):
        # Wire high-level service delegates in __init__ (not created in business methods)
        self.domain_detection_service = domain_detection_service
        self.topics_provider = topics_provider

    async def get_meta_info(self, domain: str, country: Country) -> CompanyMetaInfo:
        """Get company metadata based on domain and country.

        Args:
            domain: Company domain
            country: Country object with eager-loaded languages
        """
        if not domain:
            raise ValueError("Domain cannot be empty")

        # Extract languages from country object (already fetched by router)
        languages = [lang.name for lang in country.languages]

        # Detect business domain and brand variations using wired delegate
        business_domain, brand_variations = await self.domain_detection_service.detect(domain, languages)
        logger.info(f"Detected {business_domain} for {domain}")

        # Provide topics if supported (business_domain is not None)
        if business_domain is None:
            return CompanyMetaInfo(
                business_domain=None,
                topics=TopicMatchResult(matched_topics=[], unmatched_topics=[]),
                brand_variations=brand_variations
            )

        # Use TopicsProvider to get matched and unmatched topics
        match_result = await self.topics_provider.provide(
            domain, business_domain, country
        )

        # Store TopicMatchResult directly (preserve matched vs unmatched distinction)
        return CompanyMetaInfo(
            business_domain=business_domain,
            topics=match_result,
            brand_variations=brand_variations
        )


def get_company_meta_info_service(
    domain_detection_service: BusinessDomainDetectionService = Depends(get_business_domain_detection_service),
    topics_provider: TopicsProvider = Depends(get_topics_provider),
) -> CompanyMetaInfoService:
    """
    Dependency injection function for CompanyMetaInfoService.

    Creates a new CompanyMetaInfoService instance per request with injected high-level service delegates.
    Note: This service is request-scoped (not a global singleton) because it depends
    on session-scoped services (via BusinessDomainDetectionService and TopicsProvider).

    Args:
        domain_detection_service: BusinessDomainDetectionService with wired BusinessDomainService
        topics_provider: TopicsProvider for providing topics with DB matching

    Returns:
        CompanyMetaInfoService instance for this request with high-level delegates wired
    """
    return CompanyMetaInfoService(
        domain_detection_service=domain_detection_service,
        topics_provider=topics_provider,
    )
