"""
Rilla service layer for business logic.

This module provides the business logic layer for Rilla operations,
sitting between the FastAPI routes and the Rilla client.
"""

import asyncio
from datetime import datetime, timedelta

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

    async def export_all_conversations(self, request: ConversationsExportRequest) -> ConversationsExportResponse:
        """
        Export ALL conversations across all pages concurrently.

        Args:
            request: The conversation export request (page will be ignored)

        Returns:
            ConversationsExportResponse: All conversations from all pages
        """
        try:
            logger.info(f"Exporting ALL conversations from {request.from_date} to {request.to_date}")

            # First, get page 1 to determine total pages
            first_request = ConversationsExportRequest(
                from_date=request.from_date,
                to_date=request.to_date,
                users=request.users,
                date_type=request.date_type,
                page=1,
                limit=25,  # Use max limit
            )
            first_result = await self.rilla_client.export_conversations(first_request)

            logger.info(f"Found {first_result.total_conversations} conversations across {first_result.total_pages} pages")

            if first_result.total_pages <= 1:
                # Only one page, return as is
                return first_result

            # Create requests for remaining pages
            remaining_requests = []
            for page_num in range(2, first_result.total_pages + 1):
                page_request = ConversationsExportRequest(
                    from_date=request.from_date,
                    to_date=request.to_date,
                    users=request.users,
                    date_type=request.date_type,
                    page=page_num,
                    limit=25,
                )
                remaining_requests.append(page_request)

            # Execute all remaining page requests concurrently
            logger.info(f"Fetching {len(remaining_requests)} additional pages concurrently")
            remaining_tasks = [
                self.rilla_client.export_conversations(req) for req in remaining_requests
            ]
            remaining_results = await asyncio.gather(*remaining_tasks)

            # Combine all conversations
            all_conversations = list(first_result.conversations)
            for result in remaining_results:
                all_conversations.extend(result.conversations)

            logger.info(f"Successfully collected {len(all_conversations)} conversations from all pages")

            # Return combined result
            return ConversationsExportResponse(
                conversations=all_conversations,
                current_page=1,
                total_pages=1,
                total_conversations=len(all_conversations),
            )

        except Exception as e:
            logger.error(f"Error exporting all conversations: {e}")
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
        appointment_id: str | None,
        start_time: datetime,
        end_time: datetime,
        padding_hours: int = 0.1,
    ) -> ConversationsExportResponse:
        """
        Get Rilla conversations associated with a specific CRM appointment.

        Args:
            appointment_id: The CRM appointment/event ID (None to return all conversations in time range)
            start_time: Appointment start time
            end_time: Appointment end time
            padding_hours: Hours to pad the time range (default: 0.1)

        Returns:
            ConversationsExportResponse with conversations and pagination metadata.
            If appointment_id is provided, only matching conversations are included.
        """
        from_date = start_time - timedelta(hours=padding_hours)
        to_date = end_time + timedelta(hours=padding_hours)

        request = ConversationsExportRequest(
            from_date=from_date,
            to_date=to_date,
            users=None,
        )

        # Get ALL conversations across all pages
        response = await self.export_all_conversations(request)

        # Filter to conversations matching this specific appointment (if appointment_id provided)
        if appointment_id is not None:
            filtered_conversations = [
                conv for conv in response.conversations
                if conv.crm_event_id == appointment_id
            ]
            # Return filtered response (keep pagination metadata but update conversations)
            response.conversations = filtered_conversations
        
        return response
