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
from src.ai.voice_ai.providers.twilio.schemas import TwilioCall
from src.ai.voice_ai.schemas import CallRequest, CallResponse
from src.config import get_app_settings
from src.utils.logger import logger


def map_twilio_status(twilio_status: str) -> CallStatus:
    """
    Map Twilio call status to internal CallStatus enum.

    Args:
        twilio_status: Twilio status string (case-insensitive)

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
    return status_map.get(twilio_status.lower(), CallStatus.FAILED)


class TwilioProvider(BaseVoiceAIProvider):
    """Twilio implementation of VoiceAIProvider interface."""

    provider_name = VoiceAIProviderEnum.TWILIO

    def __init__(self, twilio_client: Client, phone_number: str, user_id: str):
        """
        Initialize with shared client, user-specific phone, and user ID.

        Args:
            twilio_client: Configured Twilio REST client (shared across tenants)
            phone_number: User's Twilio phone number (E.164 format)
            user_id: User ID for Twilio Device identity
        """
        self.client = TwilioVoiceClient(twilio_client)
        self.phone_number = phone_number
        self.user_id = user_id
        self.settings = get_app_settings()
        self.webhooks = TwilioWebhooks()

    async def create_outbound_call(self, request: CallRequest) -> CallResponse:
        """
        Create outbound call using Twilio with browser bridge.

        Creates call to browser first, then bridges to customer via status callback
        when browser answers.

        Args:
            request: Call request with phone number and context

        Returns:
            CallResponse with browser call details

        Raises:
            VoiceAIError: If call creation fails
        """
        try:
            # Generate unique conference name for this call
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            conference_name = f"call_{timestamp}_{self.user_id[:8]}"

            logger.info(
                "[TWILIO] Creating browser call",
                user_id=self.user_id,
                customer_phone=request.phone_number,
                conference=conference_name,
            )

            # Create call to browser first
            browser_call = await self.client.create_call(
                to=f"client:{self.user_id}",
                from_=self.phone_number,
                url=self.webhooks.twiml_url(conference_name),
                status_callback=self.webhooks.bridge_callback,
                status_callback_event=["answered"],
                status_callback_method="POST",
            )

            logger.info(
                "[TWILIO] Browser call created",
                call_sid=browser_call.sid,
                status=browser_call.status,
            )

            # Serialize call with conference and customer info for bridge callback
            provider_data = TwilioCall(
                sid=browser_call.sid,
                status=browser_call.status,
                to=f"client:{self.user_id}",
                from_number=getattr(browser_call, "_from", None),
                date_created=browser_call.date_created.isoformat()
                if browser_call.date_created
                else None,
                date_updated=browser_call.date_updated.isoformat()
                if browser_call.date_updated
                else None,
                duration=browser_call.duration,
                price=browser_call.price,
                direction=browser_call.direction,
                conference_name=conference_name,
                customer_phone=request.phone_number,
                user_phone=self.phone_number,
                customer_call_sid=None,
            )

            return CallResponse(
                call_id=browser_call.sid,
                status=map_twilio_status(browser_call.status),
                provider=VoiceAIProviderEnum.TWILIO,
                created_at=browser_call.date_created
                if browser_call.date_created
                else datetime.now(),
                messages=[],
                provider_data=provider_data,
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

    def _serialize_call(self, call: CallInstance) -> TwilioCall:
        """
        Serialize Twilio CallInstance to Pydantic model.

        Args:
            call: Twilio CallInstance

        Returns:
            TwilioCall Pydantic model with call data
        """
        return TwilioCall(
            sid=call.sid,
            status=call.status,
            to=call.to,
            from_number=getattr(call, "_from", None),
            date_created=call.date_created.isoformat() if call.date_created else None,
            date_updated=call.date_updated.isoformat() if call.date_updated else None,
            duration=call.duration,
            price=call.price,
            direction=call.direction,
        )

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
            status=map_twilio_status(call.status),
            provider=VoiceAIProviderEnum.TWILIO,
            created_at=call.date_created
            if isinstance(call.date_created, datetime)
            else None,
            messages=[],
            provider_data=self._serialize_call(call),
        )
