"""Gemini AI integration package."""

from src.ai.gemini.client import GeminiClient
from src.ai.gemini.config import get_gemini_settings


def get_gemini_client(
    enable_braintrust: bool = False,
    braintrust_project_name: str | None = None,
) -> GeminiClient:
    """
    Get a configured Gemini client instance.

    Args:
        enable_braintrust: Whether to enable Braintrust tracing for this client instance
        braintrust_project_name: Braintrust project name (only used if enable_braintrust=True)

    Returns:
        GeminiClient: The configured Gemini client
    """
    settings = get_gemini_settings()
    return GeminiClient(
        settings=settings,
        enable_braintrust=enable_braintrust,
        braintrust_project_name=braintrust_project_name,
    )


__all__ = [
    "get_gemini_client",
]
