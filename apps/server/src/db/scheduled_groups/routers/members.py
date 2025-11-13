"""
Router for scheduled group member operations.

Handles adding projects to groups, removing them, and marking goals as completed.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.dependencies import get_scheduled_groups_repository
from src.db.scheduled_groups.decorators import handle_db_errors
from src.db.scheduled_groups.repository import ScheduledGroupsRepository
from src.db.scheduled_groups.schemas import (
    AddProjectsToGroupRequest,
    ScheduledGroupDetailResponse,
    ScheduledGroupMemberResponse,
)

router = APIRouter()


async def _build_detail_response(group, members) -> ScheduledGroupDetailResponse:
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


@router.post(
    "/{group_id}/members",
    response_model=ScheduledGroupDetailResponse,
    status_code=HTTPStatus.CREATED,
)
@handle_db_errors("add projects to group")
async def add_projects_to_group(
    group_id: int,
    request: AddProjectsToGroupRequest,
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> ScheduledGroupDetailResponse:
    """Add projects to a scheduled group."""
    group = await repository.get_group(group_id, current_user.id)

    if not group:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Scheduled group {group_id} not found",
        )

    await repository.add_members(
        group_id=group_id, user_id=current_user.id, project_ids=request.project_ids
    )

    await repository.session.commit()

    # Get updated group with members
    members = await repository.get_group_members(group_id, current_user.id)

    return await _build_detail_response(group, members)


@router.delete("/{group_id}/members/{project_id}", status_code=HTTPStatus.NO_CONTENT)
@handle_db_errors("remove project from group")
async def remove_project_from_group(
    group_id: int,
    project_id: str,
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> None:
    """Remove a project from a scheduled group."""
    removed = await repository.remove_member(
        group_id=group_id, user_id=current_user.id, project_id=project_id
    )

    if not removed:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Project {project_id} not found in group {group_id}",
        )

    await repository.session.commit()


@router.patch(
    "/{group_id}/members/{project_id}/completed",
    response_model=ScheduledGroupMemberResponse,
)
@handle_db_errors("mark goal completed")
async def mark_goal_completed(
    group_id: int,
    project_id: str,
    completed: bool = True,
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> ScheduledGroupMemberResponse:
    """Mark goal as completed for a project in a group."""
    member = await repository.mark_goal_completed(
        group_id=group_id,
        user_id=current_user.id,
        project_id=project_id,
        completed=completed,
    )

    if not member:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Project {project_id} not found in group {group_id}",
        )

    await repository.session.commit()

    return ScheduledGroupMemberResponse(
        id=member.id,
        group_id=member.group_id,
        project_id=member.project_id,
        goal_completed=member.goal_completed,
        goal_completed_at=member.goal_completed_at,
        added_at=member.added_at,
    )
