"""
Phone number API endpoints.

This module provides endpoints for assigning and managing phone
numbers for users.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.phone_numbers.dependencies import get_phone_number_service
from src.db.phone_numbers.schemas import PhoneNumberCreate, PhoneNumberResponse
from src.db.phone_numbers.service import PhoneNumberService

router = APIRouter(prefix="/phone-numbers", tags=["Phone Numbers"])


@router.post(
    "", response_model=PhoneNumberResponse, status_code=status.HTTP_201_CREATED
)
async def assign_phone_number(
    data: PhoneNumberCreate,
    current_user: User = Depends(get_current_user),
    service: PhoneNumberService = Depends(get_phone_number_service),
) -> PhoneNumberResponse:
    """
    Assign phone number to current user.

    Args:
        data: Phone number assignment data
        current_user: Current authenticated user
        service: Phone number service

    Returns:
        Created or updated configuration

    Raises:
        HTTPException: If assignment fails
    """
    config = await service.assign_phone_number(
        user_id=current_user.id,
        phone_number=data.phone_number,
    )
    await service.session.commit()
    return PhoneNumberResponse.model_validate(config)


@router.get("", response_model=PhoneNumberResponse)
async def get_phone_number(
    current_user: User = Depends(get_current_user),
    service: PhoneNumberService = Depends(get_phone_number_service),
) -> PhoneNumberResponse:
    """
    Get phone number for current user.

    Args:
        current_user: Current authenticated user
        service: Phone number service

    Returns:
        User's phone number configuration

    Raises:
        HTTPException: If no phone number is configured
    """
    config = await service.get_phone_number(current_user.id)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No phone number configured"
        )
    return PhoneNumberResponse.model_validate(config)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phone_number(
    current_user: User = Depends(get_current_user),
    service: PhoneNumberService = Depends(get_phone_number_service),
) -> None:
    """
    Remove phone number assignment for current user.

    Args:
        current_user: Current authenticated user
        service: Phone number service
    """
    config = await service.get_phone_number(current_user.id)
    if config:
        await service.session.delete(config)
        await service.session.commit()
