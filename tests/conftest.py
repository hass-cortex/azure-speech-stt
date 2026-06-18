"""Test fixtures for azure-speech-stt.

Mocks the homeassistant module hierarchy so that custom_components
can be imported without real dependencies.
"""

import sys
from dataclasses import dataclass as _dataclass
from types import ModuleType
from unittest.mock import MagicMock

# ── Mock homeassistant module hierarchy ──
_ha = ModuleType("homeassistant")
_ha_core = ModuleType("homeassistant.core")
_ha_config_entries = ModuleType("homeassistant.config_entries")
_ha_data_entry_flow = ModuleType("homeassistant.data_entry_flow")
_ha_helpers = ModuleType("homeassistant.helpers")
_ha_helpers_cv = ModuleType("homeassistant.helpers.config_validation")
_ha_helpers_er = ModuleType("homeassistant.helpers.entity_registry")
_ha_helpers_ar = ModuleType("homeassistant.helpers.area_registry")
_ha_helpers_dr = ModuleType("homeassistant.helpers.device_registry")
_ha_helpers_fr = ModuleType("homeassistant.helpers.floor_registry")
_ha_helpers_ep = ModuleType("homeassistant.helpers.entity_platform")
_ha_helpers_aiohttp = ModuleType("homeassistant.helpers.aiohttp_client")
_ha_components = ModuleType("homeassistant.components")
_ha_components_ha = ModuleType("homeassistant.components.homeassistant")
_ha_components_ha_exposed = ModuleType(
    "homeassistant.components.homeassistant.exposed_entities"
)
_ha_components_stt = ModuleType("homeassistant.components.stt")
_ha_exceptions = ModuleType("homeassistant.exceptions")

# Core
_ha_core.HomeAssistant = MagicMock
_ha_core.callback = lambda f: f
_ha_core.Event = MagicMock
_ha_core.ServiceCall = MagicMock
_ha_core.SupportsResponse = MagicMock()
_ha_core.SupportsResponse.ONLY = "only"
_ha_core.SupportsResponse.OPTIONAL = "optional"
_ha_core.SupportsResponse.NONE = "none"
_ha_core.ServiceResponse = dict  # ServiceResponse is a TypeAlias for dict

# Exceptions
_ha_exceptions.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
_ha_exceptions.ServiceValidationError = type(
    "ServiceValidationError",
    (_ha_exceptions.HomeAssistantError,),
    {"__init__": lambda self, *a, **kw: Exception.__init__(self, *a)},
)


# ── ConfigFlow / OptionsFlow base classes ──
# Provide real base classes so subclasses can be instantiated and tested.
class _MockConfigFlow:
    """Mock ConfigFlow base class."""

    VERSION = 1
    hass = None
    _reconfigure_entry_id = None

    def __init__(self):
        self.context = {}

    def __init_subclass__(cls, *, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_abort(self, **kwargs):
        return {"type": "abort", **kwargs}

    async def async_set_unique_id(self, unique_id):
        self.context["unique_id"] = unique_id

    def _abort_if_unique_id_configured(self):
        pass

    def async_update_reload_and_abort(self, entry, **kwargs):
        return {
            "type": "abort",
            "reason": kwargs.get("reason", "reconfigure_successful"),
        }

    def _get_reconfigure_entry(self):
        entry = MagicMock()
        entry.data = {}
        entry.entry_id = "existing_entry"
        return entry

    @staticmethod
    def async_get_options_flow(config_entry):
        raise NotImplementedError


class _MockOptionsFlow:
    """Mock OptionsFlow base class."""

    hass = None
    config_entry = None

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    @staticmethod
    def add_suggested_values_to_schema(schema, suggested_values):
        return schema


_ha_config_entries.ConfigEntry = MagicMock
_ha_config_entries.ConfigEntryAuthFailed = type(
    "ConfigEntryAuthFailed", (Exception,), {}
)
_ha_config_entries.ConfigEntryNotReady = type("ConfigEntryNotReady", (Exception,), {})


# data_entry_flow section mock
class _MockSection:
    """Mock section for data entry flows."""

    def __init__(self, schema, options=None):
        self.schema = schema
        self.options = options or {}

    def __call__(self, value):
        return self.schema(value)


_ha_data_entry_flow.section = _MockSection

_ha_config_entries.ConfigFlow = _MockConfigFlow
_ha_config_entries.ConfigFlowResult = dict  # It's a TypedDict
_ha_config_entries.OptionsFlow = _MockOptionsFlow
_ha_config_entries.OptionsFlowWithReload = _MockOptionsFlow

# Entity registry
_ha_helpers_er.async_get = MagicMock()
_ha_helpers_er.EVENT_ENTITY_REGISTRY_UPDATED = "entity_registry_updated"

# Area registry
_ha_helpers_ar.async_get = MagicMock()
_ha_helpers_ar.EVENT_AREA_REGISTRY_UPDATED = "area_registry_updated"

# Device registry
_ha_helpers_dr.async_get = MagicMock()
_ha_helpers_dr.EVENT_DEVICE_REGISTRY_UPDATED = "device_registry_updated"
_ha_helpers_dr.DeviceInfo = dict  # DeviceInfo is essentially a TypedDict


class _DeviceEntryType:
    SERVICE = "service"


_ha_helpers_dr.DeviceEntryType = _DeviceEntryType

# Floor registry
_ha_helpers_fr.async_get = MagicMock()
_ha_helpers_fr.EVENT_FLOOR_REGISTRY_UPDATED = "floor_registry_updated"

# Entity platform
_ha_helpers_ep.AddConfigEntryEntitiesCallback = MagicMock

# config_validation helper
_ha_helpers_cv.config_entry_only_config_schema = lambda domain: {}

# aiohttp client helper
_ha_helpers_aiohttp.async_get_clientsession = MagicMock()

# Storage helper
_ha_helpers_storage = ModuleType("homeassistant.helpers.storage")


class _MockStore:
    """Mock HA Store that keeps data in memory."""

    def __init__(self, hass, version, key):
        self._data = None

    async def async_load(self):
        return self._data

    async def async_save(self, data):
        self._data = data


_ha_helpers_storage.Store = _MockStore

# Selector helpers
_ha_helpers_selector = ModuleType("homeassistant.helpers.selector")
_ha_helpers_selector.TextSelector = MagicMock()
_ha_helpers_selector.TextSelectorConfig = MagicMock()
_ha_helpers_selector.SelectSelector = MagicMock()
_ha_helpers_selector.SelectSelectorConfig = MagicMock()
_ha_helpers_selector.SelectOptionDict = dict

# Exposed entities
_ha_components_ha_exposed.async_should_expose = MagicMock(return_value=True)

# Sensor platform
_ha_components_sensor = ModuleType("homeassistant.components.sensor")
_ha_components_sensor.SensorEntity = type(
    "SensorEntity", (), {"_attr_device_info": None, "_attr_unique_id": None}
)


class _MockRestoreSensor:
    """Mock RestoreSensor with state restore support."""

    _attr_device_info = None
    _attr_unique_id = None
    _attr_native_value = None
    _attr_should_poll = True
    hass = None

    async def async_get_last_sensor_data(self):
        return None

    def async_write_ha_state(self):
        pass

    async def async_added_to_hass(self):
        pass


_ha_components_sensor.RestoreSensor = _MockRestoreSensor


@_dataclass(frozen=True, kw_only=True)
class _MockSensorEntityDescription:
    """Mock SensorEntityDescription with fields used by AzureSTTSensorDescription."""

    key: str = ""
    translation_key: str | None = None
    name: str | None = None
    icon: str | None = None
    device_class: object = None
    state_class: object = None
    entity_category: object = None
    entity_registry_enabled_default: bool = True
    native_unit_of_measurement: str | None = None
    suggested_display_precision: int | None = None
    options: list | None = None


_ha_components_sensor.SensorEntityDescription = _MockSensorEntityDescription
_ha_components_sensor.SensorDeviceClass = MagicMock()
_ha_components_sensor.SensorDeviceClass.ENUM = "enum"
_ha_components_sensor.SensorStateClass = MagicMock()
_ha_components_sensor.SensorStateClass.TOTAL_INCREASING = "total_increasing"

# HA constants
_ha_const = ModuleType("homeassistant.const")
_ha_const.EntityCategory = MagicMock()
_ha_const.EntityCategory.DIAGNOSTIC = "diagnostic"
_ha_const.UnitOfInformation = MagicMock()
_ha_const.UnitOfInformation.BYTES = "B"
_ha_const.UnitOfTime = MagicMock()
_ha_const.UnitOfTime.MILLISECONDS = "ms"
_ha_const.UnitOfTime.MINUTES = "min"
_ha_const.UnitOfTime.SECONDS = "s"

# STT enums and classes
_ha_components_stt.AudioFormats = MagicMock()
_ha_components_stt.AudioFormats.WAV = "wav"
_ha_components_stt.AudioFormats.OGG = "ogg"
_ha_components_stt.AudioCodecs = MagicMock()
_ha_components_stt.AudioCodecs.PCM = "pcm"
_ha_components_stt.AudioCodecs.OPUS = "opus"
_ha_components_stt.AudioBitRates = MagicMock()
_ha_components_stt.AudioBitRates.BITRATE_16 = 16
_ha_components_stt.AudioSampleRates = MagicMock()
_ha_components_stt.AudioSampleRates.SAMPLERATE_16000 = 16000
_ha_components_stt.AudioChannels = MagicMock()
_ha_components_stt.AudioChannels.CHANNEL_MONO = 1
_ha_components_stt.SpeechMetadata = MagicMock
_ha_components_stt.SpeechResult = MagicMock
_ha_components_stt.SpeechResultState = MagicMock()
_ha_components_stt.SpeechResultState.SUCCESS = "success"
_ha_components_stt.SpeechResultState.ERROR = "error"
_ha_components_stt.SpeechToTextEntity = type(
    "SpeechToTextEntity",
    (),
    {"_attr_available": True, "async_write_ha_state": lambda self: None},
)

# Register all mocked modules
for mod_name, mod in [
    ("homeassistant", _ha),
    ("homeassistant.core", _ha_core),
    ("homeassistant.config_entries", _ha_config_entries),
    ("homeassistant.data_entry_flow", _ha_data_entry_flow),
    ("homeassistant.helpers", _ha_helpers),
    ("homeassistant.helpers.entity_registry", _ha_helpers_er),
    ("homeassistant.helpers.area_registry", _ha_helpers_ar),
    ("homeassistant.helpers.device_registry", _ha_helpers_dr),
    ("homeassistant.helpers.floor_registry", _ha_helpers_fr),
    ("homeassistant.helpers.entity_platform", _ha_helpers_ep),
    ("homeassistant.helpers.config_validation", _ha_helpers_cv),
    ("homeassistant.helpers.aiohttp_client", _ha_helpers_aiohttp),
    ("homeassistant.helpers.storage", _ha_helpers_storage),
    ("homeassistant.helpers.selector", _ha_helpers_selector),
    ("homeassistant.components", _ha_components),
    ("homeassistant.components.homeassistant", _ha_components_ha),
    (
        "homeassistant.components.homeassistant.exposed_entities",
        _ha_components_ha_exposed,
    ),
    ("homeassistant.components.stt", _ha_components_stt),
    ("homeassistant.components.sensor", _ha_components_sensor),
    ("homeassistant.const", _ha_const),
    ("homeassistant.exceptions", _ha_exceptions),
]:
    sys.modules[mod_name] = mod

# Also mock voluptuous since config_flow uses it
try:
    import voluptuous  # noqa: F401
except ImportError:
    _vol = MagicMock()
    sys.modules["voluptuous"] = _vol

import pytest  # noqa: E402


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=lambda: None)
    hass.states = MagicMock()
    hass.states.get = MagicMock(return_value=None)
    hass.services = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_register = MagicMock()
    hass.data = {}
    return hass
