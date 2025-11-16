"""
Authentication and authorization dependencies.

This module provides FastAPI dependencies for handling authentication,
authorization, and user management.
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import schemas
from src.auth.constants import CookieNames, Permission, Role
from src.auth.provider_factory import get_auth_provider
from src.auth.service import AuthProvider
from src.db.database import get_db
from src.db.users.service import UserService

# Security scheme for JWT tokens (fallback for API clients)
security = HTTPBearer(auto_error=False)


async def get_auth_provider_dependency() -> AuthProvider:
    """Dependency to get the configured auth provider."""
    try:
        provider = get_auth_provider()
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Auth provider not configured",
            )
        return provider
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize auth provider: {str(e)}",
        ) from e


async def get_current_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_provider: AuthProvider = Depends(get_auth_provider_dependency),
) -> schemas.Session:
    """
    Get the current user session from cookies or authorization header.

    Args:
        request: The HTTP request
        credentials: The HTTP authorization credentials (optional)
        auth_provider: The configured auth provider

    Returns:
        Session: The current user session

    Raises:
        HTTPException: If the token is invalid or expired
    """
    # First try to get token from cookies (for web clients)
    session_token = request.cookies.get(CookieNames.SESSION_TOKEN.value)

    # Fallback to Bearer token (for API clients)
    if not session_token and credentials:
        session_token = credentials.credentials

    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authentication token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session = await auth_provider.get_session(session_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return session


async def get_current_user(
    session: schemas.Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> schemas.User:
    """
    Get the current user from the session and ensure they have an organization.

    This function ensures that every authenticated user has a persistent
    organization assignment stored in the database.

    Args:
        session: The current user session
        db: Database session

    Returns:
        User: The current user with organization_id populated
    """
    user = session.user

    # Look up or create user in database to get persistent org assignment
    user_service = UserService(db)
    db_user, db_org = await user_service.get_or_create_user(
        user_id=user.id,
        email=user.email
    )

    # Update the user object with the persistent organization_id
    user.organization_id = db_org.id

    return user


async def get_current_user_optional(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    auth_provider: AuthProvider = Depends(get_auth_provider_dependency),
) -> schemas.User | None:
    """
    Get the current user from the session, but return None if not authenticated.
    Useful for endpoints that can be called both authenticated and unauthenticated.

    Args:
        request: The HTTP request
        credentials: The HTTP authorization credentials (optional)
        auth_provider: The configured auth provider

    Returns:
        User | None: The current user or None if not authenticated
    """
    # First try to get token from cookies (for web clients)
    session_token = request.cookies.get(CookieNames.SESSION_TOKEN.value)

    # Fallback to Bearer token (for API clients)
    if not session_token and credentials:
        session_token = credentials.credentials

    if not session_token:
        return None

    try:
        session = await auth_provider.get_session(session_token)
        return session.user if session else None
    except Exception:
        return None


async def require_permission(
    permission: Permission,
    user: schemas.User = Depends(get_current_user),
    auth_provider: AuthProvider = Depends(get_auth_provider_dependency),
) -> schemas.User:
    """
    Require a specific permission for the current user.

    Args:
        permission: The required permission
        user: The current user
        auth_provider: The configured auth provider

    Returns:
        User: The current user if they have the required permission

    Raises:
        HTTPException: If the user doesn't have the required permission
    """
    has_perm = await auth_provider.has_permission(user.id, permission)
    if not has_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission.value}' required",
        )

    return user


async def require_role(
    role: Role, user: schemas.User = Depends(get_current_user)
) -> schemas.User:
    """
    Require a specific role for the current user.

    Args:
        role: The required role
        user: The current user

    Returns:
        User: The current user if they have the required role

    Raises:
        HTTPException: If the user doesn't have the required role
    """
    if user.role != role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role.value}' required",
        )

    return user


# Convenience dependencies for common roles
async def require_admin(user: schemas.User = Depends(get_current_user)) -> schemas.User:
    """Require admin role."""
    return await require_role(Role.ADMIN, user)


async def require_manager(
    user: schemas.User = Depends(get_current_user),
) -> schemas.User:
    """Require manager or admin role."""
    if user.role not in [Role.ADMIN, Role.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or admin role required",
        )
    return user


# Organization-based dependencies
async def require_same_organization(
    target_org_id: str, user: schemas.User = Depends(get_current_user)
) -> schemas.User:
    """
    Require that the user belongs to the same organization as the target.

    Args:
        target_org_id: The target organization ID
        user: The current user

    Returns:
        User: The current user if they belong to the same organization

    Raises:
        HTTPException: If the user doesn't belong to the same organization
    """
    if user.organization_id != target_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: different organization",
        )

    return user


async def require_organization_access(
    org_id: str,
    user: schemas.User = Depends(get_current_user),
    auth_provider: AuthProvider = Depends(get_auth_provider_dependency),
) -> schemas.User:
    """
    Require that the user has access to the specified organization.

    This checks both organization membership and appropriate permissions.

    Args:
        org_id: The organization ID
        user: The current user
        auth_provider: The configured auth provider

    Returns:
        User: The current user if they have access

    Raises:
        HTTPException: If the user doesn't have access
    """
    # Check organization membership
    if user.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: different organization",
        )

    # Check if user has organization view permission
    has_perm = await auth_provider.has_permission(user.id, Permission.VIEW_ORGANIZATION)
    if not has_perm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission to view organization required",
        )

    return user


# Permission-specific dependencies
async def require_manage_users_permission(
    user: schemas.User = Depends(get_current_user),
    auth_provider: AuthProvider = Depends(get_auth_provider_dependency),
) -> schemas.User:
    """Require MANAGE_USERS permission."""
    return await require_permission(Permission.MANAGE_USERS, user, auth_provider)


async def require_manage_roles_permission(
    user: schemas.User = Depends(get_current_user),
    auth_provider: AuthProvider = Depends(get_auth_provider_dependency),
) -> schemas.User:
    """Require MANAGE_ROLES permission."""
    return await require_permission(Permission.MANAGE_ROLES, user, auth_provider)
