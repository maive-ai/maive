"""Custom exceptions for the Gemini integration package."""


class GeminiError(Exception):
    """Base exception for all Gemini-related errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GeminiAPIError(GeminiError):
    """Raised when Gemini API returns an error."""

    pass


class GeminiAuthenticationError(GeminiError):
    """Raised when authentication with Gemini API fails."""

    pass


class GeminiFileUploadError(GeminiError):
    """Raised when file upload to Gemini API fails."""

    pass


class GeminiRateLimitError(GeminiError):
    """Raised when Gemini API rate limit is exceeded."""

    pass


class GeminiServerError(GeminiError):
    """Raised when Gemini API returns a server error."""

    pass


class GeminiBadRequestError(GeminiError):
    """Raised when a bad request is made to Gemini API."""

    pass


class GeminiContentGenerationError(GeminiError):
    """Raised when content generation fails."""

    pass