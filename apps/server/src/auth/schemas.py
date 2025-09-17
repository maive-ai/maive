"""
Auth-specific Pydantic schemas for request and response models.

This module contains all Pydantic models related to authentication,
authorization, and user management.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.auth.constants import Role


# Core domain models
class User(BaseModel):
    """User information."""

    id: str = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    name: str | None = Field(
        None, min_length=1, max_length=128, description="User's full name"
    )
    role: Role | None = Field(None, description="User's role")
    organization_id: str | None = Field(None, description="User's organization ID")
    profile_picture: str | None = Field(None, description="User's profile picture URL")
    email_verified: bool = Field(
        default=False, description="Whether user's email is verified"
    )
    mfa_enabled: bool = Field(
        default=False, description="Whether MFA is enabled for the user"
    )
    created_at: datetime | None = Field(None, description="User creation timestamp")
    updated_at: datetime | None = Field(None, description="User last update timestamp")


class Session(BaseModel):
    """User session information."""

    user: User | None = Field(None, description="User information")
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    id_token: str | None = Field(None, description="ID token")


# Response schemas
class AuthResponse(BaseModel):
    """Schema for authentication responses."""

    success: bool = Field(..., description="Whether the operation was successful")
    session: dict[str, Any] | None = Field(None, description="User session data")
    error: str | None = Field(None, description="Error message if operation failed")
    requires_mfa: bool = Field(default=False, description="Whether MFA is required")
    mfa_setup_required: bool = Field(
        default=False, description="Whether MFA setup is required"
    )


class MFASetupResponse(BaseModel):
    """Schema for MFA setup responses."""

    success: bool = Field(..., description="Whether setup was successful")
    secret_key: str | None = Field(None, description="Secret key for authenticator app")
    qr_code_url: str | None = Field(None, description="QR code URL for setup")
    backup_codes: list[str] | None = Field(None, description="Backup codes")
    error: str | None = Field(None, description="Error message if setup failed")


class SuccessResponse(BaseModel):
    """Schema for success responses."""

    success: bool = Field(default=True, description="Operation success status")
    data: dict[str, Any] | None = Field(None, description="Response data")
    message: str = Field(..., description="Success message")
