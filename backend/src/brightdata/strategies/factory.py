"""Factory for creating assistant-specific strategies."""

from src.brightdata.strategies.base import AssistantStrategy
from src.brightdata.strategies.chatgpt import ChatGPTStrategy
from src.brightdata.strategies.gemini import GeminiStrategy
from src.brightdata.strategies.perplexity import PerplexityStrategy


class AssistantStrategyFactory:
    """Factory for creating assistant-specific strategies.

    Maps assistant IDs and keys (from database) to their corresponding strategy
    implementations. Caches instances since strategies are stateless.
    """

    _strategies: dict[int, type[AssistantStrategy]] = {
        1: ChatGPTStrategy,
        2: PerplexityStrategy,
        3: GeminiStrategy,
    }

    _strategies_by_key: dict[str, type[AssistantStrategy]] = {
        "chatgpt": ChatGPTStrategy,
        "perplexity": PerplexityStrategy,
        "gemini": GeminiStrategy,
    }

    _instances: dict[int, AssistantStrategy] = {}

    @classmethod
    def get_strategy(cls, assistant_id: int) -> AssistantStrategy:
        """Get the strategy for the given assistant ID.

        Args:
            assistant_id: Database ID of the AI assistant.

        Returns:
            Cached instance of the appropriate strategy.

        Raises:
            ValueError: If no strategy is registered for the given ID.
        """
        if assistant_id not in cls._instances:
            strategy_cls = cls._strategies.get(assistant_id)
            if strategy_cls is None:
                registered = list(cls._strategies.keys())
                raise ValueError(
                    f"Unknown assistant_id: {assistant_id}. "
                    f"Registered assistant IDs: {registered}"
                )
            cls._instances[assistant_id] = strategy_cls()
        return cls._instances[assistant_id]

    @classmethod
    def get_strategy_by_key(cls, assistant_key: str) -> AssistantStrategy:
        """Get the strategy for the given assistant key.

        Args:
            assistant_key: URL-safe key of the AI assistant (e.g., "chatgpt", "perplexity").

        Returns:
            Cached instance of the appropriate strategy.

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
        # Use assistant_id to share cached instance
        instance = strategy_cls()
        assistant_id = instance.config.assistant_id
        if assistant_id not in cls._instances:
            cls._instances[assistant_id] = instance
        return cls._instances[assistant_id]

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
