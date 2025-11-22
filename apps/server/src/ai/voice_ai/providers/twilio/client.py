"""
Twilio client wrapper for async operations.

This module provides async wrappers around the synchronous Twilio SDK.
"""

import asyncio
from typing import Any

import httpx
from twilio.rest import Client
from twilio.rest.api.v2010.account.call import CallInstance

from src.utils.logger import logger


class TwilioVoiceClient:
    """Async wrapper for Twilio Voice API operations."""

    def __init__(self, client: Client):
        """
        Initialize client wrapper.

        Args:
            client: Configured Twilio REST client
        """
        self.client = client

    async def create_call(
        self,
        to: str,
        from_: str,
        url: str,
        status_callback: str | None = None,
        status_callback_method: str = "POST",
        record: bool = False,
        recording_status_callback: str | None = None,
        **kwargs: Any,
    ) -> CallInstance:
        """
        Create an outbound call asynchronously.

        Args:
            to: Phone number to call (E.164 format)
            from_: Twilio phone number to call from
            url: TwiML URL for call instructions
            status_callback: URL for call status updates
            status_callback_method: HTTP method for status callback
            record: Whether to record the call
            recording_status_callback: URL for recording status
            **kwargs: Additional Twilio call parameters

        Returns:
            CallInstance from Twilio SDK
        """
        # Build call parameters, only include recording params if enabled
        call_params = {
            "to": to,
            "from_": from_,
            "url": url,
            **kwargs,
        }

        if status_callback:
            call_params["status_callback"] = status_callback
            call_params["status_callback_method"] = status_callback_method

        if record:
            call_params["record"] = True
            if recording_status_callback:
                call_params["recording_status_callback"] = recording_status_callback

        return await asyncio.to_thread(
            self.client.calls.create,
            **call_params,
        )

    async def get_call(self, call_sid: str) -> CallInstance:
        """
        Fetch call details asynchronously.

        Args:
            call_sid: Twilio Call SID

        Returns:
            CallInstance with current call details
        """
        return await asyncio.to_thread(self.client.calls(call_sid).fetch)

    async def update_call(self, call_sid: str, **kwargs: Any) -> CallInstance:
        """
        Update an ongoing call asynchronously.

        Args:
            call_sid: Twilio Call SID
            **kwargs: Call update parameters (e.g., status='completed')

        Returns:
            Updated CallInstance
        """
        return await asyncio.to_thread(
            self.client.calls(call_sid).update,
            **kwargs,
        )

    async def end_call(self, call_sid: str) -> CallInstance:
        """
        End an ongoing call asynchronously.

        Args:
            call_sid: Twilio Call SID

        Returns:
            Updated CallInstance with status 'completed'
        """
        return await self.update_call(call_sid, status="completed")

    async def create_conference_call(
        self,
        to: str,
        from_: str,
        conference_url: str,
        recording_callback: str,
        status_callback: str,
    ) -> CallInstance:
        """
        Create a call that joins a conference with recording.

        Args:
            to: Phone number to call
            from_: Twilio phone number to call from
            conference_url: TwiML URL for conference join
            recording_callback: URL for recording status
            status_callback: URL for call status

        Returns:
            CallInstance from Twilio SDK
        """
        return await self.create_call(
            to=to,
            from_=from_,
            url=conference_url,
            record=True,
            recording_status_callback=recording_callback,
            status_callback=status_callback,
        )

    async def download_recording(self, recording_url: str) -> tuple[bytes, str]:
        """
        Download a call recording from Twilio.

        Args:
            recording_url: URL to the Twilio recording

        Returns:
            Tuple of (file_bytes, content_type)

        Raises:
            Exception: If download fails
        """
        try:
            logger.info("[TWILIO] Downloading recording", url=recording_url)

            # Twilio API requires HTTP Basic Auth
            auth = (self.client.username, self.client.password)

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(recording_url, auth=auth)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "audio/mpeg")
                file_bytes = response.content

                logger.info(
                    "[TWILIO] Successfully downloaded recording",
                    url=recording_url,
                    size_bytes=len(file_bytes),
                    content_type=content_type,
                )

                return file_bytes, content_type

        except Exception as e:
            logger.error(
                "[TWILIO] Failed to download recording",
                url=recording_url,
                error=str(e),
            )
            raise
