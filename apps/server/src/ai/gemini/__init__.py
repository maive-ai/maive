"""Gemini AI integration package."""

from src.ai.providers.gemini import GeminiProvider


def get_gemini_client(
    enable_braintrust: bool = False,
    braintrust_project_name: str | None = None,
) -> GeminiProvider:
    """
    Get a configured Gemini provider instance.

    Args:
        enable_braintrust: Whether to enable Braintrust tracing for this provider instance
        braintrust_project_name: Braintrust project name (only used if enable_braintrust=True)

    Returns:
        GeminiProvider: The configured Gemini provider
    """
    return GeminiProvider(
        enable_braintrust=enable_braintrust,
        braintrust_project_name=braintrust_project_name,
    )


__all__ = [
    "get_gemini_client",
]
