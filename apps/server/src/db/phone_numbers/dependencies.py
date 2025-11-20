"""
Dependencies for phone number endpoints.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db.phone_numbers.service import PhoneNumberService


async def get_phone_number_service(
    session: AsyncSession = Depends(get_db),
) -> PhoneNumberService:
    """Get phone number service instance."""
    return PhoneNumberService(session)
