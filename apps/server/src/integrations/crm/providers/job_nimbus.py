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
from src.integrations.crm.constants import JobNimbusEndpoints
from src.integrations.crm.provider_schemas import FormSubmissionListResponse
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
from src.integrations.crm.schemas_jobnimbus import (
    JobNimbusActivityResponse,
    JobNimbusContactResponse,
    JobNimbusContactsListResponse,
    JobNimbusCreateActivityRequest,
    JobNimbusCreateContactRequest,
    JobNimbusJobResponse,
    JobNimbusJobsListResponse,
    JobNimbusUpdateContactRequest,
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

    async def get_job(self, job_id: int) -> JobResponse:
        """
        Get a specific job by JNID from JobNimbus.

        Note: JobNimbus uses string JNIDs, not integer IDs.
        The job_id parameter will be treated as a string.

        Args:
            job_id: The JobNimbus JNID (will be converted to string)

        Returns:
            JobResponse: The job information

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        try:
            jnid = str(job_id)
            endpoint = JobNimbusEndpoints.JOB_BY_ID.format(jnid=jnid)

            logger.debug(f"Fetching job for JNID: {jnid}")

            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()

            # Parse as JobNimbus job response
            jn_job = JobNimbusJobResponse(**data)

            # Transform to our generic JobResponse schema
            # Note: We're adapting JobNimbus structure to Service Titan's JobResponse
            # This is a temporary solution until we refactor to universal schemas
            return JobResponse(
                id=jn_job.recid or 0,  # Use recid as ID, default to 0 if None
                jobNumber=jn_job.number or jn_job.jnid,
                projectId=None,  # JobNimbus doesn't have separate projects
                customerId=0,  # Would need to look up from related contacts
                locationId=jn_job.location.id if jn_job.location else 0,
                jobStatus=jn_job.status_name or "Unknown",
                completedOn=None,  # JobNimbus doesn't have explicit completion date
                businessUnitId=jn_job.location.id if jn_job.location else 0,
                jobTypeId=jn_job.record_type,
                priority="Normal",  # JobNimbus doesn't have priority field
                campaignId=jn_job.source or 0,
                appointmentCount=0,  # Not available in JobNimbus
                firstAppointmentId=0,
                lastAppointmentId=0,
                recallForId=None,
                warrantyId=None,
                noCharge=False,
                notificationsEnabled=True,
                createdOn=self._unix_timestamp_to_datetime(jn_job.date_created),
                createdById=0,  # Would need to look up user
                modifiedOn=self._unix_timestamp_to_datetime(jn_job.date_updated),
                tagTypeIds=[],
                customerPo=None,
                invoiceId=None,
                total=None,
                summary=jn_job.description,
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with JNID {job_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error fetching job {job_id}: {e}")
                raise CRMError(f"Failed to fetch job: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching job {job_id}: {e}")
            raise CRMError(f"Failed to fetch job: {str(e)}", "UNKNOWN_ERROR")

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

    # JobNimbus-specific contact methods

    async def get_contact(self, contact_id: str) -> JobNimbusContactResponse:
        """
        Get a specific contact by JNID from JobNimbus.

        Args:
            contact_id: The JobNimbus contact JNID

        Returns:
            JobNimbusContactResponse: The contact information

        Raises:
            CRMError: If the contact is not found or an error occurs
        """
        try:
            endpoint = JobNimbusEndpoints.CONTACT_BY_ID.format(jnid=contact_id)

            logger.debug(f"Fetching contact for JNID: {contact_id}")

            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()

            # Parse as JobNimbus contact response
            return JobNimbusContactResponse(**data)

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
        self, filters: dict[str, Any] | None = None
    ) -> JobNimbusContactsListResponse:
        """
        Get all contacts from JobNimbus with optional filters.

        Args:
            filters: Optional ElasticSearch-style filter object

        Returns:
            JobNimbusContactsListResponse: List of contacts

        Raises:
            CRMError: If an error occurs while fetching contacts
        """
        try:
            endpoint = JobNimbusEndpoints.CONTACTS

            logger.debug("Fetching all contacts")

            # Default pagination parameters
            params = {
                "size": 1000,
                "from": 0,
                "sort_field": "date_created",
                "sort_direction": "desc",
            }

            # Add filter if provided
            if filters:
                params["filter"] = json.dumps(filters)

            response = await self._make_request("GET", endpoint, params=params)
            response.raise_for_status()

            data = response.json()

            # Parse as JobNimbus contacts list response
            return JobNimbusContactsListResponse(**data)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching contacts: {e}")
            raise CRMError(f"Failed to fetch contacts: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching contacts: {e}")
            raise CRMError(f"Failed to fetch contacts: {str(e)}", "UNKNOWN_ERROR")

    async def create_contact(
        self, request: JobNimbusCreateContactRequest
    ) -> JobNimbusContactResponse:
        """
        Create a new contact in JobNimbus.

        Args:
            request: Contact creation request

        Returns:
            JobNimbusContactResponse: The created contact

        Raises:
            CRMError: If an error occurs while creating the contact
        """
        try:
            endpoint = JobNimbusEndpoints.CONTACTS

            logger.debug("Creating new contact")

            response = await self._make_request(
                "POST",
                endpoint,
                json=request.model_dump(by_alias=True, exclude_none=True),
            )
            response.raise_for_status()

            data = response.json()

            # Parse as JobNimbus contact response
            return JobNimbusContactResponse(**data)

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(f"HTTP error creating contact: {error_body}")
            raise CRMError(f"Failed to create contact: {error_body}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error creating contact: {e}")
            raise CRMError(f"Failed to create contact: {str(e)}", "UNKNOWN_ERROR")

    async def update_contact(
        self, contact_id: str, request: JobNimbusUpdateContactRequest
    ) -> JobNimbusContactResponse:
        """
        Update an existing contact in JobNimbus.

        Args:
            contact_id: The contact JNID
            request: Contact update request

        Returns:
            JobNimbusContactResponse: The updated contact

        Raises:
            CRMError: If the contact is not found or an error occurs
        """
        try:
            endpoint = JobNimbusEndpoints.CONTACT_BY_ID.format(jnid=contact_id)

            logger.debug(f"Updating contact {contact_id}")

            response = await self._make_request(
                "PUT",
                endpoint,
                json=request.model_dump(by_alias=True, exclude_none=True),
            )
            response.raise_for_status()

            data = response.json()

            # Parse as JobNimbus contact response
            return JobNimbusContactResponse(**data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Contact with JNID {contact_id} not found", "NOT_FOUND")
            else:
                error_body = e.response.text
                logger.error(f"HTTP error updating contact {contact_id}: {error_body}")
                raise CRMError(f"Failed to update contact: {error_body}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error updating contact {contact_id}: {e}")
            raise CRMError(f"Failed to update contact: {str(e)}", "UNKNOWN_ERROR")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
