"""ServiceTitan MCP server - exposes CRM tools via Model Context Protocol."""


from typing import Any

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from src.config import get_app_settings
from src.integrations.crm.base import CRMError
from src.integrations.crm.providers.service_titan.provider import ServiceTitanProvider
from src.utils.logger import logger

# Initialize ServiceTitan provider directly (not through factory)
_provider = ServiceTitanProvider()

# Create MCP server instance with optional auth
settings = get_app_settings()
auth = None
if settings.mcp_auth_token:
    # Use StaticTokenVerifier for simple bearer token authentication
    auth = StaticTokenVerifier(
        tokens={
            settings.mcp_auth_token: {
                "sub": "openai-integration",
                "aud": "maive-mcp-server",
                "client_id": "openai-client",
                "scopes": [],  # No scope restrictions
            }
        }
    )
mcp = FastMCP(name="ServiceTitan CRM", auth=auth)


@mcp.tool
async def get_job(job_id: str) -> dict[str, Any]:
    """
    Get a specific job by ID from ServiceTitan.
    
    Use this tool to retrieve detailed information about a job, including customer details,
    status, location, and other relevant data.
    
    Args:
        job_id: The unique identifier for the job (ServiceTitan job ID)
        
    Returns:
        A dictionary containing the job details including:
        - id: Job ID
        - name: Job name
        - status: Current job status
        - customer_name: Name of the customer
        - address: Job location
        - And other job-related information
        
    Example:
        get_job(job_id="12345")
    """
    try:
        logger.info(f"[MCP ServiceTitan] Getting job {job_id}")
        job = await _provider.get_job(job_id)
        return job.model_dump()
        
    except CRMError as e:
        logger.error(f"[MCP ServiceTitan] CRM error getting job {job_id}: {e.message}")
        raise Exception(f"Failed to get job: {e.message}")
    except Exception as e:
        logger.error(f"[MCP ServiceTitan] Unexpected error getting job {job_id}: {e}")
        raise Exception(f"Failed to get job: {str(e)}")

