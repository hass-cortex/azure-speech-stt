"""Config flow for Azure Speech-to-Text integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.data_entry_flow import section
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    API_MODE_FAST,
    API_MODE_REALTIME,
    AUTO_COLLECT_AREAS,
    AUTO_COLLECT_DEVICES,
    AUTO_COLLECT_ENTITIES,
    AUTO_COLLECT_FLOORS,
    AZURE_REGIONS,
    CONF_API_MODES,
    CONF_AUTO_COLLECT_SOURCES,
    CONF_CORRECTION_STAGES,
    CONF_CUSTOM_EXCLUSIONS,
    CONF_CUSTOM_PHRASES,
    CONF_CUSTOM_REPLACEMENTS,
    CONF_ENABLE_CUSTOM_REPLACEMENTS,
    CONF_ENABLE_ENTITY_HINTS,
    CONF_ENABLE_FUZZY_MATCHING,
    CONF_FUZZY_THRESHOLD,
    CONF_SECTION_AUTO_COLLECT,
    CONF_SECTION_STAGE1,
    CONF_SECTION_STAGE2,
    CONF_SECTION_STAGE3,
    CONF_SPEECH_KEY,
    CONF_SPEECH_REGION,
    CORRECTION_STAGE_HINTS,
    CORRECTION_STAGE_REPLACEMENTS,
    CORRECTION_STAGE_SIMILARITY,
    DEFAULT_API_MODES,
    DEFAULT_AUTO_COLLECT_SOURCES,
    DEFAULT_CORRECTION_STAGES,
    DEFAULT_ENABLE_CUSTOM_REPLACEMENTS,
    DEFAULT_ENABLE_ENTITY_HINTS,
    DEFAULT_ENABLE_FUZZY_MATCHING,
    DEFAULT_FUZZY_THRESHOLD,
    DOMAIN,
    TOKEN_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)

# Region options for the select selector
_REGION_OPTIONS = {r["value"]: r["label"] for r in AZURE_REGIONS}

# Schema for user/reconfigure steps (language is selected in Pipeline settings)
CONF_DISPLAY_NAME = "display_name"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SPEECH_KEY): str,
        vol.Required(CONF_SPEECH_REGION): vol.In(_REGION_OPTIONS),
        vol.Optional(CONF_DISPLAY_NAME): str,
    }
)


async def _validate_credentials(
    session: aiohttp.ClientSession, key: str, region: str
) -> str | None:
    """Validate Azure Speech credentials by requesting a token.

    Args:
        session: aiohttp client session.
        key: Azure Speech subscription key.
        region: Azure region identifier.

    Returns:
        None if valid, or an error string ("invalid_key" or "cannot_connect").
    """
    url = TOKEN_ENDPOINT.format(region=region)
    try:
        async with session.post(
            url,
            headers={"Ocp-Apim-Subscription-Key": key},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 200:
                return None
            # 401 = invalid key or region
            return "invalid_key"
    except (aiohttp.ClientError, TimeoutError):
        return "cannot_connect"


class AzureSpeechSTTConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Azure Speech-to-Text."""

    VERSION = 1

    _reauth_entry: ConfigEntry | None = None

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauthentication when API key expires."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication with new credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            assert self._reauth_entry is not None
            session = async_get_clientsession(self.hass)
            error = await _validate_credentials(
                session,
                user_input[CONF_SPEECH_KEY],
                self._reauth_entry.data[CONF_SPEECH_REGION],
            )
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    self._reauth_entry,
                    data={**self._reauth_entry.data, **user_input},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SPEECH_KEY): str,
                }
            ),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial setup step.

        Collects speech_key and speech_region, validates by requesting
        a token from the Azure token endpoint.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            error = await _validate_credentials(
                session,
                user_input[CONF_SPEECH_KEY],
                user_input[CONF_SPEECH_REGION],
            )
            if error:
                errors["base"] = error
            else:
                display_name = user_input.pop(CONF_DISPLAY_NAME, None)
                region = user_input[CONF_SPEECH_REGION]
                title = display_name or f"Azure STT ({region})"
                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of credentials."""
        errors: dict[str, str] = {}
        reconfig_entry = self._get_reconfigure_entry()

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            error = await _validate_credentials(
                session,
                user_input[CONF_SPEECH_KEY],
                user_input[CONF_SPEECH_REGION],
            )
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(
                    reconfig_entry,
                    data=user_input,
                    reload_even_if_entry_is_unchanged=False,
                )

        suggested_values = user_input or reconfig_entry.data
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, suggested_values
            )
            if hasattr(self, "add_suggested_values_to_schema")
            else STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> AzureSpeechSTTOptionsFlow:
        """Get the options flow handler."""
        return AzureSpeechSTTOptionsFlow(config_entry)


class AzureSpeechSTTOptionsFlow(OptionsFlow):
    """Handle options flow for Azure Speech-to-Text (single page)."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle all options in a single page."""
        if user_input is not None:
            # Validate at least one API is selected; fall back to default if empty
            api_modes = user_input.get(CONF_API_MODES) or DEFAULT_API_MODES

            # Correction stages multi-select replaces individual enable toggles
            stages = user_input.get(CONF_CORRECTION_STAGES) or []

            # Extract auto-collect sources from section
            s_ac = user_input.get(CONF_SECTION_AUTO_COLLECT, {})
            auto_collect_sources = s_ac.get(
                CONF_AUTO_COLLECT_SOURCES, DEFAULT_AUTO_COLLECT_SOURCES
            )

            # Extract correction fields from stage sections
            s1 = user_input.get(CONF_SECTION_STAGE1, {})
            s2 = user_input.get(CONF_SECTION_STAGE2, {})
            s3 = user_input.get(CONF_SECTION_STAGE3, {})

            # multiple=True gives list[str] directly
            phrases = [
                p.strip()
                for p in (s1.get(CONF_CUSTOM_PHRASES) or [])
                if p.strip()
            ]

            # Parse "wrong=correct" entries from list
            replacements: dict[str, str] = {}
            for entry in s2.get(CONF_CUSTOM_REPLACEMENTS) or []:
                entry = entry.strip()
                if "=" in entry:
                    wrong, correct = entry.split("=", 1)
                    wrong = wrong.strip()
                    correct = correct.strip()
                    if wrong and correct:
                        replacements[wrong] = correct

            exclusions = [
                e.strip()
                for e in (s3.get(CONF_CUSTOM_EXCLUSIONS) or [])
                if e.strip()
            ]

            return self.async_create_entry(
                title="",
                data={
                    CONF_API_MODES: api_modes,
                    CONF_AUTO_COLLECT_SOURCES: auto_collect_sources,
                    CONF_CORRECTION_STAGES: stages,
                    CONF_ENABLE_ENTITY_HINTS: CORRECTION_STAGE_HINTS in stages,
                    CONF_ENABLE_CUSTOM_REPLACEMENTS: (
                        CORRECTION_STAGE_REPLACEMENTS in stages
                    ),
                    CONF_ENABLE_FUZZY_MATCHING: (
                        CORRECTION_STAGE_SIMILARITY in stages
                    ),
                    CONF_FUZZY_THRESHOLD: s3.get(
                        CONF_FUZZY_THRESHOLD, DEFAULT_FUZZY_THRESHOLD
                    ),
                    CONF_CUSTOM_PHRASES: phrases,
                    CONF_CUSTOM_REPLACEMENTS: replacements,
                    CONF_CUSTOM_EXCLUSIONS: exclusions,
                },
            )

        options = dict(self._config_entry.options)

        # Prepare current values for suggested_values
        current_replacements = options.get(CONF_CUSTOM_REPLACEMENTS, {})
        current_replacements_list = [
            f"{k}={v}" for k, v in current_replacements.items()
        ]

        # Build correction_stages from individual enable flags (backward compat)
        current_stages = options.get(CONF_CORRECTION_STAGES)
        if current_stages is None:
            current_stages = []
            if options.get(CONF_ENABLE_ENTITY_HINTS, DEFAULT_ENABLE_ENTITY_HINTS):
                current_stages.append(CORRECTION_STAGE_HINTS)
            if options.get(
                CONF_ENABLE_CUSTOM_REPLACEMENTS, DEFAULT_ENABLE_CUSTOM_REPLACEMENTS
            ):
                current_stages.append(CORRECTION_STAGE_REPLACEMENTS)
            if options.get(
                CONF_ENABLE_FUZZY_MATCHING, DEFAULT_ENABLE_FUZZY_MATCHING
            ):
                current_stages.append(CORRECTION_STAGE_SIMILARITY)

        suggested_values = {
            CONF_API_MODES: options.get(CONF_API_MODES, DEFAULT_API_MODES),
            CONF_CORRECTION_STAGES: current_stages,
            CONF_SECTION_AUTO_COLLECT: {
                CONF_AUTO_COLLECT_SOURCES: options.get(
                    CONF_AUTO_COLLECT_SOURCES, DEFAULT_AUTO_COLLECT_SOURCES
                ),
            },
            CONF_SECTION_STAGE1: {
                CONF_CUSTOM_PHRASES: options.get(CONF_CUSTOM_PHRASES, []),
            },
            CONF_SECTION_STAGE2: {
                CONF_CUSTOM_REPLACEMENTS: current_replacements_list,
            },
            CONF_SECTION_STAGE3: {
                CONF_FUZZY_THRESHOLD: options.get(
                    CONF_FUZZY_THRESHOLD, DEFAULT_FUZZY_THRESHOLD
                ),
                CONF_CUSTOM_EXCLUSIONS: options.get(CONF_CUSTOM_EXCLUSIONS, []),
            },
        }

        schema = vol.Schema(
            {
                # API selection
                vol.Required(
                    CONF_API_MODES, default=DEFAULT_API_MODES
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=API_MODE_FAST,
                                label="Fast Transcription API",
                            ),
                            SelectOptionDict(
                                value=API_MODE_REALTIME,
                                label="Real-time API",
                            ),
                        ],
                        multiple=True,
                    )
                ),
                # Correction pipeline stage selector
                vol.Required(
                    CONF_CORRECTION_STAGES, default=DEFAULT_CORRECTION_STAGES
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=CORRECTION_STAGE_HINTS,
                                label="Pre-recognition Hints",
                            ),
                            SelectOptionDict(
                                value=CORRECTION_STAGE_REPLACEMENTS,
                                label="Custom Replacements",
                            ),
                            SelectOptionDict(
                                value=CORRECTION_STAGE_SIMILARITY,
                                label="Similarity Matching",
                            ),
                        ],
                        multiple=True,
                    )
                ),
                # Auto-collect phrase sources
                vol.Optional(CONF_SECTION_AUTO_COLLECT): section(
                    vol.Schema(
                        {
                            vol.Optional(
                                CONF_AUTO_COLLECT_SOURCES,
                                default=DEFAULT_AUTO_COLLECT_SOURCES,
                            ): SelectSelector(
                                SelectSelectorConfig(
                                    options=[
                                        SelectOptionDict(
                                            value=AUTO_COLLECT_FLOORS,
                                            label="Floors",
                                        ),
                                        SelectOptionDict(
                                            value=AUTO_COLLECT_AREAS,
                                            label="Areas",
                                        ),
                                        SelectOptionDict(
                                            value=AUTO_COLLECT_DEVICES,
                                            label="Devices",
                                        ),
                                        SelectOptionDict(
                                            value=AUTO_COLLECT_ENTITIES,
                                            label="Exposed Entities",
                                        ),
                                    ],
                                    multiple=True,
                                )
                            ),
                        }
                    ),
                    {"collapsed": True},
                ),
                # Stage detail sections
                vol.Optional(CONF_SECTION_STAGE1): section(
                    vol.Schema(
                        {
                            vol.Optional(
                                CONF_CUSTOM_PHRASES, default=[]
                            ): TextSelector(TextSelectorConfig(multiple=True)),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Optional(CONF_SECTION_STAGE2): section(
                    vol.Schema(
                        {
                            vol.Optional(
                                CONF_CUSTOM_REPLACEMENTS, default=[]
                            ): TextSelector(TextSelectorConfig(multiple=True)),
                        }
                    ),
                    {"collapsed": True},
                ),
                vol.Optional(CONF_SECTION_STAGE3): section(
                    vol.Schema(
                        {
                            vol.Required(CONF_FUZZY_THRESHOLD): vol.All(
                                vol.Coerce(float), vol.Range(min=0.5, max=1.0)
                            ),
                            vol.Optional(
                                CONF_CUSTOM_EXCLUSIONS, default=[]
                            ): TextSelector(TextSelectorConfig(multiple=True)),
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, suggested_values),
        )
