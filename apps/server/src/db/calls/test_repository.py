"""
Unit tests for CallRepository.

Tests all CRUD operations using mocked async sessions.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.voice_ai.constants import CallStatus, VoiceAIProvider
from src.db.calls.model import Call
from src.db.calls.repository import CallRepository


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def repository(mock_session):
    """Create a CallRepository with mocked session."""
    return CallRepository(mock_session)


@pytest.fixture
def sample_call():
    """Create a sample Call instance for testing."""
    return Call(
        id=1,
        user_id="test-user-123",
        call_id="vapi-call-456",
        project_id="project-789",
        status=CallStatus.IN_PROGRESS.value,
        provider=VoiceAIProvider.VAPI.value,
        phone_number="+15551234567",
        is_active=True,
        listen_url="wss://vapi.ai/listen/123",
        started_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        ended_at=None,
        created_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        provider_data={"monitor": {"listen_url": "wss://vapi.ai/listen/123"}},
        analysis_data=None,
    )


@pytest.mark.asyncio
async def test_create_call(repository, mock_session):
    """Test creating a new call record."""
    # Setup
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Execute
    call = await repository.create_call(
        user_id="test-user-123",
        call_id="vapi-call-456",
        project_id="project-789",
        status=CallStatus.IN_PROGRESS,
        provider=VoiceAIProvider.VAPI,
        phone_number="+15551234567",
        started_at=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        listen_url="wss://vapi.ai/listen/123",
        provider_data={"test": "data"},
    )

    # Assert
    assert call.user_id == "test-user-123"
    assert call.call_id == "vapi-call-456"
    assert call.is_active is True
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_call_found(repository, mock_session, sample_call):
    """Test getting active call when one exists."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_call
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    result = await repository.get_active_call("test-user-123")

    # Assert
    assert result == sample_call
    assert result.user_id == "test-user-123"
    assert result.is_active is True
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_call_not_found(repository, mock_session):
    """Test getting active call when none exists."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    result = await repository.get_active_call("test-user-123")

    # Assert
    assert result is None
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_call_by_call_id(repository, mock_session, sample_call):
    """Test getting call by provider call ID."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_call
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    result = await repository.get_call_by_call_id("vapi-call-456")

    # Assert
    assert result == sample_call
    assert result.call_id == "vapi-call-456"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_call_status(repository, mock_session, sample_call):
    """Test updating call status."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_call
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Execute
    updated_call = await repository.update_call_status(
        call_id="vapi-call-456",
        status=CallStatus.COMPLETED,
        provider_data={"new": "data"},
    )

    # Assert
    assert updated_call is not None
    assert updated_call.status == CallStatus.COMPLETED.value
    assert updated_call.provider_data == {"new": "data"}
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_call_status_not_found(repository, mock_session):
    """Test updating call status when call doesn't exist."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    result = await repository.update_call_status(
        call_id="nonexistent",
        status=CallStatus.COMPLETED,
    )

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_end_call(repository, mock_session, sample_call):
    """Test marking call as ended."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_call
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock()

    end_time = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    # Execute
    ended_call = await repository.end_call(
        call_id="vapi-call-456",
        final_status=CallStatus.COMPLETED,
        ended_at=end_time,
        analysis_data={"claim_status": "approved"},
    )

    # Assert
    assert ended_call is not None
    assert ended_call.status == CallStatus.COMPLETED.value
    assert ended_call.is_active is False
    assert ended_call.ended_at == end_time
    assert ended_call.analysis_data == {"claim_status": "approved"}
    mock_session.flush.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_remove_active_call(repository, mock_session):
    """Test removing active status from call."""
    # Setup
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    result = await repository.remove_active_call("test-user-123")

    # Assert
    assert result is True
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_remove_active_call_none_found(repository, mock_session):
    """Test removing active call when none exists."""
    # Setup
    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    result = await repository.remove_active_call("test-user-123")

    # Assert
    assert result is False
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_call_history(repository, mock_session, sample_call):
    """Test getting call history with filters."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_call]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    calls = await repository.get_call_history(
        user_id="test-user-123",
        limit=10,
        offset=0,
    )

    # Assert
    assert len(calls) == 1
    assert calls[0] == sample_call
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_call_history_with_project_filter(
    repository, mock_session, sample_call
):
    """Test getting call history filtered by project."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_call]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    calls = await repository.get_call_history(
        project_id="project-789",
        limit=50,
    )

    # Assert
    assert len(calls) == 1
    assert calls[0].project_id == "project-789"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_project_calls(repository, mock_session, sample_call):
    """Test getting all calls for a project."""
    # Setup
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_call]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Execute
    calls = await repository.get_project_calls("project-789", limit=50)

    # Assert
    assert len(calls) == 1
    assert calls[0].project_id == "project-789"
    mock_session.execute.assert_called_once()
