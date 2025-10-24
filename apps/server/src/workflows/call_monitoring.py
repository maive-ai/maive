"""
Call monitoring workflow for orchestrating Voice AI and CRM services.

This module provides workflow orchestration for creating and monitoring
voice AI calls, and updating CRM systems with call results.
"""

import asyncio

from src.ai.voice_ai.constants import CallStatus
from src.ai.voice_ai.schemas import (
    AnalysisData,
    CallRequest,
    CallResponse,
    ClaimStatusData,
    TranscriptMessage,
    VoiceAIErrorResponse,
)
from src.ai.voice_ai.service import VoiceAIService
from src.db.call_state_service import CallStateService
from src.db.models import ActiveCallState
from src.integrations.crm.service import CRMService
from src.utils.logger import logger


class CallAndWriteToCRMWorkflow:
    """Orchestrates Voice AI call creation and CRM updates."""

    def __init__(
        self,
        voice_ai_service: VoiceAIService,
        crm_service: CRMService,
        call_state_service: CallStateService,
    ):
        """
        Initialize the call monitoring workflow.

        Args:
            voice_ai_service: Service for Voice AI operations
            crm_service: Service for CRM operations
            call_state_service: Service for call state management
        """
        self.voice_ai_service = voice_ai_service
        self.crm_service = crm_service
        self.call_state_service = call_state_service

    async def call_and_write_results_to_crm(
        self,
        request: CallRequest,
        user_id: str | None = None,
    ) -> CallResponse | VoiceAIErrorResponse:
        """
        Create an outbound call and start monitoring it and writing results to CRM.

        This method orchestrates:
        1. Creating the call via Voice AI service
        2. Persisting call state to DynamoDB
        3. Starting background monitoring and writing results to CRM
        4. Updating CRM when call completes

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

        # Persist call state to DynamoDB
        logger.info(
            f"[Call Monitoring Workflow] Attempting to persist call state. user_id={user_id}, call_id={result.call_id}"
        )

        if not user_id:
            logger.warning(
                "[Call Monitoring Workflow] Cannot persist call state: user_id is None or empty"
            )
        else:
            try:
                # Extract listen URL from provider data
                listen_url = None
                if result.provider_data and hasattr(result.provider_data, "monitor"):
                    listen_url = getattr(
                        result.provider_data.monitor, "listen_url", None
                    )

                logger.info(
                    f"[Call Monitoring Workflow] Creating ActiveCallState with listen_url={listen_url}"
                )

                call_state = ActiveCallState(
                    user_id=user_id,
                    call_id=result.call_id,
                    project_id=request.job_id or "",
                    status=result.status,
                    provider=result.provider,
                    phone_number=request.phone_number,
                    listen_url=listen_url,
                    started_at=result.created_at,
                    provider_data=result.provider_data.model_dump(mode="json")
                    if result.provider_data
                    else None,
                )

                logger.info(
                    f"[Call Monitoring Workflow] Calling set_active_call for user {user_id}"
                )
                await self.call_state_service.set_active_call(call_state)
                logger.info(
                    f"[Call Monitoring Workflow] Successfully persisted call state for {result.call_id}"
                )
            except Exception as e:
                logger.error(
                    f"[Call Monitoring Workflow] Failed to persist call state: {e}",
                    exc_info=True,
                )

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
        logged_message_count = 0  # Track message count

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

                # Log new transcript messages
                logged_message_count = self._log_new_transcript_messages(
                    call_id=call_id,
                    messages=status_result.messages,
                    logged_count=logged_message_count,
                )

                logger.info(
                    f"[Call Monitoring Workflow] Call {call_id} status: {status_result.status}"
                )

                # Update call status in DynamoDB
                if user_id:
                    try:
                        existing_state = await self.call_state_service.get_active_call(
                            user_id
                        )
                        if existing_state and existing_state.call_id == call_id:
                            # Update status
                            existing_state.status = status_result.status
                            await self.call_state_service.set_active_call(
                                existing_state
                            )
                    except Exception as e:
                        logger.error(
                            f"[Call Monitoring Workflow] Failed to update call state: {e}"
                        )

                # Check if call has ended
                if CallStatus.is_call_ended(status_result.status):
                    logger.info(
                        f"[Call Monitoring Workflow] Call {call_id} ended with status: {status_result.status}"
                    )

                    # Extract structured data and update CRM
                    # At this point, status_result is guaranteed to be CallResponse due to the isinstance check above
                    assert isinstance(status_result, CallResponse), (
                        "status_result should be CallResponse at this point"
                    )
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

    def _log_new_transcript_messages(
        self,
        call_id: str,
        messages: list[TranscriptMessage],
        logged_count: int,
    ) -> int:
        """
        Log new transcript messages from the call.

        Args:
            call_id: The call identifier
            messages: List of transcript messages
            logged_count: Number of messages already logged

        Returns:
            Updated count of logged messages
        """
        if not messages:
            return logged_count

        # Log only new messages
        new_messages = messages[logged_count:]
        for msg in new_messages:
            logger.info(
                f"[Call {call_id}] [{msg.timestamp_seconds:.1f}s] "
                f"{msg.role.upper()}: {msg.content}"
            )

        return len(messages)

    async def _process_completed_call(
        self,
        call_id: str,
        call_response: CallResponse,
        request: CallRequest,
        user_id: str | None,
    ) -> None:
        """
        Process a completed call and update CRM with structured data.

        Removes the call from DynamoDB active state and updates CRM.

        Args:
            call_id: The call identifier
            call_response: The final call response with provider data
            request: The original call request (contains tenant/job_id)
            user_id: The ID of the user who created the call
        """
        try:
            # Remove from DynamoDB active calls
            if user_id:
                try:
                    await self.call_state_service.remove_active_call(user_id)
                    logger.info(
                        f"[Call Monitoring Workflow] Removed active call state for user {user_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"[Call Monitoring Workflow] Failed to remove active call state: {e}"
                    )
            # Extract typed analysis data from provider response
            analysis = call_response.analysis

            if analysis is None or analysis.structured_data is None:
                logger.info(
                    f"[Call Monitoring Workflow] No analysis available for call {call_id} after polling"
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
            note_text = self._format_crm_note(analysis)

            # Add note to CRM job via service (no HTTP!)
            crm_result = await self.crm_service.add_note(
                entity_id=job_id,
                entity_type="job",
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

            # Update project status in CRM (skip if status is empty)
            if analysis.structured_data.claim_status:
                logger.info(
                    f"[Call Monitoring Workflow] Updating project status for job {job_id} to {analysis.structured_data.claim_status}"
                )
                status_update_result = await self.crm_service.update_job_status(
                    job_id=job_id,
                    status=analysis.structured_data.claim_status,
                )

                if isinstance(status_update_result, object) and hasattr(
                    status_update_result, "error"
                ):
                    logger.error(
                        f"[Call Monitoring Workflow] Failed to update project status for job {job_id}: {status_update_result.error}"
                    )
                else:
                    logger.info(
                        f"[Call Monitoring Workflow] Successfully updated project status for job {job_id}"
                    )

        except Exception as e:
            logger.error(
                f"[Call Monitoring Workflow] Error processing completed call {call_id}: {e}"
            )

    def _format_crm_note(self, analysis: AnalysisData | None) -> str:
        """
        Format structured data into a CRM note.

        Args:
            analysis: The extracted typed analysis data

        Returns:
            Formatted note text
        """
        structured_data: ClaimStatusData | None = analysis.structured_data
        summary: str | None = analysis.summary

        try:
            if structured_data is None:
                logger.info(
                    "[Call Monitoring Workflow] No structured data found for call"
                )
                return ""

            # Build formatted note
            note_lines = [
                "🤖 Voice AI Call Summary",
                "",
                f"Call Outcome: {structured_data.call_outcome.capitalize()}",
                f"Claim Status: {structured_data.claim_status.value.capitalize()}",
                f"Summary: {summary}",
            ]

            # Add status if available
            if structured_data.claim_status:
                note_lines.append(f"Status: {structured_data.claim_status}")

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
