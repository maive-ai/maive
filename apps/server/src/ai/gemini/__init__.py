"""Google Gemini integration package."""

from src.ai.gemini.client import GeminiClient
from src.ai.gemini.config import GeminiSettings, get_gemini_settings
from src.ai.gemini.exceptions import (
    GeminiAPIError,
    GeminiAuthenticationError,
    GeminiBadRequestError,
    GeminiContentGenerationError,
    GeminiError,
    GeminiFileUploadError,
    GeminiRateLimitError,
    GeminiServerError,
)
from src.ai.gemini.schemas import (
    DeleteFileResponse,
    FileMetadata,
    FileUploadRequest,
    GenerateContentRequest,
    GenerateContentResponse,
    GenerateStructuredContentRequest,
)

__all__ = [
    "GeminiClient",
    "GeminiSettings",
    "get_gemini_settings",
    "get_gemini_client",
    # Exceptions
    "GeminiError",
    "GeminiAPIError",
    "GeminiAuthenticationError",
    "GeminiBadRequestError",
    "GeminiContentGenerationError",
    "GeminiFileUploadError",
    "GeminiRateLimitError",
    "GeminiServerError",
    # Schemas
    "FileUploadRequest",
    "FileMetadata",
    "GenerateContentRequest",
    "GenerateContentResponse",
    "GenerateStructuredContentRequest",
    "DeleteFileResponse",
]


def get_gemini_client() -> GeminiClient:
    """
    Factory function to create a GeminiClient with default settings.

    Returns:
        GeminiClient: Configured Gemini client instance
    """
    settings = get_gemini_settings()
    return GeminiClient(settings)