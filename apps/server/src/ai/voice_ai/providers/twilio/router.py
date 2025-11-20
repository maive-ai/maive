"""
Twilio-specific Voice AI endpoints.

External callbacks and provider-specific endpoints for Twilio integration.
"""

from http import HTTPStatus

from fastapi import APIRouter, Depends, Form
from fastapi.responses import Response
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse

from src.ai.voice_ai.providers.twilio.config import TwilioGlobalConfig
from src.ai.voice_ai.providers.twilio.provider import map_twilio_status
from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.calls.repository import CallRepository
from src.db.dependencies import get_call_repository
from src.utils.logger import logger

router = APIRouter(prefix="/twilio", tags=["Voice AI - Twilio"])


@router.post("/webhooks/status")
async def status_webhook(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    call_repository: CallRepository = Depends(get_call_repository),
) -> Response:
    """Handle Twilio call status updates."""
    logger.info("[TWILIO] Status webhook", call_sid=CallSid, status=CallStatus)

    internal_status = map_twilio_status(CallStatus)

    await call_repository.update_call_status(call_id=CallSid, status=internal_status)
    await call_repository.session.commit()

    return Response(status_code=HTTPStatus.OK)


@router.post("/webhooks/recording")
async def recording_webhook(
    CallSid: str = Form(...),
    RecordingUrl: str = Form(...),
    call_repository: CallRepository = Depends(get_call_repository),
) -> Response:
    """Handle Twilio recording availability."""
    logger.info(
        "[TWILIO] Recording webhook", call_sid=CallSid, recording_url=RecordingUrl
    )

    # Twilio's RecordingUrl may be a resource URL without file extension.
    # Append .mp3 if no extension present to get the direct audio file download URL.
    if RecordingUrl.endswith((".mp3", ".wav", ".m4a")):
        recording_url_mp3 = RecordingUrl
    else:
        recording_url_mp3 = f"{RecordingUrl}.mp3"

    await call_repository.update_call_recording(
        call_id=CallSid, recording_url=recording_url_mp3
    )
    await call_repository.session.commit()

    return Response(status_code=HTTPStatus.OK)


@router.post("/twiml/join-conference")
async def twiml_join_conference(conference_name: str = "default"):
    """TwiML endpoint to join conference room."""
    twiml_response = VoiceResponse()
    dial = twiml_response.dial()
    dial.conference(
        conference_name,
        start_conference_on_enter=True,
        end_conference_on_exit=True,
        record="record-from-start",
        beep=False,
    )

    twiml_xml = str(twiml_response)
    logger.info("[TWILIO] Generated TwiML", conference=conference_name, twiml=twiml_xml)

    return Response(content=twiml_xml, media_type="application/xml")


@router.get("/token")
async def get_token(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    """Generate Twilio Access Token for browser calling."""
    config = TwilioGlobalConfig()

    token = AccessToken(
        config.account_sid,
        config.api_key,
        config.api_secret,
        identity=current_user.id,
        ttl=3600,
    )

    voice_grant = VoiceGrant(incoming_allow=True)
    token.add_grant(voice_grant)

    return {"token": token.to_jwt(), "identity": current_user.id}
