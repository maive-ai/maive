"""
Configuration management for database connections.

This module handles database configuration using Pydantic settings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.logger import logger


class DatabaseSettings(BaseSettings):
    """Database configuration using Pydantic settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False, extra="ignore", env_prefix="DB_"
    )

    host: str = Field(description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(description="Database name")
    username: str = Field(description="Database username")
    password: str = Field(description="Database user password")

    # Connection pool settings
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Maximum overflow connections")
    echo: bool = Field(default=False, description="Echo SQL statements to logs")

    def get_sync_url(self) -> str:
        """
        Get synchronous database URL for psycopg2.

        Returns:
            str: Database connection URL for sync operations
        """
        return f"postgresql+psycopg2://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}?sslmode=require"

    def get_async_url(self) -> str:
        """
        Get asynchronous database URL for asyncpg.

        Returns:
            str: Database connection URL for async operations
        """
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}?ssl=require"


# Global settings instance
_db_settings: DatabaseSettings | None = None


def get_db_settings() -> DatabaseSettings:
    """
    Get the global database settings instance.

    Returns:
        DatabaseSettings: The global settings instance
    """
    global _db_settings
    if _db_settings is None:
        _db_settings = DatabaseSettings()
        logger.info(
            f"DatabaseSettings loaded. Host: {_db_settings.host}, "
            f"Port: {_db_settings.port}, Database: {_db_settings.name}"
        )
    return _db_settings


def set_db_settings(settings: DatabaseSettings) -> None:
    """
    Set the global database settings instance.

    Useful for testing.

    Args:
        settings: The settings to set
    """
    global _db_settings
    _db_settings = settings
