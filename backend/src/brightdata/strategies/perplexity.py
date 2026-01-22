"""Perplexity strategy for BrightData scraping."""

from typing import Any

from src.brightdata.strategies.base import AssistantConfig, AssistantStrategy, ParsedWebhookItem


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
        # Extract index
        index: int | None = None
        if "index" in raw_item:
            index = int(raw_item["index"])

        # Perplexity uses 'citations' list with url/title/domain structure
        raw_citations = raw_item.get("citations") or []
        citations = [
            {
                "url": c.get("url", ""),
                "text": c.get("title", c.get("text", "")),
                "domain": c.get("domain", ""),
            }
            for c in raw_citations
        ]

        # Also check 'sources' which may contain additional citation-like data
        raw_sources = raw_item.get("sources") or []
        for s in raw_sources:
            if isinstance(s, dict) and s.get("url"):
                # Avoid duplicates
                if not any(c["url"] == s.get("url") for c in citations):
                    citations.append({
                        "url": s.get("url", ""),
                        "text": s.get("title", s.get("name", "")),
                        "domain": s.get("domain", ""),
                    })

        return ParsedWebhookItem(
            index=index,
            prompt_text=raw_item.get("prompt", ""),
            answer_text=raw_item.get("answer_text", ""),
            citations=citations,
            raw_data=raw_item,
        )
