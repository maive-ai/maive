"""
Call list router with endpoints for managing user call queues.

This module contains all the API endpoints for call list operations,
including adding projects, removing projects, and querying the call list.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.call_list.repository import CallListRepository
from src.db.call_list.schemas import (
    AddToCallListRequest,
    CallListItemResponse,
    CallListResponse,
    MarkCallCompletedRequest,
)
from src.db.dependencies import get_call_list_repository

router = APIRouter(prefix="/call-list", tags=["Call List"])


@router.post("/add", response_model=CallListResponse, status_code=HTTPStatus.CREATED)
async def add_to_call_list(
    request: AddToCallListRequest,
    current_user: User = Depends(get_current_user),
    call_list_repository: CallListRepository = Depends(get_call_list_repository),
) -> CallListResponse:
    """
    Add projects to the user's call list.

    Adds multiple projects to the authenticated user's call list.
    Duplicate projects are silently ignored.

    Args:
        request: Request containing list of project IDs to add
        current_user: The authenticated user
        call_list_repository: The call list repository instance from dependency injection

    Returns:
        CallListResponse: The updated call list

    Raises:
        HTTPException: If an error occurs adding projects
    """
    try:
        # Add items to call list
        await call_list_repository.add_items(
            user_id=current_user.id,
            project_ids=request.project_ids,
        )

        # Commit the transaction
        await call_list_repository.session.commit()

        # Get updated call list
        items = await call_list_repository.get_call_list(current_user.id)

        return CallListResponse(
            items=[
                CallListItemResponse(
                    id=item.id,
                    user_id=item.user_id,
                    project_id=item.project_id,
                    call_completed=item.call_completed,
                    position=item.position,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in items
            ],
            total=len(items),
        )

    except Exception as e:
        await call_list_repository.session.rollback()
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to add projects to call list: {str(e)}",
        )


@router.get("", response_model=CallListResponse)
async def get_call_list(
    current_user: User = Depends(get_current_user),
    call_list_repository: CallListRepository = Depends(get_call_list_repository),
) -> CallListResponse:
    """
    Get the user's call list.

    Returns all items in the authenticated user's call list, ordered by position.

    Args:
        current_user: The authenticated user
        call_list_repository: The call list repository instance from dependency injection

    Returns:
        CallListResponse: The user's call list

    Raises:
        HTTPException: If an error occurs retrieving the call list
    """
    try:
        items = await call_list_repository.get_call_list(current_user.id)

        return CallListResponse(
            items=[
                CallListItemResponse(
                    id=item.id,
                    user_id=item.user_id,
                    project_id=item.project_id,
                    call_completed=item.call_completed,
                    position=item.position,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in items
            ],
            total=len(items),
        )

    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve call list: {str(e)}",
        )


@router.delete("/{project_id}", status_code=HTTPStatus.NO_CONTENT)
async def remove_from_call_list(
    project_id: str,
    current_user: User = Depends(get_current_user),
    call_list_repository: CallListRepository = Depends(get_call_list_repository),
) -> None:
    """
    Remove a project from the user's call list.

    Args:
        project_id: The project ID to remove
        current_user: The authenticated user
        call_list_repository: The call list repository instance from dependency injection

    Raises:
        HTTPException: If the project is not found or an error occurs
    """
    try:
        removed = await call_list_repository.remove_item(
            user_id=current_user.id,
            project_id=project_id,
        )

        if not removed:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Project {project_id} not found in call list",
            )

        await call_list_repository.session.commit()

    except HTTPException:
        raise
    except Exception as e:
        await call_list_repository.session.rollback()
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove project from call list: {str(e)}",
        )


@router.delete("", status_code=HTTPStatus.NO_CONTENT)
async def clear_call_list(
    current_user: User = Depends(get_current_user),
    call_list_repository: CallListRepository = Depends(get_call_list_repository),
) -> None:
    """
    Clear all items from the user's call list.

    Args:
        current_user: The authenticated user
        call_list_repository: The call list repository instance from dependency injection

    Raises:
        HTTPException: If an error occurs clearing the call list
    """
    try:
        await call_list_repository.clear_list(current_user.id)
        await call_list_repository.session.commit()

    except Exception as e:
        await call_list_repository.session.rollback()
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear call list: {str(e)}",
        )

@router.patch("/{project_id}/completed", response_model=CallListItemResponse)
async def mark_call_completed(
    project_id: str,
    request: MarkCallCompletedRequest,
    current_user: User = Depends(get_current_user),
    call_list_repository: CallListRepository = Depends(get_call_list_repository),
) -> CallListItemResponse:
    """
    Mark a call as completed or not completed.

    Args:
        project_id: The project ID to update
        request: Request containing completion status
        current_user: The authenticated user
        call_list_repository: The call list repository instance from dependency injection

    Returns:
        CallListItemResponse: The updated call list item

    Raises:
        HTTPException: If the project is not found or an error occurs
    """
    try:
        item = await call_list_repository.mark_call_completed(
            user_id=current_user.id,
            project_id=project_id,
            completed=request.completed,
        )

        if not item:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"Project {project_id} not found in call list",
            )

        await call_list_repository.session.commit()

        return CallListItemResponse(
            id=item.id,
            user_id=item.user_id,
            project_id=item.project_id,
            call_completed=item.call_completed,
            position=item.position,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        await call_list_repository.session.rollback()
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark call as completed: {str(e)}",
        )