import hashlib
import logging
import re
from datetime import datetime as dt
from datetime import timedelta as td
from typing import Any, Dict, Optional

import feedparser
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.util import Throttle

from .const import ICON, MIN_TIME_BETWEEN_UPDATES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up DRK Blutspende sensor based on a config entry."""
    config = entry.data
    _LOGGER.debug("Sensor config: %s", config)
    async_add_entities([DRKBlutspendeSensor(hass, config)], True)


class DRKBlutspendeSensor(SensorEntity):
    """Representation of a DRK Blutspende Sensor."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]) -> None:
        """Initialize the sensor."""
        self._state_attributes: Dict[str, Any] = {}
        self._state: Optional[str] = None
        self._name: str = "blutspende"
        self._zipcode: str = config.get("zipcode", "")
        self._radius: str = config.get("radius", "")
        self._countyid: str = config.get("countyid", "")
        self._lookahead: str = config.get("lookahead", "")
        self._timeformat: str = config.get("timeformat", "")
        self._zipfilter: str = config.get("zipfilter", "")
        self.entity_id = async_generate_entity_id("sensor.{}", self._name, hass=hass)
        self._attr_unique_id: str = self._generate_unique_id(config)
        _LOGGER.debug("Setup DRKBlutspendeSensor")

    def _generate_unique_id(self, config):
        j = str(config)
        return hashlib.sha256(j.encode()).hexdigest()[:8]

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def icon(self) -> str:
        return ICON

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self._state_attributes

    def build_url(self) -> str:
        """Build query URL depending on configuration"""
        date_to = ""
        if self._lookahead:
            date_to = (dt.now() + td(days=int(self._lookahead))).strftime("%d.%m.%Y")
        url = f"https://www.spenderservice.net/termine.rss?term={self._zipcode}&radius={self._radius}&county_id={self._countyid}&date_from=&date_to={date_to}&last_donation=&button="
        return url

    @staticmethod
    def get_title_data(title: str) -> dict | None:
        """Get zipcode, city, date, start and end from the title."""
        match = re.search(
            r"(?P<zipcode>\d{5})\s(?P<city>.*)\sam\s(?P<date>[\d\.]+),\s(?P<start>[\d\:]+)[^\d]+(?P<end>[\d\:]+)",
            title,
        )
        if match:
            return match.groupdict()
        return None

    @staticmethod
    def get_description_data(description: str) -> dict | None:
        """Get address and location from the description."""
        match = re.search(r"-\s(?P<address>.*)\s-\s(?P<location>[^<]+)", description)
        if match:
            return match.groupdict()
        return None

    def sanitize_data(self, feed: list[dict]) -> list[dict]:
        """Parse data from RSS entries."""
        data = []
        for entry in feed:
            title = self.get_title_data(entry["title"])
            if title:
                description = self.get_description_data(entry["description"])
                if description:
                    date = dt.strptime(
                        f"{title['date']} {title['start']}", "%d.%m.%Y %H:%M"
                    )
                    title["date"] = date.strftime(self._timeformat)
                    data.append(
                        {
                            "date": date,
                            "attributes": {
                                **title,
                                **description,
                                "link": entry["link"],
                            },
                        }
                    )
                else:
                    _LOGGER.info("No match in description found")
            else:
                _LOGGER.info("No match in title found")
        return sorted(data, key=lambda x: x["date"])

    def filter_by_zipcode(self, data: list[dict]) -> list[dict]:
        """Filter the raw list of entries for configured zipcodes."""
        zipcodes = [zip.strip() for zip in self._zipfilter.split(",")]
        return [entry for entry in data if entry["zipcode"] in zipcodes]

    def update_sensor(self, data: dict):
        """Update state and attributes."""
        self._state = data["date"]
        self._state_attributes = data["attributes"]

    def get_data(self) -> None:
        """Fetch rss data from spenderservice.net"""
        url = self.build_url()
        try:
            feed = feedparser.parse(url)
            _LOGGER.debug(f"{url} gave status code {feed.status}")
        except Exception as e:
            _LOGGER.error(f"Couldn't get data from spenderservice.net: {e}")
            return
        self._state = "unknown"
        data = self.sanitize_data(feed["entries"])
        if self._zipfilter:
            data = self.filter_by_zipcode(data)
            if data:
                self.update_sensor(data[0])
            else:
                _LOGGER.info("No entries match the zipfilter")
        else:
            if data:
                self.update_sensor(data[0])
            else:
                _LOGGER.info("No entries found")

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self) -> None:
        self.get_data()
