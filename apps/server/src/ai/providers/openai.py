"""OpenAI provider implementation."""

import base64
import json
from pathlib import Path
from typing import AsyncGenerator, TypeVar

from openai import AsyncOpenAI
from openai.types.responses import (
    EasyInputMessageParam,
    FileSearchToolParam,
    ResponseCompletedEvent,
    ResponseContentPartAddedEvent,
    ResponseCreatedEvent,
    ResponseFailedEvent,
    ResponseInProgressEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseOutputTextAnnotationAddedEvent,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseReasoningTextDeltaEvent,
    ResponseTextDeltaEvent,
    ResponseWebSearchCallCompletedEvent,
    ResponseWebSearchCallInProgressEvent,
    ResponseWebSearchCallSearchingEvent,
    WebSearchToolParam,
)
from openai.types.responses.response_create_params import (
    Reasoning as ReasoningParam,
    ResponseCreateParamsStreaming,
    ResponseTextConfigParam,
)
from openai.types.shared import ReasoningEffort
from openai.types.responses.response_output_text import AnnotationURLCitation
from pydantic import BaseModel

from src.ai.base import (
    AIProvider,
    AudioAnalysisRequest,
    ChatMessage,
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
        messages: list[ChatMessage],
        instructions: str | None = None,
        enable_web_search: bool = False,
        vector_store_ids: list[str] | None = None,
        **kwargs,
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        """Stream chat responses with optional web search, file search, and citations.

        Uses OpenAI's Responses API which supports web search and file search tools.

        For reasoning models (GPT-5, o1, etc.), use reasoning-specific parameters:
        - reasoning_effort: ReasoningEffort ("minimal", "low", "medium", "high")
        - text_verbosity: Literal["low", "medium", "high"]
        - max_output_tokens: int (instead of max_tokens)

        For non-reasoning models, use standard parameters:
        - temperature: float
        - max_tokens: int

        Args:
            messages: List of chat messages (user and assistant only, no system messages)
            instructions: Optional system prompt/instructions
            enable_web_search: Whether to enable web search capability
            vector_store_ids: Optional list of vector store IDs for file search
            **kwargs: Provider-specific options:
                - model: Model name (default from settings)
                - reasoning_effort: ReasoningEffort for reasoning models
                - text_verbosity: Text verbosity for reasoning models
                - max_output_tokens: Max tokens for reasoning models
                - temperature: Temperature for non-reasoning models (not compatible with reasoning models)
                - max_tokens: Max tokens for non-reasoning models

        Yields:
            ChatStreamChunk: Stream chunks with content, reasoning, and optional citations
        """
        try:
            client = self._get_client()

            model = kwargs.get("model", self.settings.model_name)

            # Detect if this is a reasoning model
            is_reasoning_model = any(
                model.startswith(prefix) for prefix in ["gpt-5", "o1", "o3"]
            )

            logger.info(
                f"Streaming chat with web_search={enable_web_search}, "
                f"file_search={bool(vector_store_ids)}, model={model}, "
                f"is_reasoning={is_reasoning_model}"
            )

            # Configure tools (Responses API format)
            tools: list[WebSearchToolParam | FileSearchToolParam] = []

            # Add web search if enabled
            if enable_web_search:
                tools.append(WebSearchToolParam(type="web_search"))

            # Add file search if vector store IDs provided
            if vector_store_ids:
                tools.append(
                    FileSearchToolParam(
                        type="file_search", vector_store_ids=vector_store_ids
                    )
                )

            # Convert messages to Responses API format (using OpenAI's official type)
            input_items: list[EasyInputMessageParam] = [
                EasyInputMessageParam(
                    role=msg.role,  # type: ignore[typeddict-item]
                    content=msg.content,
                )
                for msg in messages
            ]

            # Build streaming params using OpenAI's TypedDict
            stream_params: ResponseCreateParamsStreaming = {
                "model": model,  # type: ignore[typeddict-item]
                "input": input_items,  # type: ignore[typeddict-item]
                "stream": True,
            }

            # Add optional parameters
            if instructions:
                stream_params["instructions"] = instructions

            if tools:
                stream_params["tools"] = tools  # type: ignore[typeddict-item]

            # Add model-specific parameters
            if is_reasoning_model:
                # Reasoning models use different parameters
                logger.info(f"Using reasoning model: {model}")

                # Add reasoning configuration if specified
                reasoning_effort: ReasoningEffort | None = kwargs.get("reasoning_effort")
                if reasoning_effort:
                    stream_params["reasoning"] = ReasoningParam(effort=reasoning_effort)

                # Add text verbosity if specified
                text_verbosity = kwargs.get("text_verbosity")
                if text_verbosity:
                    stream_params["text"] = ResponseTextConfigParam(
                        verbosity=text_verbosity
                    )

                # Use max_output_tokens for reasoning models
                max_output_tokens = kwargs.get(
                    "max_output_tokens", self.settings.max_tokens
                )
                if max_output_tokens:
                    stream_params["max_output_tokens"] = max_output_tokens

                # Log if incompatible parameters are provided
                if "temperature" in kwargs:
                    logger.warning(
                        f"temperature parameter ignored for reasoning model {model}"
                    )
                if "top_p" in kwargs:
                    logger.warning(
                        f"top_p parameter ignored for reasoning model {model}"
                    )
                if "logprobs" in kwargs:
                    logger.warning(
                        f"logprobs parameter ignored for reasoning model {model}"
                    )
            else:
                # Non-reasoning models use standard parameters
                logger.info(f"Using standard model: {model}")
                temperature = kwargs.get("temperature", self.settings.temperature)
                max_tokens = kwargs.get("max_tokens", self.settings.max_tokens)

                if temperature is not None:
                    stream_params["temperature"] = temperature
                if max_tokens:
                    stream_params["max_output_tokens"] = max_tokens

            logger.debug(
                f"Stream params: model={model}, input_items={len(input_items)}, "
                f"has_instructions={bool(instructions)}, tools={bool(tools)}"
            )

            # Create streaming response using Responses API
            logger.info("Creating stream with OpenAI Responses API...")
            stream = await client.responses.create(**stream_params)
            logger.info("Stream created successfully, starting to read events...")

            # Track citations from web search
            accumulated_citations: list[SearchCitation] = []
            # Track file citations and optionally log their content previews
            seen_file_ids: set[str] = set()

            event_count = 0
            async for event in stream:
                event_count += 1
                logger.debug(
                    f"Received event #{event_count}: {type(event).__name__}"
                )
                # Handle different event types from Responses API using official types
                content = ""
                reasoning_summary = ""
                citations: list[SearchCitation] = []
                finish_reason = None

                try:
                    # Handle lifecycle events (informational only, don't yield)
                    if isinstance(event, (
                        ResponseCreatedEvent,
                        ResponseInProgressEvent,
                        ResponseOutputItemAddedEvent,
                        ResponseOutputItemDoneEvent,
                        ResponseContentPartAddedEvent,
                        ResponseWebSearchCallInProgressEvent,
                        ResponseWebSearchCallSearchingEvent,
                        ResponseWebSearchCallCompletedEvent,
                    )):
                        # These are status/lifecycle events, just continue
                        continue

                    # Handle reasoning text delta events (reasoning models)
                    # Note: We don't stream the raw reasoning content, only log it
                    elif isinstance(event, ResponseReasoningTextDeltaEvent):
                        logger.info(
                            f"[REASONING] Got reasoning delta: {event.delta[:100]}... "
                            f"(item_id={event.item_id}, content_index={event.content_index})"
                        )
                        # Skip yielding raw reasoning content
                        continue

                    # Handle reasoning summary delta events
                    elif isinstance(event, ResponseReasoningSummaryTextDeltaEvent):
                        reasoning_summary = event.delta
                        logger.info(
                            f"[REASONING_SUMMARY] Got summary delta: {reasoning_summary[:100]}..."
                        )

                    # Handle text delta events (streaming output content)
                    elif isinstance(event, ResponseTextDeltaEvent):
                        content = event.delta
                        logger.info(
                            f"[TEXT] Got text delta: {content[:100] if content else '(empty)'}..."
                        )

                    # Handle annotation events (citations from web search)
                    elif isinstance(event, ResponseOutputTextAnnotationAddedEvent):
                        annotation = event.annotation

                        # Parse annotation as AnnotationURLCitation (handles both dict and object)
                        try:
                            # If it's a dict, parse it; if it's already an object, use as-is
                            if isinstance(annotation, dict):
                                ann_type = annotation.get("type")
                                if ann_type == "url_citation":
                                    url_citation = AnnotationURLCitation(**annotation)
                                elif ann_type == "file_citation":
                                    # Log RAG file hits (metadata and short content preview)
                                    file_id = annotation.get("file_citation", {}).get(
                                        "file_id"
                                    ) or annotation.get("file_id")
                                    quoted_text = (
                                        annotation.get("text")
                                        or annotation.get("quote")
                                        or ""
                                    )
                                    if file_id and file_id not in seen_file_ids:
                                        seen_file_ids.add(file_id)
                                        logger.info(
                                            f"RAG file cited: id={file_id}, quoted={quoted_text!r}"
                                        )
                                        # Try to fetch file metadata
                                        try:
                                            meta = await client.files.retrieve(file_id)
                                            logger.info(
                                                f"RAG file metadata: id={file_id}, name={getattr(meta, 'filename', None)}, bytes={getattr(meta, 'bytes', None)}"
                                            )
                                        except Exception as e:
                                            logger.debug(
                                                f"Failed to retrieve file metadata for {file_id}: {e}"
                                            )

                                    # Skip adding to web citations list for file citations
                                    continue
                                else:
                                    logger.debug(
                                        f"Skipped unknown annotation type: {ann_type}"
                                    )
                                    continue  # Unknown annotation type
                            elif isinstance(annotation, AnnotationURLCitation):
                                url_citation = annotation
                            else:
                                logger.debug(
                                    f"Skipped unknown annotation format: {type(annotation).__name__}"
                                )
                                continue  # Skip unknown annotation formats

                            # Create citation from parsed annotation
                            citation = SearchCitation(
                                url=url_citation.url,
                                title=url_citation.title,
                                snippet=None,
                                accessed_at=None,
                            )
                            citations.append(citation)

                            # Track unique citations
                            if citation not in accumulated_citations:
                                accumulated_citations.append(citation)

                        except Exception as e:
                            logger.error(f"Failed to parse annotation: {e}")

                    # Handle completion events
                    elif isinstance(event, ResponseCompletedEvent):
                        finish_reason = "completed"
                        logger.info("[COMPLETED] Stream completed successfully")

                    elif isinstance(event, ResponseFailedEvent):
                        finish_reason = "failed"
                        logger.error(f"[FAILED] Stream failed: {event}")

                    else:
                        # Log unhandled event types
                        logger.warning(
                            f"[UNHANDLED] Unhandled event type: {type(event).__name__}"
                        )

                    # Yield chunk if there's content, reasoning summary, citations, or finish reason
                    if content or reasoning_summary or citations or finish_reason:
                        chunk = ChatStreamChunk(
                            content=content,
                            reasoning_summary=reasoning_summary,
                            citations=citations,
                            finish_reason=finish_reason,
                        )
                        logger.debug(
                            f"[YIELD] Yielding chunk: content_len={len(content)}, "
                            f"reasoning_len={len(reasoning_summary)}, "
                            f"citations={len(citations)}, finish={finish_reason}"
                        )
                        yield chunk

                except Exception as e:
                    logger.error(
                        f"Error parsing event: {e}, event_type={type(event).__name__}"
                    )
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
