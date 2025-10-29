"""Base classes for AI provider abstraction."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class FileMetadata(BaseModel):
    """Generic file metadata across providers."""

    id: str
    name: str
    mime_type: str | None = None
    size_bytes: int | None = None


class TranscriptionResult(BaseModel):
    """Result from audio transcription."""

    text: str
    language: str | None = None
    duration: float | None = None
    segments: list[dict[str, Any]] | None = None


class ContentGenerationResult(BaseModel):
    """Result from content generation."""

    text: str
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None


class SearchCitation(BaseModel):
    """Citation from web search results."""

    url: str
    title: str | None = None
    snippet: str | None = None
    accessed_at: str | None = None


class ChatStreamChunk(BaseModel):
    """Chunk from streaming chat response with optional citations.

    This model represents a piece of a streaming response that may include
    both content text and citations from web search results.
    """

    content: str = ""
    citations: list[SearchCitation] = []
    finish_reason: str | None = None


class AudioAnalysisRequest(BaseModel):
    """Request for audio analysis with context."""

    audio_path: str
    prompt: str
    context_data: dict[str, Any] | None = None
    temperature: float | None = None


class ContentAnalysisRequest(BaseModel):
    """Generic request for content analysis (audio, transcript, or both)."""

    audio_path: str | None = None
    transcript_text: str | None = None
    prompt: str
    context_data: dict[str, Any] | None = None
    temperature: float | None = None


class AIProvider(ABC):
    """Abstract base class for AI providers.

    Provides a common interface for different AI providers (OpenAI, Gemini, etc.)
    to enable easy switching between providers.
    """

    @abstractmethod
    async def upload_file(self, file_path: str, **kwargs) -> FileMetadata:
        """Upload a file to the provider's storage.

        Args:
            file_path: Path to the file to upload
            **kwargs: Provider-specific options

        Returns:
            FileMetadata: Metadata of the uploaded file
        """
        pass

    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from the provider's storage.

        Args:
            file_id: ID of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        pass

    @abstractmethod
    async def transcribe_audio(self, audio_path: str, **kwargs) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio_path: Path to the audio file
            **kwargs: Provider-specific options (language, prompt, etc.)

        Returns:
            TranscriptionResult: Transcription result with text and metadata
        """
        pass

    @abstractmethod
    async def generate_content(
        self,
        prompt: str,
        file_ids: list[str] | None = None,
        **kwargs,
    ) -> ContentGenerationResult:
        """Generate text content.

        Args:
            prompt: Text prompt for generation
            file_ids: Optional list of file IDs to include as context
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Returns:
            ContentGenerationResult: Generated content with metadata
        """
        pass

    @abstractmethod
    async def generate_structured_content(
        self,
        prompt: str,
        response_model: type[T],
        file_ids: list[str] | None = None,
        **kwargs,
    ) -> T:
        """Generate structured content using a Pydantic model.

        Args:
            prompt: Text prompt for generation
            response_model: Pydantic model class for structured output
            file_ids: Optional list of file IDs to include as context
            **kwargs: Provider-specific options

        Returns:
            Instance of response_model with generated data
        """
        pass

    @abstractmethod
    async def analyze_audio_with_context(
        self,
        request: AudioAnalysisRequest,
    ) -> ContentGenerationResult:
        """Analyze audio directly with contextual information.

        This method allows the AI to process audio directly (not just transcription)
        along with additional context like documents, forms, etc.

        Args:
            request: Audio analysis request with audio path, prompt, and context

        Returns:
            ContentGenerationResult: Analysis result
        """
        pass

    @abstractmethod
    async def analyze_audio_with_structured_output(
        self,
        request: AudioAnalysisRequest,
        response_model: type[T],
    ) -> T:
        """Analyze audio directly and return structured output.

        Combines audio analysis with structured output generation.

        Args:
            request: Audio analysis request
            response_model: Pydantic model for structured output

        Returns:
            Instance of response_model with analysis results
        """
        pass

    @abstractmethod
    async def analyze_content_with_structured_output(
        self,
        request: ContentAnalysisRequest,
        response_model: type[T],
    ) -> T:
        """Analyze content (audio, transcript, or both) and return structured output.

        More generic version that can handle audio files, transcripts, or both.

        Args:
            request: Content analysis request
            response_model: Pydantic model for structured output

        Returns:
            Instance of response_model with analysis results
        """
        pass

    @abstractmethod
    async def stream_chat_with_search(
        self,
        messages: list[dict[str, Any]],
        enable_web_search: bool = True,
        **kwargs,
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        """Stream chat responses with optional web search and citations.

        Args:
            messages: List of chat messages
            enable_web_search: Whether to enable web search capability
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Yields:
            ChatStreamChunk: Stream chunks with content and optional citations
        """
        pass
