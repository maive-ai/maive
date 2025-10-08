"""
Call monitoring workflow for orchestrating Voice AI and CRM services.

This module provides workflow orchestration for creating and monitoring
voice AI calls, and updating CRM systems with call results.
"""

import asyncio
import json
from typing import Any

from src.ai.voice_ai.constants import CallStatus
from src.ai.voice_ai.schemas import CallRequest, CallResponse, VoiceAIErrorResponse
from src.ai.voice_ai.service import VoiceAIService
from src.integrations.crm.service import CRMService
from src.utils.logger import logger


class CallMonitoringWorkflow:
    """Orchestrates Voice AI call creation and CRM updates."""

    def __init__(
        self,
        voice_ai_service: VoiceAIService,
        crm_service: CRMService,
    ):
        """
        Initialize the call monitoring workflow.

        Args:
            voice_ai_service: Service for Voice AI operations
            crm_service: Service for CRM operations
        """
        self.voice_ai_service = voice_ai_service
        self.crm_service = crm_service

    async def create_and_monitor_call(
        self,
        request: CallRequest,
        user_id: str | None = None,
    ) -> CallResponse | VoiceAIErrorResponse:
        """
        Create an outbound call and start monitoring it.

        This method orchestrates:
        1. Creating the call via Voice AI service
        2. Starting background monitoring
        3. Updating CRM when call completes

        Args:
            request: The call request with phone number and context
            user_id: The ID of the user creating the call (for audit trails)

        Returns:
            CallResponse or VoiceAIErrorResponse: The result of the operation
        """
        # Create the call
        result = await self.voice_ai_service.create_outbound_call(request)

        if isinstance(result, VoiceAIErrorResponse):
            return result

        # Start background monitoring
        try:
            asyncio.create_task(
                self._monitor_and_update_crm(
                    call_id=result.call_id,
                    request=request,
                    user_id=user_id,
                )
            )
            logger.info(
                f"[Call Monitoring Workflow] Started monitoring for call {result.call_id}"
            )
        except Exception as e:
            logger.error(
                f"[Call Monitoring Workflow] Failed to start monitoring task for call {result.call_id}: {e}"
            )

        return result

    async def _monitor_and_update_crm(
        self,
        call_id: str,
        request: CallRequest,
        user_id: str | None,
    ) -> None:
        """
        Monitor call status and update CRM when call completes.

        Polls call status every 10 seconds until the call reaches a terminal state,
        then extracts structured data and updates the CRM job note.

        Args:
            call_id: The call identifier to monitor
            request: The original call request (contains tenant/job_id)
            user_id: The ID of the user who created the call
        """
        poll_interval_seconds = 10
        max_polling_duration = 60 * 60 * 24  # 24 hours
        start_time = asyncio.get_event_loop().time()

        try:
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > max_polling_duration:
                    logger.warning(
                        f"[Call Monitoring Workflow] Monitoring timed out for call {call_id}"
                    )
                    break

                # Poll call status
                status_result = await self.voice_ai_service.get_call_status(call_id)

                if isinstance(status_result, VoiceAIErrorResponse):
                    logger.error(
                        f"[Call Monitoring Workflow] Error polling call {call_id}: {status_result.error}"
                    )
                    break

                logger.info(
                    f"[Call Monitoring Workflow] Call {call_id} status: {status_result.status}"
                )

                # Check if call has ended
                if CallStatus.is_call_ended(status_result.status):
                    logger.info(
                        f"[Call Monitoring Workflow] Call {call_id} ended with status: {status_result.status}"
                    )

                    # Extract structured data and update CRM
                    await self._process_completed_call(
                        call_id=call_id,
                        call_response=status_result,
                        request=request,
                        user_id=user_id,
                    )
                    break

                await asyncio.sleep(poll_interval_seconds)

        except asyncio.CancelledError:
            logger.info(
                f"[Call Monitoring Workflow] Monitoring task for call {call_id} canceled"
            )
        except Exception as e:
            logger.error(
                f"[Call Monitoring Workflow] Unexpected error monitoring call {call_id}: {e}"
            )

    async def _process_completed_call(
        self,
        call_id: str,
        call_response: CallResponse,
        request: CallRequest,
        user_id: str | None,
    ) -> None:
        """
        Process a completed call and update CRM with structured data.

        Args:
            call_id: The call identifier
            call_response: The final call response with provider data
            request: The original call request (contains tenant/job_id)
            user_id: The ID of the user who created the call
        """
        try:
            # Extract structured data from provider response
            structured_data = self._extract_structured_data(call_response.provider_data)

            if not structured_data:
                logger.info(
                    f"[Call Monitoring Workflow] No structured data found for call {call_id}"
                )
                return

            logger.info(
                f"[Call Monitoring Workflow] Extracted structured data for call {call_id}"
            )

            # Update CRM if we have tenant and job_id
            tenant = request.tenant
            job_id = request.job_id

            if tenant is None or job_id is None:
                logger.info(
                    f"[Call Monitoring Workflow] Missing tenant/job_id for call {call_id}; skipping CRM note"
                )
                return

            # Format note text from structured data
            note_text = self._format_crm_note(structured_data)

            # Add note to CRM job via service (no HTTP!)
            crm_result = await self.crm_service.add_job_note(
                job_id=job_id,
                text=note_text,
                pin_to_top=True,  # Pin important call results
                user_id=None,  # System-generated note
            )

            if hasattr(crm_result, "error"):
                logger.error(
                    f"[Call Monitoring Workflow] Failed to add job note for job {job_id}: {crm_result.error}"
                )
            else:
                logger.info(
                    f"[Call Monitoring Workflow] Successfully added CRM note for job {job_id}"
                )

        except Exception as e:
            logger.error(
                f"[Call Monitoring Workflow] Error processing completed call {call_id}: {e}"
            )

    def _extract_structured_data(
        self, provider_data: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """
        Extract structured data from provider response.

        This handles provider-specific data extraction. Currently supports Vapi format.

        Args:
            provider_data: Raw provider response data

        Returns:
            Extracted structured data or None if not found
        """
        if not provider_data:
            return None

        try:
            # Vapi format: analysis.structuredData
            analysis = provider_data.get("analysis") or {}
            structured = analysis.get("structuredData")

            if structured:
                logger.debug(
                    f"[Call Monitoring Workflow] Found structured data: {structured}"
                )
                return structured

            return None

        except Exception as e:
            logger.error(
                f"[Call Monitoring Workflow] Error extracting structured data: {e}"
            )
            return None

    def _format_crm_note(self, structured_data: dict[str, Any]) -> str:
        """
        Format structured data into a CRM note.

        Args:
            structured_data: The extracted structured data

        Returns:
            Formatted note text
        """
        try:
            # Extract key fields
            call_outcome = structured_data.get("call_outcome", "unknown")
            claim_status = structured_data.get("claim_status", "unknown")
            required_actions = structured_data.get("required_actions", {})
            next_steps = required_actions.get("next_steps", "")

            # Build formatted note
            note_lines = [
                "🤖 Voice AI Call Summary",
                "",
                f"**Call Outcome:** {call_outcome}",
                f"**Claim Status:** {claim_status}",
            ]

            if next_steps:
                note_lines.extend(["", "**Next Steps:**", next_steps])

            # Add payment details if available
            payment = structured_data.get("payment_details")
            if payment and payment.get("status") == "issued":
                note_lines.extend(
                    [
                        "",
                        "**Payment Information:**",
                        f"- Amount: ${payment.get('amount', 'N/A')}",
                        f"- Issue Date: {payment.get('issue_date', 'N/A')}",
                        f"- Check Number: {payment.get('check_number', 'N/A')}",
                    ]
                )

            # Add required documents if any
            documents = required_actions.get("documents_needed", [])
            if documents:
                note_lines.extend(["", "**Required Documents:**"])
                for doc in documents:
                    note_lines.append(f"- {doc}")

            return "\n".join(note_lines)

        except Exception as e:
            logger.error(
                f"[Call Monitoring Workflow] Error formatting CRM note: {e}"
            )
            # Fallback: return raw JSON
            return f"Voice AI Call Results:\n\n```json\n{json.dumps(structured_data, indent=2)}\n```"
