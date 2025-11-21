"""
CRM router with universal interface endpoints.

This module contains all the API endpoints for CRM operations using
the universal interface that works across all CRM providers.
"""

from io import BytesIO

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from src.auth.dependencies import get_current_user, get_current_user_optional
from src.auth.schemas import User
from src.integrations.crm.base import CRMError
from src.integrations.crm.config import get_crm_settings
from src.integrations.crm.constants import CRMProvider
from src.integrations.crm.dependencies import get_crm_service
from src.integrations.crm.providers.mock.schemas import MockProject
from src.integrations.crm.schemas import (
    Contact,
    ContactList,
    CRMErrorResponse,
    Job,
    JobList,
    Note,
    Project,
    ProjectList,
    ProjectSummary,
)
from src.integrations.crm.service import CRMService

router = APIRouter(prefix="/crm", tags=["CRM"])


# ========================================================================
# Job Endpoints
# ========================================================================


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> Job:
    """
    Get a specific job by ID.

    This endpoint works across all CRM providers and returns a standardized Job schema.

    Args:
        job_id: The unique identifier for the job (provider-specific format)
        crm_service: The CRM service instance from dependency injection

    Returns:
        Job: The job information in universal format

    Raises:
        HTTPException: If the job is not found or an error occurs
    """
    result = await crm_service.get_job(job_id)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
            )

    return result


@router.get("/jobs", response_model=JobList)
async def get_all_jobs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(
        None,
        description="Search query to filter jobs by name, address, phone, or claim number",
    ),
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> JobList:
    """
    Get all jobs with pagination.

    This endpoint works across all CRM providers and returns a standardized JobList schema.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        search: Optional search query to filter jobs
        crm_service: The CRM service instance from dependency injection

    Returns:
        JobList: Paginated list of jobs in universal format

    Raises:
        HTTPException: If an error occurs while fetching jobs
    """
    # Convert search query to filters
    filters = None
    if search and search.strip():
        filters = {"search": search.strip()}

    result = await crm_service.get_all_jobs(
        filters=filters, page=page, page_size=page_size
    )

    if isinstance(result, CRMErrorResponse):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
        )

    return result


@router.post(
    "/jobs/{job_id}/notes", response_model=Note, status_code=status.HTTP_201_CREATED
)
async def add_job_note(
    job_id: str,
    text: str = Body(..., description="The note text content"),
    pin_to_top: bool = Body(False, description="Whether to pin the note to the top"),
    current_user: User | None = Depends(get_current_user_optional),
    crm_service: CRMService = Depends(get_crm_service),
) -> Note:
    """
    Add a note to a job.

    This endpoint works across all CRM providers and returns a standardized Note schema.

    Args:
        job_id: The unique identifier for the job
        text: The text content of the note
        pin_to_top: Whether to pin the note to the top (provider-specific, may not be supported)
        crm_service: The CRM service instance from dependency injection

    Returns:
        Note: The created note in universal format

    Raises:
        HTTPException: If the job is not found or an error occurs
    """
    result = await crm_service.add_note(
        entity_id=job_id,
        entity_type="job",
        text=text,
        pin_to_top=pin_to_top,
    )

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
            )

    return result


@router.patch("/jobs/{job_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def update_job_status(
    job_id: str,
    status_value: str = Body(
        ..., embed=True, alias="status", description="The new status value"
    ),
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> None:
    """
    Update the status of a job.

    This endpoint works across all CRM providers.

    Args:
        job_id: The unique identifier for the job
        status_value: The new status value (provider-specific format)
        crm_service: The CRM service instance from dependency injection

    Raises:
        HTTPException: If the job is not found or an error occurs
    """
    result = await crm_service.update_job_status(job_id=job_id, status=status_value)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
            )


@router.get("/jobs/{job_id}/files")
async def get_job_files(
    job_id: str,
    file_filter: str = Query(
        "all", description="Filter by type: 'all', 'images', or 'pdfs'"
    ),
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
):
    """
    Get files attached to a specific job with optional type filtering.

    This endpoint returns metadata for files/attachments associated with a job.
    Supports filtering by file type (all, images, or pdfs).

    Args:
        job_id: The unique identifier for the job
        file_filter: Filter by type - "all", "images", or "pdfs" (default: "all")
        crm_service: The CRM service instance from dependency injection

    Returns:
        List of file metadata dictionaries containing:
        - id: File identifier
        - filename: Original filename
        - content_type: MIME type
        - size: File size in bytes
        - record_type_name: Type of file (Photo, Document, etc.)
        - description: Optional file description
        - date_created: Unix timestamp of creation
        - created_by_name: Name of uploader
        - is_private: Whether file is private

    Raises:
        HTTPException: If an error occurs fetching files
    """
    try:
        return await crm_service.crm_provider.get_job_files(job_id, file_filter)
    except CRMError as e:
        status_code = (
            status.HTTP_501_NOT_IMPLEMENTED
            if e.error_code == "NOT_SUPPORTED"
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    filename: str | None = Query(None, description="Optional filename from metadata"),
    content_type: str | None = Query(
        None, description="Optional content type from metadata"
    ),
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
):
    """
    Download a specific file's content.

    This endpoint streams the file content to the client with proper headers
    for browser download.

    Args:
        file_id: The unique identifier for the file
        filename: Optional filename (recommended to provide from file list)
        content_type: Optional content type (recommended to provide from file list)
        crm_service: The CRM service instance from dependency injection

    Returns:
        StreamingResponse with file content

    Raises:
        HTTPException: If the file is not found or an error occurs
    """
    try:
        (
            file_content,
            resolved_filename,
            resolved_content_type,
        ) = await crm_service.crm_provider.download_file(
            file_id, filename, content_type
        )

        return StreamingResponse(
            BytesIO(file_content),
            media_type=resolved_content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{resolved_filename}"'
            },
        )
    except CRMError as e:
        status_code = (
            status.HTTP_501_NOT_IMPLEMENTED
            if e.error_code == "NOT_SUPPORTED"
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ========================================================================
# Project Endpoints
# ========================================================================


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> Project:
    """
    Get a specific project by ID.

    This endpoint works across all CRM providers and returns a standardized Project schema.

    Note: In flat CRMs like JobNimbus, projects and jobs are the same entity.

    Args:
        project_id: The unique identifier for the project (provider-specific format)
        crm_service: The CRM service instance from dependency injection

    Returns:
        Project: The project information in universal format

    Raises:
        HTTPException: If the project is not found or an error occurs
    """
    result = await crm_service.get_project(project_id)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
            )

    return result


@router.post("/projects/{project_id}/summary", response_model=ProjectSummary)
async def generate_project_summary(
    project_id: str,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> ProjectSummary:
    """
    Generate an AI summary for a project.

    This endpoint analyzes project notes and generates a structured summary including:
    - Brief project status summary
    - Recent actions taken (2-3 bullet points)
    - Next steps (2-3 bullet points)

    Args:
        project_id: The unique identifier for the project
        current_user: The authenticated user
        crm_service: The CRM service instance from dependency injection

    Returns:
        ProjectSummary: AI-generated structured summary

    Raises:
        HTTPException: If the project is not found or an error occurs
    """
    result = await crm_service.generate_project_summary(project_id)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
            )

    return result


@router.get("/projects", response_model=ProjectList)
async def get_all_projects(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page"),
    search: str | None = Query(
        None,
        description="Search query to filter projects by name, address, phone, or claim number",
    ),
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> ProjectList:
    """
    Get all projects with pagination.

    This endpoint works across all CRM providers and returns a standardized ProjectList schema.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        search: Optional search query to filter projects
        crm_service: The CRM service instance from dependency injection

    Returns:
        ProjectList: Paginated list of projects in universal format

    Raises:
        HTTPException: If an error occurs while fetching projects
    """
    # Convert search query to filters
    filters = None
    if search and search.strip():
        filters = {"search": search.strip()}

    result = await crm_service.get_all_projects(
        filters=filters, page=page, page_size=page_size
    )

    if isinstance(result, CRMErrorResponse):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
        )

    return result


@router.patch("/projects/{project_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def update_project_status(
    project_id: str,
    status_value: str = Body(
        ..., embed=True, alias="status", description="The new status value"
    ),
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> None:
    """
    Update the status of a project.

    This endpoint works across all CRM providers.

    Args:
        project_id: The unique identifier for the project
        status_value: The new status value (provider-specific format)
        crm_service: The CRM service instance from dependency injection

    Raises:
        HTTPException: If the project is not found or an error occurs
    """
    result = await crm_service.update_project_status(
        project_id=project_id, status=status_value
    )

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
            )


# ========================================================================
# Contact Endpoints
# ========================================================================


@router.get("/contacts/{contact_id}", response_model=Contact)
async def get_contact(
    contact_id: str,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> Contact:
    """
    Get a specific contact by ID.

    This endpoint works across all CRM providers and returns a standardized Contact schema.

    Args:
        contact_id: The unique identifier for the contact (provider-specific format)
        crm_service: The CRM service instance from dependency injection

    Returns:
        Contact: The contact information in universal format

    Raises:
        HTTPException: If the contact is not found or an error occurs
    """
    result = await crm_service.get_contact(contact_id)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result.error
            )
        elif result.error_code == "NOT_SUPPORTED":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
            )

    return result


@router.get("/contacts", response_model=ContactList)
async def get_all_contacts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Number of items per page"),
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> ContactList:
    """
    Get all contacts with pagination.

    This endpoint works across all CRM providers and returns a standardized ContactList schema.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        crm_service: The CRM service instance from dependency injection

    Returns:
        ContactList: Paginated list of contacts in universal format

    Raises:
        HTTPException: If an error occurs while fetching contacts
    """
    result = await crm_service.get_all_contacts(page=page, page_size=page_size)

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_SUPPORTED":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
            )

    return result


@router.post(
    "/contacts/{contact_id}/notes",
    response_model=Note,
    status_code=status.HTTP_201_CREATED,
)
async def add_contact_note(
    contact_id: str,
    text: str = Body(..., description="The note text content"),
    pin_to_top: bool = Body(False, description="Whether to pin the note to the top"),
    current_user: User | None = Depends(get_current_user_optional),
    crm_service: CRMService = Depends(get_crm_service),
) -> Note:
    """
    Add a note to a contact.

    This endpoint works across all CRM providers and returns a standardized Note schema.

    Args:
        contact_id: The unique identifier for the contact
        text: The text content of the note
        pin_to_top: Whether to pin the note to the top (provider-specific, may not be supported)
        crm_service: The CRM service instance from dependency injection

    Returns:
        Note: The created note in universal format

    Raises:
        HTTPException: If the contact is not found or an error occurs
    """
    result = await crm_service.add_note(
        entity_id=contact_id,
        entity_type="contact",
        text=text,
        pin_to_top=pin_to_top,
    )

    if isinstance(result, CRMErrorResponse):
        if result.error_code == "NOT_FOUND":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=result.error
            )
        elif result.error_code == "NOT_SUPPORTED":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=result.error
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result.error
            )

    return result


# ========================================================================
# Mock CRM Only Endpoints
# ========================================================================


@router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_mock_project(
    request: MockProject,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> Project:
    """
    Create a new demo project (Mock CRM only).

    This endpoint is only available when using the Mock CRM provider.
    It allows creating demo projects for testing and demonstrations.

    Args:
        request: The project data to create
        current_user: The authenticated user
        crm_service: The CRM service instance

    Returns:
        Project: The created project

    Raises:
        HTTPException: If not using Mock CRM or an error occurs
    """
    # Check if using Mock CRM
    settings = get_crm_settings()
    if settings.provider != CRMProvider.MOCK:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Project creation is only available for the Mock CRM provider",
        )

    # Create the project
    await crm_service.crm_provider.create_project(request)

    # Return the most recently created project (last in the list)
    projects_result = await crm_service.crm_provider.get_all_projects(
        page=1, page_size=1000
    )
    if not projects_result.projects:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project",
        )

    # Return the last project (most recently added)
    return projects_result.projects[-1]


@router.patch("/projects/{project_id}", response_model=Project)
async def update_mock_project(
    project_id: str,
    request: MockProject,
    current_user: User = Depends(get_current_user),
    crm_service: CRMService = Depends(get_crm_service),
) -> Project:
    """
    Update an existing demo project (Mock CRM only).

    This endpoint is only available when using the Mock CRM provider.
    It allows updating demo projects for testing and demonstrations.

    Args:
        project_id: The unique identifier for the project
        request: The updated project data
        current_user: The authenticated user
        crm_service: The CRM service instance

    Returns:
        Project: The updated project

    Raises:
        HTTPException: If not using Mock CRM or an error occurs
    """
    # Check if using Mock CRM
    settings = get_crm_settings()
    if settings.provider != CRMProvider.MOCK:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Project update is only available for the Mock CRM provider",
        )

    # Update the project
    try:
        updated_project = await crm_service.crm_provider.update_project(
            project_id, request
        )
        return updated_project
    except CRMError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
