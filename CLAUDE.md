# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI service that proposes prompts for businesses. The main functionality provides topic/keyword suggestions relevant to a business and their industry via the endpoint: `GET /prompts/api/v1/topics?url=tryprofound.com&iso_code=US`

Keywords are fetched from the DataForSEO API and can be filtered by location using ISO country codes.

## Tech Stack

- Python 3.12
- FastAPI for serving requests
- DataForSEO API for keyword research
- uv for dependency management, build tool, and running code/tests
- Docker for containerization
- PostgreSQL for state management

## Development Commands

### Local Development (with uv)

- **Setup**: Copy `.env.example` to `.env` and add your DataForSEO API credentials
- Run the application: `uv run uvicorn src.main:app --reload`
- Run tests: `uv run pytest`
- Run a single test: `uv run pytest tests/path/to/test_file.py::test_function_name`
- Add dependencies: `uv add <package-name>`

### Docker

- Build image: `docker build -t prompts-volume:latest .`
- Run container: `docker run -p 8000:8000 prompts-volume:latest`
- Run in detached mode: `docker run -d -p 8000:8000 --name prompts-volume prompts-volume:latest`

### API Documentation

When the application is running:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Repository Structure

The project follows Domain-Driven Design (DDD) with clear separation of concerns:

### Domain Modules

- **`src/businessdomain/`** - Business domain classification
  - `models/` - CompanyMetaInfo, API responses (CompanyMetaInfoResponse, DBTopicResponse, etc.)
  - `services/` - BusinessDomainService, BusinessDomainDetectionService, CompanyMetaInfoService

- **`src/geography/`** - Geographic and linguistic data
  - `services/` - CountryService, LanguageService

- **`src/topics/`** - Topic generation and matching
  - `models/` - GeneratedTopic, TopicMatchResult
  - `services/` - TopicService, TopicsProvider, TopicRelevanceFilterService

- **`src/prompts/`** - Prompts generation and retrieval
  - `router.py` - API endpoints (main router)
  - `models/` - Request/response models (cluster_prompts, prompt_responses, generate_request)
  - `services/` - PromptService, DataForSEOService, PromptsGeneratorService

### Infrastructure Modules

- **`src/embeddings/`** - ML pipeline (local models)
  - `embeddings_service.py` - sentence-transformers for text embeddings
  - `clustering_service.py` - HDBSCAN for semantic clustering

- **`src/database/`** - Data persistence layer
  - `models.py` - SQLAlchemy ORM models (Topic, Prompt, Country, etc.)
  - `session.py` - Database connection and vector index setup
  - `init.py` - Database seeding logic

- **`src/config/`** - Application configuration
  - `settings.py` - Environment-based settings (Pydantic)

- **`src/utils/`** - Shared utilities
  - `keyword_filters.py` - Keyword filtering logic
  - `url_validator.py` - URL validation

- **`src/data/`** - Static data files
  - CSV files with pre-seeded prompts

- **`tests/`** - Integration tests (pytest)

### Core Principles

1. **Domain-Driven Design**: Code organized by business domains (businessdomain, geography, topics, prompts)
2. **Single Responsibility**: Each service has one clear purpose
3. **Separation of Concerns**: Models, services, and infrastructure clearly separated
4. **Dependency Direction**: Domain services depend on infrastructure, not vice versa

## Architecture Guidelines

### Module Organization

**Domain Modules** (business logic):
- Each domain has its own directory under `src/`
- Contains `models/` (data structures) and `services/` (business logic)
- Examples: `businessdomain/`, `geography/`, `topics/`, `prompts/`

**Infrastructure Modules** (technical concerns):
- Support domain modules with technical capabilities
- Examples: `database/`, `embeddings/`, `config/`, `utils/`

### Service Organization Patterns

1. **Database Services**:
   - Named `*_service.py` (e.g., `topic_service.py`)
   - Handle CRUD operations for domain entities
   - Located in domain's `services/` directory

2. **External API Services**:
   - Named `*_service.py` (e.g., `data_for_seo_service.py`)
   - Encapsulate external API calls
   - Handle authentication and error handling

3. **Orchestrator Services**:
   - Coordinate multiple services to fulfill complex operations
   - Example: `CompanyMetaInfoService` orchestrates domain detection + topic generation

4. **Provider Services**:
   - Generate or provide domain objects using external resources
   - Example: `TopicsProvider` generates topics using LLM + DB matching

### Model Organization

**Internal Models** (dataclasses):
- Domain-specific data structures for internal use
- Located in domain's `models/` directory
- Example: `CompanyMetaInfo`, `GeneratedTopic`, `TopicMatchResult`

**API Models** (Pydantic):
- Request/response models for API endpoints
- Named `*_request.py`, `*_responses.py`, or `api_models.py`
- Located in domain's `models/` directory
- Example: `CompanyMetaInfoResponse`, `GeneratedPrompts`

**Database Models** (SQLAlchemy):
- ORM models for database tables
- Located in `src/database/models.py`
- Example: `Topic`, `Prompt`, `Country`

### Naming Conventions

- **API Response Models**: End with `Response` (e.g., `CompanyMetaInfoResponse`)
- **Services**: End with `Service` (e.g., `TopicService`, `PromptService`)
- **Providers**: End with `Provider` (e.g., `TopicsProvider`)
- **Avoid naming conflicts**: Use descriptive names (e.g., `TopicWithClusters` for API model vs `Topic` for DB model)

### Single Responsibility Principle (SRP)

Always follow the Single Responsibility Principle when writing code:

**Domain Organization**:
- **Group by domain** first, then by concern (models vs services)
- Each domain directory represents a cohesive business concept
- Example: `businessdomain/` handles all business classification logic

**Service Responsibilities**:
- **Create separate services** for distinct operations
- Database operations → separate service (e.g., `TopicService`)
- External API calls → separate service (e.g., `DataForSEOService`)
- LLM operations → separate service (e.g., `TopicsProvider`)
- Orchestration → separate service (e.g., `CompanyMetaInfoService`)

**Model Separation**:
- Internal dataclasses → domain's `models/` directory
- API request/response models → domain's `models/` directory (separate files)
- Database models → `src/database/models.py`

**Extract utilities** when logic can be reused (e.g., URL validation, keyword filtering)

**Keep main.py minimal** - only application setup, lifespan, and health endpoint

When adding new functionality, ask:
1. "Which domain does this belong to?"
2. "Is this a service, model, or utility?"
3. "Does this service do more than one thing?"

### Dependency Injection Pattern

**Settings Injection**:
- NEVER import the `settings` singleton directly in service classes
- ALWAYS inject only the specific configuration values needed via constructor parameters
- This follows the Interface Segregation Principle and makes services more testable
- Only inject what you actually need - don't pass entire `Settings` object if you only need one value

Example:
```python
# ❌ BAD - Hard to test
from src.config.settings import settings

class MyService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def some_method(self):
        value = settings.some_config  # Hard-coded dependency

# ⚠️ ACCEPTABLE but not ideal - Over-injection
from src.config.settings import Settings, settings

class MyService:
    def __init__(self, session: AsyncSession, settings: Settings):
        self.session = session
        self.settings = settings  # Injecting entire Settings when only need one value

    def some_method(self):
        value = self.settings.some_config

# ✅ BEST - Inject only what you need
from src.config.settings import settings

class MyService:
    def __init__(self, session: AsyncSession, some_config: int):
        self.session = session
        self.some_config = some_config  # Only inject specific value

    def some_method(self):
        value = self.some_config  # Clean, minimal dependency

# Dependency injection function
def get_my_service(
    session: AsyncSession = Depends(get_async_session),
) -> MyService:
    return MyService(session, settings.some_config)
```

### API Integration Pattern

When integrating external APIs:
1. Create a service class in the appropriate domain's `services/` directory (e.g., `DataForSEOService` in `prompts/services/`)
2. Store credentials in environment variables, loaded via `src/config/settings.py`
3. Inject settings via constructor (see Dependency Injection Pattern above)
4. Handle errors comprehensively with meaningful HTTPException messages
5. Mock external API calls in tests using `unittest.mock` or `pytest-mock`

### Country/Location Handling

- Use ISO country codes (e.g., `US`, `GB`, `UA`) as API parameters
- CountryService and LanguageService handle geographic/linguistic data
- Located in `src/geography/services/`
- Accept case-insensitive ISO codes (convert to uppercase internally)
