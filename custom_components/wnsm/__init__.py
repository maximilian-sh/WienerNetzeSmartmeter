"""Set up the Wiener Netze SmartMeter Integration component."""
import logging
from homeassistant import core, config_entries

from .const import DOMAIN
from .coordinator import WienerNetzeCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: core.HomeAssistant,
        entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    _LOGGER.debug("Initializing WNSM entry: %s", entry.entry_id)
    # DOMAIN is "wnsm"
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = WienerNetzeCoordinator(hass, entry)
    _LOGGER.debug("Coordinator created, refreshing data...")
    
    # Store the coordinator using entry.entry_id as the key BEFORE refreshing data
    # This ensures it's available if the refresh triggers listeners immediately or if we forward setup
    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug("Coordinator added to hass.data[%s][%s]", DOMAIN, entry.entry_id)
    
    # Fetch initial data so we have data when entities subscribe
    # We do this AFTER adding to hass.data, just in case something needs it
    try:
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug("Coordinator refresh successful")
    except Exception as e:
        _LOGGER.warning("Initial coordinator refresh failed: %s", e)
        # We continue anyway, the coordinator will retry

    # Forward the setup to the sensor platform.
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    _LOGGER.debug("Forwarded setup to sensor platform")

    return True
