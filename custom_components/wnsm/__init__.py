"""Set up the Wiener Netze SmartMeter Integration component."""
import logging
from homeassistant import core, config_entries
from homeassistant.core import DOMAIN

from .coordinator import WienerNetzeCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: core.HomeAssistant,
        entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    _LOGGER.debug("Initializing WNSM entry: %s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = WienerNetzeCoordinator(hass, entry)
    _LOGGER.debug("Coordinator created, refreshing data...")
    
    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.debug("Coordinator refresh successful")
    
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug("Coordinator added to hass.data[%s][%s]", DOMAIN, entry.entry_id)

    # Forward the setup to the sensor platform.
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    _LOGGER.debug("Forwarded setup to sensor platform")

    return True
