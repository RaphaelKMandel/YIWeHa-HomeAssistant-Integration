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
    _LOGGER.debug("Setting up sensors with coordinator data: %s", coordinator.data)

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
        _LOGGER.debug("Initialized NextCandleLightingSensor")

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("NextCandleLightingSensor received coordinator update")
        if not self.coordinator.data:
            _LOGGER.debug("No data available from coordinator")
            self._next_time = None
            return
            
        data = self.coordinator.data
        now = datetime.now()
        _LOGGER.debug("Current time: %s", now)
        
        # Find future candle lighting times
        future_times = [event for event in data["candle_lightings"] if event.datetime > now]
        _LOGGER.debug("Found %d future candle lighting times", len(future_times))
        future_times.sort()
        
        if not future_times:
            _LOGGER.debug("No future candle lighting times found")
            self._next_time = None
            return
            
        # Find the event with the minimum datetime
        self._next_time = future_times[0].datetime
        _LOGGER.debug("Next candle lighting time set to: %s", self._next_time)
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
        _LOGGER.debug("Initialized NextHavdalahSensor")

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("NextHavdalahSensor received coordinator update")
        if not self.coordinator.data:
            _LOGGER.debug("No data available from coordinator")
            self._next_time = None
            return
            
        data = self.coordinator.data
        now = datetime.now()
        _LOGGER.debug("Current time: %s", now)
        
        # Find future havdalah times
        future_times = [event for event in data["havdalahs"] if event.datetime > now]
        _LOGGER.debug("Found %d future havdalah times", len(future_times))
        future_times.sort()
        
        if not future_times:
            _LOGGER.debug("No future havdalah times found")
            self._next_time = None
            return
            
        # Find the event with the minimum datetime
        self._next_time = future_times[0].datetime
        _LOGGER.debug("Next havdalah time set to: %s", self._next_time)
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
        _LOGGER.debug("Initialized IssurMelachaSensor")

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("IssurMelachaSensor received coordinator update")
        if not self.coordinator.data:
            _LOGGER.debug("No data available from coordinator")
            self._state = False
            return
            
        data = self.coordinator.data
        now = datetime.now()
        _LOGGER.debug("Current time: %s", now)
        
        # Get all past events
        events = data["candle_lightings"] + data["havdalahs"]
        _LOGGER.debug("Total events found: %d", len(events))
        past_events = [event for event in events if event.datetime < now]
        _LOGGER.debug("Past events found: %d", len(past_events))
        past_events.sort()

        if not past_events:
            _LOGGER.debug("No past events found")
            self._state = False
            return
            
        # Find the most recent past event
        last_event = past_events[-1]
        _LOGGER.debug("Last event time: %s", last_event.datetime)
        self._state = any(event.datetime == last_event.datetime for event in data["candle_lightings"])
        _LOGGER.debug("Issur Melacha state set to: %s", self._state)
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if currently in Issur Melacha period."""
        return self._state

