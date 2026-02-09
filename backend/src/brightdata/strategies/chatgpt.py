"""ChatGPT strategy for BrightData scraping."""

from typing import Any

from src.brightdata.strategies.base import AssistantConfig, AssistantStrategy, ParsedWebhookItem
from src.brightdata.strategies.citation_utils import extract_index, normalize_citations
from src.config.settings import settings


_CONFIG = AssistantConfig(
    assistant_id=1,
    assistant_name="ChatGPT",
    assistant_key="chatgpt",
    base_url="https://chatgpt.com/",
    dataset_id="gd_m7aof0k82r803d5bjm",
)

_OUTPUT_FIELDS = [
    "prompt",
    "answer_text",
    "links_attached",
    "citations",
    "shopping",
    "search_sources",
    "web_search_query",
    "input",
    "timestamp",
    "model",
    "recommendations",
    "index",  # Added for index-based matching
]


class ChatGPTStrategy(AssistantStrategy):
    """Strategy for ChatGPT assistant scraping."""

    # Legacy class-level attributes for backward compatibility
    ASSISTANT_ID = _CONFIG.assistant_id
    ASSISTANT_NAME = _CONFIG.assistant_name
    URL = _CONFIG.base_url

    @property
    def config(self) -> AssistantConfig:
        """Return ChatGPT configuration."""
        return _CONFIG

    def get_chunk_size(self) -> int:
        """Return ChatGPT-specific chunk size."""
        return settings.brightdata_chatgpt_chunk_size

    def get_output_fields(self) -> list[str]:
        """Return ChatGPT-specific output fields."""
        return _OUTPUT_FIELDS

    def build_input_item(
        self,
        prompt: str,
        country: str,
        index: int,
    ) -> dict[str, Any]:
        """Build ChatGPT input item for BrightData API.

        ChatGPT uses web_search and require_sources fields.
        """
        return {
            "url": self.config.base_url,
            "prompt": prompt,
            "country": country,
            "web_search": True,
            "require_sources": False,
            "additional_prompt": "",
            "index": index,
        }

    def parse_webhook_item(self, raw_item: dict[str, Any]) -> ParsedWebhookItem:
        """Parse ChatGPT webhook response into normalized format."""
        return ParsedWebhookItem(
            index=extract_index(raw_item),
            prompt_text=raw_item.get("prompt", ""),
            answer_text=raw_item.get("answer_text", ""),
            citations=normalize_citations(raw_item.get("citations")),
            raw_data=raw_item,
        )
