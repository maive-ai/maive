"""
Pydantic schemas for call list operations.

This module contains all Pydantic models related to call list management,
including request and response models for adding, removing, and querying call lists.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class AddToCallListRequest(BaseModel):
    """Request model for adding projects to call list."""

    project_ids: list[str] = Field(
        ..., description="List of project/job IDs to add to call list"
    )


class CallListItemResponse(BaseModel):
    """Response model for a single call list item."""

    id: int = Field(..., description="Database ID of the call list item")
    user_id: str = Field(..., description="Cognito user ID")
    project_id: str = Field(..., description="Project/Job ID from CRM")
    call_completed: bool = Field(..., description="Whether the call has been completed")
    position: int = Field(..., description="Position in the call list for ordering")
    created_at: datetime = Field(..., description="When the item was added to the list")
    updated_at: datetime = Field(..., description="When the item was last updated")


class CallListResponse(BaseModel):
    """Response model for the complete call list."""

    items: list[CallListItemResponse] = Field(
        ..., description="List of call list items"
    )
    total: int = Field(..., description="Total number of items in the call list")


class MarkCallCompletedRequest(BaseModel):
    """Request model for marking a call as completed."""

    completed: bool = Field(True, description="Whether the call is completed")
