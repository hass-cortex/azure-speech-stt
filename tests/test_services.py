"""Tests for Azure Speech-to-Text transcribe service."""

from __future__ import annotations

import base64
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol


def _make_service_call(data: dict) -> MagicMock:
    """Create a mock ServiceCall with the given data."""
    call = MagicMock()
    call.data = data
    return call


def _make_stt_entity(
    text: str = "transcribed text",
    success: bool = True,
):
    """Create a mock STT entity that returns the given text.

    Args:
        text: Text to return from async_process_audio_stream.
        success: Whether the result should be SUCCESS or ERROR.
    """
    _stt = sys.modules["homeassistant.components.stt"]

    entity = MagicMock()
    result = MagicMock()
    result.text = text if success else ""
    result.result = (
        _stt.SpeechResultState.SUCCESS if success else _stt.SpeechResultState.ERROR
    )
    entity.async_process_audio_stream = AsyncMock(return_value=result)

    # Set stored recognition result via public property
    if success:
        entity.last_recognition = text
    else:
        entity.last_recognition = None

    return entity


class TestTranscribeService:
    """Test the transcribe service handler."""

    @pytest.mark.asyncio
    async def test_valid_audio_returns_result(self, mock_hass):
        """Valid base64 audio should return text."""
        from custom_components.azure_speech_stt.services import (
            async_handle_transcribe,
        )

        audio_bytes = b"RIFF\x00\x00\x00\x00WAVEfmt "
        audio_b64 = base64.b64encode(audio_bytes).decode()

        entity = _make_stt_entity(text="hello world")

        call = _make_service_call(
            {
                "audio_data": audio_b64,
                "format": "wav",
                "codec": "pcm",
                "language": "en-US",
            }
        )

        with patch(
            "custom_components.azure_speech_stt.services._find_stt_entity",
            return_value=entity,
        ):
            result = await async_handle_transcribe(mock_hass, call)

        assert result["text"] == "hello world"
        entity.async_process_audio_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_base64_raises_error(self, mock_hass):
        """Invalid base64 should raise ServiceValidationError."""
        from homeassistant.exceptions import ServiceValidationError

        from custom_components.azure_speech_stt.services import (
            async_handle_transcribe,
        )

        call = _make_service_call({"audio_data": "not-valid-base64!!!"})

        with pytest.raises(ServiceValidationError, match="Invalid base64"):
            await async_handle_transcribe(mock_hass, call)

    @pytest.mark.asyncio
    async def test_empty_audio_data_raises_error(self, mock_hass):
        """Empty audio_data string should raise ServiceValidationError."""
        from homeassistant.exceptions import ServiceValidationError

        from custom_components.azure_speech_stt.services import (
            async_handle_transcribe,
        )

        call = _make_service_call({"audio_data": ""})

        with pytest.raises(
            ServiceValidationError, match="required and cannot be empty"
        ):
            await async_handle_transcribe(mock_hass, call)

    @pytest.mark.asyncio
    async def test_missing_audio_data_raises_error(self, mock_hass):
        """Missing audio_data key should raise ServiceValidationError."""
        from homeassistant.exceptions import ServiceValidationError

        from custom_components.azure_speech_stt.services import (
            async_handle_transcribe,
        )

        call = _make_service_call({})

        with pytest.raises(
            ServiceValidationError, match="required and cannot be empty"
        ):
            await async_handle_transcribe(mock_hass, call)

    @pytest.mark.asyncio
    async def test_stt_error_returns_empty(self, mock_hass):
        """STT entity returning ERROR should yield empty result."""
        from custom_components.azure_speech_stt.services import (
            async_handle_transcribe,
        )

        audio_bytes = b"bad-audio"
        audio_b64 = base64.b64encode(audio_bytes).decode()

        entity = _make_stt_entity(success=False)

        call = _make_service_call({"audio_data": audio_b64})

        with patch(
            "custom_components.azure_speech_stt.services._find_stt_entity",
            return_value=entity,
        ):
            result = await async_handle_transcribe(mock_hass, call)

        assert result["text"] == ""

    @pytest.mark.asyncio
    async def test_default_parameters(self, mock_hass):
        """Service should use sensible defaults for optional parameters."""
        from custom_components.azure_speech_stt.services import (
            async_handle_transcribe,
        )

        audio_bytes = b"audio-content"
        audio_b64 = base64.b64encode(audio_bytes).decode()

        entity = _make_stt_entity(text="result")

        # Only provide audio_data, rely on defaults
        call = _make_service_call({"audio_data": audio_b64})

        with patch(
            "custom_components.azure_speech_stt.services._find_stt_entity",
            return_value=entity,
        ):
            result = await async_handle_transcribe(mock_hass, call)

        assert result["text"] == "result"


class TestRegisterServices:
    """Test service registration."""

    def test_register_services(self, mock_hass):
        """async_register_services should register only the transcribe service."""
        from custom_components.azure_speech_stt.services import (
            async_register_services,
        )

        async_register_services(mock_hass)

        registered = {
            call[0][1] for call in mock_hass.services.async_register.call_args_list
        }
        expected = {"transcribe"}
        assert registered == expected


class TestSchemaValidation:
    """Test voluptuous schema validation on service inputs."""

    def test_transcribe_invalid_language_type(self):
        """Non-string language should be rejected by schema."""
        from custom_components.azure_speech_stt.services import SCHEMA_TRANSCRIBE

        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_TRANSCRIBE({"audio_data": "dGVzdA==", "language": 12345})

    def test_transcribe_invalid_format(self):
        """Invalid audio format should be rejected by schema."""
        from custom_components.azure_speech_stt.services import SCHEMA_TRANSCRIBE

        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_TRANSCRIBE({"audio_data": "dGVzdA==", "format": "mp3"})

    def test_transcribe_invalid_codec(self):
        """Invalid audio codec should be rejected by schema."""
        from custom_components.azure_speech_stt.services import SCHEMA_TRANSCRIBE

        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_TRANSCRIBE({"audio_data": "dGVzdA==", "codec": "aac"})

    def test_transcribe_missing_audio_data(self):
        """Missing audio_data should be rejected by schema."""
        from custom_components.azure_speech_stt.services import SCHEMA_TRANSCRIBE

        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_TRANSCRIBE({"language": "en-US"})


class TestInputLimits:
    """Test input size limits."""

    @pytest.mark.asyncio
    async def test_audio_too_large_rejected(self, mock_hass):
        """Audio data exceeding MAX_AUDIO_SIZE should be rejected."""
        from homeassistant.exceptions import ServiceValidationError

        from custom_components.azure_speech_stt.services import (
            MAX_AUDIO_SIZE,
            async_handle_transcribe,
        )

        # Create audio data just over the limit
        large_audio = b"\x00" * (MAX_AUDIO_SIZE + 1)
        audio_b64 = base64.b64encode(large_audio).decode()

        call = _make_service_call({"audio_data": audio_b64})

        with pytest.raises(ServiceValidationError, match="too large"):
            await async_handle_transcribe(mock_hass, call)
