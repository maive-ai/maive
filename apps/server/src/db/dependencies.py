"""
FastAPI dependencies for database services.

Provides dependency injection for database-related services.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.call_list.repository import CallListRepository
from src.db.calls.repository import CallRepository
from src.db.database import get_db


def get_call_repository(
    session: AsyncSession = Depends(get_db),
) -> CallRepository:
    """
    FastAPI dependency for getting the call repository.

    Args:
        session: Database session from get_db dependency

    Returns:
        CallRepository: Repository instance with injected session
    """
    return CallRepository(session)


def get_call_list_repository(
    session: AsyncSession = Depends(get_db),
) -> CallListRepository:
    """
    FastAPI dependency for getting the call list repository.

    Args:
        session: Database session from get_db dependency

    Returns:
        CallListRepository: Repository instance with injected session
    """
    return CallListRepository(session)
