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
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.core import callback

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the YIWH Calendar sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    next_candle = NextCandleLightingSensor(coordinator)
    next_havdalah = NextHavdalahSensor(coordinator)
    last_candle = LastCandleLightingSensor(coordinator)
    last_havdalah = LastHavdalahSensor(coordinator)
    issur_melacha = IssurMelachaSensor(last_candle_lighting_sensor=last_candle, last_havdalah_sensor=last_havdalah)
    sensors = [ next_candle, next_havdalah, last_candle, last_havdalah, issur_melacha]
    
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
        future_times = [event for event in candle_lighting_times if event.datetime > now]
        
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
        future_times = [event for event in havdalah_times if event.datetime > now]

        if not future_times:
            return None

        return min(future_times).datetime


class LastCandleLightingSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next candle lighting time."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Last Candle Lighting"
        self._attr_unique_id = f"{DOMAIN}_last_candle_lighting"
        self.next_event = None
        self.past_event = None

    @property
    def native_value(self):
        if not self.past_event:
            self.update_events()

        return self.past_event

    def update_events(self):
        if not self.coordinator.data:
            self.next_event = None
            self.past_event = None

        candle_lighting_times = self.coordinator.data[0]  # First element of tuple
        if not candle_lighting_times:
            self.next_event = None
            self.past_event = None

        now = datetime.now()
        past_times = [event for event in candle_lighting_times if event.datetime <= now]
        future_times = [event for event in candle_lighting_times if event.datetime > now]

        if not past_times:
            self.past_event = None

        if not future_times:
            self.next_event = None

        self.past_event = max(past_times).datetime
        self.next_event = min(future_times).datetime
        self.schedule_next_update()

    def schedule_next_update(self):
        self._unsub_time_listener = async_track_point_in_time(
            self.hass,
            self.update_events,
            self.next_event
        )


class LastHavdalahSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next candle lighting time."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Last Havdalah"
        self._attr_unique_id = f"{DOMAIN}_last_havdalah"
        self.next_event = None
        self.past_event = None

    @property
    def native_value(self):
        if not self.past_event:
            self.update_events()

        return self.past_event

    def update_events(self, hass_time=None):
        if not self.coordinator.data:
            self.next_event = None
            self.past_event = None

        havdalah_times = self.coordinator.data[1]  # First element of tuple
        if not havdalah_times:
            self.next_event = None
            self.past_event = None

        now = datetime.now()
        _LOGGER.info(f"Last Havdalah updating at {hass_time} and {now}")
        past_times = [event for event in havdalah_times if event.datetime <= now]
        future_times = [event for event in havdalah_times if event.datetime > now]

        if not past_times:
            self.past_event = None

        if not future_times:
            self.next_event = None

        self.past_event = max(past_times).datetime
        self.next_event = min(future_times).datetime
        self.schedule_next_update()

    def schedule_next_update(self):
        self._unsub_time_listener = async_track_point_in_time(
            self.hass,
            self.update_events,
            self.next_event
        )


class IssurMelachaSensor(BinarySensorEntity):
    """Binary sensor for Issur Melacha status."""

    def __init__(
        self,
        last_candle_lighting_sensor: LastCandleLightingSensor,
        last_havdalah_sensor: LastHavdalahSensor,
    ) -> None:
        self._attr_name = "Issur Melacha"
        self._attr_unique_id = f"{DOMAIN}_issur_melacha"
        self._attr_device_class = "running"
        self._last_candle_lighting_sensor = last_candle_lighting_sensor
        self._last_havdalah_sensor = last_havdalah_sensor

    @property
    def is_on(self) -> bool:
        """Return True if last candle lighting is more recent than last havdalah."""
        last_candle = self._last_candle_lighting_sensor.past_event
        last_havdalah = self._last_havdalah_sensor.past_event

        if not last_candle or not last_havdalah:
            return None

        return last_candle > last_havdalah
