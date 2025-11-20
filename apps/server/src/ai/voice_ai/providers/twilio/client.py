"""
Twilio client wrapper for async operations.

This module provides async wrappers around the synchronous Twilio SDK.
"""

import asyncio
from typing import Any

from twilio.rest import Client
from twilio.rest.api.v2010.account.call import CallInstance


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
