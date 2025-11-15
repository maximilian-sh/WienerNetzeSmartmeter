"""
Wiener Energie Optima Aktiv price sensor
"""
import json
import logging
import re
from datetime import date, datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import requests
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
)
from homeassistant.const import UnitOfEnergy

_LOGGER = logging.getLogger(__name__)

WIEN_ENERGIE_API_URL = "https://www.wienenergie.at/wp-json/tarife/tarifberater"

# Zusammensetzung options
ZUSAMMENSETZUNG_OPTIONS = {
    "okopure": "okopure",
    "sonnenmix": "sonnenmix",
    "basismix": "basismix",
}


class OptimaAktivPriceSensor(SensorEntity):
    """
    Representation of a Wiener Energie Optima Aktiv Verbrauchspreis sensor
    """

    def _icon(self) -> str:
        return "mdi:currency-eur"

    def __init__(self, zusammensetzung: str = "basismix") -> None:
        """
        Initialize the sensor.
        
        Args:
            zusammensetzung: Energy composition type - 'okopure', 'sonnenmix', or 'basismix' (default)
        """
        super().__init__()
        if zusammensetzung not in ZUSAMMENSETZUNG_OPTIONS:
            raise ValueError(
                f"Invalid zusammensetzung: {zusammensetzung}. "
                f"Must be one of: {', '.join(ZUSAMMENSETZUNG_OPTIONS.keys())}"
            )
        self.zusammensetzung = zusammensetzung
        
        self._attr_native_value: float | None = None
        self._attr_extra_state_attributes = {}
        
        # Set sensor name and unique ID based on Zusammensetzung
        zusammensetzung_display = {
            "okopure": "Ökopure",
            "sonnenmix": "Sonnenmix",
            "basismix": "Basismix",
        }.get(zusammensetzung, zusammensetzung.capitalize())
        
        self._attr_name = f"Optima Aktiv Verbrauchspreis ({zusammensetzung_display})"
        self._attr_unique_id = f"optima_aktiv_verbrauchspreis_{zusammensetzung}"
        self._attr_native_unit_of_measurement = "Cent/kWh"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_icon = self._icon()
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._available: bool = True
        self._updatets: str | None = None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def scan_interval(self) -> timedelta:
        """
        Update interval for the price sensor.
        Updates daily to get the latest price data.
        """
        return timedelta(hours=24)

    async def async_update(self):
        """
        Update sensor by fetching price from Wien Energie API
        """
        try:
            # Fetch price data from API
            response = await self.hass.async_add_executor_job(
                self._fetch_price_data
            )
            
            if response is None:
                self._available = False
                return
            
            self._attr_native_value = response.get("verbrauchspreis")
            
            self._attr_extra_state_attributes = {
                "zusammensetzung": self.zusammensetzung,
                "last_update": response.get("last_update"),
                "url": response.get("url"),
            }
            self._available = True
            self._updatets = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            
        except Exception as e:
            self._available = False
            _LOGGER.exception(
                f"Error retrieving Optima Aktiv price data - Error: {e}"
            )

    def _build_api_url(self) -> str:
        """
        Build the API URL with the selected Zusammensetzung option.
        
        Returns:
            Complete API URL with query parameters
        """
        # Format: SOPTA_0001-{zusammensetzung}-none
        options = f"SOPTA_0001-{self.zusammensetzung}-none"
        prozessdatum = date.today().strftime("%Y-%m-%dT00:00:00Z")
        
        params = {
            "type": "strom",
            "product": "SOPTA_0001",
            "kwh": "2300",  # Default consumption for price calculation
            "plz": "1210",  # Default postal code (Vienna)
            "options": options,
            "prozessdatum": prozessdatum
        }
        
        return f"{WIEN_ENERGIE_API_URL}?{urlencode(params)}"

    def _fetch_price_data(self) -> Optional[dict[str, Any]]:
        """
        Fetch and parse price data from Wien Energie API.
        
        Returns:
            Dictionary with 'verbrauchspreis' key, or None on error
        """
        try:
            url = self._build_api_url()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            
            if not data.get("success"):
                _LOGGER.warning(f"API returned success=false for {self.zusammensetzung}")
                return None
            
            if not data.get("data") or len(data["data"]) == 0:
                _LOGGER.warning(f"No data returned from API for {self.zusammensetzung}")
                return None
            
            content = data["data"][0].get("content", {})
            price_list = content.get("list", [])
            
            # Find Verbrauchspreis in the list using next() for efficiency
            verbrauchspreis_item = next(
                (item for item in price_list if item.get("name") == "Verbrauchspreis:"),
                None
            )
            
            if verbrauchspreis_item is None:
                _LOGGER.warning(
                    f"Could not find Verbrauchspreis in API response for {self.zusammensetzung}. "
                    f"Available items: {[item.get('name') for item in price_list]}"
                )
                return None
            
            # Extract price: "17,4237 Cent/kWh" -> 17.4237
            price_str = verbrauchspreis_item.get("shortValue", "")
            price_match = re.search(r'([\d,]+)', price_str)
            if not price_match:
                _LOGGER.warning(f"Could not extract price from '{price_str}'")
                return None
            
            verbrauchspreis = float(price_match.group(1).replace(',', '.'))
            
            return {
                "verbrauchspreis": verbrauchspreis,
                "last_update": datetime.now().isoformat(),
                "url": url,
            }
            
        except requests.RequestException as e:
            _LOGGER.error(f"Error fetching Wien Energie API: {e}")
            return None
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Error parsing JSON response from Wien Energie API: {e}")
            return None
        except (ValueError, KeyError) as e:
            _LOGGER.error(f"Error processing Wien Energie API response: {e}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error processing Wien Energie API response: {e}")
            _LOGGER.exception(e)
            return None
