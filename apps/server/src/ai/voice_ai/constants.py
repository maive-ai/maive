"""
Voice AI integration constants and enums.

This module contains all constants, enums, and static values used
across the Voice AI integration system.
"""

from enum import Enum


class CallStatus(str, Enum):
    """Call status values across Voice AI systems."""

    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    FORWARDING = "forwarding"
    ENDED = "ended"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    FAILED = "failed"
    CANCELED = "canceled"

    CALL_ENDED_STATUSES = [ENDED, FAILED, CANCELED, BUSY, NO_ANSWER]

    @classmethod
    def is_call_ended(cls, status: "CallStatus") -> bool:
        """Check if a call status indicates the call has ended."""
        return status in cls.CALL_ENDED_STATUSES


class VoiceAIProvider(str, Enum):
    """Available Voice AI providers."""

    VAPI = "vapi"


class VoiceAIErrorCode(str, Enum):
    """Standard error codes across Voice AI providers."""

    NOT_FOUND = "NOT_FOUND"
    HTTP_ERROR = "HTTP_ERROR"
    INVALID_JSON = "INVALID_JSON"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
