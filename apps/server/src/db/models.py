"""
Pydantic models for DynamoDB items.

Models for active call state and serialization/deserialization helpers.
"""

import time
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from src.ai.voice_ai.constants import CallStatus, VoiceAIProvider


def convert_floats_to_decimal(obj: Any) -> Any:
    """
    Recursively convert float values to Decimal for DynamoDB compatibility.

    DynamoDB does not support float types - they must be Decimal.

    Args:
        obj: Any Python object (dict, list, float, etc.)

    Returns:
        The same object with all floats converted to Decimal
    """
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))  # Convert via string to avoid precision issues
    else:
        return obj


class ActiveCallState(BaseModel):
    """
    Model for active call state stored in DynamoDB.

    This represents a user's currently active call session.
    """

    user_id: str = Field(..., description="Cognito user ID (sub)")
    call_id: str = Field(..., description="Provider call ID")
    project_id: str = Field(..., description="Project/Job ID")
    status: CallStatus = Field(..., description="Current call status")
    provider: VoiceAIProvider = Field(..., description="Voice AI provider")
    phone_number: str = Field(..., description="Phone number called")
    listen_url: str | None = Field(
        None, description="WebSocket URL for listening to call"
    )
    started_at: datetime = Field(..., description="Call start timestamp")
    provider_data: dict[str, Any] | None = Field(
        None, description="Raw provider response data"
    )

    def to_dynamodb_item(self) -> dict[str, Any]:
        """
        Convert to DynamoDB item format.

        Returns:
            dict: DynamoDB item with PK, SK, and attributes
        """
        # Calculate TTL (24 hours from now)
        ttl = int(time.time()) + (24 * 60 * 60)

        # Convert provider_data floats to Decimal for DynamoDB compatibility
        provider_data_clean = convert_floats_to_decimal(self.provider_data) if self.provider_data else None

        return {
            "PK": f"user_{self.user_id}",
            "SK": f"ACTIVE#user_{self.user_id}",
            "call_id": self.call_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "provider": self.provider.value,
            "phone_number": self.phone_number,
            "listen_url": self.listen_url,
            "started_at": self.started_at.isoformat(),
            "provider_data": provider_data_clean,
            "ttl": ttl,
        }

    @classmethod
    def from_dynamodb_item(cls, item: dict[str, Any]) -> "ActiveCallState":
        """
        Create from DynamoDB item format.

        Args:
            item: DynamoDB item

        Returns:
            ActiveCallState: Parsed model instance
        """
        # Extract user_id from PK (format: "user_{user_id}")
        user_id = item["PK"].replace("user_", "")

        return cls(
            user_id=user_id,
            call_id=item["call_id"],
            project_id=item["project_id"],
            status=CallStatus(item["status"]),
            provider=VoiceAIProvider(item["provider"]),
            phone_number=item["phone_number"],
            listen_url=item.get("listen_url"),
            started_at=datetime.fromisoformat(item["started_at"]),
            provider_data=item.get("provider_data"),
        )
