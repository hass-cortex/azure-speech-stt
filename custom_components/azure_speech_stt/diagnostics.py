"""Diagnostics support for Azure Speech-to-Text."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import AzureSpeechSTTConfigEntry
from .const import CONF_SPEECH_KEY

TO_REDACT = {CONF_SPEECH_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AzureSpeechSTTConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "config_entry": {
            "data": _redact(dict(entry.data)),
            "options": dict(entry.options),
        },
    }


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive fields."""
    return {k: "**REDACTED**" if k in TO_REDACT else v for k, v in data.items()}
