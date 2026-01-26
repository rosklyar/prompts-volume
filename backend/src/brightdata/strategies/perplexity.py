"""Perplexity strategy for BrightData scraping."""

from typing import Any

from src.brightdata.strategies.base import AssistantConfig, AssistantStrategy, ParsedWebhookItem
from src.brightdata.strategies.citation_utils import (
    extract_index,
    merge_additional_sources,
    normalize_citations,
)


_CONFIG = AssistantConfig(
    assistant_id=2,
    assistant_name="Perplexity",
    assistant_key="perplexity",
    base_url="https://www.perplexity.ai",
    dataset_id="gd_m7dhdot1vw9a7gc1n",
)

_OUTPUT_FIELDS = [
    "url",
    "answer_text",
    "prompt",
    "is_shopping_data",
    "shopping_data",
    "citations",
    "web_search_query",
    "sources",
    "index",
]


class PerplexityStrategy(AssistantStrategy):
    """Strategy for Perplexity assistant scraping."""

    ASSISTANT_ID = _CONFIG.assistant_id
    ASSISTANT_NAME = _CONFIG.assistant_name
    URL = _CONFIG.base_url

    @property
    def config(self) -> AssistantConfig:
        """Return Perplexity configuration."""
        return _CONFIG

    def get_output_fields(self) -> list[str]:
        """Return Perplexity-specific output fields."""
        return _OUTPUT_FIELDS

    def build_input_item(
        self,
        prompt: str,
        country: str,
        index: int,
    ) -> dict[str, Any]:
        """Build Perplexity input item for BrightData API.

        Perplexity uses simpler format with export_markdown_file flag.
        """
        return {
            "url": self.config.base_url,
            "prompt": prompt,
            "country": country,
            "index": index,
            "export_markdown_file": False,
        }

    def parse_webhook_item(self, raw_item: dict[str, Any]) -> ParsedWebhookItem:
        """Parse Perplexity webhook response into normalized format."""
        citations = normalize_citations(raw_item.get("citations"))
        citations = merge_additional_sources(citations, raw_item.get("sources"))
        return ParsedWebhookItem(
            index=extract_index(raw_item),
            prompt_text=raw_item.get("prompt", ""),
            answer_text=raw_item.get("answer_text", ""),
            citations=citations,
            raw_data=raw_item,
        )
