"""Main Rilla API client implementation."""

import asyncio
import contextlib
import logging
from typing import Any

import httpx
from pydantic import ValidationError

from .config import RillaSettings, get_rilla_settings
from .exceptions import (
    RillaAPIError,
    RillaAuthenticationError,
    RillaBadRequestError,
    RillaConnectionError,
    RillaRateLimitError,
    RillaServerError,
    RillaTimeoutError,
)
from .models import (
    Conversation,
    ConversationsExportRequest,
    ConversationsExportResponse,
    TeamsExportRequest,
    TeamsExportResponse,
    UsersExportRequest,
    UsersExportResponse,
)

logger = logging.getLogger(__name__)


class RillaClient:
    """Async client for Rilla API.

    Provides methods to export conversations, teams, and users data from Rilla.
    Handles authentication, retries, rate limiting, and error handling.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        settings: RillaSettings | None = None,
    ) -> None:
        """Initialize Rilla client.

        Args:
            api_key: API key for authentication. If not provided, will use RILLA_API_KEY env var
            base_url: Base URL for API. If not provided, will use default or RILLA_BASE_URL env var
            settings: Custom settings instance. If not provided, will create from env vars
        """
        if settings is not None:
            self.settings = settings
        else:
            self.settings = get_rilla_settings(api_key=api_key, base_url=base_url)

        self._client: httpx.AsyncClient | None = None
        self._rate_limiter = self._create_rate_limiter()

    def _create_rate_limiter(self) -> Any:
        """Create a simple rate limiter using asyncio.Semaphore."""
        return asyncio.Semaphore(self.settings.burst_limit)

    async def __aenter__(self) -> "RillaClient":
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            headers = {
                "Authorization": self.settings.api_key,
                "Content-Type": "application/json",
                "User-Agent": "Maive-Backend-RillaClient/1.0",
            }

            timeout = httpx.Timeout(
                connect=10.0,
                read=self.settings.timeout,
                write=10.0,
                pool=5.0,
            )

            self._client = httpx.AsyncClient(
                base_url=self.settings.base_url,
                headers=headers,
                timeout=timeout,
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                ),
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _mask_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mask sensitive data in request/response for logging."""
        if not self.settings.mask_sensitive_data:
            return data

        masked = data.copy()
        # Mask API key if present
        if "Authorization" in masked:
            masked["Authorization"] = "***MASKED***"
        return masked

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        retries: int | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with error handling and retries.

        Args:
            method: HTTP method (POST, GET, etc.)
            endpoint: API endpoint path
            data: Request data for POST requests
            retries: Number of retries (uses default if None)

        Returns:
            Response data as dictionary

        Raises:
            RillaAPIError: For various API errors
        """
        await self._ensure_client()

        if retries is None:
            retries = self.settings.max_retries

        last_exception: Exception | None = None

        for attempt in range(retries + 1):
            try:
                # Rate limiting
                async with self._rate_limiter:
                    if self.settings.log_requests:
                        masked_data = self._mask_sensitive_data(data or {})
                        logger.info(
                            "Making request: %s %s",
                            method, endpoint,
                            extra={"request_data": masked_data, "attempt": attempt + 1}
                        )

                    response = await self._client.request(
                        method=method,
                        url=endpoint,
                        json=data,
                    )

                    if self.settings.log_responses:
                        logger.info(
                            "Response: %s",
                            response.status_code,
                            extra={"status_code": response.status_code, "attempt": attempt + 1}
                        )

                    # Handle response
                    return await self._handle_response(response, data)

            except httpx.TimeoutException:
                last_exception = RillaTimeoutError(
                    f"Request timed out after {self.settings.timeout} seconds",
                    timeout_duration=self.settings.timeout,
                )

            except httpx.ConnectError as e:
                last_exception = RillaConnectionError(
                    f"Failed to connect to Rilla API: {e!s}",
                    original_error=e,
                )

            except RillaAPIError as e:
                # Don't retry authentication errors or bad requests
                if isinstance(e, (RillaAuthenticationError, RillaBadRequestError)):
                    raise
                last_exception = e

            except httpx.RequestError as e:
                last_exception = RillaConnectionError(
                    f"Request error: {e!s}",
                    original_error=e,
                )

            # Calculate delay for next retry
            if attempt < retries:
                delay = min(
                    self.settings.retry_delay * (self.settings.backoff_factor ** attempt),
                    self.settings.max_retry_delay,
                )
                logger.warning(
                    "Request failed, retrying in %s seconds",
                    delay,
                    extra={"attempt": attempt + 1, "delay": delay}
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise RillaAPIError("All retry attempts failed")

    async def _handle_response(
        self,
        response: httpx.Response,
        request_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle HTTP response and convert errors to appropriate exceptions.

        Args:
            response: HTTP response object
            request_data: Original request data for error context

        Returns:
            Response data as dictionary

        Raises:
            RillaAPIError: For various error conditions
        """
        try:
            response_data = response.json()
        except (ValueError, TypeError):
            response_data = {"error": "Invalid JSON response"}

        # Success
        if 200 <= response.status_code < 300:
            return response_data

        # Error handling
        error_message = response_data.get("error", f"HTTP {response.status_code} error")

        if response.status_code == 400:
            raise RillaBadRequestError(
                message=error_message,
                response_data=response_data,
                request_data=self._mask_sensitive_data(request_data or {}),
            )
        if response.status_code == 401:
            raise RillaAuthenticationError(
                message=error_message,
                response_data=response_data,
                request_data=self._mask_sensitive_data(request_data or {}),
            )
        if response.status_code == 429:
            retry_after = None
            with contextlib.suppress(ValueError, TypeError):
                retry_after = int(response.headers.get("Retry-After", 60))

            raise RillaRateLimitError(
                message=error_message,
                response_data=response_data,
                request_data=self._mask_sensitive_data(request_data or {}),
                retry_after=retry_after,
            )
        if response.status_code >= 500:
            raise RillaServerError(
                message=error_message,
                status_code=response.status_code,
                response_data=response_data,
                request_data=self._mask_sensitive_data(request_data or {}),
            )
        raise RillaAPIError(
            message=error_message,
            status_code=response.status_code,
            response_data=response_data,
            request_data=self._mask_sensitive_data(request_data or {}),
        )

    async def export_conversations(
        self, request: ConversationsExportRequest
    ) -> ConversationsExportResponse:
        """Export conversations for a given time range.

        Args:
            request: Conversations export request parameters

        Returns:
            Paginated conversations response

        Raises:
            RillaAPIError: For API errors
            ValidationError: For invalid request data
        """
        try:
            request_data = request.model_dump(mode="json", exclude_unset=True)
            # Convert snake_case to camelCase for API
            api_request = {
                "fromDate": request_data["from_date"],
                "toDate": request_data["to_date"],
                "dateType": request_data.get("date_type", "timeOfRecording"),
                "page": request_data.get("page", 1),
                "limit": request_data.get("limit", 25),
            }

            if request.users is not None:
                api_request["users"] = request.users

            response_data = await self._make_request("POST", "/export/conversations", api_request)

            # Convert camelCase response to snake_case
            conversations_data = []
            for conv in response_data.get("conversations", []):
                # Convert field names to match our Pydantic model
                conv_data = {
                    "conversation_id": conv.get("conversationId"),
                    "recording_id": conv.get("recordingId"),
                    "title": conv.get("title"),
                    "date": conv.get("date"),
                    "processed_on": conv.get("processedOn"),
                    "duration": conv.get("duration"),
                    "crm_event_id": conv.get("crmEventID"),
                    "rilla_url": conv.get("rillaUrl"),
                    "user": conv.get("user"),
                    "checklists": conv.get("checklists", []),
                    "job_number": conv.get("jobNumber"),
                    "st_link": conv.get("stLink"),
                    "total_sold": conv.get("totalSold"),
                    "outcome": conv.get("outcome"),
                    "job_summary": conv.get("jobSummary"),
                    "custom_summary": conv.get("customSummary"),
                    "rep_speed_wpm": conv.get("repSpeedWPM"),
                    "rep_talk_ratio": conv.get("repTalkRatio"),
                    "longest_rep_monologue": conv.get("longestRepMonologue"),
                    "longest_customer_monologue": conv.get("longestCustomerMonologue"),
                    "total_comments": conv.get("totalComments"),
                }

                # Convert tracker_data snake_case
                for checklist in conv_data["checklists"]:
                    if "trackerData" in checklist:
                        checklist["tracker_data"] = []
                        for tracker in checklist["trackerData"]:
                            checklist["tracker_data"].append({
                                "name": tracker.get("name"),
                                "is_hit": tracker.get("isHit"),
                                "ai_score": tracker.get("aiScore"),
                            })
                        del checklist["trackerData"]

                conversations_data.append(conv_data)

            return ConversationsExportResponse(
                current_page=response_data.get("currentPage"),
                total_pages=response_data.get("totalPages"),
                total_conversations=response_data.get("totalConversations"),
                conversations=conversations_data,
            )

        except ValidationError as e:
            raise RillaAPIError(f"Invalid request data: {e!s}") from e

    async def export_teams(self, request: TeamsExportRequest) -> TeamsExportResponse:
        """Export teams and their analytics for a given time range.

        Args:
            request: Teams export request parameters

        Returns:
            Teams response with analytics

        Raises:
            RillaAPIError: For API errors
        """
        try:
            request_data = request.model_dump(mode="json")
            api_request = {
                "fromDate": request_data["from_date"],
                "toDate": request_data["to_date"],
            }

            response_data = await self._make_request("POST", "/export/teams", api_request)

            # Convert camelCase to snake_case for teams data
            teams_data = []
            for team in response_data.get("teams", []):
                team_data = {
                    "team_id": team.get("teamId"),
                    "name": team.get("name"),
                    "external_team_id": team.get("externalTeamId"),
                    "parent_team_id": team.get("parentTeamId"),
                    "parent_team_name": team.get("parentTeamName"),
                    "appointments_recorded": team.get("appointmentsRecorded"),
                    "analytics_viewed": team.get("analyticsViewed"),
                    "average_conversation_duration": team.get("averageConversationDuration"),
                    "average_conversation_length": team.get("averageConversationLength"),
                    "clip_view_duration": team.get("clipViewDuration"),
                    "comments_given": team.get("commentsGiven"),
                    "comments_read": team.get("commentsRead"),
                    "comments_received": team.get("commentsReceived"),
                    "conversations_viewed": team.get("conversationsViewed"),
                    "conversations_recorded": team.get("conversationsRecorded"),
                    "viewed_recorded_ratio": team.get("viewedRecordedRatio"),
                    "conversation_view_duration": team.get("conversationViewDuration"),
                    "patience_average": team.get("patienceAverage"),
                    "recording_compliance": team.get("recordingCompliance"),
                    "scorecards_given": team.get("scorecardsGiven"),
                    "scorecards_received": team.get("scorecardsReceived"),
                    "talk_ratio_average": team.get("talkRatioAverage"),
                    "total_appointments": team.get("totalAppointments"),
                }
                teams_data.append(team_data)

            return TeamsExportResponse(teams=teams_data)

        except ValidationError as e:
            raise RillaAPIError(f"Invalid request data: {e!s}") from e

    async def export_users(self, request: UsersExportRequest) -> UsersExportResponse:
        """Export users and their analytics for a given time range.

        Args:
            request: Users export request parameters

        Returns:
            Users response with analytics

        Raises:
            RillaAPIError: For API errors
        """
        try:
            request_data = request.model_dump(mode="json", exclude_unset=True)
            api_request = {
                "fromDate": request_data["from_date"],
                "toDate": request_data["to_date"],
            }

            if request.users is not None:
                api_request["users"] = request.users

            response_data = await self._make_request("POST", "/export/users", api_request)

            # Convert camelCase to snake_case for users data
            users_data = []
            for user in response_data.get("users", []):
                # Convert teams data
                teams_data = [
                    {
                        "team_id": team.get("teamId"),
                        "name": team.get("name"),
                    }
                    for team in user.get("teams", [])
                ]

                user_data = {
                    "user_id": user.get("userId"),
                    "name": user.get("name"),
                    "email": user.get("email"),
                    "is_removed": user.get("isRemoved"),
                    "role": user.get("role"),
                    "teams": teams_data,
                    "analytics_viewed": user.get("analyticsViewed"),
                    "appointments_recorded": user.get("appointmentsRecorded"),
                    "average_conversation_duration": user.get("averageConversationDuration"),
                    "average_conversation_length": user.get("averageConversationLength"),
                    "clip_view_duration": user.get("clipViewDuration"),
                    "comments_received": user.get("commentsReceived"),
                    "comments_received_read": user.get("commentsReceivedRead"),
                    "comments_given": user.get("commentsGiven"),
                    "conversations_recorded": user.get("conversationsRecorded"),
                    "conversations_viewed": user.get("conversationsViewed"),
                    "conversation_view_duration": user.get("conversationViewDuration"),
                    "time_of_first_recording": user.get("timeOfFirstRecording"),
                    "patience_average": user.get("patienceAverage"),
                    "recording_compliance": user.get("recordingCompliance"),
                    "scorecards_given": user.get("scorecardsGiven"),
                    "scorecards_received": user.get("scorecardsReceived"),
                    "talk_ratio_average": user.get("talkRatioAverage"),
                    "total_appointments": user.get("totalAppointments"),
                }
                users_data.append(user_data)

            return UsersExportResponse(users=users_data)

        except ValidationError as e:
            raise RillaAPIError(f"Invalid request data: {e!s}") from e

    async def get_all_conversations(
        self, request: ConversationsExportRequest
    ) -> list[Conversation]:
        """Get all conversations by automatically handling pagination.

        Args:
            request: Conversations export request (page parameter will be ignored)

        Returns:
            List of all conversations across all pages

        Raises:
            RillaAPIError: For API errors
        """
        all_conversations: list[Conversation] = []
        current_page = 1

        while True:
            # Create request for current page
            page_request = request.model_copy()
            page_request.page = current_page

            logger.info("Fetching conversations page %s", current_page)

            response = await self.export_conversations(page_request)

            all_conversations.extend(response.conversations)

            logger.info(
                "Fetched %s conversations (page %s of %s)",
                len(response.conversations),
                current_page,
                response.total_pages,
            )

            # Check if we've reached the last page
            if current_page >= response.total_pages:
                break

            current_page += 1

        logger.info("Retrieved %s total conversations", len(all_conversations))
        return all_conversations
