"""Gemini AI integration package."""

from src.ai.gemini.client import GeminiClient
from src.ai.gemini.config import get_gemini_settings


def get_gemini_client() -> GeminiClient:
    """
    Get a configured Gemini client instance.

    Returns:
        GeminiClient: The configured Gemini client
    """
    settings = get_gemini_settings()
    return GeminiClient(settings)


__all__ = [
    "get_gemini_client",
]
