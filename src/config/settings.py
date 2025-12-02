"""Application settings and configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # DataForSEO API credentials
    dataforseo_username: str = ""
    dataforseo_password: str = ""

    # Database configuration
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prompts"
    database_echo: bool = False


# Singleton settings instance
settings = Settings()
