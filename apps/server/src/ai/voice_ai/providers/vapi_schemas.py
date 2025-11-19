"""
Provider-specific schemas for Voice AI integration data.

This module contains Pydantic models for provider-specific data
that gets stored in the provider_data field.
"""

from pydantic import BaseModel, Field


class VapiPaymentDetails(BaseModel):
    """Payment information from claim status call."""

    status: str | None = Field(
        None, description="Payment status: issued, not_issued, pending"
    )
    amount: float | None = Field(None, description="Payment amount")
    issue_date: str | None = Field(None, description="Date payment was issued")
    check_number: str | None = Field(None, description="Check number")


class VapiRequiredActions(BaseModel):
    """Required actions from claim status call."""

    documents_needed: list[str] = Field(
        default_factory=list, description="List of required documents"
    )
    submission_method: str | None = Field(
        None, description="Document submission method: email, portal, mail"
    )
    next_steps: str | None = Field(None, description="Summary of next actions")
