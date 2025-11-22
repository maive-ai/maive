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


class VapiDocumentNeeded(BaseModel):
    """Document information from required actions."""

    document_name: str = Field(..., description="Name of the required document")
    description: str | None = Field(
        None, description="Optional description of the document"
    )


class VapiRequiredActions(BaseModel):
    """Required actions from claim status call."""

    documents_needed: list[VapiDocumentNeeded] = Field(
        default_factory=list, description="List of required documents"
    )
    submission_method: str | None = Field(
        None, description="Document submission method: email, portal, mail"
    )
    next_steps: str | None = Field(None, description="Summary of next actions")
