"""
Configuration management for the Voice AI integration package.

This module handles environment variable configuration and validation
for Voice AI integrations using Pydantic settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.ai.voice_ai.constants import VoiceAIProvider
from src.utils.logger import logger


class VoiceAISettings(BaseSettings):
    """General configuration for Voice AI integrations."""

    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", env_prefix="VOICE_AI_"
    )

    # Provider configuration
    provider: VoiceAIProvider = Field(
        default=VoiceAIProvider.VAPI, description="Voice AI provider to use"
    )

    # General settings
    request_timeout: int = Field(
        default=30, description="HTTP request timeout in seconds"
    )


class VapiSettings(BaseSettings):
    """Vapi-specific configuration."""

    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", env_prefix="VAPI_"
    )

    # Vapi API configuration
    api_key: str = Field(description="Vapi API key for authentication")
    webhook_secret: str = Field(description="Vapi webhook secret for verification")
    base_url: str = Field(
        default="https://api.vapi.ai", description="Vapi API base URL"
    )
    phone_number_id: str = Field(
        description="Vapi phone number ID for outbound calls"
    )
    default_assistant_id: str = Field(
        description="Default Vapi assistant ID or squad ID for outbound calls"
    )
    use_squad: bool = Field(
        default=False, description="Whether to use squad instead of assistant"
    )

    # Vapi-specific settings
    require_webhook_verification: bool = Field(
        default=True, description="Whether to require webhook verification"
    )


# Global settings instances
_voice_ai_settings: VoiceAISettings | None = None
_vapi_settings: VapiSettings | None = None


def get_voice_ai_settings() -> VoiceAISettings:
    """
    Get the global Voice AI settings instance.

    Returns:
        VoiceAISettings: The global settings instance
    """
    global _voice_ai_settings
    if _voice_ai_settings is None:
        _voice_ai_settings = VoiceAISettings()
        logger.info("VoiceAISettings loaded", provider=_voice_ai_settings.provider)
    return _voice_ai_settings


def get_vapi_settings() -> VapiSettings:
    """
    Get the global Vapi settings instance.

    Returns:
        VapiSettings: The global Vapi settings instance
    """
    global _vapi_settings
    if _vapi_settings is None:
        _vapi_settings = VapiSettings()
        logger.info("VapiSettings loaded")
        if _vapi_settings.phone_number_id:
            logger.info("Vapi Phone Number ID", phone_number_id=_vapi_settings.phone_number_id)
        if _vapi_settings.default_assistant_id:
            logger.info("Vapi Default Assistant ID", default_assistant_id=_vapi_settings.default_assistant_id)
    return _vapi_settings


def set_voice_ai_settings(settings: VoiceAISettings) -> None:
    """
    Set the global Voice AI settings instance.

    Args:
        settings: The settings to set
    """
    global _voice_ai_settings
    _voice_ai_settings = settings


def set_vapi_settings(settings: VapiSettings) -> None:
    """
    Set the global Vapi settings instance.

    Args:
        settings: The settings to set
    """
    global _vapi_settings
    _vapi_settings = settings

