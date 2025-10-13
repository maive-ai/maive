"""Base classes for AI provider abstraction."""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

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


class AudioAnalysisRequest(BaseModel):
    """Request for audio analysis with context."""

    audio_path: str
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
