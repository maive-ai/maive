"""AWS Secrets Manager service for CRM credentials."""

import json
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError
from cachetools import TTLCache
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.crm_credentials.model import OrganizationCRMCredentials
from src.db.crm_credentials.schemas import CRMCredentialsCreate
from src.utils.logger import logger


# In-memory TTL cache: 1000 orgs max, 5 min TTL (300 seconds)
_credentials_cache: TTLCache = TTLCache(maxsize=1000, ttl=300)


@lru_cache()
def get_secrets_manager_client():
    """
    Get AWS Secrets Manager client (singleton).

    Returns:
        boto3 Secrets Manager client
    """
    return boto3.client("secretsmanager")


class CRMCredentialsService:
    """Service for managing CRM credentials in AWS Secrets Manager."""

    def __init__(self, session: AsyncSession, secrets_client=None):
        """
        Initialize the credentials service.

        Args:
            session: Async database session
            secrets_client: Optional secrets manager client (for testing)
        """
        self.session = session
        self.secrets_client = secrets_client or get_secrets_manager_client()

    async def create_credentials(
        self,
        organization_id: str,
        user_id: str,
        data: CRMCredentialsCreate,
    ) -> OrganizationCRMCredentials:
        """
        Create CRM credentials for an organization.

        Args:
            organization_id: Organization UUID
            user_id: User ID creating the credentials
            data: Credentials data

        Returns:
            Created credentials record

        Raises:
            HTTPException: If credentials already exist or secret creation fails
        """
        # Check if active credentials already exist
        existing = await self._get_active_credentials(organization_id)
        if existing:
            # Deactivate existing credentials
            existing.is_active = False
            await self.session.flush()

        # Create secret in AWS Secrets Manager
        secret_name = self._generate_secret_name(organization_id)
        secret_value = json.dumps(
            {"provider": data.provider, "credentials": data.credentials}
        )

        try:
            response = self.secrets_client.create_secret(
                Name=secret_name,
                Description=f"CRM credentials for organization {organization_id}",
                SecretString=secret_value,
            )
            secret_arn = response["ARN"]
            logger.info(
                "Created secret in Secrets Manager",
                organization_id=organization_id,
                secret_arn=secret_arn,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceExistsException":
                # Secret already exists, update it instead
                self.secrets_client.put_secret_value(
                    SecretId=secret_name, SecretString=secret_value
                )
                # Get the ARN
                secret_info = self.secrets_client.describe_secret(SecretId=secret_name)
                secret_arn = secret_info["ARN"]
                logger.info(
                    "Updated existing secret",
                    organization_id=organization_id,
                    secret_arn=secret_arn,
                )
            else:
                logger.error(
                    "Failed to create secret",
                    organization_id=organization_id,
                    error=str(e),
                )
                raise HTTPException(
                    status_code=500, detail="Failed to store credentials"
                )

        # Create database record
        cred_record = OrganizationCRMCredentials(
            organization_id=organization_id,
            provider=data.provider,
            secret_arn=secret_arn,
            is_active=True,
            created_by=user_id,
        )

        self.session.add(cred_record)
        await self.session.flush()
        await self.session.refresh(cred_record)

        # Invalidate cache
        _credentials_cache.pop(organization_id, None)

        return cred_record

    async def get_credentials(self, organization_id: str) -> dict:
        """
        Get decrypted CRM credentials for an organization.

        Implements request-scoped caching via FastAPI and
        cross-request TTL caching for performance.

        Args:
            organization_id: Organization UUID

        Returns:
            Decrypted credentials dict with 'provider' and 'credentials' keys

        Raises:
            HTTPException: If credentials not found or decryption fails
        """
        # Check TTL cache first
        if organization_id in _credentials_cache:
            logger.debug("Credentials cache hit", organization_id=organization_id)
            return _credentials_cache[organization_id]

        logger.debug("Credentials cache miss", organization_id=organization_id)

        # Get active credentials from database
        cred_record = await self._get_active_credentials(organization_id)

        if not cred_record:
            raise HTTPException(
                status_code=404,
                detail=f"No CRM credentials configured for organization {organization_id}",
            )

        # Fetch from Secrets Manager
        try:
            response = self.secrets_client.get_secret_value(
                SecretId=cred_record.secret_arn
            )
            credentials = json.loads(response["SecretString"])

            # Cache for 5 minutes
            _credentials_cache[organization_id] = credentials

            logger.info(
                "Retrieved credentials from Secrets Manager",
                organization_id=organization_id,
                provider=credentials.get("provider"),
            )

            return credentials

        except ClientError as e:
            logger.error(
                "Failed to retrieve secret",
                organization_id=organization_id,
                secret_arn=cred_record.secret_arn,
                error=str(e),
            )
            raise HTTPException(
                status_code=500, detail="Failed to retrieve credentials"
            )

    async def delete_credentials(self, organization_id: str) -> bool:
        """
        Delete CRM credentials for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            True if deleted, False if not found
        """
        cred_record = await self._get_active_credentials(organization_id)

        if not cred_record:
            return False

        # Delete from Secrets Manager
        try:
            self.secrets_client.delete_secret(
                SecretId=cred_record.secret_arn,
                ForceDeleteWithoutRecovery=True,  # Immediate deletion
            )
            logger.info(
                "Deleted secret from Secrets Manager",
                organization_id=organization_id,
                secret_arn=cred_record.secret_arn,
            )
        except ClientError as e:
            logger.warning(
                "Failed to delete secret (may not exist)",
                organization_id=organization_id,
                error=str(e),
            )

        # Mark as inactive in database
        cred_record.is_active = False
        await self.session.flush()

        # Invalidate cache
        _credentials_cache.pop(organization_id, None)

        return True

    async def _get_active_credentials(
        self, organization_id: str
    ) -> OrganizationCRMCredentials | None:
        """
        Get active credentials record from database.

        Args:
            organization_id: Organization UUID

        Returns:
            Credentials record or None
        """
        result = await self.session.execute(
            select(OrganizationCRMCredentials).where(
                OrganizationCRMCredentials.organization_id == organization_id,
                OrganizationCRMCredentials.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    def _generate_secret_name(self, organization_id: str) -> str:
        """
        Generate AWS Secrets Manager secret name.

        Args:
            organization_id: Organization UUID

        Returns:
            Secret name
        """
        # TODO: Get environment from config
        environment = "dev"  # Replace with actual env
        return f"maive/{environment}/crm/{organization_id}"
