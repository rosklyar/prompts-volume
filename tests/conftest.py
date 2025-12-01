"""Pytest configuration and fixtures for testing."""

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from src.database import Base, get_async_session, seed_initial_data
from src.main import app
from src.prompts.services.business_domain_service import BusinessDomainService
from src.prompts.services.country_service import CountryService
from src.prompts.services.topic_service import TopicService


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
def client(override_get_db):
    """
    Fixture that provides a FastAPI TestClient with database dependency overridden.
    """
    from fastapi.testclient import TestClient

    # Override database dependency
    app.dependency_overrides[get_async_session] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

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
def topic_service(test_session):
    """
    Fixture that provides a TopicService instance for testing.
    """
    return TopicService(test_session)
