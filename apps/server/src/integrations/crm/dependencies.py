"""
FastAPI dependencies for CRM integration.

This module provides dependency injection functions for CRM-related
FastAPI endpoints, following the same pattern as the auth module.
"""

from fastapi import Depends

from src.integrations.crm.base import CRMProvider
from src.integrations.crm.providers.factory import get_crm_provider
from src.integrations.crm.service import CRMService


def get_crm_provider_dependency() -> CRMProvider:
    """
    FastAPI dependency for getting the CRM provider instance.

    Returns:
        CRMProvider: The configured CRM provider
    """
    return get_crm_provider()


def get_crm_service(
    crm_provider: CRMProvider = Depends(get_crm_provider_dependency),
) -> CRMService:
    """
    FastAPI dependency for getting the CRM service instance.

    Args:
        crm_provider: The CRM provider from dependency injection

    Returns:
        CRMService: The CRM service instance
    """
    return CRMService(crm_provider)