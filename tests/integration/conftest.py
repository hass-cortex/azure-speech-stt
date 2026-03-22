"""Integration test fixtures requiring Azure API key."""

import os

import pytest

AZURE_STT_API_KEY = os.environ.get("AZURE_STT_API_KEY", "")
AZURE_STT_REGION = os.environ.get("AZURE_STT_REGION", "")

requires_azure = pytest.mark.skipif(
    not AZURE_STT_API_KEY or not AZURE_STT_REGION,
    reason="AZURE_STT_API_KEY and AZURE_STT_REGION env vars not set",
)
