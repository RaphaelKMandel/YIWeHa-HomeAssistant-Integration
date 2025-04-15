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

        # Get midnight of current day
        now = datetime.now()
        midnight = datetime(now.year, now.month, now.day)
        
        # Get all future events after midnight
        future_candle_lighting = [t for t in candle_lighting_times if t.datetime > midnight]
        future_havdalah = [t for t in havdalah_times if t.datetime > midnight]
        
        if not future_candle_lighting and not future_havdalah:
            self._state = False
            return
            
        # Find the next event (either candle lighting or havdalah)
        next_candle_lighting = min(future_candle_lighting).datetime if future_candle_lighting else None
        next_havdalah = min(future_havdalah).datetime if future_havdalah else None
        
        # Determine state based on which event comes next
        if next_candle_lighting and next_havdalah:
            # If havdalah comes before candle lighting, we're in Issur Melacha
            self._state = next_havdalah < next_candle_lighting
        else:
            # If we only have one type of event, use that to determine state
            self._state = bool(next_havdalah)  # True if next event is havdalah, False if candle lighting
            
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return True if currently in Issur Melacha period."""
        return self._state

