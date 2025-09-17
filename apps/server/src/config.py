from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environments."""

    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Current environment (dev, staging, or prod)",
    )
    client_base_url: str = Field(
        default="http://localhost:3000", description="Frontend base URL"
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
