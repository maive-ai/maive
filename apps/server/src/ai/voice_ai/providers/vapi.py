"""
Vapi provider implementation for Voice AI operations.

This module implements the VoiceAIProvider interface for Vapi.
"""

import asyncio
import json
from http import HTTPStatus
from typing import Any, Optional

import httpx
import phonenumbers
from pydantic import ValidationError

from src.ai.voice_ai.base import VoiceAIError, VoiceAIProvider
from src.ai.voice_ai.config import get_vapi_settings, get_voice_ai_settings
from src.ai.voice_ai.constants import CallStatus, VoiceAIErrorCode, WebhookEventType
from src.ai.voice_ai.constants import VoiceAIProvider as VoiceAIProviderEnum
from src.ai.voice_ai.providers.vapi_schemas import (
    VapiCallData,
    VapiClaimStatusData,
    VapiEndpoints,
    VapiMessage,
    VapiWebhookPayload,
)
from src.ai.voice_ai.schemas import (
    CallEndedData,
    CallRequest,
    CallResponse,
    CallStartedData,
    ConversationUpdateData,
    FunctionCallData,
    SpeechUpdateData,
    StatusUpdateData,
    TranscriptData,
    WebhookEvent,
    WebhookEventData,
)
from src.integrations.crm.constants import ClaimStatus
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

        # Construct endpoint URLs once
        self._call_endpoint = f"{self._vapi_settings.base_url}{VapiEndpoints.CALL}"
        self._call_by_id_endpoint = (
            lambda call_id: f"{self._vapi_settings.base_url}{VapiEndpoints.CALL_BY_ID.format(call_id=call_id)}"
        )

    async def create_outbound_call(self, request: CallRequest) -> CallResponse:
        """
        Create outbound call via Vapi REST API.

        Args:
            request: The call request with phone number and context

        Returns:
            CallResponse: The call response with call_id and status

        Raises:
            VoiceAIError: If the call creation fails
        """
        headers = self._build_headers()
        payload = self._build_call_payload(request)

        logger.info(f"[Vapi Provider] Creating outbound call to {request.phone_number}")

        try:
            async with httpx.AsyncClient(
                timeout=self._voice_ai_settings.request_timeout
            ) as client:
                response = await client.post(
                    self._call_endpoint,
                    headers=headers,
                    json=payload,
                )

                if response.status_code != HTTPStatus.CREATED:
                    error_msg = (
                        f"Vapi API error: {response.status_code} - {response.text}"
                    )
                    logger.error(f"[Vapi Provider] {error_msg}")
                    raise VoiceAIError(
                        error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR
                    )

                return self._parse_call_response(response.json())
        except httpx.HTTPError as e:
            error_msg = f"HTTP error creating call: {str(e)}"
            logger.error(f"[Vapi Provider] {error_msg}")
            raise VoiceAIError(error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR)

    async def verify_webhook(self, headers: dict[str, str], body: str) -> bool:
        """
        Verify Vapi webhook authenticity.

        Args:
            headers: HTTP headers from the webhook request
            body: Raw body of the webhook request

        Returns:
            bool: True if webhook is authentic, False otherwise
        """
        if not self._vapi_settings.require_webhook_verification:
            logger.info("[Vapi Provider] Webhook verification disabled")
            return True

        if not self._vapi_settings.webhook_secret:
            logger.warning("[Vapi Provider] No webhook secret configured")
            return False

        vapi_secret = headers.get("x-vapi-secret")
        is_valid = vapi_secret == self._vapi_settings.webhook_secret

        if not is_valid:
            logger.warning("[Vapi Provider] Webhook verification failed")

        return is_valid

    async def parse_webhook(self, headers: dict[str, str], body: str) -> WebhookEvent:
        """
        Parse Vapi webhook payload into standard format.

        Args:
            headers: HTTP headers from the webhook request
            body: Raw body of the webhook request

        Returns:
            WebhookEvent: Parsed webhook event with standard structure

        Raises:
            VoiceAIError: If webhook parsing fails
        """
        try:
            raw_data = json.loads(body)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in webhook: {str(e)}"
            logger.error(f"[Vapi Provider] {error_msg}")
            raise VoiceAIError(error_msg, error_code=VoiceAIErrorCode.INVALID_JSON)

        try:
            vapi_payload = VapiWebhookPayload(**raw_data)
        except ValidationError as e:
            error_msg = f"Invalid webhook payload structure: {str(e)}"
            logger.error(f"[Vapi Provider] {error_msg}")
            raise VoiceAIError(error_msg, error_code=VoiceAIErrorCode.INVALID_JSON)

        message = vapi_payload.message
        vapi_event_type = message.type
        call_id = message.call.id if message.call else None

        if not call_id:
            logger.warning(
                f"[Vapi Provider] No call_id found in webhook. Event type: {vapi_event_type}"
            )

        event_type = self._map_vapi_event_type(vapi_event_type)
        event_data = self._extract_event_data(event_type, message, vapi_payload)

        return WebhookEvent(
            event_type=event_type,
            call_id=call_id,
            data=event_data,
            provider_data=raw_data,
        )

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
        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(
                timeout=self._voice_ai_settings.request_timeout
            ) as client:
                response = await client.get(
                    self._call_by_id_endpoint(call_id),
                    headers=headers,
                )

                if response.status_code == HTTPStatus.NOT_FOUND:
                    raise VoiceAIError(
                        f"Call {call_id} not found",
                        error_code=VoiceAIErrorCode.NOT_FOUND,
                    )

                if response.status_code != HTTPStatus.OK:
                    error_msg = (
                        f"Vapi API error: {response.status_code} - {response.text}"
                    )
                    logger.error(f"[Vapi Provider] {error_msg}")
                    raise VoiceAIError(
                        error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR
                    )

                return self._parse_call_response(response.json())
        except httpx.HTTPError as e:
            error_msg = f"HTTP error getting call status: {str(e)}"
            logger.error(f"[Vapi Provider] {error_msg}")
            raise VoiceAIError(error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR)

    async def end_call(self, call_id: str) -> bool:
        """
        End an ongoing call programmatically.

        First fetches call details to get the controlUrl, then sends end-call command.

        Args:
            call_id: The unique identifier for the call

        Returns:
            bool: True if call was successfully ended

        Raises:
            VoiceAIError: If the call is not found or cannot be ended
        """
        # Step 1: Get call details to extract controlUrl
        call_response = await self.get_call_status(call_id)

        if not call_response.provider_data:
            raise VoiceAIError(
                "No provider data available", error_code=VoiceAIErrorCode.NOT_FOUND
            )

        # Parse provider data with typed model
        vapi_data = VapiCallData(**call_response.provider_data)

        if not vapi_data.monitor or not vapi_data.monitor.control_url:
            raise VoiceAIError(
                f"No control URL found for call {call_id}",
                error_code=VoiceAIErrorCode.NOT_FOUND,
            )

        control_url = vapi_data.monitor.control_url

        # Step 2: Send end-call command
        headers = {"Content-Type": "application/json"}
        payload = {"type": "end-call"}

        logger.info(f"[Vapi Provider] Ending call {call_id}")

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
                    logger.error(f"[Vapi Provider] {error_msg}")
                    raise VoiceAIError(
                        error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR
                    )

                logger.info(f"[Vapi Provider] Successfully ended call {call_id}")
                return True

        except httpx.HTTPError as e:
            error_msg = f"HTTP error ending call: {str(e)}"
            logger.error(f"[Vapi Provider] {error_msg}")
            raise VoiceAIError(error_msg, error_code=VoiceAIErrorCode.HTTP_ERROR)

    async def monitor_ongoing_call(
        self, call_id: str, call_request: CallRequest
    ) -> None:
        """
        Poll call status every 10s up to 24h; log structured data when call ends.

        Note: This method is deprecated and will be removed in a future version.
        Use the CallAndWriteToCRMWorkflow instead for proper orchestration.
        """
        poll_interval_seconds = 10
        max_polling_duration = 60 * 60 * 24  # 24 hours
        start_time = asyncio.get_event_loop().time()

        try:
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_polling_duration:
                    logger.warning(
                        f"[Vapi Provider] Monitoring timed out for call {call_id}"
                    )
                    break

                try:
                    status = await self.get_call_status(call_id)
                except VoiceAIError as e:
                    logger.error(
                        f"[Vapi Provider] Error polling call {call_id}: {e.message}"
                    )
                    break

                logger.info(f"[Vapi Provider] Call {call_id} status: {status.status}")

                # End condition
                if CallStatus.is_call_ended(status.status):
                    # Log structured data if available
                    self._handle_call_ended(call_id, status.provider_data or {})
                    break

                await asyncio.sleep(poll_interval_seconds)
        except asyncio.CancelledError:
            logger.info(f"[Vapi Provider] Monitoring task for call {call_id} canceled")

    def _handle_call_ended(
        self, call_id: str, provider_data: dict[str, Any]
    ) -> Optional[VapiClaimStatusData]:
        """Extract and log structured data from provider response (if present)."""
        try:
            analysis = provider_data.get("analysis") or {}
            structured = analysis.get("structuredData")
            if structured:
                structured = VapiClaimStatusData(**structured)
                logger.info(
                    f"[Vapi Provider] Structured data for call {call_id}: {structured}"
                )
                return structured
            else:
                logger.info(
                    f"[Vapi Provider] No structured data found for call {call_id}"
                )
                return None
        except Exception as e:
            logger.error(
                f"[Vapi Provider] Error logging structured data for call {call_id}: {e}"
            )
            return None

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for Vapi API requests."""
        return {
            "Authorization": f"Bearer {self._vapi_settings.api_key}",
            "Content-Type": "application/json",
        }

    def _map_vapi_event_type(self, vapi_event_type: str | None) -> WebhookEventType:
        """
        Map Vapi event type strings to standard WebhookEventType enum.

        Args:
            vapi_event_type: Vapi-specific event type string (or None)

        Returns:
            WebhookEventType: Mapped standard event type, or ERROR if not found/None
        """
        event_mapping = {
            "call.started": WebhookEventType.CALL_STARTED,
            "call.ended": WebhookEventType.CALL_ENDED,
            "end-of-call-report": WebhookEventType.CALL_ENDED,
            "function-call": WebhookEventType.FUNCTION_CALL,
            "transcript": WebhookEventType.TRANSCRIPT,
            "speech-update": WebhookEventType.SPEECH_UPDATE,
            "conversation-update": WebhookEventType.CONVERSATION_UPDATE,
            "status-update": WebhookEventType.STATUS_UPDATE,
        }
        return event_mapping.get(vapi_event_type, WebhookEventType.ERROR)

    def _extract_event_data(
        self,
        event_type: WebhookEventType,
        message: VapiMessage,
        vapi_payload: VapiWebhookPayload,
    ) -> WebhookEventData:
        """
        Extract event-specific data from webhook payload.

        Args:
            event_type: The standard event type
            message: Parsed Vapi message object
            vapi_payload: Complete Vapi webhook payload

        Returns:
            WebhookEventData: Typed event-specific data
        """
        if event_type is WebhookEventType.CALL_STARTED:
            return CallStartedData(
                customer_number=message.customer.number if message.customer else None,
                assistant_id=message.assistant.id if message.assistant else None,
            )

        if event_type is WebhookEventType.CALL_ENDED:
            return CallEndedData(
                duration=message.duration_seconds,
                transcript=message.transcript,
                end_reason=message.ended_reason,
                artifact=message.artifact,
                analysis=message.analysis.structured_data if message.analysis else None,
                vapi_payload=vapi_payload.model_dump(),
            )

        if event_type is WebhookEventType.FUNCTION_CALL:
            # Function data is at root level of webhook
            return FunctionCallData(
                function_name=vapi_payload.function.name
                if vapi_payload.function
                else None,
                parameters=vapi_payload.function.parameters
                if vapi_payload.function
                else None,
            )

        if event_type is WebhookEventType.TRANSCRIPT:
            # Transcript events have data at root level
            return TranscriptData(
                transcript=vapi_payload.transcript,
                is_partial=vapi_payload.is_partial,
            )

        if event_type is WebhookEventType.SPEECH_UPDATE:
            # Speech update events have data at root level
            return SpeechUpdateData(
                status=vapi_payload.status,
                role=vapi_payload.role,
                turn=vapi_payload.turn,
            )

        if event_type is WebhookEventType.CONVERSATION_UPDATE:
            # Conversation can be at root or in message
            return ConversationUpdateData(
                conversation=vapi_payload.conversation,
                messages=message.messages,
            )

        if event_type is WebhookEventType.STATUS_UPDATE:
            # Status updates have data at root level
            return StatusUpdateData(
                status=vapi_payload.status,
                ended_reason=vapi_payload.ended_reason,
            )

        # Fallback for unknown/unhandled event types
        logger.warning(
            f"[Vapi Provider] Unhandled event type: {event_type}. Returning empty data."
        )
        return {}

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
                f"[Vapi Provider] Could not parse phone number: {phone_number}"
            )

        # Fallback: return as-is if parsing fails
        return phone_number

    def _build_call_payload(self, request: CallRequest) -> dict[str, Any]:
        """Build the complete call payload with customer context and structured outputs."""
        formatted_phone = self._format_phone_number(request.phone_number)
        payload: dict[str, Any] = {
            "assistantId": self._vapi_settings.default_assistant_id,
            "phoneNumberId": self._vapi_settings.phone_number_id,
            "customer": {"number": formatted_phone},
        }

        # Add assistant overrides
        assistant_overrides = self._build_assistant_overrides(request)
        if assistant_overrides:
            payload["assistantOverrides"] = assistant_overrides

        # Build metadata with customer_id
        metadata: dict[str, Any] = {}
        if request.customer_id:
            metadata["customer_id"] = request.customer_id
        if request.metadata:
            metadata.update(request.metadata)

        if metadata:
            payload["metadata"] = metadata

        return payload

    def _build_assistant_overrides(self, request: CallRequest) -> dict[str, Any]:
        """Build assistant overrides with customer variables and structured outputs."""
        overrides: dict[str, Any] = {}

        # Add customer context variables
        variable_values = self._extract_customer_variables(request)
        if variable_values:
            overrides["variableValues"] = variable_values

        # Add structured data extraction
        overrides["analysisPlan"] = self._build_claim_status_structured_data()

        return overrides

    def _extract_customer_variables(self, request: CallRequest) -> dict[str, str]:
        """Extract customer context variables from request."""
        variable_values: dict[str, str] = {}

        if request.customer_name:
            variable_values["customer_name"] = request.customer_name
        if request.customer_address:
            variable_values["customer_address"] = request.customer_address
        if request.claim_number:
            variable_values["claim_number"] = request.claim_number
        if request.date_of_loss:
            variable_values["date_of_loss"] = request.date_of_loss
        if request.insurance_agency:
            variable_values["insurance_agency"] = request.insurance_agency
        if request.adjuster_name:
            variable_values["adjuster_name"] = request.adjuster_name
        if request.adjuster_phone:
            variable_values["adjuster_phone"] = request.adjuster_phone
        if request.job_id:
            variable_values["job_id"] = request.job_id
        if request.tenant:
            variable_values["tenant"] = request.tenant

        return variable_values

    def _build_claim_status_structured_data(self) -> dict[str, Any]:
        """Build analysis plan for claim status structured data extraction."""
        structured_data_prompt = "Extract insurance claim status information from this call transcript. Focus on: claim status (approved/denied/pending), payment details (amount, date, check number), required documents, and next steps."

        return {
            "structuredDataPrompt": structured_data_prompt,
            "structuredDataSchema": {
                "type": "object",
                "properties": {
                    "call_outcome": {
                        "type": "string",
                        "enum": ["success", "voicemail", "gatekeeper", "failed"],
                        "description": "How the call ended",
                    },
                    "claim_status": {
                        "type": "string",
                        "enum": [status.value for status in ClaimStatus],
                        "description": f"Current status of the insurance claim. Options: {', '.join([f'{s.value} ({s.description})' for s in ClaimStatus])}",
                    },
                    "payment_details": {
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "enum": ["issued", "not_issued", "pending"],
                                "description": "Payment status",
                            },
                            "amount": {
                                "type": "number",
                                "description": "Payment amount if mentioned",
                            },
                            "issue_date": {
                                "type": "string",
                                "format": "date",
                                "description": "Date payment was issued",
                            },
                            "check_number": {
                                "type": "string",
                                "description": "Check number if provided",
                            },
                        },
                    },
                    "required_actions": {
                        "type": "object",
                        "properties": {
                            "documents_needed": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of documents required",
                            },
                            "submission_method": {
                                "type": "string",
                                "enum": ["email", "portal", "mail"],
                                "description": "How to submit documents",
                            },
                            "next_steps": {
                                "type": "string",
                                "description": "Summary of next actions needed",
                            },
                        },
                    },
                },
                "required": ["call_outcome", "claim_status"],
            },
        }

    def _parse_call_response(self, vapi_data: dict[str, Any]) -> CallResponse:
        """Parse Vapi call response into standard format."""
        # Parse into typed model first
        call_data = VapiCallData(**vapi_data)

        # Map Vapi status strings to standard CallStatus enum
        vapi_status = (call_data.status or "").lower()
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

        return CallResponse(
            call_id=call_data.id,
            status=status,
            provider=VoiceAIProviderEnum.VAPI,
            created_at=call_data.created_at,
            provider_data=vapi_data,
        )
