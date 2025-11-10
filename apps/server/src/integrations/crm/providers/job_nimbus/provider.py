"""
JobNimbus CRM provider implementation.

This module implements the CRMProvider interface for JobNimbus,
handling API communication and data transformation.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import httpx

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.config import JobNimbusConfig, get_crm_settings
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.schemas import FormSubmissionListResponse
from src.integrations.crm.providers.job_nimbus.constants import JobNimbusEndpoints
from src.integrations.crm.providers.job_nimbus.schemas import (
    FileMetadata,
    JobNimbusActivitiesListResponse,
    JobNimbusActivityResponse,
    JobNimbusContactResponse,
    JobNimbusContactsListResponse,
    JobNimbusCreateActivityRequest,
    JobNimbusFilesListResponse,
    JobNimbusJobResponse,
    JobNimbusJobsListResponse,
)
from src.integrations.crm.schemas import (
    Contact,
    ContactList,
    EquipmentListResponse,
    EstimateResponse,
    Job,
    JobList,
    JobNoteResponse,
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

    async def _get_job_by_id(self, job_id: str) -> JobNimbusJobResponse:
        """
        Internal helper to fetch a single job from JobNimbus API.
        
        Args:
            job_id: The JobNimbus JNID
            
        Returns:
            JobNimbusJobResponse: Raw job data from API
            
        Raises:
            CRMError: If the job is not found or an error occurs
        """
        endpoint = JobNimbusEndpoints.JOB_BY_ID.format(jnid=job_id)
        logger.debug("Fetching job for JNID", job_id=job_id)
        
        response = await self._make_request("GET", endpoint)
        response.raise_for_status()
        
        data = response.json()
        return JobNimbusJobResponse(**data)

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
            jn_job = await self._get_job_by_id(job_id)
            
            # Transform to universal Job with contact details
            job = await self._transform_jn_job_to_universal_async(
                jn_job,
                include_contact_details=True,
            )
            
            # Fetch and attach notes
            job.notes = await self._get_job_notes(job_id)
            
            return job

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with JNID {job_id} not found", "NOT_FOUND")
            else:
                logger.error("HTTP error fetching job", job_id=job_id, error=str(e))
                raise CRMError(f"Failed to fetch job: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error("Unexpected error fetching job", job_id=job_id, error=str(e))
            raise CRMError(f"Failed to fetch job: {str(e)}", "UNKNOWN_ERROR")

    def _build_filter_query(self, filters: dict[str, Any]) -> dict[str, Any]:
        """
        Build a JobNimbus filter query from universal filter inputs.

        JobNimbus accepts an Elasticsearch-style filter JSON via the `filter` query parameter.
        """
        if not filters:
            return {}

        filter_query: dict[str, Any] = {"must": []}
        should_conditions: list[dict[str, Any]] = []

        customer_name = filters.get("customer_name")
        if customer_name:
            filter_query["must"].append(
                {"wildcard": {"primary.name": f"*{customer_name}*"}}
            )

        job_id = filters.get("job_id")
        if job_id:
            filter_query["must"].append({"term": {"jnid": job_id}})

        claim_number = filters.get("claim_number")
        if claim_number:
            filter_query["must"].append({"term": {"claim_number": claim_number}})

        status = filters.get("status")
        if status:
            filter_query["must"].append({"term": {"status_name": status}})

        address = filters.get("address")
        if address:
            address_fields = [
                "address_line1",
                "address_line2",
                "city",
                "state_text",
                "zip",
            ]
            should_conditions.extend(
                {"wildcard": {field: f"*{address}*"}} for field in address_fields
            )

        if should_conditions:
            filter_query["should"] = should_conditions
            filter_query["minimum_should_match"] = 1

        if not filter_query["must"] and "should" not in filter_query:
            # No valid filters translated
            return {}

        return filter_query

    async def _fetch_jobs_list(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> JobNimbusJobsListResponse:
        """
        Internal helper to fetch paginated jobs list from JobNimbus API.
        
        Args:
            filters: Optional dictionary of filters (for future server-side filtering)
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            JobNimbusJobsListResponse: Raw jobs list data from API
            
        Raises:
            CRMError: If the API request fails
        """
        logger.debug("Fetching jobs list from API", page=page, page_size=page_size, filters=filters)

        endpoint = JobNimbusEndpoints.JOBS
        
        # Convert page/page_size to JobNimbus from/size params
        # JobNimbus uses zero-based offset, we use 1-indexed pages
        from_offset = (page - 1) * page_size
        params = {
            "size": page_size,
            "from": from_offset,
        }

        api_filter = self._build_filter_query(filters or {})
        if api_filter:
            params["filter"] = json.dumps(api_filter)
        
        response = await self._make_request("GET", endpoint, params=params)
        response.raise_for_status()

        data = response.json()
        return JobNimbusJobsListResponse(**data)

    def _apply_client_filters(self, jobs: list[Job], filters: dict[str, Any]) -> list[Job]:
        """
        Apply client-side filtering to a list of jobs.
        
        Args:
            jobs: List of jobs to filter
            filters: Dictionary of filter criteria
            
        Returns:
            Filtered list of jobs
        """
        if not filters:
            return jobs
        
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
                job_claim = job.provider_data.get("claim_number") if job.provider_data else None
                if job_claim != filters["claim_number"]:
                    continue
            
            # Status filter (exact match)
            if "status" in filters:
                if job.status != filters["status"]:
                    continue
            
            filtered_jobs.append(job)
        
        return filtered_jobs

    async def _get_jobs_internal(
        self,
        filters: dict[str, Any] | None,
        page: int,
        page_size: int,
        include_contact_details: bool,
    ) -> tuple[list[Job], int, bool]:
        """
        Internal helper that fetches JobNimbus jobs and converts them to universal Job models.

        Args:
            filters: Optional dictionary of filters
            page: Page number (1-indexed)
            page_size: Number of items per page
            include_contact_details: Whether to fetch contact details for the primary contact

        Returns:
            tuple of (jobs list, total_count, has_more)
        """
        jn_jobs_list = await self._fetch_jobs_list(filters=filters, page=page, page_size=page_size)

        # Transform to universal Job schemas (async to optionally fetch contact details)
        jobs = await asyncio.gather(
            *[
                self._transform_jn_job_to_universal_async(jn_job, include_contact_details=include_contact_details)
                for jn_job in jn_jobs_list.results
            ]
        )

        # Apply client-side filtering if provided
        # TODO: Remove this once we are confident in the server-side filtering
        if filters:
            filtered_jobs = self._apply_client_filters(jobs, filters)
            if len(filtered_jobs) != len(jobs):
                jobs = filtered_jobs

        # Use API total count for pagination metadata. If client-side filtering reduced the dataset,
        # fall back to the filtered length since we don't know the total matches without server-side filtering.
        total_count = jn_jobs_list.count if filters is None or len(jobs) == len(jn_jobs_list.results) else len(jobs)

        from_offset = (page - 1) * page_size
        has_more = len(jn_jobs_list.results) == page_size and (from_offset + page_size) < total_count

        return jobs, total_count, has_more

    async def get_all_jobs(
        self,
        filters: dict[str, Any] | None = None,
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
        try:
            jobs, total_count, has_more = await self._get_jobs_internal(
                filters=filters,
                page=page,
                page_size=page_size,
                include_contact_details=False,
            )

            return JobList(
                jobs=jobs,
                total_count=total_count,
                provider=CRMProviderEnum.JOB_NIMBUS,
                page=page,
                page_size=page_size,
                has_more=has_more,
            )

        except Exception as e:
            logger.error("Error fetching all jobs", error=str(e))
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
        logger.info("Getting JobNimbus project", project_id=project_id)

        try:
            job = await self.get_job(project_id)
            return self._job_to_project(job)
        except CRMError as exc:
            raise CRMError(exc.message, exc.error_code) from exc

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
        logger.info("Getting all JobNimbus projects", page=page, page_size=page_size)

        try:
            jobs, total_count, has_more = await self._get_jobs_internal(
                filters=filters,
                page=page,
                page_size=page_size,
                include_contact_details=True,
            )

            projects = [self._job_to_project(job) for job in jobs]

            return ProjectList(
                projects=projects,
                total_count=total_count,
                provider=CRMProviderEnum.JOB_NIMBUS,
                page=page,
                page_size=page_size,
                has_more=has_more,
            )

        except Exception as e:
            logger.error("Error fetching all projects", error=str(e))
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

            logger.debug("Fetching contact for JNID", contact_id=contact_id)

            response = await self._make_request("GET", endpoint)
            response.raise_for_status()

            data = response.json()
            jn_contact = JobNimbusContactResponse(**data)

            return self._transform_jn_contact_to_universal(jn_contact)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Contact with JNID {contact_id} not found", "NOT_FOUND")
            else:
                logger.error("HTTP error fetching contact", contact_id=contact_id, error=str(e))
                raise CRMError(f"Failed to fetch contact: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error("Unexpected error fetching contact", contact_id=contact_id, error=str(e))
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
            logger.debug("Fetching all contacts", page=page, page_size=page_size)

            endpoint = JobNimbusEndpoints.CONTACTS
            
            # Convert page/page_size to JobNimbus from/size params
            from_offset = (page - 1) * page_size
            params = {
                "size": page_size,
                "from": from_offset,
            }
            
            response = await self._make_request("GET", endpoint, params=params)
            response.raise_for_status()

            data = response.json()
            jn_contacts_list = JobNimbusContactsListResponse(**data)

            # Transform to universal Contact schemas
            contacts = [
                self._transform_jn_contact_to_universal(jn_contact)
                for jn_contact in jn_contacts_list.results
            ]

            # Use API total count for accurate pagination metadata
            total_count = jn_contacts_list.count
            has_more = len(jn_contacts_list.results) == page_size and (from_offset + page_size) < total_count

            return ContactList(
                contacts=contacts,
                total_count=total_count,
                provider=CRMProviderEnum.JOB_NIMBUS,
                page=page,
                page_size=page_size,
                has_more=has_more,
            )

        except Exception as e:
            logger.error("Error fetching all contacts", error=str(e))
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
            logger.info("Adding note to entity", entity_type=entity_type, entity_id=entity_id)

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
            logger.error("Error adding note to entity", entity_type=entity_type, entity_id=entity_id, error=str(e))
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
        logger.info("Updating JobNimbus job status", job_id=job_id, status=status)

        # JobNimbus requires updating via PATCH with status_name
        try:
            endpoint = JobNimbusEndpoints.JOB_BY_ID.format(jnid=job_id)

            # Build update payload
            update_data = {"statusName": status}
            if "status_id" in kwargs:
                update_data["status"] = kwargs["status_id"]

            response = await self._make_request("PATCH", endpoint, json=update_data)
            response.raise_for_status()

            logger.info("Successfully updated job status", job_id=job_id)

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
        logger.info("Updating JobNimbus project status", project_id=project_id, status=status)
        await self.update_job_status(project_id, status, **kwargs)

    # ========================================================================
    # Helper Methods (transformation functions)
    # ========================================================================

    async def _get_job_notes(self, job_id: str) -> list[Note]:
        """
        Fetch activities (notes) for a specific job.
        
        Args:
            job_id: The job ID (JNID)
            
        Returns:
            list[Note]: List of notes for the job (empty list if none or on error)
        """
        try:
            logger.info("Fetching notes for job", job_id=job_id)
            
            # Build filter to get activities related to this job
            filter_query = json.dumps({
                "must": [{"term": {"related.id": job_id}}]
            })
            
            # Request activities from JobNimbus API
            endpoint = f"{JobNimbusEndpoints.ACTIVITIES}?filter={filter_query}"
            response = await self._make_request("GET", endpoint)
            response.raise_for_status()
            
            data = response.json()
                        
            # Parse activities list response
            activities_response = JobNimbusActivitiesListResponse(**data)
            
            # Transform each activity to universal Note
            notes = []
            for jn_activity in activities_response.results:
                try:
                    # Only include note-type activities (filter by record_type_name, not type)
                    if jn_activity.record_type_name == "Note":
                        note = Note(
                            id=jn_activity.jnid,
                            text=jn_activity.note or "",
                            entity_id=job_id,
                            entity_type="job",
                            created_by_id=jn_activity.created_by,
                            created_by_name=jn_activity.created_by_name,
                            created_at=self._unix_timestamp_to_datetime(jn_activity.date_created).isoformat(),
                            updated_at=self._unix_timestamp_to_datetime(jn_activity.date_updated).isoformat()
                            if jn_activity.date_updated
                            else None,
                            is_pinned=False,
                            provider=CRMProviderEnum.JOB_NIMBUS,
                            provider_data={
                                "record_type": jn_activity.record_type,
                                "record_type_name": jn_activity.record_type_name,
                            },
                        )
                        notes.append(note)
                except Exception as e:
                    logger.warning("Failed to parse activity for job", job_id=job_id, error=str(e))
                    continue
            
            logger.info("Fetched notes for job", job_id=job_id, note_count=len(notes))
            return notes
            
        except Exception as e:
            logger.warning("Error fetching notes for job", job_id=job_id, error=str(e))
            return []  # Return empty list on error - don't fail the job fetch

    # ========================================================================
    # File/Attachment Methods
    # ========================================================================

    async def get_specific_job_file(
        self, 
        job_id: str, 
        file_id: str
    ) -> FileMetadata | None:
        """
        Get a specific file by ID from a job.
        
        Helper method that retrieves all files for a job and returns the one
        matching the specified file_id.
        
        Args:
            job_id: The job JNID to get the file from
            file_id: The specific file ID to retrieve
            
        Returns:
            FileMetadata object if found, None if not found
        """
        # Get all files and find the specific one
        all_files = await self.get_job_files(job_id, "all")
        matching_files = [f for f in all_files if f.id == file_id]
        if not matching_files:
            logger.error("File not found in job", file_id=file_id, job_id=job_id)
            return None
        return matching_files[0]


    async def get_job_files(self, job_id: str, file_filter: str = "all") -> list[FileMetadata]:
        """
        Get files attached to a specific job with optional type filtering.
        
        Uses the 'related' query parameter to filter files server-side by job.
        Applies additional client-side filtering by file type if requested.
        
        Args:
            job_id: The job JNID to get files for
            file_filter: Filter by type - "all", "images", or "pdfs" (default: "all")
            
        Returns:
            List of file metadata objects (filtered by type if specified)
            
        Raises:
            CRMError: If the API request fails
        """
        try:
            endpoint = JobNimbusEndpoints.FILES
            params = {"related": job_id}
            logger.info("[JobNimbus] Fetching files for job", job_id=job_id, file_filter=file_filter)
            
            response = await self._make_request("GET", endpoint, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            files_response = JobNimbusFilesListResponse(**data)
            
            # Transform to FileMetadata objects
            all_files: list[FileMetadata] = []
            for file in files_response.results:
                all_files.append(
                    FileMetadata(
                        id=file.jnid,
                        filename=file.filename,
                        content_type=file.content_type,
                        size=file.size,
                        record_type_name=file.record_type_name,
                        description=file.description,
                        date_created=file.date_created,
                        created_by_name=file.created_by_name,
                        is_private=file.is_private,
                    )
                )
            
            # Apply client-side filtering by type
            if file_filter == "images":
                filtered_files = [f for f in all_files if f.content_type.startswith("image/")]
            elif file_filter == "pdfs":
                filtered_files = [f for f in all_files if f.content_type == "application/pdf"]
            else:  # "all"
                filtered_files = all_files
            
            logger.info("[JobNimbus] Found files for job", job_id=job_id, file_filter=file_filter, file_count=len(filtered_files))
            return filtered_files
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error fetching files for job", job_id=job_id, error=str(e))
            raise CRMError(
                f"Failed to fetch files: {e.response.status_code}",
                "API_ERROR"
            )
        except Exception as e:
            logger.error("Error fetching files for job", job_id=job_id, error=str(e))
            raise CRMError(f"Failed to fetch files: {str(e)}", "UNKNOWN_ERROR")

    async def download_file(
        self, 
        file_id: str, 
        filename: str | None = None, 
        content_type: str | None = None
    ) -> tuple[bytes, str, str]:
        """
        Download a file's content from JobNimbus.
        
        Args:
            file_id: The file JNID to download
            filename: Filename from file metadata
            content_type: Content type from file metadata
            
        Returns:
            Tuple of (file_content_bytes, filename, content_type)
            
        Raises:
            CRMError: If the download fails
        """
        try:
            endpoint = JobNimbusEndpoints.FILE_BY_ID.format(jnid=file_id)
            logger.info("[JobNimbus] Downloading file", file_id=file_id)
            
            # JobNimbus returns a 302 redirect to the actual file on CloudFront/S3
            response = await self._make_request("GET", endpoint, follow_redirects=True)
            response.raise_for_status()
            
            # Use provided metadata or fallback to defaults
            resolved_filename = filename or f"download_{file_id}"
            resolved_content_type = content_type or "application/octet-stream"
            
            logger.info("[JobNimbus] Downloaded file", filename=resolved_filename, size_bytes=len(response.content))
            return (response.content, resolved_filename, resolved_content_type)
            
        except httpx.HTTPStatusError as e:
            logger.error("[JobNimbus] HTTP error downloading file", file_id=file_id, error=str(e))
            raise CRMError(f"Failed to download file: {e.response.status_code}", "API_ERROR")
        except Exception as e:
            logger.error("[JobNimbus] Error downloading file", file_id=file_id, error=str(e))
            raise CRMError(f"Failed to download file: {str(e)}", "UNKNOWN_ERROR")

    # ========================================================================
    # Pagination Helper Methods
    # ========================================================================

    async def get_jobs_bulk(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 1000,
        start_offset: int = 0,
        include_contact_details: bool = False,
    ) -> tuple[list[Job], int, int | None, bool]:
        """
        Fetch jobs in bulk with offset-based pagination support.

        Args:
            filters: Optional dictionary of filters (same as get_all_jobs)
            limit: Maximum number of jobs to retrieve (must be positive)
            start_offset: Zero-based offset to start from (default: 0)
            include_contact_details: Whether to fetch contact details (default: False)

        Returns:
            Tuple of (jobs list, total_count, next_offset, has_more)
        """
        if limit <= 0:
            return [], 0, None, False

        target_items = limit + max(start_offset, 0)

        jobs, total_count = await self._paginate_jobs(
            filters=filters,
            max_items=target_items,
            page_size=1000,
            include_contact_details=include_contact_details,
        )

        # Apply offset and limit slicing
        if start_offset > 0:
            jobs = jobs[start_offset:]
        jobs = jobs[:limit]

        returned_count = len(jobs)
        next_offset = None
        if start_offset + returned_count < total_count:
            next_offset = start_offset + returned_count

        has_more = next_offset is not None
        return jobs, total_count, next_offset, has_more

    async def _paginate_jobs(
        self,
        filters: dict[str, Any] | None = None,
        max_items: int | None = None,
        page_size: int = 1000,
        include_contact_details: bool = False,
    ) -> tuple[list[Job], int]:
        """
        Iteratively fetch all jobs across multiple pages until exhaustion or max_items is reached.
        
        This helper is used internally when consumers need to fetch more than one page
        of results, such as bulk operations or when limit exceeds JobNimbus's max page size.
        
        Args:
            filters: Optional dictionary of filters (same as get_all_jobs)
            max_items: Maximum number of items to fetch (None = fetch all)
            page_size: Number of items per page (default: 1000, JobNimbus max)
            include_contact_details: Whether to fetch contact details (default: False)
            
        Returns:
            Tuple of (jobs, total_count)

        Raises:
            CRMError: If pagination fails
        """
        all_jobs: list[Job] = []
        page = 1
        fetched_count = 0
        total_count = 0
        
        try:
            while True:
                # Check if we've hit the max_items limit
                if max_items is not None and fetched_count >= max_items:
                    break

                # Calculate how many items to request this page
                remaining = max_items - fetched_count if max_items else None
                current_page_size = min(page_size, remaining) if remaining else page_size
                if current_page_size <= 0:
                    break

                logger.debug("[JobNimbus] Fetching paginated jobs", page=page, page_size=current_page_size, fetched_so_far=len(all_jobs))
                
                # Fetch current page
                jobs, total_count, has_more = await self._get_jobs_internal(
                    filters=filters,
                    page=page,
                    page_size=current_page_size,
                    include_contact_details=include_contact_details,
                )
                
                # Add jobs to our collection
                all_jobs.extend(jobs)
                fetched_count += len(jobs)

                # Log progress every 10 pages
                if page % 10 == 0:
                    logger.info("[JobNimbus] Pagination progress", page=page, total_fetched=len(all_jobs), has_more=has_more)
                
                # Stop if no more results or we got fewer results than requested
                if not has_more or len(jobs) < current_page_size:
                    break
                
                # Stop if we've reached max_items
                if max_items is not None and fetched_count >= max_items:
                    # Trim to exact max_items if we went over
                    all_jobs = all_jobs[:max_items]
                    break
                
                page += 1

            logger.info("[JobNimbus] Pagination complete", total_pages=page, total_jobs=len(all_jobs), total_count=total_count)

        except Exception as e:
            logger.error("[JobNimbus] Error during pagination", error=str(e), fetched_so_far=len(all_jobs))
            raise CRMError(f"Failed to paginate jobs: {str(e)}", "UNKNOWN_ERROR")
        
        return all_jobs, total_count

    # ========================================================================
    # Transformation Methods
    # ========================================================================

    async def _transform_jn_job_to_universal_async(
        self,
        jn_job: JobNimbusJobResponse,
        include_contact_details: bool = False,
    ) -> Job:
        """Async transformation to universal Job schema with optional contact enrichment."""
        # Gather raw data for provider_data enrichment
        all_data = jn_job.model_dump(mode="json")

        claim_number = jn_job.claim_number
        insurance_company = jn_job.insurance_company
        date_of_loss = (
            self._unix_timestamp_to_datetime(jn_job.filed_storm_date).isoformat()
            if jn_job.filed_storm_date
            else None
        )

        adjuster_name = self._extract_custom_field(all_data, ["adjustername", "adjuster"])
        adjuster_phone = self._extract_custom_field(
            all_data, ["adjusterphone", "adjusterphoneno", "adjustercontact"]
        )
        adjuster_email = self._extract_custom_field(
            all_data, ["adjusteremail", "adjusteremailaddress"]
        )

        customer_phone = None
        customer_email = None

        if include_contact_details and jn_job.primary and jn_job.primary.id:
            try:
                contact = await self.get_contact(jn_job.primary.id)
                customer_email = contact.email
                customer_phone = contact.phone or contact.mobile_phone or contact.work_phone
                logger.debug(
                    "[JobNimbus] Fetched contact",
                    contact_id=jn_job.primary.id,
                    phone=customer_phone,
                    email=customer_email,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[JobNimbus] Failed to fetch contact",
                    contact_id=jn_job.primary.id,
                    error=str(exc),
                )

        provider_data: dict[str, Any] = {
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
        }

        provider_data.update(
            {
                "claim_number": claim_number,
                "insurance_company": insurance_company,
                "insuranceAgency": insurance_company,
                "date_of_loss": date_of_loss,
                "customer_phone": customer_phone,
                "customer_email": customer_email,
                "adjusterContact": {
                    "name": adjuster_name,
                    "phone": adjuster_phone,
                    "email": adjuster_email,
                },
            }
        )

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
            provider_data=provider_data,
        )

    def _extract_custom_field(
        self, all_data: dict[str, Any], possible_names: list[str]
    ) -> Any:
        """Extract a custom field value by checking multiple possible field names.

        Args:
            all_data: All fields from JobNimbus job
            possible_names: List of possible normalized field names to check

        Returns:
            The field value if found, None otherwise
        """
        for key, value in all_data.items():
            # Normalize the key by removing spaces, underscores, and special chars
            normalized_key = key.lower().replace(" ", "").replace("_", "").replace("#", "")
            if normalized_key in possible_names and value:
                return value
        return None

    def _job_to_project(self, job: Job) -> Project:
        """Convert a universal Job into a universal Project representation."""
        provider_data = job.provider_data or {}
        adjuster_contact = provider_data.get("adjusterContact") or {}
        location = provider_data.get("location") or {}

        location_id = location.get("id") if isinstance(location, dict) else None
        if location_id is not None:
            location_id = str(location_id)

        return Project(
            id=job.id,
            name=job.name,
            number=job.number,
            status=job.status,
            status_id=job.status_id,
            sub_status=None,
            sub_status_id=None,
            workflow_type=job.workflow_type,
            description=job.description,
            customer_id=job.customer_id,
            customer_name=job.customer_name,
            location_id=location_id,
            address_line1=job.address_line1,
            address_line2=job.address_line2,
            city=job.city,
            state=job.state,
            postal_code=job.postal_code,
            country=job.country,
            created_at=job.created_at,
            updated_at=job.updated_at,
            start_date=None,
            target_completion_date=None,
            actual_completion_date=None,
            claim_number=provider_data.get("claim_number"),
            date_of_loss=provider_data.get("date_of_loss"),
            insurance_company=provider_data.get("insurance_company") or provider_data.get("insuranceAgency"),
            adjuster_name=adjuster_contact.get("name"),
            adjuster_phone=adjuster_contact.get("phone"),
            adjuster_email=adjuster_contact.get("email"),
            sales_rep_id=job.sales_rep_id,
            sales_rep_name=job.sales_rep_name,
            provider=job.provider,
            provider_data=provider_data,
            notes=job.notes,
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

            logger.debug("Fetching job status for JNID", project_id=project_id)

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
                logger.error("HTTP error fetching job status", project_id=project_id, error=str(e))
                raise CRMError(f"Failed to fetch job status: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error("Unexpected error fetching job status", project_id=project_id, error=str(e))
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
            logger.error("HTTP error fetching all jobs", error=str(e))
            raise CRMError(f"Failed to fetch job statuses: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error("Unexpected error fetching all jobs", error=str(e))
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

            logger.debug("Adding note to job", job_id=jnid)

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
                logger.error("HTTP error adding note to job", job_id=job_id, error=str(e))
                raise CRMError(f"Failed to add note to job: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error("Unexpected error adding note to job", job_id=job_id, error=str(e))
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
