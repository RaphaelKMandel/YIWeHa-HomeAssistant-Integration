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
        self._attr_device_class = "timestamp"
        self._next_time = None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            self._next_time = None
            return
            
        data = self.coordinator.data
        now = datetime.now()
        
        # Find future candle lighting times
        future_times = [event for event in data["candle_lightings"] if event.datetime > now]
        future_times.sort()
        
        if not future_times:
            self._next_time = None
            return
            
        # Find the event with the minimum datetime
        self._next_time = future_times[0].datetime
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
        self._attr_device_class = "timestamp"
        self._next_time = None

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            self._next_time = None
            return
            
        data = self.coordinator.data
        now = datetime.now()
        
        # Find future havdalah times
        future_times = [event for event in data["havdalahs"] if event.datetime > now]
        future_times.sort()
        
        if not future_times:
            self._next_time = None
            return
            
        # Find the event with the minimum datetime
        self._next_time = future_times[0].datetime
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
            
        data = self.coordinator.data
        now = datetime.now()
        
        # Get all past events
        events = data["candle_lightings"] + data["havdalahs"]
        past_events = [event for event in events if event.datetime < now]
        past_events.sort()

        if not past_events:
            self._state = False
            return
            
        # Find the most recent past event
        last_event = past_events[-1]
        self._state = any(event.datetime == last_event.datetime for event in data["candle_lightings"])
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if currently in Issur Melacha period."""
        return self._state

