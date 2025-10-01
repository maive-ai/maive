"""
FastAPI dependencies for Voice AI integration.

This module provides dependency injection functions for Voice AI-related
FastAPI endpoints, following the same pattern as the CRM module.
"""

from fastapi import Depends

from src.integrations.voice_ai.base import VoiceAIProvider
from src.integrations.voice_ai.providers.factory import get_voice_ai_provider
from src.integrations.voice_ai.service import VoiceAIService


def get_voice_ai_provider_dependency() -> VoiceAIProvider:
    """
    FastAPI dependency for getting the Voice AI provider instance.

    Returns:
        VoiceAIProvider: The configured Voice AI provider
    """
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

