"""Tests for AzureSTTClient."""

from __future__ import annotations

import wave
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.azure_speech_stt.azure_client import (
    AzureSTTClient,
    PermanentApiError,
)


def _mock_response(
    status: int = 200,
    json_data: dict | None = None,
    text: str = "",
) -> tuple[MagicMock, AsyncMock]:
    """Create a mock aiohttp response as an async context manager.

    Returns:
        Tuple of (context_manager, response_mock).
    """
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data or {})
    mock_resp.text = AsyncMock(return_value=text)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    return mock_cm, mock_resp


def _make_client(session: AsyncMock | None = None) -> AzureSTTClient:
    """Create an AzureSTTClient with a mock session."""
    return AzureSTTClient(
        region="eastasia",
        api_key="test-key",
        session=session or AsyncMock(),
    )


class TestTranscribeFast:
    """Test Fast Transcription API path."""

    @pytest.mark.asyncio
    async def test_successful_transcription(self):
        """Should return combined phrases text on success."""
        post_cm, _ = _mock_response(
            status=200,
            json_data={
                "combinedPhrases": [{"text": "hello world"}],
                "phrases": [],
            },
        )
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "en-US", ["hello"])

        assert result == "hello world"
        assert api_used == "fast_transcription"
        session.post.assert_called_once()

        # Verify URL and headers
        call_kwargs = session.post.call_args
        url = call_kwargs.args[0]
        assert "eastasia" in url
        assert "speechtotext/transcriptions:transcribe" in url
        headers = call_kwargs.kwargs.get("headers", {})
        assert headers["Ocp-Apim-Subscription-Key"] == "test-key"

    @pytest.mark.asyncio
    async def test_empty_combined_phrases(self):
        """Empty combinedPhrases should return empty string."""
        post_cm, _ = _mock_response(
            status=200,
            json_data={"combinedPhrases": [], "phrases": []},
        )
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "en-US", [])

        assert result == ""
        assert api_used == "fast_transcription"

    @pytest.mark.asyncio
    async def test_auth_error_not_retried(self):
        """HTTP 401 should not be retried (PermanentApiError)."""
        post_cm, _ = _mock_response(status=401, text="Unauthorized")
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "en-US", [])

        assert result is None
        assert api_used == "fast_transcription"
        # 401 is permanent — should only call once
        session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_forbidden_error_not_retried(self):
        """HTTP 403 should not be retried."""
        post_cm, _ = _mock_response(status=403, text="Forbidden")
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "en-US", [])

        assert result is None
        assert api_used == "fast_transcription"
        session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_error_retried(self):
        """HTTP 500 should be retried once."""
        fail_cm, _ = _mock_response(status=500, text="Server Error")
        success_cm, _ = _mock_response(
            status=200,
            json_data={"combinedPhrases": [{"text": "retry ok"}]},
        )
        session = AsyncMock()
        session.post = MagicMock(side_effect=[fail_cm, success_cm])
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "en-US", [])

        assert result == "retry ok"
        assert api_used == "fast_transcription"
        assert session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_error_not_retried(self):
        """HTTP 404 should not be retried (not in retryable whitelist)."""
        post_cm, _ = _mock_response(status=404, text="Not Found")
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "en-US", [])

        assert result is None
        assert api_used == "fast_transcription"
        session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_retried(self):
        """HTTP 429 should be retried once."""
        fail_cm, _ = _mock_response(status=429, text="Too Many Requests")
        success_cm, _ = _mock_response(
            status=200,
            json_data={"combinedPhrases": [{"text": "retry ok"}]},
        )
        session = AsyncMock()
        session.post = MagicMock(side_effect=[fail_cm, success_cm])
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "en-US", [])

        assert result == "retry ok"
        assert api_used == "fast_transcription"
        assert session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_connection_error_retried(self):
        """Network error should be retried once."""
        success_cm, _ = _mock_response(
            status=200,
            json_data={"combinedPhrases": [{"text": "retry ok"}]},
        )
        session = AsyncMock()
        session.post = MagicMock(
            side_effect=[
                aiohttp.ClientConnectionError("Connection refused"),
                success_cm,
            ]
        )
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "en-US", [])

        assert result == "retry ok"
        assert api_used == "fast_transcription"
        assert session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_double_failure_returns_none(self):
        """Two consecutive failures should return None."""
        fail_cm1, _ = _mock_response(status=500, text="Server Error")
        fail_cm2, _ = _mock_response(status=500, text="Server Error")
        session = AsyncMock()
        session.post = MagicMock(side_effect=[fail_cm1, fail_cm2])
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "en-US", [])

        assert result is None
        assert api_used == "fast_transcription"
        assert session.post.call_count == 2


class TestTranscribeRealtime:
    """Test Real-time API path (for REALTIME_ONLY_LOCALES)."""

    @pytest.mark.asyncio
    async def test_realtime_locale_routes_correctly(self):
        """zh-TW should route to the Real-time API."""
        post_cm, _ = _mock_response(
            status=200,
            json_data={
                "RecognitionStatus": "Success",
                "DisplayText": "你好世界",
            },
        )
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "zh-TW", [])

        assert result == "你好世界"
        assert api_used == "realtime"
        # Verify URL uses the realtime endpoint
        url = session.post.call_args.args[0]
        assert "stt.speech.microsoft.com" in url
        assert "language=zh-TW" in url

    @pytest.mark.asyncio
    async def test_realtime_no_speech(self):
        """RecognitionStatus != Success should return empty string."""
        post_cm, _ = _mock_response(
            status=200,
            json_data={"RecognitionStatus": "NoMatch"},
        )
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "zh-TW", [])

        assert result == ""
        assert api_used == "realtime"

    @pytest.mark.asyncio
    async def test_realtime_auth_error(self):
        """HTTP 401 on realtime should not be retried."""
        post_cm, _ = _mock_response(status=401, text="Unauthorized")
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio-data", "zh-TW", [])

        assert result is None
        assert api_used == "realtime"
        session.post.assert_called_once()


class TestApiRouting:
    """Test API routing with allowed_apis parameter."""

    @pytest.mark.asyncio
    async def test_both_apis_fast_locale_uses_fast(self):
        """With both APIs allowed, non-realtime locale uses Fast Transcription."""
        post_cm, _ = _mock_response(
            status=200,
            json_data={"combinedPhrases": [{"text": "hello"}]},
        )
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(
            b"audio",
            "en-US",
            ["hello"],
            allowed_apis=["fast_transcription", "realtime"],
        )

        assert result == "hello"
        assert api_used == "fast_transcription"
        url = session.post.call_args.args[0]
        assert "speechtotext/transcriptions:transcribe" in url

    @pytest.mark.asyncio
    async def test_both_apis_realtime_locale_uses_realtime(self):
        """With both APIs allowed, REALTIME_ONLY locale uses Real-time."""
        post_cm, _ = _mock_response(
            status=200,
            json_data={"RecognitionStatus": "Success", "DisplayText": "你好"},
        )
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(
            b"audio",
            "zh-TW",
            [],
            allowed_apis=["fast_transcription", "realtime"],
        )

        assert result == "你好"
        assert api_used == "realtime"
        url = session.post.call_args.args[0]
        assert "stt.speech.microsoft.com" in url

    @pytest.mark.asyncio
    async def test_only_realtime_for_fast_locale(self):
        """Only realtime allowed for a non-realtime locale should fallback to realtime."""
        post_cm, _ = _mock_response(
            status=200,
            json_data={"RecognitionStatus": "Success", "DisplayText": "hello"},
        )
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(
            b"audio",
            "en-US",
            ["hello"],
            allowed_apis=["realtime"],
        )

        assert result == "hello"
        assert api_used == "realtime"
        url = session.post.call_args.args[0]
        assert "stt.speech.microsoft.com" in url

    @pytest.mark.asyncio
    async def test_only_fast_for_realtime_locale_returns_none(self):
        """Only fast allowed for a REALTIME_ONLY locale should return None."""
        session = AsyncMock()
        client = _make_client(session)

        result, api_used = await client.transcribe(
            b"audio",
            "zh-TW",
            [],
            allowed_apis=["fast_transcription"],
        )

        assert result is None
        assert api_used == ""
        session.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_default_allowed_apis_matches_current_behavior(self):
        """Default allowed_apis (both) should match existing behavior."""
        post_cm, _ = _mock_response(
            status=200,
            json_data={"combinedPhrases": [{"text": "hello"}]},
        )
        session = AsyncMock()
        session.post = MagicMock(return_value=post_cm)
        client = _make_client(session)

        result, api_used = await client.transcribe(b"audio", "en-US", ["hello"])

        assert result == "hello"
        assert api_used == "fast_transcription"
        url = session.post.call_args.args[0]
        assert "speechtotext/transcriptions:transcribe" in url


class TestWrapPcmAsWav:
    """Test PCM to WAV wrapping."""

    def test_produces_valid_wav(self):
        """Output should be a valid WAV file with correct parameters."""
        pcm_data = b"\x00" * 32000  # 1 second of silence at 16kHz 16-bit mono

        wav_data = AzureSTTClient.wrap_pcm_as_wav(pcm_data)

        # Verify it starts with RIFF header
        assert wav_data[:4] == b"RIFF"
        assert wav_data[8:12] == b"WAVE"

        # Parse with wave module to verify parameters
        import io

        with wave.open(io.BytesIO(wav_data), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            assert wf.getnframes() == 16000  # 32000 bytes / 2 bytes per sample

    def test_empty_pcm_produces_valid_wav(self):
        """Empty PCM data should still produce a valid WAV header."""
        wav_data = AzureSTTClient.wrap_pcm_as_wav(b"")

        assert wav_data[:4] == b"RIFF"


class TestPermanentApiError:
    """Test the PermanentApiError exception."""

    def test_is_exception(self):
        """Should be a subclass of Exception."""
        assert issubclass(PermanentApiError, Exception)

    def test_can_be_raised_and_caught(self):
        """Should be raiseable and catchable."""
        with pytest.raises(PermanentApiError):
            raise PermanentApiError(401)

    def test_status_code_stored(self):
        """Should store the HTTP status code."""
        err = PermanentApiError(403, "Forbidden")
        assert err.status == 403
        assert "HTTP 403" in str(err)
        assert "Forbidden" in str(err)

    def test_default_message(self):
        """Should have a default empty message."""
        err = PermanentApiError(401)
        assert err.status == 401
        assert "HTTP 401" in str(err)
