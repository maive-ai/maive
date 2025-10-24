"""
CRM provider implementations.

This package contains specific implementations for different CRM systems.
"""

from src.integrations.crm.providers.factory import (
    create_crm_provider,
    get_crm_provider,
    set_crm_provider,
)
from src.integrations.crm.providers.job_nimbus.provider import JobNimbusProvider
from src.integrations.crm.providers.mock.provider import MockProvider
from src.integrations.crm.providers.service_titan.provider import ServiceTitanProvider

__all__ = [
    "create_crm_provider",
    "get_crm_provider",
    "set_crm_provider",
    "JobNimbusProvider",
    "MockProvider",
    "ServiceTitanProvider",
]
