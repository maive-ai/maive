"""
Vapi provider implementation for Voice AI operations.

This module implements the VoiceAIProvider interface for Vapi.
"""

from http import HTTPStatus
from typing import Any

import httpx
import phonenumbers
from vapi import AsyncVapi
from vapi.types import (
    AssistantOverrides,
    BotMessage,
    CallMessagesItem,
    CreateCustomerDto,
    UserMessage,
)
from vapi.types import (
    Call as VapiCall,
)
from vapi.types.analysis import Analysis

from src.ai.voice_ai.base import VoiceAIError, VoiceAIProvider
from src.ai.voice_ai.config import get_vapi_settings, get_voice_ai_settings
from src.ai.voice_ai.constants import CallStatus, VoiceAIErrorCode
from src.ai.voice_ai.constants import VoiceAIProvider as VoiceAIProviderEnum
from src.ai.voice_ai.schemas import (
    AnalysisData,
    CallRequest,
    CallResponse,
    ClaimStatusData,
)
from src.integrations.crm.constants import Status
from src.utils.logger import logger


class VapiProvider(VoiceAIProvider):
    """Vapi-specific implementation of Voice AI provider."""

    def __init__(self):
        """Initialize the Vapi provider with configuration."""
        self._voice_ai_settings = get_voice_ai_settings()
        self._vapi_settings = get_vapi_settings()
        self.provider_name = VoiceAIProviderEnum.VAPI

        if not self._vapi_settings.api_key:
            raise ValueError("VAPI_API_KEY environment variable is required")

        # Initialize Vapi SDK client
        self._client = AsyncVapi(
            token=self._vapi_settings.api_key,
            base_url=self._vapi_settings.base_url,
            timeout=self._voice_ai_settings.request_timeout,
        )

    async def create_outbound_call(self, request: CallRequest) -> CallResponse:
        """
        Create outbound call via Vapi SDK.

        Args:
            request: The call request with phone number and context

        Returns:
            CallResponse: The call response with call_id and status

        Raises:
            VoiceAIError: If the call creation fails
        """
        logger.info(
            "[Vapi Provider] Creating outbound call", phone_number=request.phone_number
        )

        try:
            # Build typed objects for SDK
            formatted_phone = self._format_phone_number(request.phone_number)
            customer = CreateCustomerDto(
                number=formatted_phone,
                external_id=request.customer_id,  # Use external_id for customer_id tracking
            )
            assistant_overrides = self._build_assistant_overrides(request)

            # Use squad_id or assistant_id based on configuration
            _use_squad = self._vapi_settings.use_squad
            _default_assistant_id = self._vapi_settings.default_assistant_id
            squad_id = None
            assistant_id = None
            if _use_squad:
                squad_id = _default_assistant_id
            else:
                assistant_id = _default_assistant_id

            # Create call
            call: VapiCall = await self._client.calls.create(
                squad_id=squad_id,
                assistant_id=assistant_id,
                phone_number_id=self._vapi_settings.phone_number_id,
                customer=customer,
                assistant_overrides=assistant_overrides,
            )

            # Return call response using SDK's Call object directly
            return self._parse_call_response(call)

        except Exception as e:
            error_msg = f"Error creating call: {str(e)}"
            logger.error("[Vapi Provider] Error creating call", error=str(e))
            raise VoiceAIError(error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR)

    async def get_call_status(self, call_id: str) -> CallResponse:
        """
        Get the status of a specific call by ID using Vapi SDK.

        Args:
            call_id: The unique identifier for the call

        Returns:
            CallResponse: The call status information

        Raises:
            VoiceAIError: If the call is not found or an error occurs
        """
        try:
            # Get call using SDK
            call = await self._client.calls.get(id=call_id)

            # Return call response using SDK's Call object directly
            return self._parse_call_response(call)

        except Exception as e:
            error_msg = f"Error getting call status: {str(e)}"
            logger.error("[Vapi Provider] Error getting call status", error=str(e))
            raise VoiceAIError(error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR)

    async def end_call(
        self,
        call_id: str,
        control_url: str | None = None,
        customer_call_sid: str | None = None,
    ) -> bool:
        """
        End an ongoing call programmatically using Vapi's control URL.

        Args:
            call_id: The unique identifier for the call
            control_url: Optional control URL. If not provided, will fetch from call status.
            customer_call_sid: Unused for Vapi (kept for interface compatibility with Twilio)

        Returns:
            bool: True if call was successfully ended

        Raises:
            VoiceAIError: If the call is not found or cannot be ended
        """
        logger.info("[Vapi Provider] Ending call", call_id=call_id)

        # If control_url not provided, fetch it from call status
        if not control_url:
            call_response = await self.get_call_status(call_id)

            if not call_response.provider_data:
                raise VoiceAIError(
                    "No provider data available", error_code=VoiceAIErrorCode.NOT_FOUND
                )

            # Use VapiCall object directly (strongly typed)
            vapi_data: VapiCall = call_response.provider_data

            if not vapi_data.monitor or not vapi_data.monitor.control_url:
                raise VoiceAIError(
                    f"No control URL found for call {call_id}",
                    error_code=VoiceAIErrorCode.NOT_FOUND,
                )

            control_url = vapi_data.monitor.control_url

        # Send end-call command to control URL
        headers = {"Content-Type": "application/json"}
        payload = {"type": "end-call"}

        logger.info(
            "[Vapi Provider] Sending end-call to control URL", control_url=control_url
        )

        try:
            async with httpx.AsyncClient(
                timeout=self._voice_ai_settings.request_timeout
            ) as client:
                response = await client.post(
                    control_url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code not in (HTTPStatus.OK, HTTPStatus.ACCEPTED):
                    error_msg = (
                        f"Failed to end call: {response.status_code} - {response.text}"
                    )
                    logger.error(
                        "[Vapi Provider] Failed to end call",
                        status_code=response.status_code,
                        response_text=response.text,
                    )
                    raise VoiceAIError(
                        error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR
                    )

                logger.info("[Vapi Provider] Successfully ended call", call_id=call_id)
                return True

        except httpx.HTTPError as e:
            error_msg = f"HTTP error ending call: {str(e)}"
            logger.error("[Vapi Provider] HTTP error ending call", error=str(e))
            raise VoiceAIError(error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR)

    def _format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number to E.164 format.

        Defaults to US region if no country code is provided.

        Args:
            phone_number: Phone number string in any format

        Returns:
            str: E.164 formatted phone number (e.g., +15551234567)
        """
        try:
            # Try parsing with explicit region (US default)
            parsed = phonenumbers.parse(phone_number, "US")

            # Validate the number
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )

            # If invalid, try parsing without region (assumes international format)
            parsed = phonenumbers.parse(phone_number, None)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(
                    parsed, phonenumbers.PhoneNumberFormat.E164
                )

        except phonenumbers.NumberParseException:
            logger.warning(
                "[Vapi Provider] Could not parse phone number",
                phone_number=phone_number,
            )

        # Fallback: return as-is if parsing fails
        return phone_number

    def _build_assistant_overrides(self, request: CallRequest) -> AssistantOverrides:
        """Build assistant overrides with customer variables."""
        # Extract customer context variables
        variable_values = self._extract_customer_variables(request)

        # Log the variables being passed to Vapi
        logger.info(
            "[Vapi Provider] Passing customer context to Vapi assistant",
            variable_values=variable_values,
        )

        # Return typed AssistantOverrides object
        return AssistantOverrides(
            variable_values=variable_values if variable_values else None,
        )

    def _extract_customer_variables(self, request: CallRequest) -> dict[str, Any]:
        """Extract customer context variables from request using Pydantic model_dump."""
        # Use model_dump to get all fields, excluding None values and specific fields
        # we don't want in variable_values (phone_number is used for customer,
        # metadata is handled separately, customer_id goes in main metadata)
        return request.model_dump(
            exclude_none=True,
            exclude={"phone_number", "metadata", "customer_id"},
        )

    def _parse_call_response(self, call: VapiCall) -> CallResponse:
        """Parse Vapi SDK Call object into standard CallResponse format."""
        # Map Vapi status strings to standard CallStatus enum
        vapi_status = (call.status or "").lower()
        status_mapping = {
            "queued": CallStatus.QUEUED,
            "ringing": CallStatus.RINGING,
            "in-progress": CallStatus.IN_PROGRESS,
            "ended": CallStatus.ENDED,
            "busy": CallStatus.BUSY,
            "no-answer": CallStatus.NO_ANSWER,
            "failed": CallStatus.FAILED,
            "canceled": CallStatus.CANCELED,
        }
        status = status_mapping.get(vapi_status, CallStatus.QUEUED)

        # Store VapiCall object directly - provides strong typing
        provider_data: VapiCall = call

        # Parse messages from Vapi format to provider-agnostic format
        messages = self._parse_messages(call.messages) if call.messages else []

        # Get analysis data if available
        analysis_data = None
        analysis: Analysis = call.analysis

        if analysis is not None:
            _structured_data = (
                ClaimStatusData.from_vapi(analysis.structured_data)
                if analysis.structured_data is not None
                else None
            )
            analysis_data = AnalysisData(
                summary=analysis.summary,
                structured_data=_structured_data,
                success_evaluation=analysis.success_evaluation,
            )

        return CallResponse(
            call_id=call.id,
            status=status,
            provider=VoiceAIProviderEnum.VAPI,
            created_at=call.created_at,
            provider_data=provider_data,
            analysis=analysis_data,
            messages=messages,
        )

    def _parse_messages(self, vapi_messages: list[CallMessagesItem]) -> list:
        """
        Parse Vapi-specific message types into provider-agnostic format.

        Args:
            vapi_messages: List of Vapi CallMessagesItem (UserMessage, BotMessage, etc.)

        Returns:
            List of provider-agnostic TranscriptMessage objects
        """
        from src.ai.voice_ai.schemas import TranscriptMessage

        messages = []
        for msg in vapi_messages:
            # Only process UserMessage and BotMessage (which have transcript content)
            if isinstance(msg, (UserMessage, BotMessage)):
                # Unpack Vapi message directly into our schema
                messages.append(
                    TranscriptMessage(
                        role=msg.role,
                        content=msg.message,
                        timestamp_seconds=msg.seconds_from_start,
                        duration_seconds=msg.duration,
                    )
                )
            # ToolCallMessage, SystemMessage, etc. don't have user/bot transcript content

        return messages
