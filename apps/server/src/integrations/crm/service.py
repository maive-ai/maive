"""
CRM service layer for business logic.

This module provides the business logic layer for CRM operations,
sitting between the FastAPI routes and the CRM providers.
"""

from typing import Any

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.schemas import (
    Contact,
    ContactList,
    CRMErrorResponse,
    EstimateItemsResponse,
    EstimateResponse,
    Job,
    JobList,
    JobNoteResponse,
    JobResponse,
    Note,
    Project,
    ProjectList,
    ProjectNoteResponse,
    ProjectStatusListResponse,
    ProjectStatusResponse,
    ProjectData,
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

    # ========================================================================
    # Universal CRM Interface Methods
    # ========================================================================

    async def get_job(self, job_id: str) -> Job | CRMErrorResponse:
        """
        Get a specific job by ID (universal interface).

        Args:
            job_id: The job identifier (string format)

        Returns:
            Job or CRMErrorResponse: The result of the operation
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

    async def get_all_jobs(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> JobList | CRMErrorResponse:
        """
        Get all jobs with optional filtering and pagination (universal interface).

        Args:
            filters: Optional provider-specific filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            JobList or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting all jobs (page={page}, size={page_size})")
            result = await self.crm_provider.get_all_jobs(
                filters=filters,
                page=page,
                page_size=page_size,
            )
            logger.info(f"Successfully retrieved {len(result.jobs)} jobs")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting all jobs: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting all jobs: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def get_project(self, project_id: str) -> Project | CRMErrorResponse:
        """
        Get a specific project by ID (universal interface).

        Args:
            project_id: The project identifier (string format)

        Returns:
            Project or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting project: {project_id}")
            result = await self.crm_provider.get_project(project_id)
            logger.info(f"Successfully retrieved project {project_id}")
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

    async def get_all_projects(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ProjectList | CRMErrorResponse:
        """
        Get all projects with optional filtering and pagination (universal interface).

        Args:
            filters: Optional provider-specific filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ProjectList or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting all projects (page={page}, size={page_size})")
            result = await self.crm_provider.get_all_projects(
                filters=filters,
                page=page,
                page_size=page_size,
            )
            logger.info(f"Successfully retrieved {len(result.projects)} projects")
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

    async def get_contact(self, contact_id: str) -> Contact | CRMErrorResponse:
        """
        Get a specific contact by ID (universal interface).

        Args:
            contact_id: The contact identifier (string format)

        Returns:
            Contact or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting contact: {contact_id}")
            result = await self.crm_provider.get_contact(contact_id)
            logger.info(f"Successfully retrieved contact {contact_id}")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting contact {contact_id}: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting contact {contact_id}: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def get_all_contacts(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ContactList | CRMErrorResponse:
        """
        Get all contacts with optional filtering and pagination (universal interface).

        Args:
            filters: Optional provider-specific filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ContactList or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting all contacts (page={page}, size={page_size})")
            result = await self.crm_provider.get_all_contacts(
                filters=filters,
                page=page,
                page_size=page_size,
            )
            logger.info(f"Successfully retrieved {len(result.contacts)} contacts")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting all contacts: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting all contacts: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def add_note(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        **kwargs: Any,
    ) -> Note | CRMErrorResponse:
        """
        Add a note to an entity (job, contact, project, etc.) (universal interface).

        Args:
            entity_id: The entity identifier
            entity_type: The type of entity (e.g., "job", "contact", "project")
            text: The text content of the note
            **kwargs: Provider-specific optional parameters (e.g., pin_to_top)

        Returns:
            Note or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Adding note to {entity_type} {entity_id}")
            result = await self.crm_provider.add_note(
                entity_id=entity_id,
                entity_type=entity_type,
                text=text,
                **kwargs,
            )
            logger.info(f"Successfully added note to {entity_type} {entity_id}")
            return result
        except CRMError as e:
            logger.error(f"CRM error adding note to {entity_type} {entity_id}: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error adding note to {entity_type} {entity_id}: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs: Any,
    ) -> None | CRMErrorResponse:
        """
        Update the status of a job (universal interface).

        Args:
            job_id: The job identifier
            status: The new status value
            **kwargs: Provider-specific optional parameters

        Returns:
            None on success, CRMErrorResponse on error
        """
        try:
            logger.info(f"Updating status for job {job_id} to {status}")
            await self.crm_provider.update_job_status(
                job_id=job_id,
                status=status,
                **kwargs,
            )
            logger.info(f"Successfully updated status for job {job_id}")
            return None
        except CRMError as e:
            logger.error(f"CRM error updating job {job_id} status: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error updating job {job_id} status: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def update_project_status(
        self,
        project_id: str,
        status: str,
        **kwargs: Any,
    ) -> None | CRMErrorResponse:
        """
        Update the status of a project (universal interface).

        Args:
            project_id: The project identifier
            status: The new status value
            **kwargs: Provider-specific optional parameters

        Returns:
            None on success, CRMErrorResponse on error
        """
        try:
            logger.info(f"Updating status for project {project_id} to {status}")
            await self.crm_provider.update_project_status(
                project_id=project_id,
                status=status,
                **kwargs,
            )
            logger.info(f"Successfully updated status for project {project_id}")
            return None
        except CRMError as e:
            logger.error(f"CRM error updating project {project_id} status: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error updating project {project_id} status: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    # ========================================================================
    # Legacy Methods (for backward compatibility)
    # ========================================================================

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

    async def create_project(self, project_data: ProjectData) -> CRMErrorResponse | None:
        """
        Create a new demo project (Mock CRM only).

        Args:
            project_data: The project data to create

        Returns:
            CRMErrorResponse if error occurs, None on success
        """
        try:
            # Check if provider supports project creation
            if not hasattr(self.crm_provider, 'create_project'):
                logger.warning("CRM provider does not support project creation")
                return CRMErrorResponse(
                    error="Project creation is only supported in demo/mock mode",
                    error_code="NOT_SUPPORTED",
                    provider=getattr(self.crm_provider, 'provider_name', None)
                )

            await self.crm_provider.create_project(project_data)
            
        except CRMError as e:
            logger.error(f"CRM error creating project: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error creating project: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def get_legacy_job(self, job_id: int) -> JobResponse | CRMErrorResponse:
        """
        Get a specific job by ID (legacy method - deprecated).

        Note: This is a legacy Service Titan-specific method. Use get_job() instead.

        Args:
            job_id: The job identifier (int format, Service Titan-specific)

        Returns:
            JobResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.warning(f"get_legacy_job() is deprecated, use get_job() instead")
            logger.info(f"Getting job: {job_id}")
            # Try to call legacy method if it exists on the provider
            if hasattr(self.crm_provider, 'get_legacy_job'):
                result = await self.crm_provider.get_legacy_job(job_id)
            else:
                # Fallback to universal interface
                result = await self.crm_provider.get_job(str(job_id))
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

    async def update_project_claim_status(
        self,
        job_id: int,
        claim_status: str,
    ) -> CRMErrorResponse | None:
        """
        Update the claim status for a specific project/job.

        Args:
            job_id: The job identifier
            claim_status: The new claim status value

        Returns:
            CRMErrorResponse if error occurs, None on success
        """
        try:
            logger.info(f"Updating claim status for job {job_id} to {claim_status}")
            await self.crm_provider.update_project_claim_status(job_id, claim_status)
            logger.info(f"Successfully updated claim status for job {job_id}")
            return None
        except CRMError as e:
            logger.error(f"CRM error updating claim status for job {job_id}: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error updating claim status for job {job_id}: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )