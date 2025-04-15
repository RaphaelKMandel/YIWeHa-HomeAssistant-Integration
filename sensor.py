"""Sensor platform for YIWH calendar integration."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the YIWH Calendar sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        NextCandleLightingSensor(coordinator),
        NextHavdalahSensor(coordinator),
        IssurMelachaSensor(coordinator),
    ]
    
    async_add_entities(sensors)

class NextCandleLightingSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next candle lighting time."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Next Candle Lighting"
        self._attr_unique_id = f"{DOMAIN}_next_candle_lighting"
        self._next_time = None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            self._next_time = None
            return
            
        candle_lighting_times = self.coordinator.data[0]  # First element of tuple
        if not candle_lighting_times:
            self._next_time = None
            return
            
        # Get midnight of current day
        now = datetime.now()
        midnight = datetime(now.year, now.month, now.day)
        future_times = [t for t in candle_lighting_times if t.datetime > midnight]
        
        if not future_times:
            self._next_time = None
            return
            
        self._next_time = min(future_times).datetime
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the next candle lighting time."""
        return self._next_time

class NextHavdalahSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next havdalah time."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Next Havdalah"
        self._attr_unique_id = f"{DOMAIN}_next_havdalah"
        self._next_time = None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            self._next_time = None
            return
            
        havdalah_times = self.coordinator.data[1]  # Second element of tuple
        if not havdalah_times:
            self._next_time = None
            return
            
        # Get midnight of current day
        now = datetime.now()
        midnight = datetime(now.year, now.month, now.day)
        future_times = [t for t in havdalah_times if t.datetime > midnight]
        
        if not future_times:
            self._next_time = None
            return
            
        self._next_time = min(future_times).datetime
        self.async_write_ha_state()

    @property
    def native_value(self):
        """Return the next havdalah time."""
        return self._next_time

class IssurMelachaSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Issur Melacha status."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Issur Melacha"
        self._attr_unique_id = f"{DOMAIN}_issur_melacha"
        self._attr_device_class = "running"
        self._state = False

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            self._state = False
            return

        candle_lighting_times = self.coordinator.data[0]
        havdalah_times = self.coordinator.data[1]
        
        if not candle_lighting_times or not havdalah_times:
            self._state = False
            return

        now = datetime.now()
        
        # Get all events
        past_candle_lighting = [t for t in candle_lighting_times if t.datetime < now]
        past_havdalah = [t for t in havdalah_times if t.datetime < now]
        future_candle_lighting = [t for t in candle_lighting_times if t.datetime > now]
        future_havdalah = [t for t in havdalah_times if t.datetime > now]
        
        # Find most recent past event
        most_recent_past = None
        if past_candle_lighting:
            most_recent_past = ("candle_lighting", max(past_candle_lighting, key=lambda x: x.datetime))
        if past_havdalah:
            havdalah = max(past_havdalah, key=lambda x: x.datetime)
            if not most_recent_past or havdalah.datetime > most_recent_past[1].datetime:
                most_recent_past = ("havdalah", havdalah)
        
        # Find next upcoming event
        next_upcoming = None
        if future_candle_lighting:
            next_upcoming = ("candle_lighting", min(future_candle_lighting, key=lambda x: x.datetime))
        if future_havdalah:
            havdalah = min(future_havdalah, key=lambda x: x.datetime)
            if not next_upcoming or havdalah.datetime < next_upcoming[1].datetime:
                next_upcoming = ("havdalah", havdalah)
        
        # Determine state based on most recent past event
        if most_recent_past:
            self._state = most_recent_past[0] == "candle_lighting"
        else:
            # If no past events, check next upcoming event
            self._state = next_upcoming and next_upcoming[0] == "havdalah"
            
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if currently in Issur Melacha period."""
        return self._state

