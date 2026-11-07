"""Core clock logic: works out which clock position each person is at."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from homeassistant.const import STATE_HOME, STATE_NOT_HOME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_LOCATIONS,
    CONF_PEOPLE,
    CONF_TITLE,
    LOC_AWAY,
    LOC_ID,
    LOC_NAME,
    LOC_STATES,
    LOC_UNKNOWN,
    LOC_ZONES,
)


@dataclass
class ClockRuntime:
    """Runtime state shared by the entities of one clock config entry."""

    hass: HomeAssistant
    entry_id: str
    name: str
    options: dict[str, Any]
    overrides: dict[str, str | None] = field(default_factory=dict)
    _listeners: list[Callable[[], None]] = field(default_factory=list)

    @property
    def title(self) -> str:
        return self.options.get(CONF_TITLE) or self.name

    @property
    def locations(self) -> list[dict[str, Any]]:
        return self.options.get(CONF_LOCATIONS, [])

    @property
    def people(self) -> list[dict[str, Any]]:
        return self.options.get(CONF_PEOPLE, [])

    @property
    def location_names(self) -> list[str]:
        return [loc[LOC_NAME] for loc in self.locations]

    def watched_zones(self) -> set[str]:
        return {z for loc in self.locations for z in loc.get(LOC_ZONES, [])}

    # -- overrides -----------------------------------------------------
    @callback
    def set_override(self, person_id: str, location_id: str | None) -> None:
        self.overrides[person_id] = location_id
        for listener in list(self._listeners):
            listener()

    @callback
    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def _remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return _remove

    # -- resolution ----------------------------------------------------
    def _zone_names(self, zone_entity_id: str) -> set[str]:
        """Return the person/device_tracker states that mean 'in this zone'."""
        if zone_entity_id == "zone.home":
            return {STATE_HOME}
        names = {zone_entity_id.split(".", 1)[-1].casefold()}
        if (zone := self.hass.states.get(zone_entity_id)) is not None:
            if friendly := zone.attributes.get("friendly_name"):
                names.add(str(friendly).strip().casefold())
            names.add(zone.name.strip().casefold())
        return names

    def resolve(self, person_id: str, raw_state: str | None) -> tuple[int | None, bool]:
        """Return (location index, overridden) for a person."""
        locations = self.locations

        override = self.overrides.get(person_id)
        if override:
            for idx, loc in enumerate(locations):
                if loc[LOC_ID] == override:
                    return idx, True

        state = (raw_state or STATE_UNKNOWN).strip().casefold()

        if state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            # 1. Explicit zone / state matches
            for idx, loc in enumerate(locations):
                for zone in loc.get(LOC_ZONES, []):
                    if state in self._zone_names(zone):
                        return idx, False
                if state in {s.strip().casefold() for s in loc.get(LOC_STATES, [])}:
                    return idx, False

            # 2. Away (not in any zone) -> e.g. "Travelling"
            if state == STATE_NOT_HOME:
                for idx, loc in enumerate(locations):
                    if loc.get(LOC_AWAY):
                        return idx, False

            # A zone we don't have a position for also counts as away.
            for idx, loc in enumerate(locations):
                if loc.get(LOC_AWAY) and state != STATE_HOME:
                    return idx, False

        # 3. Unknown / unmatched -> e.g. "Lost"
        for idx, loc in enumerate(locations):
            if loc.get(LOC_UNKNOWN):
                return idx, False

        return None, False
