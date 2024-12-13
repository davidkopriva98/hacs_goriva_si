"""Goriva.si sensor platform."""
from datetime import timedelta
import json
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.components.sensor import PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity, generate_entity_id
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

from .const import (
    ATTR_ADDRESS,
    ATTR_ATTRIBUTION,
    ATTR_FUEL_TYPE,
    CONF_PETROL_STATION_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Time between updating data from goriva.si
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=110)

SENSOR_PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_PETROL_STATION_NAME): cv.string,
    }
)


async def get_petrol_station_data(name_filter):
    """Get updated petrol station values."""
    url = (
        "https://goriva.si/api/v1/search/?position=Ljubljana&name="
        + str(name_filter).replace(" ", "+")
    )
    async with aiohttp.ClientSession() as session, session.get(url) as response:
        response_text = await response.text()
        return json.loads(response_text)


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    session = async_get_clientsession(hass)

    goriva_si_data = GorivaSiData(config[CONF_PETROL_STATION_NAME])
    await goriva_si_data.async_update()

    fuel_types = []
    for fuel_type, fuel_price in goriva_si_data.station_prices.items():
        if fuel_price is not None:
            fuel_types.append(fuel_type)

    if len(fuel_types) == 0:
        raise PlatformNotReady

    sensors = [GorivaSiSensor(config[CONF_PETROL_STATION_NAME], fuel_type, hass, goriva_si_data) for fuel_type in fuel_types]
    async_add_entities(sensors, update_before_add=False)


async def async_setup_platform(
    hass: core.HomeAssistant,
    config: ConfigType,
    async_add_entities,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    session = async_get_clientsession(hass)

    goriva_si_data = GorivaSiData(config[CONF_PETROL_STATION_NAME])
    await goriva_si_data.async_update()

    fuel_types = []
    for fuel_type, fuel_price in goriva_si_data.station_prices.items():
        if fuel_price is not None:
            fuel_types.append(fuel_type)

    if len(fuel_types) == 0:
        raise PlatformNotReady

    sensors = [GorivaSiSensor(config[CONF_PETROL_STATION_NAME], fuel_type, hass, goriva_si_data) for fuel_type in fuel_types]
    async_add_entities(sensors, update_before_add=False)


class GorivaSiSensor(Entity):
    """Representation of a Goriva.si sensor."""

    def __init__(self, name_filter, fuel_type, hass: core.HomeAssistant, data):
        super().__init__()
        self._name = f"{data.station_data["name"].title()} - {fuel_type}"
        self._fuel_type = fuel_type
        self.attrs = {ATTR_ATTRIBUTION: "https://goriva.si", ATTR_FUEL_TYPE: fuel_type, ATTR_ADDRESS: data.station_data["address"].capitalize()}
        self._state = data.station_prices[fuel_type]
        self._attr_icon = "mdi:gas-station"
        self.unit_of_measurement = "€"
        self._goriva_si_data = data

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"{self._name}_{self._fuel_type}"

    @property
    def state(self) -> str | None:
        """Returns entity state."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Returns entity extra attributes."""
        return self.attrs

    async def async_update(self):
        """Update entity state."""
        try:
            # station_data = await get_petrol_station_data(self._name_filter)
            await self._goriva_si_data.async_update()
            self._state = self._goriva_si_data.station_prices[self._fuel_type]

        except:
            self._state = None
            _LOGGER.exception("Error retrieving data from goriva.si")


class GorivaSiData:
    """Get the latest fuel prices and update the states."""

    def __init__(self, name_filter: str):
        """Initialize the data object."""
        self.name_filter = name_filter
        self.available = True
        self.station_data = None
        self.station_prices = None

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self):
        """Get the latest data from the goriva.si."""
        try:
            petrol_stations = await get_petrol_station_data(self.name_filter)

            if petrol_stations is None or petrol_stations["results"] is None or len(petrol_stations["results"]) == 0:
                raise Exception

            self.station_data = petrol_stations["results"][0]
            self.station_prices = self.station_data["prices"]
            self.available = True
        except:
            _LOGGER.error("Unable to fetch data from goriva.si for filter " + self.name_filter)
            self.available = False
