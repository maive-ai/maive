"""
Mock CRM-specific Pydantic schemas.

This module contains schemas specific to the Mock CRM provider.
"""

from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    """Simple contact information (name, phone, email)."""

    name: str | None = Field(None, description="Contact name")
    phone: str | None = Field(None, description="Contact phone")
    email: str | None = Field(None, description="Contact email")


class MockNote(BaseModel):
    """Simple note for mock projects."""

    id: str | None = Field(None, description="Note ID")
    text: str = Field(..., description="Note text")


class MockProject(BaseModel):
    """Mock project data model (Mock CRM only)."""

    model_config = {"populate_by_name": True}

    id: str | None = Field(None, description="Project ID")
    customer_name: str = Field(
        ..., min_length=1, alias="customerName", description="Customer name"
    )
    address: str | None = Field(None, description="Project address")
    phone: str | None = Field(None, description="Customer phone")
    email: str | None = Field(None, description="Customer email")
    claim_number: str | None = Field(
        None, alias="claimNumber", description="Insurance claim number"
    )
    date_of_loss: str | None = Field(
        None, alias="dateOfLoss", description="Date of loss (ISO format)"
    )
    insurance_company: str | None = Field(
        None, alias="insuranceCompany", description="Insurance company name"
    )
    insurance_agency: str | None = Field(
        None, alias="insuranceAgency", description="Insurance agency name"
    )
    insurance_agency_contact: ContactInfo | None = Field(
        None, alias="insuranceAgencyContact", description="Insurance agency contact"
    )
    insurance_contact_name: str | None = Field(
        None, alias="insuranceContactName", description="Insurance contact name"
    )
    insurance_contact_phone: str | None = Field(
        None, alias="insuranceContactPhone", description="Insurance contact phone"
    )
    insurance_contact_email: str | None = Field(
        None, alias="insuranceContactEmail", description="Insurance contact email"
    )
    adjuster_name: str | None = Field(None, alias="adjusterName", description="Adjuster name")
    adjuster_contact: ContactInfo | None = Field(
        None, alias="adjusterContact", description="Adjuster contact"
    )
    adjuster_contact_name: str | None = Field(
        None, alias="adjusterContactName", description="Adjuster contact name"
    )
    adjuster_contact_phone: str | None = Field(
        None, alias="adjusterContactPhone", description="Adjuster contact phone"
    )
    adjuster_contact_email: str | None = Field(
        None, alias="adjusterContactEmail", description="Adjuster contact email"
    )
    notes: list[MockNote] | None = Field(None, description="Project notes")
    status: str = Field(default="In Progress", description="Project status")

