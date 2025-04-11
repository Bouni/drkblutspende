import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    CONF_COUNTY_ID,
    CONF_LOOKAHEAD,
    CONF_RADIUS,
    CONF_TIMEFORMAT,
    CONF_ZIPCODE,
    CONF_ZIPFILTER,
    COUNTIES,
    DEFAULT_TIMEFORMAT,
    DOMAIN,
    RADIUS_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)


class DRKBlutspendeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DRK Blutspende."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> config_entries.FlowResult:
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
                vol.Optional(CONF_ZIPFILTER, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
