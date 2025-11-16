"""Pydantic schemas for organization models."""

from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    """Base organization schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Organization display name")


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization."""

    pass


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Updated organization name")


class Organization(OrganizationBase):
    """Organization schema with full details."""

    id: str = Field(..., description="Organization UUID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}
