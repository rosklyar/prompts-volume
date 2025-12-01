"""Service for generating topics based on business domain."""

import json
import logging
import os
from typing import List

from openai import AsyncOpenAI

from src.database import BusinessDomain

logger = logging.getLogger(__name__)


class TopicsGenerationService:
    """Generates domain-specific topics using OpenAI."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        if not api_key:
            raise ValueError("API key is required")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_topics(
        self,
        domain: str,
        business_domain: BusinessDomain,
        primary_language: str = "English"
    ) -> List[str]:
        """Generate topics for a company domain based on business domain.

        Args:
            domain: Company domain
            business_domain: Business domain type
            primary_language: Primary language for topics (default: "English")
        """
        # Route to appropriate prompt based on business domain name
        if business_domain.name == "e-comm":
            prompt = self._create_ecommerce_prompt(domain, primary_language)
        else:
            raise ValueError(f"Unsupported business domain: {business_domain.name}")

        response = await self.client.responses.create(
            model=self.model,
            tools=[{"type": "web_search"}],
            input=prompt
        )

        content = response.output_text
        if not content:
            raise ValueError("Empty response from OpenAI")

        json_content = self._extract_json(content)
        parsed_data = json.loads(json_content)

        if "top_topics" not in parsed_data:
            raise ValueError("Response missing 'top_topics' field")

        return parsed_data["top_topics"]

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

    def _create_ecommerce_prompt(self, domain: str, primary_language: str) -> str:
        """Create prompt for e-commerce topics generation."""
        return f"""Analyze the e-commerce website at {domain} and extract sales categories.

TASK:
Identify the top 10 product sales categories (what they sell)

INSTRUCTIONS:
- Generate all topics in {primary_language} language
- Be specific (e.g., "Смартфони і телефони" not just "Electronics")
- Order by importance/popularity
- Focus on SALES CATEGORIES (what customers buy)

RESPONSE FORMAT:
Return ONLY valid JSON:
{{
  "top_topics": [
    "Category 1",
    "Category 2",
    "Category 3",
    "Category 4",
    "Category 5",
    "Category 6",
    "Category 7",
    "Category 8",
    "Category 9",
    "Category 10"
  ]
}}

Use web search to gather accurate information."""


def get_topics_generation_service() -> TopicsGenerationService:
    """
    Dependency injection function for TopicsGenerationService.

    Creates instance with API key and model from environment variables.

    Returns:
        TopicsGenerationService instance
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    model = os.getenv("TOPICS_GENERATION_MODEL", "gpt-4o-mini")

    return TopicsGenerationService(api_key=api_key, model=model)
