"""
Mock CRM provider implementation for demos and local development.

This provider uses in-memory data and requires no external dependencies,
making it perfect for local development, demos, and testing.
"""

import random
import uuid
from datetime import UTC, datetime

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.constants import ClaimStatus
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.constants import Status
from src.integrations.crm.provider_schemas import FormSubmissionListResponse
from src.integrations.crm.providers.mock_data import (
    Project,
    ProjectData,
    get_mock_projects,
)
from src.integrations.crm.schemas import (
    EquipmentListResponse,
    EstimateResponse,
    JobNoteResponse,
    JobResponse,
    MaterialsListResponse,
    PricebookItemsRequest,
    ProjectStatusListResponse,
    ProjectStatusResponse,
    ServicesListResponse,
)
from src.utils.logger import logger


class MockCRMProvider(CRMProvider):
    """Mock CRM implementation using in-memory data."""

    def __init__(self):
        """Initialize the Mock CRM provider with in-memory data."""
        self._projects: list[Project] = get_mock_projects()
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

        logger.info(
            f"[MockCRM] Returning project {project_id} - "
            f"Status: {project.status}, Claim Status: {project.claim_status}"
        )

        return ProjectStatusResponse(
            project_id=project.project_data.id,
            status=Status(project.status),
            claim_status=ClaimStatus(project.claim_status),
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
        project_responses = []
        for project in self._projects:
            provider_data = project.project_data.model_dump(exclude={"id"}, mode="json")
            logger.debug(
                f"[MockCRM] Project {project.project_data.id} - "
                f"Status: {project.status}, Claim Status: {project.claim_status}"
            )
            project_responses.append(
                ProjectStatusResponse(
                    project_id=project.project_data.id,
                    status=Status(project.status),
                    claim_status=ClaimStatus(project.claim_status),
                    provider=CRMProviderEnum.MOCK_CRM,
                    updated_at=project.updated_at,
                    provider_data=provider_data,
                )
            )

        return ProjectStatusListResponse(
            projects=project_responses,
            total_count=len(project_responses),
            provider=CRMProviderEnum.MOCK_CRM,
        )

    async def create_project(self, project_data: ProjectData) -> None:
        """
        Create a new demo project (Mock CRM only).

        Args:
            project_data: The project data (id will be overridden with generated value)
        """
        # Generate random project ID and override the provided one
        project_id = uuid.uuid4()
        logger.info(f"Creating mock project with ID: {project_id}")

        # Override id, tenant, and job_id with generated values
        project_data.id = str(project_id)
        project_data.tenant = 1
        project_data.job_id = random.randint(1, 1000000)

        # Create mock project
        now = datetime.now(UTC).isoformat()
        mock_project = Project(
            project_data=project_data,
            status=Status.IN_PROGRESS,
            updated_at=now,
        )

        # Add to in-memory projects list
        self._projects.append(mock_project)
        logger.info(f"Successfully created mock project {project_id}")

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
        """Add a note to a job."""
        logger.debug(f"[MockCRMProvider] Adding note to job {job_id}")
        
        now = datetime.now()
        text = text.strip('\"')

        # Find job by job_id (already set in mock data)
        job: Project | None = next((j for j in self._projects if j.project_data.job_id == job_id), None)
        
        if job:
            # Add note to job
            enhanced_text = f"{now.strftime('%Y-%m-%d %H:%M')}: {text}"
            job.project_data.notes = enhanced_text + "\n\n" + job.project_data.notes
            logger.debug(f"[MockCRMProvider] Added note to job: {text}")
        else:
            logger.debug(f"[MockCRMProvider] Job not found: {job_id}")

        # Return properly formatted response with all required fields
        return JobNoteResponse(
            text=text,
            is_pinned=pin_to_top or False,
            created_by_id=1,  # Mock user ID
            created_on=now,
            modified_on=now,
        )

    async def update_project_claim_status(self, job_id: int, claim_status: str) -> None:
        """
        Update the claim status for a specific project/job.

        Args:
            job_id: The unique identifier for the job
            claim_status: The new claim status value

        Raises:
            CRMError: If the job is not found
        """
        logger.debug(f"[MockCRMProvider] Updating claim status for job {job_id} to {claim_status}")

        # Find job by job_id
        job: Project | None = next((j for j in self._projects if j.project_data.job_id == job_id), None)

        if job:
            old_status = job.claim_status
            job.claim_status = claim_status
            logger.info(
                f"[MockCRMProvider] Updated claim status for job {job_id} from "
                f"{old_status} to {claim_status}"
            )
        else:
            logger.warning(f"[MockCRMProvider] Job not found: {job_id}")
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Job with ID {job_id} not found",
            )

    async def get_pricebook_materials(
        self, request: PricebookItemsRequest
    ) -> MaterialsListResponse:
        """Mock CRM does not support pricebook materials."""
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Mock CRM does not support pricebook operations",
        )

    async def get_pricebook_services(
        self, request: PricebookItemsRequest
    ) -> ServicesListResponse:
        """Mock CRM does not support pricebook services."""
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Mock CRM does not support pricebook operations",
        )

    async def get_pricebook_equipment(
        self, request: PricebookItemsRequest
    ) -> EquipmentListResponse:
        """Mock CRM does not support pricebook equipment."""
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Mock CRM does not support pricebook operations",
        )

