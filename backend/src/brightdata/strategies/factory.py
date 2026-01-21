"""Factory for creating assistant-specific strategies."""

from src.brightdata.strategies.base import AssistantStrategy
from src.brightdata.strategies.chatgpt import ChatGPTStrategy
from src.brightdata.strategies.perplexity import PerplexityStrategy


class AssistantStrategyFactory:
    """Factory for creating assistant-specific strategies.

    Maps assistant IDs and keys (from database) to their corresponding strategy
    implementations. New assistants can be added by registering their strategies.
    """

    _strategies: dict[int, type[AssistantStrategy]] = {
        ChatGPTStrategy.ASSISTANT_ID: ChatGPTStrategy,
        PerplexityStrategy.ASSISTANT_ID: PerplexityStrategy,
    }

    _strategies_by_key: dict[str, type[AssistantStrategy]] = {
        "chatgpt": ChatGPTStrategy,
        "perplexity": PerplexityStrategy,
    }

    @classmethod
    def get_strategy(cls, assistant_id: int) -> AssistantStrategy:
        """Get the strategy for the given assistant ID.

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
    def get_strategy_by_key(cls, assistant_key: str) -> AssistantStrategy:
        """Get the strategy for the given assistant key.

        Args:
            assistant_key: URL-safe key of the AI assistant (e.g., "chatgpt", "perplexity").

        Returns:
            Instance of the appropriate strategy.

        Raises:
            ValueError: If no strategy is registered for the given key.
        """
        strategy_cls = cls._strategies_by_key.get(assistant_key.lower())
        if strategy_cls is None:
            registered = list(cls._strategies_by_key.keys())
            raise ValueError(
                f"Unknown assistant_key: {assistant_key}. "
                f"Registered assistant keys: {registered}"
            )
        return strategy_cls()

    @classmethod
    def register(
        cls,
        assistant_id: int,
        strategy: type[AssistantStrategy],
    ) -> None:
        """Register a new strategy for an assistant ID.

        Args:
            assistant_id: Database ID of the AI assistant.
            strategy: Strategy class to use for this assistant.
        """
        cls._strategies[assistant_id] = strategy
        # Also register by key if strategy has config
        instance = strategy()
        cls._strategies_by_key[instance.get_assistant_key()] = strategy

    @classmethod
    def get_supported_assistant_ids(cls) -> list[int]:
        """Return list of supported assistant IDs."""
        return list(cls._strategies.keys())

    @classmethod
    def get_supported_assistant_keys(cls) -> list[str]:
        """Return list of supported assistant keys."""
        return list(cls._strategies_by_key.keys())
