"""
Wiener Energie Optima Aktiv price sensor
"""
import logging
import re
from datetime import datetime
from typing import Any, Optional

import requests
from lxml import html
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
    SensorEntity,
)
from homeassistant.const import UnitOfEnergy

_LOGGER = logging.getLogger(__name__)

WIEN_ENERGIE_OPTIMA_AKTIV_BASE_URL = "https://www.wienenergie.at/privat/produkte/strom/optima-aktiv/"

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

    async def async_update(self):
        """
        Update sensor by fetching price from Wien Energie website
        """
        try:
            # Fetch the webpage with the selected Zusammensetzung
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

    def _build_url(self) -> str:
        """
        Build the URL with the selected Zusammensetzung option.
        
        Returns:
            Complete URL with query parameters
        """
        from datetime import date
        
        # Format: SOPTA_0001-{zusammensetzung}-none
        options = f"SOPTA_0001-{self.zusammensetzung}-none"
        prozessdatum = date.today().strftime("%Y-%m-%d")
        
        return f"{WIEN_ENERGIE_OPTIMA_AKTIV_BASE_URL}?prozessdatum={prozessdatum}&options={options}"

    def _fetch_price_data(self) -> Optional[dict[str, Any]]:
        """
        Fetch and parse price data from Wien Energie website.
        
        Returns:
            Dictionary with 'verbrauchspreis' key, or None on error
        """
        try:
            url = self._build_url()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            tree = html.fromstring(response.content)
            
            verbrauchspreis = None
            
            # Try multiple parsing strategies
            # Strategy 1: Look for price elements with class containing "cardPrice"
            price_elements = tree.xpath('//p[contains(@class, "cardPrice")]')
            
            # Strategy 2: Look for spans with "Verbrauchspreis" label
            verbrauchspreis_spans = tree.xpath('//span[contains(text(), "Verbrauchspreis")]')
            
            # Strategy 3: Look for any element containing "Verbrauchspreis"
            verbrauchspreis_elements = tree.xpath('//*[contains(text(), "Verbrauchspreis")]')
            
            # Try to find price near the Verbrauchspreis label
            for span in verbrauchspreis_spans:
                # Look in parent container
                parent = span.getparent()
                if parent is not None:
                    # Look for price in sibling or parent elements
                    container = parent.getparent() if parent.getparent() is not None else parent
                    price_texts = container.xpath('.//p[contains(@class, "cardPrice")]//text()')
                    if not price_texts:
                        # Try any text node containing numbers and Cent/kWh
                        price_texts = container.xpath('.//text()[contains(., "Cent/kWh")]')
                    for price_text in price_texts:
                        match = re.search(r'([\d,]+)\s*Cent/kWh', price_text)
                        if match:
                            verbrauchspreis_str = match.group(1).replace(',', '.')
                            verbrauchspreis = float(verbrauchspreis_str)
                            break
                    if verbrauchspreis is not None:
                        break
            
            # Fallback: parse all price elements and match by content
            if verbrauchspreis is None:
                for element in price_elements:
                    text = element.text_content().strip()
                    
                    # Check if it's Verbrauchspreis (contains Cent/kWh)
                    if "Cent/kWh" in text:
                        match = re.search(r'([\d,]+)\s*Cent/kWh', text)
                        if match:
                            verbrauchspreis_str = match.group(1).replace(',', '.')
                            verbrauchspreis = float(verbrauchspreis_str)
                            break
            
            # Another fallback: search in all text nodes
            if verbrauchspreis is None:
                all_text_nodes = tree.xpath('//text()[contains(., "Cent/kWh")]')
                for text_node in all_text_nodes:
                    match = re.search(r'([\d,]+)\s*Cent/kWh', text_node)
                    if match:
                        verbrauchspreis_str = match.group(1).replace(',', '.')
                        verbrauchspreis = float(verbrauchspreis_str)
                        break
            
            # Last resort: regex search on full HTML
            if verbrauchspreis is None:
                all_text = response.text
                # Try multiple patterns
                patterns = [
                    r'Verbrauchspreis[^>]*>.*?([\d,]+)\s*Cent/kWh',
                    r'([\d,]+)\s*Cent/kWh[^<]*Verbrauchspreis',
                    r'Verbrauchspreis.*?([\d,]+)\s*Cent/kWh',
                ]
                for pattern in patterns:
                    verbrauchspreis_match = re.search(pattern, all_text, re.DOTALL | re.IGNORECASE)
                    if verbrauchspreis_match:
                        verbrauchspreis_str = verbrauchspreis_match.group(1).replace(',', '.')
                        try:
                            verbrauchspreis = float(verbrauchspreis_str)
                            break
                        except ValueError:
                            continue
            
            if verbrauchspreis is None:
                _LOGGER.warning(
                    f"Could not parse Verbrauchspreis for {self.zusammensetzung}. "
                    f"Found {len(price_elements)} price elements, {len(verbrauchspreis_spans)} Verbrauchspreis spans. "
                    f"URL: {url}"
                )
                # Log a sample of the HTML for debugging
                if len(price_elements) > 0:
                    _LOGGER.debug(f"Sample price element text: {price_elements[0].text_content()[:200]}")
                return None
            
            return {
                "verbrauchspreis": verbrauchspreis,
                "last_update": datetime.now().isoformat(),
                "url": url,
            }
            
        except requests.RequestException as e:
            _LOGGER.error(f"Error fetching Wien Energie website: {e}")
            return None
        except Exception as e:
            _LOGGER.error(f"Error parsing Wien Energie website: {e}")
            return None
