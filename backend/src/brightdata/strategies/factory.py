"""Factory for creating assistant-specific URL strategies."""

from src.brightdata.strategies.base import AssistantUrlStrategy
from src.brightdata.strategies.chatgpt import ChatGPTStrategy


class AssistantStrategyFactory:
    """Factory for creating assistant-specific URL strategies.

    Maps assistant IDs (from database) to their corresponding strategy
    implementations. New assistants can be added by registering their
    strategies.
    """

    _strategies: dict[int, type[AssistantUrlStrategy]] = {
        ChatGPTStrategy.ASSISTANT_ID: ChatGPTStrategy,
    }

    @classmethod
    def get_strategy(cls, assistant_id: int) -> AssistantUrlStrategy:
        """Get the URL strategy for the given assistant ID.

        Args:
            assistant_id: Database ID of the AI assistant.

        Returns:
            Instance of the appropriate strategy.

        Raises:
            ValueError: If no strategy is registered for the given ID.
        """
        strategy_cls = cls._strategies.get(assistant_id)
        if strategy_cls is None:
            registered = list(cls._strategies.keys())
            raise ValueError(
                f"Unknown assistant_id: {assistant_id}. "
                f"Registered assistant IDs: {registered}"
            )
        return strategy_cls()

    @classmethod
    def register(
        cls,
        assistant_id: int,
        strategy: type[AssistantUrlStrategy],
    ) -> None:
        """Register a new strategy for an assistant ID.

        Args:
            assistant_id: Database ID of the AI assistant.
            strategy: Strategy class to use for this assistant.
        """
        cls._strategies[assistant_id] = strategy

    @classmethod
    def get_supported_assistant_ids(cls) -> list[int]:
        """Return list of supported assistant IDs."""
        return list(cls._strategies.keys())
