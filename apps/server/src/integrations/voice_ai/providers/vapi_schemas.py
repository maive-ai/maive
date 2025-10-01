"""
Provider-specific schemas for Voice AI integration data.

This module contains Pydantic models for provider-specific data
that gets stored in the provider_data field.
"""

from typing import Any

from pydantic import BaseModel, Field


class VapiEndpoints:
    """Vapi API endpoint paths."""

    CALL = "/call"
    CALL_BY_ID = "/call/{call_id}"


class VapiCallMetadata(BaseModel):
    """Vapi call metadata structure."""

    source: str | None = Field(None, description="Call source")
    crm_source: str | None = Field(None, description="CRM source")
    customer_id: str | None = Field(None, description="Customer identifier")
    assistant_name: str | None = Field(None, description="Assistant name")

    class Config:
        """Pydantic configuration."""
        extra = "allow"
        use_enum_values = True


class VapiCallData(BaseModel):
    """Vapi call data structure."""

    id: str = Field(..., description="Vapi call ID")
    metadata: VapiCallMetadata = Field(default_factory=VapiCallMetadata, description="Call metadata")
    org_id: str | None = Field(None, alias="orgId", description="Organization ID")
    created_at: str | None = Field(None, alias="createdAt", description="Creation timestamp")
    updated_at: str | None = Field(None, alias="updatedAt", description="Update timestamp")
    type: str | None = Field(None, description="Call type")
    status: str | None = Field(None, description="Call status")
    assistant_id: str | None = Field(None, alias="assistantId", description="Assistant ID")

    class Config:
        """Pydantic configuration."""
        extra = "allow"
        use_enum_values = True
        populate_by_name = True


class VapiPaymentDetails(BaseModel):
    """Payment information from claim status call."""

    status: str | None = Field(None, description="Payment status: issued, not_issued, pending")
    amount: float | None = Field(None, description="Payment amount")
    issue_date: str | None = Field(None, description="Date payment was issued")
    check_number: str | None = Field(None, description="Check number")


class VapiRequiredActions(BaseModel):
    """Required actions from claim status call."""

    documents_needed: list[str] = Field(default_factory=list, description="List of required documents")
    submission_method: str | None = Field(None, description="Document submission method: email, portal, mail")
    next_steps: str | None = Field(None, description="Summary of next actions")


class VapiClaimStatusData(BaseModel):
    """Structured output data from insurance claim status calls."""

    call_outcome: str = Field(..., description="Call outcome: success, voicemail, gatekeeper, failed")
    claim_status: str = Field(..., description="Claim status: approved, denied, pending_review, etc.")
    payment_details: VapiPaymentDetails | None = Field(None, description="Payment details")
    required_actions: VapiRequiredActions | None = Field(None, description="Required actions")
    claim_update_summary: str | None = Field(None, description="Summary of the call for notes")


class VapiAnalysis(BaseModel):
    """Vapi analysis structure."""

    summary: str | None = Field(None, description="Call summary")
    structured_data: dict[str, Any] | None = Field(None, description="Structured data extraction")
    success_evaluation: str | None = Field(None, description="Success evaluation")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class VapiCustomer(BaseModel):
    """Vapi customer data structure."""

    number: str | None = Field(None, description="Customer phone number")
    name: str | None = Field(None, description="Customer name")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"


class VapiAssistant(BaseModel):
    """Vapi assistant data structure."""

    id: str | None = Field(None, description="Assistant ID")
    name: str | None = Field(None, description="Assistant name")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"


class VapiFunction(BaseModel):
    """Vapi function call data structure."""

    name: str | None = Field(None, description="Function name")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Function parameters")
    
    class Config:
        """Pydantic configuration."""
        extra = "allow"


class VapiMessage(BaseModel):
    """Vapi webhook message structure."""

    timestamp: int | None = Field(None, description="Message timestamp")
    type: str | None = Field(None, description="Message type")
    analysis: VapiAnalysis | None = Field(None, description="Call analysis")
    artifact: dict[str, Any] | None = Field(None, description="Call artifact")
    started_at: str | None = Field(None, alias="startedAt", description="Call start time")
    ended_at: str | None = Field(None, alias="endedAt", description="Call end time")
    ended_reason: str | None = Field(None, alias="endedReason", description="Call end reason")
    cost: float | None = Field(None, description="Call cost")
    duration_ms: int | None = Field(None, alias="durationMs", description="Duration in milliseconds")
    duration_seconds: float | None = Field(None, alias="durationSeconds", description="Duration in seconds")
    duration_minutes: float | None = Field(None, alias="durationMinutes", description="Duration in minutes")
    summary: str | None = Field(None, description="Call summary")
    transcript: str | None = Field(None, description="Call transcript")
    messages: list[dict[str, Any]] | None = Field(None, description="Call messages")
    recording_url: str | None = Field(None, alias="recordingUrl", description="Recording URL")
    stereo_recording_url: str | None = Field(None, alias="stereoRecordingUrl", description="Stereo recording URL")
    call: VapiCallData | None = Field(None, description="Call data")
    customer: VapiCustomer | None = Field(None, description="Customer data")
    assistant: VapiAssistant | None = Field(None, description="Assistant data")

    class Config:
        """Pydantic configuration."""
        extra = "allow"
        populate_by_name = True


class VapiWebhookPayload(BaseModel):
    """Complete Vapi webhook payload structure."""

    message: VapiMessage = Field(..., description="Webhook message")
    
    # Fields that appear at root level for certain event types
    function: VapiFunction | None = Field(None, description="Function call data for function-call events")
    transcript: str | None = Field(None, description="Transcript for transcript events")
    is_partial: bool | None = Field(None, alias="isPartial", description="Whether transcript is partial")
    status: str | None = Field(None, description="Status for status-update events")
    role: str | None = Field(None, description="Role for speech-update events")
    turn: int | None = Field(None, description="Turn number for speech-update events")
    conversation: list[dict[str, Any]] | None = Field(None, description="Conversation for conversation-update events")
    ended_reason: str | None = Field(None, alias="endedReason", description="End reason for status-update events")

    class Config:
        """Pydantic configuration."""
        extra = "allow"
        populate_by_name = True



