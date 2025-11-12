"""OpenAI provider implementation."""

import json
from pathlib import Path
from typing import Any, AsyncGenerator, BinaryIO, TypeVar

import httpx
from braintrust import wrap_openai
from openai import AsyncOpenAI
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
)
from openai.types.responses.response_create_params import (
    ResponseCreateParams,
    ResponseCreateParamsStreaming,
    ResponseTextConfigParam,
)
from openai.types.responses.response_output_text import AnnotationURLCitation
from openai.types.shared import ReasoningEffort
from pydantic import BaseModel

from src.ai.base import (
    AIProvider,
    ChatMessage,
    ChatStreamChunk,
    ContentGenerationResult,
    FileMetadata,
    ReasoningSummary,
    SearchCitation,
    ToolCall,
    ToolName,
    ToolStatus,
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

    def __init__(
        self,
        enable_braintrust: bool = False,
        braintrust_project_name: str | None = None,
    ):
        """Initialize OpenAI provider.

        Args:
            enable_braintrust: Whether to enable Braintrust tracing for this provider instance
            braintrust_project_name: Braintrust project name (only used if enable_braintrust=True)
        """
        self.settings = get_openai_settings()
        self.app_settings = get_app_settings()
        self._client: AsyncOpenAI | None = None
        self.enable_braintrust = enable_braintrust
        self.braintrust_project_name = braintrust_project_name

    def _get_client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client.

        Automatically wraps the client with Braintrust tracing if enabled.
        """
        if self._client is None:
            try:
                client = AsyncOpenAI(api_key=self.settings.api_key)

                # Wrap with Braintrust if logging is enabled for this instance
                if self.enable_braintrust:
                    project_info = (
                        f" (project: {self.braintrust_project_name})"
                        if self.braintrust_project_name
                        else ""
                    )
                    logger.info(
                        f"OpenAI client initialized with Braintrust tracing enabled{project_info}"
                    )
                    self._client = wrap_openai(client)
                else:
                    logger.info("OpenAI client initialized")
                    self._client = client

                # Configure timeout for long-running MCP calls
                timeout = httpx.Timeout(
                    timeout=self.settings.request_timeout,
                    connect=10.0,  # Connection timeout: 10s
                )
                self._client = AsyncOpenAI(
                    api_key=self.settings.api_key,
                    timeout=timeout,
                )
                logger.info(
                    "[OPENAI] Client initialized",
                    timeout_seconds=self.settings.request_timeout,
                )
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
            logger.info("[OPENAI] Uploading file", file_path=str(path), purpose=purpose)

            with open(path, "rb") as f:
                uploaded_file = await client.files.create(file=f, purpose=purpose)

            metadata = FileMetadata(
                id=uploaded_file.id,
                name=uploaded_file.filename,
                mime_type=None,  # OpenAI doesn't return mime_type
                size_bytes=uploaded_file.bytes,
            )

            logger.info("[OPENAI] File uploaded successfully", file_id=metadata.id)
            return metadata

        except OpenAIFileUploadError:
            raise
        except Exception as e:
            logger.error("[OPENAI] File upload failed", error=str(e))
            raise OpenAIFileUploadError(f"Failed to upload file: {e}", e)

    async def upload_file_from_handle(
        self, file: BinaryIO, filename: str, purpose: str = "user_data"
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
                    "seconds": 86400,  # 24 hours
                },
            )

            logger.info(
                f"[OpenAI] File uploaded successfully with 24h expiration: {uploaded_file.id}"
            )

            logger.info(
                "[OpenAI] File uploaded with 24h expiration", file_id=uploaded_file.id
            )
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

    def _extract_parsed_model(
        self, parsed_response: Any, response_schema: type[T]
    ) -> T:
        """Extract parsed Pydantic model from Responses API parse response.

        Args:
            parsed_response: Response from client.responses.parse()
            response_schema: Expected Pydantic model type

        Returns:
            Instance of response_schema with parsed data

        Raises:
            OpenAIError: If no output or unable to extract parsed model
        """
        if not parsed_response.output:
            raise OpenAIError("No output in parsed response")

        for output_item in parsed_response.output:
            if output_item.type == "message":
                # Try to get directly parsed model
                if hasattr(output_item, "parsed") and output_item.parsed:
                    logger.debug("[OPENAI] Successfully parsed structured output")
                    return output_item.parsed

                # Fallback: extract text and parse JSON
                if hasattr(output_item, "content") and output_item.content:
                    for content_part in output_item.content:
                        if (
                            hasattr(content_part, "type")
                            and content_part.type == "output_text"
                        ):
                            logger.debug(
                                "[OPENAI] Fallback to JSON parsing",
                                content_preview=content_part.text[:200],
                            )
                            data = json.loads(content_part.text)
                            return response_schema(**data)

        raise OpenAIError("Could not extract parsed data from response")

    def _build_model_params(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
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
                params["reasoning"] = {"effort": reasoning_effort, "summary": "auto"}
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
            logger.info("[OPENAI] File deleted successfully", file_id=file_id)
            return True
        except Exception as e:
            logger.error(
                "[OPENAI] Failed to delete file", file_id=file_id, error=str(e)
            )
            return False

    async def generate_content(
        self,
        prompt: str,
        file_ids: list[str] | None = None,
        file_attachments: list[tuple[str, str, bool]] | None = None,
        response_schema: type[T] | None = None,
        vector_store_ids: list[str] | None = None,
        **kwargs,
    ) -> ContentGenerationResult | T:
        """Generate text or structured content.

        Args:
            prompt: Text prompt
            file_ids: Optional file IDs (unused, kept for base class compatibility)
            file_attachments: Optional list of (file_id, filename, is_image) tuples
            response_schema: Optional Pydantic model for structured output
            vector_store_ids: Optional vector store IDs for file search (RAG)
            **kwargs: Additional options:
                - model: Model name (default from settings)
                - temperature: Temperature for standard models
                - max_tokens: Max tokens for standard models
                - max_output_tokens: Max output tokens (reasoning models) or overrides max_tokens
                - reasoning_effort: Reasoning effort for reasoning models ("minimal", "low", "medium", "high")

        Returns:
            ContentGenerationResult for text generation, or instance of response_schema for structured output
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
                        content_parts.append(
                            {"type": "input_image", "file_id": file_id}
                        )
                    else:
                        content_parts.append({"type": "input_file", "file_id": file_id})

                # Add text prompt
                content_parts.append({"type": "input_text", "text": prompt})

                input_items = [{"role": "user", "content": content_parts}]
                logger.info(
                    "[OpenAI] Including files in message",
                    file_count=len(file_attachments),
                )
            else:
                # No files, just text
                input_items = [{"type": "message", "role": "user", "content": prompt}]

            # Build params for Responses API (includes model + model-specific params)
            model_params = self._build_model_params(
                model=kwargs.get("model"),
                temperature=kwargs.get("temperature"),
                max_tokens=kwargs.get("max_tokens"),
                max_output_tokens=kwargs.get("max_output_tokens"),
                reasoning_effort=kwargs.get("reasoning_effort"),
            )

            # Build tools list
            tools: list[Any] = []

            # Add file search if vector store IDs provided
            if vector_store_ids:
                logger.info(
                    "[OPENAI] Adding FileSearchTool",
                    vector_store_count=len(vector_store_ids),
                )
                tools.append(
                    FileSearchToolParam(
                        type="file_search", vector_store_ids=vector_store_ids
                    )
                )

            # Structured output vs plain text
            if response_schema:
                logger.info(
                    "[OPENAI] Generating structured content",
                    model=model_params["model"],
                    schema=response_schema.__name__,
                )

                # Use Responses API parse() for structured output
                parse_params: dict[str, Any] = {
                    **model_params,
                    "input": input_items,
                    "text_format": response_schema,  # Pydantic model directly
                }

                if tools:
                    parse_params["tools"] = tools

                parsed_response = await client.responses.parse(**parse_params)
                return self._extract_parsed_model(parsed_response, response_schema)

            else:
                logger.info("[OPENAI] Generating content", model=model_params["model"])

                # Plain text generation
                response_params = {**model_params, "input": input_items}

                if tools:
                    response_params["tools"] = tools

                response: Response = await client.responses.create(**response_params)

                # Extract text and usage from response
                result = ContentGenerationResult(
                    text=response.output_text or "",
                    usage=response.usage.model_dump() if response.usage else None,
                    finish_reason=response.status,
                )

                logger.info(
                    "[OPENAI] Content generation complete",
                    finish_reason=result.finish_reason,
                )
                return result

        except Exception as e:
            logger.error("[OPENAI] Content generation failed", error=str(e))
            raise OpenAIContentGenerationError(f"Failed to generate content: {e}", e)

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
                        annotation.get("text") or annotation.get("quote") or ""
                    )

                    if file_id:
                        # Try to fetch file metadata for logging
                        filename = None
                        try:
                            meta = await client.files.retrieve(file_id)
                            filename = getattr(meta, "filename", None)
                            logger.debug(
                                "[OPENAI] RAG file cited",
                                file_id=file_id,
                                filename=filename,
                                quoted=quoted_text[:100],
                            )
                        except Exception as e:
                            logger.debug(
                                "[OPENAI] Failed to retrieve file metadata",
                                file_id=file_id,
                                error=str(e),
                            )

                    # Don't expose file citations to users - they're internal RAG files
                    return None
                else:
                    logger.debug(
                        "[OPENAI] Skipped unknown annotation type",
                        annotation_type=ann_type,
                    )
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
                    "[OPENAI] Skipped unknown annotation format",
                    annotation_type=type(annotation).__name__,
                )
                return None

        except Exception as e:
            logger.error("[OPENAI] Failed to parse annotation", error=str(e))
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
            "[OPENAI] Streaming chat",
            web_search=enable_web_search,
            crm_search=enable_crm_search,
            file_search=bool(vector_store_ids),
            model=model,
            is_reasoning=is_reasoning_model,
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
            logger.info("[OPENAI] Using reasoning model", model=model)

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
            text_verbosity = kwargs.get("text_verbosity", self.settings.text_verbosity)
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
                    "[OPENAI] temperature parameter ignored for reasoning model",
                    model=model,
                )
            if "top_p" in kwargs:
                logger.warning(
                    "[OPENAI] top_p parameter ignored for reasoning model", model=model
                )
            if "logprobs" in kwargs:
                logger.warning(
                    "[OPENAI] logprobs parameter ignored for reasoning model",
                    model=model,
                )
        else:
            logger.info("[OPENAI] Using standard model", model=model)
            temperature = kwargs.get("temperature", self.settings.temperature)
            max_tokens = kwargs.get("max_tokens", self.settings.max_tokens)

            if temperature is not None:
                stream_params["temperature"] = temperature
            if max_tokens:
                stream_params["max_output_tokens"] = max_tokens

        logger.debug(
            "[OPENAI] Stream params",
            model=model,
            reasoning_effort=reasoning_effort if is_reasoning_model else "N/A",
            input_items=len(input_items),
            has_instructions=bool(instructions),
            tools=bool(tools),
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

    def _buffer_and_clean_text(self, buffer: str, delta: str) -> tuple[str | None, str]:
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
        if event_type in (
            "ResponseMcpListToolsInProgressEvent",
            "ResponseMcpListToolsCompletedEvent",
        ):
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
        elif summary_delta.strip().startswith("**") and current_reasoning_summary:
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
            logger.info(
                "[STREAM] Stream created successfully, starting to read events..."
            )

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
                            content_index=event.content_index,
                        )
                        # Skip yielding raw reasoning content
                        continue

                    # Handle reasoning summary delta events
                    elif isinstance(event, ResponseReasoningSummaryTextDeltaEvent):
                        (
                            current_reasoning_id,
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
                        logger.info("[STREAM] Completed successfully")

                        # Flush any remaining text in buffer
                        if text_buffer:
                            content = self._clean_citation_markers(text_buffer)
                            text_buffer = ""

                    elif isinstance(event, ResponseFailedEvent):
                        finish_reason = "failed"
                        logger.error("[STREAM] Failed", event_details=str(event))

                        # Flush any remaining text in buffer
                        if text_buffer:
                            content = self._clean_citation_markers(text_buffer)
                            text_buffer = ""

                    else:
                        # Log unhandled event types
                        logger.warning(
                            "[UNHANDLED] Unhandled event type",
                            event_type=type(event).__name__,
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
                        "[STREAM] Error parsing event",
                        error=str(e),
                        event_type=type(event).__name__,
                    )
                    continue

            logger.info(
                "[STREAM] Chat stream completed",
                citation_count=len(accumulated_citations),
            )

        except Exception as e:
            logger.error("[STREAM] Streaming chat failed", error=str(e))
            # Yield error as content
            yield ChatStreamChunk(
                content=f"\n\nError: {str(e)}",
                citations=[],
                finish_reason="error",
            )
