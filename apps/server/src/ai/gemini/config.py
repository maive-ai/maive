"""
Configuration management for the Gemini integration package.

This module handles environment variable configuration and validation
for Gemini integration using Pydantic settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.logger import logger


class GeminiSettings(BaseSettings):
    """Configuration for Gemini integration using Pydantic settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", env_prefix="GEMINI_"
    )

    # Gemini API configuration
    api_key: str = Field(description="Gemini API key for authentication")
    model_name: str = Field(description="Gemini model name to use")
    temperature: float = Field(
        description="Temperature for content generation (0.0-1.0)"
    )
    thinking_budget: int = Field(description="Thinking budget for content generation")
    timeout: int = Field(default=600, description="Request timeout in seconds")


# Global settings instance
_gemini_settings: GeminiSettings | None = None


def get_gemini_settings() -> GeminiSettings:
    """
    Get the global Gemini settings instance.

    Returns:
        GeminiSettings: The global settings instance
    """
    global _gemini_settings
    if _gemini_settings is None:
        _gemini_settings = GeminiSettings()
        logger.info("Settings loaded")
    return _gemini_settings


def set_gemini_settings(settings: GeminiSettings) -> None:
    """
    Set the global Gemini settings instance.

    Args:
        settings: The settings to set
    """
    global _gemini_settings
    _gemini_settings = settings
