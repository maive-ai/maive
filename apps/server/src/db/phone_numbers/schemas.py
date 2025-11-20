"""
Pydantic schemas for phone number API.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PhoneNumberCreate(BaseModel):
    """Request schema for assigning a phone number."""

    phone_number: str = Field(..., description="Phone number in E.164 format (+1...)")


class PhoneNumberResponse(BaseModel):
    """Response schema for phone number configuration."""

    model_config = ConfigDict(from_attributes=True)

    user_id: str
    phone_number: str
    created_at: datetime
    updated_at: datetime
