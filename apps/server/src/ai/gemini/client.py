"""Google Gemini API client implementation."""

import mimetypes
from pathlib import Path
from typing import TypeVar

from braintrust.wrappers.google_genai import setup_genai
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

    def __init__(
        self,
        settings: GeminiSettings,
        enable_braintrust: bool = False,
        braintrust_project_name: str | None = None,
    ) -> None:
        """Initialize Gemini client.

        Args:
            settings: Gemini settings instance with API configuration
            enable_braintrust: Whether to enable Braintrust tracing for this client instance
            braintrust_project_name: Braintrust project name (only used if enable_braintrust=True)
        """
        self.settings = settings
        self._client: genai.Client | None = None
        self.enable_braintrust = enable_braintrust
        self.braintrust_project_name = braintrust_project_name

    def _get_client(self) -> genai.Client:
        """Get or create the Gemini client.

        Automatically sets up Braintrust tracing if enabled.
        """
        if self._client is None:
            try:
                # Setup Braintrust tracing if enabled for this instance
                if self.enable_braintrust and self.braintrust_project_name:
                    logger.info(
                        f"Setting up Gemini with Braintrust tracing enabled (project: {self.braintrust_project_name})"
                    )
                    setup_genai(project_name=self.braintrust_project_name)

                self._client = genai.Client(api_key=self.settings.api_key)
                logger.info("Gemini client initialized")
            except Exception as e:
                logger.error("Failed to initialize Gemini client", error=str(e))
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

            logger.info("Uploading file", file_path=str(file_path), mime_type=mime_type)

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

            logger.info("File uploaded successfully", file_name=metadata.name)
            return metadata

        except Exception as e:
            logger.error("File upload failed", error=str(e))
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
                        logger.info("Added file to content", file_name=file_name)
                    except Exception as e:
                        logger.warning(
                            "Failed to retrieve file", file_name=file_name, error=str(e)
                        )
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
                logger.debug("Calling model API with response schema")

            # Configure File Search tool if store names provided
            tools = []
            if request.file_search_store_names:
                tools.append(
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=request.file_search_store_names
                        )
                    )
                )
                logger.info(
                    "Configuring File Search tool",
                    store_count=len(request.file_search_store_names),
                )

            if tools:
                generation_config["tools"] = tools

            logger.info("Generating content with model", model_name=model_name)

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
            logger.error("Content generation failed", error=str(e))
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
                file_search_store_names=request.file_search_store_names,
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
                    "Response text", text_preview=response.text[:500]
                )  # Log first 500 chars
                if not response.text:
                    logger.error("Response text is empty!")
                    logger.error("Response usage", usage=response.usage)
                    logger.error(
                        "Response finish_reason", finish_reason=response.finish_reason
                    )
                    raise GeminiError("Empty response from Gemini API")

                json_data = json.loads(response.text)
                return request.response_model(**json_data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.error("Failed to parse structured response", error=str(e))
                logger.error("Response text", text=response.text)
                raise GeminiError(f"Failed to parse structured response: {e}")

        except Exception as e:
            logger.error("Structured content generation failed", error=str(e))
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
            logger.error("Failed to get file", file_name=file_name, error=str(e))
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

            logger.info("File deleted successfully", file_name=file_name)
            return DeleteFileResponse(
                success=True, message=f"File {file_name} deleted successfully"
            )

        except Exception as e:
            logger.error("Failed to delete file", file_name=file_name, error=str(e))
            return DeleteFileResponse(
                success=False, message=f"Failed to delete file {file_name}: {e}"
            )

    async def create_file_search_store(self, display_name: str) -> str:
        """Create a new File Search store.

        Args:
            display_name: Display name for the File Search store

        Returns:
            str: Store name (format: fileSearchStores/xxxxx)

        Raises:
            GeminiError: If store creation fails
        """
        try:
            client = self._get_client()
            logger.info("Creating File Search store", display_name=display_name)

            store = client.file_search_stores.create(
                config={"display_name": display_name}
            )
            store_name = store.name

            logger.info("File Search store created", store_name=store_name)
            return store_name

        except Exception as e:
            logger.error("Failed to create File Search store", error=str(e))
            if isinstance(e, GeminiError):
                raise
            self._handle_api_error(e, "Create File Search store")

    async def list_file_search_stores(self) -> list[dict]:
        """List all File Search stores.

        Returns:
            list[dict]: List of store information dictionaries with 'name' and 'display_name'

        Raises:
            GeminiError: If listing stores fails
        """
        try:
            client = self._get_client()
            logger.info("Listing File Search stores")

            stores = client.file_search_stores.list()
            store_list = [
                {
                    "name": store.name,
                    "display_name": getattr(store, "display_name", None),
                }
                for store in stores
            ]

            logger.info("Listed File Search stores", count=len(store_list))
            return store_list

        except Exception as e:
            logger.error("Failed to list File Search stores", error=str(e))
            if isinstance(e, GeminiError):
                raise
            self._handle_api_error(e, "List File Search stores")

    async def upload_to_file_search_store(
        self, file_path: str, store_name: str, display_name: str | None = None
    ) -> types.UploadToFileSearchStoreOperation:
        """Upload a file directly to a File Search store.

        Args:
            file_path: Path to the file to upload
            store_name: Name of the File Search store (format: fileSearchStores/xxxxx)
            display_name: Optional display name for the file

        Returns:
            UploadToFileSearchStoreOperation object for polling completion

        Raises:
            GeminiError: If upload fails
        """
        try:
            client = self._get_client()
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                raise GeminiError(f"File not found: {file_path}")

            if display_name is None:
                display_name = file_path_obj.name

            logger.info(
                "Uploading file to File Search store",
                file_path=str(file_path),
                store_name=store_name,
                display_name=display_name,
            )

            operation = client.file_search_stores.upload_to_file_search_store(
                file=str(file_path),
                file_search_store_name=store_name,
                config={"display_name": display_name},
            )

            logger.info("File upload operation started", operation_name=operation.name)
            return operation

        except Exception as e:
            logger.error("Failed to upload file to File Search store", error=str(e))
            if isinstance(e, GeminiError):
                raise
            self._handle_api_error(e, "Upload to File Search store")

    async def get_operation(
        self, operation: types.UploadToFileSearchStoreOperation
    ) -> types.UploadToFileSearchStoreOperation:
        """Get the status of an operation.

        Args:
            operation: Operation object from upload or previous get_operation call

        Returns:
            Updated operation object with .done attribute

        Raises:
            GeminiError: If getting operation fails
        """
        try:
            client = self._get_client()
            updated_operation = client.operations.get(operation)
            return updated_operation

        except Exception as e:
            operation_name = getattr(operation, "name", str(operation))
            logger.error(
                "Failed to get operation", operation_name=operation_name, error=str(e)
            )
            if isinstance(e, GeminiError):
                raise
            self._handle_api_error(e, "Get operation")
