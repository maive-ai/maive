"""
Voice AI router with call management endpoints.

This module contains all the API endpoints for Voice AI operations,
including call creation and status retrieval.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.ai.voice_ai.constants import VoiceAIErrorCode
from src.ai.voice_ai.dependencies import get_voice_ai_service
from src.ai.voice_ai.schemas import CallResponse, VoiceAIErrorResponse
from src.ai.voice_ai.service import VoiceAIService
from src.db.call_state_service import CallStateService
from src.db.dependencies import get_call_state_service
from src.db.models import ActiveCallState

router = APIRouter(prefix="/voice-ai", tags=["Voice AI"])


@router.get("/calls/active", response_model=ActiveCallState | None)
async def get_active_call(
    current_user: User = Depends(get_current_user),
    call_state_service: CallStateService = Depends(get_call_state_service),
) -> ActiveCallState | None:
    """
    Get the user's currently active call.

    Returns the active call state if one exists, otherwise returns None.

    Args:
        current_user: The authenticated user
        call_state_service: The call state service instance from dependency injection

    Returns:
        ActiveCallState | None: The active call state or None if no active call

    Raises:
        HTTPException: If an error occurs retrieving the call state
    """
    try:
        active_call = await call_state_service.get_active_call(current_user.id)
        return active_call  # Returns None if no active call, which is fine

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
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=result.error)

    return result


@router.delete("/calls/{call_id}", status_code=HTTPStatus.NO_CONTENT)
async def end_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    voice_ai_service: VoiceAIService = Depends(get_voice_ai_service),
) -> None:
    """
    End an ongoing call programmatically.
    
    Args:
        call_id: The unique identifier for the call to end
        current_user: The authenticated user
        voice_ai_service: The Voice AI service instance from dependency injection
        
    Raises:
        HTTPException: If the call is not found or cannot be ended
    """
    result = await voice_ai_service.end_call(call_id)
    
    if isinstance(result, VoiceAIErrorResponse):
        if result.error_code == VoiceAIErrorCode.NOT_FOUND:
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=result.error)
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=result.error)
    
    # Success - 204 No Content response
    return None

