from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.billing.router import router as billing_router
from src.reference.router import router as reference_router
from src.config.settings import settings
from src.database import close_db, get_session_maker, init_db, seed_evals_data, seed_initial_data, seed_superuser
from src.database.users_session import close_users_db, get_users_session_maker, init_users_db
from src.database.evals_session import close_evals_db, get_evals_session_maker, init_evals_db
from src.evaluations.router import router as evaluations_router
from src.prompt_groups.router import router as prompt_groups_router
from src.prompts import router as prompts_router
from src.prompts.batch import batch_router
from src.reports.router import router as reports_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Initialize all three databases
    await init_db()  # prompts_db
    await init_users_db()  # users_db
    await init_evals_db()  # evals_db

    # Seed initial data (prompts, topics, etc.) in prompts_db
    session_maker = get_session_maker()
    async with session_maker() as session:
        await seed_initial_data(session)

    # Seed superuser in users_db
    users_session_maker = get_users_session_maker()
    async with users_session_maker() as users_session:
        await seed_superuser(users_session)

    # Seed evals data (AI assistants, plans, evaluations) in evals_db
    evals_session_maker = get_evals_session_maker()
    async with session_maker() as prompts_session:
        async with evals_session_maker() as evals_session:
            await seed_evals_data(prompts_session, evals_session)

    yield

    # Shutdown: Close all three database connections
    await close_db()
    await close_users_db()
    await close_evals_db()


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
app.include_router(admin_router)
app.include_router(auth_router)
app.include_router(reference_router)
app.include_router(prompts_router.router)
app.include_router(batch_router)
app.include_router(evaluations_router)
app.include_router(prompt_groups_router)
app.include_router(billing_router)
app.include_router(reports_router)


@app.get("/health")
async def health():
    return {"status": "UP"}
