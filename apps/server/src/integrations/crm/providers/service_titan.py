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
from src.integrations.crm.constants import ProjectStatus, ServiceTitanEndpoints
from src.integrations.crm.provider_schemas import CRMProviderDataFactory, FormSubmissionListResponse
from src.integrations.crm.schemas import (
    ProjectStatusListResponse,
    ProjectStatusResponse,
)
from src.utils.logger import logger


class ServiceTitanProvider(CRMProvider):
    """Service Titan implementation of the CRMProvider interface."""

    def __init__(self):
        """Initialize the Service Titan provider."""
        self.settings = get_crm_settings()

        # Configuration is validated in CRMSettings, so we can safely access these
        self.tenant_id = self.settings.tenant_id
        self.client_id = self.settings.client_id
        self.client_secret = self.settings.client_secret
        self.app_key = self.settings.app_key
        self.base_api_url = self.settings.base_api_url
        self.token_url = self.settings.token_url

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.settings.crm_request_timeout),
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
                headers={"Content-Type": "application/x-www-form-urlencoded"}
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

    async def get_appointment_status(self, appointment_id: str) -> ProjectStatusResponse:
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
                raise CRMError(f"Appointment with ID {appointment_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error fetching appointment {appointment_id}: {e}")
                raise CRMError(f"Failed to fetch appointment status: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching appointment {appointment_id}: {e}")
            raise CRMError(f"Failed to fetch appointment status: {str(e)}", "UNKNOWN_ERROR")

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

    async def get_job_status(self, job_id: str) -> ProjectStatusResponse:
        """
        Get the status of a specific job by ID from Service Titan.

        Args:
            job_id: The Service Titan job ID

        Returns:
            ProjectStatusResponse: The job status information

        Raises:
            CRMError: If the job is not found or an error occurs
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.JOB_BY_ID.format(tenant_id=self.tenant_id, id=job_id)}"

            logger.debug(f"Fetching job status for ID: {job_id}")

            response = await self._make_authenticated_request("GET", url)
            response.raise_for_status()

            data = response.json()

            # Transform Service Titan job data to our schema
            return self._transform_job_to_project_status(data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise CRMError(f"Job with ID {job_id} not found", "NOT_FOUND")
            else:
                logger.error(f"HTTP error fetching job {job_id}: {e}")
                raise CRMError(f"Failed to fetch job status: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching job {job_id}: {e}")
            raise CRMError(f"Failed to fetch job status: {str(e)}", "UNKNOWN_ERROR")

    async def get_all_job_statuses(self) -> ProjectStatusListResponse:
        """
        Get the status of all jobs from Service Titan.

        Returns:
            ProjectStatusListResponse: List of all job statuses

        Raises:
            CRMError: If an error occurs while fetching job statuses
        """
        try:
            url = f"{self.base_api_url}{ServiceTitanEndpoints.JOBS.format(tenant_id=self.tenant_id)}"

            logger.debug("Fetching all job statuses")

            response = await self._make_authenticated_request("GET", url)
            response.raise_for_status()

            data = response.json()

            # Debug: Log the actual response structure for jobs
            logger.info(f"Jobs endpoint response keys: {list(data.keys())}")
            logger.info(f"Jobs response sample: {str(data)[:500]}...")

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
            logger.error(f"HTTP error fetching all jobs: {e}")
            raise CRMError(f"Failed to fetch job statuses: {e}", "HTTP_ERROR")
        except Exception as e:
            logger.error(f"Unexpected error fetching all jobs: {e}")
            raise CRMError(
                f"Failed to fetch job statuses: {str(e)}", "UNKNOWN_ERROR"
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

    async def get_all_form_submissions(self, form_ids: list[int], status: str | None = None, owners: list[dict] | None = None) -> FormSubmissionListResponse:
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

            logger.debug(f"Fetching form submissions for form IDs {form_ids} with status: {status}, owners: {owners}")
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
        # Map Service Titan job status to our ProjectStatus enum
        service_titan_status = job_data.get("status", "")
        mapped_status = ProjectStatus.from_service_titan(service_titan_status)

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

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
