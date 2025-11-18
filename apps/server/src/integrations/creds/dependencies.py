from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.integrations.creds.service import (
    CRMCredentialsService,
    get_secrets_manager_client,
)


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
