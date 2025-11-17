"""
FastAPI dependencies for MCP server authentication and provider injection.

This module bridges FastMCP's JWT authentication with our multi-tenant
credential system, enabling per-organization CRM provider routing.
"""

from fastapi import HTTPException
from fastmcp import Context
from fastmcp.server.dependencies import get_access_token

from src.db.database import get_db
from src.db.users.service import UserService
from src.integrations.creds.service import (
    CRMCredentialsService,
    get_secrets_manager_client,
)
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.integrations.crm.providers.job_nimbus.provider import JobNimbusProvider
from src.utils.logger import logger


async def get_job_nimbus_provider_from_context(ctx: Context) -> JobNimbusProvider:
    """
    Get JobNimbus provider for authenticated user from FastMCP Context.

    This is the main entry point for MCP tool functions. It:
    1. Extracts the validated JWT claims from FastMCP's auth context
    2. Looks up user's organization in database
    3. Fetches CRM credentials for that organization
    4. Returns JobNimbusProvider instance with org-specific credentials

    Args:
        ctx: FastMCP Context object

    Returns:
        JobNimbusProvider configured with organization's credentials

    Raises:
        HTTPException: If authentication fails or credentials not configured
    """
    # Get the access token from FastMCP's auth context (validated by JWTVerifier)
    access_token = get_access_token()

    if not access_token:
        logger.error("No access token found in MCP request")
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide a valid JWT token.",
        )

    # Extract user_id and email from JWT claims
    claims = access_token.claims
    user_id = claims.get("sub")
    email = claims.get("email") or claims.get("cognito:username")

    if not user_id:
        logger.error("Missing 'sub' claim in JWT", claims=list(claims.keys()))
        raise HTTPException(
            status_code=401,
            detail="Invalid token: missing user ID claim",
        )

    if not email:
        logger.warning("Missing email claim in JWT, using user_id as fallback", user_id=user_id)
        email = f"{user_id}@unknown.local"

    logger.info("Extracted user from JWT claims", user_id=user_id, email=email)

    # Get database session
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        # Look up user in database to get organization
        user_service = UserService(db)
        db_user, db_org = await user_service.get_or_create_user(user_id, email)

        organization_id = db_org.id
        logger.info(
            "Resolved user to organization",
            user_id=user_id,
            organization_id=organization_id,
            organization_name=db_org.name,
        )

        # Get secrets client and credentials service
        secrets_client = get_secrets_manager_client()
        creds_service = CRMCredentialsService(db, secrets_client)

        # Get CRM credentials for this organization
        try:
            credentials = await creds_service.get_credentials(organization_id)
        except HTTPException as e:
            if e.status_code == 404:
                logger.warning(
                    "Organization has no CRM credentials configured",
                    organization_id=organization_id,
                    user_id=user_id,
                )
                raise HTTPException(
                    status_code=400,
                    detail="Your organization has not configured JobNimbus credentials. "
                           "Please add credentials in the settings page.",
                )
            raise

        # Verify it's JobNimbus
        provider_type = credentials.get("provider")
        if provider_type != CRMProviderEnum.JOB_NIMBUS:
            logger.warning(
                "Organization credentials not for JobNimbus",
                organization_id=organization_id,
                actual_provider=provider_type,
            )
            raise HTTPException(
                status_code=400,
                detail=f"Your organization is configured for {provider_type}, not JobNimbus. "
                       "Please update your CRM settings.",
            )

        # Extract JobNimbus API key
        creds = credentials.get("credentials", {})
        api_key = creds.get("api_key")

        if not api_key:
            logger.error(
                "JobNimbus credentials missing api_key",
                organization_id=organization_id,
            )
            raise HTTPException(
                status_code=500,
                detail="Invalid JobNimbus credentials configuration. Please re-save your credentials.",
            )

        # Create and return provider instance
        logger.info(
            "Creating JobNimbus provider for organization",
            organization_id=organization_id,
            user_id=user_id,
        )

        return JobNimbusProvider(api_key=api_key)

    finally:
        # Close database session
        await db.close()
