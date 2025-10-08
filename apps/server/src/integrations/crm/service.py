"""
CRM service layer for business logic.

This module provides the business logic layer for CRM operations,
sitting between the FastAPI routes and the CRM providers.
"""

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.schemas import (
    CRMErrorResponse,
    EstimateItemsResponse,
    EstimateResponse,
    JobNoteResponse,
    JobResponse,
    ProjectNoteResponse,
    ProjectStatusListResponse,
    ProjectStatusResponse,
)
from src.utils.logger import logger


class CRMService:
    """Service class for CRM operations."""

    def __init__(self, crm_provider: CRMProvider):
        """
        Initialize the CRM service.

        Args:
            crm_provider: The CRM provider to use
        """
        self.crm_provider = crm_provider

    async def get_project_status(self, project_id: str) -> ProjectStatusResponse | CRMErrorResponse:
        """
        Get the status of a specific project.

        Args:
            project_id: The project identifier

        Returns:
            ProjectStatusResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting status for project: {project_id}")
            result = await self.crm_provider.get_project_status(project_id)
            logger.info(f"Successfully retrieved status for project {project_id}: {result.status}")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting project {project_id}: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting project {project_id}: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def get_all_project_statuses(self) -> ProjectStatusListResponse | CRMErrorResponse:
        """
        Get the status of all projects.

        Returns:
            ProjectStatusListResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Getting status for all projects")
            result = await self.crm_provider.get_all_project_statuses()
            logger.info(f"Successfully retrieved status for {result.total_count} projects")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting all projects: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting all projects: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def get_job(self, job_id: int) -> JobResponse | CRMErrorResponse:
        """
        Get a specific job by ID.

        Args:
            job_id: The job identifier

        Returns:
            JobResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting job: {job_id}")
            result = await self.crm_provider.get_job(job_id)
            logger.info(f"Successfully retrieved job {job_id}")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting job {job_id}: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting job {job_id}: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def get_estimate(self, estimate_id: int) -> EstimateResponse | CRMErrorResponse:
        """
        Get a specific estimate by ID.

        Args:
            estimate_id: The estimate identifier

        Returns:
            EstimateResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting estimate: {estimate_id}")
            result = await self.crm_provider.get_estimate(estimate_id)
            logger.info(f"Successfully retrieved estimate {estimate_id}")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting estimate {estimate_id}: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting estimate {estimate_id}: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def get_estimate_items(
        self,
        estimate_id: int | None = None,
        ids: str | None = None,
        active: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> EstimateItemsResponse | CRMErrorResponse:
        """
        Get estimate items with optional filters.

        Args:
            estimate_id: Optional estimate ID to filter items
            ids: Optional comma-separated string of item IDs
            active: Optional active status filter
            page: Optional page number
            page_size: Optional page size

        Returns:
            EstimateItemsResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting estimate items for estimate_id: {estimate_id}")
            result = await self.crm_provider.get_estimate_items(
                estimate_id=estimate_id,
                ids=ids,
                active=active,
                page=page,
                page_size=page_size,
            )
            logger.info(f"Successfully retrieved {len(result.items)} estimate items")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting estimate items: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting estimate items: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def add_job_note(
        self,
        job_id: int,
        text: str,
        pin_to_top: bool | None = None,
    ) -> JobNoteResponse | CRMErrorResponse:
        """
        Add a note to a specific job.

        Args:
            job_id: The job identifier
            text: The text content of the note
            pin_to_top: Whether to pin the note to the top (optional)

        Returns:
            JobNoteResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Adding note to job {job_id}")
            result = await self.crm_provider.add_job_note(job_id, text, pin_to_top)
            logger.info(f"Successfully added note to job {job_id}")
            return result
        except CRMError as e:
            logger.error(f"CRM error adding note to job {job_id}: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error adding note to job {job_id}: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def add_project_note(
        self,
        project_id: int,
        text: str,
        pin_to_top: bool | None = None,
    ) -> ProjectNoteResponse | CRMErrorResponse:
        """
        Add a note to a specific project.

        Args:
            project_id: The project identifier
            text: The text content of the note
            pin_to_top: Whether to pin the note to the top (optional)

        Returns:
            ProjectNoteResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Adding note to project {project_id}")
            result = await self.crm_provider.add_project_note(project_id, text, pin_to_top)
            logger.info(f"Successfully added note to project {project_id}")
            return result
        except CRMError as e:
            logger.error(f"CRM error adding note to project {project_id}: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error adding note to project {project_id}: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )