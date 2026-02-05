"""OpenAI implementations for competitor discovery."""

import json
import logging
from typing import Dict, List

from openai import AsyncOpenAI

from src.onboarding.services.competitor_discovery.models import RawCompetitor
from src.onboarding.services.competitor_discovery.prompts import (
    BATCH_VARIATION_GENERATION_PROMPT,
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


class OpenAIBrandVariationGenerator:
    """OpenAI-based brand variation generator with batch support."""

    def __init__(self, *, api_key: str, model: str):
        if not api_key:
            raise ValueError("API key is required")
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate_batch(
        self,
        *,
        brand_names: List[str],
        languages: List[str],
    ) -> Dict[str, List[str]]:
        """Generate brand name variations for multiple brands in a single call."""
        if not brand_names:
            return {}

        languages_str = ", ".join(languages)
        brands_list = "\n".join(f"- {name}" for name in brand_names)

        prompt = BATCH_VARIATION_GENERATION_PROMPT.format(
            brands_list=brands_list,
            languages=languages_str,
        )

        try:
            response = await self._client.responses.create(
                model=self._model,
                input=prompt,
            )

            content = response.output_text
            if not content:
                logger.warning("Empty response for batch variation generation")
                return {name: [] for name in brand_names}

            json_content = self._extract_json(content)
            variations_map = json.loads(json_content)

            if not isinstance(variations_map, dict):
                logger.warning(f"Expected dict, got {type(variations_map)}")
                return {name: [] for name in brand_names}

            # Normalize variations for each brand
            result: Dict[str, List[str]] = {}
            for brand_name in brand_names:
                raw_variations = variations_map.get(brand_name, [])
                if not isinstance(raw_variations, list):
                    raw_variations = []
                filtered = [v for v in raw_variations if isinstance(v, str) and v.strip()]
                result[brand_name] = self._normalize_variations(filtered, brand_name)

            return result

        except Exception as e:
            logger.error(f"Batch variation generation failed: {e}")
            return {name: [] for name in brand_names}

    def _normalize_variations(
        self, variations: List[str], brand_name: str, *, max_count: int = 3
    ) -> List[str]:
        """Normalize variations: lowercase, dedupe, remove redundant suffixes."""
        brand_lower = brand_name.lower()
        seen_lower: set[str] = set()
        result: List[str] = []

        for v in variations:
            normalized = v.lower().strip()

            # Skip empty or original brand name
            if not normalized or normalized == brand_lower:
                continue

            # Skip if we've seen this (case-insensitive dedup)
            if normalized in seen_lower:
                continue

            # Skip if this is just another variation + suffix
            is_redundant = False
            for existing in result:
                if normalized.startswith(existing) and len(normalized) > len(existing):
                    is_redundant = True
                    break
                if existing.startswith(normalized) and len(existing) > len(normalized):
                    result.remove(existing)
                    seen_lower.discard(existing)
                    break

            if is_redundant:
                continue

            seen_lower.add(normalized)
            result.append(normalized)

            if len(result) >= max_count:
                break

        return result

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
