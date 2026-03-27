"""Tests for Azure Speech-to-Text sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.azure_speech_stt.models import (
    AzureSTTRuntimeData,
    TranscriptionStats,
)
from custom_components.azure_speech_stt.sensor import (
    SENSOR_DESCRIPTIONS,
    AzureSTTSensor,
    AzureSTTSensorDescription,
    async_setup_entry,
)


def _make_config_entry(entry_id: str = "test_entry") -> MagicMock:
    """Create a mock ConfigEntry with runtime_data."""
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.runtime_data = AzureSTTRuntimeData()
    return entry


def _make_sensor(
    description: AzureSTTSensorDescription | None = None,
    entry_id: str = "test_entry",
) -> AzureSTTSensor:
    """Create a sensor with the given description."""
    entry = _make_config_entry(entry_id)
    desc = description or SENSOR_DESCRIPTIONS[0]
    return AzureSTTSensor(entry, desc)


def _make_stats(
    *,
    success: bool = True,
    api_error: bool = False,
    duration_ms: float = 450.0,
    audio_bytes: int = 32000,
    audio_seconds: float = 1.0,
    language: str = "en-US",
    api_used: str = "fast_transcription",
    raw_text: str | None = "hello world",
    avg_duration_ms: float | None = 450.0,
) -> TranscriptionStats:
    """Create a TranscriptionStats with sensible defaults for success."""
    return TranscriptionStats(
        success=success,
        api_error=api_error,
        duration_ms=duration_ms,
        audio_bytes=audio_bytes,
        audio_seconds=audio_seconds,
        language=language,
        api_used=api_used,
        raw_text=raw_text,
        avg_duration_ms=avg_duration_ms,
    )


# Convenience aliases for common scenarios
_success_stats = _make_stats


def _error_stats(**kwargs: object) -> TranscriptionStats:
    """Create an API error TranscriptionStats."""
    return _make_stats(
        **{
            "success": False,
            "api_error": True,
            "duration_ms": 200.0,
            "audio_bytes": 16000,
            "audio_seconds": 0.5,
            "raw_text": None,
            "avg_duration_ms": None,
            **kwargs,
        }
    )


def _no_speech_stats(**kwargs: object) -> TranscriptionStats:
    """Create a no-speech TranscriptionStats."""
    return _make_stats(
        **{
            "success": False,
            "duration_ms": 300.0,
            "audio_bytes": 16000,
            "audio_seconds": 0.5,
            "raw_text": None,
            "avg_duration_ms": None,
            **kwargs,
        }
    )


def _find_description(key: str) -> AzureSTTSensorDescription:
    """Find a sensor description by key."""
    for desc in SENSOR_DESCRIPTIONS:
        if desc.key == key:
            return desc
    raise ValueError(f"No sensor description with key '{key}'")


class TestSensorCreation:
    """Test sensor entity attributes."""

    def test_unique_id(self):
        """Sensor unique_id should combine domain, entry_id, and key."""
        sensor = _make_sensor(entry_id="abc123")
        assert sensor._attr_unique_id == "azure_speech_stt_abc123_total_requests"

    def test_device_info(self):
        """Sensor device_info should reference the config entry."""
        sensor = _make_sensor(entry_id="abc123")
        assert sensor._attr_device_info == {
            "identifiers": {("azure_speech_stt", "abc123")}
        }

    def test_has_entity_name(self):
        """Sensor should use entity name pattern."""
        sensor = _make_sensor()
        assert sensor.has_entity_name is True

    def test_should_poll_is_false(self):
        """Sensor should not poll."""
        sensor = _make_sensor()
        assert sensor._attr_should_poll is False

    def test_entity_description_assigned(self):
        """Sensor description should be stored."""
        desc = _find_description("last_duration")
        sensor = _make_sensor(description=desc)
        assert sensor.entity_description is desc


class TestAsyncSetupEntry:
    """Test async_setup_entry creates all sensors."""

    @pytest.mark.asyncio
    async def test_creates_all_sensors(self):
        """Should create one sensor per description."""
        hass = MagicMock()
        entry = _make_config_entry()
        added: list[object] = []

        def async_add_entities(entities):
            added.extend(entities)

        await async_setup_entry(hass, entry, async_add_entities)

        assert len(added) == len(SENSOR_DESCRIPTIONS)
        keys = {s.entity_description.key for s in added}
        expected_keys = {d.key for d in SENSOR_DESCRIPTIONS}
        assert keys == expected_keys


class TestAsyncAddedToHass:
    """Test sensor registration and state restore."""

    @pytest.mark.asyncio
    async def test_registers_with_runtime_data(self):
        """Sensor should register itself in runtime_data.sensors."""
        entry = _make_config_entry()
        sensor = AzureSTTSensor(entry, SENSOR_DESCRIPTIONS[0])
        assert sensor not in entry.runtime_data.sensors

        await sensor.async_added_to_hass()

        assert sensor in entry.runtime_data.sensors

    @pytest.mark.asyncio
    async def test_restores_last_sensor_data(self):
        """Sensor should restore previous value on startup."""
        entry = _make_config_entry()
        sensor = AzureSTTSensor(entry, SENSOR_DESCRIPTIONS[0])

        # Mock RestoreSensor state restore
        mock_data = MagicMock()
        mock_data.native_value = 42
        sensor.async_get_last_sensor_data = AsyncMock(return_value=mock_data)

        await sensor.async_added_to_hass()

        assert sensor._attr_native_value == 42

    @pytest.mark.asyncio
    async def test_no_restore_when_no_data(self):
        """Sensor should keep None when no previous data exists."""
        entry = _make_config_entry()
        sensor = AzureSTTSensor(entry, SENSOR_DESCRIPTIONS[0])
        # Default mock returns None
        await sensor.async_added_to_hass()

        assert sensor._attr_native_value is None

    @pytest.mark.asyncio
    async def test_no_restore_when_native_value_is_none(self):
        """Sensor should skip restore when native_value is None."""
        entry = _make_config_entry()
        sensor = AzureSTTSensor(entry, SENSOR_DESCRIPTIONS[0])

        mock_data = MagicMock()
        mock_data.native_value = None
        sensor.async_get_last_sensor_data = AsyncMock(return_value=mock_data)

        await sensor.async_added_to_hass()

        assert sensor._attr_native_value is None


class TestAsyncWillRemoveFromHass:
    """Test sensor unregistration."""

    @pytest.mark.asyncio
    async def test_unregisters_from_runtime_data(self):
        """Sensor should remove itself from runtime_data.sensors."""
        entry = _make_config_entry()
        sensor = AzureSTTSensor(entry, SENSOR_DESCRIPTIONS[0])

        await sensor.async_added_to_hass()
        assert sensor in entry.runtime_data.sensors

        await sensor.async_will_remove_from_hass()
        assert sensor not in entry.runtime_data.sensors

    @pytest.mark.asyncio
    async def test_remove_nonexistent_sensor_no_error(self):
        """Removing a sensor not in list should not raise."""
        entry = _make_config_entry()
        sensor = AzureSTTSensor(entry, SENSOR_DESCRIPTIONS[0])
        # Don't add it first — remove should be a no-op
        await sensor.async_will_remove_from_hass()


class TestHandleTranscription:
    """Test each sensor description's update_fn via handle_transcription."""

    def test_total_requests_increments(self):
        """Total requests should increment on any transcription."""
        sensor = _make_sensor(_find_description("total_requests"))
        sensor.handle_transcription(_success_stats())
        assert sensor._attr_native_value == 1
        sensor.handle_transcription(_error_stats())
        assert sensor._attr_native_value == 2
        sensor.handle_transcription(_no_speech_stats())
        assert sensor._attr_native_value == 3

    def test_successful_requests_increments_on_success(self):
        """Successful requests should only increment on success."""
        sensor = _make_sensor(_find_description("successful_requests"))
        sensor.handle_transcription(_success_stats())
        assert sensor._attr_native_value == 1
        sensor.handle_transcription(_error_stats())
        assert sensor._attr_native_value == 1  # unchanged
        sensor.handle_transcription(_success_stats())
        assert sensor._attr_native_value == 2

    def test_failed_requests_increments_on_api_error(self):
        """Failed requests should only increment on api_error."""
        sensor = _make_sensor(_find_description("failed_requests"))
        sensor.handle_transcription(_error_stats())
        assert sensor._attr_native_value == 1
        sensor.handle_transcription(_success_stats())
        assert sensor._attr_native_value == 1  # unchanged
        sensor.handle_transcription(_no_speech_stats())
        assert sensor._attr_native_value == 1  # no_speech is not api_error

    def test_last_duration_updates_on_success(self):
        """Last duration should update only on success."""
        sensor = _make_sensor(_find_description("last_duration"))
        sensor.handle_transcription(_success_stats(duration_ms=500.123))
        assert sensor._attr_native_value == 500.1
        sensor.handle_transcription(_error_stats(duration_ms=100.0))
        assert sensor._attr_native_value == 500.1  # unchanged on error

    def test_average_duration_updates_on_success(self):
        """Average duration should update from stats.avg_duration_ms."""
        sensor = _make_sensor(_find_description("average_duration"))
        sensor.handle_transcription(_success_stats(avg_duration_ms=300.456))
        assert sensor._attr_native_value == 300.5
        sensor.handle_transcription(_error_stats())
        assert sensor._attr_native_value == 300.5  # unchanged on error

    def test_average_duration_skips_when_none(self):
        """Average duration should not update when avg_duration_ms is None."""
        sensor = _make_sensor(_find_description("average_duration"))
        sensor.handle_transcription(_success_stats(avg_duration_ms=None))
        assert sensor._attr_native_value is None

    def test_last_audio_size_updates_on_success(self):
        """Last audio size should update only on success."""
        sensor = _make_sensor(_find_description("last_audio_size"))
        sensor.handle_transcription(_success_stats(audio_bytes=64000))
        assert sensor._attr_native_value == 64000
        sensor.handle_transcription(_error_stats(audio_bytes=32000))
        assert sensor._attr_native_value == 64000  # unchanged

    def test_total_audio_duration_accumulates(self):
        """Total audio duration should accumulate minutes on success."""
        sensor = _make_sensor(_find_description("total_audio_duration"))
        sensor.handle_transcription(_success_stats(audio_seconds=60.0))
        assert sensor._attr_native_value == 1.0  # 60s = 1 min
        sensor.handle_transcription(_success_stats(audio_seconds=30.0))
        assert sensor._attr_native_value == 1.5  # 90s = 1.5 min

    def test_total_audio_duration_unchanged_on_error(self):
        """Total audio duration should not change on error."""
        sensor = _make_sensor(_find_description("total_audio_duration"))
        sensor.handle_transcription(_success_stats(audio_seconds=60.0))
        sensor.handle_transcription(_error_stats(audio_seconds=30.0))
        assert sensor._attr_native_value == 1.0

    def test_last_audio_duration_updates_on_success(self):
        """Last audio duration should update on success."""
        sensor = _make_sensor(_find_description("last_audio_duration"))
        sensor.handle_transcription(_success_stats(audio_seconds=2.567))
        assert sensor._attr_native_value == 2.6

    def test_last_raw_text_updates_on_success(self):
        """Last raw text should show transcribed text on success."""
        sensor = _make_sensor(_find_description("last_raw_text"))
        sensor.handle_transcription(_success_stats(raw_text="hello world"))
        assert sensor._attr_native_value == "hello world"

    def test_last_raw_text_clears_on_no_speech(self):
        """Last raw text should be None on no speech."""
        sensor = _make_sensor(_find_description("last_raw_text"))
        sensor.handle_transcription(_success_stats(raw_text="hello"))
        sensor.handle_transcription(_no_speech_stats())
        assert sensor._attr_native_value is None

    def test_last_raw_text_keeps_on_api_error(self):
        """Last raw text should keep previous value on API error."""
        sensor = _make_sensor(_find_description("last_raw_text"))
        sensor.handle_transcription(_success_stats(raw_text="hello"))
        sensor.handle_transcription(_error_stats())
        assert sensor._attr_native_value == "hello"

    def test_last_result_shows_success(self):
        """Last result should show 'success' on success."""
        sensor = _make_sensor(_find_description("last_result"))
        sensor.handle_transcription(_success_stats())
        assert sensor._attr_native_value == "success"

    def test_last_result_shows_api_error(self):
        """Last result should show 'api_error' on API error."""
        sensor = _make_sensor(_find_description("last_result"))
        sensor.handle_transcription(_error_stats())
        assert sensor._attr_native_value == "api_error"

    def test_last_result_shows_no_speech(self):
        """Last result should show 'no_speech' when no speech detected."""
        sensor = _make_sensor(_find_description("last_result"))
        sensor.handle_transcription(_no_speech_stats())
        assert sensor._attr_native_value == "no_speech"

    def test_last_language_always_updates(self):
        """Last language should update on any transcription."""
        sensor = _make_sensor(_find_description("last_language"))
        sensor.handle_transcription(_success_stats(language="zh-TW"))
        assert sensor._attr_native_value == "zh-TW"
        sensor.handle_transcription(_error_stats(language="en-US"))
        assert sensor._attr_native_value == "en-US"

    def test_last_api_used_updates_when_nonempty(self):
        """Last API used should update when api_used is not empty."""
        sensor = _make_sensor(_find_description("last_api_used"))
        sensor.handle_transcription(_success_stats(api_used="realtime"))
        assert sensor._attr_native_value == "realtime"

    def test_last_api_used_keeps_on_empty(self):
        """Last API used should keep previous value when api_used is empty."""
        sensor = _make_sensor(_find_description("last_api_used"))
        sensor.handle_transcription(_success_stats(api_used="fast_transcription"))
        sensor.handle_transcription(_error_stats(api_used=""))
        assert sensor._attr_native_value == "fast_transcription"


class TestStateWrite:
    """Test that async_write_ha_state is called only when value changes."""

    def test_writes_state_on_change(self):
        """Should call async_write_ha_state when value changes."""
        sensor = _make_sensor(_find_description("total_requests"))
        sensor.async_write_ha_state = MagicMock()

        sensor.handle_transcription(_success_stats())

        sensor.async_write_ha_state.assert_called_once()

    def test_no_state_write_when_unchanged(self):
        """Should not call async_write_ha_state when value stays the same."""
        sensor = _make_sensor(_find_description("last_duration"))
        sensor.async_write_ha_state = MagicMock()

        # First: set a value
        sensor.handle_transcription(_success_stats(duration_ms=500.0))
        sensor.async_write_ha_state.reset_mock()

        # Second: same value -> no write
        sensor.handle_transcription(_success_stats(duration_ms=500.0))
        sensor.async_write_ha_state.assert_not_called()

    def test_no_state_write_on_error_for_success_only_sensor(self):
        """Success-only sensors should not write state on error."""
        sensor = _make_sensor(_find_description("last_audio_size"))
        sensor.async_write_ha_state = MagicMock()

        sensor.handle_transcription(_error_stats())

        sensor.async_write_ha_state.assert_not_called()
