"""Tests for AzureSpeechSTTEntity."""

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
    return entry


def _setup_empty_registries(mock_hass: MagicMock) -> None:
    """Set up empty entity, area, device, and floor registries."""
    import homeassistant.helpers.area_registry as ar
    import homeassistant.helpers.device_registry as dr
    import homeassistant.helpers.entity_registry as er
    import homeassistant.helpers.floor_registry as fr

    ent_reg = MagicMock()
    ent_reg.entities = MagicMock()
    ent_reg.entities.values.return_value = []
    er.async_get.return_value = ent_reg

    area_reg = MagicMock()
    area_reg.async_list_areas.return_value = []
    ar.async_get.return_value = area_reg

    dev_reg = MagicMock()
    dev_reg.devices = MagicMock()
    dev_reg.devices.values.return_value = []
    dr.async_get.return_value = dev_reg

    floor_reg = MagicMock()
    floor_reg.async_list_floors.return_value = []
    fr.async_get.return_value = floor_reg


async def _audio_stream(chunks: list[bytes]):
    """Create an async iterable of audio chunks."""
    for chunk in chunks:
        yield chunk


async def _empty_audio_stream():
    """Create an empty async iterable."""
    return
    yield  # make it an async generator


def _mock_aiohttp_response(
    status: int = 200,
    json_data: dict | None = None,
    text: str = "",
) -> MagicMock:
    """Create a mock aiohttp response.

    Args:
        status: HTTP status code.
        json_data: JSON response body (for 200 responses).
        text: Text response body (for error responses).

    Returns:
        A mock that behaves as an aiohttp response context manager.
    """
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data or {})
    mock_resp.text = AsyncMock(return_value=text)

    # Make it work as async context manager (session.post(...) as resp)
    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_post_cm.__aexit__ = AsyncMock(return_value=False)

    return mock_post_cm, mock_resp


def _make_mock_session(mock_post_cm: MagicMock) -> MagicMock:
    """Create a mock aiohttp.ClientSession that returns the given post context manager.

    Args:
        mock_post_cm: The context manager returned by session.post().

    Returns:
        A mock ClientSession (not wrapped in context manager since the client
        receives the session directly).
    """
    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=mock_post_cm)
    return mock_session


@pytest.fixture
def mock_config_entry():
    """Create a default mock config entry."""
    return _make_config_entry()


@pytest.fixture
def stt_entity(mock_hass, mock_config_entry):
    """Create an AzureSpeechSTTEntity with mocked dependencies."""
    _setup_empty_registries(mock_hass)

    mock_session = AsyncMock()
    with patch(
        "custom_components.azure_speech_stt.stt.async_get_clientsession",
        return_value=mock_session,
    ):
        from custom_components.azure_speech_stt.stt import AzureSpeechSTTEntity

        return AzureSpeechSTTEntity(mock_hass, mock_config_entry)


def _create_entity_with_session(mock_hass, entry, mock_session):
    """Create an AzureSpeechSTTEntity with a specific mock session."""
    _setup_empty_registries(mock_hass)
    with patch(
        "custom_components.azure_speech_stt.stt.async_get_clientsession",
        return_value=mock_session,
    ):
        from custom_components.azure_speech_stt.stt import AzureSpeechSTTEntity

        return AzureSpeechSTTEntity(mock_hass, entry)


class TestProperties:
    """Test the 6 abstract STT properties."""

    def test_supported_languages(self, stt_entity):
        """Should return all Azure Fast Transcription supported locales."""
        langs = stt_entity.supported_languages
        assert isinstance(langs, list)
        assert len(langs) > 50  # 95 locales
        assert "zh-CN" in langs
        assert "en-US" in langs
        assert "ja-JP" in langs

    def test_supported_languages_includes_all_locales(self, stt_entity):
        """Supported languages should not depend on config options."""
        from custom_components.azure_speech_stt.const import SUPPORTED_LOCALES

        assert set(stt_entity.supported_languages) == set(SUPPORTED_LOCALES.keys())

    def test_supported_formats(self, stt_entity):
        """Should support WAV and OGG."""
        from homeassistant.components.stt import AudioFormats

        assert stt_entity.supported_formats == [AudioFormats.WAV, AudioFormats.OGG]

    def test_supported_codecs(self, stt_entity):
        """Should support PCM and OPUS."""
        from homeassistant.components.stt import AudioCodecs

        assert stt_entity.supported_codecs == [AudioCodecs.PCM, AudioCodecs.OPUS]

    def test_supported_bit_rates(self, stt_entity):
        """Should support 16-bit."""
        from homeassistant.components.stt import AudioBitRates

        assert stt_entity.supported_bit_rates == [AudioBitRates.BITRATE_16]

    def test_supported_sample_rates(self, stt_entity):
        """Should support 16000 Hz."""
        from homeassistant.components.stt import AudioSampleRates

        assert stt_entity.supported_sample_rates == [AudioSampleRates.SAMPLERATE_16000]

    def test_supported_channels(self, stt_entity):
        """Should support mono."""
        from homeassistant.components.stt import AudioChannels

        assert stt_entity.supported_channels == [AudioChannels.CHANNEL_MONO]


class TestAsyncProcessAudioStream:
    """Test the main audio processing method."""

    @pytest.mark.asyncio
    async def test_recognized_chinese_text_with_known_phrases(self, mock_hass):
        """Chinese text should be corrected by pinyin matching when known phrases exist."""
        entry = _make_config_entry(
            options={
                "locale": "zh-TW",
                "enable_entity_hints": True,
                "custom_phrases": ["走廊燈"],
            }
        )

        # Mock Azure Fast Transcription API response with a homophone error
        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=200,
            json_data={
                "combinedPhrases": [{"text": "打開走廊等"}],
                "phrases": [
                    {
                        "text": "打開走廊等",
                        "confidence": 0.93,
                        "offsetMilliseconds": 0,
                        "durationMilliseconds": 2000,
                    }
                ],
            },
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.SUCCESS
        # "走廊等" should be corrected to "走廊燈" by pinyin matching
        assert "走廊燈" in result.text
        # Raw text should be stored on the entity
        assert entity._last_raw_text == "打開走廊等"

    @pytest.mark.asyncio
    async def test_recognized_english_text(self, mock_hass):
        """English text should pass through correction (no homophone rules for English)."""
        entry = _make_config_entry(
            options={"locale": "en-US", "enable_entity_hints": True}
        )

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=200,
            json_data={
                "combinedPhrases": [{"text": "Turn on the living room light"}],
                "phrases": [
                    {
                        "text": "Turn on the living room light",
                        "confidence": 0.95,
                        "offsetMilliseconds": 0,
                        "durationMilliseconds": 3000,
                    }
                ],
            },
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.SUCCESS
        assert result.text == "Turn on the living room light"

    @pytest.mark.asyncio
    async def test_no_speech_returns_error(self, mock_hass):
        """Empty combinedPhrases should return ERROR."""
        entry = _make_config_entry()

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=200,
            json_data={
                "combinedPhrases": [],
                "phrases": [],
            },
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.ERROR
        assert result.text is None

    @pytest.mark.asyncio
    async def test_auth_error_returns_error(self, mock_hass):
        """HTTP 401 should return ERROR."""
        entry = _make_config_entry()

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=401,
            text="Unauthorized",
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.ERROR
        assert result.text is None

    @pytest.mark.asyncio
    async def test_server_error_returns_error(self, mock_hass):
        """HTTP 500 should return ERROR."""
        entry = _make_config_entry()

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=500,
            text="Internal Server Error",
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.ERROR
        assert result.text is None

    @pytest.mark.asyncio
    async def test_connection_error_returns_error(self, mock_hass):
        """Network connection error should return ERROR."""
        entry = _make_config_entry()

        # Make session.post raise a connection error
        mock_session = AsyncMock()
        mock_session.post = MagicMock(
            side_effect=aiohttp.ClientConnectionError("Connection refused")
        )
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.ERROR
        assert result.text is None

    @pytest.mark.asyncio
    async def test_empty_audio_returns_error(self, mock_hass):
        """Empty audio stream should return ERROR without calling Azure."""
        entry = _make_config_entry()

        mock_session = AsyncMock()
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _empty_audio_stream()
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.ERROR
        assert result.text is None
        # session.post should NOT have been called
        mock_session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_transient_error(self, mock_hass):
        """Transient error (500) on first attempt should retry and succeed."""
        entry = _make_config_entry()

        # First call: 500 error, second call: 200 success
        fail_resp = AsyncMock()
        fail_resp.status = 500
        fail_resp.text = AsyncMock(return_value="Internal Server Error")
        fail_cm = AsyncMock()
        fail_cm.__aenter__ = AsyncMock(return_value=fail_resp)
        fail_cm.__aexit__ = AsyncMock(return_value=False)

        success_resp = AsyncMock()
        success_resp.status = 200
        success_resp.json = AsyncMock(
            return_value={
                "combinedPhrases": [{"text": "hello world"}],
                "phrases": [],
            }
        )
        success_cm = AsyncMock()
        success_cm.__aenter__ = AsyncMock(return_value=success_resp)
        success_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=[fail_cm, success_cm])
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.SUCCESS
        assert result.text == "hello world"
        assert mock_session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self, mock_hass):
        """401 auth error should NOT be retried."""
        entry = _make_config_entry()

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=401,
            text="Unauthorized",
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.ERROR
        assert result.text is None
        # 401 is non-retryable — should only call once
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_connection_error_then_succeeds(self, mock_hass):
        """Network error on first attempt should retry and succeed."""
        entry = _make_config_entry()

        # First call: connection error, second call: success
        success_resp = AsyncMock()
        success_resp.status = 200
        success_resp.json = AsyncMock(
            return_value={
                "combinedPhrases": [{"text": "retry worked"}],
                "phrases": [],
            }
        )
        success_cm = AsyncMock()
        success_cm.__aenter__ = AsyncMock(return_value=success_resp)
        success_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(
            side_effect=[
                aiohttp.ClientConnectionError("Connection refused"),
                success_cm,
            ]
        )
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.SUCCESS
        assert result.text == "retry worked"
        assert mock_session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_phrase_list_included_in_request(self, mock_hass):
        """phraseList should be included in the multipart form data when phrases exist."""
        entry = _make_config_entry(
            options={
                "locale": "zh-TW",
                "enable_entity_hints": True,
                "custom_phrases": ["循環扇", "入口燈"],
            }
        )

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=200,
            json_data={
                "combinedPhrases": [{"text": "打開循環扇"}],
                "phrases": [
                    {
                        "text": "打開循環扇",
                        "confidence": 0.95,
                        "offsetMilliseconds": 0,
                        "durationMilliseconds": 2000,
                    }
                ],
            },
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-CN")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.SUCCESS
        assert "循環扇" in result.text

        # Verify session.post was called with the correct URL and form data
        mock_session.post.assert_called_once()
        call_kwargs = mock_session.post.call_args

        # Verify the URL contains the correct region
        url = (
            call_kwargs.args[0]
            if call_kwargs.args
            else call_kwargs.kwargs.get("url", "")
        )
        assert "eastasia" in url
        assert "speechtotext/transcriptions:transcribe" in url

        # Verify the API key header
        headers = call_kwargs.kwargs.get("headers", {})
        assert headers.get("Ocp-Apim-Subscription-Key") == "test-key"

    @pytest.mark.asyncio
    async def test_last_raw_and_corrected_text_stored(self, mock_hass):
        """Entity should store both raw and corrected text after recognition."""
        entry = _make_config_entry(
            options={"locale": "zh-TW", "enable_entity_hints": True}
        )

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=200,
            json_data={
                "combinedPhrases": [{"text": "Hello world"}],
                "phrases": [],
            },
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        # Initially None
        assert entity._last_raw_text is None
        assert entity._last_corrected_text is None

        metadata = MagicMock(language="zh-CN")
        await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        assert entity._last_raw_text == "Hello world"
        # No correction applied (raw == corrected), so _last_corrected_text stays None
        assert entity._last_corrected_text is None


class TestAsyncSetupEntry:
    """Test the platform setup function."""

    @pytest.mark.asyncio
    async def test_async_setup_entry(self, mock_hass):
        """async_setup_entry should add one entity."""
        _setup_empty_registries(mock_hass)
        entry = _make_config_entry()
        async_add_entities = MagicMock()

        with patch(
            "custom_components.azure_speech_stt.stt.async_get_clientsession",
            return_value=AsyncMock(),
        ):
            from custom_components.azure_speech_stt.stt import async_setup_entry

            await async_setup_entry(mock_hass, entry, async_add_entities)

        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1

        from custom_components.azure_speech_stt.stt import AzureSpeechSTTEntity

        assert isinstance(entities[0], AzureSpeechSTTEntity)


class TestCorrectorConfig:
    """Test the corrector configuration from options."""

    def test_custom_replacements(self, mock_hass):
        """Custom replacements should be applied by the corrector."""
        entry = _make_config_entry(
            options={"custom_replacements": {"開燈": "turn on light"}}
        )

        mock_session = AsyncMock()
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        result = entity._corrector.correct("開燈")
        assert result.corrected == "turn on light"

    def test_default_corrector_no_phrases(self, mock_hass):
        """Default corrector without known phrases should not change text."""
        entry = _make_config_entry()

        mock_session = AsyncMock()
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        # Without known phrases, pinyin matching has nothing to match against
        result = entity._corrector.correct("打開走廊等")
        assert result.corrected == "打開走廊等"

    def test_corrector_with_known_phrases(self, mock_hass):
        """Corrector with known phrases should correct homophones via pinyin."""
        entry = _make_config_entry()

        mock_session = AsyncMock()
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        # Simulate what happens when phrases are updated from entity registry
        entity._corrector.update_phrases(["走廊燈"])
        result = entity._corrector.correct("打開走廊等")
        assert "走廊燈" in result.corrected


class TestLifecycle:
    """Test entity lifecycle methods."""

    @pytest.mark.asyncio
    async def test_async_added_to_hass(self, stt_entity, mock_hass):
        """async_added_to_hass should start listening for registry events."""
        await stt_entity.async_added_to_hass()
        # Should have subscribed to bus events
        assert mock_hass.bus.async_listen.call_count >= 2

    @pytest.mark.asyncio
    async def test_async_will_remove_from_hass(self, mock_hass):
        """async_will_remove_from_hass should stop listening."""
        _setup_empty_registries(mock_hass)
        unsub_entity = MagicMock()
        unsub_area = MagicMock()
        unsub_device = MagicMock()
        unsub_floor = MagicMock()
        mock_hass.bus.async_listen.side_effect = [
            unsub_entity,
            unsub_area,
            unsub_device,
            unsub_floor,
        ]

        entry = _make_config_entry()

        with patch(
            "custom_components.azure_speech_stt.stt.async_get_clientsession",
            return_value=AsyncMock(),
        ):
            from custom_components.azure_speech_stt.stt import AzureSpeechSTTEntity

            entity = AzureSpeechSTTEntity(mock_hass, entry)
        await entity.async_added_to_hass()
        await entity.async_will_remove_from_hass()

        unsub_entity.assert_called_once()
        unsub_area.assert_called_once()
        unsub_device.assert_called_once()
        unsub_floor.assert_called_once()


class TestRealtimeApiRoute:
    """Test that zh-TW (REALTIME_ONLY_LOCALES) routes through the realtime API."""

    @pytest.mark.asyncio
    async def test_realtime_api_success(self, mock_hass):
        """zh-TW locale should route to realtime API and return DisplayText."""
        entry = _make_config_entry(options={"enable_entity_hints": False})

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=200,
            json_data={
                "RecognitionStatus": "Success",
                "DisplayText": "你好世界",
            },
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-TW")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.SUCCESS
        assert "你好世界" in result.text

        # Verify the realtime endpoint was used
        url = mock_session.post.call_args.args[0]
        assert "stt.speech.microsoft.com" in url
        assert "language=zh-TW" in url

    @pytest.mark.asyncio
    async def test_realtime_api_no_match(self, mock_hass):
        """RecognitionStatus NoMatch should return ERROR with empty text."""
        entry = _make_config_entry(options={"enable_entity_hints": False})

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=200,
            json_data={"RecognitionStatus": "NoMatch"},
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-TW")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.ERROR
        assert result.text is None

    @pytest.mark.asyncio
    async def test_realtime_api_auth_error(self, mock_hass):
        """Realtime API 401 should return ERROR."""
        entry = _make_config_entry(options={"enable_entity_hints": False})

        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=401,
            text="Unauthorized",
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        metadata = MagicMock(language="zh-TW")
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.ERROR
        assert result.text is None


class TestRebuildFromOptions:
    """Test rebuild_from_options on AzureSpeechSTTEntity."""

    def test_rebuild_from_options(self, mock_hass):
        """rebuild_from_options should rebuild corrector with new settings."""
        entry = _make_config_entry(
            options={
                "custom_replacements": {"hello": "world"},
                "custom_phrases": ["phrase1"],
            }
        )

        mock_session = AsyncMock()
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        old_corrector = entity._corrector

        # Simulate updating options on the config entry
        entry.options = {
            "custom_replacements": {"foo": "bar"},
            "custom_phrases": ["phrase2", "phrase3"],
            "fuzzy_threshold": 0.90,
        }

        entity.rebuild_from_options()

        # Corrector should be a new instance
        assert entity._corrector is not old_corrector

        # New corrector should use the updated replacement rules
        result = entity._corrector.correct("foo")
        assert result.corrected == "bar"

        # Old replacement should no longer work
        result_old = entity._corrector.correct("hello")
        assert result_old.corrected == "hello"


class TestParallelUpdates:
    """Test module-level PARALLEL_UPDATES constant."""

    def test_parallel_updates_is_one(self):
        """PARALLEL_UPDATES should be set to 1."""
        from custom_components.azure_speech_stt.stt import PARALLEL_UPDATES

        assert PARALLEL_UPDATES == 1


class TestAvailabilityTracking:
    """Test consecutive failure tracking and availability management."""

    @pytest.mark.asyncio
    async def test_unavailable_after_consecutive_failures(self, mock_hass):
        """Entity should become unavailable after 3 consecutive API failures."""
        from custom_components.azure_speech_stt.stt import _MAX_CONSECUTIVE_FAILURES

        entry = _make_config_entry(options={"enable_entity_hints": False})

        # Mock session that always returns 500 errors
        mock_post_cm, mock_resp = _mock_aiohttp_response(
            status=500, text="Internal Server Error"
        )
        mock_session = _make_mock_session(mock_post_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)

        assert entity._attr_available is True
        assert entity._consecutive_failures == 0

        metadata = MagicMock(language="en-US")

        # Fail up to threshold - 1: should still be available
        for i in range(1, _MAX_CONSECUTIVE_FAILURES):
            # Need fresh response mocks for each call (retry logic may consume them)
            fail_cm, _ = _mock_aiohttp_response(status=401, text="Unauthorized")
            mock_session.post = MagicMock(return_value=fail_cm)

            await entity.async_process_audio_stream(
                metadata, _audio_stream([b"fake-audio-data"])
            )
            assert entity._consecutive_failures == i
            assert entity._attr_available is True

        # One more failure should mark unavailable
        fail_cm, _ = _mock_aiohttp_response(status=401, text="Unauthorized")
        mock_session.post = MagicMock(return_value=fail_cm)
        await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )
        assert entity._consecutive_failures == _MAX_CONSECUTIVE_FAILURES
        assert entity._attr_available is False

    @pytest.mark.asyncio
    async def test_recovers_after_success(self, mock_hass):
        """Entity should recover availability after a successful transcription."""
        entry = _make_config_entry(options={"enable_entity_hints": False})

        # Start with failures to make it unavailable
        fail_cm, _ = _mock_aiohttp_response(status=401, text="Unauthorized")
        mock_session = _make_mock_session(fail_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)
        metadata = MagicMock(language="en-US")

        # Drive to unavailable
        for _ in range(3):
            fc, _ = _mock_aiohttp_response(status=401, text="Unauthorized")
            mock_session.post = MagicMock(return_value=fc)
            await entity.async_process_audio_stream(
                metadata, _audio_stream([b"fake-audio-data"])
            )

        assert entity._attr_available is False

        # Now succeed
        success_cm, _ = _mock_aiohttp_response(
            status=200,
            json_data={
                "combinedPhrases": [{"text": "hello world"}],
                "phrases": [],
            },
        )
        mock_session.post = MagicMock(return_value=success_cm)
        result = await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )

        from homeassistant.components.stt import SpeechResultState

        assert result.result == SpeechResultState.SUCCESS
        assert entity._attr_available is True
        assert entity._consecutive_failures == 0

    @pytest.mark.asyncio
    async def test_success_resets_counter_without_state_write(self, mock_hass):
        """Success after partial failures resets counter without toggling availability."""
        entry = _make_config_entry(options={"enable_entity_hints": False})

        fail_cm, _ = _mock_aiohttp_response(status=401, text="Unauthorized")
        mock_session = _make_mock_session(fail_cm)
        entity = _create_entity_with_session(mock_hass, entry, mock_session)
        metadata = MagicMock(language="en-US")

        # One failure (below threshold)
        fc, _ = _mock_aiohttp_response(status=401, text="Unauthorized")
        mock_session.post = MagicMock(return_value=fc)
        await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )
        assert entity._consecutive_failures == 1
        assert entity._attr_available is True

        # Succeed — should reset counter, entity stays available
        success_cm, _ = _mock_aiohttp_response(
            status=200,
            json_data={
                "combinedPhrases": [{"text": "ok"}],
                "phrases": [],
            },
        )
        mock_session.post = MagicMock(return_value=success_cm)
        await entity.async_process_audio_stream(
            metadata, _audio_stream([b"fake-audio-data"])
        )
        assert entity._consecutive_failures == 0
        assert entity._attr_available is True
