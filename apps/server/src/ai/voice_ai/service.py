"""
Voice AI service layer for business logic.

This module provides the business logic layer for Voice AI operations,
sitting between the FastAPI routes and the Voice AI providers.
"""

from src.ai.voice_ai.base import VoiceAIError, VoiceAIProvider
from src.ai.voice_ai.constants import VoiceAIErrorCode
from src.ai.voice_ai.schemas import CallRequest, CallResponse, VoiceAIErrorResponse
from src.utils.logger import logger


class VoiceAIService:
    """Service class for Voice AI operations."""

    def __init__(self, voice_ai_provider: VoiceAIProvider):
        """
        Initialize the Voice AI service.

        Args:
            voice_ai_provider: The Voice AI provider to use
        """
        self.voice_ai_provider = voice_ai_provider

    async def create_outbound_call(
        self, request: CallRequest
    ) -> CallResponse | VoiceAIErrorResponse:
        """
        Create an outbound call.

        Note: This method only creates the call. Call monitoring and CRM updates
        should be handled by the CallAndWriteToCRMWorkflow orchestration layer.

        Args:
            request: The call request with phone number and context

        Returns:
            CallResponse or VoiceAIErrorResponse: The result of the operation
        """
        try:
            logger.info("Creating outbound call", phone_number=request.phone_number)
            result = await self.voice_ai_provider.create_outbound_call(request)
            logger.info(
                "Successfully created call",
                call_id=result.call_id,
                status=result.status,
            )
            return result
        except VoiceAIError as e:
            logger.error("Voice AI error creating call", error_message=e.message)
            return VoiceAIErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.voice_ai_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error("Unexpected error creating call", error=str(e))
            return VoiceAIErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code=VoiceAIErrorCode.UNKNOWN_ERROR,
                provider=getattr(self.voice_ai_provider, "provider_name", None),
            )

    async def get_call_status(
        self, call_id: str
    ) -> CallResponse | VoiceAIErrorResponse:
        """
        Get the status of a specific call.

        Args:
            call_id: The call identifier

        Returns:
            CallResponse or VoiceAIErrorResponse: The result of the operation
        """
        try:
            logger.info("Getting status for call", call_id=call_id)
            result = await self.voice_ai_provider.get_call_status(call_id)
            logger.info(
                "Successfully retrieved status for call",
                call_id=call_id,
                status=result.status,
            )
            return result
        except VoiceAIError as e:
            logger.error(
                "Voice AI error getting call", call_id=call_id, error_message=e.message
            )
            return VoiceAIErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.voice_ai_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error("Unexpected error getting call", call_id=call_id, error=str(e))
            return VoiceAIErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code=VoiceAIErrorCode.UNKNOWN_ERROR,
                provider=getattr(self.voice_ai_provider, "provider_name", None),
            )

    async def end_call(
        self,
        call_id: str,
        control_url: str | None = None,
        customer_call_sid: str | None = None,
    ) -> bool | VoiceAIErrorResponse:
        """
        End an ongoing call programmatically.

        Args:
            call_id: The call identifier
            control_url: Optional control URL for ending the call
            customer_call_sid: Optional customer call SID (for Twilio bridge architecture)

        Returns:
            bool (True if successful) or VoiceAIErrorResponse on error
        """
        try:
            logger.info(
                "Ending call",
                call_id=call_id,
                customer_call_sid=customer_call_sid,
            )
            # Pass customer_call_sid if provider supports it (Twilio-specific)
            # Other providers will ignore this parameter
            result = await self.voice_ai_provider.end_call(
                call_id, control_url=control_url, customer_call_sid=customer_call_sid
            )
            logger.info("Successfully ended call", call_id=call_id)
            return result
        except VoiceAIError as e:
            logger.error(
                "Voice AI error ending call", call_id=call_id, error_message=e.message
            )
            return VoiceAIErrorResponse(
                error=e.message,
                error_code=e.error_code,
                provider=getattr(self.voice_ai_provider, "provider_name", None),
            )
        except Exception as e:
            logger.error("Unexpected error ending call", call_id=call_id, error=str(e))
            return VoiceAIErrorResponse(
                error=f"Unexpected error: {str(e)}",
                error_code=VoiceAIErrorCode.UNKNOWN_ERROR,
                provider=getattr(self.voice_ai_provider, "provider_name", None),
            )

    async def download_recording(self, recording_url: str) -> tuple[bytes, str]:
        """
        Download a call recording from the voice AI provider.

        Args:
            recording_url: URL to the call recording

        Returns:
            tuple[bytes, str]: Tuple of (file_bytes, content_type)

        Raises:
            VoiceAIError: If the recording cannot be downloaded
        """
        logger.info("Downloading call recording", url=recording_url)
        result = await self.voice_ai_provider.download_recording(recording_url)
        logger.info(
            "Successfully downloaded recording",
            size_bytes=len(result[0]),
            content_type=result[1],
        )
        return result
