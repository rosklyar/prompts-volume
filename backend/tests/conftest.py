"""Pytest configuration and fixtures for testing."""

import gzip
import json
import uuid
from datetime import timedelta

import pytest
import pytest_asyncio
import src.database.session as db_session
import src.database.users_session as users_db_session
import src.database.evals_session as evals_db_session
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from src.database import Base, seed_initial_data, seed_evals_data
from src.database.users_session import UsersBase
from src.database.users_models import User
from src.database.evals_session import EvalsBase
from src.main import app
from src.auth.crud import create_user
from src.auth.models import UserCreate
from src.auth.security import create_access_token
from src.config.settings import settings
from src.businessdomain.services import BusinessDomainService
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
    Creates tables for prompts_db (Base), users_db (UsersBase), and evals_db (EvalsBase).
    """
    # Create async engine
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)

    # Enable pgvector extension
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Create all tables for all three databases (using same engine for tests)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(UsersBase.metadata.create_all)
        await conn.run_sync(EvalsBase.metadata.create_all)

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
        # Seed initial data for each test (prompts_db)
        await seed_initial_data(session)
        # Seed evals data (using same session since we use single test DB)
        await seed_evals_data(session, session)

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
    Also sets the global database engine to use the test engine for all three databases.
    Seeds initial data for integration tests.

    Note: This is a sync fixture that creates its own session for TestClient's event loop.
    The test_session fixture is for async tests only.
    """
    import asyncio

    # Store original engine and session maker for prompts_db
    original_engine = db_session._engine
    original_session_maker = db_session._async_session_maker

    # Store original engine and session maker for users_db
    original_users_engine = users_db_session._users_engine
    original_users_session_maker = users_db_session._users_async_session_maker

    # Store original engine and session maker for evals_db
    original_evals_engine = evals_db_session._evals_engine
    original_evals_session_maker = evals_db_session._evals_async_session_maker

    # Create shared session maker for test engine
    test_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Override global database engine and session maker BEFORE creating TestClient
    # This ensures app lifespan uses test database
    db_session._engine = test_engine
    db_session._async_session_maker = test_session_maker

    # Override users_db engine and session maker (using same test engine)
    users_db_session._users_engine = test_engine
    users_db_session._users_async_session_maker = test_session_maker

    # Override evals_db engine and session maker (using same test engine)
    evals_db_session._evals_engine = test_engine
    evals_db_session._evals_async_session_maker = test_session_maker

    # Seed initial data for integration tests
    async def seed_data():
        async with test_session_maker() as session:
            await seed_initial_data(session)
            await seed_evals_data(session, session)

    asyncio.get_event_loop().run_until_complete(seed_data())

    # TestClient will use the overridden engine via get_async_session dependency
    # No need to override get_async_session - it will use the overridden engine

    with TestClient(app) as test_client:
        yield test_client

    # Restore original engine and session maker for prompts_db
    db_session._engine = original_engine
    db_session._async_session_maker = original_session_maker

    # Restore original engine and session maker for users_db
    users_db_session._users_engine = original_users_engine
    users_db_session._users_async_session_maker = original_users_session_maker

    # Restore original engine and session maker for evals_db
    evals_db_session._evals_engine = original_evals_engine
    evals_db_session._evals_async_session_maker = original_evals_session_maker

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


@pytest_asyncio.fixture(scope="function")
async def test_superuser(test_engine):
    """
    Fixture that creates a test superuser in the database.
    Uses the test_engine to create a session and user.
    Each invocation creates a superuser with a unique email to avoid conflicts.
    Returns the created User object.
    """
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    unique_email = f"admin-{uuid.uuid4()}@example.com"

    async with async_session_maker() as session:
        user = await create_user(
            session,
            UserCreate(
                email=unique_email,
                password="adminpassword123",
                full_name="Admin User",
                is_active=True,
                is_superuser=True,
            ),
        )
        session.expunge(user)
        return user


@pytest.fixture(scope="function")
def superuser_auth_token(test_superuser):
    """
    Fixture that creates a JWT access token for the test superuser.
    Returns the token string.
    """
    token = create_access_token(
        subject=test_superuser.id,
        expires_delta=timedelta(minutes=30),
    )
    return token


@pytest.fixture(scope="function")
def superuser_auth_headers(superuser_auth_token):
    """
    Fixture that provides authorization headers with Bearer token for superuser.
    Returns a dict with Authorization header.
    """
    return {"Authorization": f"Bearer {superuser_auth_token}"}


@pytest.fixture(scope="function")
def create_verified_user(client, test_engine):
    """
    Fixture that provides a factory function to create verified users.

    Since public signup now requires email verification, this fixture:
    1. Signs up the user via public API
    2. Verifies the user using the CRUD function (which also grants signup credits)
    3. Logs in and returns auth headers

    Usage in tests:
        def test_example(client, create_verified_user):
            auth_headers = create_verified_user(
                email="test@example.com",
                password="testpassword123"
            )
    """
    import asyncio

    def _create_user(email: str, password: str, full_name: str = "Test User") -> dict:
        # Step 1: Sign up
        signup_response = client.post(
            "/api/v1/users/signup",
            json={
                "email": email,
                "password": password,
                "full_name": full_name,
            },
        )
        assert signup_response.status_code == 200, f"Signup failed: {signup_response.json()}"

        # Step 2: Verify email using CRUD function (grants signup credits too)
        async def verify_user():
            from sqlalchemy import select
            from src.auth.crud import verify_user_email as crud_verify_user_email

            async_session_maker = async_sessionmaker(
                bind=test_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
            async with async_session_maker() as session:
                result = await session.execute(
                    select(User).where(User.email == email)
                )
                user = result.scalar_one()
                await crud_verify_user_email(session, user)

        asyncio.get_event_loop().run_until_complete(verify_user())

        # Step 3: Login and return auth headers
        login_response = client.post(
            "/api/v1/login/access-token",
            data={"username": email, "password": password},
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.json()}"
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _create_user


@pytest.fixture(scope="function")
def simulate_webhook(client):
    """Factory fixture to simulate Bright Data webhook calls.

    Usage:
        def test_example(client, simulate_webhook, auth_headers):
            # Request fresh execution to create a batch
            resp = client.post("/execution/api/v1/request-fresh", json={"prompt_ids": [1, 2]}, headers=auth_headers)
            batch_id = resp.json()["batch_id"]

            # Simulate webhook with matching prompt texts
            items = [
                {"prompt": "Prompt text 1", "answer_text": "Response 1", "citations": []},
                {"prompt": "Prompt text 2", "answer_text": "Response 2", "citations": []},
            ]
            webhook_resp = simulate_webhook(batch_id, items)
            assert webhook_resp.status_code == 200
    """
    def _simulate(batch_id: str, items: list[dict]):
        """Simulate Bright Data webhook.

        Args:
            batch_id: UUID batch identifier from request-fresh response
            items: List of dicts with keys:
                - prompt: str (must match Prompt.prompt_text exactly)
                - answer_text: str
                - citations: list[dict] with url, domain, cited, title keys (optional)
        """
        payload = json.dumps(items).encode("utf-8")
        compressed = gzip.compress(payload)

        return client.post(
            f"/evaluations/api/v1/webhook/{batch_id}",
            content=compressed,
            headers={
                "Authorization": f"Basic {settings.brightdata_webhook_secret}",
                "Content-Type": "application/octet-stream",
            },
        )

    return _simulate
