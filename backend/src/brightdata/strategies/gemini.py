"""Gemini strategy for BrightData scraping."""

from typing import Any

from src.brightdata.strategies.base import AssistantConfig, AssistantStrategy, ParsedWebhookItem


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
        # Extract index
        index: int | None = None
        if "index" in raw_item:
            index = int(raw_item["index"])
        elif "input" in raw_item and isinstance(raw_item["input"], dict):
            index = raw_item["input"].get("index")
            if index is not None:
                index = int(index)

        # Extract citations and normalize
        raw_citations = raw_item.get("citations") or []
        citations = [
            {
                "url": c.get("url", ""),
                "text": c.get("title", c.get("text", "")),
                "domain": c.get("domain", ""),
            }
            for c in raw_citations
        ]

        # Also check 'links_attached' which may contain additional citation-like data
        raw_links = raw_item.get("links_attached") or []
        for link in raw_links:
            if isinstance(link, dict) and link.get("url"):
                # Avoid duplicates
                if not any(c["url"] == link.get("url") for c in citations):
                    citations.append({
                        "url": link.get("url", ""),
                        "text": link.get("title", link.get("text", "")),
                        "domain": link.get("domain", ""),
                    })

        return ParsedWebhookItem(
            index=index,
            prompt_text=raw_item.get("prompt", ""),
            answer_text=raw_item.get("answer_text", ""),
            citations=citations,
            raw_data=raw_item,
        )
