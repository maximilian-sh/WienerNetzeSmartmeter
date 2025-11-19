"""Set up the Wiener Netze SmartMeter Integration component."""
from homeassistant import core, config_entries
from homeassistant.core import DOMAIN

from .coordinator import WienerNetzeCoordinator

async def async_setup_entry(
        hass: core.HomeAssistant,
        entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = WienerNetzeCoordinator(hass, entry)
    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()
    
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Forward the setup to the sensor platform.
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    return True
