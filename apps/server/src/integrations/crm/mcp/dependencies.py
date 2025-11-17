"""
MCP server dependencies for multi-tenant authentication.

Bridges FastMCP JWT authentication with existing REST API credential infrastructure.
"""

from contextlib import asynccontextmanager

from fastapi import HTTPException
from fastmcp import Context
from fastmcp.server.dependencies import get_access_token

from src.auth.schemas import User
from src.db.database import get_db
from src.db.users.service import UserService
from src.integrations.creds.service import (
    CRMCredentialsService,
    get_secrets_manager_client,
)
from src.integrations.crm.dependencies import get_crm_provider
from src.integrations.crm.providers.job_nimbus.provider import JobNimbusProvider
from src.utils.logger import logger


@asynccontextmanager
async def _db_session():
    """
    Context manager for database session that properly handles commit/rollback.

    This ensures the get_db() generator's cleanup logic (commit on success,
    rollback on exception) is properly executed by continuing the generator
    after the yield point. Exceptions are sent to the generator using athrow()
    so the rollback logic executes correctly.
    """
    import sys

    db_gen = get_db()
    db = await anext(db_gen)
    try:
        yield db
    except Exception:
        # Send exception to generator to trigger rollback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        # athrow() sends exception to generator, which handles it (rollback)
        # and re-raises it, so the exception will propagate naturally
        try:
            await db_gen.athrow(exc_type, exc_value, exc_traceback)
        except StopAsyncIteration:
            # Generator exhausted without re-raising (unlikely but possible)
            # Re-raise the original exception
            raise exc_value from None
    else:
        # No exception - continue generator to trigger commit
        try:
            await anext(db_gen)
        except StopAsyncIteration:
            # Generator exhausted after commit - this is expected on success
            pass


async def get_user_from_mcp_token() -> User:
    """
    Extract authenticated user from validated MCP JWT token.

    This is the MCP equivalent of get_current_user() for REST APIs.
    It extracts user_id from the JWT and looks up organization assignment.

    Returns:
        User object with organization_id populated

    Raises:
        HTTPException: If token is missing or invalid
    """
    # Get validated access token from FastMCP (already verified by JWTVerifier)
    access_token = get_access_token()
    if not access_token:
        raise HTTPException(401, "Authentication required")

    # Extract user_id from JWT claims
    user_id = access_token.claims.get("sub")
    if not user_id:
        raise HTTPException(401, "Invalid token: missing user ID")

    # Try to get email from various JWT claim locations
    email = (
        access_token.claims.get("email")
        or access_token.claims.get("cognito:username")
        or access_token.claims.get("username")
    )

    logger.info("MCP request from user", user_id=user_id, has_email=bool(email))

    # Use database session with proper cleanup (commit/rollback)
    async with _db_session() as db:
        # Look up user to get organization (same as REST API)
        user_service = UserService(db)
        db_user, db_org = await user_service.get_or_create_user(user_id, email)

        logger.info(
            "Resolved to organization",
            organization_id=db_org.id,
            organization_name=db_org.name,
        )

        # Return User schema (matches get_current_user() from REST API)
        return User(
            id=user_id,
            email=db_user.email,
            organization_id=db_org.id,
            role=None,
        )


async def get_job_nimbus_provider_from_context(ctx: Context) -> JobNimbusProvider:
    """
    Get JobNimbus provider for authenticated MCP request.

    This composes existing dependencies:
    1. get_user_from_mcp_token() - Extract user from JWT
    2. CRMCredentialsService.get_credentials() - Fetch org credentials
    3. get_crm_provider() - Create provider instance

    Args:
        ctx: FastMCP Context (unused, but required by FastMCP signature)

    Returns:
        JobNimbusProvider with organization-specific credentials

    Raises:
        HTTPException: If auth fails or org not configured for JobNimbus
    """
    # Step 1: Get user from JWT token
    user = await get_user_from_mcp_token()

    # Step 2: Get credentials for user's organization (reuse REST API logic)
    # Use database session with proper cleanup (commit/rollback)
    async with _db_session() as db:
        creds_service = CRMCredentialsService(db, get_secrets_manager_client())
        credentials = await creds_service.get_credentials(user.organization_id)

        # Step 3: Create provider using existing factory (reuse REST API logic)
        provider = await get_crm_provider(credentials)

        # Step 4: Verify type
        if not isinstance(provider, JobNimbusProvider):
            raise HTTPException(
                400,
                f"Organization configured for {credentials.get('provider')}, not JobNimbus",
            )

        return provider
