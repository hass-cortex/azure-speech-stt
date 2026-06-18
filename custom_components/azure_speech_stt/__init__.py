"""Azure Speech-to-Text integration for Home Assistant."""

from __future__ import annotations

from typing import Any, Final

import aiohttp
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SPEECH_KEY, CONF_SPEECH_REGION, DOMAIN, TOKEN_ENDPOINT
from .models import AzureSTTRuntimeData

type AzureSpeechSTTConfigEntry = ConfigEntry[AzureSTTRuntimeData]

PLATFORMS: Final = ["stt", "sensor"]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up Azure Speech-to-Text integration."""
    from .services import async_register_services

    async_register_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: AzureSpeechSTTConfigEntry
) -> bool:
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

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: AzureSpeechSTTConfigEntry
) -> bool:
    """Unload an Azure Speech-to-Text config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
