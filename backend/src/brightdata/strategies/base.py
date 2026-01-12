"""Base strategy interface for AI assistant URL building."""

from abc import ABC, abstractmethod


class AssistantUrlStrategy(ABC):
    """Strategy interface for building assistant-specific URLs.

    Each AI assistant (ChatGPT, Claude, Perplexity, etc.) may have
    a different URL for scraping. This strategy allows the BrightData
    service to use the correct URL based on the selected assistant.
    """

    @abstractmethod
    def get_url(self) -> str:
        """Return the scraping URL for this assistant."""
        ...

    @abstractmethod
    def get_assistant_id(self) -> int:
        """Return the database assistant ID."""
        ...

    @abstractmethod
    def get_assistant_name(self) -> str:
        """Return the assistant name for logging/display."""
        ...
