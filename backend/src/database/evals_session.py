"""Database configuration and session management for evals_db."""

from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from src.config.settings import settings

# Base class for evals_db ORM models
EvalsBase = declarative_base()

# Global engine and session maker for evals_db
_evals_engine: Optional[AsyncEngine] = None
_evals_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_evals_engine() -> AsyncEngine:
    """Get or create the async database engine for evals_db."""
    global _evals_engine
    if _evals_engine is None:
        _evals_engine = create_async_engine(
            settings.evals_database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            pool_size=3,
            max_overflow=5,
            pool_recycle=1800,  # Recycle connections every 30 minutes
            pool_timeout=10,    # Fail fast if no connection available
            connect_args={
                "server_settings": {
                    "tcp_keepalives_idle": "60",      # Start keepalive after 60s idle
                    "tcp_keepalives_interval": "10",  # Send keepalive every 10s
                    "tcp_keepalives_count": "3",      # Fail after 3 missed keepalives
                }
            },
        )
    return _evals_engine


def get_evals_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session maker for evals_db."""
    global _evals_async_session_maker
    if _evals_async_session_maker is None:
        _evals_async_session_maker = async_sessionmaker(
            bind=get_evals_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _evals_async_session_maker


async def get_evals_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting async evals_db sessions.

    Usage:
        @router.get("/endpoint")
        async def endpoint(session: AsyncSession = Depends(get_evals_session)):
            # Use session here
            pass
    """
    session_maker = get_evals_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_evals_db() -> None:
    """
    Initialize evals database connection.
    Should be called on application startup.
    """
    get_evals_engine()


async def close_evals_db() -> None:
    """
    Close evals database connections.
    Should be called on application shutdown.
    """
    global _evals_engine, _evals_async_session_maker

    if _evals_engine is not None:
        await _evals_engine.dispose()
        _evals_engine = None

    _evals_async_session_maker = None
