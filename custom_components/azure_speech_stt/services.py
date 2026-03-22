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
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError

from .const import (
    CONF_CUSTOM_EXCLUSIONS,
    CONF_CUSTOM_PHRASES,
    CONF_CUSTOM_REPLACEMENTS,
    CONF_ENABLE_CUSTOM_REPLACEMENTS,
    CONF_ENABLE_FUZZY_MATCHING,
    CONF_FUZZY_THRESHOLD,
    DOMAIN,
)
from .correction_config import CorrectionConfig

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
MAX_REPLACEMENT_RULES = 100
MAX_PHRASE_LIST_SIZE = 500

# Service schemas
SCHEMA_TRANSCRIBE = vol.Schema(
    {
        vol.Required("audio_data"): str,
        vol.Optional("language", default="zh-TW"): str,
        vol.Optional("format", default="wav"): vol.In(["wav", "ogg"]),
        vol.Optional("codec", default="pcm"): vol.In(["pcm", "opus"]),
        vol.Optional("apply_correction", default=True): bool,
    }
)

SCHEMA_PHRASES = vol.Schema(
    {
        vol.Required("phrases"): [str],
    }
)

SCHEMA_ADD_REPLACEMENTS = vol.Schema(
    {
        vol.Required("replacements"): {str: str},
    }
)

SCHEMA_REMOVE_REPLACEMENTS = vol.Schema(
    {
        vol.Required("keys"): [str],
    }
)

SCHEMA_SET_CORRECTION_CONFIG = vol.Schema(
    {
        vol.Optional("custom_phrases"): [str],
        vol.Optional("custom_replacements"): {str: str},
        vol.Optional("enable_custom_replacements"): bool,
        vol.Optional("enable_fuzzy_matching"): bool,
        vol.Optional("fuzzy_threshold"): vol.All(
            vol.Coerce(float), vol.Range(min=0.5, max=1.0)
        ),
        vol.Optional("custom_exclusions"): [str],
    }
)

SCHEMA_GET_CORRECTION_CONFIG = vol.Schema({})

SCHEMA_EXCLUSIONS = vol.Schema(
    {
        vol.Required("exclusions"): [str],
    }
)

SCHEMA_TEST_CORRECTION = vol.Schema(
    {
        vol.Required("text"): str,
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
    and returns the transcription result with correction details.

    Args:
        hass: Home Assistant instance.
        call: Service call with audio_data, format, codec, language,
              and apply_correction parameters.

    Returns:
        Dict with text, raw_text, and corrections list.

    Raises:
        ServiceValidationError: If audio_data is invalid or empty.
    """
    audio_b64 = call.data.get("audio_data", "")
    audio_format = call.data.get("format", "wav")
    audio_codec = call.data.get("codec", "pcm")
    language = call.data.get("language", "zh-TW")
    apply_correction = call.data.get("apply_correction", True)

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
        return {
            "text": "",
            "raw_text": "",
            "corrections": [],
        }

    corrected_text = result.text

    # Retrieve raw and corrected text stored by the entity during recognition
    last_raw, last_corrected = entity.last_recognition
    raw_text = last_raw or corrected_text
    stored_corrected = last_corrected or corrected_text

    # If correction was disabled, return raw text only
    if not apply_correction:
        return {
            "text": raw_text,
            "raw_text": raw_text,
            "corrections": [],
        }

    # Build corrections list from the difference between raw and corrected
    corrections: list[dict] = []
    if raw_text != stored_corrected:
        corrections.append({"from": raw_text, "to": stored_corrected})

    return {
        "text": stored_corrected,
        "raw_text": raw_text,
        "corrections": corrections,
    }


def _get_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Get the first Azure STT config entry.

    Raises:
        ServiceValidationError: If no config entry is found.
    """
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise ServiceValidationError(
            f"No {DOMAIN} config entry found. Ensure the integration is configured."
        )
    return entries[0]


async def _update_options(hass: HomeAssistant, new_options: dict) -> None:
    """Persist updated options to the config entry."""
    entry = _get_config_entry(hass)
    hass.config_entries.async_update_entry(entry, options=new_options)


async def async_handle_add_phrases(hass: HomeAssistant, call: ServiceCall) -> None:
    """Add phrases to the custom phrases list (deduplicated)."""
    phrases_to_add: list[str] = call.data.get("phrases", [])
    if not phrases_to_add:
        return

    entry = _get_config_entry(hass)
    current: list[str] = list(entry.options.get(CONF_CUSTOM_PHRASES, []))

    if len(current) + len(phrases_to_add) > MAX_PHRASE_LIST_SIZE:
        raise ServiceValidationError(
            f"Phrase list would exceed maximum size of {MAX_PHRASE_LIST_SIZE}"
        )
    current_set = set(current)

    for phrase in phrases_to_add:
        phrase = phrase.strip()
        if phrase and phrase not in current_set:
            current.append(phrase)
            current_set.add(phrase)

    new_options = dict(entry.options) | {CONF_CUSTOM_PHRASES: current}
    await _update_options(hass, new_options)


async def async_handle_remove_phrases(hass: HomeAssistant, call: ServiceCall) -> None:
    """Remove phrases from the custom phrases list."""
    phrases_to_remove: list[str] = call.data.get("phrases", [])
    if not phrases_to_remove:
        return

    entry = _get_config_entry(hass)
    remove_set = {p.strip() for p in phrases_to_remove}
    current: list[str] = list(entry.options.get(CONF_CUSTOM_PHRASES, []))
    updated = [p for p in current if p not in remove_set]

    new_options = dict(entry.options) | {CONF_CUSTOM_PHRASES: updated}
    await _update_options(hass, new_options)


async def async_handle_add_replacements(hass: HomeAssistant, call: ServiceCall) -> None:
    """Add or update replacement rules (merged into existing)."""
    replacements: dict[str, str] = call.data.get("replacements", {})
    if not replacements:
        return

    entry = _get_config_entry(hass)
    current: dict[str, str] = dict(entry.options.get(CONF_CUSTOM_REPLACEMENTS, {}))

    # Count new keys (not updates to existing) to check limit
    merged_size = len(set(current) | set(replacements))
    if merged_size > MAX_REPLACEMENT_RULES:
        raise ServiceValidationError(
            f"Replacement rules would exceed maximum of {MAX_REPLACEMENT_RULES}"
        )

    current.update(replacements)

    new_options = dict(entry.options) | {CONF_CUSTOM_REPLACEMENTS: current}
    await _update_options(hass, new_options)


async def async_handle_remove_replacements(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Remove replacement rules by key."""
    keys: list[str] = call.data.get("keys", [])
    if not keys:
        return

    entry = _get_config_entry(hass)
    current: dict[str, str] = dict(entry.options.get(CONF_CUSTOM_REPLACEMENTS, {}))
    for key in keys:
        current.pop(key.strip(), None)

    new_options = dict(entry.options) | {CONF_CUSTOM_REPLACEMENTS: current}
    await _update_options(hass, new_options)


async def async_handle_add_exclusions(hass: HomeAssistant, call: ServiceCall) -> None:
    """Add segments to the exclusion list (deduplicated)."""
    exclusions_to_add: list[str] = call.data.get("exclusions", [])
    if not exclusions_to_add:
        return

    entry = _get_config_entry(hass)
    current: list[str] = list(entry.options.get(CONF_CUSTOM_EXCLUSIONS, []))
    current_set = set(current)

    for exc in exclusions_to_add:
        exc = exc.strip()
        if exc and exc not in current_set:
            current.append(exc)
            current_set.add(exc)

    new_options = dict(entry.options) | {CONF_CUSTOM_EXCLUSIONS: current}
    await _update_options(hass, new_options)


async def async_handle_remove_exclusions(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Remove segments from the exclusion list."""
    exclusions_to_remove: list[str] = call.data.get("exclusions", [])
    if not exclusions_to_remove:
        return

    entry = _get_config_entry(hass)
    remove_set = {e.strip() for e in exclusions_to_remove}
    current: list[str] = list(entry.options.get(CONF_CUSTOM_EXCLUSIONS, []))
    updated = [e for e in current if e not in remove_set]

    new_options = dict(entry.options) | {CONF_CUSTOM_EXCLUSIONS: updated}
    await _update_options(hass, new_options)


async def async_handle_get_correction_config(
    hass: HomeAssistant, call: ServiceCall
) -> dict:
    """Return the current correction configuration."""
    entry = _get_config_entry(hass)
    cfg = CorrectionConfig.from_options(entry.options)
    return {
        "custom_phrases": cfg.custom_phrases,
        "custom_replacements": cfg.custom_replacements,
        "enable_custom_replacements": cfg.enable_custom_replacements,
        "enable_fuzzy_matching": cfg.enable_fuzzy_matching,
        "fuzzy_threshold": cfg.fuzzy_threshold,
        "custom_exclusions": cfg.custom_exclusions,
    }


async def async_handle_test_correction(hass: HomeAssistant, call: ServiceCall) -> dict:
    """Run correction pipeline with diagnostic output."""
    text = call.data.get("text", "")
    if not text:
        raise ServiceValidationError("text is required and cannot be empty")

    entity = _find_stt_entity(hass)

    # Run correction pipeline via the entity's public API
    result = await entity.async_test_correction(text)
    return {
        "original": result.original,
        "corrected": result.corrected,
        "changes": [
            {
                "original_segment": c.original_segment,
                "corrected_segment": c.corrected_segment,
                "method": c.method,
                "confidence": c.confidence,
            }
            for c in result.changes
        ],
        "candidates": [
            {
                "phrase": c.phrase,
                "segment": c.segment,
                "score": c.score,
                "threshold": c.threshold,
                "accepted": c.accepted,
                "excluded": c.excluded,
            }
            for c in result.candidates
        ],
    }


async def async_handle_set_correction_config(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Replace the entire correction configuration."""
    data = dict(call.data)
    entry = _get_config_entry(hass)

    # Validate input limits
    if "custom_replacements" in data:
        if len(data["custom_replacements"]) > MAX_REPLACEMENT_RULES:
            raise ServiceValidationError(
                f"Replacement rules would exceed maximum of {MAX_REPLACEMENT_RULES}"
            )
    if "custom_phrases" in data:
        if len(data["custom_phrases"]) > MAX_PHRASE_LIST_SIZE:
            raise ServiceValidationError(
                f"Phrase list would exceed maximum size of {MAX_PHRASE_LIST_SIZE}"
            )

    new_options = dict(entry.options)
    if "custom_phrases" in data:
        new_options[CONF_CUSTOM_PHRASES] = list(data["custom_phrases"])
    if "custom_replacements" in data:
        new_options[CONF_CUSTOM_REPLACEMENTS] = dict(data["custom_replacements"])
    if "enable_custom_replacements" in data:
        new_options[CONF_ENABLE_CUSTOM_REPLACEMENTS] = bool(
            data["enable_custom_replacements"]
        )
    if "enable_fuzzy_matching" in data:
        new_options[CONF_ENABLE_FUZZY_MATCHING] = bool(data["enable_fuzzy_matching"])
    if "fuzzy_threshold" in data:
        new_options[CONF_FUZZY_THRESHOLD] = float(data["fuzzy_threshold"])
    if "custom_exclusions" in data:
        new_options[CONF_CUSTOM_EXCLUSIONS] = list(data["custom_exclusions"])

    await _update_options(hass, new_options)


def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services.

    Uses async closures (not lambdas) so HA recognizes them as
    coroutine functions and properly awaits their return values.
    """

    async def _transcribe(call: ServiceCall) -> dict:
        return await async_handle_transcribe(hass, call)

    async def _add_phrases(call: ServiceCall) -> None:
        await async_handle_add_phrases(hass, call)

    async def _remove_phrases(call: ServiceCall) -> None:
        await async_handle_remove_phrases(hass, call)

    async def _add_replacements(call: ServiceCall) -> None:
        await async_handle_add_replacements(hass, call)

    async def _remove_replacements(call: ServiceCall) -> None:
        await async_handle_remove_replacements(hass, call)

    async def _get_correction_config(call: ServiceCall) -> dict:
        return await async_handle_get_correction_config(hass, call)

    async def _set_correction_config(call: ServiceCall) -> None:
        await async_handle_set_correction_config(hass, call)

    async def _test_correction(call: ServiceCall) -> dict:
        return await async_handle_test_correction(hass, call)

    async def _add_exclusions(call: ServiceCall) -> None:
        await async_handle_add_exclusions(hass, call)

    async def _remove_exclusions(call: ServiceCall) -> None:
        await async_handle_remove_exclusions(hass, call)

    hass.services.async_register(
        DOMAIN,
        "transcribe",
        _transcribe,
        schema=SCHEMA_TRANSCRIBE,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "add_phrases", _add_phrases, schema=SCHEMA_PHRASES
    )
    hass.services.async_register(
        DOMAIN, "remove_phrases", _remove_phrases, schema=SCHEMA_PHRASES
    )
    hass.services.async_register(
        DOMAIN, "add_replacements", _add_replacements, schema=SCHEMA_ADD_REPLACEMENTS
    )
    hass.services.async_register(
        DOMAIN,
        "remove_replacements",
        _remove_replacements,
        schema=SCHEMA_REMOVE_REPLACEMENTS,
    )
    hass.services.async_register(
        DOMAIN,
        "get_correction_config",
        _get_correction_config,
        schema=SCHEMA_GET_CORRECTION_CONFIG,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "set_correction_config",
        _set_correction_config,
        schema=SCHEMA_SET_CORRECTION_CONFIG,
    )
    hass.services.async_register(
        DOMAIN,
        "test_correction",
        _test_correction,
        schema=SCHEMA_TEST_CORRECTION,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "add_exclusions", _add_exclusions, schema=SCHEMA_EXCLUSIONS
    )
    hass.services.async_register(
        DOMAIN, "remove_exclusions", _remove_exclusions, schema=SCHEMA_EXCLUSIONS
    )
