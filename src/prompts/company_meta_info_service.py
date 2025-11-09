"""Service for retrieving company metadata (topics and brand variations)."""

import json
import logging
import os
from dataclasses import dataclass
from typing import List

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class CompanyMetaInfo:
    """Company metadata for prompts generation."""

    is_ecommerce: bool  # Whether company is strictly e-commerce
    top_topics: List[str]  # Top 10 topics/products company sells
    brand_variations: List[str]  # Brand name variations to filter


class CompanyMetaInfoService:
    """
    Service for company metadata using OpenAI with web search.

    Analyzes company websites to determine e-commerce status,
    product categories, and brand variations.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize the company meta info service with OpenAI client.

        Args:
            api_key: OpenAI API key
            model: OpenAI model to use (default: gpt-4o-mini)

        Raises:
            ValueError: If API key is empty
        """
        if not api_key:
            raise ValueError("API key is required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

        logger.info(f"CompanyMetaInfoService initialized with model: {self.model}")

    async def get_meta_info(self, domain: str) -> CompanyMetaInfo:
        """
        Get company metadata based on domain using OpenAI with web search.

        Args:
            domain: Company domain (e.g., "moyo.ua", "amazon.com")

        Returns:
            CompanyMetaInfo with e-commerce status, topics, and brand variations

        Raises:
            ValueError: If domain is empty or API response is invalid
        """
        if not domain:
            raise ValueError("Domain cannot be empty")

        logger.info(f"Fetching meta info for domain: {domain}")

        # Create prompt for LLM
        prompt = self._create_analysis_prompt(domain)

        try:
            # Use OpenAI with web search tool
            response = await self.client.responses.create(
                model=self.model,
                tools=[{"type": "web_search"}],
                input=prompt
            )

            # Extract content from response
            # Responses API returns output as: response.output[0].content[0].text
            content = response.output_text
            if not content:
                raise ValueError("Empty response from OpenAI")

            logger.info(f"Received raw response for {domain}: {content[:200]}...")

            # Extract JSON from response (may be wrapped in markdown code blocks)
            json_content = self._extract_json_from_response(content)
            logger.debug(f"Extracted JSON content: {json_content[:500]}...")

            # Parse JSON response
            parsed_data = json.loads(json_content)

            # Validate required fields
            if "is_ecommerce" not in parsed_data:
                raise ValueError("Response missing 'is_ecommerce' field")
            if "top_topics" not in parsed_data:
                raise ValueError("Response missing 'top_topics' field")
            if "brand_variations" not in parsed_data:
                raise ValueError("Response missing 'brand_variations' field")

            # Create and return CompanyMetaInfo
            return CompanyMetaInfo(
                is_ecommerce=parsed_data["is_ecommerce"],
                top_topics=parsed_data["top_topics"],
                brand_variations=parsed_data["brand_variations"]
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response for {domain}")
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw content: {content}")
            logger.error(f"Extracted JSON: {json_content}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")
        except Exception as e:
            logger.error(f"Error fetching meta info for {domain}: {e}")
            raise

    def _extract_json_from_response(self, content: str) -> str:
        """
        Extract JSON from LLM response, handling markdown code blocks.

        Args:
            content: Raw response from LLM

        Returns:
            Clean JSON string

        Examples:
            - "```json\n{...}\n```" -> "{...}"
            - "```\n{...}\n```" -> "{...}"
            - "{...}" -> "{...}"
        """
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        elif content.startswith("```"):
            content = content[3:]  # Remove ```

        if content.endswith("```"):
            content = content[:-3]  # Remove closing ```

        return content.strip()

    def _create_analysis_prompt(self, domain: str) -> str:
        """
        Create analysis prompt for OpenAI to analyze company website.

        Args:
            domain: Company domain to analyze

        Returns:
            Formatted prompt string
        """
        return f"""Analyze the company website at {domain} and provide the following information:

TASK:
1. Determine if this is STRICTLY an e-commerce company (selling products online)
2. Identify the top 10 product categories or topics the company sells
3. Extract brand name variations (including local language versions)

E-COMMERCE DEFINITION:
- Must sell products directly to consumers online
- Examples: zalando, amazon, ceneo, allegro, rozetka, eBay, Etsy
- NOT e-commerce: SaaS companies, service providers, B2B platforms, news sites

INSTRUCTIONS:
1. **is_ecommerce**: Set to true ONLY if you are STRICTLY confident this is an e-commerce company
   - If uncertain or mixed business model, set to false
   - Examples of TRUE: zalando.com, amazon.com, rozetka.com.ua, allegro.pl
   - Examples of FALSE: shopify.com (SaaS), stripe.com (payment processor), booking.com (services)

2. **top_topics**: List exactly 10 product categories or topics
   - Use the language appropriate to the company's main market
   - Be specific (e.g., "Смартфони і телефони" not just "Electronics")
   - Order by importance/popularity if possible

3. **brand_variations**: List brand name variations
   - Include English version
   - Include local language versions (Cyrillic, etc.)
   - Include common abbreviations or nicknames
   - Examples: ["moyo", "мойо"], ["rozetka", "розетка"], ["amazon"]

RESPONSE FORMAT - CRITICAL:
Your response must be ONLY a valid JSON object. Do NOT include:
- Markdown formatting or code blocks (no ``` or ```json)
- Explanatory text before or after the JSON
- Comments or additional information

Return EXACTLY this structure with no extra text:
{{
  "is_ecommerce": true,
  "top_topics": [
    "Topic 1",
    "Topic 2",
    "Topic 3",
    "Topic 4",
    "Topic 5",
    "Topic 6",
    "Topic 7",
    "Topic 8",
    "Topic 9",
    "Topic 10"
  ],
  "brand_variations": [
    "variation1",
    "variation2"
  ]
}}

EXAMPLE VALID RESPONSE:
{{"is_ecommerce": true, "top_topics": ["Смартфони", "Ноутбуки", "Телевізори", "Аудіотехніка", "Техніка для дому", "Техніка для кухні", "Планшети", "Комп'ютери", "Фото і відео", "Ігрові консолі"], "brand_variations": ["moyo", "мойо"]}}

Use web search to gather accurate, up-to-date information about the company.
Be thorough and accurate in your analysis.
Remember: Return ONLY the JSON object, nothing else."""


# Global instance for dependency injection
_company_meta_info_service = None


def get_company_meta_info_service() -> CompanyMetaInfoService:
    """
    Get the global CompanyMetaInfoService instance.
    Creates one if it doesn't exist yet.

    Returns:
        CompanyMetaInfoService instance

    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
    """
    global _company_meta_info_service
    if _company_meta_info_service is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        model = os.getenv("CMI_OPENAI_MODEL", "gpt-4o-mini")
        _company_meta_info_service = CompanyMetaInfoService(api_key=api_key, model=model)
    return _company_meta_info_service
