"""
Configuration management for the CRM integration package.

This module handles environment variable configuration and validation
for CRM integrations using Pydantic settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.integrations.crm.constants import CRMProvider
from src.utils.logger import logger


class CRMSettings(BaseSettings):
    """Configuration for CRM integrations using Pydantic settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", env_prefix="CRM_"
    )

    # Provider configuration
    crm_provider: CRMProvider = Field(
        default=CRMProvider.SERVICE_TITAN, description="CRM provider to use"
    )

    # Service Titan configuration
    tenant_id: str = Field(description="Tenant ID")
    client_id: str = Field(description="Client ID")
    client_secret: str = Field(description="Client Secret")
    app_key: str = Field(description="App Key")
    base_api_url: str = Field(
        default="https://api-integration.servicetitan.io", description="API base URL for requests"
    )
    token_url: str = Field(
        default="https://auth-integration.servicetitan.io/connect/token",
        description="OAuth token endpoint URL"
    )

    # General CRM settings
    crm_request_timeout: int = Field(
        default=30, description="HTTP request timeout in seconds"
    )
    crm_max_retries: int = Field(
        default=3, description="Maximum number of API request retries"
    )


# Global settings instance
_crm_settings: CRMSettings | None = None


def get_crm_settings() -> CRMSettings:
    """
    Get the global CRM settings instance.

    Returns:
        CRMSettings: The global settings instance
    """
    global _crm_settings
    if _crm_settings is None:
        _crm_settings = CRMSettings()
        logger.info(f"CRMSettings loaded. Provider: {_crm_settings.crm_provider}")
        if _crm_settings.tenant_id:
            logger.info(f"Service Titan Tenant ID: {_crm_settings.tenant_id}")
        if _crm_settings.client_id:
            logger.info(f"Service Titan Client ID: {_crm_settings.client_id}")
        if _crm_settings.client_secret:
            logger.info(
                f"Service Titan Client Secret (first 5 chars): {_crm_settings.client_secret[:5]}..."
            )
        if _crm_settings.app_key:
            logger.info(
                f"Service Titan App Key (first 5 chars): {_crm_settings.app_key[:5]}..."
            )
    return _crm_settings


def set_crm_settings(settings: CRMSettings) -> None:
    """
    Set the global CRM settings instance.

    Args:
        settings: The settings to set
    """
    global _crm_settings
    _crm_settings = settings
