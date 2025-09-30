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
            url = f"{self.base_api_url}{ServiceTitanEndpoints.PROJECT_BY_ID.format(tenant_id=self.tenant_id, appointment_id=project_id)}"

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

            # Service Titan returns data in a "data" field with pagination info
            jobs = data.get("data", [])
            total_count = data.get("totalCount", len(jobs))

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
        service_titan_status = job_data.get("jobStatus", {}).get("name", "").lower()

        # Map Service Titan statuses to our enum
        # Service Titan statuses: Scheduled, Dispatched, Working, Hold, Done, Canceled
        status_mapping = {
            "scheduled": ProjectStatus.SCHEDULED,
            "dispatched": ProjectStatus.ACTIVE,  # Dispatched jobs are active/in progress
            "working": ProjectStatus.IN_PROGRESS,
            "hold": ProjectStatus.ON_HOLD,
            "done": ProjectStatus.COMPLETED,
            "canceled": ProjectStatus.CANCELLED,
        }

        mapped_status = status_mapping.get(service_titan_status, ProjectStatus.ACTIVE)

        # Extract update timestamp
        updated_at = None
        if job_data.get("modifiedOn"):
            try:
                updated_at = datetime.fromisoformat(
                    job_data["modifiedOn"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                updated_at = datetime.now(UTC)

        return ProjectStatusResponse(
            project_id=str(job_data.get("id", "")),
            status=mapped_status,
            provider=CRMProviderEnum.SERVICE_TITAN,
            updated_at=updated_at,
            provider_data={
                "job_number": job_data.get("jobNumber"),
                "customer_id": job_data.get("customerId"),
                "location_id": job_data.get("locationId"),
                "job_type": job_data.get("jobType", {}).get("name"),
                "priority": job_data.get("priority", {}).get("name"),
                "original_status": service_titan_status,
            },
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
