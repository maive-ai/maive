"""
Configuration management for the CRM integration package.

This module handles environment variable configuration and validation
for CRM integrations using Pydantic settings.
"""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.integrations.crm.constants import CRMProvider
from src.utils.logger import logger


class ServiceTitanConfig(BaseSettings):
    """Service Titan-specific configuration."""

    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", env_prefix="CRM_SERVICE_TITAN_"
    )

    tenant_id: str = Field(description="Tenant ID")
    client_id: str = Field(description="Client ID")
    client_secret: str = Field(description="Client Secret")
    app_key: str = Field(description="App Key")
    base_api_url: str = Field(
        default="https://api-integration.servicetitan.io",
        description="API base URL for requests",
    )
    token_url: str = Field(
        default="https://auth-integration.servicetitan.io/connect/token",
        description="OAuth token endpoint URL",
    )


class JobNimbusConfig(BaseSettings):
    """JobNimbus-specific configuration."""

    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", env_prefix="CRM_JOB_NIMBUS_"
    )

    api_key: str = Field(description="JobNimbus API key")
    base_api_url: str = Field(
        default="https://app.jobnimbus.com/api1",
        description="API base URL for requests",
    )


class CRMSettings(BaseSettings):
    """Configuration for CRM integrations using Pydantic settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", env_prefix="CRM_"
    )

    # Provider configuration
    provider: CRMProvider = Field(
        default=CRMProvider.SERVICE_TITAN, description="CRM provider to use"
    )

    # General CRM settings
    request_timeout: int = Field(
        default=30, description="HTTP request timeout in seconds"
    )
    max_retries: int = Field(
        default=3, description="Maximum number of API request retries"
    )

    # Provider-specific configurations (populated on demand)
    _provider_config: ServiceTitanConfig | JobNimbusConfig | None = None

    @model_validator(mode="after")
    def validate_provider_config(self) -> "CRMSettings":
        """Validate that required provider configuration is available."""
        if self.provider == CRMProvider.SERVICE_TITAN:
            # Load Service Titan config only if using that provider
            try:
                self._provider_config = ServiceTitanConfig()
                logger.info("Service Titan configuration loaded")
            except Exception as e:
                raise ValueError(
                    f"Service Titan configuration required when CRM_PROVIDER=service_titan. "
                    f"Missing environment variables: {e}"
                )
        elif self.provider == CRMProvider.JOB_NIMBUS:
            # Load JobNimbus config only if using that provider
            try:
                self._provider_config = JobNimbusConfig()
                logger.info("JobNimbus configuration loaded")
            except Exception as e:
                raise ValueError(
                    f"JobNimbus configuration required when CRM_PROVIDER=job_nimbus. "
                    f"Missing environment variables: {e}"
                )
        return self

    @property
    def provider_config(self) -> ServiceTitanConfig | JobNimbusConfig:
        """
        Get provider-specific configuration.

        Returns:
            ServiceTitanConfig | JobNimbusConfig: Provider configuration instance

        Raises:
            ValueError: If provider config is not loaded
        """
        if self._provider_config is None:
            raise ValueError(
                f"Provider configuration not loaded for {self.provider}. "
                f"Ensure CRM_PROVIDER is set correctly."
            )
        return self._provider_config


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
        logger.info("CRMSettings loaded", provider=_crm_settings.provider)

        # Log provider-specific config if available
        if _crm_settings.provider == CRMProvider.SERVICE_TITAN:
            config = _crm_settings.provider_config
            if isinstance(config, ServiceTitanConfig):
                logger.info("Service Titan Tenant ID", tenant_id=config.tenant_id)
                logger.info("Service Titan Client ID", client_id=config.client_id)
                logger.info(
                    "Service Titan Client Secret (first 5 chars)",
                    client_secret_preview=f"{config.client_secret[:5]}...",
                )
                logger.info(
                    "Service Titan App Key (first 5 chars)",
                    app_key_preview=f"{config.app_key[:5]}...",
                )
        elif _crm_settings.provider == CRMProvider.JOB_NIMBUS:
            config = _crm_settings.provider_config
            if isinstance(config, JobNimbusConfig):
                logger.info(
                    "JobNimbus API Key (first 5 chars)",
                    api_key_preview=f"{config.api_key[:5]}...",
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
