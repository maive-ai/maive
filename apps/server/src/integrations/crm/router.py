"""
CRM router with project status endpoints.

This module contains all the API endpoints for CRM operations,
including project status retrieval and management.
"""

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.integrations.crm.dependencies import get_crm_service
from src.integrations.crm.schemas import CRMErrorResponse, ProjectStatusListResponse, ProjectStatusResponse
from src.integrations.crm.service import CRMService

router = APIRouter(prefix="/crm", tags=["CRM"])


@router.get("/projects/{project_id}/status", response_model=ProjectStatusResponse)
async def get_project_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> ProjectStatusResponse:
    """
    Get the status of a specific project by ID.

    Args:
        project_id: The unique identifier for the project
        crm_service: The CRM service instance from dependency injection

    Returns:
        ProjectStatusResponse: The project status information

    Raises:
        HTTPException: If the project is not found or an error occurs
    """
    result = await crm_service.get_project_status(project_id)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.error)
        else:
            raise HTTPException(status_code=500, detail=result.error)

    return result


@router.get("/projects/status", response_model=ProjectStatusListResponse)
async def get_all_project_statuses(
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> ProjectStatusListResponse:
    """
    Get the status of all projects.

    Args:
        crm_service: The CRM service instance from dependency injection

    Returns:
        ProjectStatusListResponse: List of all project statuses

    Raises:
        HTTPException: If an error occurs while fetching project statuses
    """
    result = await crm_service.get_all_project_statuses()

    if isinstance(result, CRMErrorResponse):
        raise HTTPException(status_code=500, detail=result.error)

    return result