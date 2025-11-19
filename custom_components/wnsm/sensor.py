"""
WienerNetze Smartmeter sensor platform
"""
import collections.abc
import logging
from datetime import timedelta
from typing import Optional, Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import core, config_entries
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
    ENTITY_ID_FORMAT
)
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_DEVICE_ID,
    UnitOfEnergy,
)
from homeassistant.core import DOMAIN as HASS_DOMAIN
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN, CONF_ZAEHLPUNKTE, CONF_ZUSAMMENSETZUNG, CONF_ENABLE_OPTIMA_AKTIV
from .optima_aktiv_sensor import OptimaAktivPriceSensor
from .coordinator import WienerNetzeCoordinator

_LOGGER = logging.getLogger(__name__)

# Time between updating data from Wiener Netze (deprecated for platform setup, but kept for valid config)
SCAN_INTERVAL = timedelta(minutes=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
    }
)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    _LOGGER.debug("Setting up sensors for entry: %s", config_entry.entry_id)
    
    # Debug logging to diagnose why coordinator is missing
    if DOMAIN in hass.data:
        _LOGGER.debug("Keys in hass.data[%s]: %s", DOMAIN, list(hass.data[DOMAIN].keys()))
    else:
        _LOGGER.error("hass.data[%s] is missing!", DOMAIN)

    # Use config_entry.entry_id to access the coordinator, but check if key exists safely
    if DOMAIN not in hass.data or config_entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("Coordinator not found in hass.data for entry %s. Setup aborted.", config_entry.entry_id)
        return

    coordinator: WienerNetzeCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    config = config_entry.data
    
    _LOGGER.debug(f"Setting up sensors with config keys: {list(config.keys())}")
    
    # Create main smartmeter sensors
    wnsm_sensors = []
    if CONF_ZAEHLPUNKTE in config and config[CONF_ZAEHLPUNKTE]:
        try:
            _LOGGER.info(f"Found {len(config[CONF_ZAEHLPUNKTE])} zaehlpunkt(e) in config")
            wnsm_sensors = [
                WNSMCoordinatedSensor(coordinator, zp["zaehlpunktnummer"])
                for zp in config[CONF_ZAEHLPUNKTE]
            ]
            _LOGGER.info(f"Created {len(wnsm_sensors)} smartmeter sensor(s)")
        except KeyError as e:
            _LOGGER.error(f"Missing required key in zaehlpunkt data: {e}")
            _LOGGER.exception(e)
        except Exception as e:
            _LOGGER.error(f"Failed to create smartmeter sensors: {e}")
            _LOGGER.exception(e)
    else:
        _LOGGER.error(
            f"No zaehlpunkte found in config. Config keys: {list(config.keys())}. "
            f"CONF_ZAEHLPUNKTE present: {CONF_ZAEHLPUNKTE in config}, "
            f"Value: {config.get(CONF_ZAEHLPUNKTE)}"
        )
    
    # Add Optima Aktiv Verbrauchspreis sensor only if enabled
    sensors_to_add = list(wnsm_sensors)
    if config.get(CONF_ENABLE_OPTIMA_AKTIV, False):
        try:
            zusammensetzung = config.get(CONF_ZUSAMMENSETZUNG, "basismix")
            optima_aktiv_sensor = OptimaAktivPriceSensor(zusammensetzung)
            sensors_to_add.append(optima_aktiv_sensor)
            _LOGGER.info(f"Added Optima Aktiv sensor with Zusammensetzung: {zusammensetzung}")
        except Exception as e:
            _LOGGER.error(
                f"Failed to create Optima Aktiv sensor: {e}. "
                "Integration will continue without price sensor."
            )
            _LOGGER.exception(e)
            # Continue without the price sensor - don't break the entire integration
    
    if not sensors_to_add:
        _LOGGER.error(
            f"No sensors to add! Check configuration. "
            f"wnsm_sensors: {len(wnsm_sensors)}, "
            f"optima_aktiv_enabled: {config.get(CONF_ENABLE_OPTIMA_AKTIV, False)}"
        )
        return
    
    _LOGGER.info(f"Adding {len(sensors_to_add)} sensor(s) total ({len(wnsm_sensors)} smartmeter + {len(sensors_to_add) - len(wnsm_sensors)} Optima Aktiv)")
    async_add_entities(sensors_to_add)


async def async_setup_platform(
    hass: core.HomeAssistant,
    config: ConfigType,
    async_add_entities: collections.abc.Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform by adding it into configuration.yaml"""
    # This platform setup is legacy and doesn't support the coordinator well 
    # because coordinator needs a config entry. 
    # But for backward compatibility if anyone uses YAML setup (which is not recommended for this integration usually)
    # we might need to support it or just warn.
    # Given the complexity, we'll log a warning that YAML setup is deprecated/not fully supported for new features.
    _LOGGER.warning("YAML configuration is deprecated. Please use the UI integration.")
    pass


class WNSMCoordinatedSensor(CoordinatorEntity, SensorEntity):
    """
    Representation of a Wiener Smartmeter sensor
    for measuring total increasing energy consumption for a specific zaehlpunkt
    using DataUpdateCoordinator.
    """

    def __init__(self, coordinator: WienerNetzeCoordinator, zaehlpunkt: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.zaehlpunkt = zaehlpunkt
        self._name = zaehlpunkt
        
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:flash"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.zaehlpunkt

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.zaehlpunkt in self.coordinator.data
            and "error" not in self.coordinator.data[self.zaehlpunkt]
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.available:
            return None
        return self.coordinator.data[self.zaehlpunkt].get("reading")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.available:
            return {}
        data = self.coordinator.data[self.zaehlpunkt]
        attributes = data.get("details") or {}
        attributes["last_update"] = data.get("timestamp")
        return attributes
