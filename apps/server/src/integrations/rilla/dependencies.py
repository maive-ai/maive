"""
FastAPI dependencies for Rilla integration.

This module provides dependency injection functions for Rilla-related
FastAPI endpoints, following the same pattern as the CRM module.
"""

from fastapi import Depends

from src.integrations.rilla.client import RillaClient
from src.integrations.rilla.config import get_rilla_settings
from src.integrations.rilla.service import RillaService


def get_rilla_client() -> RillaClient:
    """
    FastAPI dependency for getting the Rilla client instance.

    Returns:
        RillaClient: The configured Rilla client
    """
    settings = get_rilla_settings()
    return RillaClient(settings=settings)


def get_rilla_service(
    rilla_client: RillaClient = Depends(get_rilla_client),
) -> RillaService:
    """
    FastAPI dependency for getting the Rilla service instance.

    Args:
        rilla_client: The Rilla client from dependency injection

    Returns:
        RillaService: The Rilla service instance
    """
    return RillaService(rilla_client)
