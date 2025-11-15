"""
WienerNetze Smartmeter sensor platform
"""
import collections.abc
import logging
from datetime import timedelta
from typing import Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import core, config_entries
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA
)
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_DEVICE_ID
)
from homeassistant.core import DOMAIN
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
)
from .const import CONF_ZAEHLPUNKTE, CONF_ZUSAMMENSETZUNG, CONF_ENABLE_OPTIMA_AKTIV
from .wnsm_sensor import WNSMSensor
from .optima_aktiv_sensor import OptimaAktivPriceSensor

_LOGGER = logging.getLogger(__name__)
# Time between updating data from Wiener Netze
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
    # Get config from hass.data (set by __init__.py) or fallback to config_entry.data
    config = hass.data.get(DOMAIN, {}).get(config_entry.entry_id, config_entry.data)
    
    _LOGGER.debug(f"Setting up sensors with config keys: {list(config.keys())}")
    
    # Create main smartmeter sensors
    wnsm_sensors = []
    if CONF_ZAEHLPUNKTE in config and config[CONF_ZAEHLPUNKTE]:
        try:
            _LOGGER.info(f"Found {len(config[CONF_ZAEHLPUNKTE])} zaehlpunkt(e) in config")
            wnsm_sensors = [
                WNSMSensor(config[CONF_USERNAME], config[CONF_PASSWORD], zp["zaehlpunktnummer"])
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
    async_add_entities(sensors_to_add, update_before_add=True)


async def async_setup_platform(
    hass: core.HomeAssistant,  # pylint: disable=unused-argument
    config: ConfigType,
    async_add_entities: collections.abc.Callable,
    discovery_info: Optional[
        DiscoveryInfoType
    ] = None,  # pylint: disable=unused-argument
) -> None:
    """Set up the sensor platform by adding it into configuration.yaml"""
    wnsm_sensor = WNSMSensor(config[CONF_USERNAME], config[CONF_PASSWORD], config[CONF_DEVICE_ID])
    async_add_entities([wnsm_sensor], update_before_add=True)
