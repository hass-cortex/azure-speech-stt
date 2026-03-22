"""Integration tests for Azure Speech-to-Text API."""

import aiohttp
import pytest

from .conftest import AZURE_STT_API_KEY, AZURE_STT_REGION, requires_azure

TOKEN_ENDPOINT = "https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"


@requires_azure
@pytest.mark.integration
async def test_token_validation():
    """Verify Azure credentials are valid by requesting a token."""
    url = TOKEN_ENDPOINT.format(region=AZURE_STT_REGION)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers={
                "Ocp-Apim-Subscription-Key": AZURE_STT_API_KEY,
                "Content-Length": "0",
            },
        ) as resp:
            assert resp.status == 200
            token = await resp.text()
            assert len(token) > 0


@requires_azure
@pytest.mark.integration
async def test_invalid_key_returns_401():
    """Verify invalid key is rejected."""
    url = TOKEN_ENDPOINT.format(region=AZURE_STT_REGION)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers={
                "Ocp-Apim-Subscription-Key": "invalid-key-12345",
                "Content-Length": "0",
            },
        ) as resp:
            assert resp.status == 401
