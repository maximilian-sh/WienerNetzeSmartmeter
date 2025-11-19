"""
Setting up config flow for homeassistant
"""
import logging
from typing import Any, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from .api import Smartmeter
from .const import (
    ATTRS_ZAEHLPUNKTE_CALL,
    DOMAIN,
    CONF_ZAEHLPUNKTE,
    CONF_ZUSAMMENSETZUNG,
    CONF_ENABLE_OPTIMA_AKTIV,
)
from .utils import translate_dict

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

OPTIMA_AKTIV_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENABLE_OPTIMA_AKTIV, default=False): cv.boolean,
    }
)

ZUSAMMENSETZUNG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ZUSAMMENSETZUNG, default="basismix"): vol.In(
            ["okopure", "sonnenmix", "basismix"]
        ),
    }
)


class WienerNetzeSmartMeterCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Wiener Netze Smartmeter config flow"""

    VERSION = 1

    data: Optional[dict[str, Any]]

    async def validate_auth(self, username: str, password: str) -> list[dict]:
        """
        Validates credentials for smartmeter.
        Raises a ValueError if the auth credentials are invalid.
        """
        smartmeter = Smartmeter(username, password)
        await self.hass.async_add_executor_job(smartmeter.login)
        contracts = await self.hass.async_add_executor_job(smartmeter.zaehlpunkte)
        zaehlpunkte = []
        if contracts is not None and isinstance(contracts, list) and len(contracts) > 0:
            for contract in contracts:
                if "zaehlpunkte" in contract:
                    zaehlpunkte.extend(contract["zaehlpunkte"])
        return zaehlpunkte

    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                zps = await self.validate_auth(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except Exception as exception:  # pylint: disable=broad-except
                _LOGGER.error("Error validating Wiener Netze auth")
                _LOGGER.exception(exception)
                errors["base"] = "auth"
            if not errors:
                # Input is valid, set data and move to next step
                self.data = user_input
                self.data[CONF_ZAEHLPUNKTE] = [
                    translate_dict(zp, ATTRS_ZAEHLPUNKTE_CALL)
                    for zp in zps
                    if zp["isActive"]  # only create active zaehlpunkte, as inactive ones can appear in old contracts
                ]
                # Move to Optima Aktiv step
                return await self.async_step_optima_aktiv()

        return self.async_show_form(
            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
        )

    async def async_step_optima_aktiv(self, user_input: Optional[dict[str, Any]] = None):
        """Ask user if they want to add Optima Aktiv price sensor."""
        if user_input is not None:
            if self.data is None:
                self.data = {}
            enable_optima_aktiv = user_input.get(CONF_ENABLE_OPTIMA_AKTIV, False)
            self.data[CONF_ENABLE_OPTIMA_AKTIV] = enable_optima_aktiv
            
            _LOGGER.debug(f"Creating entry with data keys: {list(self.data.keys())}")
            if CONF_ZAEHLPUNKTE in self.data:
                _LOGGER.debug(f"Zaehlpunkte count: {len(self.data[CONF_ZAEHLPUNKTE])}")
            
            if enable_optima_aktiv:
                # If enabled, ask for Zusammensetzung
                return await self.async_step_zusammensetzung()
            else:
                # If not enabled, create entry
                return self.async_create_entry(
                    title="Wiener Netze Smartmeter", data=self.data
                )

        return self.async_show_form(
            step_id="optima_aktiv",
            data_schema=OPTIMA_AKTIV_SCHEMA,
            description_placeholders={
                "optima_aktiv": "Optima Aktiv"
            },
        )

    async def async_step_zusammensetzung(self, user_input: Optional[dict[str, Any]] = None):
        """Ask user to select Zusammensetzung for Optima Aktiv."""
        if user_input is not None:
            if self.data is None:
                self.data = {}
            self.data[CONF_ZUSAMMENSETZUNG] = user_input[CONF_ZUSAMMENSETZUNG]
            
            _LOGGER.debug(f"Creating entry with data keys: {list(self.data.keys())}")
            if CONF_ZAEHLPUNKTE in self.data:
                _LOGGER.debug(f"Zaehlpunkte count: {len(self.data[CONF_ZAEHLPUNKTE])}")
            
            # User is done, create entry
            return self.async_create_entry(
                title="Wiener Netze Smartmeter", data=self.data
            )

        return self.async_show_form(
            step_id="zusammensetzung",
            data_schema=ZUSAMMENSETZUNG_SCHEMA,
            description_placeholders={
                "zusammensetzung": "Zusammensetzung"
            },
        )
