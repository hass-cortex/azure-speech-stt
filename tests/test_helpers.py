"""Tests for azure_speech_stt helpers.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.azure_speech_stt.models import AzureSTTRuntimeData


def _make_config_entry(
    entry_id: str = "test_entry_123",
    runtime_data: AzureSTTRuntimeData | None = None,
) -> MagicMock:
    """Create a mock ConfigEntry with optional runtime_data."""
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.runtime_data = (
        runtime_data if runtime_data is not None else AzureSTTRuntimeData()
    )
    return entry


class TestFindSttEntityWithEntry:
    """Test find_stt_entity when a specific entry is provided."""

    def test_find_stt_entity_with_entry(self, mock_hass):
        """Should return entity from runtime_data when entry is provided."""
        from custom_components.azure_speech_stt.helpers import find_stt_entity

        mock_entity = MagicMock()
        entry = _make_config_entry(runtime_data=AzureSTTRuntimeData(entity=mock_entity))

        result = find_stt_entity(mock_hass, entry)

        assert result is mock_entity

    def test_find_stt_entity_with_entry_no_entity(self, mock_hass):
        """Should return None when runtime_data has no entity key."""
        from custom_components.azure_speech_stt.helpers import find_stt_entity

        entry = _make_config_entry(runtime_data=AzureSTTRuntimeData())

        result = find_stt_entity(mock_hass, entry)

        assert result is None

    def test_find_stt_entity_with_entry_no_runtime_data(self, mock_hass):
        """Should return None when entry has no runtime_data attribute."""
        from custom_components.azure_speech_stt.helpers import find_stt_entity

        entry = MagicMock(spec=[])  # No attributes at all
        entry.entry_id = "test"

        # Simulate entry without runtime_data attribute
        entry_no_rd = MagicMock()
        del entry_no_rd.runtime_data

        result = find_stt_entity(mock_hass, entry_no_rd)

        assert result is None


class TestFindSttEntityWithoutEntry:
    """Test find_stt_entity when no entry is specified (search all)."""

    def test_find_stt_entity_without_entry(self, mock_hass):
        """Should find entity from the first matching config entry."""
        from custom_components.azure_speech_stt.helpers import find_stt_entity

        mock_entity = MagicMock()
        cfg_entry = _make_config_entry(
            runtime_data=AzureSTTRuntimeData(entity=mock_entity)
        )
        mock_hass.config_entries.async_entries = MagicMock(return_value=[cfg_entry])

        result = find_stt_entity(mock_hass)

        assert result is mock_entity
        mock_hass.config_entries.async_entries.assert_called_once_with(
            "azure_speech_stt"
        )

    def test_find_stt_entity_no_entries(self, mock_hass):
        """Should return None when no config entries exist."""
        from custom_components.azure_speech_stt.helpers import find_stt_entity

        mock_hass.config_entries.async_entries = MagicMock(return_value=[])

        result = find_stt_entity(mock_hass)

        assert result is None

    def test_find_stt_entity_no_entity_in_runtime_data(self, mock_hass):
        """Should return None when config entries exist but none have entity."""
        from custom_components.azure_speech_stt.helpers import find_stt_entity

        cfg_entry = _make_config_entry(runtime_data=AzureSTTRuntimeData())
        mock_hass.config_entries.async_entries = MagicMock(return_value=[cfg_entry])

        result = find_stt_entity(mock_hass)

        assert result is None

    def test_find_stt_entity_skips_entries_without_runtime_data(self, mock_hass):
        """Should skip entries without runtime_data and find the next one."""
        from custom_components.azure_speech_stt.helpers import find_stt_entity

        # First entry has no runtime_data
        entry_no_rd = MagicMock()
        del entry_no_rd.runtime_data

        # Second entry has the entity
        mock_entity = MagicMock()
        entry_with_entity = _make_config_entry(
            runtime_data=AzureSTTRuntimeData(entity=mock_entity)
        )

        mock_hass.config_entries.async_entries = MagicMock(
            return_value=[entry_no_rd, entry_with_entity]
        )

        result = find_stt_entity(mock_hass)

        assert result is mock_entity

    def test_find_stt_entity_multiple_entries_returns_first(self, mock_hass):
        """Should return the entity from the first matching entry."""
        from custom_components.azure_speech_stt.helpers import find_stt_entity

        entity1 = MagicMock(name="entity1")
        entity2 = MagicMock(name="entity2")
        entry1 = _make_config_entry(
            entry_id="entry1", runtime_data=AzureSTTRuntimeData(entity=entity1)
        )
        entry2 = _make_config_entry(
            entry_id="entry2", runtime_data=AzureSTTRuntimeData(entity=entity2)
        )
        mock_hass.config_entries.async_entries = MagicMock(
            return_value=[entry1, entry2]
        )

        result = find_stt_entity(mock_hass)

        assert result is entity1
