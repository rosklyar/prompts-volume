"""Gemini strategy for BrightData scraping."""

from typing import Any

from src.brightdata.strategies.base import AssistantConfig, AssistantStrategy, ParsedWebhookItem
from src.brightdata.strategies.citation_utils import (
    extract_index,
    merge_additional_sources,
    normalize_citations,
)
from src.config.settings import settings


_CONFIG = AssistantConfig(
    assistant_id=3,
    assistant_name="Gemini",
    assistant_key="gemini",
    base_url="https://gemini.google.com/",
    dataset_id="gd_mbz66arm2mf9cu856y",
)

_OUTPUT_FIELDS = [
    "url",
    "prompt",
    "answer_text",
    "links_attached",
    "citations",
    "index",
    "timestamp",
    "error",
    "input",
]


class GeminiStrategy(AssistantStrategy):
    """Strategy for Gemini assistant scraping."""

    ASSISTANT_ID = _CONFIG.assistant_id
    ASSISTANT_NAME = _CONFIG.assistant_name
    URL = _CONFIG.base_url

    @property
    def config(self) -> AssistantConfig:
        """Return Gemini configuration."""
        return _CONFIG

    def get_chunk_size(self) -> int:
        """Return Gemini-specific chunk size."""
        return settings.brightdata_gemini_chunk_size

    def get_output_fields(self) -> list[str]:
        """Return Gemini-specific output fields."""
        return _OUTPUT_FIELDS

    def build_input_item(
        self,
        prompt: str,
        country: str,
        index: int,
    ) -> dict[str, Any]:
        """Build Gemini input item for BrightData API.

        Gemini uses simple format with url, prompt, country, and index.
        """
        return {
            "url": self.config.base_url,
            "prompt": prompt,
            "country": country,
            "index": index,
        }

    def parse_webhook_item(self, raw_item: dict[str, Any]) -> ParsedWebhookItem:
        """Parse Gemini webhook response into normalized format."""
        citations = normalize_citations(raw_item.get("citations"))
        citations = merge_additional_sources(citations, raw_item.get("links_attached"))
        return ParsedWebhookItem(
            index=extract_index(raw_item),
            prompt_text=raw_item.get("prompt", ""),
            answer_text=raw_item.get("answer_text", ""),
            citations=citations,
            raw_data=raw_item,
        )
