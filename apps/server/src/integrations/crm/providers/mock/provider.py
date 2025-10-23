"""
Mock CRM provider implementation for demos and local development.

This provider uses in-memory data and requires no external dependencies,
making it perfect for local development, demos, and testing.
"""

import random
import uuid
from datetime import UTC, datetime

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.constants import ClaimStatus, Status
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.providers.mock.mock_data import (
    Project,
    ProjectData,
    get_mock_projects,
)
from src.integrations.crm.schemas import (
    Contact,
    ContactList,
    Job,
    JobList,
    Note,
    ProjectStatusListResponse,
    ProjectStatusResponse,
)
from src.utils.logger import logger


class MockProvider(CRMProvider):
    """Mock CRM implementation using in-memory data."""

    def __init__(self):
        """Initialize the Mock CRM provider with in-memory data."""
        self._projects: list[Project] = get_mock_projects()
        logger.info(
            f"MockProvider initialized with {len(self._projects)} mock projects"
        )

    # ========================================================================
    # Universal CRM Interface Implementation (required abstract methods)
    # ========================================================================

    async def get_job(self, job_id: str) -> Job:
        """
        Get a specific job by ID.

        Args:
            job_id: The unique identifier for the job

        Returns:
            Job: Universal job schema

        Raises:
            CRMError: If the job is not found
        """
        logger.info(f"Getting mock job: {job_id}")

        # Find project by ID
        project = next(
            (p for p in self._projects if p.project_data.id == job_id), None
        )

        if not project:
            logger.warning(f"Mock job not found: {job_id}")
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Job with ID {job_id} not found",
            )

        logger.info(
            f"[Mock] Returning job {job_id} - "
            f"Status: {project.status}, Claim Status: {project.claim_status}"
        )

        return self._transform_project_to_job(project)

    async def get_all_jobs(
        self,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> JobList:
        """
        Get all jobs with optional filtering and pagination.

        Args:
            filters: Optional dictionary of filters (not implemented for mock)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            JobList: Paginated list of jobs
        """
        logger.info(f"Getting all mock jobs ({len(self._projects)} total)")

        # Convert all projects to Job schema
        jobs = [self._transform_project_to_job(project) for project in self._projects]

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = jobs[start_idx:end_idx]

        return JobList(
            jobs=paginated_jobs,
            total_count=len(jobs),
            provider=CRMProviderEnum.MOCK,
            page=page,
            page_size=page_size,
            has_more=end_idx < len(jobs),
        )

    async def get_contact(self, contact_id: str) -> Contact:
        """
        Get a specific contact by ID.

        Note: Mock CRM extracts contacts from job customer data.

        Args:
            contact_id: The unique identifier for the contact

        Returns:
            Contact: Universal contact schema

        Raises:
            CRMError: If the contact is not found
        """
        logger.info(f"Getting mock contact: {contact_id}")

        # Find project where customer name contains this ID (simplified logic)
        project = next(
            (p for p in self._projects if p.project_data.id == contact_id), None
        )

        if not project:
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Contact with ID {contact_id} not found",
            )

        return self._transform_project_to_contact(project)

    async def get_all_contacts(
        self,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ContactList:
        """
        Get all contacts with optional filtering and pagination.

        Note: Mock CRM extracts contacts from job customer data.

        Args:
            filters: Optional dictionary of filters (not implemented for mock)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ContactList: Paginated list of contacts
        """
        logger.info(f"Getting all mock contacts from {len(self._projects)} projects")

        # Extract unique contacts from projects
        contacts = [
            self._transform_project_to_contact(project) for project in self._projects
        ]

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_contacts = contacts[start_idx:end_idx]

        return ContactList(
            contacts=paginated_contacts,
            total_count=len(contacts),
            provider=CRMProviderEnum.MOCK,
            page=page,
            page_size=page_size,
            has_more=end_idx < len(contacts),
        )

    async def add_note(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        **kwargs,
    ) -> Note:
        """
        Add a note to an entity (job, contact, etc.).

        Args:
            entity_id: The ID of the entity
            entity_type: The type of entity ("job", "contact", "project")
            text: The note text
            **kwargs: Optional parameters (pin_to_top, etc.)

        Returns:
            Note: Universal note schema

        Raises:
            CRMError: If the entity is not found
        """
        logger.info(f"[MockProvider] Adding note to {entity_type} {entity_id}")

        now = datetime.now(UTC)
        text = text.strip('"')

        # Find entity (for mock, we use projects)
        project: Project | None = None

        if entity_type in ("job", "project"):
            project = next(
                (p for p in self._projects if p.project_data.id == entity_id), None
            )
        else:
            raise CRMError(
                error_code="NOT_SUPPORTED",
                message=f"Mock CRM does not support notes on entity type: {entity_type}",
            )

        if not project:
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"{entity_type.title()} with ID {entity_id} not found",
            )

        # Add note to project
        enhanced_text = f"{now.strftime('%Y-%m-%d %H:%M')}: {text}"
        if project.project_data.notes:
            project.project_data.notes = enhanced_text + "\n\n" + project.project_data.notes
        else:
            project.project_data.notes = enhanced_text

        logger.info(f"[MockProvider] Added note to {entity_type}: {text}")

        return Note(
            id=str(uuid.uuid4()),
            text=text,
            entity_id=entity_id,
            entity_type=entity_type,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=None,
            provider=CRMProviderEnum.MOCK,
            provider_data={
                "pinned": kwargs.get("pin_to_top", False),
                "enhanced_text": enhanced_text,
            },
        )

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs,
    ) -> None:
        """
        Update the status of a job.

        Args:
            job_id: The unique identifier for the job
            status: The new status value
            **kwargs: Optional parameters (claim_status, etc.)

        Raises:
            CRMError: If the job is not found
        """
        logger.info(f"[MockProvider] Updating status for job {job_id} to {status}")

        # Find job
        job: Project | None = next(
            (j for j in self._projects if j.project_data.id == job_id), None
        )

        if not job:
            logger.warning(f"[MockProvider] Job not found: {job_id}")
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Job with ID {job_id} not found",
            )

        old_status = job.status
        job.status = status

        # Update claim status if provided
        if "claim_status" in kwargs:
            old_claim_status = job.claim_status
            job.claim_status = kwargs["claim_status"]
            logger.info(
                f"[MockProvider] Updated job {job_id} status from {old_status} to {status}, "
                f"claim status from {old_claim_status} to {kwargs['claim_status']}"
            )
        else:
            logger.info(
                f"[MockProvider] Updated job {job_id} status from {old_status} to {status}"
            )

    # ========================================================================
    # Helper Methods (transformation functions)
    # ========================================================================

    def _transform_project_to_job(self, project: Project) -> Job:
        """Transform internal Project model to universal Job schema."""
        provider_data = project.project_data.model_dump(exclude={"id"}, mode="json")

        # Split customer name into first/last if possible
        customer_name = project.project_data.customerName or ""
        name_parts = customer_name.split(" ", 1)

        return Job(
            id=project.project_data.id,
            name=f"Job for {customer_name}",
            number=str(project.project_data.job_id) if project.project_data.job_id else None,
            status=project.status,
            status_id=None,
            workflow_type="Project",
            description=project.project_data.notes,
            customer_id=project.project_data.id,  # Use project ID as customer ID
            customer_name=customer_name,
            address_line1=project.project_data.address.split(",")[0] if project.project_data.address else None,
            address_line2=None,
            city=project.project_data.address.split(",")[1].strip() if "," in (project.project_data.address or "") else None,
            state=project.project_data.address.split(",")[2].strip().split()[0] if len((project.project_data.address or "").split(",")) > 2 else None,
            postal_code=project.project_data.address.split(",")[2].strip().split()[1] if len((project.project_data.address or "").split(",")) > 2 and len(project.project_data.address.split(",")[2].strip().split()) > 1 else None,
            country="USA",
            created_at=project.updated_at,
            updated_at=project.updated_at,
            completed_at=None,
            sales_rep_id=None,
            sales_rep_name=None,
            provider=CRMProviderEnum.MOCK,
            provider_data=provider_data,
        )

    def _transform_project_to_contact(self, project: Project) -> Contact:
        """Transform internal Project model to universal Contact schema."""
        # Split customer name into first/last
        customer_name = project.project_data.customerName or ""
        name_parts = customer_name.split(" ", 1)

        return Contact(
            id=project.project_data.id,
            first_name=name_parts[0] if name_parts else None,
            last_name=name_parts[1] if len(name_parts) > 1 else None,
            company=None,
            display_name=customer_name,
            email=project.project_data.email,
            phone=project.project_data.phone,
            mobile_phone=project.project_data.phone,
            work_phone=None,
            address_line1=project.project_data.address.split(",")[0] if project.project_data.address else None,
            address_line2=None,
            city=project.project_data.address.split(",")[1].strip() if "," in (project.project_data.address or "") else None,
            state=project.project_data.address.split(",")[2].strip().split()[0] if len((project.project_data.address or "").split(",")) > 2 else None,
            postal_code=project.project_data.address.split(",")[2].strip().split()[1] if len((project.project_data.address or "").split(",")) > 2 and len(project.project_data.address.split(",")[2].strip().split()) > 1 else None,
            country="USA",
            status="Active",
            workflow_type=None,
            created_at=project.updated_at,
            updated_at=project.updated_at,
            provider=CRMProviderEnum.MOCK,
            provider_data=project.project_data.model_dump(exclude={"id"}, mode="json"),
        )

    # ========================================================================
    # Legacy Methods (for backward compatibility with existing code)
    # ========================================================================

    async def get_project_status(self, project_id: str) -> ProjectStatusResponse:
        """
        Legacy method: Get the status of a specific project by ID.

        Deprecated: Use get_job() instead.

        Args:
            project_id: The unique identifier for the project

        Returns:
            ProjectStatusResponse: The project status information
        """
        logger.warning("get_project_status() is deprecated, converting to get_job()")

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
            f"[Mock] Returning project {project_id} - "
            f"Status: {project.status}, Claim Status: {project.claim_status}"
        )

        return ProjectStatusResponse(
            project_id=project.project_data.id,
            status=Status(project.status),
            claim_status=ClaimStatus(project.claim_status),
            provider=CRMProviderEnum.MOCK,
            updated_at=project.updated_at,
            provider_data=provider_data,
        )

    async def get_all_project_statuses(self) -> ProjectStatusListResponse:
        """
        Legacy method: Get the status of all projects.

        Deprecated: Use get_all_jobs() instead.

        Returns:
            ProjectStatusListResponse: List of all project statuses
        """
        logger.warning("get_all_project_statuses() is deprecated, converting to get_all_jobs()")

        # Convert all projects to ProjectStatusResponse
        project_responses = []
        for project in self._projects:
            provider_data = project.project_data.model_dump(exclude={"id"}, mode="json")
            project_responses.append(
                ProjectStatusResponse(
                    project_id=project.project_data.id,
                    status=Status(project.status),
                    claim_status=ClaimStatus(project.claim_status),
                    provider=CRMProviderEnum.MOCK,
                    updated_at=project.updated_at,
                    provider_data=provider_data,
                )
            )

        return ProjectStatusListResponse(
            projects=project_responses,
            total_count=len(project_responses),
            provider=CRMProviderEnum.MOCK,
        )

    # ========================================================================
    # Other Mock-specific Methods
    # ========================================================================

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
