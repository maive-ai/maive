"""
Service layer for phone number management.
"""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.db.phone_numbers.model import UserPhoneNumber
from src.db.users.model import User


class PhoneNumberService:
    """Service for managing user phone number assignments."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def assign_phone_number(
        self,
        user_id: str,
        phone_number: str,
    ) -> UserPhoneNumber:
        """
        Assign a phone number to a user.

        Args:
            user_id: User ID to assign phone number to
            phone_number: Phone number in E.164 format

        Returns:
            Created or updated phone number record

        Raises:
            HTTPException: If user not found
        """
        # Verify user exists
        user_result = await self.session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if phone number already exists for this user
        existing = await self.get_phone_number(user_id)
        if existing:
            # Update existing
            existing.phone_number = phone_number
            existing.updated_at = datetime.now(UTC)
            await self.session.flush()
            return existing

        # Create new
        phone_config = UserPhoneNumber(
            user_id=user_id,
            phone_number=phone_number,
            created_by=user_id,
        )
        self.session.add(phone_config)
        await self.session.flush()
        await self.session.refresh(phone_config)
        return phone_config

    async def get_phone_number(self, user_id: str) -> UserPhoneNumber | None:
        """Get phone number config for user."""
        result = await self.session.execute(
            select(UserPhoneNumber)
            .where(UserPhoneNumber.user_id == user_id)
            .options(joinedload(UserPhoneNumber.user))
        )
        return result.scalar_one_or_none()
