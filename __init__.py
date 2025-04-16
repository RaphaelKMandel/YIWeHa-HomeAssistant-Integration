"""The Young Israel West Hartford Calendar integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .scraper import YIWHScraper

_LOGGER = logging.getLogger(__name__)
DOMAIN = "yiweha"
PLATFORMS: list[Platform] = [Platform.SENSOR]

def get_next_midnight() -> timedelta:
    """Get timedelta until next midnight."""
    now = dt_util.now()
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return next_midnight - now

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Young Israel West Hartford Calendar from a config entry."""
    scraper = YIWHScraper()

    async def async_update_data():
        """Fetch data from API."""
        _LOGGER.debug("Fetching calendar data")
        candle_lightings, havdalahs = await hass.async_add_executor_job(scraper.scrape_calendar)
        if candle_lightings is None or havdalahs is None:
            _LOGGER.error("Failed to fetch calendar data")
            return None
            
        _LOGGER.debug("Found %d candle lighting times and %d havdalah times", 
                     len(candle_lightings), len(havdalahs))
        return {
            "candle_lightings": candle_lightings,
            "havdalahs": havdalahs
        }

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=get_next_midnight(),
    )

    # Force an immediate update before setting up sensors
    await coordinator.async_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

