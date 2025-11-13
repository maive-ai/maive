"""
Router for scheduled group CRUD operations.

Handles creating, reading, updating, and deleting scheduled groups.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.dependencies import get_scheduled_groups_repository
from src.db.scheduled_groups.decorators import handle_db_errors
from src.db.scheduled_groups.repository import ScheduledGroupsRepository
from src.db.scheduled_groups.schemas import (
    CreateScheduledGroupRequest,
    ScheduledGroupDetailResponse,
    ScheduledGroupResponse,
    ScheduledGroupsListResponse,
    UpdateGroupStatusRequest,
    UpdateScheduledGroupRequest,
)

router = APIRouter()


async def _build_group_response(
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

    return await _build_group_response(group, repository)


@router.get("/", response_model=ScheduledGroupsListResponse)
@handle_db_errors("list scheduled groups")
async def list_scheduled_groups(
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> ScheduledGroupsListResponse:
    """List all scheduled groups for the user."""
    groups = await repository.list_user_groups(current_user.id)

    group_responses = [
        await _build_group_response(group, repository) for group in groups
    ]

    return ScheduledGroupsListResponse(groups=group_responses, total=len(group_responses))


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

    from src.db.scheduled_groups.router import _build_detail_response

    return await _build_detail_response(group, members)


@router.put("/{group_id}", response_model=ScheduledGroupResponse)
@handle_db_errors("update scheduled group")
async def update_scheduled_group(
    group_id: int,
    request: UpdateScheduledGroupRequest,
    current_user: User = Depends(get_current_user),
    repository: ScheduledGroupsRepository = Depends(get_scheduled_groups_repository),
) -> ScheduledGroupResponse:
    """Update a scheduled group."""
    # Validate goal_description for user_specified goal type
    if request.goal_type == "user_specified" and not request.goal_description:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="goal_description is required when goal_type is user_specified",
        )

    group = await repository.get_group(group_id, current_user.id)

    if not group:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Scheduled group {group_id} not found",
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

    return await _build_group_response(group, repository)


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

    return await _build_group_response(group, repository)
