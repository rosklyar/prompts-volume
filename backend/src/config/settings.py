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

    # Evaluation configuration
    min_days_since_last_evaluation: int = 1
    evaluation_timeout_hours: int = 2
    evaluation_api_tokens: str = ""  # CSV list of allowed tokens for evaluation API

    # Priority prompts configuration
    max_priority_prompts_per_request: int = 50

    # Similar prompts search configuration
    similar_prompts_max_k: int = 100
    similar_prompts_min_similarity_threshold: float = 0.7

    # Batch upload configuration
    batch_upload_max_prompts: int = 100
    batch_upload_similarity_threshold: float = 0.90   # Min similarity to show matches
    batch_upload_match_limit: int = 3
    batch_upload_duplicate_threshold: float = 0.995   # Mark as duplicate (non-selectable)

    # Database configuration
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prompts"
    users_database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/users"
    evals_database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/evals"
    database_echo: bool = False

    # Auth configuration
    secret_key: str = "changethis"
    access_token_expire_minutes: int = 60 * 24 * 8  # 8 days
    first_superuser_email: str = "admin@example.com"
    first_superuser_password: str = "changethis"

    # CORS configuration
    frontend_url: str = "http://localhost:5173"

    # Billing configuration
    billing_price_per_evaluation: float = 0.01  # Price in dollars per evaluation
    billing_price_per_generation: float = 1.00  # Price in dollars per generate call
    billing_signup_credits: float = 10.00  # Initial credits for new users
    billing_signup_credits_expiry_days: int = 30  # Days until signup credits expire

    # Comparison time estimations (for freshness analysis)
    comparison_in_progress_estimate: str = "~15 minutes"
    comparison_next_refresh_estimate: str = "up to 6 hours"


# Singleton settings instance
settings = Settings()
