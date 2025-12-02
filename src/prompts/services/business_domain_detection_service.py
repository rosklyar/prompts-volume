"""Service for detecting business domain and brand variations."""

import json
import logging
import os
from typing import List, Optional

from fastapi import Depends
from openai import AsyncOpenAI

from src.database import BusinessDomain
from src.prompts.services.business_domain_service import BusinessDomainService, get_business_domain_service

logger = logging.getLogger(__name__)


class BusinessDomainDetectionService:
    """Detects business domain classification and brand variations using OpenAI."""

    def __init__(
        self,
        api_key: str,
        business_domain_service: BusinessDomainService,
        model: str = "gpt-4o-mini",
    ):
        if not api_key:
            raise ValueError("API key is required")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.business_domain_service = business_domain_service

    async def detect(
        self, domain: str, languages: List[str]
    ) -> tuple[Optional[BusinessDomain], List[str]]:
        """Detect business domain and brand variations for a company domain.

        Args:
            domain: Company domain
            languages: List of language names for brand variations (e.g., ["Ukrainian", "Russian"])
                      English is always added automatically.

        Returns:
            tuple of (business_domain, brand_variations)
            - business_domain: BusinessDomain ORM object if confident match found, None otherwise
            - brand_variations: List of brand name variations
        """
        # Ensure English is always included
        if "English" not in languages:
            languages = ["English"] + languages

        # Get available business domains from database
        available_domains = await self.business_domain_service.get_all()

        response = await self.client.responses.create(
            model=self.model,
            tools=[{"type": "web_search"}],
            input=self._create_prompt(domain, languages, available_domains),
        )

        content = response.output_text
        if not content:
            raise ValueError("Empty response from OpenAI")

        json_content = self._extract_json(content)
        parsed_data = json.loads(json_content)

        if "business_domain" not in parsed_data or "brand_variations" not in parsed_data:
            raise ValueError("Response missing required fields")

        domain_name = parsed_data["business_domain"]

        # Look up business domain object if not null
        business_domain_obj = None
        if domain_name is not None:
            # Find matching domain from available domains
            business_domain_obj = next(
                (d for d in available_domains if d.name == domain_name),
                None
            )
            if business_domain_obj is None:
                logger.warning(
                    f"LLM returned unknown business domain '{domain_name}', treating as not confident"
                )

        return business_domain_obj, parsed_data["brand_variations"]

    def _extract_json(self, content: str) -> str:
        """Extract JSON from response, handling markdown code blocks."""
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    def _create_prompt(
        self, domain: str, languages: List[str], available_domains: List[BusinessDomain]
    ) -> str:
        """Create prompt for business domain detection.

        Args:
            domain: Company domain to analyze
            languages: Languages for brand variations
            available_domains: List of BusinessDomain ORM objects from database
        """
        languages_str = ", ".join(languages)

        # Build dynamic list of business domains from database
        domains_section = "AVAILABLE BUSINESS DOMAINS:\n"
        for domain_obj in available_domains:
            domains_section += f"- {domain_obj.name}: {domain_obj.description}\n"

        return f"""Analyze {domain} and determine its business domain classification and brand variations.

{domains_section}
INSTRUCTIONS:
1. Analyze the website and determine which business domain it belongs to from the list above
2. Return the EXACT business domain name from the list (e.g., "e-comm")
3. Only return a domain if you are HIGHLY CONFIDENT (>80% confidence)
4. If uncertain or doesn't match any domain clearly, return null for business_domain
5. Generate brand_variations: List of different ways the brand name might be written in the following languages: {languages_str}

EXAMPLES for brand_variations:
Brand: "McDonald's", Languages: English, Spanish
Variations: ["McDonalds", "Mc Donald's", "MacDonalds", "Макдоналдс"]

Brand: "Nike", Languages: English, Russian, Chinese
Variations: ["NIKE", "Найк", "耐克", "Найки"]

Brand: "Apple", Languages: English, Chinese
Variations: ["APPLE", "苹果", "Эппл"]

Brand: "Google", Languages: English, Russian
Variations: ["GOOGLE", "Гугл", "Googl"]

Brand: "Microsoft", Languages: English, Japanese
Variations: ["MICROSOFT", "マイクロソフト", "Майкрософт"]

Brand: "Samsung", Languages: English, Korean
Variations: ["SAMSUNG", "삼성", "Самсунг"]

Return only clean variations without language labels or parentheses.
Make educated guesses based on the domain name and brand name patterns.

RESPONSE FORMAT:
Return ONLY valid JSON:
{{
  "business_domain": "e-comm",
  "brand_variations": ["brand1", "бренд1", "BRAND1"]
}}

OR if not confident:
{{
  "business_domain": null,
  "brand_variations": ["brand1", "бренд1", "BRAND1"]
}}

Use web search to gather accurate information."""


def get_business_domain_detection_service(
    business_domain_service: BusinessDomainService = Depends(get_business_domain_service),
) -> BusinessDomainDetectionService:
    """
    Dependency injection function for BusinessDomainDetectionService.

    Creates instance with wired BusinessDomainService delegate.

    Args:
        business_domain_service: BusinessDomainService injected by FastAPI

    Returns:
        BusinessDomainDetectionService instance with delegate wired
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    model = os.getenv("DOMAIN_DETECTION_MODEL", "gpt-4o-mini")

    return BusinessDomainDetectionService(
        api_key=api_key,
        business_domain_service=business_domain_service,
        model=model
    )
