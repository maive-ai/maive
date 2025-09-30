"""
Rilla service layer for business logic.

This module provides the business logic layer for Rilla operations,
sitting between the FastAPI routes and the Rilla client.
"""

from datetime import datetime, timedelta

from src.integrations.rilla.client import RillaClient
from src.integrations.rilla.schemas import (
    Conversation,
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

    async def get_conversations_for_appointment(
        self,
        appointment_id: str,
        start_time: datetime,
        end_time: datetime,
        padding_hours: int = 0.1,
    ) -> list[Conversation]:
        """
        Get Rilla conversations associated with a specific CRM appointment.

        Args:
            appointment_id: The CRM appointment/event ID
            start_time: Appointment start time
            end_time: Appointment end time
            padding_hours: Hours to pad the time range (default: 1)

        Returns:
            List of conversations matching the appointment ID
        """
        from_date = start_time - timedelta(hours=padding_hours)
        to_date = end_time + timedelta(hours=padding_hours)

        request = ConversationsExportRequest(
            from_date=from_date,
            to_date=to_date,
            users=None,
        )

        response = await self.rilla_client.export_conversations(request)

        # Filter to conversations matching this specific appointment
        return [
            conv for conv in response.conversations
            if conv.crm_event_id == appointment_id
        ]
