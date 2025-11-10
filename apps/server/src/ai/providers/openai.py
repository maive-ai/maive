"""OpenAI provider implementation."""

import base64
import json
from pathlib import Path
from typing import Any, AsyncGenerator, BinaryIO, TypeVar

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion
from openai.types.responses import (
    EasyInputMessageParam,
    FileSearchToolParam,
    Response,
    ResponseCompletedEvent,
    ResponseContentPartAddedEvent,
    ResponseContentPartDoneEvent,
    ResponseCreatedEvent,
    ResponseFailedEvent,
    ResponseFileSearchCallCompletedEvent,
    ResponseFileSearchCallInProgressEvent,
    ResponseFileSearchCallSearchingEvent,
    ResponseInProgressEvent,
    ResponseOutputItemAddedEvent,
    ResponseOutputItemDoneEvent,
    ResponseOutputTextAnnotationAddedEvent,
    ResponseReasoningSummaryPartAddedEvent,
    ResponseReasoningSummaryPartDoneEvent,
    ResponseReasoningSummaryTextDeltaEvent,
    ResponseReasoningSummaryTextDoneEvent,
    ResponseReasoningTextDeltaEvent,
    ResponseTextDeltaEvent,
    ResponseTextDoneEvent,
    ResponseWebSearchCallCompletedEvent,
    ResponseWebSearchCallInProgressEvent,
    ResponseWebSearchCallSearchingEvent,
    WebSearchToolParam,
)
from openai.types.responses.response_create_params import (
    Reasoning as ReasoningParam,
    ResponseCreateParams,
    ResponseCreateParamsStreaming,
    ResponseTextConfigParam,
)
from openai.types.responses.response_output_text import AnnotationURLCitation
from openai.types.shared import ReasoningEffort
from pydantic import BaseModel

from src.ai.base import (
    AIProvider,
    AudioAnalysisRequest,
    ChatMessage,
    ChatStreamChunk,
    ContentAnalysisRequest,
    ContentGenerationResult,
    FileMetadata,
    ReasoningSummary,
    SearchCitation,
    ToolCall,
    ToolName,
    ToolStatus,
    TranscriptionResult,
)
from src.ai.openai.config import get_openai_settings
from src.ai.openai.exceptions import (
    OpenAIAuthenticationError,
    OpenAIContentGenerationError,
    OpenAIError,
    OpenAIFileUploadError,
)
from src.config import get_app_settings
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
        self.app_settings = get_app_settings()
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            try:
                # Configure timeout for long-running MCP calls
                timeout = httpx.Timeout(
                    timeout=self.settings.request_timeout,
                    connect=10.0,  # Connection timeout: 10s
                )
                self._client = AsyncOpenAI(
                    api_key=self.settings.api_key,
                    timeout=timeout,
                )
                logger.info("[OPENAI] Client initialized", timeout_seconds=self.settings.request_timeout)
            except Exception as e:
                logger.error("[OPENAI] Failed to initialize client", error=str(e))
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
            logger.info("Uploading file", file_path=str(path), purpose=purpose)

            with open(path, "rb") as f:
                uploaded_file = await client.files.create(file=f, purpose=purpose)

            metadata = FileMetadata(
                id=uploaded_file.id,
                name=uploaded_file.filename,
                mime_type=None,  # OpenAI doesn't return mime_type
                size_bytes=uploaded_file.bytes,
            )

            logger.info("File uploaded successfully", file_id=metadata.id)
            return metadata

        except OpenAIFileUploadError:
            raise
        except Exception as e:
            logger.error("File upload failed", error=str(e))
            raise OpenAIFileUploadError(f"Failed to upload file: {e}", e)

    async def upload_file_from_handle(
        self,
        file: BinaryIO,
        filename: str,
        purpose: str = "user_data"
    ) -> str:
        """Upload file from file handle to OpenAI with 24-hour auto-expiration.
        
        Files are automatically deleted 24 hours after upload to save storage costs.
        Use purpose="user_data" for Responses API.
        
        Args:
            file: File-like object (e.g., BytesIO, open file handle)
            filename: Name for the file
            purpose: OpenAI file purpose (default: "user_data" for Responses API)
        
        Returns:
            OpenAI file_id
            
        Raises:
            OpenAIFileUploadError: If upload fails
        """
        try:
            client = self._get_client()
            
            logger.info("[OpenAI] Uploading file", filename=filename, purpose=purpose)
            
            uploaded_file = await client.files.create(
                file=(filename, file),
                purpose=purpose,
                expires_after={
                    "anchor": "created_at",
                    "seconds": 86400  # 24 hours
                }
            )
            
            logger.info("[OpenAI] File uploaded with 24h expiration", file_id=uploaded_file.id)
            return uploaded_file.id
                    
        except Exception as e:
            logger.error("[OpenAI] File upload failed", error=str(e))
            raise OpenAIFileUploadError(f"[OpenAI] Failed to upload file: {e}", e)

    def _is_reasoning_model(self, model: str) -> bool:
        """Check if a model is a reasoning model.
        
        Args:
            model: Model name
            
        Returns:
            True if reasoning model (gpt-5, o1, o3), False otherwise
        """
        return any(model.startswith(prefix) for prefix in ["gpt-5", "o1", "o3"])

    def _build_model_params(
        self, 
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None
    ) -> dict[str, Any]:
        """Build model-specific parameters for API calls.
        
        Args:
            model: Model name (defaults to settings.model_name)
            temperature: Temperature for standard models (ignored for reasoning models)
            max_tokens: Max tokens for standard models (ignored for reasoning models)
            max_output_tokens: Max output tokens (reasoning models) or overrides max_tokens
            reasoning_effort: Reasoning effort for reasoning models ("minimal", "low", "medium", "high")
            
        Returns:
            Dict with model name and model-appropriate parameters
        """
        _model = model or self.settings.model_name
        is_reasoning = self._is_reasoning_model(_model)
        
        # Build params as dict (ResponseCreateParams is a TypedDict, not a class)
        params: ResponseCreateParams = {"model": _model}
        
        if is_reasoning:
            # Reasoning models use max_output_tokens and reasoning_effort
            output_tokens = max_output_tokens or self.settings.max_tokens
            params["max_output_tokens"] = output_tokens
            
            # Add reasoning effort if provided
            if reasoning_effort:
                params["reasoning"] = {
                    "effort": reasoning_effort,
                    "summary": "auto"
                }
        else:
            # Standard models use temperature and max_output_tokens
            temp = temperature if temperature is not None else self.settings.temperature
            tokens = max_output_tokens or max_tokens or self.settings.max_tokens
            params["temperature"] = temp
            params["max_output_tokens"] = tokens
        
        return params

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
            logger.info("File deleted successfully", file_id=file_id)
            return True
        except Exception as e:
            logger.error("Failed to delete file", file_id=file_id, error=str(e))
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

            logger.info("Transcribing audio", audio_path=str(path))

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

            logger.info("Transcription complete", char_count=len(result.text))
            return result

        except OpenAIContentGenerationError:
            raise
        except Exception as e:
            logger.error("Transcription failed", error=str(e))
            raise OpenAIContentGenerationError(f"Failed to transcribe audio: {e}", e)

    async def generate_content(
        self,
        prompt: str,
        file_ids: list[str] | None = None,
        file_attachments: list[tuple[str, str, bool]] | None = None,
        **kwargs,
    ) -> ContentGenerationResult:
        """Generate text content.

        Args:
            prompt: Text prompt
            file_ids: Optional file IDs (unused, kept for base class compatibility)
            file_attachments: Optional list of (file_id, filename, is_image) tuples
            **kwargs: Additional options (temperature, max_tokens, model, reasoning_effort, etc.)

        Returns:
            ContentGenerationResult: Generated content
        """
        try:
            client = self._get_client()
            # Build input for Responses API
            if file_attachments:
                # Build content as array with file references and text (Responses API format)
                content_parts = []
                
                # Add each file with appropriate type (input_image for images, input_file for docs)
                for file_id, filename, is_image in file_attachments:
                    if is_image:
                        content_parts.append({
                            "type": "input_image",
                            "file_id": file_id
                        })
                    else:
                        content_parts.append({
                            "type": "input_file",
                            "file_id": file_id
                        })
                
                # Add text prompt
                content_parts.append({
                    "type": "input_text",
                    "text": prompt
                })
                
                input_items = [{"role": "user", "content": content_parts}]
                logger.info("[OpenAI] Including files in message", file_count=len(file_attachments))
            else:
                # No files, just text
                input_items = [{"role": "user", "content": prompt}]

            # Build params for Responses API (includes model + model-specific params)
            response_params = self._build_model_params(
                model=kwargs.get("model"),
                temperature=kwargs.get("temperature"),
                max_tokens=kwargs.get("max_tokens"),
                max_output_tokens=kwargs.get("max_output_tokens"),
                reasoning_effort=kwargs.get("reasoning_effort")
            )
            response_params["input"] = input_items
            
            logger.info("[OpenAI] Generating content", model=response_params['model'])

            # Use Responses API (not streaming)
            response: Response = await client.responses.create(**response_params)

            # Extract text and usage from response
            result = ContentGenerationResult(
                text=response.output_text or "",
                usage=response.usage.model_dump() if response.usage else None,
                finish_reason=response.status,
            )

            logger.info("Content generation complete", finish_reason=result.finish_reason)
            return result

        except Exception as e:
            logger.error("Content generation failed", error=str(e))
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

            logger.info("Generating structured content", model=model)

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

            logger.debug("Structured response", response_preview=content[:500])

            # Parse and validate
            data = json.loads(content)
            return response_model(**data)

        except Exception as e:
            logger.error("Structured content generation failed", error=str(e))
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

            logger.info("Analyzing audio with context", audio_path=str(path))

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

            logger.info("Using audio model", model=model)

            completion: ChatCompletion = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=self.settings.max_tokens,
            )

            message = completion.choices[0].message

            result = ContentGenerationResult(
                text=message.content or "",
                usage=completion.usage.model_dump() if completion.usage else None,
                finish_reason=completion.choices[0].finish_reason,
            )

            logger.info("Audio analysis complete", finish_reason=result.finish_reason)
            return result

        except Exception as e:
            logger.error("Audio analysis failed", error=str(e))
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

            logger.info("Analyzing audio with structured output", audio_path=str(path))

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

            logger.info("Using audio model with structured output", model=model)

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

            logger.debug("Structured audio analysis response", response_preview=content[:500])

            # Parse and validate
            data = json.loads(content)
            return response_model(**data)

        except Exception as e:
            logger.error("Structured audio analysis failed", error=str(e))
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

            logger.info("Analyzing content with structured output (Responses API)")

            # Build input items for Responses API
            input_items: list[dict[str, Any]] = []

            # If audio is provided, add it as input
            if request.audio_path:
                path = Path(request.audio_path)
                if not path.exists():
                    raise OpenAIError(f"Audio file not found: {request.audio_path}")

                logger.info("Including audio file", audio_path=str(path))

                # Read and encode audio as base64
                with open(path, "rb") as audio_file:
                    audio_data = base64.b64encode(audio_file.read()).decode("utf-8")

                audio_format = path.suffix.lstrip(".")

                input_items.append(
                    {
                        "type": "input_audio",
                        "audio": audio_data,
                        "format": audio_format,
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

            # Add message item
            input_items.append({"type": "message", "role": "user", "content": prompt_text})

            # Choose appropriate model
            model = (
                self.settings.audio_model_name
                if request.audio_path
                else self.settings.model_name
            )

            # Build model params using existing helper
            model_params = self._build_model_params(
                model=model,
                temperature=request.temperature,
                max_tokens=self.settings.max_tokens,
            )

            logger.info("[OPENAI] Using Responses API parse() with Pydantic model", model=model)

            # Build tools list
            tools: list[Any] = []

            # Add file search if vector store IDs provided
            if request.vector_store_ids:
                logger.info("[OPENAI] Adding FileSearchTool", vector_store_count=len(request.vector_store_ids))
                tools.append(
                    FileSearchToolParam(
                        type="file_search",
                        vector_store_ids=request.vector_store_ids
                    )
                )

            # Use Responses API parse() method which directly accepts Pydantic models
            # This is cleaner than manually constructing JSON schema
            parse_params: dict[str, Any] = {
                **model_params,
                "input": input_items,
                "text_format": response_model,
            }

            if tools:
                parse_params["tools"] = tools

            parsed_response = await client.responses.parse(**parse_params)

            # The parse() method returns a ParsedResponse with the parsed data
            # Extract the parsed Pydantic model from the response
            if not parsed_response.output:
                raise OpenAIError("No output in parsed response")

            logger.debug("[OPENAI] Parsed response status", status=parsed_response.status)
            logger.debug("[OPENAI] Parsed response has output items", output_count=len(parsed_response.output))

            # Find the message output item with parsed content
            for output_item in parsed_response.output:
                logger.debug("[OPENAI] Output item type", type=output_item.type)

                if output_item.type == "message":
                    # The content should be the parsed Pydantic model
                    if hasattr(output_item, "parsed") and output_item.parsed:
                        logger.debug("[OPENAI] Successfully parsed structured output")
                        return output_item.parsed
                    # Fallback: content is a list of content parts, extract text
                    elif hasattr(output_item, "content") and output_item.content:
                        # Content is a list of content parts (output_text, etc.)
                        text_content = ""
                        for content_part in output_item.content:
                            if hasattr(content_part, "type") and content_part.type == "output_text":
                                text_content = content_part.text
                                break

                        if text_content:
                            data = json.loads(text_content)
                            return response_model(**data)

            raise OpenAIError("Could not extract parsed data from response")

        except Exception as e:
            logger.error("[OPENAI] Structured content analysis failed", error=str(e))
            raise OpenAIContentGenerationError(
                f"Failed to analyze content with structured output: {e}", e
            )

    async def _parse_annotation_to_citation(
        self,
        annotation: dict | AnnotationURLCitation,
        client: AsyncOpenAI,
    ) -> SearchCitation | None:
        """Parse an annotation event into a SearchCitation.

        Args:
            annotation: The annotation from OpenAI (dict or object)
            client: OpenAI client for fetching file metadata

        Returns:
            SearchCitation if it's a web citation, None if it's a file citation or unknown
        """
        try:
            # Handle dict format annotations
            if isinstance(annotation, dict):
                ann_type = annotation.get("type")
                
                if ann_type == "url_citation":
                    url_citation = AnnotationURLCitation(**annotation)
                    
                    # Create citation from URL annotation
                    return SearchCitation(
                        url=url_citation.url,
                        title=url_citation.title,
                        snippet=None,
                        accessed_at=None,
                    )
                    
                elif ann_type == "file_citation":
                    # Log RAG file hits for debugging (don't expose to user)
                    file_id = annotation.get("file_citation", {}).get(
                        "file_id"
                    ) or annotation.get("file_id")
                    quoted_text = (
                        annotation.get("text")
                        or annotation.get("quote")
                        or ""
                    )
                    
                    if file_id:
                        # Try to fetch file metadata for logging
                        filename = None
                        try:
                            meta = await client.files.retrieve(file_id)
                            filename = getattr(meta, 'filename', None)
                            logger.debug(
                                "RAG file cited",
                                file_id=file_id,
                                filename=filename,
                                quoted=quoted_text[:100]
                            )
                        except Exception as e:
                            logger.debug(
                                "Failed to retrieve file metadata",
                                file_id=file_id,
                                error=str(e)
                            )
                    
                    # Don't expose file citations to users - they're internal RAG files
                    return None
                else:
                    logger.debug("Skipped unknown annotation type", annotation_type=ann_type)
                    return None
                    
            # Handle object format annotations
            elif isinstance(annotation, AnnotationURLCitation):
                # Create citation from URL annotation
                return SearchCitation(
                    url=annotation.url,
                    title=annotation.title,
                    snippet=None,
                    accessed_at=None,
                )
            else:
                logger.debug(
                    "Skipped unknown annotation format",
                    annotation_type=type(annotation).__name__
                )
                return None

        except Exception as e:
            logger.error("Failed to parse annotation", error=str(e))
            return None

    def _build_stream_params(
        self,
        messages: list[ChatMessage],
        instructions: str | None,
        enable_web_search: bool,
        enable_crm_search: bool,
        vector_store_ids: list[str] | None,
        **kwargs,
    ) -> tuple[ResponseCreateParamsStreaming, str, bool]:
        """Build streaming parameters for OpenAI Responses API.

        Args:
            messages: List of chat messages
            instructions: Optional system instructions
            enable_web_search: Whether to enable web search
            enable_crm_search: Whether to enable CRM search via MCP
            vector_store_ids: Optional vector store IDs for file search
            **kwargs: Additional model-specific parameters

        Returns:
            Tuple of (stream_params, model_name, is_reasoning_model)
        """
        model = kwargs.get("model", self.settings.model_name)

        # Detect if this is a reasoning model
        is_reasoning_model = any(
            model.startswith(prefix) for prefix in ["gpt-5", "o1", "o3"]
        )

        logger.info(
            "Streaming chat",
            web_search=enable_web_search,
            crm_search=enable_crm_search,
            file_search=bool(vector_store_ids),
            model=model,
            is_reasoning=is_reasoning_model
        )

        # Configure tools (Responses API format)
        tools: list[WebSearchToolParam | FileSearchToolParam | dict[str, Any]] = []

        # Add web search if enabled
        if enable_web_search:
            tools.append(WebSearchToolParam(type="web_search"))

        # Add CRM search via MCP if enabled
        if enable_crm_search:
            mcp_config: dict[str, Any] = {
                "type": "mcp",
                "server_label": "crm_server",
                "server_url": f"{self.app_settings.server_base_url}/crm/mcp",
                "require_approval": "never",
            }
            # Add auth token if configured
            if self.app_settings.mcp_auth_token:
                mcp_config["headers"] = {
                    "Authorization": f"Bearer {self.app_settings.mcp_auth_token}"
                }
            
            tools.append(mcp_config)

        # Add file search if vector store IDs provided
        if vector_store_ids:
            tools.append(
                FileSearchToolParam(
                    type="file_search", vector_store_ids=vector_store_ids
                )
            )

        # Convert messages to Responses API format
        input_items: list[EasyInputMessageParam] = [
            EasyInputMessageParam(
                role=msg.role,  # type: ignore[typeddict-item]
                content=msg.content,
            )
            for msg in messages
        ]

        # Build streaming params
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
            logger.info("Using reasoning model", model=model)

            # Add reasoning configuration (use default from config if not specified)
            reasoning_effort: ReasoningEffort | None = kwargs.get(
                "reasoning_effort", self.settings.reasoning_effort
            )
            if reasoning_effort:
                stream_params["reasoning"] = ReasoningParam(
                    effort=reasoning_effort,
                    summary="auto",  # Request reasoning summaries
                )

            # Add text verbosity
            text_verbosity = kwargs.get(
                "text_verbosity", self.settings.text_verbosity
            )
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
                    "temperature parameter ignored for reasoning model",
                    model=model
                )
            if "top_p" in kwargs:
                logger.warning(
                    "top_p parameter ignored for reasoning model",
                    model=model
                )
            if "logprobs" in kwargs:
                logger.warning(
                    "logprobs parameter ignored for reasoning model",
                    model=model
                )
        else:
            logger.info("Using standard model", model=model)
            temperature = kwargs.get("temperature", self.settings.temperature)
            max_tokens = kwargs.get("max_tokens", self.settings.max_tokens)

            if temperature is not None:
                stream_params["temperature"] = temperature
            if max_tokens:
                stream_params["max_output_tokens"] = max_tokens

        logger.debug(
            "Stream params",
            model=model,
            reasoning_effort=reasoning_effort if is_reasoning_model else 'N/A',
            input_items=len(input_items),
            has_instructions=bool(instructions),
            tools=bool(tools)
        )

        return stream_params, model, is_reasoning_model

    def _handle_web_search_event(
        self,
        event: ResponseWebSearchCallInProgressEvent
        | ResponseWebSearchCallSearchingEvent
        | ResponseWebSearchCallCompletedEvent,
    ) -> ToolCall | None:
        """Handle web search tool events.

        Args:
            event: Web search event from OpenAI

        Returns:
            ToolCall if the event should be yielded, None otherwise
        """
        if isinstance(event, ResponseWebSearchCallInProgressEvent):
            logger.info("[WEB_SEARCH] Search started", item_id=event.item_id)
            return ToolCall(
                tool_call_id=event.item_id,
                tool_name=ToolName.WEB_SEARCH,
                args={},
                result=None,
            )
        elif isinstance(event, ResponseWebSearchCallSearchingEvent):
            # Just skip - don't yield to prevent flickering
            return None
        elif isinstance(event, ResponseWebSearchCallCompletedEvent):
            logger.info("[WEB_SEARCH] Search completed", item_id=event.item_id)
            return ToolCall(
                tool_call_id=event.item_id,
                tool_name=ToolName.WEB_SEARCH,
                args={},
                result={"status": ToolStatus.COMPLETE.value},
            )
        return None

    def _handle_file_search_event(
        self,
        event: ResponseFileSearchCallInProgressEvent
        | ResponseFileSearchCallSearchingEvent
        | ResponseFileSearchCallCompletedEvent,
    ) -> ToolCall | None:
        """Handle file search tool events.

        Args:
            event: File search event from OpenAI

        Returns:
            ToolCall if the event should be yielded, None otherwise
        """
        if isinstance(event, ResponseFileSearchCallInProgressEvent):
            logger.info("[FILE_SEARCH] Search started", item_id=event.item_id)
            return ToolCall(
                tool_call_id=event.item_id,
                tool_name=ToolName.FILE_SEARCH,
                args={},
                result=None,
            )
        elif isinstance(event, ResponseFileSearchCallSearchingEvent):
            # Just skip - don't yield to prevent flickering
            return None
        elif isinstance(event, ResponseFileSearchCallCompletedEvent):
            logger.info("[FILE_SEARCH] Search completed", item_id=event.item_id)
            return ToolCall(
                tool_call_id=event.item_id,
                tool_name=ToolName.FILE_SEARCH,
                args={},
                result={"status": ToolStatus.COMPLETE.value},
            )
        return None

    def _clean_citation_markers(self, text: str) -> str:
        """Remove citation markers from text.
        
        Removes file citation markers and barcode symbols that OpenAI includes
        for internal RAG document references.
        Also strips MCP/tool marker tokens and Private Use Area (PUA) control
        characters that the Responses API may embed (renders as boxes/barcodes).
        
        Args:
            text: Text potentially containing citation markers
            
        Returns:
            Text with citation markers removed
        """
        import re
        
        cleaned = text
        # Remove well-known literal markers
        cleaned = cleaned.replace("filecite", "")
        # Remove 'turnXfileY', 'turnXcrmY', and any generic 'turnX<word>Y' tokens
        cleaned = re.sub(r"turn\d+[a-z_]+\d+", "", cleaned, flags=re.IGNORECASE)
        # Remove duplicated concatenations like 'turn0file1turn0file2'
        cleaned = re.sub(r"(turn\d+[a-z_]+\d+)+", "", cleaned, flags=re.IGNORECASE)
        # Remove Private Use Area Unicode chars (often render as barcode blocks)
        # BMP PUA range: U+E000-U+F8FF
        cleaned = re.sub(r"[\uE000-\uF8FF]", "", cleaned)
        # Remove any stray box-drawing/equals-like artifacts sometimes used as separators
        cleaned = cleaned.replace("≡", "").replace("░", "").replace("█", "")
        
        return cleaned

    def _buffer_and_clean_text(
        self, buffer: str, delta: str
    ) -> tuple[str | None, str]:
        """Buffer text deltas and clean citation markers at word boundaries.
        
        Buffers incoming text until a space is encountered, then cleans citation
        markers from complete words before streaming to the frontend. This prevents
        users from seeing citation markers flash during streaming.
        
        Args:
            buffer: Current text buffer
            delta: New text delta from stream
            
        Returns:
            Tuple of (cleaned_content, new_buffer):
            - cleaned_content: Cleaned text to send (None if still buffering)
            - new_buffer: Updated buffer for next iteration
        """
        buffer += delta
        
        # Wait for a space (word boundary) before cleaning and sending
        if " " not in buffer:
            return None, buffer
        
        # Split on last space to keep incomplete word in buffer
        parts = buffer.rsplit(" ", 1)
        words_to_send = parts[0] + " "  # Include the space
        new_buffer = parts[1] if len(parts) > 1 else ""
        
        # Clean citation markers from complete words
        cleaned = self._clean_citation_markers(words_to_send)
        
        return cleaned, new_buffer

    def _handle_mcp_event(self, event: Any) -> ToolCall | None:
        """Handle MCP tool call events.

        Args:
            event: MCP event from OpenAI

        Returns:
            ToolCall if the event should be yielded, None otherwise
        """
        event_type = type(event).__name__
        
        # MCP tool listing events (not individual tool calls)
        if event_type in ("ResponseMcpListToolsInProgressEvent", "ResponseMcpListToolsCompletedEvent"):
            logger.debug("[MCP] Tool listing event", event_type=event_type)
            return None
        
        # MCP tool call started
        # Note: The in_progress event doesn't include the tool name - only item_id, output_index, sequence_number, type
        elif event_type == "ResponseMcpCallInProgressEvent":
            item_id = getattr(event, "item_id", "unknown")
            logger.info("[MCP] Tool call started", item_id=item_id)
            
            # Return a hard coded "CRM search" message since we don't have the specific tool name yet
            return ToolCall(
                tool_call_id=item_id,
                tool_name=ToolName.MCP_TOOL,
                args={"description": "Searching CRM..."},  # Generic message for UI
                result=None,
            )
        
        # MCP tool arguments being streamed
        elif event_type == "ResponseMcpCallArgumentsDeltaEvent":
            # Don't yield - just accumulate args
            logger.debug("[MCP] Arguments delta")
            return None
        
        # MCP tool arguments complete
        elif event_type == "ResponseMcpCallArgumentsDoneEvent":
            # Don't yield - wait for completion
            return None
        
        # MCP tool call completed
        elif event_type == "ResponseMcpCallCompletedEvent":
            item_id = getattr(event, "item_id", "unknown")
            logger.info("[MCP] Tool call completed", item_id=item_id)
            return ToolCall(
                tool_call_id=item_id,
                tool_name=ToolName.MCP_TOOL,
                args={},
                result={"status": ToolStatus.COMPLETE.value},
            )
        
        # MCP tool listing failed
        elif event_type == "ResponseMcpListToolsFailedEvent":
            logger.error("[MCP] Tool listing failed")
            return None
        
        # MCP tool call failed
        elif event_type == "ResponseMcpCallFailedEvent":
            item_id = getattr(event, "item_id", "unknown")
            error = getattr(event, "error", "unknown error")
            logger.warning("[MCP] Tool call failed", item_id=item_id, error=str(error))
            # OpenAI typically retries automatically, so don't yield error to UI
            return None
        
        return None

    def _handle_reasoning_summary_delta(
        self,
        event: ResponseReasoningSummaryTextDeltaEvent,
        current_reasoning_id: str | None,
        reasoning_summary_count: int,
        current_reasoning_summary: str,
    ) -> tuple[str | None, int, str, ReasoningSummary | None]:
        """Handle reasoning summary delta events.
        
        Args:
            event: Reasoning summary text delta event from OpenAI
            current_reasoning_id: Current reasoning summary ID (None if starting new summary)
            reasoning_summary_count: Counter for unique reasoning IDs
            current_reasoning_summary: Accumulated summary text
            
        Returns:
            Tuple of (updated_reasoning_id, updated_count, updated_summary, reasoning_summary_to_append)
        """
        summary_delta = event.delta or ""

        if current_reasoning_id is None:
            reasoning_summary_count += 1
            current_reasoning_id = f"reasoning_{reasoning_summary_count}"
            current_reasoning_summary = summary_delta
        elif (
            summary_delta.strip().startswith("**")
            and current_reasoning_summary
        ):
            reasoning_summary_count += 1
            current_reasoning_id = f"reasoning_{reasoning_summary_count}"
            current_reasoning_summary = summary_delta
        else:
            current_reasoning_summary += summary_delta

        reasoning_summary_to_append = None
        if current_reasoning_id:
            reasoning_summary_to_append = ReasoningSummary(
                id=current_reasoning_id,
                summary=current_reasoning_summary,
            )

        return (
            current_reasoning_id,
            reasoning_summary_count,
            current_reasoning_summary,
            reasoning_summary_to_append,
        )

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        instructions: str | None = None,
        enable_web_search: bool = False,
        enable_crm_search: bool = False,
        vector_store_ids: list[str] | None = None,
        **kwargs,
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        """Stream chat responses with optional web search, file search, CRM search, and citations.

        Uses OpenAI's Responses API for all tool types including MCP (CRM search).

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
            enable_crm_search: Whether to enable CRM search tools via MCP
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

            # Build stream parameters
            stream_params, model, is_reasoning_model = self._build_stream_params(
                messages=messages,
                instructions=instructions,
                enable_web_search=enable_web_search,
                enable_crm_search=enable_crm_search,
                vector_store_ids=vector_store_ids,
                **kwargs,
            )

            # Create streaming response using Responses API
            logger.info("[STREAM] Creating stream with OpenAI Responses API...")
            stream = await client.responses.create(**stream_params)
            logger.info("[STREAM] Stream created successfully, starting to read events...")

            # Track citations from web search
            accumulated_citations: list[SearchCitation] = []
            
            # Buffer for word-by-word streaming with citation cleaning
            text_buffer = ""
            # Track reasoning summary state
            current_reasoning_summary = ""
            current_reasoning_id: str | None = None
            reasoning_summary_count = 0  # Counter for unique reasoning IDs

            async for event in stream:
                # Handle different event types from Responses API using official types
                content = ""
                citations: list[SearchCitation] = []
                finish_reason = None
                tool_calls_to_yield: list[ToolCall] = []
                reasoning_summaries_to_yield: list[ReasoningSummary] = []

                try:
                    # Handle lifecycle events (informational only, don't yield)
                    if isinstance(
                        event,
                        (
                            ResponseCreatedEvent,
                            ResponseInProgressEvent,
                            ResponseOutputItemAddedEvent,
                            ResponseOutputItemDoneEvent,
                            ResponseContentPartAddedEvent,
                        ),
                    ):
                        # These are status/lifecycle events, just continue
                        continue
                    
                    # Handle MCP tool events
                    elif type(event).__name__ in (
                        "ResponseMcpListToolsInProgressEvent",
                        "ResponseMcpListToolsCompletedEvent", 
                        "ResponseMcpListToolsFailedEvent",
                        "ResponseMcpCallInProgressEvent",
                        "ResponseMcpCallArgumentsDeltaEvent",
                        "ResponseMcpCallArgumentsDoneEvent",
                        "ResponseMcpCallCompletedEvent",
                        "ResponseMcpCallFailedEvent",
                    ):
                        tool_call = self._handle_mcp_event(event)
                        if tool_call:
                            tool_calls_to_yield.append(tool_call)
                        else:
                            continue

                    # Handle web search tool events
                    elif isinstance(
                        event,
                        (
                            ResponseWebSearchCallInProgressEvent,
                            ResponseWebSearchCallSearchingEvent,
                            ResponseWebSearchCallCompletedEvent,
                        ),
                    ):
                        tool_call = self._handle_web_search_event(event)
                        if tool_call:
                            tool_calls_to_yield.append(tool_call)
                        else:
                            continue

                    # Handle file search tool events
                    elif isinstance(
                        event,
                        (
                            ResponseFileSearchCallInProgressEvent,
                            ResponseFileSearchCallSearchingEvent,
                            ResponseFileSearchCallCompletedEvent,
                        ),
                    ):
                        tool_call = self._handle_file_search_event(event)
                        if tool_call:
                            tool_calls_to_yield.append(tool_call)
                        else:
                            continue

                    # Handle reasoning text delta events (reasoning models)
                    # Note: We don't stream the raw reasoning content, only log it
                    elif isinstance(event, ResponseReasoningTextDeltaEvent):
                        logger.debug(
                            "[REASONING] Got reasoning delta",
                            delta_preview=event.delta[:100],
                            item_id=event.item_id,
                            content_index=event.content_index
                        )
                        # Skip yielding raw reasoning content
                        continue

                    # Handle reasoning summary delta events
                    elif isinstance(event, ResponseReasoningSummaryTextDeltaEvent):
                        (   current_reasoning_id,
                            reasoning_summary_count,
                            current_reasoning_summary,
                            reasoning_summary,
                        ) = self._handle_reasoning_summary_delta(
                            event=event,
                            current_reasoning_id=current_reasoning_id,
                            reasoning_summary_count=reasoning_summary_count,
                            current_reasoning_summary=current_reasoning_summary,
                        )
                        
                        if reasoning_summary:
                            reasoning_summaries_to_yield.append(reasoning_summary)

                    # Handle reasoning summary lifecycle events (no action needed)
                    elif isinstance(
                        event,
                        (
                            ResponseReasoningSummaryPartAddedEvent,
                            ResponseReasoningSummaryTextDoneEvent,
                            ResponseReasoningSummaryPartDoneEvent,
                        ),
                    ):
                        # These are lifecycle/completion events for reasoning summaries
                        continue

                    # Handle text delta events (streaming output content)
                    elif isinstance(event, ResponseTextDeltaEvent):
                        # Buffer and clean text at word boundaries
                        cleaned_content, text_buffer = self._buffer_and_clean_text(
                            text_buffer, event.delta
                        )
                        
                        if cleaned_content:
                            content = cleaned_content
                        else:
                            # Still buffering, wait for next delta
                            continue

                    # Handle annotation events (citations from web search and file search)
                    elif isinstance(event, ResponseOutputTextAnnotationAddedEvent):
                        citation = await self._parse_annotation_to_citation(
                            annotation=event.annotation,
                            client=client,
                        )
                        
                        # Add citation if it's a web citation (file citations return None)
                        if citation:
                            citations.append(citation)
                            
                            # Track unique citations
                            if citation not in accumulated_citations:
                                accumulated_citations.append(citation)

                    # Handle text done events (completion marker for text content)
                    elif isinstance(event, ResponseTextDoneEvent):
                        # Text content is done, no action needed
                        continue
                    
                    # Handle content part done events (completion marker for content parts)
                    elif isinstance(event, ResponseContentPartDoneEvent):
                        # Content part is done, no action needed
                        continue

                    # Handle completion events
                    elif isinstance(event, ResponseCompletedEvent):
                        finish_reason = "completed"
                        logger.info("[Stream] Completed successfully")
                        
                        # Flush any remaining text in buffer
                        if text_buffer:
                            content = self._clean_citation_markers(text_buffer)
                            text_buffer = ""

                    elif isinstance(event, ResponseFailedEvent):
                        finish_reason = "failed"
                        logger.error("[Stream] Failed", event_details=str(event))
                        
                        # Flush any remaining text in buffer
                        if text_buffer:
                            content = self._clean_citation_markers(text_buffer)
                            text_buffer = ""

                    else:
                        # Log unhandled event types
                        logger.warning(
                            "[UNHANDLED] Unhandled event type",
                            event_type=type(event).__name__
                        )

                    # Yield chunk if there's content, tool calls, citations, or finish reason
                    if (
                        content
                        or tool_calls_to_yield
                        or reasoning_summaries_to_yield
                        or citations
                        or finish_reason
                    ):
                        chunk = ChatStreamChunk(
                            content=content,
                            tool_calls=tool_calls_to_yield,
                            reasoning_summaries=reasoning_summaries_to_yield,
                            citations=citations,
                            finish_reason=finish_reason,
                        )

                        yield chunk

                except Exception as e:
                    logger.error(
                        "Error parsing event",
                        error=str(e),
                        event_type=type(event).__name__
                    )
                    continue

            logger.info("Chat stream completed", citation_count=len(accumulated_citations))

        except Exception as e:
            logger.error("Streaming chat failed", error=str(e))
            # Yield error as content
            yield ChatStreamChunk(
                content=f"\n\nError: {str(e)}",
                citations=[],
                finish_reason="error",
            )
