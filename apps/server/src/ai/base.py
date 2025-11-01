"""Base classes for AI provider abstraction."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, AsyncGenerator, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ToolName(str, Enum):
    """Enum for tool names used in the system."""

    WEB_SEARCH = "web_search"
    FILE_SEARCH = "file_search"
    REASONING = "reasoning"


class ToolStatus(str, Enum):
    """Enum for tool execution status."""

    RUNNING = "running"
    SEARCHING = "searching"
    COMPLETE = "complete"


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


class ChatMessage(BaseModel):
    """Chat message model for streaming chat responses.

    Represents a single message in a conversation (user or assistant).
    System messages should be passed separately via the instructions parameter.
    """

    role: str
    content: str


class ResponseStreamParams(BaseModel):
    """Parameters for OpenAI Responses API streaming requests.
    
    Mirrors the structure of ResponseCreateParams from the OpenAI SDK.
    """

    model: str
    input: list[dict]  # List of EasyInputMessageParam dicts
    temperature: float | None = None
    max_output_tokens: int | None = None
    stream: bool = True
    instructions: str | None = None
    tools: list[dict] | None = None  # List of ToolParam dicts

    model_config = {"extra": "forbid"}


class ToolCall(BaseModel):
    """Tool call information for assistant-ui integration.

    Represents a function call made by the AI with its arguments and optional result.
    """

    tool_call_id: str
    tool_name: ToolName
    args: dict[str, Any]
    result: dict[str, Any] | None = None


class ChatStreamChunk(BaseModel):
    """Chunk from streaming chat response with optional citations.

    This model represents a piece of a streaming response that may include
    both content text, reasoning summary, and citations from web search results.
    For reasoning models, reasoning_summary contains the summary of the model's
    internal reasoning process.
    Tool calls represent function calls made by the AI.
    """

    content: str = ""
    reasoning_summary: str = ""
    tool_calls: list[ToolCall] = []
    citations: list[SearchCitation] = []
    finish_reason: str | None = None


class SSEEvent(BaseModel):
    """Server-Sent Event wrapper for type-safe SSE formatting.

    Follows the W3C Server-Sent Events specification:
    https://html.spec.whatwg.org/multipage/server-sent-events.html
    """

    data: str
    event: Literal[
        "citation", "done", "error", "tool_call", "reasoning_summary"
    ] | None = None
    id: str | None = None
    retry: int | None = None

    def format(self) -> str:
        """Format as SSE protocol string.

        Returns:
            str: Properly formatted SSE event with trailing newlines
        """
        lines = []
        if self.event:
            lines.append(f"event: {self.event}")
        if self.id:
            lines.append(f"id: {self.id}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        lines.append(f"data: {self.data}")
        lines.append("")  # Empty line as event delimiter
        return "\n".join(lines) + "\n"


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
    async def stream_chat(
        self,
        messages: list[ChatMessage],
        instructions: str | None = None,
        enable_web_search: bool = False,
        vector_store_ids: list[str] | None = None,
        **kwargs,
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        """Stream chat responses with optional web search, file search, and citations.

        Args:
            messages: List of chat messages (user and assistant only, no system messages)
            instructions: Optional system prompt/instructions
            enable_web_search: Whether to enable web search capability
            vector_store_ids: Optional list of vector store IDs for file search (RAG)
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Yields:
            ChatStreamChunk: Stream chunks with content and optional citations
        """
        pass
