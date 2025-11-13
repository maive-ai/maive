"""
Mock CRM provider implementation for demos and local development.

This provider uses in-memory data and requires no external dependencies,
making it perfect for local development, demos, and testing.
"""

import random
import uuid
from datetime import UTC, datetime

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.constants import Status
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.providers.mock.data import get_mock_projects, parse_raw_project_data
from src.integrations.crm.providers.mock.schemas import MockProject
from src.integrations.crm.schemas import (
    Contact,
    ContactList,
    Job,
    JobList,
    Note,
    Project,
    ProjectList,
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
            "MockProvider initialized with mock projects",
            project_count=len(self._projects),
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
        logger.info("Getting mock job", job_id=job_id)

        # Find project by ID
        project = next(
            (p for p in self._projects if p.provider_data.get("id") == job_id), None
        )

        if not project:
            logger.warning("Mock job not found", job_id=job_id)
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Job with ID {job_id} not found",
            )

        logger.info("[Mock] Returning job", job_id=job_id, status=project.status)

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
            filters: Optional dictionary of filters:
                - customer_name: str - Partial match on customer name (case-insensitive)
                - job_id: str - Exact match on job ID
                - address: str - Partial match on address
                - claim_number: str - Exact match on claim number
                - status: str - Exact match on status
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            JobList: Paginated list of jobs
        """
        logger.info(
            "Getting all mock jobs",
            total_projects=len(self._projects),
            filters=filters,
        )

        # Convert all projects to Job schema
        jobs = [self._transform_project_to_job(project) for project in self._projects]

        # Apply client-side filtering if provided
        if filters:
            filtered_jobs = []
            for job in jobs:
                # Customer name filter (partial, case-insensitive)
                if "customer_name" in filters:
                    if filters["customer_name"].lower() not in (job.customer_name or "").lower():
                        continue
                
                # Job ID filter (exact match)
                if "job_id" in filters:
                    if job.id != filters["job_id"]:
                        continue
                
                # Address filter (partial, case-insensitive)
                if "address" in filters:
                    full_address = f"{job.address_line1 or ''} {job.city or ''} {job.state or ''} {job.postal_code or ''}"
                    if filters["address"].lower() not in full_address.lower():
                        continue
                
                # Claim number filter (exact match from provider_data)
                if "claim_number" in filters:
                    job_claim = job.provider_data.get("claimNumber") if job.provider_data else None
                    if job_claim != filters["claim_number"]:
                        continue
                
                # Status filter (exact match)
                if "status" in filters:
                    if job.status != filters["status"]:
                        continue
                
                filtered_jobs.append(job)
            
            jobs = filtered_jobs

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
        logger.info("Getting mock contact", contact_id=contact_id)

        # Find project where customer name contains this ID (simplified logic)
        project = next(
            (p for p in self._projects if p.provider_data.get("id") == contact_id), None
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
        logger.info(
            "Getting all mock contacts from projects",
            project_count=len(self._projects),
        )

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
        logger.info(
            "[MockProvider] Adding note to entity",
            entity_type=entity_type,
            entity_id=entity_id,
        )

        now = datetime.now(UTC)
        text = text.strip('"')

        # Find entity (for mock, we use projects)
        project: Project | None = None

        if entity_type in ("job", "project"):
            project = next(
                (p for p in self._projects if p.provider_data.get("id") == entity_id),
                None,
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

        # Create note object
        note = Note(
            id=str(uuid.uuid4()),
            text=text,
            entity_id=entity_id,
            entity_type=entity_type,
            created_by_id=None,
            created_by_name=None,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            is_pinned=kwargs.get("pin_to_top", False),
            provider=CRMProviderEnum.MOCK,
            provider_data={},
        )

        # Append note to project's notes list
        if project.notes is None:
            project.notes = []
        project.notes.insert(0, note)  # Insert at beginning for newest-first order

        logger.info(
            "[MockProvider] Added note to entity",
            entity_type=entity_type,
            text=text,
        )

        return note

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
        logger.info(
            "[MockProvider] Updating status for job",
            job_id=job_id,
            status=status,
        )

        # Find job
        job: Project | None = next(
            (j for j in self._projects if j.provider_data.get("id") == job_id), None
        )

        if not job:
            logger.warning("[MockProvider] Job not found", job_id=job_id)
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Job with ID {job_id} not found",
            )

        old_status = job.status
        job.status = status

        # Update claim status if provided (stored in provider_data)
        if "claim_status" in kwargs:
            old_claim_status = job.provider_data.get("claim_status")
            job.provider_data["claim_status"] = kwargs["claim_status"]
            logger.info(
                "[MockProvider] Updated job status with claim status",
                job_id=job_id,
                old_status=old_status,
                new_status=status,
                old_claim_status=old_claim_status,
                new_claim_status=kwargs["claim_status"],
            )
        else:
            logger.info(
                "[MockProvider] Updated job status",
                job_id=job_id,
                old_status=old_status,
                new_status=status,
            )

    async def get_project(self, project_id: str) -> Project:
        """
        Get a specific project by ID.

        In Mock CRM, projects and jobs are the same entity.

        Args:
            project_id: The unique identifier for the project

        Returns:
            Project: Universal project schema

        Raises:
            CRMError: If the project is not found
        """
        logger.info("Getting mock project", project_id=project_id)

        # Find project by ID
        project = next(
            (p for p in self._projects if p.provider_data.get("id") == project_id), None
        )

        if not project:
            logger.warning("Mock project not found", project_id=project_id)
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Project with ID {project_id} not found",
            )

        return project  # Already a universal Project

    async def get_all_projects(
        self,
        filters: dict | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ProjectList:
        """
        Get all projects with optional filtering and pagination.

        In Mock CRM, projects and jobs are the same entity.

        Args:
            filters: Optional dictionary of filters (not implemented for mock)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ProjectList: Paginated list of projects
        """
        logger.info("Getting all mock projects", total_count=len(self._projects))

        # Projects are already universal Project objects
        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_projects = self._projects[start_idx:end_idx]

        return ProjectList(
            projects=paginated_projects,
            total_count=len(self._projects),
            provider=CRMProviderEnum.MOCK,
            page=page,
            page_size=page_size,
            has_more=end_idx < len(self._projects),
        )

    async def update_project_status(
        self,
        project_id: str,
        status: str,
        **kwargs,
    ) -> None:
        """
        Update the status of a project.

        In Mock CRM, this has the same effect as update_job_status().

        Args:
            project_id: The unique identifier for the project
            status: The new status value
            **kwargs: Optional parameters (claim_status, etc.)

        Raises:
            CRMError: If the project is not found
        """
        logger.info(
            "[MockProvider] Updating status for project",
            project_id=project_id,
            status=status,
        )

        # Find project
        project: Project | None = next(
            (p for p in self._projects if p.provider_data.get("id") == project_id), None
        )

        if not project:
            logger.warning("[MockProvider] Project not found", project_id=project_id)
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Project with ID {project_id} not found",
            )

        old_status = project.status
        project.status = status

        # Update claim status if provided (stored in provider_data)
        if "claim_status" in kwargs:
            old_claim_status = project.provider_data.get("claim_status")
            project.provider_data["claim_status"] = kwargs["claim_status"]
            logger.info(
                "[MockProvider] Updated project status with claim status",
                project_id=project_id,
                old_status=old_status,
                new_status=status,
                old_claim_status=old_claim_status,
                new_claim_status=kwargs["claim_status"],
            )
        else:
            logger.info(
                "[MockProvider] Updated project status",
                project_id=project_id,
                old_status=old_status,
                new_status=status,
            )

    # ========================================================================
    # Helper Methods (transformation functions)
    # ========================================================================

    def _transform_project_to_job(self, project: Project) -> Job:
        """Transform internal Project model to universal Job schema."""
        # provider_data is already a dict, so we can use it directly
        provider_data = {k: v for k, v in project.provider_data.items() if k != "id"}

        customer_name = project.provider_data.get("customerName") or ""
        address = project.provider_data.get("address")
        job_id = project.provider_data.get("job_id")

        return Job(
            id=project.provider_data.get("id"),
            name=f"Job for {customer_name}",
            number=str(job_id) if job_id else None,
            status=project.status,
            status_id=None,
            workflow_type="Project",
            description=None,  # Using structured notes instead
            customer_id=project.provider_data.get(
                "id"
            ),  # Use project ID as customer ID
            customer_name=customer_name,
            address_line1=address.split(",")[0] if address else None,
            address_line2=None,
            city=address.split(",")[1].strip() if "," in (address or "") else None,
            state=address.split(",")[2].strip().split()[0]
            if len((address or "").split(",")) > 2
            else None,
            postal_code=address.split(",")[2].strip().split()[1]
            if len((address or "").split(",")) > 2
            and len(address.split(",")[2].strip().split()) > 1
            else None,
            country="USA",
            created_at=project.updated_at,
            updated_at=project.updated_at,
            completed_at=None,
            sales_rep_id=None,
            sales_rep_name=None,
            provider=CRMProviderEnum.MOCK,
            provider_data=provider_data,
            notes=project.notes,  # Include notes from project
        )

    def _transform_project_to_contact(self, project: Project) -> Contact:
        """Transform internal Project model to universal Contact schema."""
        # Split customer name into first/last
        customer_name = project.provider_data.get("customerName") or ""
        name_parts = customer_name.split(" ", 1)
        address = project.provider_data.get("address")

        return Contact(
            id=project.provider_data.get("id"),
            first_name=name_parts[0] if name_parts else None,
            last_name=name_parts[1] if len(name_parts) > 1 else None,
            company=None,
            display_name=customer_name,
            email=project.provider_data.get("email"),
            phone=project.provider_data.get("phone"),
            mobile_phone=project.provider_data.get("phone"),
            work_phone=None,
            address_line1=address.split(",")[0] if address else None,
            address_line2=None,
            city=address.split(",")[1].strip() if "," in (address or "") else None,
            state=address.split(",")[2].strip().split()[0]
            if len((address or "").split(",")) > 2
            else None,
            postal_code=address.split(",")[2].strip().split()[1]
            if len((address or "").split(",")) > 2
            and len(address.split(",")[2].strip().split()) > 1
            else None,
            country="USA",
            status="Active",
            workflow_type=None,
            created_at=project.updated_at,
            updated_at=project.updated_at,
            provider=CRMProviderEnum.MOCK,
            provider_data={k: v for k, v in project.provider_data.items() if k != "id"},
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
            (p for p in self._projects if p.provider_data.get("id") == project_id), None
        )

        if not project:
            logger.warning("Mock project not found", project_id=project_id)
            raise CRMError(
                error_code="NOT_FOUND",
                message=f"Project with ID {project_id} not found",
            )

        # Convert to ProjectStatusResponse with providerData excluding 'id'
        provider_data = {k: v for k, v in project.provider_data.items() if k != "id"}

        logger.info(
            "[Mock] Returning project",
            project_id=project_id,
            status=project.status,
        )

        return ProjectStatusResponse(
            project_id=project.provider_data.get("id"),
            status=Status(project.status),
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
        logger.warning(
            "get_all_project_statuses() is deprecated, converting to get_all_jobs()"
        )

        # Convert all projects to ProjectStatusResponse
        project_responses = []
        for project in self._projects:
            provider_data = {
                k: v for k, v in project.provider_data.items() if k != "id"
            }
            project_responses.append(
                ProjectStatusResponse(
                    project_id=project.provider_data.get("id"),
                    status=Status(project.status),
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

    async def create_project(self, mock_project: MockProject) -> None:
        """
        Create a new demo project (Mock CRM only).

        Args:
            mock_project: The MockProject instance (id will be overridden with generated value)
        """
        # Generate random project ID and override the provided one
        project_id = str(uuid.uuid4())
        logger.info("Creating mock project with ID", project_id=project_id)

        # Create a copy with the generated project ID
        mock_project_instance = mock_project.model_copy(update={"id": project_id})

        # Generate job_id
        job_id = random.randint(1, 1000000)

        # Parse and create properly structured project using shared function
        project = parse_raw_project_data(
            mock_project_instance,
            job_id=job_id,
            timestamp=None
        )

        # Add to in-memory projects list
        self._projects.append(project)
        logger.info("Successfully created mock project", project_id=project_id)

    async def update_project(self, project_id: str, mock_project: MockProject) -> Project:
        """
        Update an existing demo project (Mock CRM only).

        Args:
            project_id: The unique identifier for the project
            mock_project: The updated MockProject data

        Returns:
            Project: The updated project

        Raises:
            CRMError: If the project is not found
        """
        logger.info("Updating mock project", project_id=project_id)

        # Get existing project (will raise CRMError if not found)
        existing_project = await self.get_project(project_id)

        # Find project index for replacement
        project_index = next(
            (i for i, p in enumerate(self._projects) if p.provider_data.get("id") == project_id),
            None,
        )

        # Merge new data with existing provider_data
        # Convert existing provider_data to dict for merging
        existing_data = existing_project.provider_data.copy()
        # Get only the fields that were provided in the update (exclude None values)
        update_data = mock_project.model_dump(by_alias=True, exclude_none=True)
        existing_data.update(update_data)

        # Create MockProject from merged data, preserving the project_id
        existing_data["id"] = project_id
        mock_project_instance = MockProject(**existing_data)

        # Get job_id from existing project
        job_id = existing_project.provider_data.get("job_id")

        # Parse and create updated project using shared function
        updated_project = parse_raw_project_data(
            mock_project_instance,
            job_id=job_id,
            timestamp=None  # Will use current time for updated_at
        )

        # Preserve created_at from original
        updated_project.created_at = existing_project.created_at

        # Replace in list (index should always exist if get_project succeeded)
        if project_index is not None:
            self._projects[project_index] = updated_project

        logger.info("Successfully updated mock project", project_id=project_id)
        return updated_project
