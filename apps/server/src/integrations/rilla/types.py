"""Type definitions and enums for Rilla API."""

from enum import Enum


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
