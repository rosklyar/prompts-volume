"""Database package for PostgreSQL with pgvector support."""

from src.database.init import seed_initial_data, seed_superuser
from src.database.models import BusinessDomain, Country, CountryLanguage, Language, Prompt, Topic
from src.database.session import (
    Base,
    close_db,
    get_async_session,
    get_engine,
    get_session_maker,
    init_db,
)

__all__ = [
    # Session management
    "Base",
    "get_async_session",
    "get_engine",
    "get_session_maker",
    "init_db",
    "close_db",
    # Models (prompts_db)
    "Country",
    "Language",
    "CountryLanguage",
    "BusinessDomain",
    "Topic",
    "Prompt",
    # Initialization
    "seed_initial_data",
    "seed_superuser",
]
