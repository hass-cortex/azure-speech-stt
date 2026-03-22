"""Azure Speech-to-Text integration for Home Assistant."""

from __future__ import annotations

import logging
from typing import Final

import aiohttp
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SPEECH_KEY, CONF_SPEECH_REGION, DOMAIN, TOKEN_ENDPOINT
from .models import AzureSTTRuntimeData

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = ["stt", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Azure Speech-to-Text from a config entry."""
    # Validate Azure credentials before setting up the platform
    session = async_get_clientsession(hass)
    token_url = TOKEN_ENDPOINT.format(region=entry.data[CONF_SPEECH_REGION])
    try:
        async with session.post(
            token_url,
            headers={"Ocp-Apim-Subscription-Key": entry.data[CONF_SPEECH_KEY]},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status in (401, 403):
                raise ConfigEntryAuthFailed(
                    f"Azure Speech API authentication failed (HTTP {resp.status})"
                )
            if resp.status != 200:
                raise ConfigEntryNotReady(
                    f"Azure Speech API returned HTTP {resp.status}"
                )
    except (aiohttp.ClientError, TimeoutError) as err:
        raise ConfigEntryNotReady(f"Cannot reach Azure Speech API: {err}") from err

    entry.runtime_data = AzureSTTRuntimeData()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Rebuild phrase builder when options change
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    # Register services (once per domain)
    if not hass.services.has_service(DOMAIN, "transcribe"):
        from .services import async_register_services

        async_register_services(hass)

    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update — rebuild phrase builder."""
    from .helpers import find_stt_entity

    entity = find_stt_entity(hass, entry)
    if entity:
        entity.rebuild_phrase_builder()
        _LOGGER.debug("Rebuilt phrase builder after options update")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Azure Speech-to-Text config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
