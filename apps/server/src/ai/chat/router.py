"""
FastAPI router for roofing chat endpoints.

Provides streaming chat interface using Server-Sent Events (SSE).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.ai.base import SSEEvent
from src.ai.chat.service import RoofingChatService
from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    """Chat message model."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Chat request with message history."""

    messages: list[ChatMessage]


# Singleton service instance
_chat_service: RoofingChatService | None = None


def get_chat_service() -> RoofingChatService:
    """
    Get or create the chat service singleton.

    Returns:
        RoofingChatService: The chat service instance
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = RoofingChatService()
        logger.info("Initialized RoofingChatService")
    return _chat_service


@router.post("/roofing")
async def stream_roofing_chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    chat_service: Annotated[RoofingChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    """
    Stream roofing chat responses via Server-Sent Events.

    Args:
        request: Chat request with message history
        current_user: Authenticated user (from JWT)
        chat_service: Chat service dependency

    Returns:
        StreamingResponse: SSE stream of chat responses
    """
    logger.info(
        f"Chat request from user {current_user.id} with {len(request.messages)} messages"
    )

    # Convert messages to OpenAI format
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

    # Create async generator for SSE
    async def event_generator():
        """Generate SSE events from chat stream with tool calls, citations and reasoning."""
        try:
            async for chunk in chat_service.stream_chat_response(messages):
                # Send tool calls if present (includes reasoning summaries)
                for tool_call in chunk.tool_calls:
                    yield SSEEvent(
                        event="tool_call",
                        data=tool_call.model_dump_json(),
                    ).format()

                # Send content if present
                if chunk.content:
                    # Escape newlines in content for SSE format
                    escaped_content = chunk.content.replace("\n", "\\n")
                    yield SSEEvent(data=escaped_content).format()

                # Send citations as separate events
                for citation in chunk.citations:
                    yield SSEEvent(
                        event="citation",
                        data=citation.model_dump_json(),
                    ).format()

                # Send finish signal if stream is complete
                if chunk.finish_reason:
                    yield SSEEvent(event="done", data=chunk.finish_reason).format()
                    break

            # Send done signal if not already sent
            yield SSEEvent(event="done", data="complete").format()

        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield SSEEvent(event="error", data=str(e)).format()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
