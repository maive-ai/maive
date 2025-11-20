"""
Rilla router with export endpoints.

This module contains all the API endpoints for Rilla operations,
including conversation, team, and user data exports.
"""

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.integrations.rilla.dependencies import get_rilla_service
from src.integrations.rilla.schemas import (
    ConversationsExportRequest,
    ConversationsExportResponse,
    TeamsExportRequest,
    TeamsExportResponse,
    UsersExportRequest,
    UsersExportResponse,
)
from src.integrations.rilla.service import RillaService

router = APIRouter(prefix="/rilla", tags=["Rilla"])


@router.post("/conversations/export", response_model=ConversationsExportResponse)
async def export_conversations(
    request: ConversationsExportRequest,
    current_user: User = Depends(get_current_user),
    rilla_service: RillaService = Depends(get_rilla_service),
) -> ConversationsExportResponse:
    """
    Export conversations from Rilla.

    Args:
        request: The conversation export request parameters
        current_user: The authenticated user
        rilla_service: The Rilla service instance from dependency injection

    Returns:
        ConversationsExportResponse: The exported conversations data

    Raises:
        HTTPException: If an error occurs during export
    """
    result = await rilla_service.export_conversations(request)

    if hasattr(result, "error") and result.error:
        raise HTTPException(status_code=500, detail=result.error)

    return result


@router.post("/teams/export", response_model=TeamsExportResponse)
async def export_teams(
    request: TeamsExportRequest,
    current_user: User = Depends(get_current_user),
    rilla_service: RillaService = Depends(get_rilla_service),
) -> TeamsExportResponse:
    """
    Export teams from Rilla.

    Args:
        request: The team export request parameters
        current_user: The authenticated user
        rilla_service: The Rilla service instance from dependency injection

    Returns:
        TeamsExportResponse: The exported teams data

    Raises:
        HTTPException: If an error occurs during export
    """
    result = await rilla_service.export_teams(request)

    if hasattr(result, "error") and result.error:
        raise HTTPException(status_code=500, detail=result.error)

    return result


@router.post("/users/export", response_model=UsersExportResponse)
async def export_users(
    request: UsersExportRequest,
    current_user: User = Depends(get_current_user),
    rilla_service: RillaService = Depends(get_rilla_service),
) -> UsersExportResponse:
    """
    Export users from Rilla.

    Args:
        request: The user export request parameters
        current_user: The authenticated user
        rilla_service: The Rilla service instance from dependency injection

    Returns:
        UsersExportResponse: The exported users data

    Raises:
        HTTPException: If an error occurs during export
    """
    result = await rilla_service.export_users(request)

    if hasattr(result, "error") and result.error:
        raise HTTPException(status_code=500, detail=result.error)

    return result
