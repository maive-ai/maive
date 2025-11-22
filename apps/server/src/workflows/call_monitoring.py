"""
Call monitoring workflow for orchestrating Voice AI and CRM services.

This module provides workflow orchestration for creating and monitoring
voice AI calls, and updating CRM systems with call results.
"""

import asyncio
import mimetypes
import tempfile
import textwrap
from pathlib import Path

from src.ai.base import AIProvider
from src.ai.providers.factory import AIProviderType, create_ai_provider
from src.ai.voice_ai.constants import CallStatus
from src.ai.voice_ai.constants import VoiceAIProvider as VoiceAIProviderEnum
from src.ai.voice_ai.schemas import (
    AnalysisData,
    CallRequest,
    CallResponse,
    ClaimStatusData,
    VoiceAIErrorResponse,
)
from src.ai.voice_ai.service import VoiceAIService
from src.db.calls.repository import CallRepository
from src.integrations.crm.service import CRMService
from src.utils.logger import logger
from src.workflows.config import get_call_monitoring_settings


class CallAndWriteToCRMWorkflow:
    """Orchestrates Voice AI call creation and CRM updates."""

    def __init__(
        self,
        voice_ai_service: VoiceAIService,
        crm_service: CRMService,
        call_repository: CallRepository,
    ):
        """
        Initialize the call monitoring workflow.

        Args:
            voice_ai_service: Service for Voice AI operations
            crm_service: Service for CRM operations
            call_repository: Repository for call data persistence
        """
        self.voice_ai_service = voice_ai_service
        self.crm_service = crm_service
        self.call_repository = call_repository
        self.settings = get_call_monitoring_settings()
        # Initialize AI provider for recording analysis (explicitly use Gemini for audio)
        self.gemini_ai_provider: AIProvider = create_ai_provider(
            provider_type=AIProviderType.GEMINI
        )

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

        # Persist call to database
        logger.info(
            "[Call Monitoring Workflow] Attempting to persist call",
            user_id=user_id,
            call_id=result.call_id,
        )

        if not user_id:
            logger.warning(
                "[Call Monitoring Workflow] Cannot persist call: user_id is None or empty"
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
                    "[Call Monitoring Workflow] Creating Call record",
                    listen_url=listen_url,
                )

                # Create call record using repository
                await self.call_repository.create_call(
                    user_id=user_id,
                    call_id=result.call_id,
                    project_id=request.job_id or "",
                    status=result.status,
                    provider=result.provider,
                    phone_number=request.phone_number,
                    started_at=result.created_at,
                    listen_url=listen_url,
                    provider_data=result.provider_data.model_dump(mode="json")
                    if result.provider_data
                    else None,
                )

                # Explicitly commit the transaction to prevent race condition
                # The background monitoring task creates its own session and might query
                # the database before the HTTP request handler commits
                await self.call_repository.session.commit()

                logger.info(
                    "[Call Monitoring Workflow] Successfully persisted call",
                    call_id=result.call_id,
                )
            except Exception as e:
                logger.error(
                    "[Call Monitoring Workflow] Failed to persist call",
                    error=str(e),
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
                "[Call Monitoring Workflow] Started monitoring for call",
                call_id=result.call_id,
            )
        except Exception as e:
            logger.error(
                "[Call Monitoring Workflow] Failed to start monitoring task for call",
                call_id=result.call_id,
                error=str(e),
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
        # Import here to avoid circular dependencies
        from src.db.database import get_async_session_local

        poll_interval_seconds = 3
        max_polling_duration = 60 * 60 * 24  # 24 hours
        start_time = asyncio.get_event_loop().time()

        # Create a new database session for this background task
        # The session from the HTTP request will be closed, so we need our own
        session_factory = get_async_session_local()

        try:
            async with session_factory() as session:
                # Create a repository with our own session
                task_repository = CallRepository(session)

                while True:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > max_polling_duration:
                        logger.warning(
                            "[Call Monitoring Workflow] Monitoring timed out for call",
                            call_id=call_id,
                        )
                        break

                    # Poll call status
                    status_result = await self.voice_ai_service.get_call_status(call_id)

                    if isinstance(status_result, VoiceAIErrorResponse):
                        logger.error(
                            "[Call Monitoring Workflow] Error polling call",
                            call_id=call_id,
                            error=status_result.error,
                        )
                        break

                    logger.info(
                        "[Call Monitoring Workflow] Call status",
                        call_id=call_id,
                        status=status_result.status,
                    )

                    # Check if call has ended
                    if CallStatus.is_call_ended(status_result.status):
                        logger.info(
                            "[Call Monitoring Workflow] Call ended",
                            call_id=call_id,
                            status=status_result.status,
                        )

                        # Process completed call
                        # At this point, status_result is guaranteed to be CallResponse due to the isinstance check above
                        assert isinstance(status_result, CallResponse), (
                            "status_result should be CallResponse at this point"
                        )

                        # Update call status to ended immediately (for downstream systems)
                        await task_repository.update_call_status(
                            call_id=call_id,
                            status=status_result.status,
                            provider_data=status_result.provider_data.model_dump(
                                mode="json"
                            )
                            if status_result.provider_data
                            else None,
                        )
                        await session.commit()

                        # Generate structured data from recording using AI (may take several seconds)
                        await self._generate_structured_data_from_call(
                            call_id=call_id,
                            call_response=status_result,
                            repository=task_repository,
                        )

                        # Persist complete call data including AI-generated analysis
                        await self._persist_completed_call(
                            call_id=call_id,
                            call_response=status_result,
                            repository=task_repository,
                        )
                        await session.commit()
                        logger.info(
                            "[Call Monitoring Workflow] Committed final call state",
                            call_id=call_id,
                        )

                        # Update CRM if enabled
                        if self.settings.enable_crm_write:
                            logger.info(
                                "[Call Monitoring Workflow] Updating CRM with call results",
                                call_id=call_id,
                            )
                            await self._update_crm_with_call_results(
                                call_id=call_id,
                                call_response=status_result,
                                request=request,
                            )
                        else:
                            logger.info(
                                "[Call Monitoring Workflow] CRM write disabled, skipping CRM update",
                                call_id=call_id,
                            )

                        break

                    # Update call status in database (only for non-ended calls)
                    # Ended calls are handled by _persist_completed_call above
                    if user_id:
                        try:
                            await task_repository.update_call_status(
                                call_id=call_id,
                                status=status_result.status,
                                provider_data=status_result.provider_data.model_dump(
                                    mode="json"
                                )
                                if status_result.provider_data
                                else None,
                            )
                            await session.commit()
                            logger.debug(
                                "[Call Monitoring Workflow] Committed status update for call",
                                call_id=call_id,
                            )
                        except Exception as e:
                            logger.error(
                                "[Call Monitoring Workflow] Failed to update call status",
                                error=str(e),
                            )
                            await session.rollback()

                    await asyncio.sleep(poll_interval_seconds)

        except asyncio.CancelledError:
            logger.info(
                "[Call Monitoring Workflow] Monitoring task canceled",
                call_id=call_id,
            )
        except Exception as e:
            logger.error(
                "[Call Monitoring Workflow] Unexpected error monitoring call",
                call_id=call_id,
                error=str(e),
            )

    async def _persist_completed_call(
        self,
        call_id: str,
        call_response: CallResponse,
        repository: CallRepository,
    ) -> None:
        """
        Persist completed call data to the database.

        Marks the call as ended and stores final status, analysis, and transcript.

        Args:
            call_id: The call identifier
            call_response: The final call response with provider data
            repository: The call repository with an active session
        """
        try:
            # Mark call as ended in database
            await repository.end_call(
                call_id=call_id,
                final_status=call_response.status,
                ended_at=call_response.ended_at
                if hasattr(call_response, "ended_at")
                else None,
                provider_data=call_response.provider_data.model_dump(mode="json")
                if call_response.provider_data
                else None,
                analysis_data=call_response.analysis.model_dump(mode="json")
                if call_response.analysis
                else None,
                transcript=[
                    msg.model_dump(mode="json") for msg in call_response.messages
                ]
                if call_response.messages
                else None,
            )
            logger.info(
                "[Call Monitoring Workflow] Marked call as ended in database",
                call_id=call_id,
            )
        except Exception as e:
            logger.error(
                "[Call Monitoring Workflow] Error persisting completed call",
                call_id=call_id,
                error=str(e),
            )

    async def _poll_for_recording_url(
        self,
        call_id: str,
        repository: CallRepository,
        max_attempts: int = 10,
        poll_interval: int = 3,
    ) -> str | None:
        """
        Poll database for recording URL with timeout.

        Args:
            call_id: The call identifier
            repository: The call repository with an active session
            max_attempts: Maximum number of polling attempts
            poll_interval: Seconds between polling attempts

        Returns:
            str | None: Recording URL if found, None otherwise
        """
        logger.debug(
            "[Call Monitoring Workflow] Polling for recording URL",
            call_id=call_id,
        )

        # TODO: Change this to be event driven instead of polling
        for attempt in range(max_attempts):
            # Expire all cached instances to force fresh database query
            repository.session.expire_all()

            call = await repository.get_call_by_call_id(call_id)
            if call and call.recording_url:
                logger.debug(
                    "[Call Monitoring Workflow] Found recording URL",
                    call_id=call_id,
                    url=call.recording_url,
                    attempt=attempt + 1,
                )
                return call.recording_url

            if attempt < max_attempts - 1:
                await asyncio.sleep(poll_interval)

        logger.warning(
            "[Call Monitoring Workflow] Recording URL not available after polling",
            call_id=call_id,
            max_attempts=max_attempts,
        )
        return None

    async def _download_and_save_recording(
        self,
        call_id: str,
        recording_url: str,
    ) -> Path:
        """
        Download recording from voice AI provider and save to temporary file.

        Args:
            call_id: The call identifier
            recording_url: URL to the recording

        Returns:
            Path: Path to the temporary file

        Raises:
            Exception: If download or file creation fails
        """
        logger.debug(
            "[Call Monitoring Workflow] Downloading recording",
            call_id=call_id,
        )

        file_bytes, content_type = await self.voice_ai_service.download_recording(
            recording_url
        )

        # Determine file extension from content type using mimetypes
        extension = mimetypes.guess_extension(content_type) or ".mp3"

        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = Path(temp_file.name)

        logger.debug(
            "[Call Monitoring Workflow] Created temporary file",
            call_id=call_id,
            path=str(temp_file_path),
        )

        return temp_file_path

    def _create_analysis_prompt(self) -> str:
        """
        Create prompt for AI analysis of call recording.

        The Pydantic schema (AnalysisData) provides detailed field descriptions,
        so this prompt focuses on context and high-level instructions.

        Returns:
            str: Formatted prompt for AI analysis
        """
        return textwrap.dedent(
            """
            You are analyzing a recorded phone call between a contractor and an insurance company / adjuster / homeowner
            regarding an insurance claim for a project.

            Listen to the call recording and extract all relevant information into the structured format.
            Pay special attention to:
            - Whether the call was successful or went to voicemail
            - Any status updates about the claim or project
            - Payment information if discussed (amount, check number, dates)
            - Required documents or next steps mentioned
            - Overall success of the call in achieving its objective

            Provide a clear summary of the call and evaluate how well it went.
            """
        ).strip()

    async def _cleanup_recording_files(
        self,
        call_id: str,
        temp_file_path: Path | None,
        uploaded_file_id: str | None,
    ) -> None:
        """
        Clean up temporary file and uploaded file from AI provider.

        Args:
            call_id: The call identifier (for logging)
            temp_file_path: Path to temporary file to delete
            uploaded_file_id: ID of uploaded file to delete from AI provider
        """
        # Clean up temporary file
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
                logger.debug(
                    "[Call Monitoring Workflow] Deleted temporary file",
                    call_id=call_id,
                    path=str(temp_file_path),
                )
            except Exception as e:
                logger.warning(
                    "[Call Monitoring Workflow] Failed to delete temporary file",
                    path=str(temp_file_path),
                    error=str(e),
                )

        # Delete uploaded file from AI provider
        if uploaded_file_id:
            try:
                await self.gemini_ai_provider.delete_file(uploaded_file_id)
                logger.debug(
                    "[Call Monitoring Workflow] Deleted uploaded file from AI provider",
                    call_id=call_id,
                    file_id=uploaded_file_id,
                )
            except Exception as e:
                logger.warning(
                    "[Call Monitoring Workflow] Failed to delete uploaded file",
                    file_id=uploaded_file_id,
                    error=str(e),
                )

    async def _generate_structured_data_from_call(
        self,
        call_id: str,
        call_response: CallResponse,
        repository: CallRepository,
    ) -> None:
        """
        Generate structured data from call recording using AI analysis.

        This method orchestrates the full recording analysis pipeline:
        1. Checks if provider is Twilio (returns early if not)
        2. Polls database for recording URL (with timeout)
        3. Downloads recording from voice AI provider
        4. Uploads to AI provider (Gemini)
        5. Generates structured analysis data
        6. Updates call_response.analysis in-place
        7. Cleans up temporary files

        Note: This function updates call_response.analysis but does NOT persist to database.
        The caller should persist the updated call_response after this returns.

        Args:
            call_id: The call identifier
            call_response: The call response to update with analysis data
            repository: The call repository with an active session
        """
        # Check if provider is Twilio
        if call_response.provider != VoiceAIProviderEnum.TWILIO:
            return

        logger.info(
            "[Call Monitoring Workflow] Processing Twilio recording with AI",
            call_id=call_id,
        )

        uploaded_file_id: str | None = None
        temp_file_path: Path | None = None

        try:
            # Poll for recording URL
            recording_url = await self._poll_for_recording_url(call_id, repository)
            if not recording_url:
                return

            # Download and save recording to temporary file
            temp_file_path = await self._download_and_save_recording(
                call_id, recording_url
            )

            # Upload to AI provider
            logger.debug(
                "[Call Monitoring Workflow] Uploading recording to AI provider",
                call_id=call_id,
            )

            file_metadata = await self.gemini_ai_provider.upload_file(
                str(temp_file_path)
            )
            uploaded_file_id = file_metadata.name

            logger.debug(
                "[Call Monitoring Workflow] Uploaded recording to AI provider",
                call_id=call_id,
                file_id=uploaded_file_id,
            )

            prompt = self._create_analysis_prompt()
            analysis_data: AnalysisData = (
                await self.gemini_ai_provider.generate_structured_content(
                    prompt=prompt,
                    response_schema=AnalysisData,
                    file_ids=[uploaded_file_id],
                )
            )

            logger.debug(
                "[Call Monitoring Workflow] Successfully generated structured data",
                call_id=call_id,
            )

            # Update call_response with AI-generated analysis (in-place mutation)
            call_response.analysis = analysis_data
            logger.debug(
                "[Call Monitoring Workflow] Updated call_response with AI-generated analysis",
                call_id=call_id,
            )

        except Exception as e:
            logger.error(
                "[Call Monitoring Workflow] Error generating structured data from recording",
                call_id=call_id,
                error=str(e),
                exc_info=True,
            )
            logger.warning(
                "[Call Monitoring Workflow] Failed to generate structured data from recording",
                call_id=call_id,
            )

        finally:
            await self._cleanup_recording_files(
                call_id, temp_file_path, uploaded_file_id
            )

    async def _update_crm_with_call_results(
        self,
        call_id: str,
        call_response: CallResponse,
        request: CallRequest,
    ) -> None:
        """
        Update CRM with structured data from completed call.

        Adds a formatted note to the CRM job and updates job status if applicable.

        Args:
            call_id: The call identifier
            call_response: The final call response with analysis data
            request: The original call request (contains tenant/job_id)
        """
        try:
            # Extract typed analysis data from provider response
            analysis = call_response.analysis

            if analysis is None or analysis.structured_data is None:
                logger.info(
                    "[Call Monitoring Workflow] No analysis available for call, skipping CRM update",
                    call_id=call_id,
                )
                return

            logger.info(
                "[Call Monitoring Workflow] Extracted structured data for call",
                call_id=call_id,
            )

            # Update CRM if we have job_id
            job_id = request.job_id

            if job_id is None:
                logger.info(
                    "[Call Monitoring Workflow] Missing tenant/job_id for call; skipping CRM note",
                    call_id=call_id,
                )
                return

            # Format note text from structured data
            note_text = self._format_crm_note(analysis)

            # Add note to CRM job via service
            crm_result = await self.crm_service.add_note(
                entity_id=job_id,
                entity_type="job",
                text=note_text,
                pin_to_top=True,  # Pin important call results
            )

            if hasattr(crm_result, "error"):
                logger.error(
                    "[Call Monitoring Workflow] Failed to add job note",
                    job_id=job_id,
                    error=crm_result.error,
                )
            else:
                logger.info(
                    "[Call Monitoring Workflow] Successfully added CRM note",
                    job_id=job_id,
                )

            # Status updates disabled for JobNimbus - will be re-enabled later
            # TODO: Re-enable status updates once status name mapping is implemented

        except Exception as e:
            logger.error(
                "[Call Monitoring Workflow] Error updating CRM with call results",
                call_id=call_id,
                error=str(e),
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
            ]

            # Add claim status if available
            if structured_data.claim_status:
                note_lines.append(f"Claim Status: {structured_data.claim_status}")

            # Add summary if available
            if summary:
                note_lines.append(f"Summary: {summary}")

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
                    doc_text = doc.document_name
                    if doc.description:
                        doc_text += f": {doc.description}"
                    note_lines.append(f"- {doc_text}")

            return "\n".join(note_lines)

        except Exception as e:
            logger.error(
                "[Call Monitoring Workflow] Error formatting CRM note",
                error=str(e),
            )
            # Fallback: return model as JSON
            return f"Voice AI Call Results:\n\n```json\n{structured_data.model_dump_json(indent=2)}\n```"
