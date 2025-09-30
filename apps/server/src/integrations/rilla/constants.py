"""
Rilla integration constants and enums.

This module contains all constants, enums, and static values used
across the Rilla integration system.
"""

from enum import Enum


class RillaEndpoint(str, Enum):
    """Rilla API endpoints."""

    CONVERSATIONS_EXPORT = "/api/v1/conversations/export"
    TEAMS_EXPORT = "/api/v1/teams/export"
    USERS_EXPORT = "/api/v1/users/export"


class RillaErrorCode(str, Enum):
    """Rilla-specific error codes."""

    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_REQUEST = "INVALID_REQUEST"
    SERVER_ERROR = "SERVER_ERROR"
    TIMEOUT = "TIMEOUT"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class RillaStatus(str, Enum):
    """Rilla operation status values."""

    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"


class DateType(str, Enum):
    """Date type for filtering conversations."""

    TIME_OF_RECORDING = "timeOfRecording"
    PROCESSED_DATE = "processedDate"


class Outcome(str, Enum):
    """Possible outcomes for appointments."""

    SOLD = "sold"
    NOT_SOLD = "not_sold"
    FOLLOW_UP = "follow_up"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


# Type aliases for better readability
ConversationId = str
RecordingId = str
UserId = str
TeamId = str
CrmEventId = str
