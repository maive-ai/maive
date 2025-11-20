"""Pydantic schemas for CRM credentials."""

from datetime import datetime

from pydantic import BaseModel, Field


class CRMCredentialsBase(BaseModel):
    """Base CRM credentials schema."""

    provider: str = Field(..., description="CRM provider (job_nimbus, service_titan)")


class CRMCredentialsCreate(CRMCredentialsBase):
    """Schema for creating CRM credentials."""

    credentials: dict = Field(
        ..., description="CRM API credentials (will be encrypted)"
    )


class CRMCredentials(CRMCredentialsBase):
    """CRM credentials schema with full details (no actual credentials exposed)."""

    id: str = Field(..., description="Credential record UUID")
    organization_id: str = Field(..., description="Organization UUID")
    secret_arn: str = Field(..., description="AWS Secrets Manager ARN")
    is_active: bool = Field(..., description="Whether credentials are active")
    created_by: str = Field(..., description="User who created the credentials")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class CRMCredentialsWithSecrets(CRMCredentials):
    """CRM credentials with decrypted secrets (for internal use only)."""

    credentials: dict = Field(..., description="Decrypted credentials")
