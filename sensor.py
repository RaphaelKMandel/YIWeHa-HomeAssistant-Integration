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

from .const import DOMAIN

SENSORS = {}
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the YIWH Calendar sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    SENSORS["next_candle"] = NextCandleLightingSensor(coordinator)
    SENSORS["next_havdalah"] = NextHavdalahSensor(coordinator)
    SENSORS["last_candle"] = LastCandleLightingSensor(coordinator)
    SENSORS["last_havdalah"] = LastHavdalahSensor(coordinator)
    SENSORS["issur_melacha"] = IssurMelachaSensor(last_candle_lighting_sensor=SENSORS["last_candle"],
                                                  last_havdalah_sensor=SENSORS["last_havdalah"])
    SENSORS["today"] = TodaySensor(coordinator)
    async_add_entities(list(SENSORS.values()))


class TodaySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Today"
        self._attr_icon = "mdi:calendar"
        self._attr_unique_id = f"{DOMAIN}_today"
        self.events = None

    @property
    def native_value(self):
        """Return the next candle lighting time."""
        if not self.coordinator.data:
            return None

        events = self.coordinator.data["today"]
        if not events:
            return None

        self.events = events

        # return ";".join([repr(event) for event in events])
        return True

    @property
    def extra_state_attributes(self):
        if self.events:
            return {
                "events": [(event.datetime.strptime("%H:%M %p"), event.title) for event in self.events]
            }


class NextCandleLightingSensor(CoordinatorEntity, SensorEntity):
    """Sensor for next candle lighting time."""

    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Next Candle Lighting"
        self._attr_icon = "mdi:candle"
        self._attr_unique_id = f"{DOMAIN}_next_candle_lighting"

    @property
    def native_value(self):
        """Return the next candle lighting time."""
        if not self.coordinator.data:
            return None

        candle_lighting_times = self.coordinator.data["candle_lighting"]  # First element of tuple
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
        self._attr_icon = "mdi:campfire"
        self._attr_unique_id = f"{DOMAIN}_next_havdalah"

    @property
    def native_value(self):
        """Return the next havdalah time."""
        if not self.coordinator.data:
            return None

        havdalah_times = self.coordinator.data["havdalah"]  # Second element of tuple
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
        self._attr_icon = "mdi:candle"
        self._attr_unique_id = f"{DOMAIN}_last_candle_lighting"
        self._attr_entity_registry_enabled_default = False
        self.next_event = None
        self.past_event = None

    @property
    def native_value(self):
        if not self.past_event or not self.next_event:
            self.update_events()

        if datetime.now() >= self.next_event:
            self.update_events()

        return self.past_event

    @callback
    def update_events(self, hass_time=None):
        if not self.coordinator.data:
            self.next_event = None
            self.past_event = None

        candle_lighting_times = self.coordinator.data["candle_lighting"]  # First element of tuple
        if not candle_lighting_times:
            self.next_event = None
            self.past_event = None

        now = datetime.now()
        _LOGGER.info(f"Last Candle Lighting updating at {hass_time} and {now}")
        past_times = [event for event in candle_lighting_times if event.datetime <= now]
        future_times = [event for event in candle_lighting_times if event.datetime > now]

        if not past_times:
            self.past_event = None

        if not future_times:
            self.next_event = None

        self.past_event = max(past_times).datetime
        self.next_event = min(future_times).datetime
        self.async_write_ha_state()
        SENSORS["issur_melacha"].async_write_ha_state()
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
        self._attr_icon = "mdi:campfire"
        self._attr_unique_id = f"{DOMAIN}_last_havdalah"
        self._attr_entity_registry_enabled_default = False
        self.next_event = None
        self.past_event = None

    @property
    def native_value(self):
        if not self.past_event or not self.next_event:
            self.update_events()

        if datetime.now() >= self.next_event:
            self.update_events()

        return self.past_event

    @callback
    def update_events(self, hass_time=None):
        if not self.coordinator.data:
            self.next_event = None
            self.past_event = None

        havdalah_times = self.coordinator.data["havdalah"]  # First element of tuple
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
        self.async_write_ha_state()
        SENSORS["issur_melacha"].async_write_ha_state()
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
        self._attr_icon = "mdi:power-plug-off"
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
