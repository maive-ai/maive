"""
Router for scheduled groups API.

Handles all scheduled group operations including CRUD operations,
member management, and status updates.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.dependencies import get_scheduled_groups_repository
from src.db.scheduled_groups.decorators import handle_db_errors
from src.db.scheduled_groups.repository import ScheduledGroupsRepository
from src.db.scheduled_groups.response_builders import (
    build_detail_response,
    build_group_response,
)
from src.db.scheduled_groups.schemas import (
    AddProjectsToGroupRequest,
    CreateScheduledGroupRequest,
    ScheduledGroupDetailResponse,
    ScheduledGroupMemberResponse,
    ScheduledGroupResponse,
    ScheduledGroupsListResponse,
    UpdateGroupStatusRequest,
    UpdateScheduledGroupRequest,
)

router = APIRouter(prefix="/scheduled-groups", tags=["Scheduled Groups"])


# ============================================================================
# Group CRUD Operations
# ============================================================================


@router.post("/", response_model=ScheduledGroupResponse, status_code=HTTPStatus.CREATED)
@handle_db_errors("create scheduled group")
async def create_scheduled_group(
    request: CreateScheduledGroupRequest,
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> ScheduledGroupResponse:
    """Create a new scheduled group."""
    # Validate goal_description for user_specified goal type
    if request.goal_type == "user_specified" and not request.goal_description:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="goal_description is required when goal_type is user_specified",
        )

    group = await repository.create_group(
        user_id=current_user.id,
        name=request.name,
        frequency=request.frequency,
        time_of_day=request.time_of_day,
        goal_type=request.goal_type.value,
        goal_description=request.goal_description,
        who_to_call=request.who_to_call.value,
    )

    await repository.session.commit()

    return await build_group_response(group, repository)


@router.get("/", response_model=ScheduledGroupsListResponse)
@handle_db_errors("list scheduled groups")
async def list_scheduled_groups(
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> ScheduledGroupsListResponse:
    """List all scheduled groups for the user."""
    groups = await repository.list_user_groups(current_user.id)

    group_responses = [
        await build_group_response(group, repository) for group in groups
    ]

    return ScheduledGroupsListResponse(
        groups=group_responses, total=len(group_responses)
    )


@router.get("/{group_id}", response_model=ScheduledGroupDetailResponse)
@handle_db_errors("get scheduled group")
async def get_scheduled_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> ScheduledGroupDetailResponse:
    """Get a scheduled group with its members."""
    group = await repository.get_group(group_id, current_user.id)

    if not group:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Scheduled group {group_id} not found",
        )

    members = await repository.get_group_members(group_id, current_user.id)

    return await build_detail_response(group, members)


@router.put("/{group_id}", response_model=ScheduledGroupResponse)
@handle_db_errors("update scheduled group")
async def update_scheduled_group(
    group_id: int,
    request: UpdateScheduledGroupRequest,
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> ScheduledGroupResponse:
    """Update a scheduled group."""
    group = await repository.get_group(group_id, current_user.id)

    if not group:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Scheduled group {group_id} not found",
        )

    # Determine final goal_type and goal_description after update
    final_goal_type = request.goal_type.value if request.goal_type else group.goal_type
    final_goal_description = (
        request.goal_description
        if request.goal_description is not None
        else group.goal_description
    )

    # Validate goal_description for user_specified goal type
    if final_goal_type == "user_specified" and not final_goal_description:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="goal_description is required when goal_type is user_specified",
        )

    group = await repository.update_group(
        group_id=group_id,
        user_id=current_user.id,
        name=request.name,
        frequency=request.frequency,
        time_of_day=request.time_of_day,
        goal_type=request.goal_type.value if request.goal_type else None,
        goal_description=request.goal_description,
        who_to_call=request.who_to_call.value if request.who_to_call else None,
    )

    await repository.session.commit()

    return await build_group_response(group, repository)


@router.delete("/{group_id}", status_code=HTTPStatus.NO_CONTENT)
@handle_db_errors("delete scheduled group")
async def delete_scheduled_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> None:
    """Delete a scheduled group."""
    deleted = await repository.delete_group(group_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Scheduled group {group_id} not found",
        )

    await repository.session.commit()


@router.patch("/{group_id}/active", response_model=ScheduledGroupResponse)
@handle_db_errors("toggle group active status")
async def toggle_group_active(
    group_id: int,
    request: UpdateGroupStatusRequest,
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> ScheduledGroupResponse:
    """Start or stop a scheduled group."""
    group = await repository.toggle_group_active(
        group_id=group_id,
        user_id=current_user.id,
        is_active=request.is_active,
    )

    if not group:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Scheduled group {group_id} not found",
        )

    await repository.session.commit()

    return await build_group_response(group, repository)


# ============================================================================
# Member Management Operations
# ============================================================================


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

    return await build_detail_response(group, members)


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
