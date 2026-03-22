"""Shared helpers for Azure Speech-to-Text integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .models import AzureSTTRuntimeData

if TYPE_CHECKING:
    from .stt import AzureSpeechSTTEntity


def find_stt_entity(
    hass: HomeAssistant, entry: ConfigEntry | None = None
) -> AzureSpeechSTTEntity | None:
    """Find an AzureSpeechSTTEntity instance via runtime_data.

    Args:
        hass: Home Assistant instance.
        entry: If provided, find the entity for this specific config entry.
               If None, return the first Azure STT entity found.

    Returns:
        The AzureSpeechSTTEntity instance, or None if not found.
    """
    if entry is not None:
        runtime_data: AzureSTTRuntimeData | None = getattr(entry, "runtime_data", None)
        if runtime_data is not None:
            return runtime_data.entity
        return None

    # No entry specified -- search all config entries for this domain
    for cfg_entry in hass.config_entries.async_entries(DOMAIN):
        runtime_data = getattr(cfg_entry, "runtime_data", None)
        if isinstance(runtime_data, AzureSTTRuntimeData):
            return runtime_data.entity

    return None
