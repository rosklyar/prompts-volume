"""Service for retrieving company metadata (orchestrator)."""

import logging
import os
from typing import List

from src.config.countries import get_country_by_code
from src.prompts.models import BusinessDomain, CompanyMetaInfo
from src.prompts.services.business_domain_detection_service import BusinessDomainDetectionService
from src.prompts.services.topics_generation_service import TopicsGenerationService

logger = logging.getLogger(__name__)


class CompanyMetaInfoService:
    """Orchestrates company metadata retrieval using specialized services."""

    def __init__(
        self,
        domain_detection_service: BusinessDomainDetectionService,
        topics_generation_service: TopicsGenerationService
    ):
        self.domain_detection_service = domain_detection_service
        self.topics_generation_service = topics_generation_service

    async def get_meta_info(self, domain: str, iso_country_code: str) -> CompanyMetaInfo:
        """Get company metadata based on domain and country.

        Args:
            domain: Company domain
            iso_country_code: ISO country code to determine languages
        """
        if not domain:
            raise ValueError("Domain cannot be empty")

        # Get languages from country code
        languages = self._get_languages(iso_country_code)

        # Detect business domain and brand variations
        business_domain, brand_variations = await self.domain_detection_service.detect(domain, languages)
        logger.info(f"Detected {business_domain} for {domain}")

        # Generate topics if supported
        if business_domain == BusinessDomain.NOT_SUPPORTED:
            return CompanyMetaInfo(
                business_domain=business_domain,
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

    def _get_languages(self, iso_country_code: str) -> List[str]:
        """Get language names for a country."""
        country = get_country_by_code(iso_country_code)
        if not country:
            return []

        return [lang.name for lang in country.preferred_languages]


# Global instance for dependency injection
_company_meta_info_service = None


def get_company_meta_info_service() -> CompanyMetaInfoService:
    """Get the global CompanyMetaInfoService instance."""
    global _company_meta_info_service
    if _company_meta_info_service is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        domain_model = os.getenv("DOMAIN_DETECTION_MODEL", "gpt-4o-mini")
        topics_model = os.getenv("TOPICS_GENERATION_MODEL", "gpt-4o-mini")

        domain_detection_service = BusinessDomainDetectionService(api_key=api_key, model=domain_model)
        topics_generation_service = TopicsGenerationService(api_key=api_key, model=topics_model)

        _company_meta_info_service = CompanyMetaInfoService(
            domain_detection_service=domain_detection_service,
            topics_generation_service=topics_generation_service
        )
    return _company_meta_info_service
