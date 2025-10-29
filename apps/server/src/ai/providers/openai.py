"""OpenAI provider implementation."""

import base64
import json
from pathlib import Path
from typing import Any, AsyncGenerator, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.ai.base import (
    AIProvider,
    AudioAnalysisRequest,
    ChatStreamChunk,
    ContentAnalysisRequest,
    ContentGenerationResult,
    FileMetadata,
    SearchCitation,
    TranscriptionResult,
)
from src.ai.openai.config import get_openai_settings
from src.ai.openai.exceptions import (
    OpenAIAuthenticationError,
    OpenAIContentGenerationError,
    OpenAIError,
    OpenAIFileUploadError,
)
from src.utils.logger import logger

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(AIProvider):
    """OpenAI provider implementation.

    Uses OpenAI's API for audio processing, transcription, and content generation.
    Supports native audio input for models like gpt-4o-audio-preview.
    """

    def __init__(self):
        """Initialize OpenAI provider."""
        self.settings = get_openai_settings()
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                self._client = AsyncOpenAI(api_key=self.settings.api_key)
                logger.info("OpenAI client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise OpenAIAuthenticationError(
                    f"Failed to authenticate with OpenAI: {e}", e
                )
        return self._client

    async def upload_file(self, file_path: str, **kwargs) -> FileMetadata:
        """Upload a file to OpenAI.

        Args:
            file_path: Path to the file to upload
            **kwargs: Additional options (purpose, etc.)

        Returns:
            FileMetadata: Metadata of the uploaded file
        """
        try:
            client = self._get_client()
            path = Path(file_path)

            if not path.exists():
                raise OpenAIFileUploadError(f"File not found: {file_path}")

            purpose = kwargs.get("purpose", "assistants")
            logger.info(f"Uploading file: {path} with purpose: {purpose}")

            with open(path, "rb") as f:
                uploaded_file = await client.files.create(file=f, purpose=purpose)

            metadata = FileMetadata(
                id=uploaded_file.id,
                name=uploaded_file.filename,
                mime_type=None,  # OpenAI doesn't return mime_type
                size_bytes=uploaded_file.bytes,
            )

            logger.info(f"File uploaded successfully: {metadata.id}")
            return metadata

        except OpenAIFileUploadError:
            raise
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            raise OpenAIFileUploadError(f"Failed to upload file: {e}", e)

    async def delete_file(self, file_id: str) -> bool:
        """Delete a file from OpenAI.

        Args:
            file_id: ID of the file to delete

        Returns:
            bool: True if deletion was successful
        """
        try:
            client = self._get_client()
            await client.files.delete(file_id)
            logger.info(f"File deleted successfully: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    async def transcribe_audio(self, audio_path: str, **kwargs) -> TranscriptionResult:
        """Transcribe audio using Whisper.

        Args:
            audio_path: Path to the audio file
            **kwargs: Additional options (model, language, prompt, etc.)

        Returns:
            TranscriptionResult: Transcription result
        """
        try:
            client = self._get_client()
            path = Path(audio_path)

            if not path.exists():
                raise OpenAIContentGenerationError(
                    f"Audio file not found: {audio_path}"
                )

            logger.info(f"Transcribing audio: {path}")

            model = kwargs.get("model", "whisper-1")
            language = kwargs.get("language")
            prompt = kwargs.get("prompt")
            response_format = kwargs.get("response_format", "verbose_json")
            temperature = kwargs.get("temperature", 0.0)

            with open(path, "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    language=language,
                    prompt=prompt,
                    response_format=response_format,
                    temperature=temperature,
                )

            # Handle different response formats
            if response_format == "verbose_json":
                result = TranscriptionResult(
                    text=transcript.text,
                    language=getattr(transcript, "language", None),
                    duration=getattr(transcript, "duration", None),
                    segments=getattr(transcript, "segments", None),
                )
            elif response_format == "json":
                result = TranscriptionResult(text=transcript.text)
            else:
                # For text, srt, vtt formats
                result = TranscriptionResult(text=str(transcript))

            logger.info(f"Transcription complete: {len(result.text)} characters")
            return result

        except OpenAIContentGenerationError:
            raise
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise OpenAIContentGenerationError(f"Failed to transcribe audio: {e}", e)

    async def generate_content(
        self,
        prompt: str,
        file_ids: list[str] | None = None,
        **kwargs,
    ) -> ContentGenerationResult:
        """Generate text content.

        Args:
            prompt: Text prompt
            file_ids: Optional file IDs (not used for standard chat)
            **kwargs: Additional options (temperature, max_tokens, model, etc.)

        Returns:
            ContentGenerationResult: Generated content
        """
        try:
            client = self._get_client()

            model = kwargs.get("model", self.settings.model_name)
            temperature = kwargs.get("temperature", self.settings.temperature)
            max_tokens = kwargs.get("max_tokens", self.settings.max_tokens)

            logger.info(f"Generating content with model: {model}")

            messages = [{"role": "user", "content": prompt}]

            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            message = completion.choices[0].message
            usage = (
                {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }
                if completion.usage
                else None
            )

            result = ContentGenerationResult(
                text=message.content or "",
                usage=usage,
                finish_reason=completion.choices[0].finish_reason,
            )

            logger.info(f"Content generation complete: {result.finish_reason}")
            return result

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise OpenAIContentGenerationError(f"Failed to generate content: {e}", e)

    async def generate_structured_content(
        self,
        prompt: str,
        response_model: type[T],
        file_ids: list[str] | None = None,
        **kwargs,
    ) -> T:
        """Generate structured content using a Pydantic model.

        Args:
            prompt: Text prompt
            response_model: Pydantic model for structured output
            file_ids: Optional file IDs
            **kwargs: Additional options

        Returns:
            Instance of response_model with generated data
        """
        try:
            client = self._get_client()

            model = kwargs.get("model", self.settings.model_name)
            temperature = kwargs.get("temperature", self.settings.temperature)
            max_tokens = kwargs.get("max_tokens", self.settings.max_tokens)

            logger.info(f"Generating structured content with model: {model}")

            # Convert Pydantic model to JSON schema
            schema = response_model.model_json_schema()

            messages = [{"role": "user", "content": prompt}]

            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_model.__name__,
                        "schema": schema,
                        "strict": True,
                    },
                },
            )

            message = completion.choices[0].message
            content = message.content or "{}"

            logger.debug(f"Structured response: {content[:500]}")

            # Parse and validate
            data = json.loads(content)
            return response_model(**data)

        except Exception as e:
            logger.error(f"Structured content generation failed: {e}")
            raise OpenAIContentGenerationError(
                f"Failed to generate structured content: {e}", e
            )

    async def analyze_audio_with_context(
        self,
        request: AudioAnalysisRequest,
    ) -> ContentGenerationResult:
        """Analyze audio directly with contextual information.

        Uses OpenAI's audio-capable models to process audio directly.

        Args:
            request: Audio analysis request

        Returns:
            ContentGenerationResult: Analysis result
        """
        try:
            client = self._get_client()
            path = Path(request.audio_path)

            if not path.exists():
                raise OpenAIError(f"Audio file not found: {request.audio_path}")

            logger.info(f"Analyzing audio with context: {path}")

            # Read and encode audio as base64
            with open(path, "rb") as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode("utf-8")

            # Determine audio format from extension
            audio_format = path.suffix.lstrip(".")  # e.g., 'mp3', 'wav'

            # Build message with audio input
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_data,
                                "format": audio_format,
                            },
                        },
                        {"type": "text", "text": request.prompt},
                    ],
                }
            ]

            # If context data is provided, include it in the prompt
            if request.context_data:
                context_text = (
                    f"\n\nContext Data:\n{json.dumps(request.context_data, indent=2)}"
                )
                messages[0]["content"].append({"type": "text", "text": context_text})

            model = self.settings.audio_model_name
            temperature = request.temperature or self.settings.temperature

            logger.info(f"Using audio model: {model}")

            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=self.settings.max_tokens,
            )

            message = completion.choices[0].message
            usage = (
                {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }
                if completion.usage
                else None
            )

            result = ContentGenerationResult(
                text=message.content or "",
                usage=usage,
                finish_reason=completion.choices[0].finish_reason,
            )

            logger.info(f"Audio analysis complete: {result.finish_reason}")
            return result

        except Exception as e:
            logger.error(f"Audio analysis failed: {e}")
            raise OpenAIContentGenerationError(f"Failed to analyze audio: {e}", e)

    async def analyze_audio_with_structured_output(
        self,
        request: AudioAnalysisRequest,
        response_model: type[T],
    ) -> T:
        """Analyze audio directly and return structured output.

        Args:
            request: Audio analysis request
            response_model: Pydantic model for structured output

        Returns:
            Instance of response_model with analysis results
        """
        try:
            client = self._get_client()
            path = Path(request.audio_path)

            if not path.exists():
                raise OpenAIError(f"Audio file not found: {request.audio_path}")

            logger.info(f"Analyzing audio with structured output: {path}")

            # Read and encode audio as base64
            with open(path, "rb") as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode("utf-8")

            audio_format = path.suffix.lstrip(".")

            # Build message with audio input
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_data,
                                "format": audio_format,
                            },
                        },
                        {"type": "text", "text": request.prompt},
                    ],
                }
            ]

            if request.context_data:
                context_text = (
                    f"\n\nContext Data:\n{json.dumps(request.context_data, indent=2)}"
                )
                messages[0]["content"].append({"type": "text", "text": context_text})

            model = self.settings.audio_model_name
            temperature = request.temperature or self.settings.temperature

            # Convert Pydantic model to JSON schema
            schema = response_model.model_json_schema()

            logger.info(f"Using audio model with structured output: {model}")

            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=self.settings.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_model.__name__,
                        "schema": schema,
                        "strict": True,
                    },
                },
            )

            message = completion.choices[0].message
            content = message.content or "{}"

            logger.debug(f"Structured audio analysis response: {content[:500]}")

            # Parse and validate
            data = json.loads(content)
            return response_model(**data)

        except Exception as e:
            logger.error(f"Structured audio analysis failed: {e}")
            raise OpenAIContentGenerationError(
                f"Failed to analyze audio with structured output: {e}", e
            )

    async def analyze_content_with_structured_output(
        self,
        request: ContentAnalysisRequest,
        response_model: type[T],
    ) -> T:
        """Analyze content (audio, transcript, or both) and return structured output.

        Args:
            request: Content analysis request
            response_model: Pydantic model for structured output

        Returns:
            Instance of response_model with analysis results
        """
        try:
            client = self._get_client()

            logger.info("Analyzing content with structured output (OpenAI)")

            # Build the base message
            content_parts = []

            # If audio is provided, add it as input
            if request.audio_path:
                path = Path(request.audio_path)
                if not path.exists():
                    raise OpenAIError(f"Audio file not found: {request.audio_path}")

                logger.info(f"Including audio file: {path}")

                # Read and encode audio as base64
                with open(path, "rb") as audio_file:
                    audio_data = base64.b64encode(audio_file.read()).decode("utf-8")

                audio_format = path.suffix.lstrip(".")

                content_parts.append(
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_data,
                            "format": audio_format,
                        },
                    }
                )

            # Build the prompt text
            prompt_text = request.prompt

            # Add transcript if provided
            if request.transcript_text:
                prompt_text = f"{request.prompt}\n\n**Conversation Transcript:**\n{request.transcript_text}"

            # Add context data if provided
            if request.context_data:
                context_text = (
                    f"\n\nContext Data:\n{json.dumps(request.context_data, indent=2)}"
                )
                prompt_text += context_text

            # Add text part
            content_parts.append({"type": "text", "text": prompt_text})

            messages = [{"role": "user", "content": content_parts}]

            # Choose appropriate model
            model = (
                self.settings.audio_model_name
                if request.audio_path
                else self.settings.model_name
            )
            temperature = request.temperature or self.settings.temperature

            # Convert Pydantic model to JSON schema
            schema = response_model.model_json_schema()

            logger.info(f"Using model with structured output: {model}")

            completion = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=self.settings.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_model.__name__,
                        "schema": schema,
                        "strict": True,
                    },
                },
            )

            message = completion.choices[0].message
            content = message.content or "{}"

            logger.debug(f"Structured content analysis response: {content[:500]}")

            # Parse and validate
            data = json.loads(content)
            return response_model(**data)

        except Exception as e:
            logger.error(f"Structured content analysis failed: {e}")
            raise OpenAIContentGenerationError(
                f"Failed to analyze content with structured output: {e}", e
            )

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        enable_web_search: bool = False,
        **kwargs,
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        """Stream chat responses with optional web search and citations.

        Uses OpenAI's Responses API which supports web search tools.

        Args:
            messages: List of chat messages
            enable_web_search: Whether to enable web search capability
            **kwargs: Provider-specific options (temperature, max_tokens, model, etc.)

        Yields:
            ChatStreamChunk: Stream chunks with content and optional citations
        """
        try:
            client = self._get_client()

            model = kwargs.get("model", self.settings.model_name)
            temperature = kwargs.get("temperature", self.settings.temperature)
            max_tokens = kwargs.get("max_tokens", self.settings.max_tokens)

            logger.info(f"Streaming chat with web_search={enable_web_search}, model={model}")

            # Configure tools for web search if enabled (Responses API format)
            tools = [{"type": "web_search"}] if enable_web_search else []

            # Extract system prompt (instructions) from messages
            # Responses API uses 'instructions' parameter for system prompts
            instructions = None
            input_items = []
            
            for msg in messages:
                if msg.get("role") == "system":
                    # Extract system message as instructions
                    if instructions:
                        # If multiple system messages, combine them
                        instructions = f"{instructions}\n\n{msg.get('content', '')}"
                    else:
                        instructions = msg.get("content", "")
                else:
                    # User and assistant messages go in input
                    # Responses API expects messages in format: {"type": "message", "role": "...", "content": "..."}
                    input_items.append({
                        "type": "message",
                        "role": msg["role"],
                        "content": msg.get("content", "")
                    })

            # Validate: must have at least input messages or instructions
            if not input_items and not instructions:
                raise ValueError("Must provide at least input messages or instructions")

            # Create streaming response using Responses API
            # Use 'instructions' for system prompt, 'input' for conversation messages
            # Note: input should be a list (can be empty), not None
            stream_params = {
                "model": model,
                "input": input_items,  # List of messages (can be empty if only instructions)
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "stream": True,
            }
            
            # Add instructions if we have a system prompt
            if instructions:
                stream_params["instructions"] = instructions
            
            # Add tools if web search is enabled
            if tools:
                stream_params["tools"] = tools

            logger.debug(f"Stream params: model={model}, input_items={len(input_items)}, has_instructions={bool(instructions)}, tools={tools}")
            
            stream = await client.responses.create(**stream_params)

            # Track citations from web search
            accumulated_citations: list[SearchCitation] = []

            async for event in stream:
                # Handle different event types from Responses API
                content = ""
                citations: list[SearchCitation] = []
                finish_reason = None

                try:
                    # Get event type (should be a string like "response.output_text.delta")
                    event_type = getattr(event, "type", None)
                    
                    if not event_type:
                        logger.warning(f"Event missing type attribute: {type(event)}")
                        continue

                    # Handle text delta events (streaming content)
                    if event_type == "response.output_text.delta":
                        delta = getattr(event, "delta", "")
                        # Delta should be a string, but handle other types gracefully
                        content = delta if isinstance(delta, str) else str(delta) if delta else ""

                    # Handle annotation events (citations from web search)
                    elif event_type == "response.output_text.annotation.added":
                        annotation = getattr(event, "annotation", None)
                        if annotation is None:
                            logger.warning("Annotation event missing annotation data")
                            continue
                        
                        # Parse annotation - handle both dict and object formats
                        if isinstance(annotation, dict):
                            url = annotation.get("url", "")
                            title = annotation.get("title")
                            snippet = annotation.get("text") or annotation.get("snippet")
                        elif hasattr(annotation, "url"):
                            url = getattr(annotation, "url", "")
                            title = getattr(annotation, "title", None)
                            snippet = getattr(annotation, "text", None) or getattr(annotation, "snippet", None)
                        else:
                            logger.warning(f"Unsupported annotation format: {type(annotation)}")
                            continue
                        
                        # Create citation if URL is present
                        if url:
                            citation = SearchCitation(
                                url=url,
                                title=title,
                                snippet=snippet,
                                accessed_at=None,
                            )
                            citations.append(citation)
                            # Track unique citations
                            if citation not in accumulated_citations:
                                accumulated_citations.append(citation)

                    # Handle completion events
                    elif event_type == "response.completed":
                        finish_reason = "completed"
                    
                    elif event_type == "response.failed":
                        finish_reason = "failed"

                    # Yield chunk if there's content, citations, or finish reason
                    if content or citations or finish_reason:
                        yield ChatStreamChunk(
                            content=content,
                            citations=citations,
                            finish_reason=finish_reason,
                        )
                        
                except Exception as e:
                    logger.error(f"Error parsing event: {e}, event_type={getattr(event, 'type', 'unknown')}")
                    continue

            logger.info(
                f"Chat stream completed with {len(accumulated_citations)} total citations"
            )

        except Exception as e:
            logger.error(f"Streaming chat with search failed: {e}")
            # Yield error as content
            yield ChatStreamChunk(
                content=f"\n\nError: {str(e)}",
                citations=[],
                finish_reason="error",
            )
