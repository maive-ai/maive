"""
Mock CRM provider implementation for demos and local development.

This provider uses in-memory data and requires no external dependencies,
making it perfect for local development, demos, and testing.
"""

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.constants import ProjectStatus
from src.integrations.crm.provider_schemas import FormSubmissionListResponse
from src.integrations.crm.providers.mock_data import MockProject, get_mock_projects
from src.integrations.crm.schemas import (
    EstimateResponse,
    JobNoteResponse,
    JobResponse,
    ProjectStatusListResponse,
    ProjectStatusResponse,
)
from src.utils.logger import logger


class MockCRMProvider(CRMProvider):
    """Mock CRM implementation using in-memory data."""

    def __init__(self):
        """Initialize the Mock CRM provider with in-memory data."""
        self._projects: list[MockProject] = get_mock_projects()
        logger.info(
            f"MockCRMProvider initialized with {len(self._projects)} mock projects"
        )

    async def get_project_status(self, project_id: str) -> ProjectStatusResponse:
        """
        Get the status of a specific project by ID.

        Args:
            project_id: The unique identifier for the project

        Returns:
            ProjectStatusResponse: The project status information

        Raises:
            CRMError: If the project is not found
        """
        logger.info(f"Getting mock project status for: {project_id}")

        # Find project by ID
        project = next(
            (p for p in self._projects if p.project_data.id == project_id), None
        )

        if not project:
            logger.warning(f"Mock project not found: {project_id}")
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Project with ID {project_id} not found",
            )

        # Convert to ProjectStatusResponse with providerData excluding 'id'
        provider_data = project.project_data.model_dump(exclude={"id"}, mode="json")

        return ProjectStatusResponse(
            project_id=project.project_data.id,
            status=ProjectStatus(project.status),
            provider=CRMProviderEnum.MOCK_CRM,
            updated_at=project.updated_at,
            provider_data=provider_data,
        )

    async def get_all_project_statuses(self) -> ProjectStatusListResponse:
        """
        Get the status of all projects.

        Returns:
            ProjectStatusListResponse: List of all project statuses
        """
        logger.info(f"Getting all mock project statuses ({len(self._projects)} total)")

        # Convert all projects to ProjectStatusResponse
        project_responses = [
            ProjectStatusResponse(
                project_id=project.project_data.id,
                status=ProjectStatus(project.status),
                provider=CRMProviderEnum.MOCK_CRM,
                updated_at=project.updated_at,
                provider_data=project.project_data.model_dump(exclude={"id"}, mode="json"),
            )
            for project in self._projects
        ]

        return ProjectStatusListResponse(
            projects=project_responses,
            total_count=len(project_responses),
            provider=CRMProviderEnum.MOCK_CRM,
        )

    # Stub implementations for unsupported operations

    async def get_appointment_status(
        self, appointment_id: str
    ) -> ProjectStatusResponse:
        """Mock CRM does not support appointments."""
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Mock CRM does not support appointment operations",
        )

    async def get_all_appointment_statuses(self) -> ProjectStatusListResponse:
        """Mock CRM does not support appointments."""
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Mock CRM does not support appointment operations",
        )

    async def get_all_form_submissions(
        self,
        form_ids: list[int],
        status: str | None = None,
        owners: list[dict] | None = None,
    ) -> FormSubmissionListResponse:
        """Mock CRM does not support form submissions."""
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Mock CRM does not support form submission operations",
        )

    async def get_job(self, job_id: int) -> JobResponse:
        """Mock CRM does not support jobs."""
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Mock CRM does not support job operations",
        )

    async def get_estimate(self, estimate_id: int) -> EstimateResponse:
        """Mock CRM does not support estimates."""
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Mock CRM does not support estimate operations",
        )

    async def add_job_note(
        self, job_id: int, text: str, pin_to_top: bool | None = None
    ) -> JobNoteResponse:
        """Mock CRM does not support job notes."""
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Mock CRM does not support job note operations",
        )

