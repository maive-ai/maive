"""
Dependencies for Twilio provider integration.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client

from src.ai.voice_ai.providers.twilio.client import TwilioVoiceClient
from src.ai.voice_ai.providers.twilio.config import TwilioGlobalConfig
from src.ai.voice_ai.providers.twilio.provider import TwilioProvider
from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.database import get_db
from src.db.phone_numbers.service import PhoneNumberService


def get_twilio_client() -> Client:
    """
    Get global Twilio client (singleton, shared account).

    Returns:
        Configured Twilio REST client
    """
    config = TwilioGlobalConfig()
    return Client(config.account_sid, config.auth_token)


def get_twilio_voice_client() -> TwilioVoiceClient:
    """
    Get Twilio Voice client with async wrappers.

    Returns:
        TwilioVoiceClient with async methods
    """
    return TwilioVoiceClient(get_twilio_client())


async def get_user_phone_number(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> str | None:
    """
    Get phone number for current user.

    Returns None if not configured (safe for Vapi users).
    Caller should check and raise error if phone number is required.

    Args:
        current_user: Current authenticated user
        session: Database session

    Returns:
        User's phone number or None if not configured
    """
    service = PhoneNumberService(session)
    config = await service.get_phone_number(current_user.id)
    return config.phone_number if config else None
