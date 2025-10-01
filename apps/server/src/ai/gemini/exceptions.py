"""Custom exceptions for the Gemini integration package."""


class GeminiError(Exception):
    """Base exception for all Gemini-related errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code