"""
Decorators for scheduled groups router endpoints.

This module provides reusable decorators for common patterns like error handling.
"""

from functools import wraps
from http import HTTPStatus

from fastapi import HTTPException

from src.utils.logger import logger


def handle_db_errors(operation: str):
    """
    Decorator to handle database errors consistently across endpoints.

    Catches exceptions, rolls back transactions, logs errors, and returns
    appropriate HTTP responses.

    Args:
        operation: Description of the operation for error messages (e.g., "create scheduled group")

    Returns:
        Decorator function
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
            except Exception as e:
                # Get repository and current_user from kwargs if available
                repository = kwargs.get("repository")
                current_user = kwargs.get("current_user")

                # Rollback transaction if repository is available
                if repository:
                    await repository.session.rollback()

                # Log the error with context
                logger.exception(
                    "[SCHEDULED_GROUPS] Operation failed",
                    operation=operation,
                    user_id=current_user.id if current_user else None,
                    error=str(e),
                )

                # Raise HTTP exception
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail=f"Failed to {operation}: {str(e)}",
                )

        return wrapper

    return decorator
