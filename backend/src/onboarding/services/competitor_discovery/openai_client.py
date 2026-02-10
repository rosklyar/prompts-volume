"""OpenAI implementations for competitor discovery."""

import json
import logging
from typing import List

from openai import AsyncOpenAI

from src.onboarding.services.competitor_discovery.models import RawCompetitor
from src.onboarding.services.competitor_discovery.prompts import (
    COMPETITOR_SEARCH_PROMPT,
)

logger = logging.getLogger(__name__)


class OpenAICompetitorSearcher:
    """OpenAI-based competitor searcher using web search."""

    def __init__(self, *, api_key: str, model: str):
        if not api_key:
            raise ValueError("API key is required")
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def search(
        self,
        *,
        brand_name: str,
        brand_domain: str,
        country_name: str,
        num_competitors: int = 5,
    ) -> List[RawCompetitor]:
        """Search for competitors using OpenAI with web search."""
        prompt = COMPETITOR_SEARCH_PROMPT.format(
            brand_name=brand_name,
            target_domain=brand_domain,
            country=country_name,
            num_competitors=num_competitors,
            brand_name_lower=brand_name.lower(),
        )

        try:
            response = await self._client.responses.create(
                model=self._model,
                tools=[{"type": "web_search"}],
                input=prompt,
            )

            content = response.output_text
            if not content:
                logger.warning("Empty response from OpenAI competitor search")
                return []

            json_content = self._extract_json(content)
            competitors_data = json.loads(json_content)

            if not isinstance(competitors_data, list):
                logger.warning(f"Expected list, got {type(competitors_data)}")
                return []

            return [
                RawCompetitor(
                    name=item.get("name", ""),
                    domain=item.get("domain"),
                )
                for item in competitors_data
                if isinstance(item, dict) and item.get("name")
            ]

        except Exception as e:
            logger.error(f"Competitor search failed: {e}")
            return []

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
