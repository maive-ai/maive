"""
Voice AI-specific Pydantic schemas for request and response models.

This module contains all Pydantic models related to Voice AI operations,
call management, and status tracking across different Voice AI providers.
"""

from typing import Any

from pydantic import BaseModel, Field

from src.ai.voice_ai.constants import CallStatus, VoiceAIErrorCode, VoiceAIProvider as VoiceAIProviderEnum, WebhookEventType


class CallRequest(BaseModel):
    """Request model for creating an outbound call."""

    phone_number: str = Field(..., description="Phone number to call")
    customer_id: str | None = Field(None, description="Customer identifier")
    customer_name: str | None = Field(None, description="Customer name")
    company_name: str | None = Field(None, description="Company name")
    customer_address: str | None = Field(None, description="Customer address")
    claim_number: str | None = Field(None, description="Insurance claim number")
    date_of_loss: str | None = Field(None, description="Date of loss for insurance claim")
    insurance_agency: str | None = Field(None, description="Insurance agency name")
    adjuster_name: str | None = Field(None, description="Insurance adjuster name")
    adjuster_phone: str | None = Field(None, description="Insurance adjuster phone")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class CallResponse(BaseModel):
    """Response model for call information."""

    call_id: str = Field(..., description="Unique call identifier")
    status: CallStatus = Field(..., description="Current call status")
    provider: VoiceAIProviderEnum = Field(..., description="Voice AI provider")
    created_at: str | None = Field(None, description="Call creation timestamp")
    provider_data: dict[str, Any] | None = Field(None, description="Provider-specific data")


class CallListResponse(BaseModel):
    """Response model for multiple calls."""

    calls: list[CallResponse] = Field(..., description="List of calls")
    total_count: int = Field(..., description="Total number of calls")
    provider: VoiceAIProviderEnum = Field(..., description="Voice AI provider")


class CallStartedData(BaseModel):
    """Data for call started events."""

    customer_number: str | None = Field(None, description="Customer phone number")
    assistant_id: str | None = Field(None, description="Assistant ID used for the call")


class CallEndedData(BaseModel):
    """Data for call ended events."""

    duration: float | None = Field(None, description="Call duration in seconds")
    transcript: str = Field(default="", description="Full call transcript")
    end_reason: str | None = Field(None, description="Reason the call ended")
    artifact: dict[str, Any] = Field(default_factory=dict, description="Call artifacts")
    analysis: dict[str, Any] = Field(default_factory=dict, description="Call analysis data")
    vapi_payload: dict[str, Any] = Field(default_factory=dict, description="Full provider payload for processing")


class FunctionCallData(BaseModel):
    """Data for function call events."""

    function_name: str | None = Field(None, description="Name of the function being called")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Function call parameters")


class TranscriptData(BaseModel):
    """Data for transcript events."""

    transcript: str = Field(default="", description="Transcript text")
    is_partial: bool = Field(default=False, description="Whether this is a partial transcript")


class SpeechUpdateData(BaseModel):
    """Data for speech update events."""

    status: str | None = Field(None, description="Speech status")
    role: str | None = Field(None, description="Speaker role")
    turn: int | None = Field(None, description="Turn number")


class ConversationUpdateData(BaseModel):
    """Data for conversation update events."""

    conversation: list[dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    messages: list[dict[str, Any]] = Field(default_factory=list, description="Message list")


class StatusUpdateData(BaseModel):
    """Data for status update events."""

    status: str | None = Field(None, description="Call status")
    ended_reason: str | None = Field(None, description="Reason for status change")


# Union type for all event data types
WebhookEventData = (
    CallStartedData
    | CallEndedData
    | FunctionCallData
    | TranscriptData
    | SpeechUpdateData
    | ConversationUpdateData
    | StatusUpdateData
    | dict[str, Any]  # Fallback for unknown event types
)


class WebhookEvent(BaseModel):
    """Standard webhook event model across all Voice AI providers."""

    event_type: WebhookEventType = Field(..., description="Type of webhook event")
    call_id: str | None = Field(None, description="Unique call identifier (may be None for some event types)")
    data: WebhookEventData = Field(..., description="Event-specific typed data")
    provider_data: dict[str, Any] = Field(default_factory=dict, description="Raw provider data")


class VoiceAIErrorResponse(BaseModel):
    """Error response from Voice AI operations."""

    success: bool = Field(default=False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: VoiceAIErrorCode | None = Field(None, description="Error code")
    provider: VoiceAIProviderEnum | None = Field(None, description="Voice AI provider")

