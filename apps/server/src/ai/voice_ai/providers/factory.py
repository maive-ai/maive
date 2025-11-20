"""
Voice AI provider factory for dependency injection.

This module provides factory functions to create Voice AI provider instances
based on configuration, following the same pattern as the CRM module.
"""

from src.ai.voice_ai.base import VoiceAIProvider
from src.ai.voice_ai.config import get_voice_ai_settings
from src.ai.voice_ai.constants import VoiceAIProvider as VoiceAIProviderEnum
from src.ai.voice_ai.providers.vapi import VapiProvider
from src.utils.logger import logger


def create_voice_ai_provider() -> VoiceAIProvider:
    """
    Create a Voice AI provider instance based on configuration.

    Returns:
        VoiceAIProvider: The configured Voice AI provider instance

    Raises:
        ValueError: If the configured provider is not supported
    """
    settings = get_voice_ai_settings()

    if settings.provider == VoiceAIProviderEnum.VAPI:
        logger.info("Creating Vapi Voice AI provider")
        return VapiProvider()
    else:
        raise ValueError(f"Unsupported Voice AI provider: {settings.provider}")


# Global provider instance
_voice_ai_provider: VoiceAIProvider | None = None


def get_voice_ai_provider() -> VoiceAIProvider:
    """
    Get the global Voice AI provider instance.

    Returns:
        VoiceAIProvider: The global provider instance
    """
    global _voice_ai_provider
    if _voice_ai_provider is None:
        _voice_ai_provider = create_voice_ai_provider()
    return _voice_ai_provider


def set_voice_ai_provider(provider: VoiceAIProvider) -> None:
    """
    Set the global Voice AI provider instance.

    Args:
        provider: The provider to set
    """
    global _voice_ai_provider
    _voice_ai_provider = provider
