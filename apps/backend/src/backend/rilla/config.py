"""Configuration management for Rilla API client."""


from pydantic import Field
from pydantic_settings import BaseSettings


class RillaSettings(BaseSettings):
    """Settings for Rilla API client.

    All settings can be configured via environment variables with RILLA_ prefix.
    """

    api_key: str = Field(..., description="Rilla API key for authentication")
    base_url: str = Field(
        "https://customer.rillavoice.com",
        description="Base URL for Rilla API"
    )
    timeout: int = Field(30, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retry attempts")
    retry_delay: float = Field(1.0, description="Base delay between retries in seconds")
    max_retry_delay: float = Field(60.0, description="Maximum delay between retries in seconds")
    backoff_factor: float = Field(2.0, description="Exponential backoff factor for retries")

    # Rate limiting
    requests_per_minute: int = Field(60, description="Maximum requests per minute")
    burst_limit: int = Field(10, description="Burst limit for requests")

    # Logging
    log_requests: bool = Field(False, description="Whether to log HTTP requests")
    log_responses: bool = Field(False, description="Whether to log HTTP responses")
    mask_sensitive_data: bool = Field(True, description="Whether to mask sensitive data in logs")

    class Config:
        """Pydantic config."""
        env_prefix = "RILLA_"
        case_sensitive = False


def get_rilla_settings(
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs,
) -> RillaSettings:
    """Get Rilla settings with optional overrides.

    Args:
        api_key: Override API key
        base_url: Override base URL
        **kwargs: Additional setting overrides

    Returns:
        Configured RillaSettings instance
    """
    overrides = {}

    if api_key is not None:
        overrides["api_key"] = api_key
    if base_url is not None:
        overrides["base_url"] = base_url

    overrides.update(kwargs)

    return RillaSettings(**overrides)
