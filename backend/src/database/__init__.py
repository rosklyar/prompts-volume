"""Database package for PostgreSQL with pgvector support."""

from src.database.init import seed_evals_data, seed_initial_data, seed_superuser
from src.database.models import BusinessDomain, Country, CountryLanguage, Language, Prompt, PromptGroup, PromptGroupBinding, Topic
from src.database.session import (
    Base,
    close_db,
    get_async_session,
    get_engine,
    get_session_maker,
    init_db,
)
from src.database.evals_session import (
    EvalsBase,
    close_evals_db,
    get_evals_session,
    get_evals_engine,
    get_evals_session_maker,
    init_evals_db,
)

__all__ = [
    # Session management (prompts_db)
    "Base",
    "get_async_session",
    "get_engine",
    "get_session_maker",
    "init_db",
    "close_db",
    # Session management (evals_db)
    "EvalsBase",
    "get_evals_session",
    "get_evals_engine",
    "get_evals_session_maker",
    "init_evals_db",
    "close_evals_db",
    # Models (prompts_db)
    "Country",
    "Language",
    "CountryLanguage",
    "BusinessDomain",
    "Topic",
    "Prompt",
    "PromptGroup",
    "PromptGroupBinding",
    # Initialization
    "seed_initial_data",
    "seed_evals_data",
    "seed_superuser",
]
