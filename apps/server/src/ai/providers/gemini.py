"""Gemini provider implementation."""

import mimetypes
from pathlib import Path
from typing import AsyncGenerator, TypeVar

from braintrust.wrappers.google_genai import setup_genai
from google import genai
from google.genai.types import (
    FileSearch,
    GenerateContentConfig,
    GenerateContentResponse,
    Tool,
)
from pydantic import BaseModel

from src.ai.base import (
    AIProvider,
    ChatMessage,
    ChatStreamChunk,
    ContentGenerationResult,
    FileMetadata,
)
from src.ai.gemini.config import get_gemini_settings
from src.ai.gemini.exceptions import GeminiError
from src.utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(AIProvider):
    """Gemini provider implementation.

    Uses Google's Gemini API for audio processing, transcription, and content generation.
    Gemini supports native multimodal input including audio files.
    """

    def __init__(
        self,
        enable_braintrust: bool = False,
        braintrust_project_name: str | None = None,
    ):
        """Initialize Gemini provider.

        Args:
            enable_braintrust: Whether to enable Braintrust tracing for this provider instance
            braintrust_project_name: Braintrust project name (only used if enable_braintrust=True)
        """
        self._client: genai.Client | None = None
        self.enable_braintrust = enable_braintrust
        self.braintrust_project_name = braintrust_project_name
        self.settings = get_gemini_settings()

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

    async def upload_file(self, file_path: str, **kwargs) -> FileMetadata:
        """Upload a file to Gemini Files API.

        Args:
            file_path: Path to the file to upload
            **kwargs: Additional options (display_name, mime_type)

        Returns:
            FileMetadata: Metadata of the uploaded file
        """
        try:
            client = self._get_client()
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                raise GeminiError(f"File not found: {file_path}")

            # Auto-detect MIME type if not provided
            mime_type = kwargs.get("mime_type")
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(str(file_path_obj))
                if not mime_type:
                    mime_type = "application/octet-stream"

            logger.info(
                "Uploading file", file_path=str(file_path_obj), mime_type=mime_type
            )

            # Upload file using the google-genai library
            uploaded_file = client.files.upload(file=str(file_path_obj))

            # Convert to our metadata format
            metadata = FileMetadata(
                id=uploaded_file.name,
                name=getattr(uploaded_file, "display_name", None) or file_path_obj.name,
                mime_type=getattr(uploaded_file, "mime_type", None),
                size_bytes=getattr(uploaded_file, "size_bytes", None),
            )

            logger.info("File uploaded successfully", file_name=metadata.name)
            return metadata

        except Exception as e:
            logger.error("File upload failed", error=str(e))
            if isinstance(e, GeminiError):
                raise
            raise GeminiError(f"File upload failed: {e}")

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Gemini Files API.

        Args:
            file_id: ID (name) of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            client = self._get_client()
            client.files.delete(name=file_id)
            logger.info("File deleted successfully", file_id=file_id)
            return True
        except Exception as e:
            logger.error("Failed to delete file", file_id=file_id, error=str(e))
            return False

    async def generate_content(
        self,
        prompt: str,
        file_ids: list[str] | None = None,
        file_attachments: list[tuple[str, str, bool]] | None = None,
        file_search_store_names: list[str] | None = None,
        **kwargs,
    ) -> ContentGenerationResult:
        """Generate text content using Gemini.

        Args:
            prompt: Text prompt
            file_ids: Optional list of file IDs (names) to include
            file_attachments: Optional list of (file_id, filename, is_image) tuples (not supported)
            file_search_store_names: Optional list of File Search store names to search
            **kwargs: Additional options (temperature, max_tokens, model, etc.)

        Returns:
            ContentGenerationResult: Generated content

        Raises:
            NotImplementedError: If file_attachments is provided
        """
        # Check for unsupported features
        if file_attachments:
            raise NotImplementedError(
                "File attachments are not supported for Gemini provider. "
                "Use file_ids parameter instead."
            )

        try:
            client = self._get_client()
            logger.info("Generating content with Gemini")

            # Prepare content list
            contents = [prompt]

            # Add files if provided
            if file_ids:
                for file_name in file_ids:
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
            model_name = kwargs.get("model") or self.settings.model_name
            temperature = kwargs.get("temperature") or self.settings.temperature

            generation_config = {}
            if temperature is not None:
                generation_config["temperature"] = temperature

            # Configure File Search tool if store names provided
            tools = []
            if file_search_store_names:
                tools.append(
                    Tool(
                        file_search=FileSearch(
                            file_search_store_names=file_search_store_names
                        )
                    )
                )
                logger.info(
                    "Configuring File Search tool",
                    store_count=len(file_search_store_names),
                )

            if tools:
                generation_config["tools"] = tools

            logger.info("Generating content with model", model_name=model_name)

            # Generate content
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=GenerateContentConfig(**generation_config)
                if generation_config
                else None,
            )

            return ContentGenerationResult(
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
            raise GeminiError(f"Content generation failed: {e}")

    async def generate_structured_content(
        self,
        prompt: str,
        response_schema: type[T],
        file_ids: list[str] | None = None,
        vector_store_ids: list[str] | None = None,
        file_search_store_names: list[str] | None = None,
        **kwargs,
    ) -> T:
        """Generate structured content using a Pydantic model.

        Args:
            prompt: Text prompt
            response_schema: Pydantic model for structured output
            file_ids: Optional list of file names
            vector_store_ids: Optional vector store IDs (deprecated, use file_search_store_names)
            file_search_store_names: Optional list of File Search store names to search
            **kwargs: Additional options

        Returns:
            Instance of response_schema with generated data

        Raises:
            NotImplementedError: If vector_store_ids is provided (use file_search_store_names instead)
        """
        # Check for deprecated parameter
        if vector_store_ids:
            raise NotImplementedError(
                "Vector store search is not supported for Gemini provider. "
                "Please use file_search_store_names parameter for Gemini File Search."
            )

        try:
            client = self._get_client()

            # Prepare content list
            contents = [prompt]

            # Add files if provided
            if file_ids:
                for file_name in file_ids:
                    file_obj = client.files.get(name=file_name)
                    contents.append(file_obj)
                    logger.info("Added file to content", file_name=file_name)

            # Prepare generation config
            model_name = kwargs.get("model") or self.settings.model_name
            temperature = kwargs.get("temperature") or self.settings.temperature
            tools = None
            if file_search_store_names:
                tools = [
                    Tool(file_search=FileSearch(file_search_store_names=[store_name]))
                    for store_name in file_search_store_names
                ]

            generation_config = GenerateContentConfig(
                temperature=temperature,
                # response_schema=response_schema,
                response_schema=response_schema,
                tools=tools,
            )

            logger.info("Generating content with model", model_name=model_name)

            # Generate content
            response: GenerateContentResponse = client.models.generate_content(
                model=model_name, contents=contents, config=generation_config
            )
            # logger.info("First pass response", response=response)
            # if not response.text:
            #     logger.error("Response text is empty", response=response)
            #     raise ValueError("Response text is empty")
            # logger.info("First pass response text", text=response.text)

            structured_config = GenerateContentConfig(
                temperature=temperature,
                response_json_schema=response_schema.model_json_schema(),
                response_mime_type="application/json",
            )
            structured_response: GenerateContentResponse = (
                client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=[
                        "Please parse the following text into a JSON object: ",
                        response.text,
                    ],
                    config=structured_config,
                )
            )
            if structured_response.parsed:
                # logger.info("Have parsed response", parsed=structured_response.parsed)
                return response_schema.model_validate(structured_response.parsed)

            if not structured_response.text:
                logger.error(
                    "Structured response text is empty", response=structured_response
                )
                raise ValueError("Structured response text is empty")

            logger.info("Second pass response text", text=structured_response.parsed)
            return response_schema(**structured_response.parsed)

        except Exception as e:
            logger.error("Content generation failed", error=str(e))
            raise

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
            raise GeminiError(f"Create File Search store failed: {e}")

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
            raise GeminiError(f"List File Search stores failed: {e}")

    async def upload_to_file_search_store(
        self, file_path: str, store_name: str, display_name: str | None = None
    ):
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
            raise GeminiError(f"Upload to File Search store failed: {e}")

    async def get_operation(self, operation):
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
            raise GeminiError(f"Get operation failed: {e}")

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        instructions: str | None = None,
        enable_web_search: bool = False,
        vector_store_ids: list[str] | None = None,
        **kwargs,
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        """Stream chat responses with optional web search and citations.

        Note: Gemini does not currently support web search or vector stores
        in the same way as OpenAI. This is a placeholder implementation.

        Args:
            messages: List of chat messages (user and assistant only, no system messages)
            instructions: Optional system prompt/instructions
            enable_web_search: Whether to enable web search capability (not supported)
            vector_store_ids: Vector store IDs for file search (not supported)
            **kwargs: Provider-specific options

        Yields:
            ChatStreamChunk: Stream chunks with content
        """
        if enable_web_search:
            raise NotImplementedError(
                "Web search is not yet implemented for Gemini provider. "
                "Please use OpenAI provider for web search capabilities."
            )
        # TODO: Implement basic streaming chat for Gemini
        raise NotImplementedError("Stream chat not yet implemented for Gemini provider")
        yield  # Make this a generator for type compatibility
