"""MCP server factory for CRM integrations."""

from fastmcp import FastMCP

from src.integrations.crm.config import get_crm_settings
from src.integrations.crm.constants import CRMProvider as CRMProviderEnum
from src.utils.logger import logger


def get_crm_mcp_server() -> FastMCP:
    """Get the MCP server for the configured CRM provider.
    
    Returns the appropriate MCP server instance based on the CRM_PROVIDER
    environment variable setting.
    
    Returns:
        FastMCP: The configured MCP server instance
        
    Raises:
        ValueError: If the configured provider is not supported
    """
    settings = get_crm_settings()
    
    if settings.provider == CRMProviderEnum.JOB_NIMBUS:
        logger.info("Loading JobNimbus MCP server")
        from src.integrations.crm.providers.job_nimbus.mcp import mcp
        return mcp
    elif settings.provider == CRMProviderEnum.MOCK:
        logger.info("Loading Mock CRM MCP server")
        from src.integrations.crm.providers.mock.mcp import mcp
        return mcp
    elif settings.provider == CRMProviderEnum.SERVICE_TITAN:
        logger.info("Returning ServiceTitan MCP server")
        from src.integrations.crm.providers.service_titan.mcp import mcp
        return mcp
    else:
        raise ValueError(f"Unsupported CRM provider for MCP: {settings.provider}")


__all__ = ["get_crm_mcp_server"]

