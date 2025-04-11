import logging
import voluptuous as vol
from typing import Any, Dict, Optional
from homeassistant import config_entries
from .const import (
    DOMAIN,
    CONF_ZIPCODE,
    CONF_RADIUS,
    CONF_COUNTY_ID,
    COUNTIES,
    CONF_LOOKAHEAD,
    CONF_TIMEFORMAT,
    CONF_ZIPFILTER,
    RADIUS_OPTIONS,
    DEFAULT_TIMEFORMAT,
)

_LOGGER = logging.getLogger(__name__)

class DRKBlutspendeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DRK Blutspende."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}
        
        if user_input is not None:
            return self.async_create_entry(title="DRK Blutspende", data=user_input)
        
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ZIPCODE): str,
                vol.Optional(CONF_RADIUS, default=10): vol.In(RADIUS_OPTIONS),
                vol.Optional(CONF_COUNTY_ID): vol.In(COUNTIES),
                vol.Optional(CONF_LOOKAHEAD, default=7): int,
                vol.Optional(CONF_TIMEFORMAT, default=DEFAULT_TIMEFORMAT): str,
                vol.Optional(CONF_ZIPFILTER, default=""): str
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

#     @staticmethod
#     @callback
#     def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "DRKBlutspendeOptionsFlowHandler":
#         return DRKBlutspendeOptionsFlowHandler(config_entry)
#
# class DRKBlutspendeOptionsFlowHandler(config_entries.OptionsFlow):
#     """Handle options flow for DRK Blutspende."""
#
#     def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
#         """Initialize options flow."""
#         self.config_entry = config_entry
#
#     async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> config_entries.FlowResult:
#         """Manage the options."""
#         errors: Dict[str, str] = {}
#
#         if user_input is not None:
#             return self.async_create_entry(title="", data=user_input)
#
#         data_schema = vol.Schema(
#             {
#                 vol.Optional(CONF_RADIUS, default=self.config_entry.options.get(CONF_RADIUS, 10)): vol.In(RADIUS_OPTIONS),
#                 vol.Optional(CONF_LOOKAHEAD, default=self.config_entry.options.get(CONF_LOOKAHEAD, 7)): int,
#                 vol.Optional(CONF_TIMEFORMAT, default=self.config_entry.options.get(CONF_TIMEFORMAT, DEFAULT_TIMEFORMAT)): str,
#                 # vol.Optional(CONF_ZIPFILTER, default=self.config_entry.options.get(CONF_ZIPFILTER, [])): vol.All(list, [vol.Match(CONF_ZIP_REGEX)]),
#                 vol.Optional(CONF_ZIPFILTER): vol.All(list, [vol.Match(CONF_ZIP_REGEX)]),
#             }
#         )
#
#         return self.async_show_form(step_id="init", data_schema=data_schema, errors=errors)
#
