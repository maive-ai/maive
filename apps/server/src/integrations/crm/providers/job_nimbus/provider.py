"""
JobNimbus CRM provider implementation.

This module implements the CRMProvider interface for JobNimbus,
handling API communication and data transformation.
"""

import json
from datetime import UTC, datetime
from typing import Any

import httpx

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.config import JobNimbusConfig, get_crm_settings
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.provider_schemas import FormSubmissionListResponse
from src.integrations.crm.providers.job_nimbus.constants import JobNimbusEndpoints
from src.integrations.crm.providers.job_nimbus.schemas import (
    JobNimbusActivityResponse,
    JobNimbusContactResponse,
    JobNimbusContactsListResponse,
    JobNimbusCreateActivityRequest,
    JobNimbusCreateContactRequest,
    JobNimbusJobResponse,
    JobNimbusJobsListResponse,
    JobNimbusUpdateContactRequest,
)
from src.integrations.crm.schemas import (
    Contact,
    ContactList,
    EquipmentListResponse,
    EstimateResponse,
    Job,
    JobList,
    JobNoteResponse,
    JobResponse,
    MaterialsListResponse,
    Note,
    PricebookItemsRequest,
    Project,
    ProjectList,
    ProjectStatusListResponse,
    ProjectStatusResponse,
    ServicesListResponse,
)
from src.utils.logger import logger


class JobNimbusProvider(CRMProvider):
    """JobNimbus implementation of the CRMProvider interface."""

    def __init__(self):
        """Initialize the JobNimbus provider."""
        self.config = get_crm_settings()
        self.settings = self.config.provider_config

        if not isinstance(self.settings, JobNimbusConfig):
            raise ValueError("JobNimbusConfig required for JobNimbusProvider")

        self.api_key = self.settings.api_key
        self.base_api_url = self.settings.base_api_url

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.request_timeout),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        logger.info("JobNimbusProvider initialized")

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> httpx.Response:
        """Make an authenticated request to JobNimbus API."""
        url = f"{self.base_api_url}{endpoint}"
        return await self.client.request(method, url, **kwargs)

    def _unix_timestamp_to_datetime(self, timestamp: int) -> datetime:
        """Convert Unix timestamp to datetime."""
        return datetime.fromtimestamp(timestamp, tz=UTC)

    # Job methods

    # ========================================================================
    # Universal CRM Interface Implementation (required abstract methods)
    # ========================================================================

    async def get_job(self, job_id: str) -> Job:
        """
        Get a specific job by JNID from JobNimbus.

        Args:
            job_id: The JobNimbus JNID (string identifier)

        Returns:
            Job: Universal job schema

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        try:
            endpoint = JobNimbusEndpoints.JOB_BY_ID.format(jnid=job_id)

            logger.debug(f"Fetching job for JNID: {job_id}")

            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()
            jn_job = JobNimbusJobResponse(**data)

            return self._transform_jn_job_to_universal(jn_job)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with JNID {job_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error fetching job {job_id}: {e}")
                raise CRMError(f"Failed to fetch job: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching job {job_id}: {e}")
            raise CRMError(f"Failed to fetch job: {str(e)}", "UNKNOWN_ERROR")

    async def get_all_jobs(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> JobList:
        """
        Get all jobs with optional filtering and pagination.

        Args:
            filters: Optional dictionary of filters (not yet implemented)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            JobList: Paginated list of jobs
        """
        try:
            logger.debug(f"Fetching all jobs (page={page}, size={page_size})")

            endpoint = JobNimbusEndpoints.JOBS
            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()
            jn_jobs_list = JobNimbusJobsListResponse(**data)

            # Transform to universal Job schemas
            jobs = [
                self._transform_jn_job_to_universal(jn_job)
                for jn_job in jn_jobs_list.results
            ]

            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_jobs = jobs[start_idx:end_idx]

            return JobList(
                jobs=paginated_jobs,
                total_count=len(jobs),
                provider=CRMProviderEnum.JOB_NIMBUS,
                page=page,
                page_size=page_size,
                has_more=end_idx < len(jobs),
            )

        except Exception as e:
            logger.error(f"Error fetching all jobs: {e}")
            raise CRMError(f"Failed to fetch jobs: {str(e)}", "UNKNOWN_ERROR")

    async def get_project(self, project_id: str) -> Project:
        """
        Get a specific project by ID.

        In JobNimbus, projects and jobs are the same entity (flat structure).

        Args:
            project_id: The JobNimbus JNID

        Returns:
            Project: Universal project schema

        Raises:
            CRMError: If the project is not found
        """
        logger.info(f"Getting JobNimbus project: {project_id}")

        # Get job first
        endpoint = JobNimbusEndpoints.JOB_BY_ID.format(jnid=project_id)

        try:
            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()
            jn_job = JobNimbusJobResponse(**data)

            return self._transform_jn_job_to_universal_project(jn_job)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Project with JNID {project_id} not found", "NOT_FOUND")
            raise CRMError(f"Failed to fetch project: {e}", "HTTP_ERROR")
        except Exception as e:
            raise CRMError(f"Failed to fetch project: {str(e)}", "UNKNOWN_ERROR")

    async def get_all_projects(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ProjectList:
        """
        Get all projects with optional filtering and pagination.

        In JobNimbus, projects and jobs are the same entity (flat structure).

        Args:
            filters: Optional dictionary of filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ProjectList: Paginated list of projects
        """
        logger.info(f"Getting all JobNimbus projects (page={page}, size={page_size})")

        try:
            endpoint = JobNimbusEndpoints.JOBS
            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()
            jn_jobs_list = JobNimbusJobsListResponse(**data)

            # Transform to universal Project schemas
            projects = [
                self._transform_jn_job_to_universal_project(jn_job)
                for jn_job in jn_jobs_list.results
            ]

            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_projects = projects[start_idx:end_idx]

            return ProjectList(
                projects=paginated_projects,
                total_count=len(projects),
                provider=CRMProviderEnum.JOB_NIMBUS,
                page=page,
                page_size=page_size,
                has_more=end_idx < len(projects),
            )

        except Exception as e:
            logger.error(f"Error fetching all projects: {e}")
            raise CRMError(f"Failed to fetch projects: {str(e)}", "UNKNOWN_ERROR")

    async def get_contact(self, contact_id: str) -> Contact:
        """
        Get a specific contact by JNID from JobNimbus.

        Args:
            contact_id: The JobNimbus contact JNID

        Returns:
            Contact: Universal contact schema

        Raises:
            CRMError: If the contact is not found
        """
        try:
            endpoint = JobNimbusEndpoints.CONTACT_BY_ID.format(jnid=contact_id)

            logger.debug(f"Fetching contact for JNID: {contact_id}")

            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()
            jn_contact = JobNimbusContactResponse(**data)

            return self._transform_jn_contact_to_universal(jn_contact)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Contact with JNID {contact_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error fetching contact {contact_id}: {e}")
                raise CRMError(f"Failed to fetch contact: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching contact {contact_id}: {e}")
            raise CRMError(f"Failed to fetch contact: {str(e)}", "UNKNOWN_ERROR")

    async def get_all_contacts(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ContactList:
        """
        Get all contacts with optional filtering and pagination.

        Args:
            filters: Optional dictionary of filters (not yet implemented)
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            ContactList: Paginated list of contacts
        """
        try:
            logger.debug(f"Fetching all contacts (page={page}, size={page_size})")

            endpoint = JobNimbusEndpoints.CONTACTS
            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()
            jn_contacts_list = JobNimbusContactsListResponse(**data)

            # Transform to universal Contact schemas
            contacts = [
                self._transform_jn_contact_to_universal(jn_contact)
                for jn_contact in jn_contacts_list.results
            ]

            # Apply pagination
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_contacts = contacts[start_idx:end_idx]

            return ContactList(
                contacts=paginated_contacts,
                total_count=len(contacts),
                provider=CRMProviderEnum.JOB_NIMBUS,
                page=page,
                page_size=page_size,
                has_more=end_idx < len(contacts),
            )

        except Exception as e:
            logger.error(f"Error fetching all contacts: {e}")
            raise CRMError(f"Failed to fetch contacts: {str(e)}", "UNKNOWN_ERROR")

    async def add_note(
        self,
        entity_id: str,
        entity_type: str,
        text: str,
        **kwargs: Any,
    ) -> Note:
        """
        Add a note/activity to an entity (job, contact, etc.).

        Args:
            entity_id: The ID of the entity (JNID)
            entity_type: The type of entity ("job", "contact", etc.)
            text: The note text
            **kwargs: Optional parameters (not used by JobNimbus)

        Returns:
            Note: Universal note schema

        Raises:
            CRMError: If the entity is not found or note creation fails
        """
        try:
            logger.info(f"Adding note to {entity_type} {entity_id}")

            # Create activity in JobNimbus
            activity_request = JobNimbusCreateActivityRequest(
                type="note",
                related=[entity_id],
                body=text,
            )

            endpoint = JobNimbusEndpoints.ACTIVITIES
            response = await self._make_request(
                "POST", endpoint, json=activity_request.model_dump(by_alias=True)
            )
            response.raise_for_status()

            data = response.json()
            jn_activity = JobNimbusActivityResponse(**data)

            # Transform to universal Note
            return Note(
                id=jn_activity.jnid,
                text=jn_activity.body or text,
                entity_id=entity_id,
                entity_type=entity_type,
                created_by_id=jn_activity.created_by,
                created_by_name=jn_activity.created_by_name,
                created_at=self._unix_timestamp_to_datetime(jn_activity.date_created).isoformat(),
                updated_at=self._unix_timestamp_to_datetime(jn_activity.date_updated).isoformat()
                if jn_activity.date_updated
                else None,
                is_pinned=False,  # JobNimbus doesn't support pinning
                provider=CRMProviderEnum.JOB_NIMBUS,
                provider_data={
                    "activity_type": jn_activity.type,
                    "recid": jn_activity.recid,
                },
            )

        except Exception as e:
            logger.error(f"Error adding note to {entity_type} {entity_id}: {e}")
            raise CRMError(f"Failed to add note: {str(e)}", "UNKNOWN_ERROR")

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        **kwargs: Any,
    ) -> None:
        """
        Update the status of a job.

        Args:
            job_id: The JobNimbus JNID
            status: The new status value (status name)
            **kwargs: Optional parameters (status_id, etc.)

        Raises:
            CRMError: If the job is not found or update fails
        """
        logger.info(f"Updating JobNimbus job {job_id} status to {status}")

        # JobNimbus requires updating via PATCH with status_name
        try:
            endpoint = JobNimbusEndpoints.JOB_BY_ID.format(jnid=job_id)

            # Build update payload
            update_data = {"statusName": status}
            if "status_id" in kwargs:
                update_data["status"] = kwargs["status_id"]

            response = await self._make_request("PATCH", endpoint, json=update_data)
            response.raise_for_status()

            logger.info(f"Successfully updated job {job_id} status")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with JNID {job_id} not found", "NOT_FOUND")
            raise CRMError(f"Failed to update job status: {e}", "HTTP_ERROR")
        except Exception as e:
            raise CRMError(f"Failed to update job status: {str(e)}", "UNKNOWN_ERROR")

    async def update_project_status(
        self,
        project_id: str,
        status: str,
        **kwargs: Any,
    ) -> None:
        """
        Update the status of a project.

        In JobNimbus, this has the same effect as update_job_status().

        Args:
            project_id: The JobNimbus JNID
            status: The new status value
            **kwargs: Optional parameters

        Raises:
            CRMError: If the project is not found or update fails
        """
        logger.info(f"Updating JobNimbus project {project_id} status to {status}")
        await self.update_job_status(project_id, status, **kwargs)

    # ========================================================================
    # Helper Methods (transformation functions)
    # ========================================================================

    def _transform_jn_job_to_universal(self, jn_job: JobNimbusJobResponse) -> Job:
        """Transform JobNimbus job to universal Job schema."""
        return Job(
            id=jn_job.jnid,
            name=jn_job.name,
            number=jn_job.number,
            status=jn_job.status_name or "Unknown",
            status_id=str(jn_job.status) if jn_job.status else None,
            workflow_type=jn_job.record_type_name,
            description=jn_job.description,
            customer_id=jn_job.primary.id if jn_job.primary else None,
            customer_name=jn_job.primary.name if jn_job.primary else None,
            address_line1=jn_job.address_line1,
            address_line2=jn_job.address_line2,
            city=jn_job.city,
            state=jn_job.state_text,
            postal_code=jn_job.zip,
            country=jn_job.country_name,
            created_at=self._unix_timestamp_to_datetime(jn_job.date_created).isoformat(),
            updated_at=self._unix_timestamp_to_datetime(jn_job.date_updated).isoformat(),
            completed_at=None,  # JobNimbus doesn't track completion explicitly
            sales_rep_id=jn_job.sales_rep,
            sales_rep_name=jn_job.sales_rep_name,
            provider=CRMProviderEnum.JOB_NIMBUS,
            provider_data={
                "recid": jn_job.recid,
                "jnid": jn_job.jnid,
                "record_type": jn_job.record_type,
                "source": jn_job.source,
                "source_name": jn_job.source_name,
                "location": jn_job.location.model_dump() if jn_job.location else None,
                "owners": [owner.model_dump() for owner in jn_job.owners],
                "related": [r.model_dump() for r in jn_job.related] if jn_job.related else None,
                "is_active": jn_job.is_active,
                "is_archived": jn_job.is_archived,
                "geo": jn_job.geo.model_dump() if jn_job.geo else None,
            },
        )

    def _transform_jn_job_to_universal_project(self, jn_job: JobNimbusJobResponse) -> Project:
        """Transform JobNimbus job to universal Project schema."""
        return Project(
            id=jn_job.jnid,
            name=jn_job.name,
            number=jn_job.number,
            status=jn_job.status_name or "Unknown",
            status_id=str(jn_job.status) if jn_job.status else None,
            sub_status=None,  # JobNimbus doesn't have sub-statuses
            sub_status_id=None,
            workflow_type=jn_job.record_type_name,
            description=jn_job.description,
            customer_id=jn_job.primary.id if jn_job.primary else None,
            customer_name=jn_job.primary.name if jn_job.primary else None,
            location_id=str(jn_job.location.id) if jn_job.location else None,
            address_line1=jn_job.address_line1,
            address_line2=jn_job.address_line2,
            city=jn_job.city,
            state=jn_job.state_text,
            postal_code=jn_job.zip,
            country=jn_job.country_name,
            created_at=self._unix_timestamp_to_datetime(jn_job.date_created).isoformat(),
            updated_at=self._unix_timestamp_to_datetime(jn_job.date_updated).isoformat(),
            start_date=None,  # Not tracked in JobNimbus
            target_completion_date=None,
            actual_completion_date=None,
            sales_rep_id=jn_job.sales_rep,
            sales_rep_name=jn_job.sales_rep_name,
            provider=CRMProviderEnum.JOB_NIMBUS,
            provider_data={
                "recid": jn_job.recid,
                "jnid": jn_job.jnid,
                "record_type": jn_job.record_type,
                "source": jn_job.source,
                "source_name": jn_job.source_name,
                "owners": [owner.model_dump() for owner in jn_job.owners],
                "related": [r.model_dump() for r in jn_job.related] if jn_job.related else None,
            },
        )

    def _transform_jn_contact_to_universal(self, jn_contact: JobNimbusContactResponse) -> Contact:
        """Transform JobNimbus contact to universal Contact schema."""
        # Parse name
        first_name = jn_contact.first_name
        last_name = jn_contact.last_name
        display_name = jn_contact.display_name or f"{first_name or ''} {last_name or ''}".strip()

        return Contact(
            id=jn_contact.jnid,
            first_name=first_name,
            last_name=last_name,
            company=jn_contact.company,
            display_name=display_name,
            email=jn_contact.email,
            phone=jn_contact.home_phone or jn_contact.mobile_phone or jn_contact.work_phone,
            mobile_phone=jn_contact.mobile_phone,
            work_phone=jn_contact.work_phone,
            address_line1=jn_contact.address_line1,
            address_line2=jn_contact.address_line2,
            city=jn_contact.city,
            state=jn_contact.state_text,
            postal_code=jn_contact.zip,
            country=jn_contact.country_name,
            status=jn_contact.status_name,
            workflow_type=jn_contact.record_type_name,
            created_at=self._unix_timestamp_to_datetime(jn_contact.date_created).isoformat(),
            updated_at=self._unix_timestamp_to_datetime(jn_contact.date_updated).isoformat(),
            provider=CRMProviderEnum.JOB_NIMBUS,
            provider_data={
                "recid": jn_contact.recid,
                "jnid": jn_contact.jnid,
                "record_type": jn_contact.record_type,
                "is_active": jn_contact.is_active,
                "is_archived": jn_contact.is_archived,
                "is_sub": jn_contact.is_sub,
                "home_phone": jn_contact.home_phone,
                "location": jn_contact.location.model_dump() if jn_contact.location else None,
            },
        )

    # ========================================================================
    # Legacy/JobNimbus-Specific Methods
    # ========================================================================

    async def get_project_status(self, project_id: str) -> ProjectStatusResponse:
        """
        Get the status of a specific job/project by JNID from JobNimbus.

        Note: JobNimbus doesn't have a separate "project" concept - jobs serve this purpose.

        Args:
            project_id: The JobNimbus JNID

        Returns:
            ProjectStatusResponse: The job status information

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        try:
            endpoint = JobNimbusEndpoints.JOB_BY_ID.format(jnid=project_id)

            logger.debug(f"Fetching job status for JNID: {project_id}")

            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()

            # Parse as JobNimbus job response
            jn_job = JobNimbusJobResponse(**data)

            # Transform to ProjectStatusResponse
            # Note: JobNimbus has custom statuses per workflow, so we store the raw status name
            return ProjectStatusResponse(
                project_id=jn_job.jnid,
                status=jn_job.status_name or "Unknown",  # Using raw status name
                provider=CRMProviderEnum.JOB_NIMBUS,
                updated_at=self._unix_timestamp_to_datetime(jn_job.date_updated),
                provider_data={
                    "jnid": jn_job.jnid,
                    "number": jn_job.number,
                    "name": jn_job.name,
                    "record_type_name": jn_job.record_type_name,
                    "status_name": jn_job.status_name,
                    "status_id": jn_job.status,
                    "sales_rep_name": jn_job.sales_rep_name,
                    "address": {
                        "line1": jn_job.address_line1,
                        "line2": jn_job.address_line2,
                        "city": jn_job.city,
                        "state": jn_job.state_text,
                        "zip": jn_job.zip,
                    },
                },
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with JNID {project_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error fetching job status {project_id}: {e}")
                raise CRMError(f"Failed to fetch job status: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching job status {project_id}: {e}")
            raise CRMError(f"Failed to fetch job status: {str(e)}", "UNKNOWN_ERROR")

    async def get_all_project_statuses(self) -> ProjectStatusListResponse:
        """
        Get the status of all jobs from JobNimbus.

        Returns:
            ProjectStatusListResponse: List of all job statuses

        Raises:
            CRMError: If an error occurs while fetching job statuses
        """
        try:
            endpoint = JobNimbusEndpoints.JOBS

            logger.debug("Fetching all job statuses")

            # Default pagination parameters
            params = {
                "size": 1000,  # Max size per request
                "from": 0,
                "sort_field": "date_updated",
                "sort_direction": "desc",
            }

            response = await self._make_request("GET", endpoint, params=params)
            response.raise_for_status()

            data = response.json()

            # Parse as JobNimbus jobs list response
            jobs_list = JobNimbusJobsListResponse(**data)

            # Transform all jobs to project statuses
            projects = []
            for jn_job in jobs_list.results:
                projects.append(
                    ProjectStatusResponse(
                        project_id=jn_job.jnid,
                        status=jn_job.status_name or "Unknown",
                        provider=CRMProviderEnum.JOB_NIMBUS,
                        updated_at=self._unix_timestamp_to_datetime(jn_job.date_updated),
                        provider_data={
                            "jnid": jn_job.jnid,
                            "number": jn_job.number,
                            "name": jn_job.name,
                            "record_type_name": jn_job.record_type_name,
                            "status_name": jn_job.status_name,
                        },
                    )
                )

            return ProjectStatusListResponse(
                projects=projects,
                total_count=jobs_list.count,
                provider=CRMProviderEnum.JOB_NIMBUS,
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching all jobs: {e}")
            raise CRMError(f"Failed to fetch job statuses: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching all jobs: {e}")
            raise CRMError(f"Failed to fetch job statuses: {str(e)}", "UNKNOWN_ERROR")

    async def get_appointment_status(
        self, appointment_id: str
    ) -> ProjectStatusResponse:
        """
        Get the status of an appointment by ID.

        Note: JobNimbus doesn't have separate appointments - they use Tasks.
        This method is not directly supported.

        Args:
            appointment_id: The appointment/task JNID

        Returns:
            ProjectStatusResponse: The appointment status information

        Raises:
            CRMError: Always raises - not supported for JobNimbus
        """
        raise CRMError(
            "Appointments are not supported by JobNimbus. Use tasks instead.",
            "NOT_SUPPORTED",
        )

    async def get_all_appointment_statuses(self) -> ProjectStatusListResponse:
        """
        Get the status of all appointments.

        Note: JobNimbus doesn't have separate appointments - they use Tasks.
        This method is not directly supported.

        Returns:
            ProjectStatusListResponse: Empty list

        Raises:
            CRMError: Always raises - not supported for JobNimbus
        """
        raise CRMError(
            "Appointments are not supported by JobNimbus. Use tasks instead.",
            "NOT_SUPPORTED",
        )

    async def add_job_note(
        self, job_id: int, text: str, pin_to_top: bool | None = None
    ) -> JobNoteResponse:
        """
        Add a note (activity) to a specific job in JobNimbus.

        Args:
            job_id: The JobNimbus JNID (will be converted to string)
            text: The text content of the note
            pin_to_top: Not supported by JobNimbus (ignored)

        Returns:
            JobNoteResponse: The created note information

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        try:
            jnid = str(job_id)
            endpoint = JobNimbusEndpoints.ACTIVITIES

            # Create activity request
            request_body = JobNimbusCreateActivityRequest(
                note=text,
                recordTypeName="Note",  # Standard note type
                primary={"id": jnid},
                dateCreated=int(datetime.now(UTC).timestamp()),
            )

            logger.debug(f"Adding note to job {jnid}")

            response = await self._make_request(
                "POST", endpoint, json=request_body.model_dump(by_alias=True, exclude_none=True)
            )
            response.raise_for_status()

            data = response.json()

            # Parse as JobNimbus activity response
            activity = JobNimbusActivityResponse(**data)

            # Transform to JobNoteResponse
            return JobNoteResponse(
                text=activity.note,
                isPinned=False,  # JobNimbus doesn't support pinning
                createdById=0,  # Would need to look up user ID
                createdOn=self._unix_timestamp_to_datetime(activity.date_created),
                modifiedOn=self._unix_timestamp_to_datetime(activity.date_updated),
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with JNID {job_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error adding note to job {job_id}: {e}")
                raise CRMError(f"Failed to add note to job: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error adding note to job {job_id}: {e}")
            raise CRMError(f"Failed to add note to job: {str(e)}", "UNKNOWN_ERROR")

    # Unsupported Service Titan-specific methods

    async def get_all_form_submissions(
        self,
        form_ids: list[int],
        status: str | None = None,
        owners: list[dict] | None = None,
    ) -> FormSubmissionListResponse:
        """Not supported by JobNimbus."""
        raise CRMError("Form submissions are not supported by JobNimbus", "NOT_SUPPORTED")

    async def get_estimate(self, estimate_id: int) -> EstimateResponse:
        """Not supported by JobNimbus."""
        raise CRMError("Estimates are not directly supported by JobNimbus", "NOT_SUPPORTED")

    async def update_project_claim_status(self, job_id: int, claim_status: str) -> None:
        """
        Update the claim status for a specific job.

        Note: JobNimbus doesn't have a native claim status field.
        This would require using custom fields.
        """
        logger.warning(
            f"[JobNimbusProvider] Claim status update not supported for job {job_id}. "
            f"Would need to implement custom field support."
        )

    async def get_pricebook_materials(
        self, request: PricebookItemsRequest
    ) -> MaterialsListResponse:
        """Not supported by JobNimbus."""
        raise CRMError("Pricebook materials are not supported by JobNimbus", "NOT_SUPPORTED")

    async def get_pricebook_services(
        self, request: PricebookItemsRequest
    ) -> ServicesListResponse:
        """Not supported by JobNimbus."""
        raise CRMError("Pricebook services are not supported by JobNimbus", "NOT_SUPPORTED")

    async def get_pricebook_equipment(
        self, request: PricebookItemsRequest
    ) -> EquipmentListResponse:
        """Not supported by JobNimbus."""
        raise CRMError("Pricebook equipment is not supported by JobNimbus", "NOT_SUPPORTED")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
