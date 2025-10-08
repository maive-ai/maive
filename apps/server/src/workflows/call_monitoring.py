"""
Call monitoring workflow for orchestrating Voice AI and CRM services.

This module provides workflow orchestration for creating and monitoring
voice AI calls, and updating CRM systems with call results.
"""

import asyncio

from src.ai.voice_ai.constants import CallStatus
from src.ai.voice_ai.schemas import (
    CallRequest,
    CallResponse,
    ClaimStatusData,
    VoiceAIErrorResponse,
)
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
            # Extract typed analysis data from provider response
            analysis = call_response.extract_analysis()

            if not analysis or not analysis.structured_data:
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
            note_text = self._format_crm_note(analysis.structured_data)

            # Add note to CRM job via service (no HTTP!)
            crm_result = await self.crm_service.add_job_note(
                job_id=job_id,
                text=note_text,
                pin_to_top=True,  # Pin important call results
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

    def _format_crm_note(self, structured_data: ClaimStatusData) -> str:
        """
        Format structured data into a CRM note.

        Args:
            structured_data: The extracted typed structured data

        Returns:
            Formatted note text
        """
        try:
            # Build formatted note
            note_lines = [
                "🤖 Voice AI Call Summary",
                "",
                f"Call Outcome: {structured_data.call_outcome}",
                f"Claim Status: {structured_data.claim_status}",
            ]

            # Add next steps if available
            if (
                structured_data.required_actions
                and structured_data.required_actions.next_steps
            ):
                note_lines.extend(
                    ["", "Next Steps:", structured_data.required_actions.next_steps]
                )

            # Add payment details if available
            if (
                structured_data.payment_details
                and structured_data.payment_details.status == "issued"
            ):
                note_lines.extend(
                    [
                        "",
                        "Payment Information:",
                        f"- Amount: ${structured_data.payment_details.amount or 'N/A'}",
                        f"- Issue Date: {structured_data.payment_details.issue_date or 'N/A'}",
                        f"- Check Number: {structured_data.payment_details.check_number or 'N/A'}",
                    ]
                )

            # Add required documents if any
            if (
                structured_data.required_actions
                and structured_data.required_actions.documents_needed
            ):
                note_lines.extend(["", "Required Documents:"])
                for doc in structured_data.required_actions.documents_needed:
                    note_lines.append(f"- {doc}")

            return "\n".join(note_lines)

        except Exception as e:
            logger.error(f"[Call Monitoring Workflow] Error formatting CRM note: {e}")
            # Fallback: return model as JSON
            return f"Voice AI Call Results:\n\n```json\n{structured_data.model_dump_json(indent=2)}\n```"
