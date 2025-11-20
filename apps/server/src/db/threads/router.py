"""
Thread router with endpoints for managing chat threads and messages.

This module contains all the API endpoints for thread operations, including
creating threads, managing messages, and generating AI titles.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.ai.base import SSEEvent
from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.dependencies import get_thread_repository
from src.db.threads.repository import ThreadRepository
from src.db.threads.schemas import (
    CreateMessageRequest,
    CreateThreadRequest,
    GenerateTitleRequest,
    MessageListResponse,
    MessageResponse,
    ThreadListResponse,
    ThreadResponse,
    UpdateThreadTitleRequest,
)
from src.utils.logger import logger

router = APIRouter(prefix="/threads", tags=["Threads"])


# ========== Thread Operations ==========


@router.post("", response_model=ThreadResponse, status_code=HTTPStatus.CREATED)
async def create_thread(
    request: CreateThreadRequest,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> ThreadResponse:
    """
    Create a new thread.

    Args:
        request: Request containing optional thread ID and title
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Returns:
        ThreadResponse: The created thread

    Raises:
        HTTPException: If an error occurs creating the thread
    """
    try:
        thread = await thread_repository.create_thread(
            user_id=current_user.id,
            thread_id=request.thread_id,
            title=request.title,
        )

        await thread_repository.session.commit()

        return ThreadResponse(
            id=thread.id,
            user_id=thread.user_id,
            title=thread.title,
            archived=thread.archived,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

    except Exception as e:
        await thread_repository.session.rollback()
        logger.error("Failed to create thread", error=str(e))
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to create thread: {str(e)}",
        )


@router.get("", response_model=ThreadListResponse)
async def list_threads(
    include_archived: bool = True,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> ThreadListResponse:
    """
    List all threads for the current user.

    Args:
        include_archived: Whether to include archived threads (default: True)
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Returns:
        ThreadListResponse: List of threads

    Raises:
        HTTPException: If an error occurs retrieving threads
    """
    try:
        threads = await thread_repository.list_threads(
            user_id=current_user.id,
            include_archived=include_archived,
        )

        return ThreadListResponse(
            threads=[
                ThreadResponse(
                    id=thread.id,
                    user_id=thread.user_id,
                    title=thread.title,
                    archived=thread.archived,
                    created_at=thread.created_at,
                    updated_at=thread.updated_at,
                )
                for thread in threads
            ],
            total=len(threads),
        )

    except Exception as e:
        logger.error("Failed to list threads", error=str(e))
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to list threads: {str(e)}",
        )


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> ThreadResponse:
    """
    Get a specific thread.

    Args:
        thread_id: Thread UUID
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Returns:
        ThreadResponse: The thread

    Raises:
        HTTPException: If thread not found or an error occurs
    """
    try:
        thread = await thread_repository.get_thread(thread_id, current_user.id)

        if not thread:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Thread {thread_id} not found",
            )

        return ThreadResponse(
            id=thread.id,
            user_id=thread.user_id,
            title=thread.title,
            archived=thread.archived,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get thread", error=str(e), thread_id=thread_id)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to get thread: {str(e)}",
        )


@router.patch("/{thread_id}/title", response_model=ThreadResponse)
async def update_thread_title(
    thread_id: str,
    request: UpdateThreadTitleRequest,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> ThreadResponse:
    """
    Update a thread's title.

    Args:
        thread_id: Thread UUID
        request: Request containing new title
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Returns:
        ThreadResponse: The updated thread

    Raises:
        HTTPException: If thread not found or an error occurs
    """
    try:
        thread = await thread_repository.update_thread_title(
            thread_id=thread_id,
            user_id=current_user.id,
            title=request.title,
        )

        if not thread:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Thread {thread_id} not found",
            )

        await thread_repository.session.commit()

        return ThreadResponse(
            id=thread.id,
            user_id=thread.user_id,
            title=thread.title,
            archived=thread.archived,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        await thread_repository.session.rollback()
        logger.error("Failed to update thread title", error=str(e), thread_id=thread_id)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to update thread title: {str(e)}",
        )


@router.patch("/{thread_id}/archive", response_model=ThreadResponse)
async def archive_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> ThreadResponse:
    """
    Archive a thread.

    Args:
        thread_id: Thread UUID
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Returns:
        ThreadResponse: The archived thread

    Raises:
        HTTPException: If thread not found or an error occurs
    """
    try:
        thread = await thread_repository.archive_thread(thread_id, current_user.id)

        if not thread:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Thread {thread_id} not found",
            )

        await thread_repository.session.commit()

        return ThreadResponse(
            id=thread.id,
            user_id=thread.user_id,
            title=thread.title,
            archived=thread.archived,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        await thread_repository.session.rollback()
        logger.error("Failed to archive thread", error=str(e), thread_id=thread_id)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive thread: {str(e)}",
        )


@router.patch("/{thread_id}/unarchive", response_model=ThreadResponse)
async def unarchive_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> ThreadResponse:
    """
    Unarchive a thread.

    Args:
        thread_id: Thread UUID
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Returns:
        ThreadResponse: The unarchived thread

    Raises:
        HTTPException: If thread not found or an error occurs
    """
    try:
        thread = await thread_repository.unarchive_thread(thread_id, current_user.id)

        if not thread:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Thread {thread_id} not found",
            )

        await thread_repository.session.commit()

        return ThreadResponse(
            id=thread.id,
            user_id=thread.user_id,
            title=thread.title,
            archived=thread.archived,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        await thread_repository.session.rollback()
        logger.error("Failed to unarchive thread", error=str(e), thread_id=thread_id)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to unarchive thread: {str(e)}",
        )


@router.delete("/{thread_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> None:
    """
    Delete a thread and all its messages.

    Args:
        thread_id: Thread UUID
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Raises:
        HTTPException: If thread not found or an error occurs
    """
    try:
        deleted = await thread_repository.delete_thread(thread_id, current_user.id)

        if not deleted:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Thread {thread_id} not found",
            )

        await thread_repository.session.commit()

    except HTTPException:
        raise
    except Exception as e:
        await thread_repository.session.rollback()
        logger.error("Failed to delete thread", error=str(e), thread_id=thread_id)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete thread: {str(e)}",
        )


@router.post("/{thread_id}/generate-title")
async def generate_thread_title(
    thread_id: str,
    request: GenerateTitleRequest,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> StreamingResponse:
    """
    Generate a title for a thread using AI based on messages.

    Returns an SSE stream with the generated title for assistant-ui compatibility.

    Args:
        thread_id: Thread UUID
        request: Request containing messages to generate title from
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Returns:
        StreamingResponse: SSE stream with generated title

    Raises:
        HTTPException: If thread not found or an error occurs
    """
    try:
        # Verify thread exists and belongs to user
        thread = await thread_repository.get_thread(thread_id, current_user.id)
        if not thread:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Thread {thread_id} not found",
            )

        # Generate title from first user message (simple heuristic)
        # TODO: Use AI service for better title generation
        title = "New Chat"
        for msg in request.messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str) and content:
                    # Take first 50 chars as title
                    title = content[:50].strip()
                    if len(content) > 50:
                        title += "..."
                    break

        # Update thread title
        await thread_repository.update_thread_title(
            thread_id=thread_id,
            user_id=current_user.id,
            title=title,
        )
        await thread_repository.session.commit()

        # Return as SSE stream for assistant-ui compatibility
        async def generate_title_stream():
            """Generate SSE stream with title."""
            yield SSEEvent(data=title).format()
            yield SSEEvent(event="done", data="complete").format()

        return StreamingResponse(
            generate_title_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        await thread_repository.session.rollback()
        logger.error(
            "Failed to generate thread title", error=str(e), thread_id=thread_id
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate thread title: {str(e)}",
        )


# ========== Message Operations ==========


@router.get("/{thread_id}/messages", response_model=MessageListResponse)
async def get_messages(
    thread_id: str,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> MessageListResponse:
    """
    Get all messages for a thread.

    Args:
        thread_id: Thread UUID
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Returns:
        MessageListResponse: List of messages ordered by created_at

    Raises:
        HTTPException: If thread not found or an error occurs
    """
    try:
        messages = await thread_repository.get_messages(thread_id, current_user.id)

        return MessageListResponse(
            messages=[
                MessageResponse(
                    id=msg.id,
                    thread_id=msg.thread_id,
                    role=msg.role,
                    content=msg.content,
                    created_at=msg.created_at,
                )
                for msg in messages
            ],
            total=len(messages),
        )

    except Exception as e:
        logger.error("Failed to get messages", error=str(e), thread_id=thread_id)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}",
        )


@router.post(
    "/{thread_id}/messages", response_model=MessageResponse, status_code=HTTPStatus.CREATED
)
async def create_message(
    thread_id: str,
    request: CreateMessageRequest,
    current_user: User = Depends(get_current_user),
    thread_repository: ThreadRepository = Depends(get_thread_repository),
) -> MessageResponse:
    """
    Create a new message in a thread.

    Args:
        thread_id: Thread UUID
        request: Request containing message data
        current_user: The authenticated user
        thread_repository: The thread repository instance from dependency injection

    Returns:
        MessageResponse: The created message

    Raises:
        HTTPException: If thread not found or an error occurs
    """
    try:
        message = await thread_repository.create_message(
            thread_id=thread_id,
            user_id=current_user.id,
            message_id=request.message_id,
            role=request.role,
            content=request.content,
        )

        if not message:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Thread {thread_id} not found",
            )

        await thread_repository.session.commit()

        return MessageResponse(
            id=message.id,
            thread_id=message.thread_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        await thread_repository.session.rollback()
        logger.error(
            "Failed to create message", error=str(e), thread_id=thread_id
        )
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to create message: {str(e)}",
        )
