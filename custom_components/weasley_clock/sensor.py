"""Sensor platform: one sensor per person showing their clock position."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import (
    async_track_point_in_time,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from . import WeasleyClockConfigEntry
from .clock import ClockRuntime
from .const import LOC_ID, LOC_NAME, PERSON_CALENDAR, PERSON_COLOR, PERSON_ENTITY, PERSON_ID
from .entity import WeasleyClockEntity

_LOGGER = logging.getLogger(__name__)

# How far ahead to fetch calendar events, so the next start can be scheduled precisely.
PLAN_LOOKAHEAD = timedelta(hours=1)
# Fallback re-check, in case the calendar changes without its entity state changing.
PLAN_REFRESH = timedelta(minutes=15)


def _parse_event_time(value: Any) -> datetime | None:
    """Parse a calendar event start/end; all-day events give a date only."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        return dt_util.start_of_local_day(value)
    elif value:
        parsed = dt_util.parse_datetime(str(value))
        if parsed is None:
            day = dt_util.parse_date(str(value))
            return dt_util.start_of_local_day(day) if day else None
    else:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_util.get_default_time_zone())


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
        self._calendar: str = person.get(PERSON_CALENDAR) or ""
        self._planned: str | None = None  # location id from a calendar event happening now
        self._planned_event: str | None = None
        self._unsub_next_plan: CALLBACK_TYPE | None = None
        self._plan_stopped = False

    async def async_added_to_hass(self) -> None:
        watched = [self.person[PERSON_ENTITY], *self.clock.watched_zones()]
        self.async_on_remove(
            async_track_state_change_event(self.hass, watched, self._handle_state_change)
        )
        self.async_on_remove(self.clock.add_listener(self._handle_override))
        self._recalculate()

        if self._calendar:
            # The calendar entity's state flips at event starts/ends and when it first loads.
            self.async_on_remove(
                async_track_state_change_event(self.hass, [self._calendar], self._handle_calendar_change)
            )
            self.async_on_remove(async_track_time_interval(self.hass, self._async_refresh_plan, PLAN_REFRESH))
            self.async_on_remove(self._cancel_next_plan)
            self.async_on_remove(self._mark_removed)
            # Don't hold up startup waiting for a (possibly remote) calendar.
            self.hass.async_create_task(self._async_refresh_plan())

    @callback
    def _handle_calendar_change(self, event: Event[EventStateChangedData]) -> None:
        self.hass.async_create_task(self._async_refresh_plan())

    @callback
    def _mark_removed(self) -> None:
        self._plan_stopped = True

    @callback
    def _cancel_next_plan(self) -> None:
        if self._unsub_next_plan:
            self._unsub_next_plan()
            self._unsub_next_plan = None

    async def _async_refresh_plan(self, *_: Any) -> None:
        """Find a calendar event happening now whose title is a position name."""
        now = dt_util.now()
        try:
            response = await self.hass.services.async_call(
                "calendar",
                "get_events",
                {"entity_id": self._calendar, "start_date_time": now, "end_date_time": now + PLAN_LOOKAHEAD},
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError as err:  # calendar not loaded yet, or unavailable
            _LOGGER.debug("%s: can't read calendar %s: %s", self.clock.name, self._calendar, err)
            return
        if self._plan_stopped:  # removed (e.g. options saved) while waiting for the calendar
            return
        events = ((response or {}).get(self._calendar) or {}).get("events") or []

        by_name: dict[str, str] = {}
        for loc in self.clock.locations:
            by_name.setdefault(loc[LOC_NAME].strip().casefold(), loc[LOC_ID])

        planned: str | None = None
        planned_event: str | None = None
        planned_start: datetime | None = None
        boundaries: list[datetime] = []
        for ev in events:
            summary = str(ev.get("summary") or "").strip()
            location_id = by_name.get(summary.casefold())
            start, end = _parse_event_time(ev.get("start")), _parse_event_time(ev.get("end"))
            if location_id is None or start is None or end is None:
                continue
            boundaries += [t for t in (start, end) if t > now]
            # If events overlap, the one that started most recently wins.
            if start <= now < end and (planned_start is None or start > planned_start):
                planned, planned_event, planned_start = location_id, summary, start

        self._cancel_next_plan()
        if boundaries:
            self._unsub_next_plan = async_track_point_in_time(
                self.hass, self._async_refresh_plan, min(boundaries) + timedelta(seconds=1)
            )

        if (planned, planned_event) != (self._planned, self._planned_event):
            self._planned, self._planned_event = planned, planned_event
            self._recalculate()
            self.async_write_ha_state()

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
        self._index, self._overridden = self.clock.resolve(
            self.person[PERSON_ID], self._raw_state, self._planned
        )

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
            "planned": bool(self._planned) and not self._overridden,
            "planned_event": self._planned_event,
        }
