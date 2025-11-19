"""
Pydantic schemas for scheduled groups operations.

This module contains all Pydantic models related to scheduled groups management,
including request and response models for creating, updating, and querying groups.
"""

from datetime import datetime, time
from enum import Enum

from pydantic import BaseModel, Field


class GoalType(str, Enum):
    """Goal type enum for scheduled groups."""

    STATUS_CHECK = "status_check"
    LOCATE_CHECK = "locate_check"
    USER_SPECIFIED = "user_specified"
    AI_DETERMINED = "ai_determined"


class WhoToCall(str, Enum):
    """Who to call enum for scheduled groups."""

    ADJUSTER = "adjuster"
    INSURANCE_CARRIER = "insurance_carrier"
    AI_DETERMINES = "ai_determines"


class CreateScheduledGroupRequest(BaseModel):
    """Request model for creating a scheduled group."""

    name: str = Field(..., description="Group display name", min_length=1, max_length=255)
    frequency: list[str] = Field(
        ...,
        description="Days of week: ['monday', 'tuesday', etc.]",
        min_length=1,
    )
    time_of_day: time = Field(..., description="Time of day to make calls")
    goal_type: GoalType = Field(..., description="Type of goal for this group")
    goal_description: str | None = Field(
        None, description="User-specified goal description (required if goal_type is user_specified)"
    )
    who_to_call: WhoToCall = Field(..., description="Who to call for this group")


class UpdateScheduledGroupRequest(BaseModel):
    """Request model for updating a scheduled group."""

    name: str | None = Field(None, description="Group display name", min_length=1, max_length=255)
    frequency: list[str] | None = Field(
        None, description="Days of week: ['monday', 'tuesday', etc.]", min_length=1
    )
    time_of_day: time | None = Field(None, description="Time of day to make calls")
    goal_type: GoalType | None = Field(None, description="Type of goal for this group")
    goal_description: str | None = Field(
        None, description="User-specified goal description"
    )
    who_to_call: WhoToCall | None = Field(None, description="Who to call for this group")


class AddProjectsToGroupRequest(BaseModel):
    """Request model for adding projects to a group."""

    project_ids: list[str] = Field(
        ..., description="List of project/job IDs to add to group", min_length=1
    )


class UpdateGroupStatusRequest(BaseModel):
    """Request model for updating group active status."""

    is_active: bool = Field(..., description="Whether the group should be active")


class ScheduledGroupMemberResponse(BaseModel):
    """Response model for a single scheduled group member."""

    id: int = Field(..., description="Database ID of the member")
    group_id: int = Field(..., description="Group ID")
    project_id: str = Field(..., description="Project/Job ID from CRM")
    goal_completed: bool = Field(..., description="Whether the goal has been completed")
    goal_completed_at: datetime | None = Field(
        None, description="Timestamp when goal was completed"
    )
    added_at: datetime = Field(..., description="When the project was added to the group")


class ScheduledGroupResponse(BaseModel):
    """Response model for a scheduled group."""

    id: int = Field(..., description="Database ID of the group")
    user_id: str = Field(..., description="Cognito user ID")
    name: str = Field(..., description="Group display name")
    frequency: list[str] = Field(..., description="Days of week")
    time_of_day: str = Field(..., description="Time of day (HH:MM:SS format)")
    goal_type: str = Field(..., description="Goal type")
    goal_description: str | None = Field(None, description="Goal description")
    who_to_call: str = Field(..., description="Who to call")
    is_active: bool = Field(..., description="Whether the group is active")
    member_count: int = Field(..., description="Number of projects in the group")
    created_at: datetime = Field(..., description="When the group was created")
    updated_at: datetime = Field(..., description="When the group was last updated")


class ScheduledGroupDetailResponse(BaseModel):
    """Response model for a scheduled group with members."""

    id: int = Field(..., description="Database ID of the group")
    user_id: str = Field(..., description="Cognito user ID")
    name: str = Field(..., description="Group display name")
    frequency: list[str] = Field(..., description="Days of week")
    time_of_day: str = Field(..., description="Time of day (HH:MM:SS format)")
    goal_type: str = Field(..., description="Goal type")
    goal_description: str | None = Field(None, description="Goal description")
    who_to_call: str = Field(..., description="Who to call")
    is_active: bool = Field(..., description="Whether the group is active")
    members: list[ScheduledGroupMemberResponse] = Field(
        ..., description="List of group members"
    )
    created_at: datetime = Field(..., description="When the group was created")
    updated_at: datetime = Field(..., description="When the group was last updated")


class ScheduledGroupsListResponse(BaseModel):
    """Response model for listing scheduled groups."""

    groups: list[ScheduledGroupResponse] = Field(..., description="List of scheduled groups")
    total: int = Field(..., description="Total number of groups")

