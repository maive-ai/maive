"""
CRM service layer for business logic.

This module provides the business logic layer for CRM operations using
the universal interface that works across all CRM providers.
"""

from typing import Any

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.schemas import (
    Contact,
    ContactList,
    CRMErrorResponse,
    Job,
    JobList,
    Note,
    Project,
    ProjectList,
)
from src.utils.logger import logger


class CRMService:
    """Service class for CRM operations using the universal interface."""

    def __init__(self, crm_provider: CRMProvider):
        """
        Initialize the CRM service.

        Args:
            crm_provider: The CRM provider to use
        """
        self.crm_provider = crm_provider

    # ========================================================================
    # Job Methods
    # ========================================================================

    async def get_job(self, job_id: str) -> Job | CRMErrorResponse:
        """
        Get a specific job by ID.

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
        Get all jobs with optional filtering and pagination.

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

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs: Any,
    ) -> None | CRMErrorResponse:
        """
        Update the status of a job.

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

    # ========================================================================
    # Project Methods
    # ========================================================================

    async def get_project(self, project_id: str) -> Project | CRMErrorResponse:
        """
        Get a specific project by ID.

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
        Get all projects with optional filtering and pagination.

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

    async def update_project_status(
        self,
        project_id: str,
        status: str,
        **kwargs: Any,
    ) -> None | CRMErrorResponse:
        """
        Update the status of a project.

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
    # Contact Methods
    # ========================================================================

    async def get_contact(self, contact_id: str) -> Contact | CRMErrorResponse:
        """
        Get a specific contact by ID.

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
        Get all contacts with optional filtering and pagination.

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

    # ========================================================================
    # Note Methods
    # ========================================================================

    async def add_note(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        **kwargs: Any,
    ) -> Note | CRMErrorResponse:
        """
        Add a note to an entity (job, contact, project, etc.).

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
