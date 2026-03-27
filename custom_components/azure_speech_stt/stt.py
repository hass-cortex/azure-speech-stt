"""Azure Speech-to-Text STT platform for Home Assistant."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterable
from functools import cached_property
from typing import TYPE_CHECKING, Any

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .azure_client import AzureSTTClient
from .const import (
    CONF_API_MODES,
    CONF_AUTO_COLLECT_SOURCES,
    CONF_CUSTOM_PHRASES,
    CONF_ENABLE_ENTITY_HINTS,
    CONF_SPEECH_KEY,
    CONF_SPEECH_REGION,
    DEFAULT_API_MODES,
    DEFAULT_AUTO_COLLECT_SOURCES,
    DEFAULT_ENABLE_ENTITY_HINTS,
    DOMAIN,
    SUPPORTED_LOCALES,
)
from .models import AzureSTTRuntimeData, TranscriptionStats
from .phrase_builder import PhraseBuilder

if TYPE_CHECKING:
    from . import AzureSpeechSTTConfigEntry

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

_MAX_CONSECUTIVE_FAILURES = 3

# PCM audio: 16kHz sample rate, 16-bit (2 bytes), mono (1 channel)
_PCM_BYTES_PER_SECOND = 16000 * 2 * 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: AzureSpeechSTTConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Azure Speech-to-Text STT platform from a config entry."""
    async_add_entities([AzureSpeechSTTEntity(hass, config_entry)])


class AzureSpeechSTTEntity(SpeechToTextEntity):
    """Azure Speech-to-Text entity with pre-recognition phrase hints.

    Uses Azure phraseList API to hint known entity/area names,
    improving recognition accuracy for home automation commands.
    """

    has_entity_name = True

    def __init__(
        self, hass: HomeAssistant, config_entry: AzureSpeechSTTConfigEntry
    ) -> None:
        """Initialize the Azure STT entity.

        Args:
            hass: Home Assistant instance.
            config_entry: Config entry with Azure credentials and options.
        """
        self._hass = hass
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=config_entry.title,
            manufacturer="Microsoft",
            model="Azure Speech Services",
            entry_type=DeviceEntryType.SERVICE,
        )

        # Store last recognition result for service handler access
        self._last_raw_text: str | None = None

        # Track consecutive failures for availability management
        self._consecutive_failures = 0

        # Session-level counters for average duration computation (ephemeral)
        self._session_total_duration_ms: float = 0.0
        self._session_success_count: int = 0

        # Azure HTTP client (uses HA shared session)
        self._client = AzureSTTClient(
            region=config_entry.data[CONF_SPEECH_REGION],
            api_key=config_entry.data[CONF_SPEECH_KEY],
            session=async_get_clientsession(hass),
        )

        # Build PhraseBuilder for entity/area hints
        custom_phrases = self._options.get(CONF_CUSTOM_PHRASES, [])
        auto_collect_sources = self._options.get(
            CONF_AUTO_COLLECT_SOURCES, DEFAULT_AUTO_COLLECT_SOURCES
        )
        self._phrase_builder = PhraseBuilder(hass, custom_phrases, auto_collect_sources)

    @property
    def _options(self) -> dict[str, Any]:
        """Return config entry options directly.

        In HA, config_entry.options is already a MappingProxyType (immutable).
        No need to copy on every access.
        """
        return self._config_entry.options

    @cached_property
    def supported_languages(self) -> list[str]:
        """Return all Azure Fast Transcription supported languages."""
        return list(SUPPORTED_LOCALES.keys())

    @property
    def supported_formats(self) -> list[AudioFormats]:
        """Return a list of supported audio formats."""
        return [AudioFormats.WAV, AudioFormats.OGG]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        """Return a list of supported audio codecs."""
        return [AudioCodecs.PCM, AudioCodecs.OPUS]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        """Return a list of supported bit rates."""
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        """Return a list of supported sample rates."""
        return [AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        """Return a list of supported channels."""
        return [AudioChannels.CHANNEL_MONO]

    @property
    def last_recognition(self) -> str | None:
        """Return the last raw recognition text.

        Returns:
            The raw transcription text, or None if no recognition
            has been performed yet.
        """
        return self._last_raw_text

    async def async_get_phrases(self) -> list[str]:
        """Return the current phrase list from the phrase builder.

        Returns:
            List of known phrases (entity names, area names, custom phrases).
        """
        return await self._phrase_builder.build()

    async def async_added_to_hass(self) -> None:
        """Start listening for registry changes."""
        runtime_data: AzureSTTRuntimeData = self._config_entry.runtime_data
        runtime_data.entity = self
        self._phrase_builder.async_start_listening()

    async def async_will_remove_from_hass(self) -> None:
        """Stop listening for registry changes."""
        self._phrase_builder.async_stop_listening()

    def _push_stats(self, stats: TranscriptionStats) -> None:
        """Push transcription statistics to all registered sensor entities."""
        runtime_data: AzureSTTRuntimeData = self._config_entry.runtime_data
        for sensor in runtime_data.sensors:
            sensor.handle_transcription(stats)

    def rebuild_phrase_builder(self) -> None:
        """Rebuild phrase builder after options change."""
        custom_phrases = self._options.get(CONF_CUSTOM_PHRASES, [])
        auto_collect_sources = self._options.get(
            CONF_AUTO_COLLECT_SOURCES, DEFAULT_AUTO_COLLECT_SOURCES
        )
        self._phrase_builder.update_custom_phrases(custom_phrases)
        self._phrase_builder.update_sources(auto_collect_sources)

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> SpeechResult:
        """Process an audio stream and return transcribed text.

        Steps:
        1. Collect all audio bytes from the async stream
        2. Build phrase list (cached) for Azure API hints
        3. Call Azure STT API
        4. Return SpeechResult with raw transcription

        Args:
            metadata: Audio metadata (format, codec, sample rate, etc.).
            stream: Async iterable of audio byte chunks.

        Returns:
            SpeechResult with transcribed text.
        """
        # Step 1: Collect audio bytes
        chunks: list[bytes] = []
        async for chunk in stream:
            chunks.append(chunk)
        audio_data = b"".join(chunks)

        if not audio_data:
            _LOGGER.warning("Received empty audio stream")
            return SpeechResult(text=None, result=SpeechResultState.ERROR)

        _LOGGER.debug(
            "Audio received: %d bytes, language=%s, format=%s, codec=%s",
            len(audio_data),
            metadata.language,
            metadata.format,
            metadata.codec,
        )

        # Step 2: Build phrases for Azure API hints
        enable_hints = self._options.get(
            CONF_ENABLE_ENTITY_HINTS, DEFAULT_ENABLE_ENTITY_HINTS
        )
        if enable_hints:
            phrases = await self._phrase_builder.build()
            _LOGGER.debug("Phrase list: %d phrases", len(phrases))
            if _LOGGER.isEnabledFor(logging.DEBUG):
                for category, items in self._phrase_builder.categories.items():
                    if items:
                        _LOGGER.debug("  %s (%d): %s", category, len(items), items)
        else:
            phrases = []

        # Step 3: Call Azure STT API
        api_modes = self._options.get(CONF_API_MODES, DEFAULT_API_MODES)
        _LOGGER.debug(
            "Calling Azure STT for locale %s (allowed APIs: %s)",
            metadata.language,
            api_modes,
        )

        audio_seconds = len(audio_data) / _PCM_BYTES_PER_SECOND
        t0 = time.monotonic()
        raw_text, api_used = await self._client.transcribe(
            audio_data, metadata.language, phrases, allowed_apis=api_modes
        )
        elapsed_ms = (time.monotonic() - t0) * 1000

        if api_used:
            _LOGGER.debug("Used %s API for locale %s", api_used, metadata.language)

        if raw_text is None:
            # API error occurred (already logged)
            self._last_raw_text = None
            self._consecutive_failures += 1
            self._push_stats(
                TranscriptionStats(
                    success=False,
                    api_error=True,
                    duration_ms=elapsed_ms,
                    audio_bytes=len(audio_data),
                    audio_seconds=audio_seconds,
                    language=metadata.language,
                    api_used=api_used,
                )
            )
            if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                _LOGGER.warning(
                    "Azure STT marked unavailable after %d consecutive failures",
                    self._consecutive_failures,
                )
                self._attr_available = False
                self.async_write_ha_state()
            return SpeechResult(text=None, result=SpeechResultState.ERROR)

        if not raw_text:
            # Empty transcription (no speech detected)
            _LOGGER.debug("Azure STT: No speech recognized")
            self._last_raw_text = ""
            self._push_stats(
                TranscriptionStats(
                    success=False,
                    api_error=False,
                    duration_ms=elapsed_ms,
                    audio_bytes=len(audio_data),
                    audio_seconds=audio_seconds,
                    language=metadata.language,
                    api_used=api_used,
                )
            )
            return SpeechResult(text=None, result=SpeechResultState.ERROR)

        _LOGGER.info("Azure STT result: %s", raw_text)

        # Update service API state
        self._last_raw_text = raw_text

        # Compute session average duration
        self._session_success_count += 1
        self._session_total_duration_ms += elapsed_ms
        avg_ms = self._session_total_duration_ms / self._session_success_count

        # Push stats to sensors
        self._push_stats(
            TranscriptionStats(
                success=True,
                api_error=False,
                duration_ms=elapsed_ms,
                audio_bytes=len(audio_data),
                audio_seconds=audio_seconds,
                language=metadata.language,
                api_used=api_used,
                raw_text=raw_text,
                avg_duration_ms=avg_ms,
            )
        )

        # Reset failure counter and restore availability on success
        if self._consecutive_failures > 0:
            if not self._attr_available:
                _LOGGER.info("Azure STT recovered, marking available")
                self._attr_available = True
                self.async_write_ha_state()
            self._consecutive_failures = 0

        return SpeechResult(
            text=raw_text,
            result=SpeechResultState.SUCCESS,
        )
