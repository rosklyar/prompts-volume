from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import close_db, get_session_maker, init_db, seed_initial_data
from src.evaluations.router import router as evaluations_router
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

    yield

    # Shutdown: Close database connections
    await close_db()


app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(prompts_router.router)
app.include_router(evaluations_router)


@app.get("/health")
async def health():
    return {"status": "UP"}
