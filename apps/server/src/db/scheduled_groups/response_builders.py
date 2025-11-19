"""
Shared response builder functions for scheduled groups API.

Contains helper functions to convert database models into API response schemas.
"""

from src.db.scheduled_groups.repository import ScheduledGroupsRepository
from src.db.scheduled_groups.schemas import (
    ScheduledGroupDetailResponse,
    ScheduledGroupMemberResponse,
    ScheduledGroupResponse,
)


async def build_group_response(
    group, repository: ScheduledGroupsRepository
) -> ScheduledGroupResponse:
    """Build a ScheduledGroupResponse from a ScheduledGroup model."""
    member_count = await repository.get_member_count(group.id)

    return ScheduledGroupResponse(
        id=group.id,
        user_id=group.user_id,
        name=group.name,
        frequency=group.frequency,
        time_of_day=group.time_of_day.strftime("%H:%M:%S"),
        goal_type=group.goal_type,
        goal_description=group.goal_description,
        who_to_call=group.who_to_call,
        is_active=group.is_active,
        member_count=member_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


async def build_detail_response(group, members) -> ScheduledGroupDetailResponse:
    """Build a ScheduledGroupDetailResponse from a ScheduledGroup model and its members."""
    return ScheduledGroupDetailResponse(
        id=group.id,
        user_id=group.user_id,
        name=group.name,
        frequency=group.frequency,
        time_of_day=group.time_of_day.strftime("%H:%M:%S"),
        goal_type=group.goal_type,
        goal_description=group.goal_description,
        who_to_call=group.who_to_call,
        is_active=group.is_active,
        members=[
            ScheduledGroupMemberResponse(
                id=member.id,
                group_id=member.group_id,
                project_id=member.project_id,
                goal_completed=member.goal_completed,
                goal_completed_at=member.goal_completed_at,
                added_at=member.added_at,
            )
            for member in members
        ],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )
