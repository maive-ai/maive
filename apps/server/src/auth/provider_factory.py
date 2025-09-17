"""
Auth provider factory.

This module provides a factory function to create the appropriate auth provider
based on configuration.
"""

from src.auth.service import CognitoAuthProvider, AuthProvider
from src.auth.config import get_auth_settings


def create_auth_provider() -> AuthProvider:
    """
    Create an auth provider based on environment configuration.

    Returns:
        AuthProvider: The configured auth provider instance.

    Raises:
        ValueError: If an unknown auth provider is specified.
    """
    settings = get_auth_settings()
    provider = settings.auth_provider.lower()

    if provider == "cognito":
        return CognitoAuthProvider()
    elif provider == "keycloak":
        # TODO: Implement Keycloak provider
        raise NotImplementedError("Keycloak provider not yet implemented")
    elif provider == "custom":
        # TODO: Implement custom provider
        raise NotImplementedError("Custom provider not yet implemented")
    else:
        raise ValueError(f"Unknown auth provider: {provider}")


def get_auth_provider() -> AuthProvider | None:
    """
    Get a singleton instance of the auth provider.

    This function caches the provider instance to avoid recreating it
    on every request.

    Returns:
        Optional[AuthProvider]: The cached auth provider instance.
    """
    if not hasattr(get_auth_provider, "_instance"):
        get_auth_provider._instance = create_auth_provider()
    return get_auth_provider._instance
