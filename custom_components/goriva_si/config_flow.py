"""Goriva.si custom component config flow."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv

from .const import CONF_PETROL_STATION_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


PETROL_STATION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PETROL_STATION_NAME): cv.string,
    }
)

class GorivaSiCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Goriva.si Custom config flow."""

    data: dict[str, Any] | None

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Invoke when a user initiates a flow via the user interface."""

        if user_input is not None:
            self.data = user_input
            return self.async_create_entry(title=self.data[CONF_PETROL_STATION_NAME].title(), data=self.data)

        return self.async_show_form(
            step_id="user", data_schema=PETROL_STATION_SCHEMA
        )
