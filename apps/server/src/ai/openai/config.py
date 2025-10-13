"""OpenAI API configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    """Settings for OpenAI API integration.

    Attributes:
        api_key: OpenAI API key for authentication
        model_name: Default model to use (e.g., 'gpt-4o', 'gpt-4o-audio-preview', 'o1')
        audio_model_name: Model to use for audio processing
        temperature: Default temperature for generation (0.0-2.0)
        max_tokens: Default max tokens for generation
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
        default="gpt-4o",
        description="Default OpenAI model to use",
    )
    audio_model_name: str = Field(
        default="gpt-4o-audio-preview",
        description="Model to use for audio processing (gpt-4o-audio-preview supports native audio)",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for generation",
    )
    max_tokens: int = Field(
        default=4096,
        gt=0,
        description="Default max tokens for generation",
    )


@lru_cache
def get_openai_settings() -> OpenAISettings:
    """Get cached OpenAI settings instance.

    Returns:
        OpenAISettings: Cached settings instance
    """
    return OpenAISettings()
