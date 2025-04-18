"""The Young Israel West Hartford Calendar integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED

from .scraper import YIWHScraper

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.SENSOR]

def get_next_midnight():
    """Get timedelta until next midnight."""
    now = dt_util.now()
    next_midnight = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return next_midnight

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = MidnightCoordinator(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class MidnightCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant):
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.scraper = YIWHScraper()
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, self._handle_startup)

    @callback
    async def _handle_startup(self, event):
        # Run update once at startup
        await self._async_update_data()

        # Schedule the first midnight update
        self._schedule_next_midnight()

    def _schedule_next_midnight(self):
        """Schedule the next update at midnight."""
        next_midnight = get_next_midnight()
        async_track_point_in_time(
            self.hass,
            self._handle_midnight,
            next_midnight,
        )

    async def _handle_midnight(self, _):
        await self._async_update_data()
        self._schedule_next_midnight()

    async def _async_update_data(self):
        _LOGGER.info("YIWeHa Scraper is updating...")
        data = await self.hass.async_add_executor_job(self.scraper.scrape_calendar)
        self.async_set_updated_data(data)