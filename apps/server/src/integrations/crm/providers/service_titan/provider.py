"""
Service Titan CRM provider implementation.

This module implements the CRMProvider interface for Service Titan,
handling API communication and data transformation.
"""

from datetime import UTC, datetime
from typing import Any

import httpx

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.config import get_crm_settings
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.constants import Status
from src.integrations.crm.providers.service_titan.constants import ServiceTitanEndpoints
from src.integrations.crm.providers.service_titan.schemas import ServiceTitanJob
from src.integrations.crm.schemas import (
    Contact,
    ContactList,
    CRMProviderDataFactory,
    EquipmentListResponse,
    EstimateItemResponse,
    EstimateItemsRequest,
    EstimateItemsResponse,
    EstimateResponse,
    EstimatesListResponse,
    EstimatesRequest,
    FormSubmissionListResponse,
    FormSubmissionsRequest,
    Job,
    JobHoldReasonsListResponse,
    JobList,
    JobNoteResponse,
    JobResponse,
    MaterialsListResponse,
    Note,
    PricebookItemsRequest,
    Project,
    ProjectByIdRequest,
    ProjectList,
    ProjectNoteResponse,
    ProjectResponse,
    ProjectStatusListResponse,
    ProjectStatusResponse,
    ProjectSubStatusesRequest,
    ProjectSubStatusListResponse,
    ServicesListResponse,
    UpdateProjectRequest,
)
from src.utils.logger import logger


class ServiceTitanProvider(CRMProvider):
    """Service Titan implementation of the CRMProvider interface."""

    def __init__(self):
        """Initialize the Service Titan provider."""
        self.config = get_crm_settings()
        self.settings = self.config.provider_config

        # Configuration is validated in CRMSettings, so we can safely access these
        self.tenant_id = self.settings.tenant_id
        self.client_id = self.settings.client_id
        self.client_secret = self.settings.client_secret
        self.app_key = self.settings.app_key
        self.base_api_url = self.settings.base_api_url
        self.token_url = self.settings.token_url

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.request_timeout),
            headers={
                "Content-Type": "application/json",
            },
        )

        logger.info(f"ServiceTitanProvider initialized for tenant: {self.tenant_id}")
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Get OAuth access token for Service Titan API."""
        if self._access_token:
            return self._access_token

        auth_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            response = await self.client.post(
                self.token_url,
                data=auth_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            token_response = response.json()
            self._access_token = token_response["access_token"]

            logger.info("Successfully obtained Service Titan access token")
            return self._access_token

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Failed to get access token: {e.response.status_code} - {e.response.text}"
            )
            raise CRMError(
                error_code="AUTH_FAILED",
                message=f"Failed to authenticate with Service Titan: {e.response.text}",
            )
        except Exception as e:
            logger.error(f"Unexpected error getting access token: {e}")
            raise CRMError(
                error_code="AUTH_ERROR", message=f"Unexpected authentication error: {e}"
            )

    async def _make_authenticated_request(
        self, method: str, url: str, **kwargs
    ) -> httpx.Response:
        """Make an authenticated request to Service Titan API."""
        token = await self._get_access_token()

        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["ST-App-Key"] = self.app_key
        kwargs["headers"] = headers

        return await self.client.request(method, url, **kwargs)

    # ========================================================================
    # Universal CRM Interface Implementation (required abstract methods)
    # ========================================================================

    async def get_project(self, project_id: str) -> Project:
        """
        Get a specific project by ID.

        In Service Titan, projects are top-level work containers (one per customer).

        Args:
            project_id: The unique identifier for the project

        Returns:
            Project: Universal project schema

        Raises:
            CRMError: If the project is not found or an error occurs
        """
        logger.info(f"Getting Service Titan project: {project_id}")

        # Call existing Service Titan-specific method to get project
        from src.integrations.crm.schemas import ProjectByIdRequest

        project_request = ProjectByIdRequest(
            tenant=self.tenant_id, project_id=int(project_id)
        )
        st_project = await self.get_project_by_id(project_request)

        # Transform to universal Project schema
        return self._transform_st_project_to_universal_project(st_project)

    async def get_all_projects(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ProjectList:
        """
        Get all projects with optional filtering and pagination.

        Args:
            filters: Optional dictionary of filters (not yet implemented)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ProjectList: Paginated list of projects
        """
        logger.info(f"Getting all Service Titan projects (page={page}, size={page_size})")

        # Call existing get_all_project_statuses method
        project_list = await self.get_all_project_statuses()

        # Transform to universal ProjectList
        projects = []
        for project_status in project_list.projects:
            # Extract project data from provider_data
            if project_status.provider_data:
                project = Project(
                    id=project_status.project_id,
                    name=project_status.provider_data.get("name"),
                    number=project_status.provider_data.get("number"),
                    status=project_status.status.value,
                    status_id=project_status.provider_data.get("statusId"),
                    sub_status=project_status.provider_data.get("subStatus"),
                    sub_status_id=project_status.provider_data.get("subStatusId"),
                    workflow_type="Project",
                    description=None,
                    customer_id=str(project_status.provider_data.get("customerId"))
                    if project_status.provider_data.get("customerId")
                    else None,
                    customer_name=None,  # Not available in project list
                    location_id=str(project_status.provider_data.get("locationId"))
                    if project_status.provider_data.get("locationId")
                    else None,
                    address_line1=None,
                    address_line2=None,
                    city=None,
                    state=None,
                    postal_code=None,
                    country=None,
                    created_at=project_status.provider_data.get("createdOn"),
                    updated_at=project_status.updated_at.isoformat()
                    if project_status.updated_at
                    else None,
                    start_date=project_status.provider_data.get("startDate"),
                    target_completion_date=project_status.provider_data.get("targetCompletionDate"),
                    actual_completion_date=project_status.provider_data.get("actualCompletionDate"),
                    sales_rep_id=None,
                    sales_rep_name=None,
                    provider=CRMProviderEnum.SERVICE_TITAN,
                    provider_data=project_status.provider_data,
                )
                projects.append(project)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_projects = projects[start_idx:end_idx]

        return ProjectList(
            projects=paginated_projects,
            total_count=project_list.total_count,
            provider=CRMProviderEnum.SERVICE_TITAN,
            page=page,
            page_size=page_size,
            has_more=end_idx < len(projects),
        )

    async def get_job(self, job_id: str) -> Job:
        """
        Get a specific job by ID.

        In Service Titan, jobs are sub-items under projects.

        Args:
            job_id: The unique identifier for the job

        Returns:
            Job: Universal job schema

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        logger.info(f"Getting Service Titan job: {job_id}")

        # Fetch the Service Titan Job
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.JOB_BY_ID.format(tenant_id=self.tenant_id, id=int(job_id))}"

            logger.debug(f"Fetching Service Titan job {job_id}")

            response = await self._make_authenticated_request("GET", url)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Successfully fetched Service Titan job {job_id}")

            st_job = ServiceTitanJob(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(
                    f"Service Titan Job with ID {job_id} not found", "NOT_FOUND"
                )
            else:
                logger.error(f"HTTP error fetching job {job_id}: {e}")
                raise CRMError(f"Failed to fetch job: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching job {job_id}: {e}")
            raise CRMError(f"Failed to fetch job: {str(e)}", "UNKNOWN_ERROR")

        # Transform to universal Job schema
        return self._transform_st_job_to_universal(st_job)

    async def get_all_jobs(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> JobList:
        """
        Get all jobs with optional filtering and pagination.

        Note: Service Titan uses projects endpoint for jobs.

        Args:
            filters: Optional dictionary of filters (not yet implemented)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            JobList: Paginated list of jobs
        """
        logger.info(f"Getting all Service Titan jobs (page={page}, size={page_size})")

        # Call existing get_all_project_statuses method
        project_list = await self.get_all_project_statuses()

        # Transform to universal JobList
        jobs = []
        for project_status in project_list.projects:
            # Extract job data from provider_data
            if project_status.provider_data:
                job = Job(
                    id=project_status.project_id,
                    name=project_status.provider_data.get("name"),
                    number=project_status.provider_data.get("number"),
                    status=project_status.status.value,
                    status_id=project_status.provider_data.get("statusId"),
                    workflow_type="Project",
                    description=None,
                    customer_id=str(project_status.provider_data.get("customerId"))
                    if project_status.provider_data.get("customerId")
                    else None,
                    customer_name=None,  # Not available in project list
                    address_line1=None,
                    address_line2=None,
                    city=None,
                    state=None,
                    postal_code=None,
                    country=None,
                    created_at=project_status.provider_data.get("createdOn"),
                    updated_at=project_status.updated_at.isoformat()
                    if project_status.updated_at
                    else None,
                    completed_at=project_status.provider_data.get(
                        "actualCompletionDate"
                    ),
                    sales_rep_id=None,
                    sales_rep_name=None,
                    provider=CRMProviderEnum.SERVICE_TITAN,
                    provider_data=project_status.provider_data,
                )
                jobs.append(job)

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = jobs[start_idx:end_idx]

        return JobList(
            jobs=paginated_jobs,
            total_count=project_list.total_count,
            provider=CRMProviderEnum.SERVICE_TITAN,
            page=page,
            page_size=page_size,
            has_more=end_idx < len(jobs),
        )

    async def get_contact(self, contact_id: str) -> Contact:
        """
        Get a specific contact by ID.

        Note: Service Titan does not have a separate contacts/customers endpoint
        accessible via the CRM interface. Customer data is embedded in jobs/projects.

        Args:
            contact_id: The unique identifier for the contact

        Returns:
            Contact: Universal contact schema

        Raises:
            CRMError: Service Titan doesn't support standalone contacts
        """
        logger.warning("get_contact() called for Service Titan - not supported")
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Service Titan does not support fetching contacts as standalone entities. Customer data is embedded in jobs/projects.",
        )

    async def get_all_contacts(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ContactList:
        """
        Get all contacts with optional filtering and pagination.

        Note: Service Titan does not have a separate contacts endpoint.

        Raises:
            CRMError: Service Titan doesn't support standalone contacts
        """
        logger.warning("get_all_contacts() called for Service Titan - not supported")
        raise CRMError(
            error_code="NOT_SUPPORTED",
            message="Service Titan does not support fetching contacts as standalone entities. Customer data is embedded in jobs/projects.",
        )

    async def add_note(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        **kwargs: Any,
    ) -> Note:
        """
        Add a note to an entity.

        Note: For Service Titan, universal "job" entity_type maps to Service Titan projects.
        Use "st_job" entity_type for Service Titan-specific job notes.

        Args:
            entity_id: The ID of the entity
            entity_type: The type of entity ("job", "st_job", "project")
            text: The note text
            **kwargs: Optional parameters (pin_to_top, etc.)

        Returns:
            Note: Universal note schema

        Raises:
            CRMError: If the entity type is not supported or entity not found
        """
        logger.info(f"Adding note to Service Titan {entity_type} {entity_id}")

        pin_to_top = kwargs.get("pin_to_top", False)

        if entity_type == "job":
            # Universal "job" maps to Service Titan "project"
            st_note = await self.add_project_note(int(entity_id), text, pin_to_top)

            return Note(
                id=None,  # Service Titan doesn't return note ID
                text=st_note.text,
                entity_id=entity_id,
                entity_type=entity_type,
                created_at=st_note.created_on.isoformat(),
                updated_at=st_note.modified_on.isoformat()
                if st_note.modified_on
                else None,
                created_by=str(st_note.created_by_id)
                if st_note.created_by_id
                else None,
                provider=CRMProviderEnum.SERVICE_TITAN,
                provider_data={
                    "is_pinned": st_note.is_pinned,
                    "created_by_id": st_note.created_by_id,
                },
            )
        elif entity_type == "st_job":
            # Service Titan-specific: notes on Service Titan jobs (sub-items)
            st_note = await self.add_job_note(int(entity_id), text, pin_to_top)

            return Note(
                id=None,
                text=st_note.text,
                entity_id=entity_id,
                entity_type=entity_type,
                created_at=st_note.created_on.isoformat(),
                updated_at=st_note.modified_on.isoformat()
                if st_note.modified_on
                else None,
                created_by=str(st_note.created_by_id)
                if st_note.created_by_id
                else None,
                provider=CRMProviderEnum.SERVICE_TITAN,
                provider_data={
                    "is_pinned": st_note.is_pinned,
                    "created_by_id": st_note.created_by_id,
                },
            )
        elif entity_type == "project":
            # Explicitly add to Service Titan project (same as "job")
            st_note = await self.add_project_note(int(entity_id), text, pin_to_top)

            return Note(
                id=None,
                text=st_note.text,
                entity_id=entity_id,
                entity_type=entity_type,
                created_at=st_note.created_on.isoformat(),
                updated_at=st_note.modified_on.isoformat()
                if st_note.modified_on
                else None,
                created_by=str(st_note.created_by_id)
                if st_note.created_by_id
                else None,
                provider=CRMProviderEnum.SERVICE_TITAN,
                provider_data={
                    "is_pinned": st_note.is_pinned,
                    "created_by_id": st_note.created_by_id,
                },
            )
        else:
            raise CRMError(
                error_code="NOT_SUPPORTED",
                message=f"Service Titan does not support notes on entity type: {entity_type}. Use 'job', 'st_job', or 'project'.",
            )

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs: Any,
    ) -> None:
        """
        Update the status of a job.

        Note: For Service Titan, this updates the project status/substatus.

        Args:
            job_id: The unique identifier for the job (project ID)
            status: The new status value (status name or ID)
            **kwargs: Optional parameters (sub_status_id, etc.)

        Raises:
            CRMError: If the job is not found or update fails
        """
        logger.info(f"Updating Service Titan job {job_id} status to {status}")

        # For Service Titan, we need to call update_project with status_id and sub_status_id
        # The status parameter could be a status name or ID
        # For now, we'll use the sub_status_id from kwargs if provided

        sub_status_id = kwargs.get("sub_status_id")

        if not sub_status_id:
            raise CRMError(
                error_code="INVALID_REQUEST",
                message="Service Titan requires 'sub_status_id' in kwargs to update job status",
            )

        # Create update request
        from src.integrations.crm.schemas import UpdateProjectRequest

        update_req = UpdateProjectRequest(
            tenant=self.tenant_id,
            project_id=int(job_id),
            sub_status_id=sub_status_id,
        )

        # Call existing update_project method
        await self.update_project(update_req)

        logger.info(f"Successfully updated job {job_id} status")

    async def update_project_status(
        self,
        project_id: str,
        status: str,
        **kwargs: Any,
    ) -> None:
        """
        Update the status of a project.

        Args:
            project_id: The unique identifier for the project
            status: The new status value (status name or ID)
            **kwargs: Optional parameters (sub_status_id, etc.)

        Raises:
            CRMError: If the project is not found or update fails
        """
        logger.info(f"Updating Service Titan project {project_id} status to {status}")

        # For Service Titan, we need to call update_project with status_id and sub_status_id
        # The status parameter could be a status name or ID
        # For now, we'll use the sub_status_id from kwargs if provided

        sub_status_id = kwargs.get("sub_status_id")

        if not sub_status_id:
            raise CRMError(
                error_code="INVALID_REQUEST",
                message="Service Titan requires 'sub_status_id' in kwargs to update project status",
            )

        # Create update request
        from src.integrations.crm.schemas import UpdateProjectRequest

        update_req = UpdateProjectRequest(
            tenant=self.tenant_id,
            project_id=int(project_id),
            sub_status_id=sub_status_id,
        )

        # Call existing update_project method
        await self.update_project(update_req)

        logger.info(f"Successfully updated project {project_id} status")

    async def get_available_statuses(self) -> list[str]:
        """
        Get list of valid status values for Service Titan.

        Attempts to fetch project substatuses from Service Titan API.
        Falls back to hardcoded Status enum if API call fails.

        Returns:
            List of valid status strings
        """
        logger.info("[ServiceTitanProvider] Fetching available statuses")

        try:
            # Fetch all project substatuses (these are the actual status values in ST)
            from src.integrations.crm.schemas import ProjectSubStatusesRequest

            substatus_req = ProjectSubStatusesRequest(
                tenant=self.tenant_id,
                active="Any",  # Get all statuses, active and inactive
                page=1,
                page_size=500,  # Get a large batch
            )

            substatus_response = await self.get_project_substatuses(substatus_req)

            # Extract unique status names from substatuses
            statuses = []
            for substatus in substatus_response.data:
                if substatus.name and substatus.name not in statuses:
                    statuses.append(substatus.name)

            if statuses:
                logger.info(
                    f"[ServiceTitanProvider] Fetched {len(statuses)} statuses from API"
                )
                return statuses

            # If no statuses returned, fall back to hardcoded enum
            logger.warning(
                "[ServiceTitanProvider] No statuses returned from API, using fallback"
            )
            return [status.value for status in Status]

        except Exception as e:
            logger.error(
                f"[ServiceTitanProvider] Failed to fetch statuses from API: {e}"
            )
            # Fallback to hardcoded Status enum values
            return [status.value for status in Status]

    # ========================================================================
    # Helper Methods (transformation functions)
    # ========================================================================

    def _transform_st_project_to_universal_project(self, st_project: ProjectResponse) -> Project:
        """
        Transform Service Titan project to universal Project schema.

        Service Titan projects are top-level work containers (one per customer).
        """
        return Project(
            id=str(st_project.id),
            name=st_project.name,
            number=st_project.number,
            status=st_project.status or "Unknown",
            status_id=str(st_project.status_id) if st_project.status_id else None,
            sub_status=st_project.sub_status,
            sub_status_id=str(st_project.sub_status_id) if st_project.sub_status_id else None,
            workflow_type="Project",
            description=None,  # Projects don't have description in ST
            customer_id=str(st_project.customer_id) if st_project.customer_id else None,
            customer_name=None,  # Not in project response
            location_id=str(st_project.location_id) if st_project.location_id else None,
            address_line1=None,  # Not in project response
            address_line2=None,
            city=None,
            state=None,
            postal_code=None,
            country=None,
            created_at=st_project.created_on.isoformat(),
            updated_at=st_project.modified_on.isoformat(),
            start_date=st_project.start_date.isoformat()
            if st_project.start_date
            else None,
            target_completion_date=st_project.target_completion_date.isoformat()
            if st_project.target_completion_date
            else None,
            actual_completion_date=st_project.actual_completion_date.isoformat()
            if st_project.actual_completion_date
            else None,
            sales_rep_id=None,
            sales_rep_name=None,
            provider=CRMProviderEnum.SERVICE_TITAN,
            provider_data={},  # Additional ST-specific data can go here if needed
        )

    def _transform_st_job_to_universal(self, st_job: ServiceTitanJob) -> Job:
        """
        Transform Service Titan job to universal Job schema.

        Service Titan jobs are sub-items under projects and contain references
        to their parent project_id.
        """
        return Job(
            id=str(st_job.id),
            name=st_job.summary,
            number=st_job.job_number,
            status=st_job.job_status,
            status_id=None,  # ST Jobs don't have separate status IDs
            workflow_type="Job",
            description=st_job.summary,
            customer_id=str(st_job.customer_id),
            customer_name=None,  # Not in job response
            address_line1=None,  # Not in job response
            address_line2=None,
            city=None,
            state=None,
            postal_code=None,
            country=None,
            created_at=st_job.created_on.isoformat(),
            updated_at=st_job.modified_on.isoformat(),
            completed_at=st_job.completed_on.isoformat()
            if st_job.completed_on
            else None,
            sales_rep_id=None,
            sales_rep_name=None,
            provider=CRMProviderEnum.SERVICE_TITAN,
            provider_data={
                "project_id": st_job.project_id,
                "location_id": st_job.location_id,
                "business_unit_id": st_job.business_unit_id,
                "job_type_id": st_job.job_type_id,
                "priority": st_job.priority,
                "campaign_id": st_job.campaign_id,
                "appointment_count": st_job.appointment_count,
                "first_appointment_id": st_job.first_appointment_id,
                "last_appointment_id": st_job.last_appointment_id,
                "recall_for_id": st_job.recall_for_id,
                "warranty_id": st_job.warranty_id,
                "no_charge": st_job.no_charge,
                "notifications_enabled": st_job.notifications_enabled,
                "invoice_id": st_job.invoice_id,
                "total": st_job.total,
            },
        )

    # ========================================================================
    # Legacy/Service Titan-Specific Methods
    # ========================================================================

    async def get_project_status(self, project_id: str) -> ProjectStatusResponse:
        """
        Get the status of a specific project by ID from Service Titan.

        Args:
            project_id: The Service Titan job ID

        Returns:
            ProjectStatusResponse: The project status information

        Raises:
            CRMError: If the project is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PROJECT_BY_ID.format(tenant_id=self.tenant_id, id=project_id)}"

            logger.debug(f"Fetching project status for ID: {project_id}")

            response = await self._make_authenticated_request("GET", url)
            response.raise_for_status()

            data = response.json()

            # Transform Service Titan job data to our schema
            return self._transform_job_to_project_status(data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Project with ID {project_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error fetching project {project_id}: {e}")
                raise CRMError(f"Failed to fetch project status: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching project {project_id}: {e}")
            raise CRMError(f"Failed to fetch project status: {str(e)}", "UNKNOWN_ERROR")

    async def get_appointment_status(
        self, appointment_id: str
    ) -> ProjectStatusResponse:
        """
        Get the status of a specific appointment by ID from Service Titan.

        Args:
            appointment_id: The Service Titan appointment ID

        Returns:
            ProjectStatusResponse: The appointment status information

        Raises:
            CRMError: If the appointment is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.APPOINTMENT_BY_ID.format(tenant_id=self.tenant_id, id=appointment_id)}"

            logger.debug(f"Fetching appointment status for ID: {appointment_id}")

            response = await self._make_authenticated_request("GET", url)
            response.raise_for_status()

            data = response.json()

            # Transform Service Titan appointment data to our schema
            return self._transform_job_to_project_status(data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(
                    f"Appointment with ID {appointment_id} not found", "NOT_FOUND"
                )
            else:
                logger.error(f"HTTP error fetching appointment {appointment_id}: {e}")
                raise CRMError(f"Failed to fetch appointment status: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching appointment {appointment_id}: {e}")
            raise CRMError(
                f"Failed to fetch appointment status: {str(e)}", "UNKNOWN_ERROR"
            )

    async def get_all_appointment_statuses(self) -> ProjectStatusListResponse:
        """
        Get the status of all appointments from Service Titan.

        Returns:
            ProjectStatusListResponse: List of all appointment statuses

        Raises:
            CRMError: If an error occurs while fetching appointment statuses
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.APPOINTMENTS.format(tenant_id=self.tenant_id)}"

            logger.debug("Fetching all appointment statuses")

            response = await self._make_authenticated_request("GET", url)
            response.raise_for_status()

            data = response.json()

            # Service Titan returns data in a "data" field with pagination info
            jobs = data.get("data", [])
            total_count = data.get("totalCount", len(jobs))

            # Transform all appointments to project statuses
            projects = [self._transform_job_to_project_status(job) for job in jobs]

            return ProjectStatusListResponse(
                projects=projects,
                total_count=total_count,
                provider=CRMProviderEnum.SERVICE_TITAN,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching all appointments: {e}")
            raise CRMError(f"Failed to fetch appointment statuses: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching all appointments: {e}")
            raise CRMError(
                f"Failed to fetch appointment statuses: {str(e)}", "UNKNOWN_ERROR"
            )

    async def get_all_project_statuses(self) -> ProjectStatusListResponse:
        """
        Get the status of all projects from Service Titan.

        Returns:
            ProjectStatusListResponse: List of all project statuses

        Raises:
            CRMError: If an error occurs while fetching project statuses
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PROJECTS.format(tenant_id=self.tenant_id)}"

            logger.debug("Fetching all project statuses")

            response = await self._make_authenticated_request("GET", url)
            response.raise_for_status()

            data = response.json()

            # Debug: Log the actual response structure
            logger.info(f"Projects endpoint response keys: {list(data.keys())}")
            logger.info(f"Projects response sample: {str(data)[:500]}...")

            # Debug: Log the actual response structure for jobs
            logger.info(f"Jobs endpoint response keys: {list(data.keys())}")

            # Service Titan returns data in a "data" field with pagination info
            jobs = data.get("data", [])
            total_count = data.get("totalCount") or data.get("count") or len(jobs)

            # Transform all jobs to project statuses
            projects = [self._transform_job_to_project_status(job) for job in jobs]

            return ProjectStatusListResponse(
                projects=projects,
                total_count=total_count,
                provider=CRMProviderEnum.SERVICE_TITAN,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching all projects: {e}")
            raise CRMError(f"Failed to fetch project statuses: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching all projects: {e}")
            raise CRMError(
                f"Failed to fetch project statuses: {str(e)}", "UNKNOWN_ERROR"
            )

    async def get_all_form_submissions(
        self,
        form_ids: list[int],
        status: str | None = None,
        owners: list[dict] | None = None,
    ) -> FormSubmissionListResponse:
        """
        Get all form submissions from Service Titan for a specific form.

        Args:
            form_ids: List of form IDs to get submissions for
            status: Optional form status to filter by (Started, Completed, Any)
            owners: Optional list of owner objects with type and id

        Returns:
            FormSubmissionListResponse: List of all form submissions

        Raises:
            CRMError: If an error occurs while fetching form submissions
        """
        try:
            # Use the general form submissions endpoint
            url = f"{self.base_api_url}{ServiceTitanEndpoints.FORM_SUBMISSIONS.format(tenant_id=self.tenant_id)}"

            # Prepare query parameters using camelCase as Service Titan expects
            # Convert list of form IDs to comma-separated string
            form_ids_str = ",".join(str(form_id) for form_id in form_ids)
            params = {
                "formIds": form_ids_str,
            }

            if status:
                params["status"] = status

            if owners:
                params["owners"] = owners

            logger.debug(
                f"Fetching form submissions for form IDs {form_ids} with status: {status}, owners: {owners}"
            )
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Request params: {params}")

            response = await self._make_authenticated_request("GET", url, params=params)
            response.raise_for_status()

            data = response.json()

            # Return the response directly as FormSubmissionListResponse
            return FormSubmissionListResponse(**data)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching form submissions: {e}")
            raise CRMError(f"Failed to fetch form submissions: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching form submissions: {e}")
            raise CRMError(
                f"Failed to fetch form submissions: {str(e)}", "UNKNOWN_ERROR"
            )

    def _transform_job_to_project_status(
        self, job_data: dict[str, Any]
    ) -> ProjectStatusResponse:
        """
        Transform Service Titan job data to our ProjectStatusResponse schema.

        Args:
            job_data: Raw job data from Service Titan API

        Returns:
            ProjectStatusResponse: Transformed project status
        """
        # Get Service Titan job status (it already matches our Status enum values)
        service_titan_status = job_data.get("status", "")
        # Convert to Status enum - Service Titan uses exact same values
        try:
            mapped_status = Status(service_titan_status)
        except ValueError:
            # Default to SCHEDULED if status is unknown
            mapped_status = Status.SCHEDULED

        # Extract update timestamp
        updated_at = None
        if job_data.get("modifiedOn"):
            try:
                updated_at = datetime.fromisoformat(
                    job_data["modifiedOn"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                updated_at = datetime.now(UTC)

        # Create structured provider data using Pydantic model
        provider_data_model = CRMProviderDataFactory.create_service_titan_data(job_data)

        return ProjectStatusResponse(
            project_id=str(job_data.get("id", "")),
            status=mapped_status,
            provider=CRMProviderEnum.SERVICE_TITAN,
            updated_at=updated_at,
            provider_data=provider_data_model.model_dump(),
        )

    async def get_estimate(self, estimate_id: int) -> EstimateResponse:
        """
        Get a specific estimate by ID from Service Titan.

        Args:
            estimate_id: The Service Titan estimate ID

        Returns:
            EstimateResponse: The estimate information

        Raises:
            CRMError: If the estimate is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.ESTIMATE_BY_ID.format(tenant_id=self.tenant_id, id=estimate_id)}"

            logger.debug(f"Fetching estimate for ID: {estimate_id}")

            response = await self._make_authenticated_request("GET", url)
            response.raise_for_status()

            data = response.json()

            # Return the raw response as EstimateResponse
            return EstimateResponse(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Estimate with ID {estimate_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error fetching estimate {estimate_id}: {e}")
                raise CRMError(f"Failed to fetch estimate: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching estimate {estimate_id}: {e}")
            raise CRMError(f"Failed to fetch estimate: {str(e)}", "UNKNOWN_ERROR")

    async def get_estimates(
        self,
        request: EstimatesRequest,
    ) -> EstimatesListResponse:
        """
        Get estimates from Service Titan with optional filters.

        Args:
            request: EstimatesRequest with filter and pagination parameters

        Returns:
            EstimatesListResponse: Paginated list of estimates

        Raises:
            CRMError: If an error occurs while fetching estimates
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.ESTIMATES.format(tenant_id=self.tenant_id)}"

            # Convert request model to params dict with camelCase field names
            params = {}
            if request.job_id is not None:
                params["jobId"] = request.job_id
            if request.project_id is not None:
                params["projectId"] = request.project_id
            if request.page is not None:
                params["page"] = request.page
            if request.page_size is not None:
                params["pageSize"] = min(request.page_size, 50)  # Enforce max of 50
            if request.ids is not None:
                params["ids"] = request.ids

            logger.debug(f"Fetching estimates with params: {params}")

            response = await self._make_authenticated_request("GET", url, params=params)
            response.raise_for_status()

            data = response.json()

            # Service Titan returns data in a "data" field with pagination info
            estimates_data = data.get("data", [])

            # Convert each estimate to EstimateResponse
            estimates = [
                EstimateResponse(**estimate_data) for estimate_data in estimates_data
            ]

            # Build the response with pagination info
            estimates_response = EstimatesListResponse(
                estimates=estimates,
                total_count=data.get("totalCount"),
                page=data.get("page", request.page),
                page_size=data.get("pageSize", request.page_size),
                has_more=data.get("hasMore"),
            )

            logger.info(f"Found {len(estimates)} estimates")
            return estimates_response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching estimates: {e}")
            raise CRMError(f"Failed to fetch estimates: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching estimates: {e}")
            raise CRMError(f"Failed to fetch estimates: {str(e)}", "UNKNOWN_ERROR")

    async def get_estimate_items(
        self,
        request: EstimateItemsRequest,
    ) -> EstimateItemsResponse:
        """
        Get estimate items from Service Titan with optional filters.

        Args:
            request: EstimateItemsRequest with filter and pagination parameters

        Returns:
            EstimateItemsResponse: Paginated list of estimate items

        Raises:
            CRMError: If an error occurs while fetching estimate items
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.ESTIMATE_ITEMS.format(tenant_id=self.tenant_id)}"

            # Convert request model to params dict with camelCase field names
            params = {}
            if request.estimate_id is not None:
                params["estimateId"] = request.estimate_id
            if request.ids is not None:
                params["ids"] = request.ids
            if request.active is not None:
                params["active"] = request.active
            if request.page is not None:
                params["page"] = request.page
            if request.page_size is not None:
                params["pageSize"] = min(request.page_size, 50)  # Enforce max of 50

            logger.debug(f"Fetching estimate items with params: {params}")

            response = await self._make_authenticated_request("GET", url, params=params)
            response.raise_for_status()

            data = response.json()

            # Service Titan returns data in a "data" field with pagination info
            items_data = data.get("data", [])

            # Convert each item to EstimateItemResponse
            items = [EstimateItemResponse(**item_data) for item_data in items_data]

            # Build the response with pagination info
            items_response = EstimateItemsResponse(
                items=items,
                total_count=data.get("totalCount"),
                page=data.get("page", request.page or 1),
                page_size=data.get("pageSize", request.page_size or 50),
                has_more=data.get("hasMore", False),
            )

            logger.info(f"Found {len(items)} estimate items")
            return items_response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching estimate items: {e}")
            raise CRMError(f"Failed to fetch estimate items: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching estimate items: {e}")
            raise CRMError(f"Failed to fetch estimate items: {str(e)}", "UNKNOWN_ERROR")

    async def add_job_note(
        self, job_id: int, text: str, pin_to_top: bool | None = None
    ) -> JobNoteResponse:
        """
        Add a note to a specific job in Service Titan.

        Args:
            job_id: The Service Titan job ID
            text: The text content of the note
            pin_to_top: Whether to pin the note to the top (optional)

        Returns:
            JobNoteResponse: The created note information

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.JOB_NOTES.format(tenant_id=self.tenant_id, id=job_id)}"

            # Prepare request body with camelCase field names
            request_body = {"text": text}
            if pin_to_top is not None:
                request_body["pinToTop"] = pin_to_top

            logger.debug(f"Adding note to job {job_id}")

            response = await self._make_authenticated_request(
                "POST", url, json=request_body
            )
            response.raise_for_status()

            data = response.json()

            # Return the response as JobNoteResponse
            return JobNoteResponse(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with ID {job_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error adding note to job {job_id}: {e}")
                raise CRMError(f"Failed to add note to job: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error adding note to job {job_id}: {e}")
            raise CRMError(f"Failed to add note to job: {str(e)}", "UNKNOWN_ERROR")

    async def update_project_claim_status(self, job_id: int, claim_status: str) -> None:
        """
        Update the claim status for a specific project/job.

        Note: Service Titan doesn't have a native claim status field, so this is
        currently a no-op. In a real implementation, you might store this in a
        custom field or use project tags/categories.

        Args:
            job_id: The unique identifier for the job
            claim_status: The new claim status value

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        logger.info(
            f"[ServiceTitanProvider] Claim status update not supported for job {job_id} "
            f"(would set to {claim_status}). This would require custom field implementation."
        )

    async def get_job_hold_reasons(
        self, active: str | None = None
    ) -> JobHoldReasonsListResponse:
        """
        Get a list of job hold reasons from Service Titan.

        Args:
            active: Optional active status filter (True, False, Any)

        Returns:
            JobHoldReasonsListResponse: List of job hold reasons

        Raises:
            CRMError: If an error occurs while fetching hold reasons
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.JOB_HOLD_REASONS.format(tenant_id=self.tenant_id)}"

            params = {}
            if active is not None:
                params["active"] = active

            logger.debug("Fetching job hold reasons")

            response = await self._make_authenticated_request("GET", url, params=params)
            response.raise_for_status()

            data = response.json()

            # Return the response as JobHoldReasonsListResponse
            return JobHoldReasonsListResponse(**data)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching job hold reasons: {e}")
            raise CRMError(f"Failed to fetch job hold reasons: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching job hold reasons: {e}")
            raise CRMError(
                f"Failed to fetch job hold reasons: {str(e)}", "UNKNOWN_ERROR"
            )

    async def hold_job(self, job_id: int, reason_id: int, memo: str) -> None:
        """
        Put a job on hold in Service Titan.

        Args:
            job_id: The Service Titan job ID
            reason_id: The ID of the hold reason
            memo: The memo/message for the hold

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.JOB_HOLD.format(tenant_id=self.tenant_id, id=job_id)}"

            # Prepare request body with camelCase field names
            request_body = {"reasonId": reason_id, "memo": memo}

            logger.debug(f"Putting job {job_id} on hold with reason {reason_id}")

            response = await self._make_authenticated_request(
                "PUT", url, json=request_body
            )
            response.raise_for_status()

            logger.info(f"Successfully put job {job_id} on hold")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with ID {job_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error holding job {job_id}: {e}")
                raise CRMError(f"Failed to hold job: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error holding job {job_id}: {e}")
            raise CRMError(f"Failed to hold job: {str(e)}", "UNKNOWN_ERROR")

    async def remove_job_cancellation(self, job_id: int) -> None:
        """
        Remove cancellation from a job in Service Titan.

        Args:
            job_id: The Service Titan job ID

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.JOB_REMOVE_CANCELLATION.format(tenant_id=self.tenant_id, id=job_id)}"

            logger.debug(f"Removing cancellation from job {job_id}")

            response = await self._make_authenticated_request("PUT", url)
            response.raise_for_status()

            logger.info(f"Successfully removed cancellation from job {job_id}")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with ID {job_id} not found", "NOT_FOUND")
            elif e.response.status_code == 400:
                raise CRMError(
                    f"Job {job_id} is not in a canceled state", "INVALID_STATE"
                )
            else:
                logger.error(f"HTTP error removing cancellation from job {job_id}: {e}")
                raise CRMError(f"Failed to remove cancellation: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(
                f"Unexpected error removing cancellation from job {job_id}: {e}"
            )
            raise CRMError(f"Failed to remove cancellation: {str(e)}", "UNKNOWN_ERROR")

    async def get_project_substatuses(
        self,
        request: ProjectSubStatusesRequest,
    ) -> ProjectSubStatusListResponse:
        """
        Get project sub statuses from Service Titan.

        Args:
            request: ProjectSubStatusesRequest with filter and pagination parameters

        Returns:
            ProjectSubStatusListResponse: List of project sub statuses

        Raises:
            CRMError: If an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PROJECT_SUBSTATUSES.format(tenant_id=self.tenant_id)}"

            params: dict[str, Any] = {}
            if request.name is not None:
                params["name"] = request.name
            if request.status_id is not None:
                params["statusId"] = request.status_id
            if request.active is not None:
                params["active"] = request.active
            if request.page is not None:
                params["page"] = request.page
            if request.page_size is not None:
                params["pageSize"] = request.page_size

            logger.debug(f"Fetching project substatuses with params: {params}")

            response = await self._make_authenticated_request("GET", url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Found {len(data.get('data', []))} project substatuses")

            return ProjectSubStatusListResponse(**data)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching project substatuses: {e}")
            raise CRMError(f"Failed to fetch project substatuses: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching project substatuses: {e}")
            raise CRMError(
                f"Failed to fetch project substatuses: {str(e)}", "UNKNOWN_ERROR"
            )

    async def get_project_by_id(self, request: ProjectByIdRequest) -> ProjectResponse:
        """
        Get a project by ID from Service Titan.

        Args:
            request: ProjectByIdRequest with project_id

        Returns:
            ProjectResponse: Project data

        Raises:
            CRMError: If the project is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PROJECT_BY_ID.format(tenant_id=self.tenant_id, id=request.project_id)}"

            logger.debug(f"Fetching project {request.project_id}")

            response = await self._make_authenticated_request("GET", url)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Successfully fetched project {request.project_id}")

            return ProjectResponse(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(
                    f"Project with ID {request.project_id} not found", "NOT_FOUND"
                )
            else:
                logger.error(f"HTTP error fetching project {request.project_id}: {e}")
                raise CRMError(f"Failed to fetch project: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching project {request.project_id}: {e}")
            raise CRMError(f"Failed to fetch project: {str(e)}", "UNKNOWN_ERROR")

    async def update_project(self, request: UpdateProjectRequest) -> ProjectResponse:
        """
        Update a project in Service Titan.

        Args:
            request: Update project request with fields to update

        Returns:
            ProjectResponse: Updated project data

        Raises:
            CRMError: If the project is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PROJECT_UPDATE.format(tenant_id=self.tenant_id, id=request.project_id)}"

            # Dump Pydantic model excluding None values and using API aliases
            request_body = request.model_dump(
                exclude_none=True,
                by_alias=True,
                exclude={"tenant", "project_id", "external_data"},
            )

            # Handle external_data separately - API expects specific format
            if request.external_data is not None:
                # Service Titan approved application GUID
                approved_guid = "4a1ac44b-bab3-4de9-9a59-b40327e3fd42"
                request_body["externalData"] = {
                    "applicationGuid": approved_guid,
                    "patchMode": "Merge",  # Use Merge to preserve existing data
                    "externalData": [
                        {"key": item.key, "value": item.value}
                        for item in request.external_data
                    ],
                }

            logger.debug(
                f"Updating project {request.project_id} with data: {request_body}"
            )

            response = await self._make_authenticated_request(
                "PATCH", url, json=request_body
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Successfully updated project {request.project_id}")

            return ProjectResponse(**data)

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(
                f"HTTP {e.response.status_code} error updating project {request.project_id}: {error_body}"
            )

            if e.response.status_code == 404:
                raise CRMError(
                    f"Project with ID {request.project_id} not found", "NOT_FOUND"
                )
            elif e.response.status_code == 400:
                raise CRMError(
                    f"Invalid request data for project {request.project_id}: {error_body}",
                    "INVALID_REQUEST",
                )
            else:
                raise CRMError(f"Failed to update project: {error_body}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error updating project {request.project_id}: {e}")
            raise CRMError(f"Failed to update project: {str(e)}", "UNKNOWN_ERROR")

    async def add_project_note(
        self, project_id: int, text: str, pin_to_top: bool | None = None
    ) -> ProjectNoteResponse:
        """
        Add a note to a specific project in Service Titan.

        Args:
            project_id: The Service Titan project ID
            text: The text content of the note
            pin_to_top: Whether to pin the note to the top (optional)

        Returns:
            ProjectNoteResponse: The created note information

        Raises:
            CRMError: If the project is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PROJECT_NOTES.format(tenant_id=self.tenant_id, id=project_id)}"

            # Prepare request body with camelCase field names
            request_body = {"text": text}
            if pin_to_top is not None:
                request_body["pinToTop"] = pin_to_top

            logger.debug(f"Adding note to project {project_id}")

            response = await self._make_authenticated_request(
                "POST", url, json=request_body
            )
            response.raise_for_status()

            data = response.json()

            # Return the response as ProjectNoteResponse
            return ProjectNoteResponse(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Project with ID {project_id} not found", "NOT_FOUND")
            else:
                error_body = e.response.text
                logger.error(
                    f"HTTP error adding note to project {project_id}: {error_body}"
                )
                raise CRMError(
                    f"Failed to add note to project: {error_body}", "HTTP_ERROR"
                )
        except Exception as e:
            logger.error(f"Unexpected error adding note to project {project_id}: {e}")
            raise CRMError(f"Failed to add note to project: {str(e)}", "UNKNOWN_ERROR")

    async def get_form_submissions(
        self,
        request: FormSubmissionsRequest,
    ) -> FormSubmissionListResponse:
        """
        Get form submissions from Service Titan.

        Args:
            request: FormSubmissionsRequest with filter and pagination parameters

        Returns:
            FormSubmissionListResponse: Form submissions data with pagination info

        Raises:
            CRMError: If an error occurs fetching submissions
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.FORM_SUBMISSIONS.format(tenant_id=self.tenant_id)}"

            # Build query parameters
            params: dict[str, Any] = {
                "page": request.page,
                "pageSize": request.page_size,
            }

            if request.form_id is not None:
                params["formIds"] = str(request.form_id)

            if request.status is not None:
                params["status"] = request.status

            # Add owners filter if provided
            # Format: owners[0].type=Job&owners[0].id=123456
            if request.owners is not None:
                for i, owner in enumerate(request.owners):
                    params[f"owners[{i}].type"] = owner.type
                    params[f"owners[{i}].id"] = owner.id

            logger.debug(f"Fetching form submissions with params: {params}")

            response = await self._make_authenticated_request("GET", url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.info(
                f"Successfully fetched {len(data.get('data', []))} form submissions"
            )

            return FormSubmissionListResponse(**data)

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(f"HTTP error fetching form submissions: {error_body}")
            raise CRMError(
                f"Failed to fetch form submissions: {error_body}", "HTTP_ERROR"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching form submissions: {e}")
            raise CRMError(
                f"Failed to fetch form submissions: {str(e)}", "UNKNOWN_ERROR"
            )

    async def get_pricebook_materials(
        self, request: PricebookItemsRequest
    ) -> MaterialsListResponse:
        """
        Get materials from the Service Titan pricebook.

        Args:
            request: Request parameters including pagination and filters

        Returns:
            MaterialsListResponse: Paginated list of materials

        Raises:
            CRMError: If an error occurs while fetching materials
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PRICEBOOK_MATERIALS.format(tenant_id=self.tenant_id)}"

            params = {
                "page": request.page,
                "pageSize": request.page_size,
                "active": request.active,
            }

            logger.debug(f"Fetching pricebook materials with params: {params}")

            response = await self._make_authenticated_request("GET", url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Found {len(data.get('data', []))} materials")

            return MaterialsListResponse(**data)

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(f"HTTP error fetching pricebook materials: {error_body}")
            raise CRMError(
                f"Failed to fetch pricebook materials: {error_body}", "HTTP_ERROR"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching pricebook materials: {e}")
            raise CRMError(
                f"Failed to fetch pricebook materials: {str(e)}", "UNKNOWN_ERROR"
            )

    async def get_pricebook_services(
        self, request: PricebookItemsRequest
    ) -> ServicesListResponse:
        """
        Get services from the Service Titan pricebook.

        Args:
            request: Request parameters including pagination and filters

        Returns:
            ServicesListResponse: Paginated list of services

        Raises:
            CRMError: If an error occurs while fetching services
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PRICEBOOK_SERVICES.format(tenant_id=self.tenant_id)}"

            params = {
                "page": request.page,
                "pageSize": request.page_size,
                "active": request.active,
            }

            logger.debug(f"Fetching pricebook services with params: {params}")

            response = await self._make_authenticated_request("GET", url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Found {len(data.get('data', []))} services")

            return ServicesListResponse(**data)

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(f"HTTP error fetching pricebook services: {error_body}")
            raise CRMError(
                f"Failed to fetch pricebook services: {error_body}", "HTTP_ERROR"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching pricebook services: {e}")
            raise CRMError(
                f"Failed to fetch pricebook services: {str(e)}", "UNKNOWN_ERROR"
            )

    async def get_pricebook_equipment(
        self, request: PricebookItemsRequest
    ) -> EquipmentListResponse:
        """
        Get equipment from the Service Titan pricebook.

        Args:
            request: Request parameters including pagination and filters

        Returns:
            EquipmentListResponse: Paginated list of equipment

        Raises:
            CRMError: If an error occurs while fetching equipment
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PRICEBOOK_EQUIPMENT.format(tenant_id=self.tenant_id)}"

            params = {
                "page": request.page,
                "pageSize": request.page_size,
                "active": request.active,
            }

            logger.debug(f"Fetching pricebook equipment with params: {params}")

            response = await self._make_authenticated_request("GET", url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.info(f"Found {len(data.get('data', []))} equipment items")

            return EquipmentListResponse(**data)

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(f"HTTP error fetching pricebook equipment: {error_body}")
            raise CRMError(
                f"Failed to fetch pricebook equipment: {error_body}", "HTTP_ERROR"
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching pricebook equipment: {e}")
            raise CRMError(
                f"Failed to fetch pricebook equipment: {str(e)}", "UNKNOWN_ERROR"
            )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
