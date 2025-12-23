# Prompts Volume

Full-stack AI-powered prompts management platform

## Overview

**Backend:** FastAPI service for AI-powered prompt generation and management
**Frontend:** React + TypeScript web application for user authentication and prompt interaction

## Features

- User authentication (JWT-based)
- AI-powered prompt generation
- Semantic search with vector similarity in prompts database([paraphrase-multilingual-MiniLM-L12-v2 embedder supports 50+ languages](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2))
- Prompts periodic evaluation
- Priority evaluation for prompts not from db

## Architecture

![Architecture Diagram](arhitecture.png)

## Demo

### Smartphones group with existing prompts

https://github.com/user-attachments/assets/d46eee20-31be-448f-84e4-562162ec76f9

### GEO group with new prompt

https://github.com/user-attachments/assets/70568a80-b094-4a24-96ea-99367ea30b60

## Quick Start

### Prerequisites

- Docker & Docker Compose
- (Optional) DataForSEO API credentials
- (Optional) OpenAI API key

### Running with Docker Compose

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env and add API keys (optional for basic auth testing)

# 2. Start all services
docker-compose up -d

# 3. Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
```

**Default credentials:**
- Email: `admin@example.com`
- Password: `changethis`

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 5173 | React dev server |
| Backend | 8000 | FastAPI application |
| PostgreSQL | 5432 | Database with pgvector |
| Chat-automation |    | Playwright dockerized bot for scrapping answers
## Development

### Backend Development

See [backend/README.md](backend/README.md) for detailed backend documentation:
- API endpoints reference
- Architecture & DDD structure
- ML pipeline details
- Local development setup

```bash
cd backend
uv run uvicorn src.main:app --reload
```

### Frontend Development

See [frontend/README.md](frontend/README.md) for frontend setup:
- Component structure
- Authentication flow
- Local development

```bash
cd frontend
npm install
npm run dev
```

## Technology Stack

### Frontend
- React 18 + TypeScript
- Vite (build tool)
- TanStack Router (file-based routing)
- TanStack Query (server state)
- Tailwind CSS v4

### Backend
- FastAPI (async Python)
- PostgreSQL + pgvector
- JWT authentication (bcrypt)
- sentence-transformers (embeddings)
- OpenAI API (generation)

## Project Structure

```
prompts-volume/
├── backend/              # FastAPI service
│   ├── src/
│   │   ├── auth/        # JWT authentication
│   │   ├── prompts/     # Prompt generation
│   │   ├── topics/      # Topic matching
│   │   ├── database/    # ORM models
│   │   └── ...
│   └── tests/
├── frontend/            # React application
│   ├── src/
│   │   ├── routes/      # Pages (login, signup, dashboard)
│   │   ├── hooks/       # useAuth, etc.
│   │   └── components/  # UI components
│   └── ...
└── docker-compose.yml   # Multi-service orchestration
```

## Documentation

- [Backend README](backend/README.md) - API reference, architecture, development
- [Frontend README](frontend/README.md) - UI setup, component structure
- [CLAUDE.md](CLAUDE.md) - AI assistant development guidelines
