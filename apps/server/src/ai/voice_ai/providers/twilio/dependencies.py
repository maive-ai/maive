"""
Dependencies for Twilio provider integration.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.rest import Client

from src.ai.voice_ai.providers.twilio.client import TwilioVoiceClient
from src.ai.voice_ai.providers.twilio.config import TwilioGlobalConfig
from src.ai.voice_ai.providers.twilio.provider import TwilioProvider
from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.database import get_db
from src.db.twilio_config.service import TwilioConfigService


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


async def get_org_phone_number(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> str:
    """
    Get phone number for user's organization.

    Args:
        current_user: Current authenticated user
        session: Database session

    Returns:
        Organization's Twilio phone number

    Raises:
        HTTPException: If no phone number is configured
    """
    service = TwilioConfigService(session)
    return await service.get_phone_number(current_user.organization_id)


async def get_twilio_provider(
    client: Client = Depends(get_twilio_client),
    phone_number: str = Depends(get_org_phone_number),
) -> TwilioProvider:
    """
    Create TwilioProvider with global client + org phone.

    Args:
        client: Global Twilio client
        phone_number: Organization's phone number

    Returns:
        Configured TwilioProvider instance
    """
    return TwilioProvider(client, phone_number)
