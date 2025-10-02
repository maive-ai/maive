"""
Abstract base classes for CRM providers.

This module defines the abstract interface that all CRM providers
must implement, ensuring consistent behavior across different CRM systems.
"""

from abc import ABC, abstractmethod

from src.integrations.crm.provider_schemas import FormSubmissionListResponse
from src.integrations.crm.schemas import (
    EstimateResponse,
    JobNoteResponse,
    JobResponse,
    ProjectStatusListResponse,
    ProjectStatusResponse,
)


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
    async def get_appointment_status(
        self, appointment_id: str
    ) -> ProjectStatusResponse:
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
    async def get_all_form_submissions(
        self,
        form_ids: list[int],
        status: str | None = None,
        owners: list[dict] | None = None,
    ) -> FormSubmissionListResponse:
        """
        Get all form submissions for a specific form.

        Args:
            form_ids: List of form IDs to get submissions for
            status: Optional form status to filter by (Started, Completed, Any)
            owners: Optional list of owner objects with type and id

        Returns:
            FormSubmissionListResponse: List of all form submissions

        Raises:
            CRMError: If an error occurs while fetching form submissions
        """
        pass

    @abstractmethod
    async def get_job(self, job_id: int) -> JobResponse:
        """
        Get a specific job by ID.

        Args:
            job_id: The unique identifier for the job

        Returns:
            JobResponse: The job information

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        pass

    @abstractmethod
    async def get_estimate(self, estimate_id: int) -> EstimateResponse:
        """
        Get a specific estimate by ID.

        Args:
            estimate_id: The unique identifier for the estimate

        Returns:
            EstimateResponse: The estimate information

        Raises:
            CRMError: If the estimate is not found or an error occurs
        """
        pass

    @abstractmethod
    async def add_job_note(self, job_id: int, text: str, pin_to_top: bool | None = None) -> JobNoteResponse:
        """
        Add a note to a specific job.

        Args:
            job_id: The unique identifier for the job
            text: The text content of the note
            pin_to_top: Whether to pin the note to the top (optional)

        Returns:
            JobNoteResponse: The created note information

        Raises:
            CRMError: If the job is not found or an error occurs
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
