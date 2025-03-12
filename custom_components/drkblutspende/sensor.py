"""German red cross blood donation sensor."""

import logging
import re
from datetime import datetime as dt
from datetime import timedelta as td

import feedparser
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import ENTITY_ID_FORMAT, PLATFORM_SCHEMA
from homeassistant.const import CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.util import Throttle

from .const import (
    CONF_COUNTY_ID,
    CONF_LOOKAHEAD,
    CONF_RADIUS,
    CONF_TIMEFORMAT,
    CONF_ZIP_REGEX,
    CONF_ZIPCODE,
    CONF_ZIPFILTER,
    COUNTY_OPTIONS,
    ICON,
    RADIUS_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

DOMAIN = "drkblutspende"

DEFAULT_TIMEFORMAT = "%A, %d.%m.%Y"

MIN_TIME_BETWEEN_UPDATES = td(seconds=3600)  # minimum one hour between requests

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ZIPCODE): vol.Match(CONF_ZIP_REGEX),
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Optional(CONF_RADIUS): vol.All(vol.Coerce(int), vol.In(RADIUS_OPTIONS)),
        vol.Optional(CONF_COUNTY_ID): vol.All(cv.string, vol.In(COUNTY_OPTIONS)),
        vol.Optional(CONF_LOOKAHEAD): vol.Coerce(int),
        vol.Optional(CONF_TIMEFORMAT, default=DEFAULT_TIMEFORMAT): cv.string,
        vol.Optional(CONF_ZIPFILTER): vol.All(list, [vol.Match(CONF_ZIP_REGEX)]),
    }
)


async def async_setup_platform(hass, config, async_add_devices):
    """Set up date sensor."""
    unique_id = config.get(CONF_UNIQUE_ID, None)
    zipcode = config.get(CONF_ZIPCODE, "")
    radius = config.get(CONF_RADIUS, "")
    countyid = config.get(CONF_COUNTY_ID, "")
    lookahead = config.get(CONF_LOOKAHEAD, "")
    timeformat = config.get(CONF_TIMEFORMAT, "")
    zipfilter = config.get(CONF_ZIPFILTER, "")

    devices = []
    devices.append(
        DRKBlutspendeSensor(
            hass,
            unique_id,
            zipcode,
            radius,
            countyid,
            lookahead,
            timeformat,
            zipfilter,
        )
    )
    async_add_devices(devices)


class DRKBlutspendeSensor(Entity):
    """Representation of a DRKBlutspende Sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
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
        self._unique_id = unique_id
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
    def unique_id(self):
        """Return the unique_id of the sensor."""
        return self._unique_id

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

    def build_url(self):
        """Build query URL depending on configuration"""
        _LOGGER.debug(f"Zipcode is {self._zipcode}")
        url = f"https://www.spenderservice.net/termine.rss?term={self._zipcode}"
        if self._radius:
            _LOGGER.debug(f"Radius is {self._radius}")
            url += f"&radius={self._radius}"
        if self._countyid:
            _LOGGER.debug(f"County ID is {self._countyid}")
            url += f"&county_id={self._countyid}"
        if self._lookahead:
            _LOGGER.debug(f"Lookahead is {self._lookahead}")
            date_to = (dt.now() + td(days=self._lookahead)).strftime("%d.%m.%Y")
            url += f"&date_to={date_to}"
        return url

    def get_data(self):
        url = self.build_url()
        try:
            feed = feedparser.parse(url)
            _LOGGER.debug(f"{url} gave status code {feed.status}")
        except Exception as e:
            _LOGGER.error(f"Couldn't get data from spenderservice.net: {e}")
            return

        self._state = "unknown"
        for entry in feed["entries"]:
            t = re.search(
                r"(?P<zip>\d{5})\s(?P<city>.*)\sam\s(?P<date>[\d\.]+),\s(?P<start>[\d\:]+)[^\d]+(?P<end>[\d\:]+)",
                entry["title"],
            )
            if not t:
                continue
            data = t.groupdict()
            d = re.search(
                r"-\s(?P<address>.*)\s-\s(?P<location>[^<]+)", entry["description"]
            )
            if not d:
                continue
            description = d.groupdict()
            if not self._zipfilter:
                self._state = dt.strptime(
                    f"{data['date']} {data['start']}", "%d.%m.%Y %H:%M"
                )
                self._state_attributes = data
                self._state_attributes["address"] = description["address"]
                self._state_attributes["location"] = description["location"]
                self._state_attributes["link"] = entry["link"]
                break
            else:
                _LOGGER.debug(
                    f"search for {data['zip']} in zip filter {self._zipfilter}"
                )
                if data["zip"] in self._zipfilter:
                    _LOGGER.debug(f"{data['zip']} matches zip filter {self._zipfilter}")
                    self._state = dt.strptime(
                        f"{data['date']} {data['start']}", "%d.%m.%Y %H:%M"
                    )
                    self._state_attributes = data
                    self._state_attributes["address"] = description["address"]
                    self._state_attributes["location"] = description["location"]
                    self._state_attributes["link"] = entry["link"]
                    break

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Fetch new state data for the sensor from the ics file url."""
        self.get_data()
