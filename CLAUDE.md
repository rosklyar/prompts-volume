# CLAUDE.md

This file provides guidance for working with this full-stack application.

## Project Overview

Full-stack AI-powered prompts management platform with:
- **Backend:** FastAPI service (JWT auth, prompt generation, vector search)
- **Frontend:** React + TypeScript application (login, signup, dashboard)

## Architecture

```
Frontend (React) ←→ REST API ←→ Backend (FastAPI) ←→ PostgreSQL
```

- Frontend makes authenticated requests with JWT Bearer tokens
- Backend validates tokens and serves protected endpoints
- CORS enabled for frontend origin

## Development Setup

### Quick Start (Docker Compose)

```bash
docker-compose up -d
# Frontend: http://localhost:5173
# Backend: http://localhost:8000/docs
```

### Local Development

**Backend:**
```bash
cd backend
uv run uvicorn src.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Authentication Flow

1. User logs in via frontend (`/login`)
2. Frontend sends credentials to `POST /api/v1/login/access-token`
3. Backend validates and returns JWT token
4. Frontend stores token and includes in `Authorization: Bearer {token}` header
5. Backend validates token on protected routes via `CurrentUser` dependency

## Environment Variables

**Backend (`backend/.env`):**
- `SECRET_KEY` - JWT signing key
- `FRONTEND_URL` - CORS allowed origin (default: http://localhost:5173)
- `DATABASE_URL` - PostgreSQL connection string

**Frontend (`frontend/.env`):**
- `VITE_API_URL` - Backend API URL (default: http://localhost:8000)

## CORS Configuration

Backend CORS is configured in `backend/src/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Component-Specific Guidance

- **Backend development:** See [backend/CLAUDE.md](backend/CLAUDE.md)
- **Frontend development:** See [frontend/CLAUDE.md](frontend/CLAUDE.md)

## Docker Services

- `postgres` - PostgreSQL 16 + pgvector (port 5432)
- `backend` - FastAPI app (port 8000)
- `frontend` - Vite dev server (port 5173)

## Testing Full Integration

```bash
# 1. Start services
docker-compose up -d

# 2. Test backend
curl http://localhost:8000/health

# 3. Test login
curl -X POST http://localhost:8000/api/v1/login/access-token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=changethis"

# 4. Access frontend
open http://localhost:5173
```
