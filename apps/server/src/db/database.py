"""
Database connection and session management for PostgreSQL.

Provides SQLAlchemy engine, session factory, and dependency injection
for FastAPI endpoints.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.db.config import get_db_settings
from src.utils.logger import logger


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def get_database_url(async_driver: bool = False) -> str:
    """
    Construct database URL from settings.

    Args:
        async_driver: If True, use asyncpg driver for async connections.
                     If False, use psycopg2 for sync connections.

    Returns:
        Database connection URL
    """
    settings = get_db_settings()
    return settings.get_async_url() if async_driver else settings.get_sync_url()


# Lazy-loaded engines and session factories
_async_engine = None
_async_session_local = None
_sync_engine = None
_sync_session_local = None


def get_async_engine():
    """Get or create the async database engine."""
    global _async_engine
    if _async_engine is None:
        settings = get_db_settings()
        _async_engine = create_async_engine(
            settings.get_async_url(),
            echo=settings.echo,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
        )
    return _async_engine


def get_async_session_local():
    """Get or create the async session factory."""
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_local


def get_sync_engine():
    """Get or create the sync database engine (for Alembic migrations)."""
    global _sync_engine
    if _sync_engine is None:
        settings = get_db_settings()
        _sync_engine = create_engine(
            settings.get_sync_url(),
            echo=settings.echo,
            pool_pre_ping=True,
        )
    return _sync_engine


def get_sync_session_local():
    """Get or create the sync session factory (for migrations)."""
    global _sync_session_local
    if _sync_session_local is None:
        _sync_session_local = sessionmaker(
            bind=get_sync_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _sync_session_local


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Yields:
        AsyncSession: Database session for use in endpoints

    Example:
        ```python
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
        ```
    """
    session_local = get_async_session_local()
    async with session_local() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_db() -> Session:
    """
    Get a synchronous database session (for use in non-async contexts).

    Returns:
        Session: Sync database session

    Note:
        Caller is responsible for closing the session.
    """
    session_local = get_sync_session_local()
    return session_local()


async def init_db() -> None:
    """
    Initialize database by creating all tables.

    Note:
        In production, use Alembic migrations instead.
        This is useful for testing or initial setup.
    """
    logger.info("Initializing database tables...")
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully")


async def close_db() -> None:
    """
    Close database connections and dispose of engine.

    Call this on application shutdown.
    """
    logger.info("Closing database connections...")
    engine = get_async_engine()
    await engine.dispose()
    logger.info("Database connections closed")
