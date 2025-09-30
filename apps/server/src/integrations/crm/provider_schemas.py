"""
Provider-specific schemas for CRM integration data.

This module contains Pydantic models for provider-specific data
that gets stored in the provider_data field.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ServiceTitanProviderData(BaseModel):
    """Service Titan specific provider data."""

    appointment_number: str = Field(..., description="Service Titan appointment number")
    job_id: int = Field(..., description="Associated job ID")
    customer_id: int = Field(..., description="Customer identifier")
    active: bool = Field(..., description="Whether appointment is active")
    is_confirmed: bool = Field(..., description="Whether appointment is confirmed")
    original_status: str = Field(
        ..., description="Original Service Titan status string"
    )

    # Optional fields that might be available
    start_time: datetime | None = Field(None, description="Appointment start time")
    end_time: datetime | None = Field(None, description="Appointment end time")
    special_instructions: str | None = Field(None, description="Special instructions")
    arrival_window_start: datetime | None = Field(
        None, description="Arrival window start"
    )
    arrival_window_end: datetime | None = Field(None, description="Arrival window end")

    class Config:
        """Pydantic configuration."""

        # Allow extra fields for future extensibility
        extra = "allow"
        # Use enum values for serialization
        use_enum_values = True


class FormSubmissionOwner(BaseModel):
    """Form submission owner object."""

    type: str = Field(..., description="Owner type (e.g., 'Job')")
    id: int = Field(..., description="Owner ID")


class FormSubmissionRequest(BaseModel):
    """Request model for form submissions."""

    form_id: int = Field(..., description="Form ID to get submissions for")
    owners: list[FormSubmissionOwner] = Field(..., description="List of owner objects")


class FormSubmissionResponse(BaseModel):
    """Individual form submission response from Service Titan API."""

    id: int = Field(..., description="Form submission ID")
    form_id: int = Field(..., description="Form ID", alias="formId")
    form_name: str | None = Field(None, description="Form name", alias="formName")
    submitted_on: datetime = Field(
        ..., description="Submission timestamp", alias="submittedOn"
    )
    created_by_id: int = Field(
        ..., description="ID of user who created the submission", alias="createdById"
    )
    status: str = Field(..., description="Submission status")
    owners: list[FormSubmissionOwner] | None = Field(None, description="Form owners")
    units: list[dict[str, Any]] | None = Field(None, description="Form units/fields")

    class Config:
        """Pydantic configuration."""

        validate_by_name = True


class FormSubmissionListResponse(BaseModel):
    """Paginated response for form submissions from Service Titan API."""

    page: int = Field(..., description="From which page this output has started")
    page_size: int = Field(
        ..., description="Page size for this query", alias="pageSize"
    )
    has_more: bool = Field(
        ..., description="True if there are more records", alias="hasMore"
    )
    total_count: int | None = Field(
        None, description="Total count of records", alias="totalCount"
    )
    data: list[FormSubmissionResponse] = Field(
        ..., description="The collection of form submissions"
    )

    class Config:
        """Pydantic configuration."""

        validate_by_name = True


class CRMProviderDataFactory:
    """Factory for creating provider-specific data models."""

    @staticmethod
    def create_service_titan_data(raw_data: dict[str, Any]) -> ServiceTitanProviderData:
        """Create Service Titan provider data from raw API response."""
        try:
            # Parse datetime fields
            start_time = None
            if raw_data.get("start"):
                start_time = datetime.fromisoformat(
                    raw_data["start"].replace("Z", "+00:00")
                )

            end_time = None
            if raw_data.get("end"):
                end_time = datetime.fromisoformat(
                    raw_data["end"].replace("Z", "+00:00")
                )

            arrival_window_start = None
            if raw_data.get("arrivalWindowStart"):
                arrival_window_start = datetime.fromisoformat(
                    raw_data["arrivalWindowStart"].replace("Z", "+00:00")
                )

            arrival_window_end = None
            if raw_data.get("arrivalWindowEnd"):
                arrival_window_end = datetime.fromisoformat(
                    raw_data["arrivalWindowEnd"].replace("Z", "+00:00")
                )

            return ServiceTitanProviderData(
                appointment_number=raw_data.get("appointmentNumber", ""),
                job_id=raw_data.get("jobId", 0),
                customer_id=raw_data.get("customerId", 0),
                active=raw_data.get("active", False),
                is_confirmed=raw_data.get("isConfirmed", False),
                original_status=raw_data.get("status") or "unknown",
                start_time=start_time,
                end_time=end_time,
                special_instructions=raw_data.get("specialInstructions"),
                arrival_window_start=arrival_window_start,
                arrival_window_end=arrival_window_end,
            )
        except Exception:
            # Fallback to basic data if parsing fails
            return ServiceTitanProviderData(
                appointment_number=raw_data.get("appointmentNumber", ""),
                job_id=raw_data.get("jobId", 0),
                customer_id=raw_data.get("customerId", 0),
                active=raw_data.get("active", False),
                is_confirmed=raw_data.get("isConfirmed", False),
                original_status=raw_data.get("status") or "unknown",
            )
