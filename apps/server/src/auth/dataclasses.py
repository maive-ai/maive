"""
Core authentication types and interfaces.

This module defines the abstract interfaces that all auth providers must implement,
ensuring consistency across different authentication backends.
"""

from dataclasses import dataclass
from typing import Any

from src.auth.constants import Role


@dataclass
class AuthResult:
    """Result of authentication operations."""

    success: bool
    session: Any | None = None  # Session from schemas
    error: str | None = None
    requires_mfa: bool = False
    mfa_setup_required: bool = False


@dataclass
class SignUpData:
    """Data required for user registration."""

    email: str
    password: str
    name: str | None = None
    organization_id: str | None = None
    role: Role | None = None


@dataclass
class MFASetupResult:
    """Result of MFA setup process."""

    success: bool
    secret_key: str | None = None
    qr_code_url: str | None = None
    backup_codes: list[str] | None = None
    error: str | None = None
