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

            # Transform to universal Job
            job = self._transform_jn_job_to_universal(jn_job)
            
            # Fetch and attach notes
            job.notes = await self._get_job_notes(job_id)
            
            return job

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
            logger.debug(f"Fetching all jobs (page={page}, size={page_size}, filters={filters})")

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
                        job_claim = job.provider_data.get("claim_number") if job.provider_data else None
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

            # Transform to universal Project
            project = await self._transform_jn_job_to_universal_project_async(jn_job)
            
            # Fetch and attach notes
            project.notes = await self._get_job_notes(project_id)
            
            return project

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

            # Transform to universal Project schemas (using async to fetch contact details)
            projects = await asyncio.gather(*[
                self._transform_jn_job_to_universal_project_async(jn_job)
                for jn_job in jn_jobs_list.results
            ])

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

    async def _get_job_notes(self, job_id: str) -> list[Note]:
        """
        Fetch activities (notes) for a specific job.
        
        Args:
            job_id: The job ID (JNID)
            
        Returns:
            list[Note]: List of notes for the job (empty list if none or on error)
        """
        try:
            logger.info(f"Fetching notes for job {job_id}")
            
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
                    logger.warning(f"Failed to parse activity for job {job_id}: {e}")
                    continue
            
            logger.info(f"Fetched {len(notes)} notes for job {job_id}")
            return notes
            
        except Exception as e:
            logger.warning(f"Error fetching notes for job {job_id}: {e}")
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
            logger.error(f"File {file_id} not found in job {job_id}")
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
            logger.info(f"[JobNimbus] Fetching files for job {job_id} with filter: {file_filter}")
            
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
            
            logger.info(f"[JobNimbus] Found {len(filtered_files)} {file_filter} file(s) for job {job_id}")
            return filtered_files
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching files for job {job_id}: {e}")
            raise CRMError(
                f"Failed to fetch files: {e.response.status_code}",
                "API_ERROR"
            )
        except Exception as e:
            logger.error(f"Error fetching files for job {job_id}: {e}")
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
            logger.info(f"[JobNimbus] Downloading file {file_id}")
            
            # JobNimbus returns a 302 redirect to the actual file on CloudFront/S3
            response = await self._make_request("GET", endpoint, follow_redirects=True)
            response.raise_for_status()
            
            # Use provided metadata or fallback to defaults
            resolved_filename = filename or f"download_{file_id}"
            resolved_content_type = content_type or "application/octet-stream"
            
            logger.info(f"[JobNimbus] Downloaded {resolved_filename} ({len(response.content)} bytes)")
            return (response.content, resolved_filename, resolved_content_type)
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[JobNimbus] HTTP error downloading file {file_id}: {e}")
            raise CRMError(f"Failed to download file: {e.response.status_code}", "API_ERROR")
        except Exception as e:
            logger.error(f"[JobNimbus] Error downloading file {file_id}: {e}")
            raise CRMError(f"Failed to download file: {str(e)}", "UNKNOWN_ERROR")

    # ========================================================================
    # Transformation Methods
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

    async def _transform_jn_job_to_universal_project_async(self, jn_job: JobNimbusJobResponse) -> Project:
        """Async version that fetches primary contact details for email."""
        # Get all fields from the JobNimbus job, including custom fields
        all_data = jn_job.model_dump(mode="json")

        # Extract typed custom fields directly from schema
        claim_number = jn_job.claim_number
        insurance_company = jn_job.insurance_company
        
        # Convert filed storm date to ISO format for date_of_loss
        date_of_loss = None
        if jn_job.filed_storm_date:
            date_of_loss = self._unix_timestamp_to_datetime(jn_job.filed_storm_date).isoformat()

        # Extract primary contact info
        customer_name = jn_job.primary.name if jn_job.primary else None
        customer_phone = None
        customer_email = None

        # Fetch primary contact details to get email and phone
        if jn_job.primary and jn_job.primary.id:
            try:
                contact = await self.get_contact(jn_job.primary.id)
                customer_email = contact.email
                customer_phone = contact.phone or contact.mobile_phone or contact.work_phone
                logger.debug(f"[JobNimbus] Fetched contact {jn_job.primary.id} - phone: {customer_phone}, email: {customer_email}")
            except Exception as e:
                logger.warning(f"[JobNimbus] Failed to fetch contact {jn_job.primary.id}: {e}")

        # Extract adjuster information (fallback to _extract_custom_field for fields not in typed schema)
        adjuster_name = self._extract_custom_field(
            all_data, ["adjustername", "adjuster"]
        )
        adjuster_phone = self._extract_custom_field(
            all_data, ["adjusterphone", "adjusterphoneno", "adjustercontact"]
        )
        adjuster_email = self._extract_custom_field(
            all_data, ["adjusteremail", "adjusteremailaddress"]
        )

        # Store contact info in provider_data for frontend access
        all_data["customer_phone"] = customer_phone
        all_data["customer_email"] = customer_email
        all_data["insuranceAgency"] = insurance_company
        all_data["adjusterContact"] = {
            "name": adjuster_name,
            "phone": adjuster_phone,
            "email": adjuster_email,
        }

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
            customer_name=customer_name,
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
            claim_number=claim_number,
            date_of_loss=date_of_loss,
            insurance_company=insurance_company,
            adjuster_name=adjuster_name,
            adjuster_phone=adjuster_phone,
            adjuster_email=adjuster_email,
            sales_rep_id=jn_job.sales_rep,
            sales_rep_name=jn_job.sales_rep_name,
            provider=CRMProviderEnum.JOB_NIMBUS,
            provider_data=all_data,  # Includes all fields including custom fields
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
