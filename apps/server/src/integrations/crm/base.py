"""
Abstract base classes for CRM providers.

This module defines the abstract interface that all CRM providers
must implement, ensuring consistent behavior across different CRM systems.
"""

from abc import ABC, abstractmethod

from src.integrations.crm.schemas import ProjectStatusListResponse, ProjectStatusResponse


class CRMProvider(ABC):
    """Abstract interface for CRM providers."""

    @abstractmethod
    async def get_project_status(self, project_id: str) -> ProjectStatusResponse:
        """
        Get the status of a specific project by ID.

        Args:
            project_id: The unique identifier for the project

        Returns:
            ProjectStatusResponse: The project status information

        Raises:
            CRMError: If the project is not found or an error occurs
        """
        pass

    @abstractmethod
    async def get_all_project_statuses(self) -> ProjectStatusListResponse:
        """
        Get the status of all projects.

        Returns:
            ProjectStatusListResponse: List of all project statuses

        Raises:
            CRMError: If an error occurs while fetching project statuses
        """
        pass

    @abstractmethod
    async def get_appointment_status(self, appointment_id: str) -> ProjectStatusResponse:
        """
        Get the status of a specific appointment by ID.

        Args:
            appointment_id: The unique identifier for the appointment

        Returns:
            ProjectStatusResponse: The appointment status information

        Raises:
            CRMError: If the appointment is not found or an error occurs
        """
        pass

    @abstractmethod
    async def get_all_appointment_statuses(self) -> ProjectStatusListResponse:
        """
        Get the status of all appointments.

        Returns:
            ProjectStatusListResponse: List of all appointment statuses

        Raises:
            CRMError: If an error occurs while fetching appointment statuses
        """
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> ProjectStatusResponse:
        """
        Get the status of a specific job by ID.

        Args:
            job_id: The unique identifier for the job

        Returns:
            ProjectStatusResponse: The job status information

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        pass

    @abstractmethod
    async def get_all_job_statuses(self) -> ProjectStatusListResponse:
        """
        Get the status of all jobs.

        Returns:
            ProjectStatusListResponse: List of all job statuses

        Raises:
            CRMError: If an error occurs while fetching job statuses
        """
        pass


class CRMError(Exception):
    """Base exception for CRM-related errors."""

    def __init__(self, message: str, error_code: str | None = None):
        """
        Initialize CRM error.

        Args:
            message: Error message
            error_code: Optional provider-specific error code
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code