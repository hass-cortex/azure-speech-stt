"""Tests for Azure Speech-to-Text transcribe service."""

from __future__ import annotations

import base64
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol

from custom_components.azure_speech_stt.models import AzureSTTRuntimeData


def _make_service_call(data: dict) -> MagicMock:
    """Create a mock ServiceCall with the given data."""
    call = MagicMock()
    call.data = data
    return call


def _make_stt_entity(
    corrected_text: str = "corrected text",
    raw_text: str | None = None,
    success: bool = True,
):
    """Create a mock STT entity that returns the given text.

    Args:
        corrected_text: Text to return from async_process_audio_stream.
        raw_text: Raw text before correction (defaults to corrected_text).
        success: Whether the result should be SUCCESS or ERROR.
    """
    _stt = sys.modules["homeassistant.components.stt"]

    entity = MagicMock()
    result = MagicMock()
    result.text = corrected_text if success else ""
    result.result = (
        _stt.SpeechResultState.SUCCESS if success else _stt.SpeechResultState.ERROR
    )
    entity.async_process_audio_stream = AsyncMock(return_value=result)

    # Set stored recognition results via public property
    if success:
        stored_raw = raw_text if raw_text is not None else corrected_text
        entity.last_recognition = (stored_raw, corrected_text)
    else:
        entity.last_recognition = (None, None)

    return entity


class TestTranscribeService:
    """Test the transcribe service handler."""

    @pytest.mark.asyncio
    async def test_valid_audio_returns_result(self, mock_hass):
        """Valid base64 audio should return text, raw_text, corrections."""
        from custom_components.azure_speech_stt.services import (
            async_handle_transcribe,
        )

        audio_bytes = b"RIFF\x00\x00\x00\x00WAVEfmt "
        audio_b64 = base64.b64encode(audio_bytes).decode()

        entity = _make_stt_entity(corrected_text="hello world")

        call = _make_service_call(
            {
                "audio_data": audio_b64,
                "format": "wav",
                "codec": "pcm",
                "language": "en-US",
                "apply_correction": True,
            }
        )

        with patch(
            "custom_components.azure_speech_stt.services._find_stt_entity",
            return_value=entity,
        ):
            result = await async_handle_transcribe(mock_hass, call)

        assert result["text"] == "hello world"
        assert "raw_text" in result
        assert "corrections" in result
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
    async def test_apply_correction_false(self, mock_hass):
        """apply_correction=false should return text equal to raw_text."""
        from custom_components.azure_speech_stt.services import (
            async_handle_transcribe,
        )

        audio_bytes = b"fake-audio-data"
        audio_b64 = base64.b64encode(audio_bytes).decode()

        entity = _make_stt_entity(corrected_text="some text")

        call = _make_service_call(
            {
                "audio_data": audio_b64,
                "apply_correction": False,
                "language": "zh-TW",
            }
        )

        with patch(
            "custom_components.azure_speech_stt.services._find_stt_entity",
            return_value=entity,
        ):
            result = await async_handle_transcribe(mock_hass, call)

        assert result["text"] == result["raw_text"]
        assert result["corrections"] == []

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
        assert result["raw_text"] == ""
        assert result["corrections"] == []

    @pytest.mark.asyncio
    async def test_default_parameters(self, mock_hass):
        """Service should use sensible defaults for optional parameters."""
        from custom_components.azure_speech_stt.services import (
            async_handle_transcribe,
        )

        audio_bytes = b"audio-content"
        audio_b64 = base64.b64encode(audio_bytes).decode()

        entity = _make_stt_entity(corrected_text="result")

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
        """async_register_services should register all services."""
        from custom_components.azure_speech_stt.services import (
            async_register_services,
        )

        async_register_services(mock_hass)

        registered = {
            call[0][1] for call in mock_hass.services.async_register.call_args_list
        }
        expected = {
            "transcribe",
            "add_phrases",
            "remove_phrases",
            "add_replacements",
            "remove_replacements",
            "get_correction_config",
            "set_correction_config",
            "test_correction",
            "add_exclusions",
            "remove_exclusions",
        }
        assert registered == expected


def _make_config_entry(options: dict | None = None) -> MagicMock:
    """Create a mock config entry with the given options."""
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.options = options or {}
    entry.runtime_data = AzureSTTRuntimeData()
    return entry


def _mock_hass_with_entry(mock_hass, entry):
    """Set up mock_hass with config_entries that return the given entry."""
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(return_value=[entry])
    mock_hass.config_entries.async_update_entry = MagicMock()
    return mock_hass


class TestAddPhrases:
    """Test add_phrases service."""

    @pytest.mark.asyncio
    async def test_add_new_phrases(self, mock_hass):
        """Adding new phrases should append them to the list."""
        from custom_components.azure_speech_stt.services import (
            async_handle_add_phrases,
        )

        entry = _make_config_entry({"custom_phrases": ["existing"]})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"phrases": ["new1", "new2"]})
        await async_handle_add_phrases(mock_hass, call)

        updated_options = mock_hass.config_entries.async_update_entry.call_args[1][
            "options"
        ]
        assert updated_options["custom_phrases"] == ["existing", "new1", "new2"]

    @pytest.mark.asyncio
    async def test_add_duplicate_phrases_deduped(self, mock_hass):
        """Duplicate phrases should not be added twice."""
        from custom_components.azure_speech_stt.services import (
            async_handle_add_phrases,
        )

        entry = _make_config_entry({"custom_phrases": ["a", "b"]})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"phrases": ["b", "c"]})
        await async_handle_add_phrases(mock_hass, call)

        updated_options = mock_hass.config_entries.async_update_entry.call_args[1][
            "options"
        ]
        assert updated_options["custom_phrases"] == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_add_empty_phrases_noop(self, mock_hass):
        """Empty phrases list should not trigger an update."""
        from custom_components.azure_speech_stt.services import (
            async_handle_add_phrases,
        )

        entry = _make_config_entry()
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"phrases": []})
        await async_handle_add_phrases(mock_hass, call)

        mock_hass.config_entries.async_update_entry.assert_not_called()


class TestRemovePhrases:
    """Test remove_phrases service."""

    @pytest.mark.asyncio
    async def test_remove_existing_phrases(self, mock_hass):
        """Removing existing phrases should filter them out."""
        from custom_components.azure_speech_stt.services import (
            async_handle_remove_phrases,
        )

        entry = _make_config_entry({"custom_phrases": ["a", "b", "c"]})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"phrases": ["b"]})
        await async_handle_remove_phrases(mock_hass, call)

        updated_options = mock_hass.config_entries.async_update_entry.call_args[1][
            "options"
        ]
        assert updated_options["custom_phrases"] == ["a", "c"]

    @pytest.mark.asyncio
    async def test_remove_nonexistent_phrases(self, mock_hass):
        """Removing phrases that don't exist should not error."""
        from custom_components.azure_speech_stt.services import (
            async_handle_remove_phrases,
        )

        entry = _make_config_entry({"custom_phrases": ["a"]})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"phrases": ["z"]})
        await async_handle_remove_phrases(mock_hass, call)

        updated_options = mock_hass.config_entries.async_update_entry.call_args[1][
            "options"
        ]
        assert updated_options["custom_phrases"] == ["a"]


class TestAddReplacements:
    """Test add_replacements service."""

    @pytest.mark.asyncio
    async def test_add_new_replacements(self, mock_hass):
        """Adding new replacement rules should merge them."""
        from custom_components.azure_speech_stt.services import (
            async_handle_add_replacements,
        )

        entry = _make_config_entry({"custom_replacements": {"a": "b"}})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"replacements": {"c": "d"}})
        await async_handle_add_replacements(mock_hass, call)

        updated_options = mock_hass.config_entries.async_update_entry.call_args[1][
            "options"
        ]
        assert updated_options["custom_replacements"] == {"a": "b", "c": "d"}

    @pytest.mark.asyncio
    async def test_update_existing_replacement(self, mock_hass):
        """Updating an existing key should overwrite the value."""
        from custom_components.azure_speech_stt.services import (
            async_handle_add_replacements,
        )

        entry = _make_config_entry({"custom_replacements": {"old": "v1"}})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"replacements": {"old": "v2"}})
        await async_handle_add_replacements(mock_hass, call)

        updated_options = mock_hass.config_entries.async_update_entry.call_args[1][
            "options"
        ]
        assert updated_options["custom_replacements"] == {"old": "v2"}


class TestRemoveReplacements:
    """Test remove_replacements service."""

    @pytest.mark.asyncio
    async def test_remove_existing_keys(self, mock_hass):
        """Removing existing keys should delete them."""
        from custom_components.azure_speech_stt.services import (
            async_handle_remove_replacements,
        )

        entry = _make_config_entry({"custom_replacements": {"a": "1", "b": "2"}})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"keys": ["a"]})
        await async_handle_remove_replacements(mock_hass, call)

        updated_options = mock_hass.config_entries.async_update_entry.call_args[1][
            "options"
        ]
        assert updated_options["custom_replacements"] == {"b": "2"}

    @pytest.mark.asyncio
    async def test_remove_nonexistent_keys(self, mock_hass):
        """Removing keys that don't exist should not error."""
        from custom_components.azure_speech_stt.services import (
            async_handle_remove_replacements,
        )

        entry = _make_config_entry({"custom_replacements": {"a": "1"}})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"keys": ["z"]})
        await async_handle_remove_replacements(mock_hass, call)

        updated_options = mock_hass.config_entries.async_update_entry.call_args[1][
            "options"
        ]
        assert updated_options["custom_replacements"] == {"a": "1"}


class TestGetCorrectionConfig:
    """Test get_correction_config service."""

    @pytest.mark.asyncio
    async def test_returns_full_config(self, mock_hass):
        """Should return all correction-related options."""
        from custom_components.azure_speech_stt.services import (
            async_handle_get_correction_config,
        )

        entry = _make_config_entry(
            {
                "custom_phrases": ["phrase1"],
                "custom_replacements": {"a": "b"},
                "enable_custom_replacements": True,
                "enable_fuzzy_matching": False,
                "fuzzy_threshold": 0.9,
            }
        )
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({})
        result = await async_handle_get_correction_config(mock_hass, call)

        assert result["custom_phrases"] == ["phrase1"]
        assert result["custom_replacements"] == {"a": "b"}
        assert result["enable_custom_replacements"] is True
        assert result["enable_fuzzy_matching"] is False
        assert result["fuzzy_threshold"] == 0.9

    @pytest.mark.asyncio
    async def test_returns_defaults_when_empty(self, mock_hass):
        """Should return defaults when no options are set."""
        from custom_components.azure_speech_stt.services import (
            async_handle_get_correction_config,
        )

        entry = _make_config_entry({})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({})
        result = await async_handle_get_correction_config(mock_hass, call)

        assert result["custom_phrases"] == []
        assert result["custom_replacements"] == {}
        assert result["enable_custom_replacements"] is True
        assert result["enable_fuzzy_matching"] is True
        assert result["fuzzy_threshold"] == 0.80


class TestSetCorrectionConfig:
    """Test set_correction_config service."""

    @pytest.mark.asyncio
    async def test_set_full_config(self, mock_hass):
        """Setting all fields should update all options."""
        from custom_components.azure_speech_stt.services import (
            async_handle_set_correction_config,
        )

        entry = _make_config_entry({})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call(
            {
                "custom_phrases": ["a", "b"],
                "custom_replacements": {"x": "y"},
                "enable_custom_replacements": False,
                "enable_fuzzy_matching": False,
                "fuzzy_threshold": 0.6,
            }
        )
        await async_handle_set_correction_config(mock_hass, call)

        updated = mock_hass.config_entries.async_update_entry.call_args[1]["options"]
        assert updated["custom_phrases"] == ["a", "b"]
        assert updated["custom_replacements"] == {"x": "y"}
        assert updated["enable_custom_replacements"] is False
        assert updated["enable_fuzzy_matching"] is False
        assert updated["fuzzy_threshold"] == 0.6

    @pytest.mark.asyncio
    async def test_set_partial_config(self, mock_hass):
        """Setting partial fields should only update those fields."""
        from custom_components.azure_speech_stt.services import (
            async_handle_set_correction_config,
        )

        entry = _make_config_entry(
            {
                "custom_phrases": ["existing"],
                "custom_replacements": {"old": "val"},
                "fuzzy_threshold": 0.8,
            }
        )
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"custom_phrases": ["new"]})
        await async_handle_set_correction_config(mock_hass, call)

        updated = mock_hass.config_entries.async_update_entry.call_args[1]["options"]
        assert updated["custom_phrases"] == ["new"]
        assert updated["custom_replacements"] == {"old": "val"}
        assert updated["fuzzy_threshold"] == 0.8


class TestAddExclusions:
    """Test add_exclusions service."""

    @pytest.mark.asyncio
    async def test_add_new_exclusions(self, mock_hass):
        """Adding new exclusions should append them."""
        from custom_components.azure_speech_stt.services import (
            async_handle_add_exclusions,
        )

        entry = _make_config_entry({"custom_exclusions": ["existing"]})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"exclusions": ["new1", "new2"]})
        await async_handle_add_exclusions(mock_hass, call)

        updated = mock_hass.config_entries.async_update_entry.call_args[1]["options"]
        assert updated["custom_exclusions"] == ["existing", "new1", "new2"]

    @pytest.mark.asyncio
    async def test_add_duplicate_exclusions_deduped(self, mock_hass):
        """Duplicate exclusions should not be added twice."""
        from custom_components.azure_speech_stt.services import (
            async_handle_add_exclusions,
        )

        entry = _make_config_entry({"custom_exclusions": ["a"]})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"exclusions": ["a", "b"]})
        await async_handle_add_exclusions(mock_hass, call)

        updated = mock_hass.config_entries.async_update_entry.call_args[1]["options"]
        assert updated["custom_exclusions"] == ["a", "b"]


class TestRemoveExclusions:
    """Test remove_exclusions service."""

    @pytest.mark.asyncio
    async def test_remove_existing_exclusions(self, mock_hass):
        """Removing existing exclusions should filter them out."""
        from custom_components.azure_speech_stt.services import (
            async_handle_remove_exclusions,
        )

        entry = _make_config_entry({"custom_exclusions": ["a", "b", "c"]})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"exclusions": ["b"]})
        await async_handle_remove_exclusions(mock_hass, call)

        updated = mock_hass.config_entries.async_update_entry.call_args[1]["options"]
        assert updated["custom_exclusions"] == ["a", "c"]


class TestTestCorrection:
    """Test test_correction service handler."""

    @pytest.mark.asyncio
    async def test_returns_diagnostic_result(self, mock_hass):
        """Should return corrected text, changes, and candidates."""
        from custom_components.azure_speech_stt.services import (
            async_handle_test_correction,
        )
        from custom_components.azure_speech_stt.stt_corrector import SpeechCorrector

        corrector = SpeechCorrector(
            known_phrases=["走廊燈"],
            fuzzy_threshold=0.75,
        )

        # Create entity mock with async_test_correction that delegates
        # to a real corrector (same behavior as the entity's public API)
        async def _test_correction(text):
            corrector.update_phrases(["走廊燈"])
            return corrector.diagnose(text)

        entity = MagicMock()
        entity.async_test_correction = _test_correction

        call = _make_service_call({"text": "走廊等"})

        with patch(
            "custom_components.azure_speech_stt.services._find_stt_entity",
            return_value=entity,
        ):
            result = await async_handle_test_correction(mock_hass, call)

        assert result["original"] == "走廊等"
        assert result["corrected"] == "走廊燈"
        assert len(result["changes"]) == 1
        assert result["changes"][0]["method"] == "fuzzy_match"
        assert isinstance(result["candidates"], list)

    @pytest.mark.asyncio
    async def test_empty_text_raises_error(self, mock_hass):
        """Empty text should raise ServiceValidationError."""
        from homeassistant.exceptions import ServiceValidationError

        from custom_components.azure_speech_stt.services import (
            async_handle_test_correction,
        )

        call = _make_service_call({"text": ""})
        with pytest.raises(ServiceValidationError, match="required"):
            await async_handle_test_correction(mock_hass, call)


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

    def test_set_correction_config_fuzzy_threshold_out_of_range(self):
        """Fuzzy threshold outside 0.5-1.0 should be rejected."""
        from custom_components.azure_speech_stt.services import (
            SCHEMA_SET_CORRECTION_CONFIG,
        )

        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_SET_CORRECTION_CONFIG({"fuzzy_threshold": 0.1})

        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_SET_CORRECTION_CONFIG({"fuzzy_threshold": 1.5})

    def test_set_correction_config_valid_threshold(self):
        """Valid fuzzy threshold should be accepted."""
        from custom_components.azure_speech_stt.services import (
            SCHEMA_SET_CORRECTION_CONFIG,
        )

        result = SCHEMA_SET_CORRECTION_CONFIG({"fuzzy_threshold": 0.75})
        assert result["fuzzy_threshold"] == 0.75

    def test_phrases_schema_rejects_non_list(self):
        """Non-list phrases should be rejected."""
        from custom_components.azure_speech_stt.services import SCHEMA_PHRASES

        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_PHRASES({"phrases": "not-a-list"})

    def test_add_replacements_schema_rejects_non_dict(self):
        """Non-dict replacements should be rejected."""
        from custom_components.azure_speech_stt.services import (
            SCHEMA_ADD_REPLACEMENTS,
        )

        with pytest.raises(vol.MultipleInvalid):
            SCHEMA_ADD_REPLACEMENTS({"replacements": "not-a-dict"})


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

    @pytest.mark.asyncio
    async def test_add_phrases_exceeds_limit(self, mock_hass):
        """Adding phrases beyond MAX_PHRASE_LIST_SIZE should be rejected."""
        from homeassistant.exceptions import ServiceValidationError

        from custom_components.azure_speech_stt.services import (
            MAX_PHRASE_LIST_SIZE,
            async_handle_add_phrases,
        )

        entry = _make_config_entry(
            {"custom_phrases": [f"phrase_{i}" for i in range(MAX_PHRASE_LIST_SIZE)]}
        )
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"phrases": ["one_more"]})
        with pytest.raises(ServiceValidationError, match="maximum size"):
            await async_handle_add_phrases(mock_hass, call)

    @pytest.mark.asyncio
    async def test_add_replacements_exceeds_limit(self, mock_hass):
        """Adding replacements beyond MAX_REPLACEMENT_RULES should be rejected."""
        from homeassistant.exceptions import ServiceValidationError

        from custom_components.azure_speech_stt.services import (
            MAX_REPLACEMENT_RULES,
            async_handle_add_replacements,
        )

        existing = {f"key_{i}": f"val_{i}" for i in range(MAX_REPLACEMENT_RULES)}
        entry = _make_config_entry({"custom_replacements": existing})
        _mock_hass_with_entry(mock_hass, entry)

        call = _make_service_call({"replacements": {"new_key": "new_val"}})
        with pytest.raises(ServiceValidationError, match="maximum"):
            await async_handle_add_replacements(mock_hass, call)

    @pytest.mark.asyncio
    async def test_set_correction_config_replacements_exceeds_limit(self, mock_hass):
        """Setting too many replacement rules should be rejected."""
        from homeassistant.exceptions import ServiceValidationError

        from custom_components.azure_speech_stt.services import (
            MAX_REPLACEMENT_RULES,
            async_handle_set_correction_config,
        )

        entry = _make_config_entry({})
        _mock_hass_with_entry(mock_hass, entry)

        too_many = {f"k{i}": f"v{i}" for i in range(MAX_REPLACEMENT_RULES + 1)}
        call = _make_service_call({"custom_replacements": too_many})
        with pytest.raises(ServiceValidationError, match="maximum"):
            await async_handle_set_correction_config(mock_hass, call)
