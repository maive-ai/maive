"""
Pydantic schemas for thread and message operations.

This module contains all Pydantic models related to chat thread management,
including request and response models for CRUD operations.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ========== Thread Schemas ==========


class CreateThreadRequest(BaseModel):
    """Request model for creating a new thread."""

    title: str = Field("New Chat", description="Thread title")
    thread_id: str | None = Field(
        None, description="Optional specific thread ID (UUID)"
    )


class UpdateThreadTitleRequest(BaseModel):
    """Request model for updating a thread's title."""

    title: str = Field(..., description="New thread title", min_length=1)


class ThreadResponse(BaseModel):
    """Response model for a single thread."""

    id: str = Field(..., description="Thread UUID")
    user_id: str = Field(..., description="Cognito user ID")
    title: str = Field(..., description="Thread title")
    archived: bool = Field(..., description="Whether thread is archived")
    created_at: datetime = Field(..., description="When the thread was created")
    updated_at: datetime = Field(..., description="When the thread was last updated")


class ThreadListResponse(BaseModel):
    """Response model for list of threads."""

    threads: list[ThreadResponse] = Field(..., description="List of threads")
    total: int = Field(..., description="Total number of threads")


class GenerateTitleRequest(BaseModel):
    """Request model for generating a thread title from messages."""

    messages: list[dict[str, Any]] = Field(
        ..., description="Messages to generate title from"
    )


# ========== Message Schemas ==========


class CreateMessageRequest(BaseModel):
    """Request model for creating a new message."""

    message_id: str = Field(..., description="Message UUID")
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: dict[str, Any] = Field(
        ..., description="Message content (ThreadMessage format)"
    )


class MessageResponse(BaseModel):
    """Response model for a single message."""

    id: str = Field(..., description="Message UUID")
    thread_id: str = Field(..., description="Thread UUID")
    role: str = Field(..., description="Message role")
    content: dict[str, Any] = Field(..., description="Message content")
    created_at: datetime = Field(..., description="When the message was created")


class MessageListResponse(BaseModel):
    """Response model for list of messages."""

    messages: list[MessageResponse] = Field(..., description="List of messages")
    total: int = Field(..., description="Total number of messages")
