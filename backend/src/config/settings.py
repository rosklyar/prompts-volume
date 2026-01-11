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
    evaluation_timeout_hours: int = 2
    evaluation_api_tokens: str = ""  # CSV list of allowed tokens for evaluation API

    # Freshness thresholds (hours)
    freshness_fresh_threshold_hours: int = 24  # < 24h = fresh
    freshness_stale_threshold_hours: int = 72  # > 72h = very stale, 24-72h = stale

    # Execution queue configuration
    execution_timeout_hours: int = 2  # Hours before timed-out entries reset to PENDING

    # Similar prompts search configuration
    similar_prompts_max_k: int = 100
    similar_prompts_min_similarity_threshold: float = 0.5

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

    # Startup configuration
    seed_data: bool = False  # Enable data seeding on startup (for local dev only)
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    # CORS configuration
    frontend_url: str = "http://localhost:5173"

    # Brevo email configuration (uses HTTP API instead of SMTP to avoid port blocking)
    brevo_api_key: str = ""  # Set via BREVO_API_KEY env var
    brevo_sender_email: str = "llmheroai@gmail.com"
    brevo_sender_name: str = "LLM Hero"

    # Email verification configuration
    email_verification_token_expire_hours: int = 24

    # Billing configuration
    billing_price_per_evaluation: float = 0.01  # Price in dollars per evaluation
    billing_price_per_generation: float = 1.00  # Price in dollars per generate call
    billing_signup_credits: float = 10.00  # Initial credits for new users
    billing_signup_credits_expiry_days: int = 30  # Days until signup credits expire
    billing_max_signup_bonuses: int | None = 100  # Max users to receive signup bonus (None = unlimited)

    # Comparison time estimations (for freshness analysis)
    comparison_in_progress_estimate: str = "~15 minutes"
    comparison_next_refresh_estimate: str = "up to 6 hours"

    # Bright Data configuration
    brightdata_answers: bool = False  # Toggle: use Bright Data instead of bot polling
    brightdata_api_token: str = ""
    brightdata_dataset_id: str = "gd_m7aof0k82r803d5bjm"
    brightdata_base_url: str = "https://api.brightdata.com/datasets/v3/trigger"
    brightdata_timeout: float = 30.0
    brightdata_batch_ttl_hours: int = 24
    brightdata_webhook_secret: str = "dev-webhook-secret"  # For webhook auth
    brightdata_default_country: str = "UA"
    backend_webhook_base_url: str = "http://localhost:8000"


# Singleton settings instance
settings = Settings()
