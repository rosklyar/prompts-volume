"""Base strategy interface for AI assistant BrightData integration."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from src.config.settings import settings


@dataclass(frozen=True)
class AssistantConfig:
    """Immutable configuration for an AI assistant."""

    assistant_id: int
    assistant_name: str
    assistant_key: str  # URL-safe key for webhook routing (e.g., "chatgpt", "perplexity")
    base_url: str  # URL to scrape (e.g., "https://chatgpt.com/")
    dataset_id: str  # BrightData dataset ID


@dataclass
class ParsedWebhookItem:
    """Normalized webhook response item.

    Standard format regardless of which assistant the response came from.
    """

    index: int | None  # 1-based index for matching (None if not available)
    prompt_text: str  # Original prompt text (fallback matching)
    answer_text: str
    citations: list[dict[str, Any]]  # Normalized: [{"url": str, "text": str, "domain": str}]
    raw_data: dict[str, Any]  # Original webhook data for debugging


class IndexBasedPromptMatcher:
    """Matcher that uses index field for prompt correlation.

    BrightData webhook responses include the index we sent in the request.
    This matcher uses that index to find the corresponding prompt_id.
    """

    def __init__(self, index_to_prompt_id: dict[str, int]):
        """Initialize matcher with index mapping.

        Args:
            index_to_prompt_id: Map of "1" -> prompt_id_1, "2" -> prompt_id_2, etc.
                               Keys are strings for JSON compatibility.
        """
        self._index_to_prompt_id = index_to_prompt_id

    def match(self, item: ParsedWebhookItem) -> int | None:
        """Match webhook item to prompt_id using index.

        Args:
            item: Parsed webhook item with index field

        Returns:
            prompt_id if matched, None otherwise
        """
        if item.index is None:
            return None
        return self._index_to_prompt_id.get(str(item.index))


class AssistantStrategy(ABC):
    """Strategy interface for AI assistant BrightData integration.

    Each AI assistant (ChatGPT, Perplexity, etc.) has different:
    - Scraping URL and dataset ID
    - Input payload format
    - Output fields to request
    - Webhook response parsing
    """

    @property
    @abstractmethod
    def config(self) -> AssistantConfig:
        """Return configuration for this assistant."""
        ...

    def get_url(self) -> str:
        """Return the scraping URL for this assistant."""
        return self.config.base_url

    def get_assistant_id(self) -> int:
        """Return the database assistant ID."""
        return self.config.assistant_id

    def get_assistant_name(self) -> str:
        """Return the assistant name for logging/display."""
        return self.config.assistant_name

    def get_assistant_key(self) -> str:
        """Return URL-safe key for webhook routing."""
        return self.config.assistant_key

    def get_dataset_id(self) -> str:
        """Return BrightData dataset ID for this assistant."""
        return self.config.dataset_id

    def get_chunk_size(self) -> int:
        """Return chunk size for this assistant. Defaults to global setting."""
        return settings.brightdata_chunk_size

    @abstractmethod
    def get_output_fields(self) -> list[str]:
        """Return custom output fields to request from BrightData API."""
        ...

    @abstractmethod
    def build_input_item(
        self,
        prompt: str,
        country: str,
        index: int,
    ) -> dict[str, Any]:
        """Build a single input item for BrightData API.

        Args:
            prompt: The prompt text
            country: ISO country code (e.g., "US", "UA")
            index: 1-based index for webhook correlation

        Returns:
            Dict with assistant-specific input format
        """
        ...

    @abstractmethod
    def parse_webhook_item(self, raw_item: dict[str, Any]) -> ParsedWebhookItem:
        """Parse raw webhook item into normalized format.

        Args:
            raw_item: Raw dict from BrightData webhook

        Returns:
            ParsedWebhookItem with normalized fields
        """
        ...
