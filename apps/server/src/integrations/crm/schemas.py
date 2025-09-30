"""
CRM-specific Pydantic schemas for request and response models.

This module contains all Pydantic models related to CRM operations,
project management, and status tracking across different CRM providers.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.integrations.crm.constants import CRMProvider, ProjectStatus


class ProjectStatusResponse(BaseModel):
    """Response model for project status information."""

    project_id: str = Field(..., description="Unique project identifier")
    status: ProjectStatus = Field(..., description="Current project status")
    provider: CRMProvider = Field(..., description="CRM provider")
    updated_at: datetime | None = Field(None, description="Last status update timestamp")
    provider_data: dict[str, Any] | None = Field(None, description="Provider-specific data")


class ProjectStatusListResponse(BaseModel):
    """Response model for multiple project statuses."""

    projects: list[ProjectStatusResponse] = Field(..., description="List of project statuses")
    total_count: int = Field(..., description="Total number of projects")
    provider: CRMProvider = Field(..., description="CRM provider")


class CRMErrorResponse(BaseModel):
    """Error response from CRM operations."""

    success: bool = Field(default=False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: str | None = Field(None, description="Provider-specific error code")
    provider: CRMProvider | None = Field(None, description="CRM provider")