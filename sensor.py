"""Sensor platform for YIWH calendar integration."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.sensor import SensorEntity
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

