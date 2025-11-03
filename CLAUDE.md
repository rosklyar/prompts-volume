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

- `src/` - All source code
  - `src/main.py` - Application entry point, includes routers and health endpoint
  - `src/config/` - Configuration files and mappings
    - `src/config/countries.py` - ISO country code to location name mapping (94 countries)
    - `src/config/settings.py` - Application settings (DataForSEO credentials from env vars)
  - `src/services/` - External service integrations
    - `src/services/dataforseo_service.py` - DataForSEO API client for keyword research
  - `src/routers/` - API route handlers (FastAPI routers)
  - `src/utils/` - Reusable utility functions and helpers
- `tests/` - All test files (pytest)
- `Dockerfile` - Docker configuration
- `.env.example` - Environment variable template

## Architecture Guidelines

### Single Responsibility Principle (SRP)

Always follow the Single Responsibility Principle when writing code:

- **Create separate components** for identifiable pieces of functionality
- **Extract utilities** when logic can be reused (e.g., URL validation, data transformation)
- **Use routers** to organize endpoints by domain/feature area
- **Keep main.py minimal** - only application setup and health checks
- **Service layer** - External API calls should be in dedicated service classes in `src/services/`
- **Configuration** - Use `pydantic-settings` for environment-based configuration; store static mappings in `src/config/`

When adding new functionality, ask: "Does this belong in a separate module/utility?" If a function does more than one thing, split it into focused, single-purpose components.

### API Integration Pattern

When integrating external APIs:
1. Create a service class in `src/services/` (e.g., `DataForSEOService`)
2. Store credentials in environment variables, loaded via `src/config/settings.py`
3. Handle errors comprehensively with meaningful HTTPException messages
4. Mock external API calls in tests using `unittest.mock` or `pytest-mock`

### Country/Location Handling

- Use ISO country codes (e.g., `US`, `GB`, `UA`) as API parameters
- Map ISO codes to location names in `src/config/countries.py`
- Support 94 countries as defined in the country mapping
- Accept case-insensitive ISO codes (convert to uppercase internally)
