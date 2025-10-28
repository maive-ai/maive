"""
Repository for call list database operations.

Provides CRUD operations for CallListItem records using SQLAlchemy async sessions.
"""

from datetime import UTC, datetime

from sqlalchemy import delete, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.call_list.model import CallListItem
from src.utils.logger import logger


class CallListRepository:
    """Repository for managing call list items in the database."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def add_items(
        self,
        user_id: str,
        project_ids: list[str],
    ) -> list[CallListItem]:
        """
        Add multiple projects to a user's call list.

        Duplicates are silently ignored (based on unique constraint).

        Args:
            user_id: Cognito user ID
            project_ids: List of project/job IDs to add

        Returns:
            list[CallListItem]: List of created call list items (excludes duplicates)
        """
        if not project_ids:
            logger.debug(f"[CallListRepository] No project IDs provided for user {user_id}")
            return []

        # Get current max position for this user
        stmt = (
            select(CallListItem.position)
            .where(CallListItem.user_id == user_id)
            .order_by(desc(CallListItem.position))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        max_position = result.scalar_one_or_none()
        next_position = (max_position or -1) + 1

        created_items = []
        for i, project_id in enumerate(project_ids):
            try:
                item = CallListItem(
                    user_id=user_id,
                    project_id=project_id,
                    call_completed=False,
                    position=next_position + i,
                )
                self.session.add(item)
                await self.session.flush()  # Get the ID without committing
                await self.session.refresh(item)
                created_items.append(item)

                logger.debug(
                    f"[CallListRepository] Added item: id={item.id}, user_id={user_id}, project_id={project_id}"
                )
            except IntegrityError:
                # Duplicate (user_id, project_id) - skip it
                await self.session.rollback()
                logger.debug(
                    f"[CallListRepository] Skipped duplicate project {project_id} for user {user_id}"
                )

        logger.info(
            f"[CallListRepository] Added {len(created_items)}/{len(project_ids)} items to call list for user {user_id}"
        )
        return created_items

    async def get_call_list(self, user_id: str) -> list[CallListItem]:
        """
        Get all items in a user's call list, ordered by position.

        Args:
            user_id: Cognito user ID

        Returns:
            list[CallListItem]: List of call list items ordered by position
        """
        stmt = (
            select(CallListItem)
            .where(CallListItem.user_id == user_id)
            .order_by(CallListItem.position)
        )

        result = await self.session.execute(stmt)
        items = list(result.scalars().all())

        logger.debug(
            f"[CallListRepository] Retrieved {len(items)} call list items for user {user_id}"
        )
        return items

    async def remove_item(self, user_id: str, project_id: str) -> bool:
        """
        Remove a specific project from a user's call list.

        Args:
            user_id: Cognito user ID
            project_id: Project/job ID to remove

        Returns:
            bool: True if item was removed, False if not found
        """
        stmt = delete(CallListItem).where(
            CallListItem.user_id == user_id,
            CallListItem.project_id == project_id,
        )

        result = await self.session.execute(stmt)
        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(
                f"[CallListRepository] Removed project {project_id} from call list for user {user_id}"
            )
            return True

        logger.debug(
            f"[CallListRepository] Project {project_id} not found in call list for user {user_id}"
        )
        return False

    async def clear_list(self, user_id: str) -> int:
        """
        Remove all items from a user's call list.

        Args:
            user_id: Cognito user ID

        Returns:
            int: Number of items removed
        """
        stmt = delete(CallListItem).where(CallListItem.user_id == user_id)

        result = await self.session.execute(stmt)
        deleted_count = result.rowcount

        logger.info(
            f"[CallListRepository] Cleared {deleted_count} items from call list for user {user_id}"
        )
        return deleted_count

    async def reorder_items(
        self, user_id: str, project_id_order: list[str]
    ) -> list[CallListItem]:
        """
        Reorder items in a user's call list.

        Updates the position field for each item based on the provided order.

        Args:
            user_id: Cognito user ID
            project_id_order: List of project IDs in desired order

        Returns:
            list[CallListItem]: Updated call list items in new order

        Raises:
            ValueError: If project_id_order contains IDs not in the user's call list
        """
        # Get all current items
        current_items = await self.get_call_list(user_id)
        current_project_ids = {item.project_id for item in current_items}

        # Validate that all provided IDs exist in the call list
        provided_project_ids = set(project_id_order)
        if not provided_project_ids.issubset(current_project_ids):
            invalid_ids = provided_project_ids - current_project_ids
            raise ValueError(
                f"Cannot reorder: project IDs not in call list: {invalid_ids}"
            )

        # Update positions
        for new_position, project_id in enumerate(project_id_order):
            stmt = (
                select(CallListItem)
                .where(CallListItem.user_id == user_id)
                .where(CallListItem.project_id == project_id)
            )
            result = await self.session.execute(stmt)
            item = result.scalar_one_or_none()

            if item:
                item.position = new_position
                item.updated_at = datetime.now(UTC)

        await self.session.flush()

        # Return updated list
        updated_items = await self.get_call_list(user_id)
        logger.info(
            f"[CallListRepository] Reordered {len(updated_items)} items for user {user_id}"
        )
        return updated_items

    async def mark_call_completed(
        self, user_id: str, project_id: str, completed: bool = True
    ) -> CallListItem | None:
        """
        Mark a call as completed or not completed.

        Args:
            user_id: Cognito user ID
            project_id: Project/job ID
            completed: Whether the call is completed (default: True)

        Returns:
            CallListItem | None: Updated item if found, None otherwise
        """
        stmt = (
            select(CallListItem)
            .where(CallListItem.user_id == user_id)
            .where(CallListItem.project_id == project_id)
        )
        result = await self.session.execute(stmt)
        item = result.scalar_one_or_none()

        if not item:
            logger.warning(
                f"[CallListRepository] Cannot mark call completed: "
                f"project {project_id} not found in call list for user {user_id}"
            )
            return None

        item.call_completed = completed
        item.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(item)

        logger.info(
            f"[CallListRepository] Marked call as {'completed' if completed else 'not completed'}: "
            f"project_id={project_id}, user_id={user_id}"
        )
        return item
