"""Tests for Azure Speech-to-Text config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_flow(mock_hass):
    """Create an AzureSpeechSTTConfigFlow with mocked hass."""
    from custom_components.azure_speech_stt.config_flow import (
        AzureSpeechSTTConfigFlow,
    )

    flow = AzureSpeechSTTConfigFlow()
    flow.hass = mock_hass
    return flow


def _make_options_flow(options=None, entry_id="test_entry"):
    """Create an AzureSpeechSTTOptionsFlow with a mock config entry."""
    from custom_components.azure_speech_stt.config_flow import (
        AzureSpeechSTTOptionsFlow,
    )

    entry = MagicMock()
    entry.entry_id = entry_id
    entry.options = options or {}
    return AzureSpeechSTTOptionsFlow(entry)


class TestConfigFlowUser:
    """Test the user config flow step."""

    @pytest.mark.asyncio
    async def test_show_form_no_input(self, mock_hass):
        """Show form when no user input provided."""
        flow = _make_flow(mock_hass)
        result = await flow.async_step_user(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_valid_credentials_creates_entry(self, mock_hass):
        """Valid key and region should create a config entry."""
        flow = _make_flow(mock_hass)

        # Mock the validation to return success (None = no error)
        with patch(
            "custom_components.azure_speech_stt.config_flow._validate_credentials",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await flow.async_step_user(
                user_input={
                    "speech_key": "valid-key-123",
                    "speech_region": "eastasia",
                }
            )

        assert result["type"] == "create_entry"
        assert result["title"] == "Azure STT (eastasia)"
        assert result["data"]["speech_key"] == "valid-key-123"
        assert result["data"]["speech_region"] == "eastasia"

    @pytest.mark.asyncio
    async def test_invalid_key_shows_error(self, mock_hass):
        """Invalid key should show invalid_key error."""
        flow = _make_flow(mock_hass)

        with patch(
            "custom_components.azure_speech_stt.config_flow._validate_credentials",
            new_callable=AsyncMock,
            return_value="invalid_key",
        ):
            result = await flow.async_step_user(
                user_input={
                    "speech_key": "bad-key",
                    "speech_region": "eastasia",
                }
            )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_key"}

    @pytest.mark.asyncio
    async def test_connection_error_shows_error(self, mock_hass):
        """Connection error should show cannot_connect error."""
        flow = _make_flow(mock_hass)

        with patch(
            "custom_components.azure_speech_stt.config_flow._validate_credentials",
            new_callable=AsyncMock,
            return_value="cannot_connect",
        ):
            result = await flow.async_step_user(
                user_input={
                    "speech_key": "some-key",
                    "speech_region": "eastasia",
                }
            )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "cannot_connect"}


class TestConfigFlowReauth:
    """Test the reauthentication config flow steps."""

    @pytest.mark.asyncio
    async def test_reauth_flow_success(self, mock_hass):
        """New key validates successfully, entry is updated and reloaded."""
        flow = _make_flow(mock_hass)

        # Set up the reauth context
        existing_entry = MagicMock()
        existing_entry.data = {
            "speech_key": "expired-key",
            "speech_region": "eastasia",
        }
        existing_entry.entry_id = "reauth_entry_id"
        flow.context["entry_id"] = "reauth_entry_id"
        mock_hass.config_entries = MagicMock()
        mock_hass.config_entries.async_get_entry = MagicMock(
            return_value=existing_entry
        )

        # Step 1: async_step_reauth should show the confirm form
        result = await flow.async_step_reauth(entry_data=existing_entry.data)
        assert result["type"] == "form"
        assert result["step_id"] == "reauth_confirm"

        # Step 2: Submit new key with successful validation
        with patch(
            "custom_components.azure_speech_stt.config_flow._validate_credentials",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await flow.async_step_reauth_confirm(
                user_input={"speech_key": "new-valid-key"}
            )

        assert result["type"] == "abort"

    @pytest.mark.asyncio
    async def test_reauth_flow_invalid_key(self, mock_hass):
        """Invalid key should show form with error."""
        flow = _make_flow(mock_hass)

        existing_entry = MagicMock()
        existing_entry.data = {
            "speech_key": "expired-key",
            "speech_region": "eastasia",
        }
        existing_entry.entry_id = "reauth_entry_id"
        flow.context["entry_id"] = "reauth_entry_id"
        mock_hass.config_entries = MagicMock()
        mock_hass.config_entries.async_get_entry = MagicMock(
            return_value=existing_entry
        )

        # Trigger reauth to set up state
        await flow.async_step_reauth(entry_data=existing_entry.data)

        # Submit invalid key
        with patch(
            "custom_components.azure_speech_stt.config_flow._validate_credentials",
            new_callable=AsyncMock,
            return_value="invalid_key",
        ):
            result = await flow.async_step_reauth_confirm(
                user_input={"speech_key": "bad-key"}
            )

        assert result["type"] == "form"
        assert result["step_id"] == "reauth_confirm"
        assert result["errors"] == {"base": "invalid_key"}


class TestConfigFlowReconfigure:
    """Test the reconfigure config flow step."""

    @pytest.mark.asyncio
    async def test_reconfigure_shows_form(self, mock_hass):
        """Reconfigure should show form with current values."""
        flow = _make_flow(mock_hass)

        # Mock _get_reconfigure_entry to return existing entry data
        existing_entry = MagicMock()
        existing_entry.data = {
            "speech_key": "old-key",
            "speech_region": "eastus",
        }
        existing_entry.entry_id = "existing_entry"
        flow._get_reconfigure_entry = MagicMock(return_value=existing_entry)

        result = await flow.async_step_reconfigure(user_input=None)
        assert result["type"] == "form"
        assert result["step_id"] == "reconfigure"

    @pytest.mark.asyncio
    async def test_reconfigure_updates_entry(self, mock_hass):
        """Reconfigure with valid credentials should update the entry."""
        flow = _make_flow(mock_hass)

        existing_entry = MagicMock()
        existing_entry.data = {
            "speech_key": "old-key",
            "speech_region": "eastus",
        }
        existing_entry.entry_id = "existing_entry"
        flow._get_reconfigure_entry = MagicMock(return_value=existing_entry)

        with patch(
            "custom_components.azure_speech_stt.config_flow._validate_credentials",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await flow.async_step_reconfigure(
                user_input={
                    "speech_key": "new-key",
                    "speech_region": "westus2",
                }
            )

        assert result["type"] == "abort"


class TestValidateCredentials:
    """Test the _validate_credentials helper function."""

    @pytest.mark.asyncio
    async def test_valid_returns_none(self):
        """200 response should return None (no error)."""
        from custom_components.azure_speech_stt.config_flow import (
            _validate_credentials,
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        result = await _validate_credentials(mock_session, "valid-key", "eastasia")
        assert result is None

    @pytest.mark.asyncio
    async def test_401_returns_invalid_key(self):
        """401 response should return 'invalid_key'."""
        from custom_components.azure_speech_stt.config_flow import (
            _validate_credentials,
        )

        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)

        result = await _validate_credentials(mock_session, "bad-key", "eastasia")
        assert result == "invalid_key"

    @pytest.mark.asyncio
    async def test_connection_error_returns_cannot_connect(self):
        """Connection error should return 'cannot_connect'."""
        import aiohttp

        from custom_components.azure_speech_stt.config_flow import (
            _validate_credentials,
        )

        mock_session = MagicMock()
        mock_session.post = MagicMock(
            side_effect=aiohttp.ClientError("Connection refused")
        )

        result = await _validate_credentials(mock_session, "some-key", "eastasia")
        assert result == "cannot_connect"

    @pytest.mark.asyncio
    async def test_timeout_returns_cannot_connect(self):
        """Timeout should return 'cannot_connect'."""
        from custom_components.azure_speech_stt.config_flow import (
            _validate_credentials,
        )

        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=TimeoutError())

        result = await _validate_credentials(mock_session, "some-key", "eastasia")
        assert result == "cannot_connect"


class TestOptionsFlowInit:
    """Test the single-page options flow."""

    @pytest.mark.asyncio
    async def test_init_shows_form(self):
        """Init step should show form with defaults."""
        flow = _make_options_flow()
        result = await flow.async_step_init(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_init_creates_entry(self):
        """Init step with input should create entry directly."""
        flow = _make_options_flow()
        result = await flow.async_step_init(
            user_input={
                "stage_1": {
                    "enable_entity_hints": False,
                    "custom_phrases": ["living room", "kitchen"],
                },
                "stage_2": {
                    "enable_custom_replacements": True,
                    "custom_replacements": ["bad=good", "wrong=right"],
                },
                "stage_3": {
                    "enable_fuzzy_matching": True,
                    "fuzzy_threshold": 0.8,
                },
            }
        )

        assert result["type"] == "create_entry"
        data = result["data"]
        assert data["enable_entity_hints"] is False
        assert data["fuzzy_threshold"] == 0.8
        assert data["custom_phrases"] == ["living room", "kitchen"]
        assert data["custom_replacements"] == {"bad": "good", "wrong": "right"}

    @pytest.mark.asyncio
    async def test_init_parses_replacements(self):
        """Init step should parse wrong=correct entries from list."""
        flow = _make_options_flow()
        result = await flow.async_step_init(
            user_input={
                "stage_1": {
                    "enable_entity_hints": True,
                    "custom_phrases": [],
                },
                "stage_2": {
                    "enable_custom_replacements": True,
                    "custom_replacements": ["oops=fixed", "typo=correct"],
                },
                "stage_3": {
                    "enable_fuzzy_matching": True,
                    "fuzzy_threshold": 0.75,
                },
            }
        )

        assert result["type"] == "create_entry"
        assert result["data"]["custom_replacements"] == {
            "oops": "fixed",
            "typo": "correct",
        }

    @pytest.mark.asyncio
    async def test_init_handles_empty_phrases_and_replacements(self):
        """Init step should handle empty phrases and replacements."""
        flow = _make_options_flow()
        result = await flow.async_step_init(
            user_input={
                "stage_1": {
                    "enable_entity_hints": True,
                    "custom_phrases": [],
                },
                "stage_2": {
                    "enable_custom_replacements": True,
                    "custom_replacements": [],
                },
                "stage_3": {
                    "enable_fuzzy_matching": True,
                    "fuzzy_threshold": 0.75,
                },
            }
        )

        assert result["type"] == "create_entry"
        assert result["data"]["custom_phrases"] == []
        assert result["data"]["custom_replacements"] == {}

    @pytest.mark.asyncio
    async def test_init_shows_form_with_existing_options(self):
        """Init step should show form pre-filled with existing options."""
        flow = _make_options_flow(
            options={
                "enable_entity_hints": True,
                "fuzzy_threshold": 0.9,
                "custom_phrases": ["hello"],
                "custom_replacements": {"bad": "good"},
            }
        )
        result = await flow.async_step_init(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_init_saves_api_modes(self):
        """Init step should save api_modes selection."""
        flow = _make_options_flow()
        result = await flow.async_step_init(
            user_input={
                "api_modes": ["fast_transcription"],
                "stage_1": {
                    "enable_entity_hints": True,
                    "custom_phrases": [],
                },
                "stage_2": {
                    "enable_custom_replacements": True,
                    "custom_replacements": [],
                },
                "stage_3": {
                    "enable_fuzzy_matching": True,
                    "fuzzy_threshold": 0.8,
                },
            }
        )

        assert result["type"] == "create_entry"
        assert result["data"]["api_modes"] == ["fast_transcription"]

    @pytest.mark.asyncio
    async def test_init_defaults_api_modes_when_missing(self):
        """Init step should default to both APIs when api_modes not provided."""
        flow = _make_options_flow()
        result = await flow.async_step_init(
            user_input={
                "stage_1": {
                    "enable_entity_hints": True,
                    "custom_phrases": [],
                },
                "stage_2": {
                    "enable_custom_replacements": True,
                    "custom_replacements": [],
                },
                "stage_3": {
                    "enable_fuzzy_matching": True,
                    "fuzzy_threshold": 0.8,
                },
            }
        )

        assert result["type"] == "create_entry"
        assert result["data"]["api_modes"] == ["fast_transcription", "realtime"]

    @pytest.mark.asyncio
    async def test_init_empty_api_modes_defaults_to_both(self):
        """Init step should default to both APIs when api_modes is empty list."""
        flow = _make_options_flow()
        result = await flow.async_step_init(
            user_input={
                "api_modes": [],
                "stage_1": {
                    "enable_entity_hints": True,
                    "custom_phrases": [],
                },
                "stage_2": {
                    "enable_custom_replacements": True,
                    "custom_replacements": [],
                },
                "stage_3": {
                    "enable_fuzzy_matching": True,
                    "fuzzy_threshold": 0.8,
                },
            }
        )

        assert result["type"] == "create_entry"
        assert result["data"]["api_modes"] == ["fast_transcription", "realtime"]

    @pytest.mark.asyncio
    async def test_init_shows_existing_api_modes(self):
        """Init step should pre-fill existing api_modes selection."""
        flow = _make_options_flow(
            options={
                "api_modes": ["realtime"],
                "enable_entity_hints": True,
            }
        )
        result = await flow.async_step_init(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"


class TestAsyncGetOptionsFlow:
    """Test the options flow factory method."""

    def test_returns_options_flow(self):
        """async_get_options_flow should return AzureSpeechSTTOptionsFlow."""
        from custom_components.azure_speech_stt.config_flow import (
            AzureSpeechSTTConfigFlow,
            AzureSpeechSTTOptionsFlow,
        )

        entry = MagicMock()
        entry.options = {}

        flow = AzureSpeechSTTConfigFlow.async_get_options_flow(entry)
        assert isinstance(flow, AzureSpeechSTTOptionsFlow)
