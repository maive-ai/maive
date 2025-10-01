"""
Abstract base classes for Voice AI providers.

This module defines the abstract interface that all Voice AI providers
must implement, ensuring consistent behavior across different voice AI systems.
"""

from abc import ABC, abstractmethod

from src.integrations.voice_ai.schemas import CallRequest, CallResponse, WebhookEvent


class VoiceAIProvider(ABC):
    """Abstract interface for Voice AI providers."""

    @abstractmethod
    async def create_outbound_call(self, request: CallRequest) -> CallResponse:
        """
        Create an outbound call.

        Args:
            request: The call request with phone number and context

        Returns:
            CallResponse: The call response with call_id and status

        Raises:
            VoiceAIError: If the call creation fails
        """
        pass

    @abstractmethod
    async def verify_webhook(self, headers: dict[str, str], body: str) -> bool:
        """
        Verify webhook authenticity.

        Args:
            headers: HTTP headers from the webhook request
            body: Raw body of the webhook request

        Returns:
            bool: True if webhook is authentic, False otherwise
        """
        pass

    @abstractmethod
    async def parse_webhook(self, headers: dict[str, str], body: str) -> WebhookEvent:
        """
        Parse webhook payload into standard format.

        Args:
            headers: HTTP headers from the webhook request
            body: Raw body of the webhook request

        Returns:
            WebhookEvent: Parsed webhook event with standard structure

        Raises:
            VoiceAIError: If webhook parsing fails
        """
        pass

    @abstractmethod
    async def get_call_status(self, call_id: str) -> CallResponse:
        """
        Get the status of a specific call by ID.

        Args:
            call_id: The unique identifier for the call

        Returns:
            CallResponse: The call status information

        Raises:
            VoiceAIError: If the call is not found or an error occurs
        """
        pass


class VoiceAIError(Exception):
    """Base exception for Voice AI-related errors."""

    def __init__(self, message: str, error_code: str | None = None):
        """
        Initialize Voice AI error.

        Args:
            message: Error message
            error_code: Optional provider-specific error code
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code

