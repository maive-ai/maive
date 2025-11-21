"""
Twilio global configuration.

This module defines the global Twilio account configuration that is shared
across all tenants. Individual tenants have their own phone numbers configured
in the database.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.config import get_app_settings


class TwilioGlobalConfig(BaseSettings):
    """
    Global Twilio account configuration.

    These credentials are for YOUR Twilio account and are shared across
    all tenants. Each tenant gets their own phone number but uses the
    same account credentials.
    """

    model_config = SettingsConfigDict(env_prefix="TWILIO_")

    account_sid: str = Field(..., description="Twilio Account SID (ACxxx)")
    auth_token: str = Field(..., description="Twilio Auth Token")
    api_key: str = Field(..., description="Twilio API Key (SKxxx) for access tokens")
    api_secret: str = Field(..., description="Twilio API Secret for access tokens")


class TwilioWebhooks:
    """Twilio webhook URLs for callbacks."""

    def __init__(self):
        settings = get_app_settings()
        self._base_url = settings.server_base_url

    @property
    def status_callback(self) -> str:
        """URL for call status updates."""
        return f"{self._base_url}/api/voice-ai/twilio/webhooks/status"

    @property
    def recording_status_callback(self) -> str:
        """URL for recording availability."""
        return f"{self._base_url}/api/voice-ai/twilio/webhooks/recording"

    @property
    def bridge_callback(self) -> str:
        """URL for bridge callback when browser answers."""
        return f"{self._base_url}/api/voice-ai/twilio/webhooks/bridge"

    def twiml_url(self, conference_name: str = "default") -> str:
        """
        Get TwiML URL for joining a conference.

        Args:
            conference_name: Conference room name

        Returns:
            TwiML endpoint URL
        """
        return f"{self._base_url}/api/voice-ai/twilio/twiml/join-conference?conference_name={conference_name}"
