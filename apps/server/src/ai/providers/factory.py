"""Factory for creating AI provider instances."""

import os
from enum import Enum

from src.ai.base import AIProvider
from src.utils.logger import logger


class AIProviderType(str, Enum):
    """Available AI provider types."""

    OPENAI = "openai"
    GEMINI = "gemini"


def create_ai_provider(
    provider_type: AIProviderType | str | None = None,
    enable_braintrust: bool = False,
    braintrust_project_name: str | None = None,
) -> AIProvider:
    """Create an AI provider instance.

    Args:
        provider_type: Type of provider to create. If None, uses AI_PROVIDER env var
                      or defaults to OpenAI.
        enable_braintrust: Whether to enable Braintrust tracing for this provider instance
        braintrust_project_name: Braintrust project name (only used if enable_braintrust=True)

    Returns:
        AIProvider: Instance of the specified provider

    Raises:
        ValueError: If provider type is not supported
    """
    if provider_type is None:
        provider_type = os.getenv("AI_PROVIDER", AIProviderType.GEMINI.value)

    if isinstance(provider_type, str):
        provider_type = AIProviderType(provider_type.lower())

    logger.info(f"Creating AI provider: {provider_type.value}")

    if provider_type == AIProviderType.OPENAI:
        from src.ai.providers.openai import OpenAIProvider

        return OpenAIProvider(
            enable_braintrust=enable_braintrust,
            braintrust_project_name=braintrust_project_name,
        )
    elif provider_type == AIProviderType.GEMINI:
        from src.ai.providers.gemini import GeminiProvider

        return GeminiProvider(
            enable_braintrust=enable_braintrust,
            braintrust_project_name=braintrust_project_name,
        )
    else:
        raise ValueError(f"Unsupported AI provider: {provider_type}")


# Global provider instance (deprecated - use create_ai_provider with explicit config)
_ai_provider: AIProvider | None = None


def get_ai_provider(
    enable_braintrust: bool = False,
    braintrust_project_name: str | None = None,
) -> AIProvider:
    """Get an AI provider instance.

    Note: This creates a new provider instance each time with the given config.
    For workflows that need tracing, pass enable_braintrust=True and project_name.

    Args:
        enable_braintrust: Whether to enable Braintrust tracing for this provider instance
        braintrust_project_name: Braintrust project name (only used if enable_braintrust=True)

    Returns:
        AIProvider: Provider instance
    """
    return create_ai_provider(
        enable_braintrust=enable_braintrust,
        braintrust_project_name=braintrust_project_name,
    )


def set_ai_provider(provider: AIProvider) -> None:
    """Set the global AI provider instance.

    Useful for testing or manually overriding the provider.

    Args:
        provider: The provider instance to set
    """
    global _ai_provider
    _ai_provider = provider
