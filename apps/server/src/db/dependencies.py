"""
FastAPI dependencies for database services.

Provides dependency injection for database-related services.
"""

from functools import lru_cache

from src.db.call_state_service import CallStateService


@lru_cache(maxsize=1)
def get_call_state_service() -> CallStateService:
    """
    FastAPI dependency for getting the call state service.

    Returns a singleton instance of CallStateService.

    Returns:
        CallStateService: The call state service instance
    """
    return CallStateService()
