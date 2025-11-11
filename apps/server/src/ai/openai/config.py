"""OpenAI API configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    """Settings for OpenAI API integration.

    Attributes:
        api_key: OpenAI API key for authentication
        model_name: Default model to use (e.g., 'gpt-4o', 'gpt-5', 'o1')
        audio_model_name: Model to use for audio processing
        temperature: Default temperature for non-reasoning models (0.0-2.0)
        max_tokens: Default max output tokens for generation
        reasoning_effort: Default reasoning effort for reasoning models
        text_verbosity: Default text verbosity for reasoning models

    Note:
        For reasoning models (gpt-5, o1, o3), temperature/top_p/logprobs are not
        supported. Use reasoning_effort and text_verbosity instead.
    """

    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: str = Field(
        ...,
        description="OpenAI API key",
    )
    model_name: str = Field(
        default="gpt-5",
        description="Default OpenAI model to use (supports gpt-4o, gpt-5, o1, etc.)",
    )
    audio_model_name: str = Field(
        default="gpt-4o-audio-preview",
        description="Model to use for audio processing (gpt-4o-audio-preview supports native audio)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for non-reasoning models (not used with reasoning models)",
    )
    max_tokens: int = Field(
        default=128000,
        gt=0,
        description="Default max output tokens for generation",
    )
    reasoning_effort: str = Field(
        default="low",
        description="Default reasoning effort for reasoning models (minimal, low, medium, high)",
    )
    text_verbosity: str = Field(
        default="low",
        description="Default text verbosity for reasoning models (low, medium, high)",
    )
    request_timeout: int = Field(
        default=300,
        gt=0,
        description="HTTP request timeout in seconds (default: 300s for long-running MCP calls)",
    )


@lru_cache
def get_openai_settings() -> OpenAISettings:
    """Get cached OpenAI settings instance.

    Returns:
        OpenAISettings: Cached settings instance
    """
    return OpenAISettings()
