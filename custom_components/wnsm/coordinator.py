import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID

from .api import Smartmeter
from .AsyncSmartmeter import AsyncSmartmeter
from .const import DOMAIN, CONF_ZAEHLPUNKTE
from .importer import Importer
from .utils import before, today

_LOGGER = logging.getLogger(__name__)


class WienerNetzeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Wiener Netze."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entry = entry
        self.username = entry.data[CONF_USERNAME]
        self.password = entry.data[CONF_PASSWORD]
        
        # Initialize Smartmeter API
        self.smartmeter = Smartmeter(self.username, self.password)
        self.async_smartmeter = AsyncSmartmeter(hass, self.smartmeter)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # Ensure we are logged in
            await self.async_smartmeter.login()

            data = {}
            zaehlpunkte_config = self.entry.data.get(CONF_ZAEHLPUNKTE, [])
            
            if not zaehlpunkte_config:
                _LOGGER.warning("No zaehlpunkte configured")
                return data

            for zp_config in zaehlpunkte_config:
                zp_id = zp_config["zaehlpunktnummer"]
                try:
                    # Fetch Zaehlpunkt details (attributes)
                    zp_details = await self.async_smartmeter.get_zaehlpunkt(zp_id)
                    
                    meter_reading = None
                    # Fetch latest meter reading (state)
                    if self.async_smartmeter.is_active(zp_details):
                        # Try getting reading from yesterday or day before
                        reading_dates = [before(today(), 1), before(today(), 2)]
                        for reading_date in reading_dates:
                            meter_reading = await self.async_smartmeter.get_meter_reading_from_historic_data(
                                zp_id, reading_date, datetime.now()
                            )
                            if meter_reading is not None:
                                break
                        
                        if meter_reading is None:
                            _LOGGER.warning(f"Could not retrieve meter reading for {zp_id}")
                            
                        # Trigger Importer for historical statistics
                        # We do this here to ensure it runs regularly
                        # Importer handles its own check if it needs to run (< 24h check)
                        # We need unit_of_measurement and granularity. 
                        # Attributes might not be fully available here if we just fetched zp_details.
                        # wnsm_sensor used self.unit_of_measurement which defaults to KWH
                        # and self.granularity() from attributes.
                        
                        granularity = zp_details.get("granularity", "QUARTER_HOUR") if zp_details else "QUARTER_HOUR"
                        # Default to KWh as in WNSMSensor
                        unit = "kWh" 
                        
                        from .api.constants import ValueType
                        val_type = ValueType.from_str(granularity)
                        
                        importer = Importer(self.hass, self.async_smartmeter, zp_id, unit, val_type)
                        await importer.async_import()

                    data[zp_id] = {
                        "details": zp_details,
                        "reading": meter_reading,
                        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                    }
                    
                except Exception as e:
                    _LOGGER.error(f"Error updating zaehlpunkt {zp_id}: {e}")
                    # We continue to next zaehlpunkt instead of failing everything
                    data[zp_id] = {
                        "error": str(e),
                        "details": None,
                        "reading": None
                    }

            return data

        except Exception as e:
            _LOGGER.exception("Error updating Wiener Netze data")
            raise UpdateFailed(e) from e

