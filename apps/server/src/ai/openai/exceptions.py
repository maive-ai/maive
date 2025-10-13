"""OpenAI API exceptions."""


class OpenAIError(Exception):
    """Base exception for OpenAI API errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        """Initialize OpenAI error.

        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.original_error = original_error


class OpenAIAuthenticationError(OpenAIError):
    """Exception raised for authentication errors."""

    pass


class OpenAIFileUploadError(OpenAIError):
    """Exception raised for file upload errors."""

    pass


class OpenAIContentGenerationError(OpenAIError):
    """Exception raised for content generation errors."""

    pass


class OpenAIAgentError(OpenAIError):
    """Exception raised for agent execution errors."""

    pass
