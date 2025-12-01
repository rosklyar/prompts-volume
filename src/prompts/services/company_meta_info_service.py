"""Service for retrieving company metadata (orchestrator)."""

import logging
import os

from fastapi import Depends

from src.database import Country
from src.prompts.models import CompanyMetaInfo
from src.prompts.services.business_domain_detection_service import (
    BusinessDomainDetectionService,
    get_business_domain_detection_service,
)
from src.prompts.services.topics_generation_service import (
    TopicsGenerationService,
    get_topics_generation_service,
)

logger = logging.getLogger(__name__)


class CompanyMetaInfoService:
    """Orchestrates company metadata retrieval using specialized services."""

    def __init__(
        self,
        domain_detection_service: BusinessDomainDetectionService,
        topics_generation_service: TopicsGenerationService,
    ):
        # Wire high-level service delegates in __init__ (not created in business methods)
        self.domain_detection_service = domain_detection_service
        self.topics_generation_service = topics_generation_service

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

        # Generate topics if supported (business_domain is not None)
        if business_domain is None:
            return CompanyMetaInfo(
                business_domain=None,
                top_topics=[],
                brand_variations=brand_variations
            )

        # Get primary language (first in list, fallback to English)
        primary_language = languages[0] if languages else "English"

        topics = await self.topics_generation_service.generate_topics(
            domain, business_domain, primary_language
        )

        return CompanyMetaInfo(
            business_domain=business_domain,
            top_topics=topics,
            brand_variations=brand_variations
        )


def get_company_meta_info_service(
    domain_detection_service: BusinessDomainDetectionService = Depends(get_business_domain_detection_service),
    topics_generation_service: TopicsGenerationService = Depends(get_topics_generation_service),
) -> CompanyMetaInfoService:
    """
    Dependency injection function for CompanyMetaInfoService.

    Creates a new CompanyMetaInfoService instance per request with injected high-level service delegates.
    Note: This service is request-scoped (not a global singleton) because it depends
    on session-scoped services (via BusinessDomainDetectionService).

    Args:
        domain_detection_service: BusinessDomainDetectionService with wired BusinessDomainService
        topics_generation_service: TopicsGenerationService for generating topic suggestions

    Returns:
        CompanyMetaInfoService instance for this request with high-level delegates wired
    """
    return CompanyMetaInfoService(
        domain_detection_service=domain_detection_service,
        topics_generation_service=topics_generation_service,
    )
