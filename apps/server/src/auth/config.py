"""
Configuration management for the auth package.

This module handles environment variable configuration and validation
for the authentication system using Pydantic settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.auth.constants import SameSite
from src.utils.logger import logger


class AuthSettings(BaseSettings):
    """Configuration for the auth system using Pydantic settings."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    # Provider configuration
    auth_provider: str = Field(
        default="cognito", description="Authentication provider to use"
    )

    # AWS Cognito configuration
    aws_region: str = Field(
        default="us-west-1",
        description="AWS region for Cognito (can also be set via AWS_REGION env var)",
    )
    cognito_user_pool_id: str | None = Field(
        default=None, description="Cognito User Pool ID"
    )
    cognito_client_id: str | None = Field(
        default=None, description="Cognito App Client ID"
    )
    cognito_client_secret: str | None = Field(
        default=None, description="Cognito App Client Secret"
    )
    cognito_domain: str = Field(
        default="https://prod-maive.auth-fips.us-west-1.amazoncognito.com",
        description="Cognito domain (hosted UI base URL)",
    )

    # MFA configuration
    auth_mfa_required: bool = Field(default=True, description="Whether MFA is required")
    auth_mfa_methods: str = Field(
        default="email", description="Comma-separated list of MFA methods"
    )

    # Session configuration
    auth_session_timeout_hours: int = Field(description="Session timeout in hours")
    auth_refresh_token_timeout_days: int = Field(
        description="Refresh token timeout in days"
    )

    # OAuth2 configuration
    oauth_redirect_uri: str = Field(
        default="http://localhost:8080/auth/callback",
        description="OAuth2 redirect URI",
    )
    oauth_scope: str = Field(
        default="openid email profile", description="OAuth2 scopes to request"
    )

    # Cookie configuration - defaults to most secure settings
    cookie_secure: bool = Field(
        default=True,
        description="Set secure flag for cookies (True for HTTPS, False for HTTP)",
    )
    cookie_samesite: SameSite = Field(
        default=SameSite.LAX, description="SameSite setting for cookies"
    )
    cookie_domain: str = Field(
        description="Domain for cookies (None for current domain)"
    )
    cookie_httponly: bool = Field(
        default=True, description="Set HttpOnly flag for cookies (True for security)"
    )

    def get_mfa_methods(self) -> list[str]:
        """Get MFA methods as a list."""
        return [
            method.strip()
            for method in self.auth_mfa_methods.split(",")
            if method.strip()
        ]

    def is_cognito_provider(self) -> bool:
        """Check if using Cognito provider."""
        return self.auth_provider.lower() == "cognito"

    def is_keycloak_provider(self) -> bool:
        """Check if using Keycloak provider."""
        return self.auth_provider.lower() == "keycloak"

    def is_custom_provider(self) -> bool:
        """Check if using custom provider."""
        return self.auth_provider.lower() == "custom"


# Global settings instance
_auth_settings: AuthSettings | None = None


def get_auth_settings() -> AuthSettings:
    """
    Get the global auth settings instance.

    Returns:
        AuthSettings: The global settings instance
    """
    global _auth_settings
    if _auth_settings is None:
        _auth_settings = AuthSettings()
        logger.info(
            f"AuthSettings loaded. Client ID: {_auth_settings.cognito_client_id}"
        )
        if _auth_settings.cognito_client_secret:
            logger.info(
                f"AuthSettings loaded. Client Secret (first 5 chars): {_auth_settings.cognito_client_secret[:5]}..."
            )
        else:
            logger.info("AuthSettings loaded without Client Secret.")
    return _auth_settings


def set_auth_settings(settings: AuthSettings) -> None:
    """
    Set the global auth settings instance.

    Args:
        settings: The settings to set
    """
    global _auth_settings
    _auth_settings = settings


# Backward compatibility aliases
AuthConfig = AuthSettings
load_auth_config = get_auth_settings
get_auth_config = get_auth_settings
set_auth_config = set_auth_settings
