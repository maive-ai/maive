"""Tests for Rilla API client."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from pydantic import ValidationError

from backend.rilla import (
    RillaClient,
    RillaAuthenticationError,
    RillaBadRequestError,
    RillaRateLimitError,
    RillaServerError,
    ConversationsExportRequest,
    ConversationsExportResponse,
    TeamsExportRequest,
    TeamsExportResponse,
    UsersExportRequest,
    UsersExportResponse,
)
from backend.rilla.config import RillaSettings
from backend.rilla.exceptions import RillaConnectionError, RillaTimeoutError


class TestRillaClient:
    """Test cases for RillaClient."""

    @pytest.fixture
    def settings(self):
        """Test settings."""
        return RillaSettings(
            api_key="test-api-key",
            base_url="https://test.rillavoice.com",
            timeout=10,
            max_retries=2,
        )

    @pytest.fixture
    def client(self, settings):
        """Test client."""
        return RillaClient(settings=settings)

    @pytest.fixture
    def mock_conversations_response(self):
        """Mock conversations API response."""
        return {
            "currentPage": 1,
            "totalPages": 2,
            "totalConversations": 50,
            "conversations": [
                {
                    "conversationId": "conv-123",
                    "recordingId": "rec-456",
                    "title": "Test Conversation",
                    "date": "2024-03-01T14:00:00Z",
                    "processedOn": "2024-03-01T15:00:00Z",
                    "duration": 1800,
                    "crmEventID": "crm-789",
                    "rillaUrl": "https://app.rillavoice.com/conversations/123",
                    "user": {
                        "id": "user-123",
                        "name": "John Doe",
                        "email": "john@example.com"
                    },
                    "checklists": [
                        {
                            "name": "Sales",
                            "score": 8,
                            "denominator": 10,
                            "trackerData": [
                                {
                                    "name": "Greeting",
                                    "isHit": True,
                                    "aiScore": 0.95
                                }
                            ]
                        }
                    ],
                    "jobNumber": "JOB-001",
                    "totalSold": 5000.0,
                    "outcome": "sold",
                    "repSpeedWPM": 150.5,
                    "repTalkRatio": 0.65,
                    "longestRepMonologue": 120,
                    "longestCustomerMonologue": 90,
                    "totalComments": 3
                }
            ]
        }

    @pytest.fixture
    def mock_teams_response(self):
        """Mock teams API response."""
        return {
            "teams": [
                {
                    "teamId": "team-123",
                    "name": "Sales Team",
                    "externalTeamId": "ext-123",
                    "parentTeamId": None,
                    "parentTeamName": None,
                    "appointmentsRecorded": 25,
                    "analyticsViewed": 100,
                    "averageConversationDuration": 1800.5,
                    "averageConversationLength": 900.2,
                    "clipViewDuration": 500,
                    "commentsGiven": 15,
                    "commentsRead": 20,
                    "commentsReceived": 18,
                    "conversationsViewed": 75,
                    "conversationsRecorded": 30,
                    "viewedRecordedRatio": 2.5,
                    "conversationViewDuration": 10000,
                    "patienceAverage": 0.75,
                    "recordingCompliance": 0.83,
                    "scorecardsGiven": 5,
                    "scorecardsReceived": 8,
                    "talkRatioAverage": 0.65,
                    "totalAppointments": 35
                }
            ]
        }

    @pytest.fixture
    def mock_users_response(self):
        """Mock users API response."""
        return {
            "users": [
                {
                    "userId": "user-123",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "isRemoved": False,
                    "role": "Sales Rep",
                    "teams": [
                        {
                            "teamId": "team-123",
                            "name": "Sales Team"
                        }
                    ],
                    "analyticsViewed": 50,
                    "appointmentsRecorded": 12,
                    "averageConversationDuration": 1800.0,
                    "averageConversationLength": 900.0,
                    "clipViewDuration": 200,
                    "commentsReceived": 5,
                    "commentsReceivedRead": 4,
                    "commentsGiven": 8,
                    "conversationsRecorded": 15,
                    "conversationsViewed": 25,
                    "conversationViewDuration": 5000,
                    "timeOfFirstRecording": "2024-01-01T10:00:00Z",
                    "patienceAverage": 0.8,
                    "recordingCompliance": 0.75,
                    "scorecardsGiven": 2,
                    "scorecardsReceived": 3,
                    "talkRatioAverage": 0.7,
                    "totalAppointments": 16
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_client_initialization(self, settings):
        """Test client initialization."""
        client = RillaClient(settings=settings)
        assert client.settings == settings
        assert client._client is None

    @pytest.mark.asyncio
    async def test_client_context_manager(self, client):
        """Test client as context manager."""
        async with client as c:
            assert c is client
            assert client._client is not None
        
        # Client should be closed after context
        assert client._client is None

    @pytest.mark.asyncio
    async def test_export_conversations_success(self, client, mock_conversations_response):
        """Test successful conversations export."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_conversations_response
            
            request = ConversationsExportRequest(
                from_date=datetime(2024, 3, 1),
                to_date=datetime(2024, 4, 1),
                page=1,
                limit=25
            )
            
            response = await client.export_conversations(request)
            
            assert isinstance(response, ConversationsExportResponse)
            assert response.current_page == 1
            assert response.total_pages == 2
            assert response.total_conversations == 50
            assert len(response.conversations) == 1
            
            conversation = response.conversations[0]
            assert conversation.conversation_id == "conv-123"
            assert conversation.title == "Test Conversation"
            assert conversation.user.name == "John Doe"
            assert len(conversation.checklists) == 1
            
            # Verify request was made correctly
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "/export/conversations"

    @pytest.mark.asyncio
    async def test_export_conversations_with_users_filter(self, client, mock_conversations_response):
        """Test conversations export with users filter."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_conversations_response
            
            request = ConversationsExportRequest(
                from_date=datetime(2024, 3, 1),
                to_date=datetime(2024, 4, 1),
                users=["john@example.com", "jane@example.com"]
            )
            
            await client.export_conversations(request)
            
            # Verify users were included in request
            call_args = mock_request.call_args
            request_data = call_args[0][2]
            assert "users" in request_data
            assert request_data["users"] == ["john@example.com", "jane@example.com"]

    @pytest.mark.asyncio
    async def test_export_teams_success(self, client, mock_teams_response):
        """Test successful teams export."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_teams_response
            
            request = TeamsExportRequest(
                from_date=datetime(2024, 3, 1),
                to_date=datetime(2024, 4, 1)
            )
            
            response = await client.export_teams(request)
            
            assert isinstance(response, TeamsExportResponse)
            assert len(response.teams) == 1
            
            team = response.teams[0]
            assert team.team_id == "team-123"
            assert team.name == "Sales Team"
            assert team.conversations_recorded == 30
            assert team.recording_compliance == 0.83

    @pytest.mark.asyncio
    async def test_export_users_success(self, client, mock_users_response):
        """Test successful users export."""
        with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_users_response
            
            request = UsersExportRequest(
                from_date=datetime(2024, 3, 1),
                to_date=datetime(2024, 4, 1)
            )
            
            response = await client.export_users(request)
            
            assert isinstance(response, UsersExportResponse)
            assert len(response.users) == 1
            
            user = response.users[0]
            assert user.user_id == "user-123"
            assert user.name == "John Doe"
            assert user.email == "john@example.com"
            assert user.role == "Sales Rep"
            assert len(user.teams) == 1

    @pytest.mark.asyncio
    async def test_get_all_conversations_pagination(self, client, mock_conversations_response):
        """Test auto-pagination for get_all_conversations."""
        # Mock responses for multiple pages
        page1_response = mock_conversations_response.copy()
        page1_response["currentPage"] = 1
        page1_response["totalPages"] = 2
        
        page2_response = mock_conversations_response.copy()
        page2_response["currentPage"] = 2
        page2_response["totalPages"] = 2
        page2_response["conversations"] = [
            {
                "conversationId": "conv-456",
                "recordingId": "rec-789",
                "title": "Another Conversation",
                "date": "2024-03-02T14:00:00Z",
                "processedOn": "2024-03-02T15:00:00Z",
                "duration": 1200,
                "rillaUrl": "https://app.rillavoice.com/conversations/456",
                "user": {"id": "user-456", "name": "Jane Doe", "email": "jane@example.com"},
                "checklists": [],
                "totalComments": 1
            }
        ]
        
        with patch.object(client, 'export_conversations', new_callable=AsyncMock) as mock_export:
            # Create proper response objects with snake_case field names
            page1_conv = {
                "conversation_id": "conv-123",
                "recording_id": "rec-456", 
                "title": "Test Conversation",
                "date": "2024-03-01T14:00:00Z",
                "processed_on": "2024-03-01T15:00:00Z",
                "duration": 1800,
                "crm_event_id": "crm-789",
                "rilla_url": "https://app.rillavoice.com/conversations/123",
                "user": {"id": "user-123", "name": "John Doe", "email": "john@example.com"},
                "checklists": [{"name": "Sales", "score": 8, "denominator": 10, "tracker_data": []}],
                "total_comments": 3
            }
            
            page2_conv = {
                "conversation_id": "conv-456",
                "recording_id": "rec-789",
                "title": "Another Conversation", 
                "date": "2024-03-02T14:00:00Z",
                "processed_on": "2024-03-02T15:00:00Z",
                "duration": 1200,
                "rilla_url": "https://app.rillavoice.com/conversations/456",
                "user": {"id": "user-456", "name": "Jane Doe", "email": "jane@example.com"},
                "checklists": [],
                "total_comments": 1
            }
            
            # Return different responses for each page
            mock_export.side_effect = [
                ConversationsExportResponse(
                    current_page=1,
                    total_pages=2,
                    total_conversations=50,
                    conversations=[page1_conv]
                ),
                ConversationsExportResponse(
                    current_page=2,
                    total_pages=2,
                    total_conversations=50,
                    conversations=[page2_conv]
                )
            ]
            
            request = ConversationsExportRequest(
                from_date=datetime(2024, 3, 1),
                to_date=datetime(2024, 4, 1)
            )
            
            all_conversations = await client.get_all_conversations(request)
            
            # Should have called export_conversations twice (once per page)
            assert mock_export.call_count == 2
            
            # Should have all conversations from both pages
            assert len(all_conversations) == 2
            assert all_conversations[0].conversation_id == "conv-123"
            assert all_conversations[1].conversation_id == "conv-456"

    @pytest.mark.asyncio
    async def test_authentication_error(self, client):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        
        with patch.object(client, '_client') as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)
            
            with pytest.raises(RillaAuthenticationError) as exc_info:
                request = ConversationsExportRequest(
                    from_date=datetime(2024, 3, 1),
                    to_date=datetime(2024, 4, 1)
                )
                await client.export_conversations(request)
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_bad_request_error(self, client):
        """Test bad request error handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid date format"}
        
        with patch.object(client, '_client') as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)
            
            with pytest.raises(RillaBadRequestError) as exc_info:
                request = ConversationsExportRequest(
                    from_date=datetime(2024, 3, 1),
                    to_date=datetime(2024, 4, 1)
                )
                await client.export_conversations(request)
            
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, client):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.json.return_value = {"error": "Rate limit exceeded"}
        
        with patch.object(client, '_client') as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)
            
            with pytest.raises(RillaRateLimitError) as exc_info:
                request = ConversationsExportRequest(
                    from_date=datetime(2024, 3, 1),
                    to_date=datetime(2024, 4, 1)
                )
                await client.export_conversations(request)
            
            assert exc_info.value.status_code == 429
            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_server_error(self, client):
        """Test server error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        
        with patch.object(client, '_client') as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)
            
            with pytest.raises(RillaServerError) as exc_info:
                request = ConversationsExportRequest(
                    from_date=datetime(2024, 3, 1),
                    to_date=datetime(2024, 4, 1)
                )
                await client.export_conversations(request)
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_timeout_error(self, client):
        """Test timeout error handling."""
        with patch.object(client, '_client') as mock_client:
            mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            
            with pytest.raises(RillaTimeoutError):
                request = ConversationsExportRequest(
                    from_date=datetime(2024, 3, 1),
                    to_date=datetime(2024, 4, 1)
                )
                await client.export_conversations(request)

    @pytest.mark.asyncio
    async def test_connection_error(self, client):
        """Test connection error handling."""
        with patch.object(client, '_client') as mock_client:
            mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            
            with pytest.raises(RillaConnectionError):
                request = ConversationsExportRequest(
                    from_date=datetime(2024, 3, 1),
                    to_date=datetime(2024, 4, 1)
                )
                await client.export_conversations(request)

    @pytest.mark.asyncio
    async def test_retry_logic(self, client):
        """Test retry logic on transient failures."""
        # First call fails, second succeeds
        mock_response_error = Mock()
        mock_response_error.status_code = 500
        mock_response_error.json.return_value = {"error": "Server error"}
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {"conversations": []}
        
        with patch.object(client, '_client') as mock_client:
            mock_client.request = AsyncMock(side_effect=[mock_response_error, mock_response_success])
            
            # Should succeed after retry
            with patch('asyncio.sleep', new_callable=AsyncMock):  # Speed up test
                response_data = await client._make_request("POST", "/test", {})
                assert response_data == {"conversations": []}
                
                # Should have made 2 requests (original + 1 retry)
                assert mock_client.request.call_count == 2

    def test_settings_from_env_vars(self):
        """Test settings loading from environment variables."""
        with patch.dict('os.environ', {
            'RILLA_API_KEY': 'env-api-key',
            'RILLA_BASE_URL': 'https://env.rillavoice.com',
            'RILLA_TIMEOUT': '45',
        }):
            settings = RillaSettings()
            assert settings.api_key == 'env-api-key'
            assert settings.base_url == 'https://env.rillavoice.com'
            assert settings.timeout == 45

    def test_request_validation(self):
        """Test request model validation."""
        # Valid request
        request = ConversationsExportRequest(
            from_date=datetime(2024, 3, 1),
            to_date=datetime(2024, 4, 1)
        )
        assert request.page == 1  # Default value
        assert request.limit == 25  # Default value
        
        # Invalid page number
        with pytest.raises(ValidationError):
            ConversationsExportRequest(
                from_date=datetime(2024, 3, 1),
                to_date=datetime(2024, 4, 1),
                page=0  # Must be >= 1
            )
        
        # Invalid limit
        with pytest.raises(ValidationError):
            ConversationsExportRequest(
                from_date=datetime(2024, 3, 1),
                to_date=datetime(2024, 4, 1),
                limit=30  # Must be <= 25
            )

    def test_users_validation(self):
        """Test users list validation."""
        # Empty list should become None
        request = ConversationsExportRequest(
            from_date=datetime(2024, 3, 1),
            to_date=datetime(2024, 4, 1),
            users=[]
        )
        assert request.users is None
        
        # Non-empty list should remain
        request = ConversationsExportRequest(
            from_date=datetime(2024, 3, 1),
            to_date=datetime(2024, 4, 1),
            users=["user@example.com"]
        )
        assert request.users == ["user@example.com"]

    def test_sensitive_data_masking(self, client):
        """Test sensitive data masking in logs."""
        data = {
            "Authorization": "secret-api-key",
            "other_field": "visible-data"
        }
        
        # With masking enabled (default)
        client.settings.mask_sensitive_data = True
        masked = client._mask_sensitive_data(data)
        assert masked["Authorization"] == "***MASKED***"
        assert masked["other_field"] == "visible-data"
        
        # With masking disabled
        client.settings.mask_sensitive_data = False
        unmasked = client._mask_sensitive_data(data)
        assert unmasked["Authorization"] == "secret-api-key"
        assert unmasked["other_field"] == "visible-data"
