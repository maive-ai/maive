"""
Voice AI router with call management endpoints.

This module contains all the API endpoints for Voice AI operations,
including call creation and status retrieval.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException

from src.ai.voice_ai.constants import VoiceAIErrorCode
from src.ai.voice_ai.dependencies import get_voice_ai_service
from src.ai.voice_ai.schemas import ActiveCallResponse, CallResponse, VoiceAIErrorResponse
from src.ai.voice_ai.service import VoiceAIService
from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.calls.repository import CallRepository
from src.db.dependencies import get_call_repository

router = APIRouter(prefix="/voice-ai", tags=["Voice AI"])


@router.get("/calls/active", response_model=ActiveCallResponse | None)
async def get_active_call(
    current_user: User = Depends(get_current_user),
    call_repository: CallRepository = Depends(get_call_repository),
) -> ActiveCallResponse | None:
    """
    Get the user's currently active call.

    Returns the active call data if one exists, otherwise returns None.

    Args:
        current_user: The authenticated user
        call_repository: The call repository instance from dependency injection

    Returns:
        ActiveCallResponse | None: The active call data or None if no active call

    Raises:
        HTTPException: If an error occurs retrieving the call
    """
    try:
        active_call = await call_repository.get_active_call(current_user.id)

        if active_call is None:
            return None

        return ActiveCallResponse(
            user_id=active_call.user_id,
            call_id=active_call.call_id,
            project_id=active_call.project_id,
            status=active_call.status,
            provider=active_call.provider,
            phone_number=active_call.phone_number,
            listen_url=active_call.listen_url,
            started_at=active_call.started_at.isoformat(),
            provider_data=active_call.provider_data,
        )

    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve active call: {str(e)}",
        )


@router.get("/calls/{call_id}", response_model=CallResponse)
async def get_call_status(
    call_id: str,
    current_user: User = Depends(get_current_user),
    voice_ai_service: VoiceAIService = Depends(get_voice_ai_service),
) -> CallResponse:
    """
    Get the status of a specific call by ID.

    Args:
        call_id: The unique identifier for the call
        current_user: The authenticated user
        voice_ai_service: The Voice AI service instance from dependency injection

    Returns:
        CallResponse: The call status information

    Raises:
        HTTPException: If the call is not found or an error occurs
    """
    result = await voice_ai_service.get_call_status(call_id)

    if isinstance(result, VoiceAIErrorResponse):
        if result.error_code == VoiceAIErrorCode.NOT_FOUND:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=result.error)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=result.error
        )

    return result


@router.delete("/calls/{call_id}", status_code=HTTPStatus.NO_CONTENT)
async def end_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    voice_ai_service: VoiceAIService = Depends(get_voice_ai_service),
    call_repository: CallRepository = Depends(get_call_repository),
) -> None:
    """
    End an ongoing call programmatically.

    Args:
        call_id: The unique identifier for the call to end
        current_user: The authenticated user
        voice_ai_service: The Voice AI service instance from dependency injection
        call_repository: The call repository instance from dependency injection

    Raises:
        HTTPException: If the call is not found or cannot be ended
    """
    from src.ai.voice_ai.constants import CallStatus
    from src.utils.logger import logger

    # First check if call exists and belongs to user
    call = await call_repository.get_call_by_call_id(call_id)
    if not call:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Call not found")

    if call.user_id != current_user.id:
        raise HTTPException(status_code=HTTPStatus.FORBIDDEN, detail="Not authorized to end this call")

    # If call is already ended, return success (idempotent)
    if not call.is_active:
        logger.info("[End Call] Call already ended, returning success", call_id=call_id)
        return None

    # Extract control URL from stored provider data
    control_url = None
    if call.provider_data and isinstance(call.provider_data, dict):
        monitor = call.provider_data.get('monitor', {})
        control_url = monitor.get('control_url')

    if not control_url:
        logger.error("[End Call] No control URL found for call", call_id=call_id)
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Control URL not available for this call"
        )

    # Try to end call via Vapi using the control URL
    logger.info("[End Call] Attempting to end call via control URL", call_id=call_id, control_url=control_url)
    result = await voice_ai_service.end_call(call_id, control_url=control_url)

    if isinstance(result, VoiceAIErrorResponse):
        logger.error("[End Call] Failed to end call via Vapi", call_id=call_id, error=result.error)
        # If Vapi fails, still mark as ended in DB so UI can update
        # The monitoring task will sync the actual state
        await call_repository.end_call(
            call_id=call_id,
            final_status=CallStatus.ENDED,
        )
        await call_repository.session.commit()
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to end call: {result.error}"
        )

    # Vapi succeeded - now update database
    await call_repository.end_call(
        call_id=call_id,
        final_status=CallStatus.ENDED,
    )
    await call_repository.session.commit()
    logger.info("[End Call] Successfully ended call and updated database", call_id=call_id)

    # Success - 204 No Content response
    return None
