"""Service handlers for Azure Speech-to-Text integration."""

from __future__ import annotations

import base64
import binascii
import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResultState,
)
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN

if TYPE_CHECKING:
    from .stt import AzureSpeechSTTEntity

_LOGGER = logging.getLogger(__name__)

# Map string format/codec to HA enums
_FORMAT_MAP = {
    "wav": AudioFormats.WAV,
    "ogg": AudioFormats.OGG,
}

_CODEC_MAP = {
    "pcm": AudioCodecs.PCM,
    "opus": AudioCodecs.OPUS,
}

# Input limits
MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10 MB

# Service schemas
SCHEMA_TRANSCRIBE = vol.Schema(
    {
        vol.Required("audio_data"): str,
        vol.Optional("language", default="en-US"): str,
        vol.Optional("format", default="wav"): vol.In(["wav", "ogg"]),
        vol.Optional("codec", default="pcm"): vol.In(["pcm", "opus"]),
    }
)


async def _bytes_to_stream(data: bytes) -> AsyncIterator[bytes]:
    """Wrap raw bytes into an async iterator for the STT entity.

    Args:
        data: Raw audio bytes.

    Yields:
        Audio data as a single chunk.
    """
    yield data


def _find_stt_entity(hass: HomeAssistant) -> AzureSpeechSTTEntity:
    """Find the first Azure STT entity, raising if not found."""
    from .helpers import find_stt_entity

    entity = find_stt_entity(hass)
    if entity is None:
        raise ServiceValidationError(
            f"No {DOMAIN} STT entity found. Ensure the integration is configured."
        )
    return entity


async def async_handle_transcribe(hass: HomeAssistant, call: ServiceCall) -> dict:
    """Handle the transcribe service call.

    Decodes base64 audio, sends it through the STT entity pipeline,
    and returns the transcription result.

    Args:
        hass: Home Assistant instance.
        call: Service call with audio_data, format, codec, and language
              parameters.

    Returns:
        Dict with text.

    Raises:
        ServiceValidationError: If audio_data is invalid or empty.
    """
    audio_b64 = call.data.get("audio_data", "")
    audio_format = call.data.get("format", "wav")
    audio_codec = call.data.get("codec", "pcm")
    language = call.data.get("language", "en-US")

    # Decode base64 audio
    if not audio_b64:
        raise ServiceValidationError("audio_data is required and cannot be empty")

    try:
        audio_bytes = base64.b64decode(audio_b64)
    except binascii.Error as err:
        raise ServiceValidationError("Invalid base64 audio_data") from err

    if not audio_bytes:
        raise ServiceValidationError("Decoded audio data is empty")

    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise ServiceValidationError(
            f"Audio data too large: {len(audio_bytes)} bytes "
            f"(max {MAX_AUDIO_SIZE} bytes)"
        )

    # Find the STT entity
    entity = _find_stt_entity(hass)

    # Build metadata
    metadata = SpeechMetadata(
        language=language,
        format=_FORMAT_MAP.get(audio_format, AudioFormats.WAV),
        codec=_CODEC_MAP.get(audio_codec, AudioCodecs.PCM),
        bit_rate=AudioBitRates.BITRATE_16,
        sample_rate=AudioSampleRates.SAMPLERATE_16000,
        channel=AudioChannels.CHANNEL_MONO,
    )

    # Process through the STT entity
    result = await entity.async_process_audio_stream(
        metadata, _bytes_to_stream(audio_bytes)
    )

    if result.result != SpeechResultState.SUCCESS:
        return {"text": ""}

    return {"text": result.text or ""}


def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services.

    Uses async closures (not lambdas) so HA recognizes them as
    coroutine functions and properly awaits their return values.
    """

    async def _transcribe(call: ServiceCall) -> dict:
        return await async_handle_transcribe(hass, call)

    hass.services.async_register(
        DOMAIN,
        "transcribe",
        _transcribe,
        schema=SCHEMA_TRANSCRIBE,
        supports_response=SupportsResponse.ONLY,
    )
