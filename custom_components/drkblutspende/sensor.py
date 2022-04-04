""" German red cross blood donation sensor."""
import asyncio
import logging
import re
import xml.etree.ElementTree as et
from datetime import datetime as dt
from datetime import timedelta as td

import feedparser
import requests

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from .const import (
    CONF_COUNTY_ID,
    CONF_LOOKAHEAD,
    CONF_RADIUS,
    CONF_TIMEFORMAT,
    CONF_ZIPCODE,
    CONF_ZIPFILTER,
    CONF_ZIP_REGEX,
    COUNTY_OPTIONS,
    ICON,
    RADIUS_OPTIONS,
)
from homeassistant.components.sensor import ENTITY_ID_FORMAT, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

DOMAIN = "drkblutspende"

DEFAULT_TIMEFORMAT = "%A, %d.%m.%Y"
DEFAULT_LOOKAHEAD = 14


MIN_TIME_BETWEEN_UPDATES = td(seconds=3600)  # minimum one hour between requests

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ZIPCODE): vol.Match(CONF_ZIP_REGEX),
        vol.Optional(CONF_RADIUS): vol.All(vol.Coerce(int), vol.In(RADIUS_OPTIONS)),
        vol.Optional(CONF_COUNTY_ID): vol.All(cv.string, vol.In(COUNTY_OPTIONS)),
        vol.Optional(CONF_LOOKAHEAD, default=DEFAULT_LOOKAHEAD): vol.Coerce(int),
        vol.Optional(CONF_TIMEFORMAT, default=DEFAULT_TIMEFORMAT): cv.string,
        vol.Optional(CONF_ZIPFILTER): vol.All(list, [vol.Match(CONF_ZIP_REGEX)]),
    }
)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up date sensor."""
    zipcode = config.get(CONF_ZIPCODE,"")
    radius = config.get(CONF_RADIUS,"")
    countyid = config.get(CONF_COUNTY_ID,"")
    lookahead = config.get(CONF_LOOKAHEAD,"")
    timeformat = config.get(CONF_TIMEFORMAT,"")
    zipfilter = config.get(CONF_ZIPFILTER,"")

    devices = []
    devices.append(
        DRKBlutspendeSensor(
            hass, zipcode, radius, countyid, lookahead, timeformat, zipfilter,
        )
    )
    async_add_devices(devices)


class DRKBlutspendeSensor(Entity):
    """Representation of a DRKBlutspende Sensor."""

    def __init__(
        self,
        hass: HomeAssistantType,
        zipcode,
        radius,
        countyid,
        lookahead,
        timeformat,
        zipfilter,
    ):
        """Initialize the sensor."""
        self._state_attributes = {}
        self._state = None
        self._name = "blutspende"
        self._zipcode = zipcode
        self._radius = radius
        self._countyid = countyid
        self._lookahead = lookahead
        self._timeformat = timeformat
        self._zipfilter = zipfilter

        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, "blutspende", hass=hass
        )
        _LOGGER.debug("Setup DRKBlutspendeSensor")

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._state_attributes

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    def get_data(self):
        date_to = (dt.now() + td(days=self._lookahead)).strftime("%d.%m.%Y")
        url = "https://www.spenderservice.net/termine.rss"
        try:
            feed = feedparser.parse(
                f"{url}?term={self._zipcode}&radius={self._radius}&county_id={self._countyid}&date_to={date_to}"
            )
            _LOGGER.debug(f"{url}?term={self._zipcode}&radius={self._radius}&county_id={self._countyid}&date_to={date_to} gave status code {feed.status}")
        except Exception as e:
            _LOGGER.error("Couldn't get data from spenderservice.net")
            return

        self._state = "unknown"
        for entry in feed["entries"]:
            t = re.search(
                r"(?P<zip>\d{5})\s(?P<city>.*)\sam\s(?P<date>[\d\.]+),\s(?P<start>[\d\:]+)[^\d]+(?P<end>[\d\:]+)",
                entry["title"],
            )
            data = t.groupdict()
            d = re.search(
                r"-\s(?P<address>.*)\s-\s(?P<location>[^<]+)", entry["description"]
            )
            _LOGGER.debug(data)
            description = d.groupdict()
            if not self._zipfilter:
                self._state = dt.strptime(
                    f"{data['date']} {data['start']}", "%d.%m.%Y %H:%M"
                )
                self._state_attributes = data
                self._state_attributes["address"] = description["address"]
                self._state_attributes["location"] = description["location"]
                break
            else:
                if data["zip"] in self._zipfilter:
                    self._state = dt.strptime(
                        f"{data['date']} {data['start']}", "%d.%m.%Y %H:%M"
                    )
                    self._state_attributes = data
                    self._state_attributes["address"] = description["address"]
                    self._state_attributes["location"] = description["location"]
                    break

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Fetch new state data for the sensor from the ics file url."""
        self.get_data()
