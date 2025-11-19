     1|"""
     2|Setting up config flow for homeassistant
     3|"""
     4|import logging
     5|from typing import Any, Optional
     6|
     7|import homeassistant.helpers.config_validation as cv
     8|import voluptuous as vol
     9|from homeassistant import config_entries
    10|from homeassistant.const import CONF_USERNAME, CONF_PASSWORD
    11|
    12|from .api import Smartmeter
    13|from .const import (
    14|    ATTRS_ZAEHLPUNKTE_CALL,
    15|    DOMAIN,
    16|    CONF_ZAEHLPUNKTE,
    17|    CONF_ZUSAMMENSETZUNG,
    18|    CONF_ENABLE_OPTIMA_AKTIV,
    19|)
    20|from .utils import translate_dict
    21|
    22|_LOGGER = logging.getLogger(__name__)
    23|
    24|AUTH_SCHEMA = vol.Schema(
    25|    {
    26|        vol.Required(CONF_USERNAME): cv.string,
    27|        vol.Required(CONF_PASSWORD): cv.string,
    28|    }
    29|)
    30|
    31|OPTIMA_AKTIV_SCHEMA = vol.Schema(
    32|    {
    33|        vol.Required(CONF_ENABLE_OPTIMA_AKTIV, default=False): cv.boolean,
    34|    }
    35|)
    36|
    37|ZUSAMMENSETZUNG_SCHEMA = vol.Schema(
    38|    {
    39|        vol.Required(CONF_ZUSAMMENSETZUNG, default="basismix"): vol.In(
    40|            ["okopure", "sonnenmix", "basismix"]
    41|        ),
    42|    }
    43|)
    44|
    45|
    46|class WienerNetzeSmartMeterCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    47|    """Wiener Netze Smartmeter config flow"""
    48|
    49|    VERSION = 1
    50|
    51|    data: Optional[dict[str, Any]]
    52|
    53|    async def validate_auth(self, username: str, password: str) -> list[dict]:
    54|        """
    55|        Validates credentials for smartmeter.
    56|        Raises a ValueError if the auth credentials are invalid.
    57|        """
    58|        smartmeter = Smartmeter(username, password)
    59|        await self.hass.async_add_executor_job(smartmeter.login)
    60|        contracts = await self.hass.async_add_executor_job(smartmeter.zaehlpunkte)
    61|        zaehlpunkte = []
    62|        if contracts is not None and isinstance(contracts, list) and len(contracts) > 0:
    63|            for contract in contracts:
    64|                if "zaehlpunkte" in contract:
    65|                    zaehlpunkte.extend(contract["zaehlpunkte"])
    66|        return zaehlpunkte
    67|
    68|    async def async_step_user(self, user_input: Optional[dict[str, Any]] = None):
    69|        """Invoked when a user initiates a flow via the user interface."""
    70|        errors: dict[str, str] = {}
    71|        if user_input is not None:
    72|            try:
    73|                zps = await self.validate_auth(
    74|                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
    75|                )
    76|            except Exception as exception:  # pylint: disable=broad-except
    77|                _LOGGER.error("Error validating Wiener Netze auth")
    78|                _LOGGER.exception(exception)
    79|                errors["base"] = "auth"
    80|            if not errors:
    81|                # Input is valid, set data and move to next step
    82|                self.data = user_input
    83|                self.data[CONF_ZAEHLPUNKTE] = [
    84|                    translate_dict(zp, ATTRS_ZAEHLPUNKTE_CALL)
    85|                    for zp in zps
    86|                    if zp["isActive"]  # only create active zaehlpunkte, as inactive ones can appear in old contracts
    87|                ]
    88|                # Move to Optima Aktiv step
    89|                return await self.async_step_optima_aktiv()
    90|
    91|        return self.async_show_form(
    92|            step_id="user", data_schema=AUTH_SCHEMA, errors=errors
    93|        )
    94|
    95|    async def async_step_optima_aktiv(self, user_input: Optional[dict[str, Any]] = None):
    96|        """Ask user if they want to add Optima Aktiv price sensor."""
    97|        if user_input is not None:
    98|            if self.data is None:
    99|                self.data = {}
   100|            enable_optima_aktiv = user_input.get(CONF_ENABLE_OPTIMA_AKTIV, False)
   101|            self.data[CONF_ENABLE_OPTIMA_AKTIV] = enable_optima_aktiv
   102|            
   103|            _LOGGER.debug(f"Creating entry with data keys: {list(self.data.keys())}")
   104|            if CONF_ZAEHLPUNKTE in self.data:
   105|                _LOGGER.debug(f"Zaehlpunkte count: {len(self.data[CONF_ZAEHLPUNKTE])}")
   106|            
   107|            if enable_optima_aktiv:
   108|                # If enabled, ask for Zusammensetzung
   109|                return await self.async_step_zusammensetzung()
   110|            else:
   111|                # If not enabled, create entry
   112|                return self.async_create_entry(
   113|                    title="Wiener Netze Smartmeter", data=self.data
   114|                )
   115|
   116|        return self.async_show_form(
   117|            step_id="optima_aktiv",
   118|            data_schema=OPTIMA_AKTIV_SCHEMA,
   119|            description_placeholders={
   120|                "optima_aktiv": "Optima Aktiv"
   121|            },
   122|        )
   123|
   124|    async def async_step_zusammensetzung(self, user_input: Optional[dict[str, Any]] = None):
   125|        """Ask user to select Zusammensetzung for Optima Aktiv."""
   126|        if user_input is not None:
   127|            if self.data is None:
   128|                self.data = {}
   129|            self.data[CONF_ZUSAMMENSETZUNG] = user_input[CONF_ZUSAMMENSETZUNG]
   130|            
   131|            _LOGGER.debug(f"Creating entry with data keys: {list(self.data.keys())}")
   132|            if CONF_ZAEHLPUNKTE in self.data:
   133|                _LOGGER.debug(f"Zaehlpunkte count: {len(self.data[CONF_ZAEHLPUNKTE])}")
   134|            
   135|            # User is done, create entry
   136|            return self.async_create_entry(
   137|                title="Wiener Netze Smartmeter", data=self.data
   138|            )
   139|
   140|        return self.async_show_form(
   141|            step_id="zusammensetzung",
   142|            data_schema=ZUSAMMENSETZUNG_SCHEMA,
   143|            description_placeholders={
   144|                "zusammensetzung": "Zusammensetzung"
   145|            },
   146|        )
