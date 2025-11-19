from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environments."""

    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Current environment (dev, staging, or prod)",
    )
    client_base_url: str = Field(
        default="http://localhost:3000", description="Frontend base URL"
    )
    server_base_url: str = Field(
        default="http://localhost:8080",
        description="Server base URL for MCP and internal APIs",
    )

    # AWS Configuration
    aws_region: str = Field(
        default="us-west-1",
        description="AWS region for services (DynamoDB, Cognito, etc.)",
    )
    dynamodb_table_name: str = Field(
        default="maive-active-calls-dev",
        description="DynamoDB table name for active call state",
    )

    # MCP Authentication
    mcp_auth_token: str | None = Field(
        default=None,
        description="Bearer token for MCP server authentication (optional)",
    )


_app_settings: AppSettings | None = None


def get_app_settings() -> AppSettings:
    global _app_settings
    if _app_settings is None:
        _app_settings = AppSettings()
    return _app_settings


def get_client_base_url() -> str:
    """Get the client base URL from settings."""
    settings = get_app_settings()
    return settings.client_base_url
