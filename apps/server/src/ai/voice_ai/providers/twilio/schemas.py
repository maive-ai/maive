"""
Pydantic schemas for Twilio provider data.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TwilioCall(BaseModel):
    """Twilio call data structure for provider_data storage."""

    sid: str = Field(..., description="Twilio Call SID (browser call)")
    status: str = Field(..., description="Twilio call status")
    to: str = Field(..., description="Destination phone number")
    from_number: str | None = Field(
        None, alias="from", description="Source phone number"
    )
    date_created: str | None = Field(None, description="Call creation timestamp (ISO)")
    date_updated: str | None = Field(None, description="Last update timestamp (ISO)")
    duration: str | None = Field(None, description="Call duration in seconds")
    price: str | None = Field(None, description="Call price")
    direction: str | None = Field(None, description="Call direction")
    conference_name: str | None = Field(
        None, description="Conference room name for bridging"
    )
    customer_phone: str | None = Field(
        None, description="Customer phone number to bridge"
    )
    user_phone: str | None = Field(
        None, description="User's phone number (for webhook to create provider)"
    )
    customer_call_sid: str | None = Field(
        None, description="Customer call SID (set after bridge)"
    )

    model_config = {"populate_by_name": True}
