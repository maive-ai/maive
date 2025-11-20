"""
Repository for thread and message database operations.

Provides CRUD operations for Thread and Message records using SQLAlchemy async sessions.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.threads.model import Message, Thread
from src.utils.logger import logger


class ThreadRepository:
    """Repository for managing chat threads and messages in the database."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    # ========== Thread Operations ==========

    async def create_thread(
        self,
        user_id: str,
        thread_id: str | None = None,
        title: str = "New Chat",
    ) -> Thread:
        """
        Create a new thread for a user.

        Args:
            user_id: Cognito user ID
            thread_id: Optional specific thread ID (UUID string), generated if not provided
            title: Thread title (default: "New Chat")

        Returns:
            Thread: Created thread
        """
        thread = Thread(
            user_id=user_id,
            title=title,
            archived=False,
        )

        # Set specific ID if provided
        if thread_id:
            thread.id = thread_id

        self.session.add(thread)
        await self.session.flush()
        await self.session.refresh(thread)

        logger.info(
            f"[ThreadRepository] Created thread: id={thread.id}, user_id={user_id}, title={title}"
        )
        return thread

    async def get_thread(self, thread_id: str, user_id: str) -> Thread | None:
        """
        Get a specific thread by ID.

        Args:
            thread_id: Thread UUID
            user_id: Cognito user ID (for authorization check)

        Returns:
            Thread | None: Thread if found and owned by user, None otherwise
        """
        stmt = select(Thread).where(
            Thread.id == thread_id,
            Thread.user_id == user_id,
        )

        result = await self.session.execute(stmt)
        thread = result.scalar_one_or_none()

        if thread:
            logger.debug(
                f"[ThreadRepository] Retrieved thread: id={thread_id}, user_id={user_id}"
            )
        else:
            logger.debug(
                f"[ThreadRepository] Thread not found: id={thread_id}, user_id={user_id}"
            )

        return thread

    async def list_threads(
        self,
        user_id: str,
        include_archived: bool = True,
    ) -> list[Thread]:
        """
        List all threads for a user.

        Args:
            user_id: Cognito user ID
            include_archived: Whether to include archived threads (default: True)

        Returns:
            list[Thread]: List of threads ordered by updated_at DESC
        """
        stmt = select(Thread).where(Thread.user_id == user_id)

        if not include_archived:
            stmt = stmt.where(Thread.archived == False)

        stmt = stmt.order_by(desc(Thread.updated_at))

        result = await self.session.execute(stmt)
        threads = list(result.scalars().all())

        logger.debug(
            f"[ThreadRepository] Listed {len(threads)} threads for user {user_id}"
        )
        return threads

    async def update_thread_title(
        self,
        thread_id: str,
        user_id: str,
        title: str,
    ) -> Thread | None:
        """
        Update a thread's title.

        Args:
            thread_id: Thread UUID
            user_id: Cognito user ID (for authorization check)
            title: New title

        Returns:
            Thread | None: Updated thread if found, None otherwise
        """
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            return None

        thread.title = title
        thread.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(thread)

        logger.info(
            f"[ThreadRepository] Updated thread title: id={thread_id}, title={title}"
        )
        return thread

    async def archive_thread(
        self,
        thread_id: str,
        user_id: str,
    ) -> Thread | None:
        """
        Archive a thread.

        Args:
            thread_id: Thread UUID
            user_id: Cognito user ID (for authorization check)

        Returns:
            Thread | None: Updated thread if found, None otherwise
        """
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            return None

        thread.archived = True
        thread.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(thread)

        logger.info(f"[ThreadRepository] Archived thread: id={thread_id}")
        return thread

    async def unarchive_thread(
        self,
        thread_id: str,
        user_id: str,
    ) -> Thread | None:
        """
        Unarchive a thread.

        Args:
            thread_id: Thread UUID
            user_id: Cognito user ID (for authorization check)

        Returns:
            Thread | None: Updated thread if found, None otherwise
        """
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            return None

        thread.archived = False
        thread.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(thread)

        logger.info(f"[ThreadRepository] Unarchived thread: id={thread_id}")
        return thread

    async def delete_thread(
        self,
        thread_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a thread and all its messages.

        Args:
            thread_id: Thread UUID
            user_id: Cognito user ID (for authorization check)

        Returns:
            bool: True if thread was deleted, False if not found
        """
        # First verify ownership
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            logger.warning(
                f"[ThreadRepository] Cannot delete thread: not found or unauthorized: "
                f"id={thread_id}, user_id={user_id}"
            )
            return False

        # Delete the thread (messages will cascade delete due to FK constraint)
        stmt = delete(Thread).where(
            Thread.id == thread_id,
            Thread.user_id == user_id,
        )

        result = await self.session.execute(stmt)
        deleted = result.rowcount > 0

        if deleted:
            logger.info(
                f"[ThreadRepository] Deleted thread and messages: id={thread_id}"
            )
        else:
            logger.warning(
                f"[ThreadRepository] Failed to delete thread: id={thread_id}"
            )

        return deleted

    # ========== Message Operations ==========

    async def create_message(
        self,
        thread_id: str,
        user_id: str,
        message_id: str,
        role: str,
        content: dict[str, Any],
    ) -> Message | None:
        """
        Create a new message in a thread.

        Args:
            thread_id: Thread UUID
            user_id: Cognito user ID (for authorization check)
            message_id: Message UUID
            role: Message role (user, assistant, system)
            content: Message content as dict (ThreadMessage format)

        Returns:
            Message | None: Created message if thread exists, None otherwise
        """
        # Verify thread exists and belongs to user
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            logger.warning(
                f"[ThreadRepository] Cannot create message: thread not found or unauthorized: "
                f"thread_id={thread_id}, user_id={user_id}"
            )
            return None

        message = Message(
            id=message_id,
            thread_id=thread_id,
            role=role,
            content=content,
        )

        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)

        # Update thread's updated_at
        thread.updated_at = datetime.now(UTC)
        await self.session.flush()

        logger.info(
            f"[ThreadRepository] Created message: id={message_id}, thread_id={thread_id}, role={role}"
        )
        return message

    async def get_messages(
        self,
        thread_id: str,
        user_id: str,
    ) -> list[Message]:
        """
        Get all messages for a thread.

        Args:
            thread_id: Thread UUID
            user_id: Cognito user ID (for authorization check)

        Returns:
            list[Message]: List of messages ordered by created_at ASC, empty list if thread not found
        """
        # Verify thread exists and belongs to user
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            logger.warning(
                f"[ThreadRepository] Cannot get messages: thread not found or unauthorized: "
                f"thread_id={thread_id}, user_id={user_id}"
            )
            return []

        stmt = (
            select(Message)
            .where(Message.thread_id == thread_id)
            .order_by(Message.created_at)
        )

        result = await self.session.execute(stmt)
        messages = list(result.scalars().all())

        logger.debug(
            f"[ThreadRepository] Retrieved {len(messages)} messages for thread {thread_id}"
        )
        return messages

    async def delete_messages(
        self,
        thread_id: str,
        user_id: str,
    ) -> int:
        """
        Delete all messages in a thread.

        Args:
            thread_id: Thread UUID
            user_id: Cognito user ID (for authorization check)

        Returns:
            int: Number of messages deleted
        """
        # Verify thread exists and belongs to user
        thread = await self.get_thread(thread_id, user_id)
        if not thread:
            logger.warning(
                f"[ThreadRepository] Cannot delete messages: thread not found or unauthorized: "
                f"thread_id={thread_id}, user_id={user_id}"
            )
            return 0

        stmt = delete(Message).where(Message.thread_id == thread_id)

        result = await self.session.execute(stmt)
        deleted_count = result.rowcount

        logger.info(
            f"[ThreadRepository] Deleted {deleted_count} messages from thread {thread_id}"
        )
        return deleted_count
