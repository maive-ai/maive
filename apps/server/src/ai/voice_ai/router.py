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

router = APIRouter(prefix="/voice-ai", tags=["Voice AI"])


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

