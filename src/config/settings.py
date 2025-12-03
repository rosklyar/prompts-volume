"""Application settings and configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # OpenAI API credentials
    openai_api_key: str = ""

    # DataForSEO API credentials and configuration
    dataforseo_username: str = ""
    dataforseo_password: str = ""
    dataforseo_base_url: str = "https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live"
    dataforseo_batch_size: int = 1000
    dataforseo_max_total: int = 10000
    dataforseo_timeout: float = 30.0

    # Business Domain Detection configuration
    domain_detection_model: str = "gpt-4o-mini"

    # Topics Generation configuration
    topics_generation_model: str = "gpt-4o-mini"

    # Topics Provider configuration
    topics_provider_similarity_threshold: float = 0.9

    # Prompts Generator configuration
    pg_openai_model: str = "gpt-4o-mini"

    # Clustering configuration
    clustering_min_cluster_size: int = 5
    clustering_min_samples: int = 5
    clustering_cluster_selection_epsilon: float = 0.0

    # Topic Relevance Filter configuration
    topic_filter_similarity_threshold: float = 0.7
    topic_filter_min_relevant_ratio: float = 0.5

    # Database configuration
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prompts"
    database_echo: bool = False


# Singleton settings instance
settings = Settings()
