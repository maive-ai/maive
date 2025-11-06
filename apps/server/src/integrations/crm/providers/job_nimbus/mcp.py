"""JobNimbus MCP Server for CRM job search and retrieval."""

from typing import Any

from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from src.config import get_app_settings
from src.integrations.crm.base import CRMError
from src.integrations.crm.providers.job_nimbus.provider import JobNimbusProvider
from src.utils.logger import logger

# Initialize JobNimbus provider directly (not through factory)
_provider = JobNimbusProvider()

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
mcp = FastMCP(name="JobNimbus CRM", auth=auth)


@mcp.tool
async def get_job(job_id: str) -> dict[str, Any]:
    """Get a specific job by ID from JobNimbus.
    
    Args:
        job_id: The JobNimbus job ID (JNID) to retrieve
        
    Returns:
        Job details including customer name, address, status, and other information
        
    Raises:
        Exception: If the job is not found or an error occurs
    """
    try:
        logger.info(f"[MCP JobNimbus] Getting job: {job_id}")
        job = await _provider.get_job(job_id)
        
        result = job.model_dump()
        logger.info(f"[MCP JobNimbus] Successfully retrieved job {job_id}")
        return result
        
    except CRMError as e:
        logger.error(f"[MCP JobNimbus] CRM error getting job {job_id}: {e.message}")
        raise Exception(f"Failed to get job: {e.message}")
    except Exception as e:
        logger.error(f"[MCP JobNimbus] Unexpected error getting job {job_id}: {e}")
        raise Exception(f"Failed to get job: {str(e)}")


@mcp.tool
async def search_jobs(
    customer_name: str | None = None,
    job_id: str | None = None,
    address: str | None = None,
    claim_number: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """Search for jobs in JobNimbus with various filters.
    
    Use this tool to find jobs based on customer information, job details, or status.
    You can combine multiple search criteria to narrow down results.
    
    Args:
        customer_name: Search by customer name (partial match, case-insensitive)
        job_id: Search by exact job ID
        address: Search by address (partial match)
        claim_number: Search by insurance claim number (exact match)
        status: Filter by job status (e.g., "In Progress", "Scheduled", "Completed")
        page: Page number for pagination (default: 1)
        page_size: Number of results per page (default: 10, max: 50)
        
    Returns:
        A dictionary containing:
        - jobs: List of matching jobs with full details
        - total_count: Total number of matching jobs
        - page: Current page number
        - page_size: Number of results per page
        - has_more: Whether there are more results available
        
    Examples:
        - Search by customer name: search_jobs(customer_name="John Smith")
        - Search by job ID: search_jobs(job_id="jn_12345")
        - Search by status: search_jobs(status="In Progress")
        - Combine filters: search_jobs(customer_name="Smith", status="Completed")
    """
    try:
        logger.info(f"[MCP JobNimbus] Searching jobs with filters: customer_name={customer_name}, "
                   f"job_id={job_id}, address={address}, claim_number={claim_number}, "
                   f"status={status}")
        
        # Build filters dict for provider
        filters = {}
        if customer_name:
            filters["customer_name"] = customer_name
        if job_id:
            filters["job_id"] = job_id
        if address:
            filters["address"] = address
        if claim_number:
            filters["claim_number"] = claim_number
        if status:
            filters["status"] = status
        
        # Delegate to provider (handles all filtering logic)
        job_list = await _provider.get_all_jobs(
            filters=filters if filters else None,
            page=page,
            page_size=page_size,
        )
        
        # Convert to dict format for MCP response
        result = {
            "jobs": [job.model_dump() for job in job_list.jobs],
            "total_count": job_list.total_count,
            "page": job_list.page,
            "page_size": job_list.page_size,
            "has_more": job_list.has_more,
        }
        
        logger.info(f"[MCP JobNimbus] Search returned {len(job_list.jobs)} of {job_list.total_count} total jobs")
        return result
        
    except CRMError as e:
        logger.error(f"[MCP JobNimbus] CRM error searching jobs: {e.message}")
        raise Exception(f"Failed to search jobs: {e.message}")
    except Exception as e:
        logger.error(f"[MCP JobNimbus] Unexpected error searching jobs: {e}")
        raise Exception(f"Failed to search jobs: {str(e)}")

