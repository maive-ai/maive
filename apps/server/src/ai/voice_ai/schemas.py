"""
Voice AI-specific Pydantic schemas for request and response models.

This module contains all Pydantic models related to Voice AI operations,
call management, and status tracking across different Voice AI providers.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.ai.voice_ai.constants import CallStatus, VoiceAIErrorCode
from src.ai.voice_ai.constants import VoiceAIProvider as VoiceAIProviderEnum


class CallRequest(BaseModel):
    """Request model for creating an outbound call."""

    phone_number: str = Field(..., description="Phone number to call")
    customer_id: str | None = Field(None, description="Customer identifier")
    customer_name: str | None = Field(None, description="Customer name")
    company_name: str | None = Field(None, description="Company name")
    customer_address: str | None = Field(None, description="Customer address")
    claim_number: str | None = Field(None, description="Insurance claim number")
    date_of_loss: str | None = Field(
        None, description="Date of loss for insurance claim"
    )
    insurance_agency: str | None = Field(None, description="Insurance agency name")
    adjuster_name: str | None = Field(None, description="Insurance adjuster name")
    adjuster_phone: str | None = Field(None, description="Insurance adjuster phone")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    job_id: int | str | None = Field(None, description="Job/Project ID (int for Service Titan, str for JobNimbus/Mock)")
    tenant: int | None = Field(None, description="Tenant ID")


class VoiceAIErrorResponse(BaseModel):
    """Error response from Voice AI operations."""

    success: bool = Field(default=False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: VoiceAIErrorCode | None = Field(None, description="Error code")
    provider: VoiceAIProviderEnum | None = Field(None, description="Voice AI provider")


# Provider-agnostic structured data models
# These models provide a common interface across different voice AI providers


class PaymentDetails(BaseModel):
    """Provider-agnostic payment information from claim status calls."""

    status: str | None = Field(
        None, description="Payment status: issued, not_issued, pending"
    )
    amount: float | None = Field(None, description="Payment amount")
    issue_date: str | None = Field(None, description="Date payment was issued")
    check_number: str | None = Field(None, description="Check number")

    @classmethod
    def from_vapi(cls, vapi_payment: Any) -> "PaymentDetails":
        """Create from Vapi payment details."""
        from src.ai.voice_ai.providers.vapi_schemas import VapiPaymentDetails

        if isinstance(vapi_payment, VapiPaymentDetails):
            return cls(
                status=vapi_payment.status,
                amount=vapi_payment.amount,
                issue_date=vapi_payment.issue_date,
                check_number=vapi_payment.check_number,
            )
        elif isinstance(vapi_payment, dict):
            return cls(**vapi_payment)
        return cls()


class RequiredActions(BaseModel):
    """Provider-agnostic required actions from claim status calls."""

    documents_needed: list[str] = Field(
        default_factory=list, description="List of required documents"
    )
    submission_method: str | None = Field(
        None, description="Document submission method: email, portal, mail"
    )
    next_steps: str | None = Field(None, description="Summary of next actions")

    @classmethod
    def from_vapi(cls, vapi_actions: Any) -> "RequiredActions":
        """Create from Vapi required actions."""
        from src.ai.voice_ai.providers.vapi_schemas import VapiRequiredActions

        if isinstance(vapi_actions, VapiRequiredActions):
            return cls(
                documents_needed=vapi_actions.documents_needed,
                submission_method=vapi_actions.submission_method,
                next_steps=vapi_actions.next_steps,
            )
        elif isinstance(vapi_actions, dict):
            return cls(**vapi_actions)
        return cls()


class ClaimStatusData(BaseModel):
    """Provider-agnostic structured data from insurance claim status calls.

    Note: claim_status now represents the project/job status in the CRM.
    Different CRM providers have different status values.
    """

    call_outcome: str = Field(
        default="unknown",
        description="Call outcome: success, voicemail, gatekeeper, failed",
    )
    claim_status: str = Field(
        default="",
        description="Project/job status from call: e.g. 'Completed', 'Hold', 'Pending Review', etc.",
    )
    payment_details: PaymentDetails | None = Field(None, description="Payment details")
    required_actions: RequiredActions | None = Field(
        None, description="Required actions"
    )
    claim_update_summary: str | None = Field(
        None, description="Summary of the call for notes"
    )

    @classmethod
    def from_vapi(cls, vapi_data: dict[str, Any]) -> "ClaimStatusData":
        """Create from Vapi-specific structured data."""
        # Handle claim_status - always a string now
        claim_status = vapi_data.get("claim_status", "")

        return cls(
            call_outcome=vapi_data.get("call_outcome", "unknown"),
            claim_status=claim_status,
            payment_details=(
                PaymentDetails.from_vapi(vapi_data["payment_details"])
                if vapi_data.get("payment_details")
                else None
            ),
            required_actions=(
                RequiredActions.from_vapi(vapi_data["required_actions"])
                if vapi_data.get("required_actions")
                else None
            ),
            claim_update_summary=vapi_data.get("claim_update_summary"),
        )


class AnalysisData(BaseModel):
    """Provider-agnostic analysis data from completed calls."""

    summary: str | None = Field(None, description="Call summary")
    structured_data: ClaimStatusData | None = Field(
        None, description="Structured data extraction"
    )
    success_evaluation: str | None = Field(None, description="Success evaluation")


class TranscriptMessage(BaseModel):
    """Provider-agnostic transcript message."""

    role: str = Field(..., description="Speaker role: user, assistant, system")
    content: str = Field(..., description="Message content")
    timestamp_seconds: float = Field(..., description="Seconds from call start")
    duration_seconds: float | None = Field(None, description="Message duration")


class CallResponse(BaseModel):
    """Response model for call information."""
    
    model_config = {"arbitrary_types_allowed": True}

    call_id: str = Field(..., description="Unique call identifier")
    status: CallStatus = Field(..., description="Current call status")
    provider: VoiceAIProviderEnum = Field(..., description="Voice AI provider")
    created_at: datetime | None = Field(None, description="Call creation timestamp")
    provider_data: Any = Field(
        None, description="Provider-specific data (VapiCall for Vapi, dict for others)"
    )
    analysis: AnalysisData | None = Field(
        None, description="Typed analysis data (extracted from provider_data)"
    )
    messages: list[TranscriptMessage] = Field(
        default_factory=list,
        description="Transcript messages from the call"
    )


class ActiveCallResponse(BaseModel):
    """Response model for the user's currently active call."""

    user_id: str = Field(..., description="User identifier")
    call_id: str = Field(..., description="Unique call identifier")
    project_id: str = Field(..., description="Associated project identifier")
    status: CallStatus = Field(..., description="Current call status")
    provider: VoiceAIProviderEnum = Field(..., description="Voice AI provider")
    phone_number: str = Field(..., description="Phone number being called")
    listen_url: str | None = Field(None, description="URL to listen to the call")
    started_at: str = Field(..., description="Call start timestamp (ISO format)")
    provider_data: Any = Field(
        None, description="Provider-specific data for the call"
    )
    transcript: list[TranscriptMessage] = Field(
        default_factory=list,
        description="Transcript messages from the call"
    )


class CallListResponse(BaseModel):
    """Response model for multiple calls."""

    calls: list[CallResponse] = Field(..., description="List of calls")
    total_count: int = Field(..., description="Total number of calls")
    provider: VoiceAIProviderEnum = Field(..., description="Voice AI provider")