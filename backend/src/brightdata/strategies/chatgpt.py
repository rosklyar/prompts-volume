"""ChatGPT URL strategy for BrightData scraping."""

from src.brightdata.strategies.base import AssistantUrlStrategy


class ChatGPTStrategy(AssistantUrlStrategy):
    """Strategy for ChatGPT assistant scraping."""

    ASSISTANT_ID = 1
    ASSISTANT_NAME = "ChatGPT"
    URL = "https://chatgpt.com/"

    def get_url(self) -> str:
        """Return ChatGPT scraping URL."""
        return self.URL

    def get_assistant_id(self) -> int:
        """Return ChatGPT database ID."""
        return self.ASSISTANT_ID

    def get_assistant_name(self) -> str:
        """Return ChatGPT name."""
        return self.ASSISTANT_NAME
