"""
FastAPI dependencies for Voice AI integration.

This module provides dependency injection functions for Voice AI-related
FastAPI endpoints, following the same pattern as the CRM module.
"""

from fastapi import Depends, HTTPException, status
from twilio.rest import Client

from src.ai.voice_ai.base import VoiceAIProvider
from src.ai.voice_ai.config import get_voice_ai_settings
from src.ai.voice_ai.constants import VoiceAIProvider as VoiceAIProviderEnum
from src.ai.voice_ai.providers.factory import get_voice_ai_provider
from src.ai.voice_ai.providers.twilio.dependencies import (
    get_twilio_client,
    get_user_phone_number,
)
from src.ai.voice_ai.providers.twilio.provider import TwilioProvider
from src.ai.voice_ai.service import VoiceAIService
from src.auth.dependencies import get_current_user
from src.auth.schemas import User


async def get_voice_ai_provider_dependency(
    current_user: User = Depends(get_current_user),
    twilio_client: Client = Depends(get_twilio_client),
    phone_number: str | None = Depends(get_user_phone_number),
) -> VoiceAIProvider:
    """
    FastAPI dependency for getting the Voice AI provider instance.

    For Twilio, creates user-specific provider with user's phone number and ID.
    For Vapi, returns global provider instance (other params unused).

    Args:
        current_user: Current authenticated user
        twilio_client: Global Twilio client (unused for Vapi)
        phone_number: User's phone number or None (unused for Vapi)

    Returns:
        VoiceAIProvider: The configured Voice AI provider

    Raises:
        HTTPException: If Twilio is configured but user has no phone number
    """
    settings = get_voice_ai_settings()

    if settings.provider == VoiceAIProviderEnum.TWILIO:
        # Twilio requires user context - create user-specific provider
        if not phone_number:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No phone number configured for user",
            )
        return TwilioProvider(twilio_client, phone_number, current_user.id)
    else:
        # Vapi and others use global factory
        return get_voice_ai_provider()


def get_voice_ai_service(
    voice_ai_provider: VoiceAIProvider = Depends(get_voice_ai_provider_dependency),
) -> VoiceAIService:
    """
    FastAPI dependency for getting the Voice AI service instance.

    Args:
        voice_ai_provider: The Voice AI provider from dependency injection

    Returns:
        VoiceAIService: The Voice AI service instance
    """
    return VoiceAIService(voice_ai_provider)
