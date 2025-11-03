# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI service that proposes prompts for businesses. The main functionality provides topic/keyword suggestions relevant to a business and their industry via the endpoint: `GET /volumes/api/v1/topics?url=tryprofound.com`

## Tech Stack

- Python 3.12
- FastAPI for serving requests
- uv for dependency management, build tool, and running code/tests
- Docker for containerization
- PostgreSQL for state management

## Development Commands

### Local Development (with uv)

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

When adding new functionality, ask: "Does this belong in a separate module/utility?" If a function does more than one thing, split it into focused, single-purpose components.
