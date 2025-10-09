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
) -> AIProvider:
    """Create an AI provider instance.

    Args:
        provider_type: Type of provider to create. If None, uses AI_PROVIDER env var
                      or defaults to OpenAI.

    Returns:
        AIProvider: Instance of the specified provider

    Raises:
        ValueError: If provider type is not supported
    """
    if provider_type is None:
        provider_type = os.getenv("AI_PROVIDER", AIProviderType.OPENAI.value)

    if isinstance(provider_type, str):
        provider_type = AIProviderType(provider_type.lower())

    logger.info(f"Creating AI provider: {provider_type.value}")

    if provider_type == AIProviderType.OPENAI:
        from src.ai.providers.openai import OpenAIProvider

        return OpenAIProvider()
    elif provider_type == AIProviderType.GEMINI:
        from src.ai.providers.gemini import GeminiProvider

        return GeminiProvider()
    else:
        raise ValueError(f"Unsupported AI provider: {provider_type}")


# Global provider instance
_ai_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    """Get the global AI provider instance.

    Returns:
        AIProvider: The global provider instance
    """
    global _ai_provider
    if _ai_provider is None:
        _ai_provider = create_ai_provider()
    return _ai_provider


def set_ai_provider(provider: AIProvider) -> None:
    """Set the global AI provider instance.

    Useful for testing or manually overriding the provider.

    Args:
        provider: The provider instance to set
    """
    global _ai_provider
    _ai_provider = provider
