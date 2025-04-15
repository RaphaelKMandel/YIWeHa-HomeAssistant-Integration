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

    @property
    def native_value(self):
        """Return the next candle lighting time."""
        if not self.coordinator.data:
            return None
            
        candle_lighting_times = self.coordinator.data[0]  # First element of tuple
        if not candle_lighting_times:
            return None
            
        now = datetime.now()
        future_times = [t for t in candle_lighting_times if t.datetime > now]
        
        if not future_times:
            return None
            
        return min(future_times).datetime

class NextHavdalahSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next havdalah time."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Next Havdalah"
        self._attr_unique_id = f"{DOMAIN}_next_havdalah"

    @property
    def native_value(self):
        """Return the next havdalah time."""
        if not self.coordinator.data:
            return None
            
        havdalah_times = self.coordinator.data[1]  # Second element of tuple
        if not havdalah_times:
            return None
            
        now = datetime.now()
        future_times = [t for t in havdalah_times if t.datetime > now]
        
        if not future_times:
            return None
            
        return min(future_times).datetime

class IssurMelachaSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Issur Melacha status."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Issur Melacha"
        self._attr_unique_id = f"{DOMAIN}_issur_melacha"
        self._attr_device_class = "running"
        self._state = False
        self._next_candle_lighting = None
        self._next_havdalah = None

    def _update_next_times(self) -> None:
        """Update the next candle lighting and havdalah times."""
        now = datetime.now()
        
        # Get next candle lighting
        candle_lighting_times = self.coordinator.data[0]
        future_candle_lighting = [t for t in candle_lighting_times if t.datetime > now]
        self._next_candle_lighting = min(future_candle_lighting).datetime if future_candle_lighting else None

        # Get next havdalah
        havdalah_times = self.coordinator.data[1]
        future_havdalah = [t for t in havdalah_times if t.datetime > now]
        self._next_havdalah = min(future_havdalah).datetime if future_havdalah else None

    @property
    def is_on(self) -> bool:
        """Return True if currently in Issur Melacha period."""
        if not self.coordinator.data:
            return False

        now = datetime.now()

        # If we don't have next times stored, or we're not in Issur Melacha,
        # update the next times
        if not self._state or (not self._next_candle_lighting and not self._next_havdalah):
            self._update_next_times()

        # If we're waiting for candle lighting
        if not self._state and self._next_candle_lighting:
            if now >= self._next_candle_lighting:
                self._state = True
                # Clear the next candle lighting since we've passed it
                self._next_candle_lighting = None

        # If we're in Issur Melacha and waiting for havdalah
        elif self._state and self._next_havdalah:
            if now >= self._next_havdalah:
                self._state = False
                # Update times for the next cycle
                self._update_next_times()

        return self._state

