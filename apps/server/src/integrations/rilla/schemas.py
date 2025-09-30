"""
Rilla-specific Pydantic schemas for request and response models.

This module contains all Pydantic models related to Rilla operations,
data exports, and API responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

from src.integrations.rilla.constants import (
    ConversationId,
    CrmEventId,
    DateType,
    Outcome,
    RecordingId,
    TeamId,
    UserId,
)


# Request Models
class ConversationsExportRequest(BaseModel):
    """Request model for exporting conversations."""

    from_date: datetime = Field(..., alias="fromDate", description="Beginning of the desired time range")
    to_date: datetime = Field(..., alias="toDate", description="End of the desired time range")
    users: list[str] | None = Field(
        None,
        description="Optional array of user emails. If empty/None, returns all users"
    )
    date_type: DateType = Field(
        DateType.TIME_OF_RECORDING,
        alias="dateType",
        description="Filter by time of recording or processed date"
    )
    page: int = Field(1, ge=1, description="Page number (1-based)")
    limit: int = Field(25, ge=1, le=25, description="Number of conversations per page (max 25)")

    @field_validator("users")
    @classmethod
    def validate_users(cls, v: list[str] | None) -> list[str] | None:
        """Validate users list - empty list should be None."""
        if v is not None and len(v) == 0:
            return None
        return v


class TeamsExportRequest(BaseModel):
    """Request model for exporting teams."""

    from_date: datetime = Field(..., alias="fromDate", description="Beginning of the desired time range")
    to_date: datetime = Field(..., alias="toDate", description="End of the desired time range")


class UsersExportRequest(BaseModel):
    """Request model for exporting users."""

    from_date: datetime = Field(..., alias="fromDate", description="Beginning of the desired time range")
    to_date: datetime = Field(..., alias="toDate", description="End of the desired time range")
    users: list[str] | None = Field(
        None,
        description="Optional array of user emails. If empty/None, returns all users"
    )

    @field_validator("users")
    @classmethod
    def validate_users(cls, v: list[str] | None) -> list[str] | None:
        """Validate users list - empty list should be None."""
        if v is not None and len(v) == 0:
            return None
        return v


# Nested Models
class User(BaseModel):
    """User information."""

    id: UserId = Field(..., description="Unique ID of the user")
    name: str = Field(..., description="Name of the user")
    email: str = Field(..., description="Email of the user")


class TrackerData(BaseModel):
    """Individual tracker data within a checklist."""

    name: str = Field(..., description="Name of the tracker")
    is_hit: bool = Field(..., description="Whether the tracker was hit")
    ai_score: float = Field(..., description="AI tracker score")


class Checklist(BaseModel):
    """Checklist data for a conversation."""

    name: str = Field(..., description="Name of the checklist")
    score: int = Field(..., description="Score for the conversation")
    denominator: int = Field(..., description="Maximum possible score")
    tracker_data: list[TrackerData] = Field(..., description="Individual trackers")


class Conversation(BaseModel):
    """Individual conversation data."""

    conversation_id: ConversationId = Field(..., description="Unique ID for the conversation")
    recording_id: RecordingId = Field(..., description="Unique ID for the audio recording")
    title: str = Field(..., description="Title of the conversation")
    date: datetime = Field(..., description="Date when conversation began")
    processed_on: datetime = Field(..., description="Date when conversation was processed")
    duration: int = Field(..., description="Duration of conversation in seconds")
    crm_event_id: CrmEventId | None = Field(None, description="ID of associated CRM appointment/job")
    rilla_url: HttpUrl = Field(..., description="URL of conversation on Rilla")
    user: User = Field(..., description="User who recorded the conversation")
    checklists: list[Checklist] = Field(..., description="Latest checklists for the conversation")
    job_number: str | None = Field(None, description="Job number for the appointment")
    st_link: str | None = Field(None, description="ServiceTitan link (ST integrations only)")
    total_sold: float | None = Field(None, description="Total amount sold")
    outcome: Outcome | None = Field(None, description="Outcome of the appointment")
    job_summary: str | None = Field(None, description="Summary of the appointment")
    custom_summary: str | None = Field(None, description="Admin summary in custom format")
    rep_speed_wpm: float | None = Field(None, description="Rep's talking speed (WPM)")
    rep_talk_ratio: float | None = Field(None, description="Ratio of time rep spent talking")
    longest_rep_monologue: int | None = Field(
        None,
        description="Duration of longest rep monologue (seconds)"
    )
    longest_customer_monologue: int | None = Field(
        None,
        description="Duration of longest customer monologue (seconds)"
    )
    total_comments: int = Field(..., description="Number of comments on the conversation")


class Team(BaseModel):
    """Team information with analytics."""

    team_id: TeamId = Field(..., description="Unique ID for the team")
    name: str = Field(..., description="Name of the team")
    external_team_id: str | None = Field(None, description="External system team ID")
    parent_team_id: TeamId | None = Field(None, description="Parent team ID if applicable")
    parent_team_name: str | None = Field(None, description="Parent team name if applicable")

    # Analytics for the requested date range
    appointments_recorded: int = Field(..., description="Number of CRM appointments recorded")
    analytics_viewed: int = Field(..., description="Number of analytics viewed")
    average_conversation_duration: float = Field(..., description="Average conversation duration")
    average_conversation_length: float = Field(..., description="Average conversation length")
    clip_view_duration: int = Field(..., description="Total clip view duration")
    comments_given: int = Field(..., description="Number of comments written")
    comments_read: int = Field(..., description="Number of comments read")
    comments_received: int = Field(..., description="Number of comments received")
    conversations_viewed: int = Field(..., description="Number of conversations viewed")
    conversations_recorded: int = Field(..., description="Total conversations recorded")
    viewed_recorded_ratio: float = Field(..., description="Ratio of viewed to recorded conversations")
    conversation_view_duration: int = Field(..., description="Total conversation view duration")
    patience_average: float = Field(..., description="Average patience for the team")
    recording_compliance: float = Field(..., description="Recording compliance ratio")
    scorecards_given: int = Field(..., description="Number of scorecards graded")
    scorecards_received: int = Field(..., description="Number of scorecards received")
    talk_ratio_average: float = Field(..., description="Average talk ratio")
    total_appointments: int = Field(..., description="Total number of appointments")


class UserTeam(BaseModel):
    """Team information for a user."""

    team_id: TeamId = Field(..., description="Unique ID of the team")
    name: str = Field(..., description="Name of the team")


class UserWithAnalytics(BaseModel):
    """User information with analytics."""

    user_id: UserId = Field(..., description="Unique ID of the user")
    name: str = Field(..., description="Name of the user")
    email: str = Field(..., description="Email of the user")
    is_removed: bool = Field(..., description="Whether user has been deleted")
    role: str = Field(..., description="User's role within Rilla")
    teams: list[UserTeam] = Field(..., description="Teams the user belongs to")

    # Analytics for the requested date range
    analytics_viewed: int = Field(..., description="Number of analytics viewed")
    appointments_recorded: int = Field(..., description="Number of appointments recorded")
    average_conversation_duration: float = Field(..., description="Average conversation duration")
    average_conversation_length: float = Field(..., description="Average conversation length")
    clip_view_duration: int = Field(..., description="Total clip view duration")
    comments_received: int = Field(..., description="Number of comments received")
    comments_received_read: int = Field(..., description="Number of received comments read")
    comments_given: int = Field(..., description="Number of comments given")
    conversations_recorded: int = Field(..., description="Number of conversations recorded")
    conversations_viewed: int = Field(..., description="Number of conversations viewed")
    conversation_view_duration: int = Field(..., description="Total conversation view duration")
    time_of_first_recording: datetime | None = Field(
        None,
        description="Date of first recording"
    )
    patience_average: float = Field(..., description="Average patience score")
    recording_compliance: float = Field(..., description="Recording compliance ratio")
    scorecards_given: int = Field(..., description="Number of scorecards graded")
    scorecards_received: int = Field(..., description="Number of scorecards received")
    talk_ratio_average: float = Field(..., description="Average talk ratio")
    total_appointments: int = Field(..., description="Total number of appointments")


# Response Models
class ConversationsExportResponse(BaseModel):
    """Response model for conversations export."""

    conversations: list[Conversation] = Field(..., description="Conversations for this page")
    current_page: int = Field(..., alias="currentPage", description="Current page number")
    total_pages: int = Field(..., alias="totalPages", description="Total number of pages")
    total_conversations: int = Field(..., alias="totalConversations", description="Total number of conversations")


class TeamsExportResponse(BaseModel):
    """Response model for teams export."""

    teams: list[Team] = Field(..., description="All teams with analytics")


class UsersExportResponse(BaseModel):
    """Response model for users export."""

    users: list[UserWithAnalytics] = Field(..., description="All users with analytics")
