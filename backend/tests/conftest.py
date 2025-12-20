"""Pytest configuration and fixtures for testing."""

import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
import src.database.session as db_session
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from src.database import Base, seed_initial_data
from src.main import app
from src.auth.crud import create_user
from src.auth.models import UserCreate
from src.auth.security import create_access_token
from src.businessdomain.services import BusinessDomainService
from src.evaluations.services.evaluation_service import EvaluationService
from src.geography.services import CountryService, LanguageService
from src.topics.services import TopicService


@pytest.fixture(scope="session")
def postgres_container():
    """
    Session-scoped fixture that provides a PostgreSQL container with pgvector.
    The container is started once for all tests and stopped at the end.
    """
    with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def db_url(postgres_container):
    """Get the database URL from the container."""
    return postgres_container.get_connection_url()


@pytest_asyncio.fixture(scope="function")
async def test_engine(db_url):
    """
    Function-scoped fixture that provides an async engine connected to the test database.
    """
    # Create async engine
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)

    # Enable pgvector extension
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    """
    Function-scoped fixture that provides a fresh database session for each test.
    Rolls back changes after each test to ensure isolation.
    """
    # Create session maker
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        # Seed initial data for each test
        await seed_initial_data(session)

        yield session

        # Cleanup after test
        await session.close()


@pytest.fixture(scope="function")
def override_get_db(test_session):
    """
    Fixture to override the FastAPI database dependency for integration tests.

    Usage:
        def test_endpoint(client, override_get_db):
            app.dependency_overrides[get_async_session] = override_get_db
            response = client.get("/endpoint")
            # ... assertions
    """
    async def _override_get_db():
        yield test_session

    return _override_get_db


@pytest.fixture(scope="function")
def client(test_engine):
    """
    Fixture that provides a FastAPI TestClient with database dependency overridden.
    Also sets the global database engine to use the test engine.

    Note: This is a sync fixture that creates its own session for TestClient's event loop.
    The test_session fixture is for async tests only.
    """
    # Store original engine and session maker
    original_engine = db_session._engine
    original_session_maker = db_session._async_session_maker

    # Override global database engine and session maker BEFORE creating TestClient
    # This ensures app lifespan uses test database
    db_session._engine = test_engine
    db_session._async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # TestClient will use the overridden engine via get_async_session dependency
    # No need to override get_async_session - it will use the overridden engine

    with TestClient(app) as test_client:
        yield test_client

    # Restore original engine and session maker
    db_session._engine = original_engine
    db_session._async_session_maker = original_session_maker

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def country_service(test_session):
    """
    Fixture that provides a CountryService instance for testing.
    """
    return CountryService(test_session)


@pytest.fixture(scope="function")
def business_domain_service(test_session):
    """
    Fixture that provides a BusinessDomainService instance for testing.
    """
    return BusinessDomainService(test_session)


@pytest.fixture(scope="function")
def language_service(test_session):
    """
    Fixture that provides a LanguageService instance for testing.
    """
    return LanguageService(test_session)


@pytest.fixture(scope="function")
def topic_service(test_session):
    """
    Fixture that provides a TopicService instance for testing.
    """
    return TopicService(test_session)


@pytest.fixture(scope="function")
def evaluation_service_short_timeout(test_session):
    """
    Fixture that provides an EvaluationService with a very short timeout.
    Useful for testing timeout behavior without long waits.
    """
    # Use 0.001 hours = 3.6 seconds for testing
    return EvaluationService(
        session=test_session,
        min_days_since_last_evaluation=1,
        evaluation_timeout_hours=0.001
    )


@pytest_asyncio.fixture(scope="function")
async def test_user(test_engine):
    """
    Fixture that creates a test user in the database.
    Uses the test_engine to create a session and user.
    Each invocation creates a user with a unique email to avoid conflicts.
    Returns the created User object.
    """
    # Create a new session using the test engine
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Use UUID to ensure unique email per test
    unique_email = f"test-{uuid.uuid4()}@example.com"

    async with async_session_maker() as session:
        user = await create_user(
            session,
            UserCreate(
                email=unique_email,
                password="testpassword123",
                full_name="Test User",
                is_active=True,
                is_superuser=False,
            ),
        )
        # Detach the user from the session so it can be used outside
        session.expunge(user)
        return user


@pytest.fixture(scope="function")
def auth_token(test_user):
    """
    Fixture that creates a JWT access token for the test user.
    Returns the token string.
    """
    token = create_access_token(
        subject=test_user.id,
        expires_delta=timedelta(minutes=30),
    )
    return token


@pytest.fixture(scope="function")
def auth_headers(auth_token):
    """
    Fixture that provides authorization headers with Bearer token.
    Returns a dict with Authorization header.
    """
    return {"Authorization": f"Bearer {auth_token}"}
