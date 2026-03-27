"""Azure Speech-to-Text HTTP API client."""

from __future__ import annotations

import io
import json
import logging
import wave
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import (
    API_MODE_FAST,
    API_MODE_REALTIME,
    DEFAULT_API_MODES,
    FAST_TRANSCRIPTION_ENDPOINT,
    REALTIME_ONLY_LOCALES,
    REALTIME_STT_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)

# HTTP status codes that should be retried (per Azure API docs)
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# WAV container parameters for PCM audio
_WAV_CHANNELS = 1
_WAV_SAMPLE_WIDTH = 2  # 16-bit
_WAV_FRAME_RATE = 16000


class PermanentApiError(Exception):
    """API error that should not be retried (e.g., authentication failure)."""

    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


class AzureSTTClient:
    """HTTP client for Azure Speech-to-Text APIs.

    Supports two Azure endpoints:
    - Fast Transcription API: most locales (supports phraseList hints)
    - Real-time REST API: locales not supported by Fast Transcription

    Uses a shared aiohttp.ClientSession (provided via constructor) instead
    of creating new sessions per request.
    """

    def __init__(
        self, region: str, api_key: str, session: aiohttp.ClientSession
    ) -> None:
        """Initialize the Azure STT client.

        Args:
            region: Azure region (e.g., 'eastasia').
            api_key: Azure Speech API subscription key.
            session: Shared aiohttp.ClientSession from HA.
        """
        self._region = region
        self._api_key = api_key
        self._session = session

    async def transcribe(
        self,
        audio: bytes,
        language: str,
        phrases: list[str],
        allowed_apis: list[str] | None = None,
    ) -> tuple[str | None, str]:
        """Transcribe audio using the appropriate Azure API.

        Routes to Fast Transcription or Real-time API based on locale and
        allowed_apis configuration. Retries once on transient failures.

        Args:
            audio: Raw PCM audio bytes (16kHz, 16-bit, mono).
            language: BCP-47 locale from Pipeline metadata.
            phrases: Known phrases for phraseList hints.
            allowed_apis: List of allowed API modes. Defaults to both.

        Returns:
            Tuple of (transcribed text or None on error, api_used string).
            Text is empty string if no speech detected.
        """
        apis = allowed_apis or DEFAULT_API_MODES

        # Resolve API choice once, before retry loop
        if language in REALTIME_ONLY_LOCALES:
            if API_MODE_REALTIME in apis:
                use_realtime = True
            else:
                _LOGGER.warning(
                    "Locale %s requires Real-time API but only Fast Transcription "
                    "is enabled. Skipping transcription",
                    language,
                )
                return None, ""
        else:
            if API_MODE_FAST in apis:
                use_realtime = False
            elif API_MODE_REALTIME in apis:
                use_realtime = True
            else:
                _LOGGER.error("No API mode enabled for locale %s", language)
                return None, ""

        api_used = API_MODE_REALTIME if use_realtime else API_MODE_FAST

        async def _call() -> str | None:
            if use_realtime:
                return await self._transcribe_realtime(audio, language)
            return await self._transcribe_fast(audio, language, phrases)

        try:
            result = await _call()
        except PermanentApiError:
            return None, api_used

        if result is not None:
            return result, api_used

        _LOGGER.warning("Azure STT: First attempt failed, retrying once")
        try:
            result = await _call()
            return result, api_used
        except PermanentApiError:
            return None, api_used

    async def _transcribe_fast(
        self, audio: bytes, language: str, phrases: list[str]
    ) -> str | None:
        """Call Azure Fast Transcription REST API (supports phraseList).

        Args:
            audio: Raw PCM audio bytes.
            language: BCP-47 locale.
            phrases: Known phrases for phraseList hints.

        Returns:
            Transcribed text, empty string if no speech, or None on transient error.

        Raises:
            PermanentApiError: On non-retryable HTTP errors (401, 400, 403).
        """
        url = FAST_TRANSCRIPTION_ENDPOINT.format(region=self._region)

        definition: dict[str, Any] = {"locales": [language]}
        if phrases:
            definition["phraseList"] = {"phrases": phrases}

        wav_data = self.wrap_pcm_as_wav(audio)

        form = aiohttp.FormData()
        form.add_field(
            "audio", wav_data, filename="audio.wav", content_type="audio/wav"
        )
        form.add_field("definition", json.dumps(definition))

        try:
            async with self._session.post(
                url,
                data=form,
                headers={"Ocp-Apim-Subscription-Key": self._api_key},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    combined = data.get("combinedPhrases", [])
                    if combined:
                        return combined[0].get("text", "")
                    return ""
                if resp.status in (401, 403):
                    _LOGGER.error(
                        "Azure STT authentication error (HTTP %d)", resp.status
                    )
                else:
                    body = await resp.text()
                    _LOGGER.error("Azure STT error %d: %.200s", resp.status, body)
                if resp.status in _RETRYABLE_STATUS_CODES:
                    return None
                raise PermanentApiError(resp.status)
        except PermanentApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.error("Azure STT connection error: %s", err)
            return None

    async def _transcribe_realtime(self, audio: bytes, language: str) -> str | None:
        """Call Azure Real-time REST API for short audio.

        Used for locales not supported by Fast Transcription (e.g., zh-TW).
        Returns native script (Traditional Chinese for zh-TW).
        No phraseList support -- phrases are only used by Fast Transcription.

        Args:
            audio: Raw PCM audio bytes.
            language: BCP-47 locale.

        Returns:
            Transcribed text, empty string if no speech, or None on transient error.

        Raises:
            PermanentApiError: On non-retryable HTTP errors (401, 400, 403).
        """
        url = REALTIME_STT_ENDPOINT.format(
            region=self._region,
            language=quote(language),
        )

        wav_data = self.wrap_pcm_as_wav(audio)

        try:
            async with self._session.post(
                url,
                data=wav_data,
                headers={
                    "Content-Type": "audio/wav",
                    "Ocp-Apim-Subscription-Key": self._api_key,
                },
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    _LOGGER.debug("Azure Realtime STT response: %s", data)
                    if data.get("RecognitionStatus") == "Success":
                        return data.get("DisplayText", "")
                    return ""
                if resp.status in (401, 403):
                    _LOGGER.error(
                        "Azure STT authentication error (HTTP %d)", resp.status
                    )
                else:
                    body = await resp.text()
                    _LOGGER.error("Azure STT error %d: %.200s", resp.status, body)
                if resp.status in _RETRYABLE_STATUS_CODES:
                    return None
                raise PermanentApiError(resp.status)
        except PermanentApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.error("Azure STT connection error: %s", err)
            return None

    @staticmethod
    def wrap_pcm_as_wav(pcm_data: bytes) -> bytes:
        """Wrap raw PCM bytes in a WAV container (16kHz, 16-bit, mono).

        Args:
            pcm_data: Raw PCM audio bytes.

        Returns:
            WAV-formatted audio bytes.
        """
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(_WAV_CHANNELS)
            wf.setsampwidth(_WAV_SAMPLE_WIDTH)
            wf.setframerate(_WAV_FRAME_RATE)
            wf.writeframes(pcm_data)
        return wav_buffer.getvalue()
