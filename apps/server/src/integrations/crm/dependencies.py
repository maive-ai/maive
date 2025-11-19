"""
FastAPI dependencies for CRM integration.

This module provides dependency injection functions for CRM-related
FastAPI endpoints with multi-tenant credential management.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.database import get_db
from src.integrations.creds.service import (
    CRMCredentialsService,
    get_secrets_manager_client,
)
from src.integrations.crm.base import CRMProvider
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.providers.job_nimbus.provider import JobNimbusProvider
from src.integrations.crm.providers.service_titan.provider import ServiceTitanProvider
from src.integrations.crm.service import CRMService
from src.utils.logger import logger


async def get_crm_credentials_service(
    db: AsyncSession = Depends(get_db),
    secrets_client=Depends(get_secrets_manager_client),
) -> CRMCredentialsService:
    """
    FastAPI dependency for getting the CRM credentials service.

    Args:
        db: Database session
        secrets_client: AWS Secrets Manager client

    Returns:
        CRMCredentialsService instance
    """
    return CRMCredentialsService(db, secrets_client)


async def get_org_crm_credentials(
    current_user: User = Depends(get_current_user),
    credentials_service: CRMCredentialsService = Depends(get_crm_credentials_service),
) -> dict:
    """
    Get CRM credentials for the current user's organization.

    FastAPI automatically caches this for the request duration.

    Args:
        current_user: Current authenticated user (guaranteed to have organization_id)
        credentials_service: CRM credentials service

    Returns:
        Dict with 'provider' and 'credentials' keys

    Raises:
        HTTPException: If credentials not configured
    """
    return await credentials_service.get_credentials(current_user.organization_id)


async def get_crm_provider(
    credentials: dict = Depends(get_org_crm_credentials),
) -> CRMProvider:
    """
    Get CRM provider instance with organization-specific credentials.

    FastAPI ensures this uses the cached credentials from get_org_crm_credentials.

    Args:
        credentials: Decrypted credentials from dependency

    Returns:
        CRMProvider instance configured with org credentials

    Raises:
        HTTPException: If provider type is unknown or credentials invalid
    """
    provider_type = credentials.get("provider")
    creds = credentials.get("credentials", {})

    if provider_type == CRMProviderEnum.JOB_NIMBUS:
        logger.info("Instantiating JobNimbus provider from org credentials")
        api_key = creds.get("api_key")
        if not api_key:
            raise HTTPException(
                status_code=500, detail="Missing api_key in JobNimbus credentials"
            )
        return JobNimbusProvider(api_key=api_key)

    elif provider_type == CRMProviderEnum.SERVICE_TITAN:
        logger.info("Instantiating ServiceTitan provider from org credentials")
        required = ["tenant_id", "client_id", "client_secret", "app_key"]
        missing = [f for f in required if not creds.get(f)]
        if missing:
            raise HTTPException(
                status_code=500,
                detail=f"Missing ServiceTitan credentials: {', '.join(missing)}",
            )
        return ServiceTitanProvider(
            tenant_id=creds["tenant_id"],
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            app_key=creds["app_key"],
        )

    else:
        raise HTTPException(
            status_code=400, detail=f"Unknown CRM provider: {provider_type}"
        )


async def get_crm_service(
    crm_provider: CRMProvider = Depends(get_crm_provider),
) -> CRMService:
    """
    Get CRM service instance.

    Args:
        crm_provider: The CRM provider from dependency injection

    Returns:
        CRMService instance
    """
    return CRMService(crm_provider)
