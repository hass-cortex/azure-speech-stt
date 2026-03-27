"""Tests for Azure Speech-to-Text diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.azure_speech_stt.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.azure_speech_stt.models import AzureSTTRuntimeData


def _make_entry(data: dict | None = None, options: dict | None = None) -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = data or {
        "speech_key": "secret-api-key-123",
        "speech_region": "eastasia",
    }
    entry.options = options or {"enable_entity_hints": True}
    entry.runtime_data = AzureSTTRuntimeData()
    return entry


class TestDiagnostics:
    """Test diagnostics output."""

    @pytest.mark.asyncio
    async def test_redacts_speech_key(self):
        """API key should be redacted in diagnostics output."""
        hass = MagicMock()
        entry = _make_entry()

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["config_entry"]["data"]["speech_key"] == "**REDACTED**"
        assert result["config_entry"]["data"]["speech_region"] == "eastasia"

    @pytest.mark.asyncio
    async def test_includes_options(self):
        """Options should be included unredacted."""
        hass = MagicMock()
        entry = _make_entry(options={"enable_entity_hints": False})

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert result["config_entry"]["options"]["enable_entity_hints"] is False

    @pytest.mark.asyncio
    async def test_structure(self):
        """Diagnostics should have expected structure."""
        hass = MagicMock()
        entry = _make_entry()

        result = await async_get_config_entry_diagnostics(hass, entry)

        assert "config_entry" in result
        assert "data" in result["config_entry"]
        assert "options" in result["config_entry"]
