"""Sensor platform: one sensor per person showing their clock position."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from . import WeasleyClockConfigEntry
from .clock import ClockRuntime
from .const import PERSON_COLOR, PERSON_ENTITY, PERSON_ID
from .entity import WeasleyClockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WeasleyClockConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    clock = entry.runtime_data
    async_add_entities(WeasleyClockSensor(clock, person) for person in clock.people)


class WeasleyClockSensor(WeasleyClockEntity, SensorEntity):
    """Where on the clock a person currently is."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:clock-time-twelve-outline"

    def __init__(self, clock: ClockRuntime, person: dict[str, Any]) -> None:
        super().__init__(clock, person, "location")
        self._attr_name = self.person_name
        self._attr_options = clock.location_names
        self._index: int | None = None
        self._overridden = False
        self._raw_state: str | None = None

    async def async_added_to_hass(self) -> None:
        watched = [self.person[PERSON_ENTITY], *self.clock.watched_zones()]
        self.async_on_remove(
            async_track_state_change_event(self.hass, watched, self._handle_state_change)
        )
        self.async_on_remove(self.clock.add_listener(self._handle_override))
        self._recalculate()

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        self._recalculate()
        self.async_write_ha_state()

    @callback
    def _handle_override(self) -> None:
        self._recalculate()
        self.async_write_ha_state()

    @callback
    def _recalculate(self) -> None:
        state = self.hass.states.get(self.person[PERSON_ENTITY])
        self._raw_state = state.state if state else None
        self._index, self._overridden = self.clock.resolve(self.person[PERSON_ID], self._raw_state)

    @property
    def native_value(self) -> str | None:
        if self._index is None:
            return None
        return self.clock.location_names[self._index]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        source = self.hass.states.get(self.person[PERSON_ENTITY]) if self.hass else None
        picture = source.attributes.get("entity_picture") if source else None
        return {
            "weasley_clock": True,
            "clock_id": self.clock.entry_id,
            "clock_name": self.clock.name,
            "clock_title": self.clock.title,
            "locations": self.clock.location_names,
            "location_index": self._index,
            "person_name": self.person_name,
            "person_entity": self.person[PERSON_ENTITY],
            "person_order": [p[PERSON_ID] for p in self.clock.people].index(self.person[PERSON_ID]),
            "color": self.person.get(PERSON_COLOR),
            "entity_picture_source": picture,
            "source_state": self._raw_state,
            "overridden": self._overridden,
        }
