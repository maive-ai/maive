"""
CRM credentials management API endpoints.

This module provides endpoints for users to configure their organization's
CRM integration credentials.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.crm_credentials.model import OrganizationCRMCredentials
from src.db.crm_credentials.schemas import CRMCredentials, CRMCredentialsCreate
from src.db.database import get_db
from src.integrations.creds.service import CRMCredentialsService, get_secrets_manager_client

router = APIRouter(prefix="/creds", tags=["Credentials"])


async def get_creds_service(
    db: AsyncSession = Depends(get_db),
    secrets_client=Depends(get_secrets_manager_client),
) -> CRMCredentialsService:
    """
    FastAPI dependency for getting the credentials service.

    Args:
        db: Database session
        secrets_client: AWS Secrets Manager client

    Returns:
        CRMCredentialsService instance
    """
    return CRMCredentialsService(db, secrets_client)


@router.post("", response_model=CRMCredentials, status_code=status.HTTP_201_CREATED)
async def create_crm_credentials(
    data: CRMCredentialsCreate,
    current_user: User = Depends(get_current_user),
    creds_service: CRMCredentialsService = Depends(get_creds_service),
) -> CRMCredentials:
    """
    Create or update CRM credentials for the user's organization.

    If credentials already exist, they will be deactivated and new ones created.

    Args:
        data: CRM credentials data (provider and credentials dict)
        current_user: Current authenticated user
        creds_service: Credentials service

    Returns:
        Created credentials record (without actual credential values)

    Raises:
        HTTPException: If user has no organization or creation fails
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to an organization",
        )

    # Create credentials in Secrets Manager and DB
    cred_record = await creds_service.create_credentials(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        data=data,
    )

    # Convert to response schema
    return CRMCredentials.model_validate(cred_record)


@router.get("", response_model=CRMCredentials)
async def get_crm_credentials(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CRMCredentials:
    """
    Get CRM credentials configuration for the user's organization.

    Note: This endpoint does NOT return the actual credential values,
    only the metadata (provider type, created date, etc.).

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Credentials metadata (no actual secrets)

    Raises:
        HTTPException: If user has no organization or credentials not found
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to an organization",
        )

    result = await db.execute(
        select(OrganizationCRMCredentials).where(
            OrganizationCRMCredentials.organization_id
            == current_user.organization_id,
            OrganizationCRMCredentials.is_active == True,  # noqa: E712
        )
    )
    cred_record = result.scalar_one_or_none()

    if not cred_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No CRM credentials configured for your organization",
        )

    return CRMCredentials.model_validate(cred_record)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_crm_credentials(
    current_user: User = Depends(get_current_user),
    creds_service: CRMCredentialsService = Depends(get_creds_service),
) -> None:
    """
    Delete CRM credentials for the user's organization.

    This removes credentials from both Secrets Manager and the database.

    Args:
        current_user: Current authenticated user
        creds_service: Credentials service

    Raises:
        HTTPException: If user has no organization or credentials not found
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not belong to an organization",
        )

    deleted = await creds_service.delete_credentials(current_user.organization_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No CRM credentials found for your organization",
        )
