"""
CRM service layer for business logic.

This module provides the business logic layer for CRM operations,
sitting between the FastAPI routes and the CRM providers.
"""

from src.integrations.crm.base import CRMError, CRMProvider
from src.integrations.crm.schemas import CRMErrorResponse, ProjectStatusListResponse, ProjectStatusResponse
from src.utils.logger import logger


class CRMService:
    """Service class for CRM operations."""

    def __init__(self, crm_provider: CRMProvider):
        """
        Initialize the CRM service.

        Args:
            crm_provider: The CRM provider to use
        """
        self.crm_provider = crm_provider

    async def get_project_status(self, project_id: str) -> ProjectStatusResponse | CRMErrorResponse:
        """
        Get the status of a specific project.

        Args:
            project_id: The project identifier

        Returns:
            ProjectStatusResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info(f"Getting status for project: {project_id}")
            result = await self.crm_provider.get_project_status(project_id)
            logger.info(f"Successfully retrieved status for project {project_id}: {result.status}")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting project {project_id}: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting project {project_id}: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )

    async def get_all_project_statuses(self) -> ProjectStatusListResponse | CRMErrorResponse:
        """
        Get the status of all projects.

        Returns:
            ProjectStatusListResponse or CRMErrorResponse: The result of the operation
        """
        try:
            logger.info("Getting status for all projects")
            result = await self.crm_provider.get_all_project_statuses()
            logger.info(f"Successfully retrieved status for {result.total_count} projects")
            return result
        except CRMError as e:
            logger.error(f"CRM error getting all projects: {e.message}")
            return CRMErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.crm_provider, 'provider_name', None)
            )
        except Exception as e:
            logger.error(f"Unexpected error getting all projects: {e}")
            return CRMErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR",
                provider=getattr(self.crm_provider, 'provider_name', None)
            )