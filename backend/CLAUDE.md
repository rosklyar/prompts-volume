# CLAUDE.md

## Project Overview

FastAPI service providing:
- JWT authentication
- Prompt search (vector similarity)
- Prompt groups (CRUD, bindings)
- Evaluation workflows
- Report generation with billing

## Tech Stack

- Python 3.12
- FastAPI for serving requests
- DataForSEO API for keyword research
- uv for dependency management, build tool, and running code/tests
- Docker for containerization
- PostgreSQL for state management
- Alembic for database migrations

## Development Commands

### Local Development (with uv)

- **Setup**: Copy `.env.example` to `.env` and add your DataForSEO API credentials
- Run the application: `uv run uvicorn src.main:app --reload`
- Run tests: `uv run pytest`
- Run a single test: `uv run pytest tests/path/to/test_file.py::test_function_name`
- Add dependencies: `uv add <package-name>`

### Database Migrations (Alembic)

Three databases with separate migration paths:

| Database | Apply | Generate | Models |
|----------|-------|----------|--------|
| prompts_db | `uv run alembic -c alembic/prompts/alembic.ini upgrade head` | `... revision --autogenerate -m "desc"` | `src/database/models.py` |
| users_db | `uv run alembic -c alembic/users/alembic.ini upgrade head` | `... revision --autogenerate -m "desc"` | `src/database/users_models.py` |
| evals_db | `uv run alembic -c alembic/evals/alembic.ini upgrade head` | `... revision --autogenerate -m "desc"` | `src/database/evals_models.py` |

**Note:** Migrations run automatically on Docker container startup.

### Docker

- Build: `docker build -t prompts-volume:latest .`
- Run: `docker run -p 8000:8000 prompts-volume:latest`

### API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Repository Structure

Domain-Driven Design with clear separation of concerns:

**Domain Modules:**
- `src/businessdomain/` - Business domain classification
- `src/geography/` - Geographic and linguistic data
- `src/topics/` - Topic generation and matching
- `src/prompts/` - Prompt search and generation (main router)
- `src/evaluations/` - Prompt evaluation tracking
- `src/prompt_groups/` - User prompt group management
- `src/billing/` - Pay-as-you-go billing system
- `src/reports/` - Report generation

**Infrastructure Modules:**
- `src/embeddings/` - ML pipeline (sentence-transformers, HDBSCAN)
- `src/database/` - SQLAlchemy models, sessions
- `src/config/` - Pydantic settings
- `src/utils/` - Shared utilities
- `alembic/` - Database migrations
- `tests/` - Integration tests (pytest)

## Coding Guidelines

1. **Look Before You Leap** - Check conditions explicitly, don't rely on exceptions for control flow
2. **Never Swallow Exceptions** - Let exceptions propagate; no bare `except:` or silent failures
3. **Defer Import-Time Computation** - Use `@cache` for lazy initialization, avoid module-level side effects
4. **Verify Casts at Runtime** - Add `isinstance()` check before `typing.cast()`
5. **Use Literal Types** - Model fixed values (status codes, types) as `Literal["a", "b"]` not `str`
6. **Keyword Args for 5+ params** - Use `*` separator to force keyword-only arguments
7. **Use solid-architect agent** - When designing new modules, classes, or components, invoke solid-architect to ensure proper SOLID principles and module boundaries

## Architecture Guidelines

### Service Patterns

| Pattern | Purpose | Example |
|---------|---------|---------|
| Database Service | CRUD operations | `TopicService`, `PromptService` |
| External API Service | Third-party integrations | `DataForSEOService` |
| Orchestrator Service | Coordinate multiple services | `CompanyMetaInfoService` |
| Provider Service | Generate domain objects | `TopicsProvider` |

### Model Organization

| Type | Location | Example |
|------|----------|---------|
| Internal (dataclasses) | `domain/models/` | `CompanyMetaInfo`, `GeneratedTopic` |
| API (Pydantic) | `domain/models/api_models.py` | `*Response`, `*Request` |
| Database (SQLAlchemy) | `src/database/models.py` | `Topic`, `Prompt`, `PromptGroup` |

### Dependency Injection

Inject only specific config values, not entire `Settings` object:

```python
# ✅ Good - inject specific value
class MyService:
    def __init__(self, session: AsyncSession, *, api_key: str):
        self.session = session
        self.api_key = api_key

def get_my_service(session: AsyncSession = Depends(get_async_session)) -> MyService:
    return MyService(session, api_key=settings.api_key)
```

### Country/Location Handling

- Use ISO codes (`US`, `GB`, `UA`) as API parameters
- Accept case-insensitive codes (convert to uppercase internally)
- `CountryService` and `LanguageService` in `src/geography/services/`
