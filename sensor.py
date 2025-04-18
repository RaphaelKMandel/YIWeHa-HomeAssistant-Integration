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

    sensors = [
        NextCandleLightingSensor(coordinator),
        NextHavdalahSensor(coordinator),
        LastCandleLightingSensor(coordinator),
        LastHavdalahSensor(coordinator),
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
        future_times = [event for event in candle_lighting_times if event.datetime > now]
        
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
        if not self._value:
            self.update()

        return self.past_event

    def update(self):
        if not self.coordinator.data:
            self.next_event = None
            self.past_event = None

        candle_lighting_times = self.coordinator.data[0]  # First element of tuple
        if not candle_lighting_times:
            self.next_event = None
            self.past_event = None

        now = datetime.now()
        past_times = [event for event in candle_lighting_times if event.datetime < now]
        future_times = [event for event in candle_lighting_times if event.datetime > now]

        if not past_times:
            self.past_event = None

        if not future_times:
            self.next_event = None

        self.past_event = max(past_times).datetime
        self.next_event = min(future_times).datetime

    def schedule_next_update(self):
        self._unsub_time_listener = async_track_point_in_time(
            self.hass,
            self.update,
            self.next_event,
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
        if not self._value:
            self.update()

        return self.past_event

    def update(self):
        if not self.coordinator.data:
            self.next_event = None
            self.past_event = None

        havdalah_times = self.coordinator.data[1]  # First element of tuple
        if not havdalah_times:
            self.next_event = None
            self.past_event = None

        now = datetime.now()
        past_times = [event for event in havdalah_times if event.datetime < now]
        future_times = [event for event in havdalah_times if event.datetime > now]

        if not past_times:
            self.past_event = None

        if not future_times:
            self.next_event = None

        self.past_event = max(past_times).datetime
        self.next_event = min(future_times).datetime

    def schedule_next_update(self):
        self._unsub_time_listener = async_track_point_in_time(
            self.hass,
            self.update,
            self.next_event,
        )

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

class IssurMelachaSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for Issur Melacha status."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Issur Melacha"
        self._attr_unique_id = f"{DOMAIN}_issur_melacha"
        self._attr_device_class = "running"
        self._state = False
        self._last_event_type = None  # "candle_lighting" or "havdalah"
        self._next_event_time = None
        self._unsub_time_listener = None

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._schedule_next_update()

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        if self._unsub_time_listener:
            self._unsub_time_listener()
        await super().async_will_remove_from_hass()

    def _schedule_next_update(self) -> None:
        """Schedule the next update for when the next event occurs."""
        if self._unsub_time_listener:
            self._unsub_time_listener()
            self._unsub_time_listener = None

        if not self.coordinator.data:
            return

        now = datetime.now()
        candle_lightings = self.coordinator.data[0]
        havdalahs = self.coordinator.data[1]

        # Find next candle lighting
        next_candle_lighting = None
        for event in sorted(candle_lightings, key=lambda x: x.datetime):
            if event.datetime > now:
                next_candle_lighting = event.datetime
                break

        # Find next havdalah
        next_havdalah = None
        for event in sorted(havdalahs, key=lambda x: x.datetime):
            if event.datetime > now:
                next_havdalah = event.datetime
                break

        # Determine which event is next
        if next_candle_lighting and next_havdalah:
            self._next_event_time = min(next_candle_lighting, next_havdalah)
        elif next_candle_lighting:
            self._next_event_time = next_candle_lighting
        elif next_havdalah:
            self._next_event_time = next_havdalah
        else:
            self._next_event_time = None

        if self._next_event_time:
            self._unsub_time_listener = async_track_point_in_time(
                self.hass,
                self._handle_time_reached,
                self._next_event_time,
            )
            _LOGGER.debug(
                "Scheduled next update at %s",
                self._next_event_time,
            )

    async def _handle_time_reached(self, now: datetime) -> None:
        """Handle when the next event time is reached."""
        _LOGGER.debug("Event time reached at %s", now)
        
        # Determine which event just occurred
        if not self.coordinator.data:
            return

        now = datetime.now()
        candle_lightings = self.coordinator.data[0]
        havdalahs = self.coordinator.data[1]

        # Find the most recent event
        last_candle_lighting = None
        for event in sorted(candle_lightings, key=lambda x: x.datetime):
            if event.datetime <= now:
                last_candle_lighting = event.datetime
            else:
                break

        last_havdalah = None
        for event in sorted(havdalahs, key=lambda x: x.datetime):
            if event.datetime <= now:
                last_havdalah = event.datetime
            else:
                break

        # Determine which event was most recent
        if last_candle_lighting and last_havdalah:
            if last_candle_lighting > last_havdalah:
                self._last_event_type = "candle_lighting"
                self._state = True
            else:
                self._last_event_type = "havdalah"
                self._state = False
        elif last_candle_lighting:
            self._last_event_type = "candle_lighting"
            self._state = True
        elif last_havdalah:
            self._last_event_type = "havdalah"
            self._state = False
        else:
            self._last_event_type = None
            self._state = False

        _LOGGER.debug(
            "Updated state - Last event: %s, State: %s",
            self._last_event_type,
            self._state,
        )

        # Schedule the next update
        self._schedule_next_update()
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("IssurMelachaSensor received coordinator update")
        self._schedule_next_update()

    @property
    def is_on(self) -> bool:
        """Return True if currently in Issur Melacha period."""
        return self._state

