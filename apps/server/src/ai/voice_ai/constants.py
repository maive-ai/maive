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


class VoiceAIProvider(str, Enum):
    """Available Voice AI providers."""

    VAPI = "vapi"


class WebhookEventType(str, Enum):
    """Standard webhook event types across providers."""

    CALL_STARTED = "call_started"
    CALL_ENDED = "call_ended"
    FUNCTION_CALL = "function_call"
    TRANSCRIPT = "transcript"
    SPEECH_UPDATE = "speech_update"
    CONVERSATION_UPDATE = "conversation_update"
    STATUS_UPDATE = "status_update"
    ERROR = "error"


class VoiceAIErrorCode(str, Enum):
    """Standard error codes across Voice AI providers."""

    NOT_FOUND = "NOT_FOUND"
    HTTP_ERROR = "HTTP_ERROR"
    INVALID_JSON = "INVALID_JSON"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

