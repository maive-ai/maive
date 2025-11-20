"""
SQLAlchemy models for chat threads and messages.

Stores conversation threads and their messages for assistant-ui persistence.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class Thread(Base):
    """
    Chat thread model for storing conversation metadata.

    Each user can have multiple conversation threads with titles, archive status,
    and timestamps. Messages are stored in the Message table with a foreign key
    to this table.
    """

    __tablename__ = "threads"

    # Primary key - UUID
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default="gen_random_uuid()",
        comment="Thread UUID",
    )

    # User association
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="User ID (Cognito sub)",
    )

    # Thread metadata
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="New Chat",
        comment="Thread display title",
    )

    archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether thread is archived",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="Record creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="Record last update timestamp",
    )

    # Indexes
    __table_args__ = (
        # Find all threads for a user, ordered by updated_at
        Index("idx_threads_user_updated", "user_id", "updated_at"),
        # Find non-archived threads
        Index("idx_threads_user_archived", "user_id", "archived"),
    )

    def __repr__(self) -> str:
        return (
            f"<Thread(id={self.id}, user_id={self.user_id}, "
            f"title={self.title[:30]}..., archived={self.archived})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary representation.

        Returns:
            dict: Dictionary with all thread data
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "archived": self.archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Message(Base):
    """
    Message model for storing individual messages within threads.

    Each message belongs to a thread and contains role, content (stored as JSONB
    to match assistant-ui's ThreadMessage format), and timestamp.
    """

    __tablename__ = "messages"

    # Primary key - UUID
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default="gen_random_uuid()",
        comment="Message UUID",
    )

    # Foreign key to thread
    thread_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Thread UUID",
    )

    # Message role
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Message role: user, assistant, or system",
    )

    # Message content (JSONB for ThreadMessage content array)
    content: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Message content as JSON (ThreadMessage format)",
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="Record creation timestamp",
    )

    # Indexes
    __table_args__ = (
        # Find all messages for a thread, ordered by created_at
        Index("idx_messages_thread_created", "thread_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Message(id={self.id}, thread_id={self.thread_id}, "
            f"role={self.role}, created_at={self.created_at})>"
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model to dictionary representation.

        Returns:
            dict: Dictionary with all message data
        """
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
