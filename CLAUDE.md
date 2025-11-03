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

All commands use `uv`:

- Run the application: `uv run uvicorn src.main:app --reload`
- Run tests: `uv run pytest`
- Run a single test: `uv run pytest tests/path/to/test_file.py::test_function_name`
- Add dependencies: `uv add <package-name>`

## Repository Structure

- `src/` - All source code
- `tests/` - All test files (pytest)
- `.Dockerfile` - Docker configuration
- `.env.example` - Environment variable template
