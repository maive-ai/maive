"""Simplified Rilla API client implementation."""

import httpx
from pydantic import ValidationError

from src.integrations.rilla.config import RillaSettings
from src.integrations.rilla.constants import RillaEndpoint
from src.integrations.rilla.exceptions import (
    RillaAPIError,
    RillaAuthenticationError,
    RillaBadRequestError,
    RillaRateLimitError,
    RillaServerError,
)
from src.integrations.rilla.schemas import (
    ConversationsExportRequest,
    ConversationsExportResponse,
    TeamsExportRequest,
    TeamsExportResponse,
    UsersExportRequest,
    UsersExportResponse,
)
from src.utils.logger import logger


class RillaClient:
    """Async client for Rilla API.

    Provides methods to export conversations, teams, and users data from Rilla.
    Handles authentication and error handling.
    """

    def __init__(self, settings: RillaSettings) -> None:
        """Initialize Rilla client.

        Args:
            settings: Rilla settings instance with API configuration
        """
        self.settings = settings
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.settings.base_url,
                headers={
                    "Authorization": self.settings.api_key,
                    "Content-Type": "application/json",
                },
                timeout=self.settings.timeout,
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self, method: str, endpoint: str, data: dict | None = None
    ) -> dict:
        """Make an HTTP request to the Rilla API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Optional request body data

        Returns:
            Response data as dictionary

        Raises:
            RillaAPIError: For various API errors
        """
        await self._ensure_client()

        try:
            response = await self._client.request(method, endpoint, json=data)

            # Handle error responses
            if response.status_code == 401:
                raise RillaAuthenticationError("Invalid API key")
            elif response.status_code == 400:
                raise RillaBadRequestError(f"Bad request: {response.text}")
            elif response.status_code == 429:
                raise RillaRateLimitError("Rate limit exceeded")
            elif response.status_code >= 500:
                raise RillaServerError(f"Server error: {response.status_code}")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise RillaAPIError(f"HTTP error: {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise RillaAPIError(f"Request error: {e}") from e
        except Exception as e:
            raise RillaAPIError(f"Unexpected error: {e}") from e

    async def export_conversations(
        self, request: ConversationsExportRequest
    ) -> ConversationsExportResponse:
        """Export conversations for a given time range.

        Args:
            request: Conversations export request parameters

        Returns:
            Conversations response with data

        Raises:
            RillaAPIError: For API errors
        """
        logger.info(
            f"Exporting conversations from {request.from_date} to {request.to_date}"
        )

        # Use Pydantic's serialization with aliases
        api_request = request.model_dump(by_alias=True, exclude_none=True, mode="json")

        response_data = await self._make_request(
            "POST", RillaEndpoint.CONVERSATIONS_EXPORT.value, api_request
        )

        try:
            return ConversationsExportResponse(**response_data)
        except ValidationError as e:
            logger.error("Failed to parse conversations response", error=str(e))
            raise RillaAPIError(f"Invalid response format: {e}") from e

    async def export_teams(self, request: TeamsExportRequest) -> TeamsExportResponse:
        """Export teams and their analytics for a given time range.

        Args:
            request: Teams export request parameters

        Returns:
            Teams response with analytics

        Raises:
            RillaAPIError: For API errors
        """
        logger.info(
            "Exporting teams",
            from_date=str(request.from_date),
            to_date=str(request.to_date),
        )

        # Use Pydantic's serialization with aliases
        api_request = request.model_dump(by_alias=True, exclude_none=True, mode="json")

        response_data = await self._make_request(
            "POST", RillaEndpoint.TEAMS_EXPORT.value, api_request
        )

        try:
            return TeamsExportResponse(**response_data)
        except ValidationError as e:
            logger.error("Failed to parse teams response", error=str(e))
            raise RillaAPIError(f"Invalid response format: {e}") from e

    async def export_users(self, request: UsersExportRequest) -> UsersExportResponse:
        """Export users and their analytics for a given time range.

        Args:
            request: Users export request parameters

        Returns:
            Users response with analytics

        Raises:
            RillaAPIError: For API errors
        """
        logger.info(
            "Exporting users",
            from_date=str(request.from_date),
            to_date=str(request.to_date),
        )

        # Use Pydantic's serialization with aliases
        api_request = request.model_dump(by_alias=True, exclude_none=True, mode="json")

        response_data = await self._make_request(
            "POST", RillaEndpoint.USERS_EXPORT.value, api_request
        )

        try:
            return UsersExportResponse(**response_data)
        except ValidationError as e:
            logger.error("Failed to parse users response", error=str(e))
            raise RillaAPIError(f"Invalid response format: {e}") from e
