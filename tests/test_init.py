"""Tests for azure_speech_stt __init__.py (setup/unload/options update)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.azure_speech_stt.models import AzureSTTRuntimeData


def _make_config_entry(
    data: dict | None = None,
    options: dict | None = None,
    entry_id: str = "test_entry_123",
) -> MagicMock:
    """Create a mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = entry_id
    entry.data = data or {
        "speech_key": "test-key",
        "speech_region": "eastasia",
    }
    entry.options = options or {}
    entry.runtime_data = AzureSTTRuntimeData()

    # Track update_listener callbacks registered via add_update_listener
    _listeners: list = []

    def _add_update_listener(listener):
        _listeners.append(listener)
        return lambda: _listeners.remove(listener)

    entry.add_update_listener = MagicMock(side_effect=_add_update_listener)
    entry._listeners = _listeners

    # async_on_unload should just call the callback registration
    entry.async_on_unload = MagicMock(side_effect=lambda unsub: unsub)

    return entry


def _mock_token_response(status: int = 200, text: str = "token-value"):
    """Create a mock aiohttp response for token endpoint."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.text = AsyncMock(return_value=text)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    return mock_cm


class TestAsyncSetupEntry:
    """Test async_setup_entry in __init__.py."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(self, mock_hass):
        """Successful token validation should forward entry setup."""
        entry = _make_config_entry()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=_mock_token_response(status=200))

        with patch(
            "custom_components.azure_speech_stt.async_get_clientsession",
            return_value=mock_session,
        ):
            mock_hass.config_entries.async_forward_entry_setups = AsyncMock()

            from custom_components.azure_speech_stt import async_setup_entry

            result = await async_setup_entry(mock_hass, entry)

        assert result is True
        mock_hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
            entry, ["stt", "sensor"]
        )

    @pytest.mark.asyncio
    async def test_async_setup_entry_auth_failed(self, mock_hass):
        """HTTP 401 from token endpoint should raise ConfigEntryAuthFailed."""
        from homeassistant.config_entries import ConfigEntryAuthFailed

        entry = _make_config_entry()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(
            return_value=_mock_token_response(status=401, text="Unauthorized")
        )

        with patch(
            "custom_components.azure_speech_stt.async_get_clientsession",
            return_value=mock_session,
        ):
            from custom_components.azure_speech_stt import async_setup_entry

            with pytest.raises(ConfigEntryAuthFailed):
                await async_setup_entry(mock_hass, entry)

    @pytest.mark.asyncio
    async def test_async_setup_entry_forbidden_raises_auth_failed(self, mock_hass):
        """HTTP 403 from token endpoint should raise ConfigEntryAuthFailed."""
        from homeassistant.config_entries import ConfigEntryAuthFailed

        entry = _make_config_entry()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(
            return_value=_mock_token_response(status=403, text="Forbidden")
        )

        with patch(
            "custom_components.azure_speech_stt.async_get_clientsession",
            return_value=mock_session,
        ):
            from custom_components.azure_speech_stt import async_setup_entry

            with pytest.raises(ConfigEntryAuthFailed):
                await async_setup_entry(mock_hass, entry)

    @pytest.mark.asyncio
    async def test_async_setup_entry_not_ready(self, mock_hass):
        """HTTP 500 from token endpoint should raise ConfigEntryNotReady."""
        from homeassistant.config_entries import ConfigEntryNotReady

        entry = _make_config_entry()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(
            return_value=_mock_token_response(status=500, text="Server Error")
        )

        with patch(
            "custom_components.azure_speech_stt.async_get_clientsession",
            return_value=mock_session,
        ):
            from custom_components.azure_speech_stt import async_setup_entry

            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(mock_hass, entry)

    @pytest.mark.asyncio
    async def test_async_setup_entry_connection_error(self, mock_hass):
        """Connection error should raise ConfigEntryNotReady."""
        from homeassistant.config_entries import ConfigEntryNotReady

        entry = _make_config_entry()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(
            side_effect=aiohttp.ClientConnectionError("Connection refused")
        )

        with patch(
            "custom_components.azure_speech_stt.async_get_clientsession",
            return_value=mock_session,
        ):
            from custom_components.azure_speech_stt import async_setup_entry

            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(mock_hass, entry)

    @pytest.mark.asyncio
    async def test_async_setup_entry_timeout_error(self, mock_hass):
        """Timeout should raise ConfigEntryNotReady."""
        from homeassistant.config_entries import ConfigEntryNotReady

        entry = _make_config_entry()

        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=TimeoutError("Request timed out"))

        with patch(
            "custom_components.azure_speech_stt.async_get_clientsession",
            return_value=mock_session,
        ):
            from custom_components.azure_speech_stt import async_setup_entry

            with pytest.raises(ConfigEntryNotReady):
                await async_setup_entry(mock_hass, entry)


class TestAsyncUnloadEntry:
    """Test async_unload_entry."""

    @pytest.mark.asyncio
    async def test_async_unload_entry_success(self, mock_hass):
        """Unload should call async_unload_platforms."""
        entry = _make_config_entry()
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        from custom_components.azure_speech_stt import async_unload_entry

        result = await async_unload_entry(mock_hass, entry)

        assert result is True
        mock_hass.config_entries.async_unload_platforms.assert_awaited_once_with(
            entry, ["stt", "sensor"]
        )

    @pytest.mark.asyncio
    async def test_async_unload_entry_failure(self, mock_hass):
        """Unload returning False should propagate."""
        entry = _make_config_entry()
        mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

        from custom_components.azure_speech_stt import async_unload_entry

        result = await async_unload_entry(mock_hass, entry)

        assert result is False


class TestUpdateOptions:
    """Test _async_update_options listener."""

    @pytest.mark.asyncio
    async def test_update_options_rebuilds_phrase_builder(self, mock_hass):
        """Options update should call rebuild_phrase_builder on the entity."""
        entry = _make_config_entry()

        # Simulate an entity stored in runtime_data
        mock_entity = MagicMock()
        mock_entity.rebuild_phrase_builder = MagicMock()
        entry.runtime_data = AzureSTTRuntimeData(entity=mock_entity)

        from custom_components.azure_speech_stt import _async_update_options

        await _async_update_options(mock_hass, entry)

        mock_entity.rebuild_phrase_builder.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_options_no_entity(self, mock_hass):
        """Options update with no entity should not raise."""
        entry = _make_config_entry()
        entry.runtime_data = AzureSTTRuntimeData()

        from custom_components.azure_speech_stt import _async_update_options

        # Should not raise
        await _async_update_options(mock_hass, entry)
