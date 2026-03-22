"""Azure Speech-to-Text STT platform for Home Assistant."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterable
from functools import cached_property
from typing import Any

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
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .azure_client import AzureSTTClient
from .const import (
    CONF_API_MODES,
    CONF_CORRECTION_STAGES,
    CONF_SPEECH_KEY,
    CONF_SPEECH_REGION,
    DEFAULT_API_MODES,
    DEFAULT_CORRECTION_STAGES,
    DOMAIN,
    SUPPORTED_LOCALES,
)
from .correction_config import CorrectionConfig
from .models import AzureSTTRuntimeData, TranscriptionStats
from .phrase_builder import PhraseBuilder
from .stt_corrector import DiagnosticResult, SpeechCorrector
from .stt_corrector.matchers import DefaultMatcher, PhoneticMatcher, PinyinMatcher

# Locales that should use PinyinMatcher for phonetic similarity.
# Only standard Mandarin locales are supported — pypinyin is based on
# Mandarin phonology and does not produce accurate results for Cantonese
# (yue-/zh-HK) or Wu (wuu-) dialects.
_MANDARIN_LOCALE_PREFIXES = ("zh-CN", "zh-TW")

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

_MAX_CONSECUTIVE_FAILURES = 3

# PCM audio: 16kHz sample rate, 16-bit (2 bytes), mono (1 channel)
_PCM_BYTES_PER_SECOND = 16000 * 2 * 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Azure Speech-to-Text STT platform from a config entry."""
    async_add_entities([AzureSpeechSTTEntity(hass, config_entry)])


class AzureSpeechSTTEntity(SpeechToTextEntity):
    """Azure Speech-to-Text entity with dual-layer correction.

    Dual-layer correction pipeline:
    1. Azure Fast Transcription phraseList — hint known phrases to the API
    2. SpeechCorrector — post-recognition homophone + custom + fuzzy correction
    """

    has_entity_name = True

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
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

        # Store last recognition results for service handler access
        self._last_raw_text: str | None = None
        self._last_corrected_text: str | None = None

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
        cfg = CorrectionConfig.from_options(self._options)
        self._phrase_builder = PhraseBuilder(
            hass, cfg.custom_phrases, cfg.auto_collect_sources
        )

        # Build SpeechCorrector (matchers set per-locale on first use)
        self._corrector_locale: str | None = None
        self._corrector = self._build_corrector()

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
    def last_recognition(self) -> tuple[str | None, str | None]:
        """Return the last raw and corrected recognition texts.

        Returns:
            Tuple of (raw_text, corrected_text). Both are None if no
            recognition has been performed yet.
        """
        return self._last_raw_text, self._last_corrected_text

    async def async_test_correction(self, text: str) -> DiagnosticResult:
        """Run the correction pipeline on text for diagnostic purposes.

        Builds the current phrase list and runs the corrector's diagnose
        method, returning detailed correction and candidate information.

        Args:
            text: Input text to test correction against.

        Returns:
            DiagnosticResult with original, corrected, changes, and candidates.
        """
        phrases = await self._phrase_builder.build()
        self._corrector.update_phrases(phrases)
        return self._corrector.diagnose(text)

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

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> SpeechResult:
        """Process an audio stream and return transcribed text.

        Steps:
        1. Collect all audio bytes from the async stream
        2. Build phrase list (cached) and update corrector phrases
        3. Call Azure Fast Transcription REST API
        4. Apply SpeechCorrector correction pipeline
        5. Return SpeechResult

        Args:
            metadata: Audio metadata (format, codec, sample rate, etc.).
            stream: Async iterable of audio byte chunks.

        Returns:
            SpeechResult with transcribed and corrected text.
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

        # Step 2: Read options once per request
        cfg = CorrectionConfig.from_options(self._options)

        # Rebuild corrector if locale changed (selects correct matchers)
        if metadata.language != self._corrector_locale:
            self._corrector = self._build_corrector(locale=metadata.language, cfg=cfg)
            self._corrector_locale = metadata.language
            _LOGGER.debug("Corrector rebuilt for locale %s", metadata.language)
        # Always build phrases (based on auto_collect_sources + custom phrases)
        # and update the corrector for similarity matching
        phrases = await self._phrase_builder.build()
        self._corrector.update_phrases(phrases)
        _LOGGER.debug("Phrase list: %d phrases", len(phrases))
        if _LOGGER.isEnabledFor(logging.DEBUG):
            for category, items in self._phrase_builder._categories.items():
                if items:
                    _LOGGER.debug("  %s (%d): %s", category, len(items), items)

        # Only send phrases to Azure API if Pre-recognition Hints stage is enabled
        api_phrases = phrases if cfg.enable_entity_hints else []

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
            audio_data, metadata.language, api_phrases, allowed_apis=api_modes
        )
        elapsed_ms = (time.monotonic() - t0) * 1000

        if api_used:
            _LOGGER.debug("Used %s API for locale %s", api_used, metadata.language)

        if raw_text is None:
            # API error occurred (already logged)
            self._last_raw_text = None
            self._last_corrected_text = None
            self._consecutive_failures += 1
            self._push_stats(
                TranscriptionStats(
                    success=False,
                    api_error=True,
                    correction_applied=False,
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
            self._last_corrected_text = None
            self._push_stats(
                TranscriptionStats(
                    success=False,
                    api_error=False,
                    correction_applied=False,
                    duration_ms=elapsed_ms,
                    audio_bytes=len(audio_data),
                    audio_seconds=audio_seconds,
                    language=metadata.language,
                    api_used=api_used,
                )
            )
            return SpeechResult(text=None, result=SpeechResultState.ERROR)

        _LOGGER.info("Azure STT raw: %s", raw_text)

        # Step 4: Apply correction pipeline (if any stage enabled)
        correction_stages = self._options.get(
            CONF_CORRECTION_STAGES, DEFAULT_CORRECTION_STAGES
        )
        if correction_stages:
            correction = self._corrector.diagnose(raw_text)
            self._log_correction_result(correction, cfg)
            final_text = correction.corrected
            correction_applied = bool(correction.changes)
        else:
            _LOGGER.debug("Correction pipeline disabled, using raw text")
            final_text = raw_text
            correction_applied = False

        # Update service API state
        self._last_raw_text = raw_text
        self._last_corrected_text = final_text if correction_applied else None

        # Compute session average duration
        self._session_success_count += 1
        self._session_total_duration_ms += elapsed_ms
        avg_ms = self._session_total_duration_ms / self._session_success_count

        # Push stats to sensors
        self._push_stats(
            TranscriptionStats(
                success=True,
                api_error=False,
                correction_applied=correction_applied,
                duration_ms=elapsed_ms,
                audio_bytes=len(audio_data),
                audio_seconds=audio_seconds,
                language=metadata.language,
                api_used=api_used,
                raw_text=raw_text,
                corrected_text=(final_text if correction_applied else None),
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
            text=final_text,
            result=SpeechResultState.SUCCESS,
        )

    def _log_correction_result(
        self,
        correction: DiagnosticResult,
        cfg: CorrectionConfig,
    ) -> None:
        """Log correction pipeline results at appropriate levels.

        Args:
            correction: Diagnostic result from the correction pipeline.
            cfg: Current correction configuration.
        """
        if correction.corrected != correction.original:
            _LOGGER.info(
                "Azure STT corrected: '%s' → '%s'",
                correction.original,
                correction.corrected,
            )

        if not _LOGGER.isEnabledFor(logging.DEBUG):
            return

        # Single pass to partition changes by method
        custom_changes: list = []
        fuzzy_changes: list = []
        for change in correction.changes:
            if change.method == "custom_rule":
                custom_changes.append(change)
            else:
                fuzzy_changes.append(change)

        _LOGGER.debug(
            "Correction stage 1 (replacements): %s, %d rules, %d applied",
            "ON" if cfg.enable_custom_replacements else "OFF",
            len(cfg.custom_replacements),
            len(custom_changes),
        )
        for change in custom_changes:
            _LOGGER.debug(
                "  [custom_rule] '%s' → '%s'",
                change.original_segment,
                change.corrected_segment,
            )

        excluded_count = sum(1 for c in correction.candidates if c.excluded)
        _LOGGER.debug(
            "Correction stage 2 (similarity): %s, threshold=%.2f, %d applied, %d exclusions (%d hit)",
            "ON" if cfg.enable_fuzzy_matching else "OFF",
            cfg.fuzzy_threshold,
            len(fuzzy_changes),
            len(cfg.custom_exclusions),
            excluded_count,
        )
        for change in fuzzy_changes:
            _LOGGER.debug(
                "  [fuzzy_match] '%s' → '%s' (score: %.2f)",
                change.original_segment,
                change.corrected_segment,
                change.confidence,
            )

        if correction.candidates:
            top3 = correction.candidates[:3]
            _LOGGER.debug("Top candidates:")
            for c in top3:
                status = (
                    "excluded"
                    if c.excluded
                    else "accepted"
                    if c.accepted
                    else "rejected"
                )
                _LOGGER.debug(
                    "  '%s' → '%s' (score: %.4f, threshold: %.2f, %s)",
                    c.segment,
                    c.phrase,
                    c.score,
                    c.threshold,
                    status,
                )

    def rebuild_from_options(self) -> None:
        """Rebuild corrector and phrase builder after options change."""
        cfg = CorrectionConfig.from_options(self._options)
        self._corrector = self._build_corrector(locale=self._corrector_locale, cfg=cfg)
        self._phrase_builder.update_custom_phrases(cfg.custom_phrases)
        self._phrase_builder.update_sources(cfg.auto_collect_sources)

    def _build_corrector(
        self,
        locale: str | None = None,
        cfg: CorrectionConfig | None = None,
    ) -> SpeechCorrector:
        """Build the SpeechCorrector from config options.

        Args:
            locale: BCP-47 locale code. Determines which phonetic matchers
                    to use (PinyinMatcher for Mandarin, DefaultMatcher for others).
            cfg: Pre-built config. If None, reads from options.
        """
        if cfg is None:
            cfg = CorrectionConfig.from_options(self._options)

        # Select matchers based on locale.
        is_non_chinese = locale is not None and not any(
            locale.startswith(p) for p in _MANDARIN_LOCALE_PREFIXES
        )
        matchers: list[PhoneticMatcher] = (
            [DefaultMatcher()]
            if is_non_chinese
            else [PinyinMatcher(), DefaultMatcher()]
        )

        return SpeechCorrector(
            known_phrases=[],
            custom_replacements=cfg.custom_replacements or None,
            fuzzy_threshold=cfg.fuzzy_threshold,
            enable_custom_replacements=cfg.enable_custom_replacements,
            enable_fuzzy_matching=cfg.enable_fuzzy_matching,
            matchers=matchers,
            exclusions=cfg.custom_exclusions or None,
        )
