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
    _LOGGER.info(f"YIWeHa: Set up {SENSORS}")


class TodaySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Today"
        self._attr_icon = "mdi:calendar"
        self._attr_unique_id = f"{DOMAIN}_today"

    @property
    def extra_state_attributes(self):
        """Return the next candle lighting time."""
        if not self.coordinator.data:
            _LOGGER.debug(f"{DOMAIN}: TodaySensor coordinator data is None")
            return None

        today = self.coordinator.data["today"]
        if not today:
            _LOGGER.debug(f"{DOMAIN}: TodaySensor cannot find today in coorindator data")
            return None

        _LOGGER.debug(f"{DOMAIN}: TodaySensor attributes are being updated to {today}")
        return today.to_dict()


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
            _LOGGER.debug(f"{DOMAIN}: NextCandleLightingSensor coordinator data is None")
            return None

        candle_lighting_times = self.coordinator.data["candle_lighting"]
        if not candle_lighting_times:
            _LOGGER.debug(f"{DOMAIN}: NextCandleLightingSensor could not find any times")
            return None

        now = datetime.now()
        future_times = [event for event in candle_lighting_times if event.datetime > now]

        if not future_times:
            _LOGGER.debug(f"{DOMAIN}: NextCandleLightingSensor could not find any future times among {candle_lighting_times}")
            return None

        value = min(future_times).datetime
        _LOGGER.debug(f"{DOMAIN}: NextCandleLightingSensor native value is being updated to {value}")
        return value


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
            _LOGGER.debug(f"{DOMAIN}: NextHavdalahSensor coordinator data is None")
            return None

        havdalah_times = self.coordinator.data["havdalah"]
        if not havdalah_times:
            _LOGGER.debug(f"{DOMAIN}: NextHavdalahSensor could not find any times")
            return None

        now = datetime.now()
        future_times = [event for event in havdalah_times if event.datetime > now]

        if not future_times:
            _LOGGER.debug(f"{DOMAIN}: NextHavdalahSensor could not find any future times among {havdalah_times}")
            return None

        value = min(future_times).datetime
        _LOGGER.debug(f"{DOMAIN}: NextHavdalahSensor native value is being updated to {value}")
        return value


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
        if not self.past_event or not self.next_event or datetime.now() >= self.next_event:
            self.update_events()

        if not self.past_event or not self.next_event:
            _LOGGER.debug(f"{DOMAIN}: LastCandleLightingSensor native value failed to set")
            return

        _LOGGER.debug(f"{DOMAIN}: LastCandleLightingSensor native value is being updated to {self.past_event}")

        return self.past_event

    @callback
    def update_events(self, hass_time=None):
        if not self.coordinator.data:
            _LOGGER.debug(f"{DOMAIN}: LastCandleLightingSensor coordinator data is None")
            self.next_event = None
            self.past_event = None
            return

        candle_lighting_times = self.coordinator.data["candle_lighting"]
        if not candle_lighting_times:
            _LOGGER.debug(f"{DOMAIN}: LastCandleLightingSensor could not find any times")
            self.next_event = None
            self.past_event = None
            return

        now = datetime.now()
        past_times = [event for event in candle_lighting_times if event.datetime <= now]
        future_times = [event for event in candle_lighting_times if event.datetime > now]

        if not past_times:
            _LOGGER.debug(f"{DOMAIN}: LastCandleLightingSensor could not find any past times among {past_times}")
            self.past_event = None

        if not future_times:
            _LOGGER.debug(f"{DOMAIN}: LastCandleLightingSensor could not find any future times among {future_times}")
            self.next_event = None

        if self.past_event is None or self.next_event is None:
            return

        self.past_event = max(past_times).datetime
        self.next_event = min(future_times).datetime
        _LOGGER.info(f"YIWeHa: LastCandleLightingSensor updated past event to {self.past_event} and next event to {self.next_event}")
        self.async_write_ha_state()
        SENSORS["issur_melacha"].async_write_ha_state()
        self.schedule_next_update()

    def schedule_next_update(self):
        self._unsub_time_listener = async_track_point_in_time(
            self.hass,
            self.update_events,
            self.next_event
        )
        _LOGGER.info(f"YIWeHa: LastCandleLightingSensor scheduled next update for {self.next_event}")


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
        if not self.past_event or not self.next_event or datetime.now() >= self.next_event:
            self.update_events()

        if not self.past_event or not self.next_event:
            _LOGGER.debug(f"{DOMAIN}: LastHavdalahSensor native value failed to set")
            return


        _LOGGER.debug(f"{DOMAIN}: LastHavdalahSensor native value is being updated to {self.past_event}")

        return self.past_event

    @callback
    def update_events(self, hass_time=None):
        if not self.coordinator.data:
            _LOGGER.debug(f"{DOMAIN}: LastHavdalahSensor coordinator data is None")
            self.next_event = None
            self.past_event = None
            return

        havdalah_times = self.coordinator.data["havdalah"]
        if not havdalah_times:
            _LOGGER.debug(f"{DOMAIN}: LastHavdalahSensor could not find any times")
            self.next_event = None
            self.past_event = None
            return

        now = datetime.now()
        past_times = [event for event in havdalah_times if event.datetime <= now]
        future_times = [event for event in havdalah_times if event.datetime > now]

        if not past_times:
            _LOGGER.debug(f"{DOMAIN}: LastHavdalahSensor could not find any past times among {past_times}")
            self.past_event = None

        if not future_times:
            _LOGGER.debug(f"{DOMAIN}: LastHavdalahSensor could not find any future times among {future_times}")
            self.next_event = None

        if self.past_event is None or self.next_event is None:
            return

        self.past_event = max(past_times).datetime
        self.next_event = min(future_times).datetime
        _LOGGER.info(f"YIWeHa: LastHavdalahSensor updated past event to {self.past_event} and next event to {self.next_event}")
        self.async_write_ha_state()
        SENSORS["issur_melacha"].async_write_ha_state()
        self.schedule_next_update()

    def schedule_next_update(self):
        self._unsub_time_listener = async_track_point_in_time(
            self.hass,
            self.update_events,
            self.next_event
        )
        _LOGGER.info(f"YIWeHa: LastHavdalahSensor scheduled next update for {self.next_event}")


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
            _LOGGER.debug(f"IssurMelachaSensor is missing last_candle ({last_candle}) or last_havdalah ({last_havdalah})")
            return None

        value = last_candle > last_havdalah
        _LOGGER.debug(f"IssurMelachaSensor state was updated to {value}")
        return value
