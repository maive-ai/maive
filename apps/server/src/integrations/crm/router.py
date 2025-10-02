"""
CRM router with project status endpoints.

This module contains all the API endpoints for CRM operations,
including project status retrieval and management.
"""

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.integrations.crm.dependencies import get_crm_service
from src.integrations.crm.schemas import (
    AddJobNoteRequest,
    CRMErrorResponse,
    EstimateItemsResponse,
    EstimateResponse,
    JobNoteResponse,
    JobResponse,
    ProjectStatusListResponse,
    ProjectStatusResponse,
)
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


@router.get("/{tenant}/estimates/{estimate_id}", response_model=EstimateResponse)
async def get_estimate(
    tenant: int,
    estimate_id: int,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> EstimateResponse:
    """
    Get a specific estimate by ID.

    Args:
        tenant: The tenant ID
        estimate_id: The unique identifier for the estimate
        crm_service: The CRM service instance from dependency injection

    Returns:
        EstimateResponse: The estimate information

    Raises:
        HTTPException: If the estimate is not found or an error occurs
    """
    result = await crm_service.get_estimate(estimate_id)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.error)
        else:
            raise HTTPException(status_code=500, detail=result.error)

    return result


@router.get("/{tenant}/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    tenant: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> JobResponse:
    """
    Get a specific job by ID.

    Args:
        tenant: The tenant ID
        job_id: The unique identifier for the job
        crm_service: The CRM service instance from dependency injection

    Returns:
        JobResponse: The job information

    Raises:
        HTTPException: If the job is not found or an error occurs
    """
    result = await crm_service.get_job(job_id)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.error)
        else:
            raise HTTPException(status_code=500, detail=result.error)

    return result


@router.get("/{tenant}/estimates/items", response_model=EstimateItemsResponse)
async def get_estimate_items(
    tenant: int,
    estimate_id: int | None = None,
    ids: str | None = None,
    active: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> EstimateItemsResponse:
    """
    Get estimate items with optional filters.

    Args:
        tenant: The tenant ID
        estimate_id: Optional estimate ID to filter items
        ids: Optional comma-separated string of item IDs (max 50)
        active: Optional active status filter (True, False, Any)
        page: Optional page number for pagination
        page_size: Optional page size for pagination (max 50)
        crm_service: The CRM service instance from dependency injection

    Returns:
        EstimateItemsResponse: The paginated list of estimate items

    Raises:
        HTTPException: If an error occurs
    """
    result = await crm_service.get_estimate_items(
        estimate_id=estimate_id,
        ids=ids,
        active=active,
        page=page,
        page_size=page_size,
    )

    if isinstance(result, CRMErrorResponse):
        raise HTTPException(status_code=500, detail=result.error)

    return result


@router.post("/{tenant}/jobs/{job_id}/notes", response_model=JobNoteResponse)
async def add_job_note(
    tenant: int,
    job_id: int,
    text: str,
    pin_to_top: bool | None = None,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> JobNoteResponse:
    """
    Add a note to a specific job.

    Args:
        tenant: The tenant ID
        job_id: The unique identifier for the job
        text: The text content of the note
        pin_to_top: Whether to pin the note to the top (optional)
        crm_service: The CRM service instance from dependency injection

    Returns:
        JobNoteResponse: The created note information

    Raises:
        HTTPException: If the job is not found or an error occurs
    """
    result = await crm_service.add_job_note(job_id, text, pin_to_top)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(status_code=404, detail=result.error)
        else:
            raise HTTPException(status_code=500, detail=result.error)

    return result