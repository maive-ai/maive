"""MCP server factory for CRM integrations."""

from fastmcp import FastMCP

from src.utils.logger import logger


def get_crm_mcp_server() -> FastMCP:
    """Get the MCP server for CRM integrations.

    Returns the multi-tenant JobNimbus MCP server which supports per-user
    authentication and organization-specific credential routing.

    Note: ServiceTitan and Mock MCP servers are not yet multi-tenant enabled.
    For now, we only return the JobNimbus MCP server.

    Returns:
        FastMCP: The JobNimbus MCP server instance with multi-tenant support
    """
    logger.info("Loading JobNimbus MCP server (multi-tenant)")
    from src.integrations.crm.providers.job_nimbus.mcp import mcp
    return mcp


__all__ = ["get_crm_mcp_server"]

