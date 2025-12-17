from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.config.settings import settings
from src.database import close_db, get_session_maker, init_db, seed_initial_data, seed_superuser
from src.evaluations.router import router as evaluations_router
from src.prompt_groups.router import router as prompt_groups_router
from src.prompts import router as prompts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Initialize database and seed data
    await init_db()

    # Seed initial data
    session_maker = get_session_maker()
    async with session_maker() as session:
        await seed_initial_data(session)
        await seed_superuser(session)

    yield

    # Shutdown: Close database connections
    await close_db()


app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(prompts_router.router)
app.include_router(evaluations_router)
app.include_router(prompt_groups_router)


@app.get("/health")
async def health():
    return {"status": "UP"}
