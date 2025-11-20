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

from src.ai.voice_ai.providers.twilio.client import TwilioVoiceClient
from src.ai.voice_ai.providers.twilio.config import TwilioGlobalConfig, TwilioWebhooks
from src.ai.voice_ai.providers.twilio.dependencies import get_twilio_voice_client
from src.ai.voice_ai.providers.twilio.provider import map_twilio_status
from src.auth.dependencies import get_current_user
from src.auth.schemas import User
from src.db.calls.repository import CallRepository
from src.db.dependencies import get_call_repository
from src.utils.logger import logger

router = APIRouter(prefix="/twilio", tags=["Twilio"])


@router.post("/webhooks/status", include_in_schema=False)
async def status_webhook(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    call_repository: CallRepository = Depends(get_call_repository),
) -> Response:
    """Handle Twilio call status updates."""
    logger.info("[TWILIO] Status webhook", call_sid=CallSid, status=CallStatus)

    internal_status = map_twilio_status(CallStatus)

    # Try to find call by CallSid (could be browser or customer call)
    call = await call_repository.get_call_by_call_id(CallSid)

    # If not found, it might be the customer call - look for it in provider_data
    if not call:
        call = await call_repository.get_call_by_customer_call_sid(CallSid)

        if call:
            logger.debug(
                "[TWILIO] Status webhook - found call by customer_call_sid",
                browser_call_sid=call.call_id,
                customer_call_sid=CallSid,
            )

    if call:
        await call_repository.update_call_status(
            call_id=call.call_id, status=internal_status
        )
        await call_repository.session.commit()
    else:
        logger.warning(
            "[TWILIO] Status webhook - call not found",
            call_sid=CallSid,
        )

    return Response(status_code=HTTPStatus.OK)


@router.post("/webhooks/bridge", include_in_schema=False)
async def bridge_webhook(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    call_repository: CallRepository = Depends(get_call_repository),
    twilio_client: TwilioVoiceClient = Depends(get_twilio_voice_client),
) -> Response:
    """
    Handle browser call answered - create customer call to bridge them.

    When browser answers, this webhook creates the customer call
    and bridges both into the same conference.
    """
    logger.info("[TWILIO] Bridge webhook", call_sid=CallSid, status=CallStatus)

    # Only proceed if browser answered
    if CallStatus != "in-progress":
        logger.info(
            "[TWILIO] Bridge webhook - browser not answered yet",
            call_sid=CallSid,
            status=CallStatus,
        )
        return Response(status_code=HTTPStatus.OK)

    # Fetch call from database to get conference and customer info
    call = await call_repository.get_call_by_call_id(CallSid)
    if not call:
        logger.warning("[TWILIO] Bridge webhook - call not found", call_sid=CallSid)
        return Response(status_code=HTTPStatus.OK)

    # Extract conference and customer phone from provider_data
    if not call.provider_data:
        logger.warning("[TWILIO] Bridge webhook - no provider_data", call_sid=CallSid)
        return Response(status_code=HTTPStatus.OK)

    logger.debug(
        "[TWILIO] Bridge webhook - provider_data",
        call_sid=CallSid,
        provider_data=call.provider_data,
    )

    conference_name = call.provider_data.get("conference_name")
    customer_phone = call.provider_data.get("customer_phone")
    user_phone = call.provider_data.get("user_phone")

    logger.debug(
        "[TWILIO] Bridge webhook - extracted values",
        call_sid=CallSid,
        conference_name=conference_name,
        customer_phone=customer_phone,
        user_phone=user_phone,
    )

    if not all([conference_name, customer_phone, user_phone]):
        logger.warning(
            "[TWILIO] Bridge webhook - missing required info",
            call_sid=CallSid,
            conference_name=conference_name,
            customer_phone=customer_phone,
            user_phone=user_phone,
        )
        return Response(status_code=HTTPStatus.OK)

    # Create customer call to join conference
    try:
        webhooks = TwilioWebhooks()

        customer_call = await twilio_client.create_conference_call(
            to=customer_phone,
            from_=user_phone,
            conference_url=webhooks.twiml_url(conference_name),
            recording_callback=webhooks.recording_status_callback,
            status_callback=webhooks.status_callback,
        )

        logger.info(
            "[TWILIO] Customer call created for bridge",
            customer_call_sid=customer_call.sid,
            browser_call_sid=CallSid,
        )

        # Update call record with customer call SID
        # Create a new dict to trigger SQLAlchemy's change detection
        updated_provider_data = dict(call.provider_data)
        updated_provider_data["customer_call_sid"] = customer_call.sid
        call.provider_data = updated_provider_data

        # Explicitly flush and refresh to ensure the change is persisted
        await call_repository.session.flush()
        await call_repository.session.refresh(call)
        await call_repository.session.commit()

    except Exception as e:
        logger.error(
            "[TWILIO] Failed to bridge customer call",
            browser_call_sid=CallSid,
            error=str(e),
        )

    return Response(status_code=HTTPStatus.OK)


@router.post("/webhooks/recording", include_in_schema=False)
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

    # Try to find call by CallSid (could be browser or customer call)
    call = await call_repository.get_call_by_call_id(CallSid)

    # If not found, it might be the customer call - look for it in provider_data
    if not call:
        call = await call_repository.get_call_by_customer_call_sid(CallSid)

        if call:
            logger.debug(
                "[TWILIO] Recording webhook - found call by customer_call_sid",
                browser_call_sid=call.call_id,
                customer_call_sid=CallSid,
            )

    if call:
        await call_repository.update_call_recording(
            call_id=call.call_id, recording_url=recording_url_mp3
        )
        await call_repository.session.commit()
    else:
        logger.warning(
            "[TWILIO] Recording webhook - call not found",
            call_sid=CallSid,
        )

    return Response(status_code=HTTPStatus.OK)


@router.post("/twiml/join-conference", include_in_schema=False)
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
