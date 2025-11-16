import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    ENTITY_ID_FORMAT
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .AsyncSmartmeter import AsyncSmartmeter
from .api import Smartmeter
from .api.constants import ValueType
from .importer import Importer
from .utils import before, today

_LOGGER = logging.getLogger(__name__)


class WNSMSensor(SensorEntity):
    """
    Representation of a Wiener Smartmeter sensor
    for measuring total increasing energy consumption for a specific zaehlpunkt
    """

    def _icon(self) -> str:
        return "mdi:flash"

    def __init__(self, username: str, password: str, zaehlpunkt: str) -> None:
        super().__init__()
        self.username = username
        self.password = password
        self.zaehlpunkt = zaehlpunkt

        self._attr_native_value: int | float | None = 0
        self._attr_extra_state_attributes = {}
        self._attr_name = zaehlpunkt
        self._attr_icon = self._icon()
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR

        self.attrs: dict[str, Any] = {}
        self._name: str = zaehlpunkt
        self._available: bool = True
        self._updatets: str | None = None
        self._remove_update_listener: Callable[[], None] | None = None

    @property
    def get_state(self) -> Optional[str]:
        return f"{self._attr_native_value:.3f}"

    @property
    def _id(self):
        return ENTITY_ID_FORMAT.format(slugify(self._name).lower())

    @property
    def icon(self) -> str:
        return self._attr_icon

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self.zaehlpunkt

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    def granularity(self) -> ValueType:
        return ValueType.from_str(self._attr_extra_state_attributes.get("granularity", "QUARTER_HOUR"))

    @property
    def scan_interval(self) -> timedelta:
        """
        Update interval for smart meter sensors.
        Always updates hourly to get the latest data from the smart meter.
        """
        return timedelta(minutes=60)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Schedule updates at exactly xx:00 (minute 0, second 0 of every hour)
        # Using minute=0, second=0 without hour parameter triggers every hour at :00
        self._remove_update_listener = async_track_time_change(
            self.hass,
            self._scheduled_update,
            minute=0,
            second=0
        )
        _LOGGER.debug(f"Scheduled hourly updates at xx:00 for {self.zaehlpunkt}")
        
        # Trigger initial update if we're not at the top of the hour
        # This ensures the sensor is updated immediately on startup
        now = dt_util.utcnow()
        if now.minute != 0 or now.second != 0:
            _LOGGER.debug(f"Not at top of hour ({now.strftime('%H:%M:%S')}), triggering initial update for {self.zaehlpunkt}")
            await self.async_update()

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        if self._remove_update_listener:
            self._remove_update_listener()
            self._remove_update_listener = None
        await super().async_will_remove_from_hass()

    async def _scheduled_update(self, now: datetime) -> None:
        """Callback for scheduled updates at xx:00."""
        _LOGGER.debug(f"Scheduled update triggered at {now.strftime('%Y-%m-%d %H:%M:%S')} for {self.zaehlpunkt}")
        await self.async_update()

    async def async_update(self):
        """
        update sensor
        """
        try:
            smartmeter = Smartmeter(username=self.username, password=self.password)
            async_smartmeter = AsyncSmartmeter(self.hass, smartmeter)
            await async_smartmeter.login()
            zaehlpunkt_response = await async_smartmeter.get_zaehlpunkt(self.zaehlpunkt)
            self._attr_extra_state_attributes = zaehlpunkt_response

            if async_smartmeter.is_active(zaehlpunkt_response):
                # Since the update is not exactly at midnight, both yesterday and the day before are tried to make sure a meter reading is returned
                reading_dates = [before(today(), 1), before(today(), 2)]
                meter_reading = None
                for reading_date in reading_dates:
                    meter_reading = await async_smartmeter.get_meter_reading_from_historic_data(self.zaehlpunkt, reading_date, datetime.now())
                    if meter_reading is not None:
                        self._attr_native_value = meter_reading
                        break
                if meter_reading is None:
                    _LOGGER.warning(f"Could not retrieve meter reading for {self.zaehlpunkt}")
                importer = Importer(self.hass, async_smartmeter, self.zaehlpunkt, self.unit_of_measurement, self.granularity())
                await importer.async_import()
            self._available = True
            self._updatets = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        except TimeoutError as e:
            self._available = False
            _LOGGER.warning(
                "Error retrieving data from smart meter api - Timeout: %s" % e)
        except RuntimeError as e:
            self._available = False
            _LOGGER.exception(
                "Error retrieving data from smart meter api - Error: %s" % e)
