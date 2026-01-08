"""Database configuration and session management for users_db."""

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

# Base class for users_db ORM models
UsersBase = declarative_base()

# Global engine and session maker for users_db
_users_engine: Optional[AsyncEngine] = None
_users_async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_users_engine() -> AsyncEngine:
    """Get or create the async database engine for users_db."""
    global _users_engine
    if _users_engine is None:
        _users_engine = create_async_engine(
            settings.users_database_url,
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
    return _users_engine


def get_users_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session maker for users_db."""
    global _users_async_session_maker
    if _users_async_session_maker is None:
        _users_async_session_maker = async_sessionmaker(
            bind=get_users_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _users_async_session_maker


async def get_users_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting async users_db sessions.

    Usage:
        @router.get("/endpoint")
        async def endpoint(session: AsyncSession = Depends(get_users_session)):
            # Use session here
            pass
    """
    session_maker = get_users_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_users_db() -> None:
    """
    Initialize users database connection.
    Should be called on application startup.
    """
    get_users_engine()


async def close_users_db() -> None:
    """
    Close users database connections.
    Should be called on application shutdown.
    """
    global _users_engine, _users_async_session_maker

    if _users_engine is not None:
        await _users_engine.dispose()
        _users_engine = None

    _users_async_session_maker = None
