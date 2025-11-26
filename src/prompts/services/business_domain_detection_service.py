"""Service for detecting business domain and brand variations."""

import json
import logging
from typing import List

from openai import AsyncOpenAI

from src.prompts.models import BusinessDomain

logger = logging.getLogger(__name__)


class BusinessDomainDetectionService:
    """Detects business domain classification and brand variations using OpenAI."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("API key is required")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def detect(self, domain: str, languages: List[str]) -> tuple[BusinessDomain, List[str]]:
        """Detect business domain and brand variations for a company domain.

        Args:
            domain: Company domain
            languages: List of language names for brand variations (e.g., ["Ukrainian", "Russian"])
                      English is always added automatically.
        """
        # Ensure English is always included
        if "English" not in languages:
            languages = ["English"] + languages

        response = await self.client.responses.create(
            model=self.model,
            tools=[{"type": "web_search"}],
            input=self._create_prompt(domain, languages)
        )

        content = response.output_text
        if not content:
            raise ValueError("Empty response from OpenAI")

        json_content = self._extract_json(content)
        parsed_data = json.loads(json_content)

        if "business_domain" not in parsed_data or "brand_variations" not in parsed_data:
            raise ValueError("Response missing required fields")

        try:
            business_domain = BusinessDomain(parsed_data["business_domain"])
        except ValueError:
            logger.warning(f"Unknown business domain, returning NOT_SUPPORTED")
            business_domain = BusinessDomain.NOT_SUPPORTED

        return business_domain, parsed_data["brand_variations"]

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

    def _create_prompt(self, domain: str, languages: List[str]) -> str:
        """Create prompt for business domain detection."""
        languages_str = ", ".join(languages)
        return f"""Analyze {domain} and determine its business domain classification and brand variations.

AVAILABLE BUSINESS DOMAINS:
- E_COMMERCE: Companies that sell products directly to consumers online
- NOT_SUPPORTED: All other business types (SaaS, services, B2B, news, etc.)

E_COMMERCE CRITERIA:
- Must sell physical or digital products directly to consumers online
- Has shopping cart, product catalog, and checkout functionality
- Examples: zalando.com, amazon.com, rozetka.com.ua, allegro.pl, moyo.ua

NOT E_COMMERCE (NOT_SUPPORTED):
- SaaS companies (shopify.com, stripe.com)
- Service providers (booking.com, uber.com)
- B2B platforms without direct consumer sales
- News sites, blogs, educational platforms

INSTRUCTIONS:
1. Classify with HIGH CONFIDENCE. If uncertain, return NOT_SUPPORTED
2. Generate brand_variations: List of different ways the brand name might be written in the following languages: {languages_str}

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
  "business_domain": "E_COMMERCE",
  "brand_variations": ["brand1", "бренд1", "BRAND1"]
}}

Use web search to gather accurate information."""
