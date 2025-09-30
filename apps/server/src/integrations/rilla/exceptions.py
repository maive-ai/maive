"""Custom exception classes for Rilla API client."""

from typing import Any


class RillaAPIError(Exception):
    """Base exception for all Rilla API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
        request_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize RillaAPIError.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_data: Response data from the API
            request_data: Request data that caused the error (sensitive data should be excluded)
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        self.request_data = request_data

    def __str__(self) -> str:
        """Return string representation of the error."""
        if self.status_code:
            return f"Rilla API Error ({self.status_code}): {self.message}"
        return f"Rilla API Error: {self.message}"


class RillaAuthenticationError(RillaAPIError):
    """Exception raised for authentication errors (401)."""

    def __init__(
        self,
        message: str = "Invalid API key or authentication failed",
        response_data: dict[str, Any] | None = None,
        request_data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            response_data=response_data,
            request_data=request_data,
        )


class RillaBadRequestError(RillaAPIError):
    """Exception raised for bad request errors (400)."""

    def __init__(
        self,
        message: str = "Bad request - malformed or missing required parameters",
        response_data: dict[str, Any] | None = None,
        request_data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            response_data=response_data,
            request_data=request_data,
        )


class RillaRateLimitError(RillaAPIError):
    """Exception raised for rate limit errors (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        response_data: dict[str, Any] | None = None,
        request_data: dict[str, Any] | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=429,
            response_data=response_data,
            request_data=request_data,
        )
        self.retry_after = retry_after


class RillaServerError(RillaAPIError):
    """Exception raised for server errors (5xx)."""

    def __init__(
        self,
        message: str = "Internal server error occurred",
        status_code: int = 500,
        response_data: dict[str, Any] | None = None,
        request_data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status_code,
            response_data=response_data,
            request_data=request_data,
        )


class RillaTimeoutError(RillaAPIError):
    """Exception raised for request timeout errors."""

    def __init__(
        self,
        message: str = "Request timed out",
        timeout_duration: float | None = None,
    ) -> None:
        super().__init__(message=message)
        self.timeout_duration = timeout_duration


class RillaConnectionError(RillaAPIError):
    """Exception raised for connection errors."""

    def __init__(
        self,
        message: str = "Failed to connect to Rilla API",
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message=message)
        self.original_error = original_error
