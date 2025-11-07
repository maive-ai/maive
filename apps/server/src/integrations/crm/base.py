"""
Abstract base classes for CRM providers.

This module defines the abstract interface that all CRM providers
must implement, ensuring consistent behavior across different CRM systems.

The interface is designed around universal CRM primitives (jobs, contacts, notes)
that work across all providers, with provider-specific data stored in the
provider_data field of each universal schema.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.integrations.crm.schemas import Contact, ContactList, Job, JobList, Note, Project, ProjectList


class CRMProvider(ABC):
    """
    Universal abstract interface for CRM providers.

    All CRM providers must implement these 6 core methods that work with
    universal schemas. Providers can add additional provider-specific methods
    as regular (non-abstract) instance methods.
    """

    @abstractmethod
    async def get_job(self, job_id: str) -> Job:
        """
        Get a specific job by ID.

        Args:
            job_id: The unique identifier for the job (provider-specific format)

        Returns:
            Job: Universal job schema with provider-specific data in provider_data

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        pass

    @abstractmethod
    async def get_all_jobs(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> JobList:
        """
        Get all jobs with optional filtering and pagination.

        Args:
            filters: Optional dictionary of provider-specific filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            JobList: Paginated list of jobs in universal schema

        Raises:
            CRMError: If an error occurs while fetching jobs
        """
        pass

    @abstractmethod
    async def get_contact(self, contact_id: str) -> Contact:
        """
        Get a specific contact/customer by ID.

        Args:
            contact_id: The unique identifier for the contact (provider-specific format)

        Returns:
            Contact: Universal contact schema with provider-specific data

        Raises:
            CRMError: If the contact is not found or an error occurs
            CRMError: If the provider doesn't support contacts as separate entities
        """
        pass

    @abstractmethod
    async def get_all_contacts(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ContactList:
        """
        Get all contacts with optional filtering and pagination.

        Args:
            filters: Optional dictionary of provider-specific filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ContactList: Paginated list of contacts in universal schema

        Raises:
            CRMError: If an error occurs while fetching contacts
            CRMError: If the provider doesn't support contacts as separate entities
        """
        pass

    @abstractmethod
    async def add_note(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        **kwargs: Any,
    ) -> Note:
        """
        Add a note/activity to an entity (job, contact, project, etc.).

        Args:
            entity_id: The ID of the entity to add the note to
            entity_type: The type of entity (e.g., "job", "contact", "project")
            text: The text content of the note
            **kwargs: Provider-specific optional parameters (e.g., pin_to_top, private, etc.)

        Returns:
            Note: Universal note schema with provider-specific metadata

        Raises:
            CRMError: If the entity is not found or an error occurs
        """
        pass

    @abstractmethod
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs: Any,
    ) -> None:
        """
        Update the status of a job.

        Args:
            job_id: The unique identifier for the job
            status: The new status value (provider-specific format)
            **kwargs: Provider-specific optional parameters (e.g., sub_status, reason, etc.)

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        pass

    @abstractmethod
    async def get_project(self, project_id: str) -> Project:
        """
        Get a specific project by ID.

        In hierarchical CRMs (Service Titan), projects are top-level containers
        that may contain multiple jobs. In flat CRMs (JobNimbus), this returns
        the same entity as get_job().

        Args:
            project_id: The unique identifier for the project (provider-specific format)

        Returns:
            Project: Universal project schema with provider-specific data in provider_data

        Raises:
            CRMError: If the project is not found or an error occurs
        """
        pass

    @abstractmethod
    async def get_all_projects(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ProjectList:
        """
        Get all projects with optional filtering and pagination.

        In flat CRMs (JobNimbus), this returns the same data as get_all_jobs().

        Args:
            filters: Optional dictionary of provider-specific filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ProjectList: Paginated list of projects in universal schema

        Raises:
            CRMError: If an error occurs while fetching projects
        """
        pass

    @abstractmethod
    async def update_project_status(
        self,
        project_id: str,
        status: str,
        **kwargs: Any,
    ) -> None:
        """
        Update the status of a project.

        In flat CRMs (JobNimbus), this has the same effect as update_job_status().

        Args:
            project_id: The unique identifier for the project
            status: The new status value (provider-specific format)
            **kwargs: Provider-specific optional parameters (e.g., sub_status, reason, etc.)

        Raises:
            CRMError: If the project is not found or an error occurs
        """
        pass

    # Optional provider-specific methods
    # These are not abstract and have default implementations that raise CRMError

    async def get_job_files(self, job_id: str) -> list[Any]:
        """
        Get all files attached to a specific job.

        This is an optional method that not all providers support.
        Providers that support file attachments should override this method.

        Args:
            job_id: The job ID to get files for

        Returns:
            List of file metadata objects

        Raises:
            CRMError: If the provider doesn't support file operations
        """
        raise CRMError(
            "This CRM provider does not support file operations",
            "NOT_SUPPORTED"
        )

    async def download_file(
        self, 
        file_id: str, 
        filename: str | None = None, 
        content_type: str | None = None
    ) -> tuple[bytes, str, str]:
        """
        Download a file's content.

        This is an optional method that not all providers support.
        Providers that support file attachments should override this method.

        Args:
            file_id: The file ID to download
            filename: Optional filename hint
            content_type: Optional content type hint

        Returns:
            Tuple of (file_content, filename, content_type)

        Raises:
            CRMError: If the provider doesn't support file operations
        """
        raise CRMError(
            "This CRM provider does not support file operations",
            "NOT_SUPPORTED"
        )


class CRMError(Exception):
    """Base exception for CRM-related errors."""

    def __init__(self, message: str, error_code: str | None = None):
        """
        Initialize CRM error.

        Args:
            message: Error message
            error_code: Optional provider-specific error code (e.g., "NOT_FOUND", "NOT_SUPPORTED", "UNAUTHORIZED")
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
