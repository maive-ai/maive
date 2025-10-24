"""
Unit tests for DynamoDB call state service.

Tests cover storing, retrieving, and removing active call state.
"""

import os
from datetime import datetime

import pytest
from moto import mock_aws

from src.ai.voice_ai.constants import CallStatus, VoiceAIProvider
from src.db.call_state_service import CallStateService
from src.db.models import ActiveCallState


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "us-west-2"
    os.environ["DYNAMODB_ACTIVE_CALLS"] = "test-active-calls"


@pytest.fixture
def dynamodb_table(aws_credentials):
    """Create a mock DynamoDB table for testing."""
    with mock_aws():
        import boto3

        # Create DynamoDB table
        dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        table = dynamodb.create_table(
            TableName="test-active-calls",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        yield table


@pytest.fixture
def sample_call_state():
    """Create a sample active call state for testing."""
    return ActiveCallState(
        user_id="test-user-123",
        call_id="vapi_call_456",
        project_id="project_789",
        status=CallStatus.IN_PROGRESS,
        provider=VoiceAIProvider.VAPI,
        phone_number="+15551234567",
        listen_url="wss://vapi.com/listen/test",
        started_at=datetime(2025, 10, 23, 10, 30, 0),
        provider_data={"test": "data"},
    )


@pytest.mark.asyncio
async def test_set_active_call(dynamodb_table, sample_call_state):
    """Test storing an active call in DynamoDB."""
    # Clear cache to ensure fresh instance
    from src.db.dynamodb_client import get_dynamodb_resource

    get_dynamodb_resource.cache_clear()

    service = CallStateService()
    await service.set_active_call(sample_call_state)

    # Verify item was stored
    response = dynamodb_table.get_item(
        Key={
            "PK": f"user_{sample_call_state.user_id}",
            "SK": f"ACTIVE#user_{sample_call_state.user_id}",
        }
    )

    assert "Item" in response
    item = response["Item"]
    assert item["call_id"] == sample_call_state.call_id
    assert item["project_id"] == sample_call_state.project_id
    assert item["status"] == sample_call_state.status.value
    assert item["phone_number"] == sample_call_state.phone_number
    assert "ttl" in item  # Verify TTL is set


@pytest.mark.asyncio
async def test_get_active_call(dynamodb_table, sample_call_state):
    """Test retrieving an active call from DynamoDB."""
    # Clear cache
    from src.db.dynamodb_client import get_dynamodb_resource

    get_dynamodb_resource.cache_clear()

    # Store the call first
    service = CallStateService()
    await service.set_active_call(sample_call_state)

    # Retrieve it
    retrieved = await service.get_active_call(sample_call_state.user_id)

    assert retrieved is not None
    assert retrieved.user_id == sample_call_state.user_id
    assert retrieved.call_id == sample_call_state.call_id
    assert retrieved.project_id == sample_call_state.project_id
    assert retrieved.status == sample_call_state.status
    assert retrieved.provider == sample_call_state.provider
    assert retrieved.phone_number == sample_call_state.phone_number
    assert retrieved.listen_url == sample_call_state.listen_url


@pytest.mark.asyncio
async def test_get_active_call_not_found(dynamodb_table):
    """Test retrieving a non-existent active call returns None."""
    # Clear cache
    from src.db.dynamodb_client import get_dynamodb_resource

    get_dynamodb_resource.cache_clear()

    service = CallStateService()
    retrieved = await service.get_active_call("non-existent-user")

    assert retrieved is None


@pytest.mark.asyncio
async def test_remove_active_call(dynamodb_table, sample_call_state):
    """Test removing an active call from DynamoDB."""
    # Clear cache
    from src.db.dynamodb_client import get_dynamodb_resource

    get_dynamodb_resource.cache_clear()

    # Store the call first
    service = CallStateService()
    await service.set_active_call(sample_call_state)

    # Verify it exists
    retrieved = await service.get_active_call(sample_call_state.user_id)
    assert retrieved is not None

    # Remove it
    await service.remove_active_call(sample_call_state.user_id)

    # Verify it's gone
    retrieved = await service.get_active_call(sample_call_state.user_id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_set_active_call_updates_existing(dynamodb_table, sample_call_state):
    """Test that setting an active call updates an existing one."""
    # Clear cache
    from src.db.dynamodb_client import get_dynamodb_resource

    get_dynamodb_resource.cache_clear()

    service = CallStateService()

    # Store initial call
    await service.set_active_call(sample_call_state)

    # Update with new status
    updated_state = sample_call_state.model_copy()
    updated_state.status = CallStatus.ENDED
    updated_state.call_id = "new_call_id"

    await service.set_active_call(updated_state)

    # Retrieve and verify it was updated
    retrieved = await service.get_active_call(sample_call_state.user_id)
    assert retrieved is not None
    assert retrieved.status == CallStatus.ENDED
    assert retrieved.call_id == "new_call_id"


@pytest.mark.asyncio
async def test_ttl_is_set(dynamodb_table, sample_call_state):
    """Test that TTL attribute is properly set (24 hours from now)."""
    import time

    # Clear cache
    from src.db.dynamodb_client import get_dynamodb_resource

    get_dynamodb_resource.cache_clear()

    service = CallStateService()
    current_time = int(time.time())

    await service.set_active_call(sample_call_state)

    # Verify TTL is set to approximately 24 hours from now
    response = dynamodb_table.get_item(
        Key={
            "PK": f"user_{sample_call_state.user_id}",
            "SK": f"ACTIVE#user_{sample_call_state.user_id}",
        }
    )

    ttl = response["Item"]["ttl"]
    expected_ttl = current_time + (24 * 60 * 60)

    # Allow 10 second tolerance for test execution time
    assert abs(ttl - expected_ttl) < 10


@pytest.mark.asyncio
async def test_model_serialization_roundtrip(sample_call_state):
    """Test that model serialization and deserialization work correctly."""
    # Convert to DynamoDB item
    item = sample_call_state.to_dynamodb_item()

    # Verify key structure
    assert item["PK"] == f"user_{sample_call_state.user_id}"
    assert item["SK"] == f"ACTIVE#user_{sample_call_state.user_id}"

    # Convert back to model
    restored = ActiveCallState.from_dynamodb_item(item)

    # Verify all fields match
    assert restored.user_id == sample_call_state.user_id
    assert restored.call_id == sample_call_state.call_id
    assert restored.project_id == sample_call_state.project_id
    assert restored.status == sample_call_state.status
    assert restored.provider == sample_call_state.provider
    assert restored.phone_number == sample_call_state.phone_number
    assert restored.listen_url == sample_call_state.listen_url
    assert restored.provider_data == sample_call_state.provider_data
