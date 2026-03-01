import json
import logging
from typing import List

from openai import AsyncOpenAI

from src.config.settings import settings
from src.keyword_inspiration.domain_prompts import get_prompt_builder

logger = logging.getLogger(__name__)


class PromptsGeneratorService:
    """Service for generating search prompts based on keywords."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize the prompts generator service with OpenAI client."""
        if not api_key:
            raise ValueError("API key is required")

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

        logger.info(f"PromptsGeneratorService initialized with model: {self.model}")

    async def _call_openai_json(
        self,
        system_prompt: str,
        user_prompt: str,
        error_context: str,
    ) -> dict:
        """Make OpenAI API call with JSON response format."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response for {error_context}: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")

    async def generate_prompts_from_keywords(
        self,
        keywords: List[str],
        business_domain: str,
        language: str,
    ) -> List[tuple[str, str]]:
        """
        Generate exactly 1 LLM prompt per keyword (max 20 keywords).

        Args:
            keywords: List of keywords to generate prompts from
            business_domain: Business domain (e-comm, fintech, saas, etc.)
            language: Language for generated prompts (e.g., "Ukrainian", "English")

        Returns:
            List of (prompt, source_keyword) tuples

        Raises:
            ValueError: If keywords list is empty
        """
        if not keywords:
            raise ValueError("Keywords list cannot be empty")

        keywords = keywords[:20]

        builder = get_prompt_builder(business_domain)
        system_prompt = builder.build_system_prompt(keywords, language)

        user_prompt = (
            f"Generate exactly 1 prompt per keyword. "
            f"Keywords: {', '.join(keywords)}"
        )

        parsed_data = await self._call_openai_json(
            system_prompt, user_prompt, "GSC keywords"
        )
        prompts_data = parsed_data.get("prompts", [])

        if not prompts_data:
            raise ValueError("Response missing 'prompts' field or prompts list is empty")

        return [(item["prompt"], item["source_keyword"]) for item in prompts_data]


# Global instance for dependency injection
_prompts_generator_service = None


def get_prompts_generator_service() -> PromptsGeneratorService:
    """
    Get the global PromptsGeneratorService instance.
    Creates one if it doesn't exist yet.

    Returns:
        PromptsGeneratorService instance

    Raises:
        ValueError: If OPENAI_API_KEY environment variable is not set
    """
    global _prompts_generator_service
    if _prompts_generator_service is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        _prompts_generator_service = PromptsGeneratorService(
            api_key=settings.openai_api_key,
            model=settings.pg_openai_model
        )
    return _prompts_generator_service
