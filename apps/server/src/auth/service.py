"""
AWS Cognito authentication provider.

This module implements the AuthProvider interface using AWS Cognito User Pools
for authentication, authorization, and user management.
"""

import base64
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import boto3
import requests
from botocore.exceptions import ClientError

from src.auth import schemas
from src.auth.config import get_auth_settings
from src.auth.constants import (
    OAuthEndpoints,
    Permission,
    Role,
    TimeInSeconds,
)
from src.auth.dataclasses import AuthResult, MFASetupResult, SignUpData
from src.utils.logger import logger


class AuthProvider(ABC):
    """Abstract interface for authentication providers."""

    @abstractmethod
    async def sign_in(self, email: str, password: str) -> AuthResult:
        """Sign in a user with email and password."""
        pass

    @abstractmethod
    async def sign_up(self, data: SignUpData) -> AuthResult:
        """Register a new user."""
        pass

    @abstractmethod
    async def sign_out(self, access_token: str) -> bool:
        """Sign out a user."""
        pass

    @abstractmethod
    async def get_session(self, access_token: str) -> schemas.Session | None:
        """Get session information from access token."""
        pass

    @abstractmethod
    async def refresh_session(
        self, refresh_token: str, email: str | None = None
    ) -> AuthResult:
        """Refresh an expired session."""
        pass

    @abstractmethod
    async def get_user(self, user_id: str) -> schemas.User | None:
        """Get user information by ID."""
        pass

    @abstractmethod
    async def update_user(
        self, user_id: str, data: dict[str, Any]
    ) -> schemas.User | None:
        """Update user information."""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        pass

    @abstractmethod
    async def setup_mfa(self, user_id: str) -> MFASetupResult:
        """Set up MFA for a user."""
        pass

    @abstractmethod
    async def verify_mfa(self, user_id: str, code: str) -> bool:
        """Verify MFA code for a user."""
        pass

    @abstractmethod
    async def enable_mfa(self, user_id: str) -> bool:
        """Enable MFA for a user."""
        pass

    @abstractmethod
    async def disable_mfa(self, user_id: str) -> bool:
        """Disable MFA for a user."""
        pass

    @abstractmethod
    async def get_user_roles(self, user_id: str) -> list[Role]:
        """Get roles for a user."""
        pass

    @abstractmethod
    async def assign_role(self, user_id: str, role: Role) -> bool:
        """Assign a role to a user."""
        pass

    @abstractmethod
    async def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        pass

    @abstractmethod
    async def create_organization(
        self, name: str, domain: str | None = None
    ) -> Any | None:
        """Create a new organization."""
        pass

    @abstractmethod
    async def get_organization(self, org_id: str) -> Any | None:
        """Get organization information."""
        pass

    @abstractmethod
    async def update_organization(
        self, org_id: str, data: dict[str, Any]
    ) -> Any | None:
        """Update organization information."""
        pass

    @abstractmethod
    async def delete_organization(self, org_id: str) -> bool:
        """Delete an organization."""
        pass

    @abstractmethod
    async def get_organization_users(self, org_id: str) -> list[schemas.User]:
        """Get all users in an organization."""
        pass

    @abstractmethod
    async def exchange_code_for_tokens(self, code: str) -> AuthResult:
        """
        Exchange authorization code for tokens using OAuth2 flow.

        This method handles the OAuth2 authorization code flow from Cognito hosted UI.
        """
        pass


class CognitoAuthProvider(AuthProvider):
    """AWS Cognito implementation of the AuthProvider interface."""

    def __init__(self):
        """Initialize the Cognito auth provider."""
        settings = get_auth_settings()
        self.region = settings.aws_region
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self.client_secret = settings.cognito_client_secret

        # Use the configured domain from settings, not construct from user_pool_id
        self.cognito_domain = settings.cognito_domain
        # Cache redirect URI to avoid dynamic lookup per request
        self.oauth_redirect_uri = settings.oauth_redirect_uri

        if not all([self.user_pool_id, self.client_id]):
            raise ValueError("COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID must be set")

        logger.info(f"CognitoAuthProvider initialized with Client ID: {self.client_id}")
        if self.client_secret:
            logger.info(
                f"CognitoAuthProvider initialized with Client Secret (first 5 chars): {self.client_secret[:5]}..."
            )
        else:
            logger.info("CognitoAuthProvider initialized without Client Secret.")

        # Initialize AWS client - boto3 will automatically use AWS credentials
        # and region from environment/profile
        self.cognito_client = boto3.client("cognito-idp", region_name=self.region)

    async def sign_in(self, email: str, password: str) -> AuthResult:
        """Sign in a user with email and password."""
        # Not implemented - using OAuth2 flow instead
        raise NotImplementedError("Use OAuth2 flow for authentication")

    async def sign_up(self, data: SignUpData) -> AuthResult:
        """Register a new user."""
        # Not implemented - using Cognito hosted UI for signup
        raise NotImplementedError("Use Cognito hosted UI for user registration")

    async def sign_out(self, access_token: str) -> bool:
        """Sign out a user."""
        try:
            self.cognito_client.global_sign_out(AccessToken=access_token)
            return True
        except ClientError:
            return False

    async def get_session(self, access_token: str) -> schemas.Session | None:
        """Get session information from access token."""
        try:
            # Get user info from userinfo endpoint
            user_info_url = urljoin(
                self.cognito_domain, OAuthEndpoints.USERINFO_ENDPOINT
            )
            user_info_response = requests.get(
                user_info_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()

            user = await self._create_user_from_userinfo_response(user_info)
            if not user:
                return None

            # Create session object
            # Note: We don't have refresh token here, so this is a limited session
            session = schemas.Session(
                user=user,
                access_token=access_token,
                refresh_token="",  # Not available in this context
                expires_at=datetime.now(UTC)
                + timedelta(seconds=TimeInSeconds.ONE_HOUR),
                id_token=None,
            )

            return session

        except (requests.exceptions.RequestException, ClientError):
            return None

    async def refresh_session(
        self, refresh_token: str, email: str | None = None
    ) -> AuthResult:
        """
        Refresh an expired session using GetTokensFromRefreshToken
        (for refresh token rotation).
        """
        logger.info(
            f"Attempting to refresh session with refresh token: {refresh_token[:5]}..."
        )
        try:
            # When refresh token rotation is enabled, we must use
            # GetTokensFromRefreshToken instead of REFRESH_TOKEN_AUTH flow
            response = self.cognito_client.get_tokens_from_refresh_token(
                RefreshToken=refresh_token,
                ClientId=self.client_id,
                ClientSecret=self.client_secret,
            )

            logger.info("Received response from get_tokens_from_refresh_token")

            # Get user info to create session
            auth_result = response.get("AuthenticationResult", {})
            access_token = auth_result.get("AccessToken")

            if not access_token:
                logger.warning(
                    "No access token obtained from Cognito refresh response."
                )
                return AuthResult(
                    success=False,
                    error="Failed to obtain new access token from refresh token",
                )

            # Directly create session with new tokens, user info will be fetched separately if needed
            session = schemas.Session(
                user=None,  # User info is not fetched in this simplified flow
                access_token=access_token,
                refresh_token=auth_result.get("RefreshToken", refresh_token),
                expires_at=datetime.now(UTC)
                + timedelta(
                    seconds=auth_result.get("ExpiresIn", TimeInSeconds.ONE_HOUR)
                ),
                id_token=auth_result.get("IdToken"),
            )
            logger.info(
                f"Successfully refreshed session. New access token starts with: {session.access_token[:5]}..."
            )
            logger.debug(f"ID Token: {session.id_token}")
            return AuthResult(success=True, session=session)

        except ClientError as e:
            logger.error(f"ClientError during token refresh: {e.response['Error']}")
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            return AuthResult(
                success=False,
                error=f"Token refresh failed ({error_code}): {error_message}",
            )
        except Exception as e:
            logger.exception("Unexpected error during session refresh.")
            return AuthResult(
                success=False, error=f"Failed to refresh session: {str(e)}"
            )

    async def get_user(self, user_id: str) -> schemas.User | None:
        """Get user information by ID."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def update_user(
        self, user_id: str, data: dict[str, Any]
    ) -> schemas.User | None:
        """Update user information."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def setup_mfa(self, user_id: str) -> MFASetupResult:
        """Set up MFA for a user."""
        # Not implemented - placeholder for future implementation
        raise NotImplementedError("MFA setup not yet implemented")

    async def verify_mfa(self, user_id: str, code: str) -> bool:
        """Verify MFA code for a user."""
        # Not implemented - placeholder for future implementation
        raise NotImplementedError("MFA verification not yet implemented")

    async def enable_mfa(self, user_id: str) -> bool:
        """Enable MFA for a user."""
        # Not implemented - placeholder for future implementation
        raise NotImplementedError("MFA enable not yet implemented")

    async def disable_mfa(self, user_id: str) -> bool:
        """Disable MFA for a user."""
        # Not implemented - placeholder for future implementation
        raise NotImplementedError("MFA disable not yet implemented")

    async def get_user_roles(self, user_id: str) -> list[Role]:
        """Get roles for a user."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def assign_role(self, user_id: str, role: Role) -> bool:
        """Assign a role to a user using Cognito groups."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def create_organization(
        self, name: str, domain: str | None = None
    ) -> Any | None:
        """Create a new organization."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def get_organization(self, org_id: str) -> Any | None:
        """Get organization information."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def update_organization(
        self, org_id: str, data: dict[str, Any]
    ) -> Any | None:
        """Update organization information."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def delete_organization(self, org_id: str) -> bool:
        """Delete an organization."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def get_organization_users(self, org_id: str) -> list[schemas.User]:
        """Get all users in an organization."""
        # Not implemented - not needed for current flow
        raise NotImplementedError("Not implemented")

    async def exchange_code_for_tokens(self, code: str) -> AuthResult:
        """
        Exchange authorization code for tokens using OAuth2 flow.

        This method handles the OAuth2 authorization code flow from Cognito hosted UI.
        """
        try:
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "code": code,
                "redirect_uri": self.oauth_redirect_uri,
            }
            if self.client_secret:
                data["client_secret"] = self.client_secret

            # Debug: Log the URL being constructed
            token_url = urljoin(self.cognito_domain, OAuthEndpoints.TOKEN_ENDPOINT)
            logger.debug(f"Token URL: {token_url}")
            logger.debug(f"Cognito domain: {self.cognito_domain}")
            logger.debug(f"Token endpoint: {OAuthEndpoints.TOKEN_ENDPOINT}")

            response = requests.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()  # Raise an exception for HTTP errors

            token_data = response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            id_token = token_data.get("id_token")

            if not access_token:
                return AuthResult(
                    success=False,
                    error="Failed to obtain access token from authorization code",
                )

            # Get user info from access token using the userInfo endpoint
            user_info_url = urljoin(
                self.cognito_domain, OAuthEndpoints.USERINFO_ENDPOINT
            )
            user_info_response = requests.get(
                user_info_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_info_response.raise_for_status()
            user_info = user_info_response.json()
            user = await self._create_user_from_userinfo_response(user_info)

            if not user:
                return AuthResult(
                    success=False,
                    error="Failed to get user information from access token",
                )

            # Create session
            session = schemas.Session(
                user=user,
                access_token=access_token,
                refresh_token=refresh_token or "",
                expires_at=datetime.now(UTC)
                + timedelta(
                    seconds=token_data.get("expires_in", TimeInSeconds.ONE_HOUR)
                ),
                id_token=id_token,
            )

            return AuthResult(success=True, session=session)

        except requests.exceptions.RequestException as e:
            logger.error(
                f"HTTP error during token exchange: {e.response.text if e.response else e}"
            )
            return AuthResult(
                success=False, error=f"HTTP error during token exchange: {e}"
            )
        except Exception as e:
            logger.exception(f"Failed to exchange authorization code: {e}")
            return AuthResult(
                success=False, error=f"Failed to exchange authorization code: {str(e)}"
            )

    # Helper methods

    def _calculate_secret_hash(self, username: str) -> str:
        """Calculate the secret hash for Cognito API calls."""
        if not self.client_secret:
            return ""

        message = str(username) + str(self.client_id)
        import hashlib
        import hmac

        dig = hmac.new(
            self.client_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        )
        return base64.b64encode(dig.digest()).decode()

    async def _create_user_from_cognito_response(
        self, response: dict
    ) -> schemas.User | None:
        """Create a User object from Cognito response."""
        try:
            # Extract attributes
            attributes = {
                attr["Name"]: attr["Value"]
                for attr in response.get("UserAttributes", [])
            }

            # Get role from groups (default to USER if no groups found)
            role = Role.USER  # Default role
            username = response.get("Username", "")

            # Try to get user's groups to determine role
            try:
                groups_response = self.cognito_client.admin_list_groups_for_user(
                    Username=username, UserPoolId=self.user_pool_id
                )
                groups = [
                    group["GroupName"] for group in groups_response.get("Groups", [])
                ]

                # Map group names to roles
                if "admin" in groups:
                    role = Role.ADMIN
                elif "manager" in groups:
                    role = Role.MANAGER
                elif "user" in groups:
                    role = Role.USER
                # If no groups found, default to USER
            except ClientError:
                # If we can't get groups (e.g., user not confirmed), default to USER
                pass

            return schemas.User(
                id=username,
                email=attributes.get("email", ""),
                name=attributes.get("name"),
                organization_id=None,  # No organization support for now
                role=role,
                profile_picture=attributes.get("picture"),
                email_verified=attributes.get("email_verified", "false").lower()
                == "true",
                mfa_enabled=response.get("MFAOptions", []) != [],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

        except Exception:
            return None

    async def _create_user_from_userinfo_response(
        self, response: dict
    ) -> schemas.User | None:
        """Create a User object from Cognito /userinfo response."""
        try:
            user_id = response.get("sub")
            if not user_id:
                return None

            # Use default USER role since userInfo endpoint doesn't provide role information
            # Role information would need to be retrieved separately via admin API if needed
            role = Role.USER

            return schemas.User(
                id=user_id,
                email=response.get("email", ""),
                name=response.get("name"),
                organization_id=None,
                role=role,
                profile_picture=response.get("picture"),
                email_verified=str(response.get("email_verified", "false")).lower()
                == "true",
                mfa_enabled=False,  # This info is not in userInfo endpoint
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.exception(f"Error creating user from userinfo: {e}")
            return None


class MockAuthProvider(AuthProvider):
    """Mock implementation of AuthProvider for testing and local development."""

    def __init__(self, *, user=None, session=None, fail=False):
        self._user = user
        self._session = session
        self._fail = fail

    async def sign_in(self, email: str, password: str) -> AuthResult:
        if self._fail:
            return AuthResult(success=False, error="Mocked sign-in failure")
        return AuthResult(success=True, session=self._session)

    async def sign_up(self, data: SignUpData) -> AuthResult:
        if self._fail:
            return AuthResult(success=False, error="Mocked sign-up failure")
        return AuthResult(success=True, session=self._session)

    async def sign_out(self, access_token: str) -> bool:
        return not self._fail

    async def get_session(self, access_token: str) -> schemas.Session | None:
        return self._session if not self._fail else None

    async def refresh_session(
        self, refresh_token: str, email: str | None = None
    ) -> AuthResult:
        if self._fail:
            return AuthResult(success=False, error="Mocked refresh failure")
        return AuthResult(success=True, session=self._session)

    async def get_user(self, user_id: str) -> schemas.User | None:
        return self._user if not self._fail else None

    async def update_user(
        self, user_id: str, data: dict[str, Any]
    ) -> schemas.User | None:
        return self._user if not self._fail else None

    async def delete_user(self, user_id: str) -> bool:
        return not self._fail

    async def setup_mfa(self, user_id: str) -> MFASetupResult:
        if self._fail:
            return MFASetupResult(success=False, error="Mocked MFA setup failure")
        return MFASetupResult(
            success=True,
            secret_key="mock_secret",
            qr_code_url="mock_qr",
            backup_codes=["code1", "code2"],
        )

    async def verify_mfa(self, user_id: str, code: str) -> bool:
        return not self._fail

    async def enable_mfa(self, user_id: str) -> bool:
        return not self._fail

    async def disable_mfa(self, user_id: str) -> bool:
        return not self._fail

    async def get_user_roles(self, user_id: str) -> list[Role]:
        if self._fail or not self._user:
            return []
        return [self._user.role] if self._user and self._user.role else []

    async def assign_role(self, user_id: str, role: Role) -> bool:
        return not self._fail

    async def has_permission(self, user_id: str, permission: Permission) -> bool:
        return not self._fail

    async def create_organization(
        self, name: str, domain: str | None = None
    ) -> Any | None:
        if self._fail:
            return None
        return {"id": "mock_org", "name": name, "domain": domain}

    async def get_organization(self, org_id: str) -> Any | None:
        if self._fail:
            return None
        return {"id": org_id, "name": "Mock Org", "domain": "mock.com"}

    async def update_organization(
        self, org_id: str, data: dict[str, Any]
    ) -> Any | None:
        if self._fail:
            return None
        return {"id": org_id, **data}

    async def delete_organization(self, org_id: str) -> bool:
        return not self._fail

    async def get_organization_users(self, org_id: str) -> list[schemas.User]:
        if self._fail or not self._user:
            return []
        return [self._user]

    async def exchange_code_for_tokens(self, code: str) -> AuthResult:
        if self._fail:
            return AuthResult(success=False, error="Mocked code exchange failure")
        return AuthResult(success=True, session=self._session)
