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
        return await hass.async_add_executor_job(scraper.scrape_calendar)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=get_next_midnight(),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

