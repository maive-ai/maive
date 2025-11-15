"""CRM credentials management module."""

from src.integrations.creds.service import CRMCredentialsService, get_secrets_manager_client

__all__ = ["CRMCredentialsService", "get_secrets_manager_client"]
