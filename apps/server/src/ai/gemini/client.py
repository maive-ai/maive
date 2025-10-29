"""Google Gemini API client implementation."""

import mimetypes
from pathlib import Path
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from src.ai.gemini.config import GeminiSettings
from src.ai.gemini.exceptions import GeminiError
from src.ai.gemini.schemas import (
    DeleteFileResponse,
    FileMetadata,
    FileUploadRequest,
    GenerateContentRequest,
    GenerateContentResponse,
    GenerateStructuredContentRequest,
)
from src.utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    """Async client for Google Gemini API.

    Provides methods to upload files, generate content with optional file inputs,
    and generate structured output. Handles authentication and error handling.
    """

    def __init__(self, settings: GeminiSettings) -> None:
        """Initialize Gemini client.

        Args:
            settings: Gemini settings instance with API configuration
        """
        self.settings = settings
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """Get or create the Gemini client."""
        if self._client is None:
            try:
                self._client = genai.Client(api_key=self.settings.api_key)
                logger.info("Gemini client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                raise GeminiError(f"Failed to authenticate: {e}")
        return self._client

    def _handle_api_error(self, error: Exception, operation: str) -> None:
        """Handle API errors and convert to appropriate exceptions."""
        raise GeminiError(f"{operation} failed: {error}")

    async def upload_file(self, request: FileUploadRequest) -> FileMetadata:
        """Upload a file to Gemini Files API.

        Args:
            request: File upload request with file path and optional metadata

        Returns:
            FileMetadata: Metadata of the uploaded file

        Raises:
            GeminiFileUploadError: If file upload fails
            GeminiAPIError: For other API errors
        """
        try:
            client = self._get_client()
            file_path = Path(request.file_path)

            if not file_path.exists():
                raise GeminiError(f"File not found: {request.file_path}")

            # Auto-detect MIME type if not provided
            mime_type = request.mime_type
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if not mime_type:
                    mime_type = "application/octet-stream"

            logger.info(f"Uploading file: {file_path} with MIME type: {mime_type}")

            # Upload file using the google-genai library
            uploaded_file = client.files.upload(file=str(file_path))

            # Convert to our metadata format
            metadata = FileMetadata(
                name=uploaded_file.name,
                display_name=getattr(uploaded_file, "display_name", None)
                or file_path.name,
                mime_type=getattr(uploaded_file, "mime_type", None),
                size_bytes=getattr(uploaded_file, "size_bytes", None),
                sha256_hash=getattr(uploaded_file, "sha256_hash", None),
                uri=getattr(uploaded_file, "uri", None),
                state=getattr(uploaded_file, "state", None),
            )

            logger.info(f"File uploaded successfully: {metadata.name}")
            return metadata

        except Exception as e:
            logger.error(f"File upload failed: {e}")
            if isinstance(e, GeminiError):
                raise
            self._handle_api_error(e, "File upload")

    async def generate_content(
        self, request: GenerateContentRequest
    ) -> GenerateContentResponse:
        """Generate content using Gemini API.

        Args:
            request: Content generation request with prompt and optional files

        Returns:
            GenerateContentResponse: Generated content response

        Raises:
            GeminiContentGenerationError: If content generation fails
            GeminiAPIError: For other API errors
        """
        try:
            client = self._get_client()

            # Prepare content list
            contents = [request.prompt]

            # Add files if provided
            if request.files:
                for file_name in request.files:
                    try:
                        file_obj = client.files.get(name=file_name)
                        contents.append(file_obj)
                        logger.info(f"Added file to content: {file_name}")
                    except Exception as e:
                        logger.warning(f"Failed to retrieve file {file_name}: {e}")
                        # Continue without this file rather than failing completely

            # Prepare generation config
            model_name = request.model_name or self.settings.model_name
            temperature = request.temperature or self.settings.temperature

            generation_config = {}
            if temperature is not None:
                generation_config["temperature"] = temperature
            if request.response_schema:
                generation_config["response_schema"] = request.response_schema
                generation_config["response_mime_type"] = "application/json"
                logger.debug(f"Response schema: {request.response_schema}")

            logger.info(f"Generating content with model: {model_name}")

            # Generate content
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(**generation_config)
                if generation_config
                else None,
            )

            return GenerateContentResponse(
                text=response.text,
                usage=response.usage_metadata.__dict__
                if hasattr(response, "usage_metadata")
                else None,
                finish_reason=getattr(response, "finish_reason", None),
            )

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            if isinstance(e, GeminiError):
                raise
            self._handle_api_error(e, "Content generation")

    async def generate_structured_content(
        self, request: GenerateStructuredContentRequest
    ) -> T:
        """Generate structured content using a Pydantic model.

        Args:
            request: Structured content generation request

        Returns:
            Instance of the specified Pydantic model with generated data

        Raises:
            GeminiContentGenerationError: If content generation fails
            GeminiAPIError: For other API errors
        """
        try:
            # Convert Pydantic model to JSON schema
            schema = request.response_model.model_json_schema()

            # Create a regular content request with the schema
            content_request = GenerateContentRequest(
                prompt=request.prompt,
                files=request.files,
                temperature=request.temperature,
                model_name=request.model_name,
                thinking_budget=request.thinking_budget,
                response_schema=schema,
            )

            response = await self.generate_content(content_request)

            # Parse the response text as JSON and validate with the model
            import json

            try:
                logger.debug(
                    f"Response text: {response.text[:500]}"
                )  # Log first 500 chars
                if not response.text:
                    logger.error("Response text is empty!")
                    logger.error(f"Response usage: {response.usage}")
                    logger.error(f"Response finish_reason: {response.finish_reason}")
                    raise GeminiError("Empty response from Gemini API")

                json_data = json.loads(response.text)
                return request.response_model(**json_data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse structured response: {e}")
                logger.error(f"Response text: {response.text}")
                raise GeminiError(f"Failed to parse structured response: {e}")

        except Exception as e:
            logger.error(f"Structured content generation failed: {e}")
            if isinstance(e, GeminiError):
                raise
            self._handle_api_error(e, "Structured content generation")

    async def get_file(self, file_name: str) -> FileMetadata:
        """Get metadata for a specific file.

        Args:
            file_name: Name/ID of the file to retrieve

        Returns:
            FileMetadata: Metadata of the file

        Raises:
            GeminiAPIError: If getting file metadata fails
        """
        try:
            client = self._get_client()
            file = client.files.get(name=file_name)

            return FileMetadata(
                name=file.name,
                display_name=getattr(file, "display_name", None),
                mime_type=getattr(file, "mime_type", None),
                size_bytes=getattr(file, "size_bytes", None),
                sha256_hash=getattr(file, "sha256_hash", None),
                uri=getattr(file, "uri", None),
                state=getattr(file, "state", None),
            )

        except Exception as e:
            logger.error(f"Failed to get file {file_name}: {e}")
            self._handle_api_error(e, "Get file")

    async def delete_file(self, file_name: str) -> DeleteFileResponse:
        """Delete an uploaded file.

        Args:
            file_name: Name/ID of the file to delete

        Returns:
            DeleteFileResponse: Result of the deletion

        Raises:
            GeminiAPIError: If deleting file fails
        """
        try:
            client = self._get_client()
            client.files.delete(name=file_name)

            logger.info(f"File deleted successfully: {file_name}")
            return DeleteFileResponse(
                success=True, message=f"File {file_name} deleted successfully"
            )

        except Exception as e:
            logger.error(f"Failed to delete file {file_name}: {e}")
            return DeleteFileResponse(
                success=False, message=f"Failed to delete file {file_name}: {e}"
            )
