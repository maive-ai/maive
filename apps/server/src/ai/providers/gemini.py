"""Gemini provider implementation."""

from pathlib import Path
from typing import AsyncGenerator, TypeVar

from pydantic import BaseModel

from src.ai.base import (
    AIProvider,
    ChatMessage,
    ChatStreamChunk,
    ContentGenerationResult,
    FileMetadata,
    TranscriptionResult,
)
from src.ai.gemini import get_gemini_client
from src.ai.gemini.schemas import (
    FileUploadRequest,
    GenerateContentRequest,
    GenerateStructuredContentRequest,
)
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
        self.client = get_gemini_client(
            enable_braintrust=enable_braintrust,
            braintrust_project_name=braintrust_project_name,
        )

    async def upload_file(self, file_path: str, **kwargs) -> FileMetadata:
        """Upload a file to Gemini Files API.

        Args:
            file_path: Path to the file to upload
            **kwargs: Additional options (display_name, mime_type)

        Returns:
            FileMetadata: Metadata of the uploaded file
        """
        try:
            request = FileUploadRequest(
                file_path=file_path,
                display_name=kwargs.get("display_name"),
                mime_type=kwargs.get("mime_type"),
            )
            result = await self.client.upload_file(request)

            # Convert Gemini's FileMetadata to our generic format
            return FileMetadata(
                id=result.name,
                name=result.display_name or Path(file_path).name,
                mime_type=result.mime_type,
                size_bytes=result.size_bytes,
            )
        except Exception as e:
            logger.error("File upload failed", error=str(e))
            raise

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from Gemini Files API.

        Args:
            file_id: ID (name) of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            result = await self.client.delete_file(file_id)
            return result.success
        except Exception as e:
            logger.error("Failed to delete file", file_id=file_id, error=str(e))
            return False

    async def transcribe_audio(self, audio_path: str, **kwargs) -> TranscriptionResult:
        """Transcribe audio using Gemini.

        Note: Gemini doesn't have a dedicated transcription API like Whisper.
        This method processes the audio and extracts text via content generation.

        Args:
            audio_path: Path to the audio file
            **kwargs: Additional options (language, prompt, etc.)

        Returns:
            TranscriptionResult: Transcription result
        """
        try:
            logger.info("Transcribing audio with Gemini", audio_path=audio_path)

            # Upload audio file
            file_metadata = await self.upload_file(audio_path)

            # Use content generation to transcribe
            prompt = kwargs.get(
                "prompt",
                "Please transcribe the audio. Provide only the transcription text, no additional commentary.",
            )

            request = GenerateContentRequest(
                prompt=prompt,
                files=[file_metadata.id],
                temperature=kwargs.get("temperature", 0.0),
            )

            response = await self.client.generate_content(request)

            # Clean up uploaded file
            await self.delete_file(file_metadata.id)

            return TranscriptionResult(
                text=response.text,
                language=kwargs.get("language"),
            )
        except Exception as e:
            logger.error("Transcription failed", error=str(e))
            raise

    async def generate_content(
        self,
        prompt: str,
        file_ids: list[str] | None = None,
        response_schema: type[T] | None = None,
        vector_store_ids: list[str] | None = None,
        **kwargs,
    ) -> ContentGenerationResult | T:
        """Generate text or structured content using Gemini.

        Args:
            prompt: Text prompt
            file_ids: Optional list of file IDs (names) to include
            response_schema: Optional Pydantic model for structured output
            vector_store_ids: Optional vector store IDs (not supported by Gemini)
            **kwargs: Additional options (temperature, max_tokens, model, etc.)

        Returns:
            ContentGenerationResult for text, or instance of response_schema for structured output

        Raises:
            NotImplementedError: If vector_store_ids is provided
        """
        # Check for unsupported features
        if vector_store_ids:
            raise NotImplementedError(
                "Vector store search is not supported for Gemini provider. "
                "Please use OpenAI provider for RAG capabilities."
            )

        try:
            # Structured output
            if response_schema:
                logger.info(
                    "Generating structured content with Gemini",
                    schema=response_schema.__name__,
                )
                request = GenerateStructuredContentRequest(
                    prompt=prompt,
                    response_model=response_schema,
                    files=file_ids or [],
                    temperature=kwargs.get("temperature"),
                    model_name=kwargs.get("model"),
                )
                result = await self.client.generate_structured_content(request)
                return result

            # Plain text generation
            else:
                logger.info("Generating content with Gemini")
                request = GenerateContentRequest(
                    prompt=prompt,
                    files=file_ids or [],
                    temperature=kwargs.get("temperature"),
                    model_name=kwargs.get("model"),
                )
                response = await self.client.generate_content(request)
                return ContentGenerationResult(
                    text=response.text,
                    usage=response.usage,
                    finish_reason=response.finish_reason,
                )

        except Exception as e:
            logger.error("Content generation failed", error=str(e))
            raise

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
