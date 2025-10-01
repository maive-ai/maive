"""
Rilla integration constants and enums.

This module contains all constants, enums, and static values used
across the Rilla integration system.
"""

from enum import Enum


class RillaEndpoint(str, Enum):
    """Rilla API endpoints."""

    CONVERSATIONS_EXPORT = "/export/conversations"
    TEAMS_EXPORT = "/export/teams"
    USERS_EXPORT = "/export/users"


class DateType(str, Enum):
    """Date type for filtering conversations."""

    TIME_OF_RECORDING = "timeOfRecording"
    PROCESSED_DATE = "processedDate"


class Outcome(str, Enum):
    """Possible outcomes for appointments."""

    SOLD = "sold"
    SOLD_CAPS = "Sold"  # API also returns capitalized version
    NOT_SOLD = "not_sold"
    FOLLOW_UP = "follow_up"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"
    OPEN = "Open"  # API returns this value


# Type aliases for better readability
ConversationId = str
RecordingId = str
UserId = str
TeamId = str
CrmEventId = str
