"""
Rilla service layer for business logic.

This module provides the business logic layer for Rilla operations,
sitting between the FastAPI routes and the Rilla client.
"""

from src.integrations.rilla.client import RillaClient
from src.integrations.rilla.schemas import (
    ConversationsExportRequest,
    ConversationsExportResponse,
    TeamsExportRequest,
    TeamsExportResponse,
    UsersExportRequest,
    UsersExportResponse,
)
from src.utils.logger import logger


class RillaService:
    """Service class for Rilla operations."""

    def __init__(self, rilla_client: RillaClient):
        """
        Initialize the Rilla service.

        Args:
            rilla_client: The Rilla client to use
        """
        self.rilla_client = rilla_client

    async def export_conversations(self, request: ConversationsExportRequest) -> ConversationsExportResponse:
        """
        Export conversations with business logic.

        Args:
            request: The conversation export request

        Returns:
            ConversationsExportResponse: The exported conversations data
        """
        try:
            logger.info(f"Exporting conversations from {request.from_date} to {request.to_date}")
            result = await self.rilla_client.export_conversations(request)
            logger.info(f"Successfully exported {len(result.conversations)} conversations")
            return result
        except Exception as e:
            logger.error(f"Error exporting conversations: {e}")
            raise

    async def export_teams(self, request: TeamsExportRequest) -> TeamsExportResponse:
        """
        Export teams with business logic.

        Args:
            request: The team export request

        Returns:
            TeamsExportResponse: The exported teams data
        """
        try:
            logger.info(f"Exporting teams from {request.from_date} to {request.to_date}")
            result = await self.rilla_client.export_teams(request)
            logger.info(f"Successfully exported {len(result.teams)} teams")
            return result
        except Exception as e:
            logger.error(f"Error exporting teams: {e}")
            raise

    async def export_users(self, request: UsersExportRequest) -> UsersExportResponse:
        """
        Export users with business logic.

        Args:
            request: The user export request

        Returns:
            UsersExportResponse: The exported users data
        """
        try:
            logger.info(f"Exporting users from {request.from_date} to {request.to_date}")
            result = await self.rilla_client.export_users(request)
            logger.info(f"Successfully exported {len(result.users)} users")
            return result
        except Exception as e:
            logger.error(f"Error exporting users: {e}")
            raise
