"""
Twilio Voice AI provider implementation.
"""

from datetime import datetime
from typing import Any

from twilio.rest import Client
from twilio.rest.api.v2010.account.call import CallInstance

from src.ai.voice_ai.base import VoiceAIError
from src.ai.voice_ai.base import VoiceAIProvider as BaseVoiceAIProvider
from src.ai.voice_ai.constants import CallStatus
from src.ai.voice_ai.constants import VoiceAIProvider as VoiceAIProviderEnum
from src.ai.voice_ai.providers.twilio.client import TwilioVoiceClient
from src.ai.voice_ai.providers.twilio.config import TwilioWebhooks
from src.ai.voice_ai.schemas import CallRequest, CallResponse
from src.config import get_app_settings
from src.utils.logger import logger


class TwilioProvider(BaseVoiceAIProvider):
    """Twilio implementation of VoiceAIProvider interface."""

    provider_name = VoiceAIProviderEnum.TWILIO

    def __init__(self, twilio_client: Client, phone_number: str):
        """
        Initialize with shared client and org-specific phone.

        Args:
            twilio_client: Configured Twilio REST client (shared across tenants)
            phone_number: Organization's Twilio phone number (E.164 format)
        """
        self.client = TwilioVoiceClient(twilio_client)
        self.phone_number = phone_number
        self.settings = get_app_settings()
        self.webhooks = TwilioWebhooks()

    async def create_outbound_call(self, request: CallRequest) -> CallResponse:
        """
        Create outbound call using Twilio.

        Args:
            request: Call request with phone number and context

        Returns:
            CallResponse with call details

        Raises:
            VoiceAIError: If call creation fails
        """
        try:
            logger.info(
                "[TWILIO] Creating outbound call",
                to=request.phone_number,
                from_=self.phone_number,
            )

            call = await self.client.create_call(
                to=request.phone_number,
                from_=self.phone_number,
                url=self.webhooks.twiml_url(),
                record=True,
                recording_status_callback=self.webhooks.recording_status_callback,
                status_callback=self.webhooks.status_callback,
            )

            logger.info(
                "[TWILIO] Call created",
                call_sid=call.sid,
                status=call.status,
            )

            return CallResponse(
                call_id=call.sid,
                status=self._map_status(call.status),
                provider=VoiceAIProviderEnum.TWILIO,
                created_at=call.date_created,
                messages=[],
                provider_data=self._serialize_call(call),
            )

        except Exception as e:
            logger.error(
                "[TWILIO] Failed to create call",
                error=str(e),
                phone_number=request.phone_number,
            )
            raise VoiceAIError(f"Failed to create Twilio call: {e}") from e

    async def get_call_status(self, call_id: str) -> CallResponse:
        """
        Get the status of a specific call by ID.

        Args:
            call_id: Twilio Call SID

        Returns:
            CallResponse with current call status

        Raises:
            VoiceAIError: If call is not found
        """
        try:
            call = await self.client.get_call(call_id)
            return self._parse_call_response(call)

        except Exception as e:
            logger.error(
                "[TWILIO] Failed to get call status", call_sid=call_id, error=str(e)
            )
            raise VoiceAIError(f"Failed to get Twilio call status: {e}") from e

    async def end_call(self, call_id: str, control_url: str | None = None) -> bool:
        """
        End an ongoing call programmatically.

        Args:
            call_id: Twilio Call SID
            control_url: Unused for Twilio (kept for interface compatibility)

        Returns:
            True if call was successfully ended

        Raises:
            VoiceAIError: If call cannot be ended
        """
        try:
            logger.info("[TWILIO] Ending call", call_sid=call_id)
            await self.client.end_call(call_id)
            logger.info("[TWILIO] Call ended", call_sid=call_id)
            return True

        except Exception as e:
            logger.error("[TWILIO] Failed to end call", call_sid=call_id, error=str(e))
            raise VoiceAIError(f"Failed to end Twilio call: {e}") from e

    def _map_status(self, twilio_status: str) -> CallStatus:
        """
        Map Twilio call status to internal CallStatus enum.

        Args:
            twilio_status: Twilio status string

        Returns:
            Internal CallStatus enum value
        """
        status_map = {
            "queued": CallStatus.QUEUED,
            "ringing": CallStatus.RINGING,
            "in-progress": CallStatus.IN_PROGRESS,
            "completed": CallStatus.ENDED,
            "busy": CallStatus.BUSY,
            "no-answer": CallStatus.NO_ANSWER,
            "failed": CallStatus.FAILED,
            "canceled": CallStatus.CANCELED,
        }
        return status_map.get(twilio_status, CallStatus.FAILED)

    def _serialize_call(self, call: CallInstance) -> dict[str, Any]:
        """
        Serialize Twilio CallInstance to dictionary.

        Args:
            call: Twilio CallInstance

        Returns:
            Dictionary with call data
        """
        return {
            "sid": call.sid,
            "status": call.status,
            "to": call.to,
            "from": call.from_,
            "date_created": call.date_created.isoformat()
            if call.date_created
            else None,
            "date_updated": call.date_updated.isoformat()
            if call.date_updated
            else None,
            "duration": call.duration,
            "price": call.price,
            "direction": call.direction,
        }

    def _parse_call_response(self, call: CallInstance) -> CallResponse:
        """
        Parse Twilio CallInstance into CallResponse.

        Args:
            call: Twilio CallInstance

        Returns:
            CallResponse with parsed data
        """
        return CallResponse(
            call_id=call.sid,
            status=self._map_status(call.status),
            provider=VoiceAIProviderEnum.TWILIO,
            created_at=call.date_created
            if isinstance(call.date_created, datetime)
            else None,
            messages=[],
            provider_data=self._serialize_call(call),
        )
