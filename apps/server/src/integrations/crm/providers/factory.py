"""
CRM provider factory for dependency injection.

This module provides factory functions to create CRM provider instances
based on configuration, following the same pattern as the auth module.
"""

from src.integrations.crm.base import CRMProvider
from src.integrations.crm.config import get_crm_settings
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.providers.job_nimbus import JobNimbusProvider
from src.integrations.crm.providers.mock_crm import MockCRMProvider
from src.integrations.crm.providers.service_titan import ServiceTitanProvider
from src.utils.logger import logger


def create_crm_provider() -> CRMProvider:
    """
    Create a CRM provider instance based on configuration.

    Returns:
        CRMProvider: The configured CRM provider instance

    Raises:
        ValueError: If the configured provider is not supported
    """
    settings = get_crm_settings()

    if settings.provider == CRMProviderEnum.SERVICE_TITAN:
        logger.info("Creating Service Titan CRM provider")
        return ServiceTitanProvider()
    elif settings.provider == CRMProviderEnum.JOB_NIMBUS:
        logger.info("Creating JobNimbus CRM provider")
        return JobNimbusProvider()
    elif settings.provider == CRMProviderEnum.MOCK_CRM:
        logger.info("Creating Mock CRM provider")
        return MockCRMProvider()
    else:
        raise ValueError(f"Unsupported CRM provider: {settings.provider}")


# Global provider instance
_crm_provider: CRMProvider | None = None


def get_crm_provider() -> CRMProvider:
    """
    Get the global CRM provider instance.

    Returns:
        CRMProvider: The global provider instance
    """
    global _crm_provider
    if _crm_provider is None:
        _crm_provider = create_crm_provider()
    return _crm_provider


def set_crm_provider(provider: CRMProvider) -> None:
    """
    Set the global CRM provider instance.

    Args:
        provider: The provider to set
    """
    global _crm_provider
    _crm_provider = provider