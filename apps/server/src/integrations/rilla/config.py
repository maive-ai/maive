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
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    retry_delay: float = Field(default=1.0, description="Base delay between retries in seconds")
    max_retry_delay: float = Field(default=60.0, description="Maximum delay between retries in seconds")
    backoff_factor: float = Field(default=2.0, description="Exponential backoff factor for retries")

    # Rate limiting
    requests_per_minute: int = Field(default=60, description="Maximum requests per minute")
    burst_limit: int = Field(default=10, description="Burst limit for requests")

    # Logging
    log_requests: bool = Field(default=False, description="Whether to log HTTP requests")
    log_responses: bool = Field(default=False, description="Whether to log HTTP responses")
    mask_sensitive_data: bool = Field(default=True, description="Whether to mask sensitive data in logs")


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
        if _rilla_settings.api_key:
            logger.info(f"Rilla API Key (first 5 chars): {_rilla_settings.api_key[:5]}...")
    return _rilla_settings


def set_rilla_settings(settings: RillaSettings) -> None:
    """
    Set the global Rilla settings instance.

    Args:
        settings: The settings to set
    """
    global _rilla_settings
    _rilla_settings = settings
