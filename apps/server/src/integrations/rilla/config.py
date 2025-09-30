"""
Configuration management for the Rilla integration package.

This module handles environment variable configuration and validation
for Rilla integration using Pydantic settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.logger import logger


class RillaSettings(BaseSettings):
    """Configuration for Rilla integration using Pydantic settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", env_prefix="RILLA_"
    )

    # Rilla configuration
    api_key: str = Field(description="Rilla API key for authentication")
    base_url: str = Field(
        default="https://customer.rillavoice.com", 
        description="Rilla API base URL"
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")


# Global settings instance
_rilla_settings: RillaSettings | None = None


def get_rilla_settings() -> RillaSettings:
    """
    Get the global Rilla settings instance.

    Returns:
        RillaSettings: The global settings instance
    """
    global _rilla_settings
    if _rilla_settings is None:
        _rilla_settings = RillaSettings()
        logger.info("RillaSettings loaded")
    return _rilla_settings


def set_rilla_settings(settings: RillaSettings) -> None:
    """
    Set the global Rilla settings instance.

    Args:
        settings: The settings to set
    """
    global _rilla_settings
    _rilla_settings = settings
