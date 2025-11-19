"""
Repository for scheduled groups database operations.

Provides CRUD operations for ScheduledGroup and ScheduledGroupMember records using SQLAlchemy async sessions.
"""

from datetime import UTC, datetime, time

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.scheduled_groups.model import ScheduledGroup, ScheduledGroupMember
from src.utils.logger import logger


class ScheduledGroupsRepository:
    """Repository for managing scheduled groups in the database."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create_group(
        self,
        user_id: str,
        name: str,
        frequency: list[str],
        time_of_day: time,
        goal_type: str,
        goal_description: str | None,
        who_to_call: str,
    ) -> ScheduledGroup:
        """
        Create a new scheduled group.

        Args:
            user_id: Cognito user ID
            name: Group display name
            frequency: Days of week list
            time_of_day: Time of day to make calls
            goal_type: Type of goal
            goal_description: Optional goal description
            who_to_call: Who to call

        Returns:
            ScheduledGroup: Created group
        """
        group = ScheduledGroup(
            user_id=user_id,
            name=name,
            frequency=frequency,
            time_of_day=time_of_day,
            goal_type=goal_type,
            goal_description=goal_description,
            who_to_call=who_to_call,
            is_active=False,
        )
        self.session.add(group)
        await self.session.flush()
        await self.session.refresh(group)

        logger.info(
            "[ScheduledGroupsRepository] Created group",
            id=group.id,
            user_id=user_id,
            name=name,
        )
        return group

    async def get_group(self, group_id: int, user_id: str) -> ScheduledGroup | None:
        """
        Get a scheduled group by ID, ensuring it belongs to the user.

        Args:
            group_id: Group ID
            user_id: Cognito user ID

        Returns:
            ScheduledGroup | None: Group if found, None otherwise
        """
        stmt = select(ScheduledGroup).where(
            ScheduledGroup.id == group_id, ScheduledGroup.user_id == user_id
        )
        result = await self.session.execute(stmt)
        group = result.scalar_one_or_none()

        if group:
            logger.debug(
                "[ScheduledGroupsRepository] Retrieved group",
                group_id=group_id,
                user_id=user_id,
            )
        else:
            logger.debug(
                "[ScheduledGroupsRepository] Group not found",
                group_id=group_id,
                user_id=user_id,
            )

        return group

    async def list_user_groups(self, user_id: str) -> list[ScheduledGroup]:
        """
        List all scheduled groups for a user.

        Args:
            user_id: Cognito user ID

        Returns:
            list[ScheduledGroup]: List of groups
        """
        stmt = (
            select(ScheduledGroup)
            .where(ScheduledGroup.user_id == user_id)
            .order_by(ScheduledGroup.created_at.desc())
        )
        result = await self.session.execute(stmt)
        groups = list(result.scalars().all())

        logger.debug(
            "[ScheduledGroupsRepository] Retrieved groups for user",
            count=len(groups),
            user_id=user_id,
        )
        return groups

    async def update_group(
        self,
        group_id: int,
        user_id: str,
        name: str | None = None,
        frequency: list[str] | None = None,
        time_of_day: time | None = None,
        goal_type: str | None = None,
        goal_description: str | None = None,
        who_to_call: str | None = None,
    ) -> ScheduledGroup | None:
        """
        Update a scheduled group.

        Args:
            group_id: Group ID
            user_id: Cognito user ID
            name: Optional new name
            frequency: Optional new frequency
            time_of_day: Optional new time
            goal_type: Optional new goal type
            goal_description: Optional new goal description
            who_to_call: Optional new who_to_call

        Returns:
            ScheduledGroup | None: Updated group if found, None otherwise
        """
        group = await self.get_group(group_id, user_id)
        if not group:
            return None

        if name is not None:
            group.name = name
        if frequency is not None:
            group.frequency = frequency
        if time_of_day is not None:
            group.time_of_day = time_of_day
        if goal_type is not None:
            group.goal_type = goal_type
        if goal_description is not None:
            group.goal_description = goal_description
        if who_to_call is not None:
            group.who_to_call = who_to_call

        group.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(group)

        logger.info(
            "[ScheduledGroupsRepository] Updated group",
            group_id=group_id,
            user_id=user_id,
        )
        return group

    async def delete_group(self, group_id: int, user_id: str) -> bool:
        """
        Delete a scheduled group.

        Args:
            group_id: Group ID
            user_id: Cognito user ID

        Returns:
            bool: True if deleted, False if not found
        """
        group = await self.get_group(group_id, user_id)
        if not group:
            return False

        await self.session.delete(group)
        await self.session.flush()

        logger.info(
            "[ScheduledGroupsRepository] Deleted group",
            group_id=group_id,
            user_id=user_id,
        )
        return True

    async def toggle_group_active(
        self, group_id: int, user_id: str, is_active: bool
    ) -> ScheduledGroup | None:
        """
        Toggle group active status.

        Args:
            group_id: Group ID
            user_id: Cognito user ID
            is_active: New active status

        Returns:
            ScheduledGroup | None: Updated group if found, None otherwise
        """
        group = await self.get_group(group_id, user_id)
        if not group:
            return None

        group.is_active = is_active
        group.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(group)

        logger.info(
            "[ScheduledGroupsRepository] Toggled group active",
            group_id=group_id,
            user_id=user_id,
            is_active=is_active,
        )
        return group

    async def add_members(
        self, group_id: int, user_id: str, project_ids: list[str]
    ) -> list[ScheduledGroupMember]:
        """
        Add multiple projects to a group.

        Duplicates are silently ignored (based on unique constraint).

        Args:
            group_id: Group ID
            user_id: Cognito user ID
            project_ids: List of project/job IDs to add

        Returns:
            list[ScheduledGroupMember]: List of created members (excludes duplicates)
        """
        # Verify group belongs to user
        group = await self.get_group(group_id, user_id)
        if not group:
            return []

        if not project_ids:
            logger.debug(
                "[ScheduledGroupsRepository] No project IDs provided for group",
                group_id=group_id,
            )
            return []

        # Check for existing members to avoid duplicates
        existing_stmt = (
            select(ScheduledGroupMember.project_id)
            .where(ScheduledGroupMember.group_id == group_id)
            .where(ScheduledGroupMember.project_id.in_(project_ids))
        )
        existing_result = await self.session.execute(existing_stmt)
        existing_project_ids = {row[0] for row in existing_result.all()}

        created_members = []
        for project_id in project_ids:
            # Skip if already exists
            if project_id in existing_project_ids:
                logger.debug(
                    "[ScheduledGroupsRepository] Skipped duplicate project",
                    project_id=project_id,
                    group_id=group_id,
                )
                continue

            member = ScheduledGroupMember(
                group_id=group_id,
                project_id=project_id,
                goal_completed=False,
            )
            self.session.add(member)
            created_members.append(member)

            logger.debug(
                "[ScheduledGroupsRepository] Added member",
                group_id=group_id,
                project_id=project_id,
            )

        # Flush to get IDs for all members
        if created_members:
            await self.session.flush()
            for member in created_members:
                await self.session.refresh(member)

        logger.info(
            "[ScheduledGroupsRepository] Added members to group",
            created_count=len(created_members),
            total_count=len(project_ids),
            group_id=group_id,
        )
        return created_members

    async def remove_member(self, group_id: int, user_id: str, project_id: str) -> bool:
        """
        Remove a project from a group.

        Args:
            group_id: Group ID
            user_id: Cognito user ID
            project_id: Project/job ID to remove

        Returns:
            bool: True if removed, False if not found
        """
        # Verify group belongs to user
        group = await self.get_group(group_id, user_id)
        if not group:
            return False

        stmt = delete(ScheduledGroupMember).where(
            ScheduledGroupMember.group_id == group_id,
            ScheduledGroupMember.project_id == project_id,
        )

        result = await self.session.execute(stmt)
        deleted_count = result.rowcount

        if deleted_count > 0:
            logger.info(
                "[ScheduledGroupsRepository] Removed project from group",
                project_id=project_id,
                group_id=group_id,
            )
            return True

        logger.debug(
            "[ScheduledGroupsRepository] Project not found in group",
            project_id=project_id,
            group_id=group_id,
        )
        return False

    async def get_group_members(
        self, group_id: int, user_id: str
    ) -> list[ScheduledGroupMember]:
        """
        Get all members of a group.

        Args:
            group_id: Group ID
            user_id: Cognito user ID

        Returns:
            list[ScheduledGroupMember]: List of members
        """
        # Verify group belongs to user
        group = await self.get_group(group_id, user_id)
        if not group:
            return []

        stmt = select(ScheduledGroupMember).where(
            ScheduledGroupMember.group_id == group_id
        )
        result = await self.session.execute(stmt)
        members = list(result.scalars().all())

        logger.debug(
            "[ScheduledGroupsRepository] Retrieved members for group",
            count=len(members),
            group_id=group_id,
        )
        return members

    async def mark_goal_completed(
        self, group_id: int, user_id: str, project_id: str, completed: bool = True
    ) -> ScheduledGroupMember | None:
        """
        Mark goal as completed for a group member.

        Args:
            group_id: Group ID
            user_id: Cognito user ID
            project_id: Project/job ID
            completed: Whether goal is completed (default: True)

        Returns:
            ScheduledGroupMember | None: Updated member if found, None otherwise
        """
        # Verify group belongs to user
        group = await self.get_group(group_id, user_id)
        if not group:
            return None

        stmt = select(ScheduledGroupMember).where(
            ScheduledGroupMember.group_id == group_id,
            ScheduledGroupMember.project_id == project_id,
        )
        result = await self.session.execute(stmt)
        member = result.scalar_one_or_none()

        if not member:
            logger.warning(
                "[ScheduledGroupsRepository] Cannot mark goal completed: project not found",
                project_id=project_id,
                group_id=group_id,
            )
            return None

        member.goal_completed = completed
        if completed:
            member.goal_completed_at = datetime.now(UTC)
        else:
            member.goal_completed_at = None

        await self.session.flush()
        await self.session.refresh(member)

        logger.info(
            "[ScheduledGroupsRepository] Marked goal completed status",
            completed=completed,
            group_id=group_id,
            project_id=project_id,
        )
        return member

    async def get_member_count(self, group_id: int) -> int:
        """
        Get the number of members in a group.

        Args:
            group_id: Group ID

        Returns:
            int: Number of members
        """
        stmt = select(func.count(ScheduledGroupMember.id)).where(
            ScheduledGroupMember.group_id == group_id
        )
        result = await self.session.execute(stmt)
        count = result.scalar_one() or 0

        return count
