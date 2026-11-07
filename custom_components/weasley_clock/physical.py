"""Drive an optional physical clock so its hands mirror the virtual one.

The physical clock is an ESPHome device (see "Physical Clock/esphome.yaml") that
exposes one number entity per hand, "Hand N Position (Steps)". Setting that
number moves the stepper to that absolute step count, where 0 is the hand's
home (Hall sensor) position.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event

from .clock import ClockRuntime
from .const import (
    CONF_PHYSICAL,
    DEFAULT_STEPS_PER_REV,
    DOMAIN,
    PERSON_HAND,
    PERSON_ID,
    PHYS_DEVICE,
    PHYS_OFFSETS,
    PHYS_PAUSED,
    PHYS_REVERSE,
    PHYS_STEPS_PER_REV,
)

_LOGGER = logging.getLogger(__name__)

_HAND_NUMBER_RE = re.compile(r"hand[\s_]*(\d+)[\s_]*position", re.IGNORECASE)


@callback
def async_find_hand_numbers(hass: HomeAssistant, device_id: str) -> dict[int, str]:
    """Return {hand number: number entity_id} for an ESPHome clock device."""
    hands: dict[int, str] = {}
    registry = er.async_get(hass)
    for entry in er.async_entries_for_device(registry, device_id):
        if entry.domain != "number":
            continue
        for text in (entry.original_name, entry.name, entry.entity_id):
            if text and (match := _HAND_NUMBER_RE.search(text)):
                hands.setdefault(int(match.group(1)), entry.entity_id)
                break
    return hands


def target_steps(
    index: int | None,
    count: int,
    steps_per_rev: int,
    offset: int,
    reverse: bool,
    current: float,
    min_value: float,
    max_value: float,
) -> int:
    """Return the step target closest to ``current`` that points at ``index``.

    Position 0 is 12 o'clock and positions run clockwise, evenly spaced, exactly
    like the Lovelace card. ``None`` (no matching position) points at 12 o'clock.
    """
    fraction = (index or 0) / max(count, 1)
    base = offset + (-1 if reverse else 1) * fraction * steps_per_rev
    turns = round((current - base) / steps_per_rev)
    candidates = [base + (turns + d) * steps_per_rev for d in (0, -1, 1, -2, 2)]
    in_range = [c for c in candidates if min_value <= c <= max_value] or candidates
    return round(min(in_range, key=lambda c: abs(c - current)))


class PhysicalClock:
    """Keeps the hands of one ESPHome clock in step with a virtual clock."""

    def __init__(self, hass: HomeAssistant, clock: ClockRuntime) -> None:
        self.hass = hass
        self.clock = clock
        cfg: dict[str, Any] = clock.options.get(CONF_PHYSICAL) or {}
        self.device_id: str = cfg.get(PHYS_DEVICE) or ""
        self.steps_per_rev = int(cfg.get(PHYS_STEPS_PER_REV) or DEFAULT_STEPS_PER_REV)
        self.reverse = bool(cfg.get(PHYS_REVERSE))
        self.paused = bool(cfg.get(PHYS_PAUSED))
        self.offsets: dict[str, int] = {str(k): int(v) for k, v in (cfg.get(PHYS_OFFSETS) or {}).items()}
        self._unsub: CALLBACK_TYPE | None = None
        # hand number -> (person id, clock sensor entity_id, device number entity_id)
        self._hands: dict[int, tuple[str, str, str]] = {}

    @callback
    def async_start(self) -> None:
        numbers = async_find_hand_numbers(self.hass, self.device_id)
        if not numbers:
            _LOGGER.warning(
                "%s: physical clock device has no 'Hand N Position' number entities; is it the Weasley Clock ESPHome firmware?",
                self.clock.name,
            )
            return

        registry = er.async_get(self.hass)
        for person in self.clock.people:
            hand = int(person.get(PERSON_HAND) or 0)
            if not hand:
                continue
            if hand not in numbers:
                _LOGGER.warning("%s: physical clock has no hand %s", self.clock.name, hand)
                continue
            sensor_id = registry.async_get_entity_id(
                "sensor", DOMAIN, f"{self.clock.entry_id}_{person[PERSON_ID]}_location"
            )
            if sensor_id:
                self._hands[hand] = (person[PERSON_ID], sensor_id, numbers[hand])

        if not self._hands:
            return
        watched = [eid for _, sensor_id, number_id in self._hands.values() for eid in (sensor_id, number_id)]
        self._unsub = async_track_state_change_event(self.hass, watched, self._handle_change)
        for hand in self._hands:
            self._sync(hand)

    @callback
    def async_stop(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_change(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        for hand, (_, sensor_id, number_id) in self._hands.items():
            if entity_id in (sensor_id, number_id):
                self._sync(hand)

    @callback
    def _sync(self, hand: int) -> None:
        """Send the hand to its person's position unless it is already there.

        Re-sending whenever the device's value differs from the target also
        covers the device homing (which resets the value to 0) and reboots.
        """
        if self.paused:
            return
        _, sensor_id, number_id = self._hands[hand]
        number = self.hass.states.get(number_id)
        sensor = self.hass.states.get(sensor_id)
        if number is None or sensor is None or number.state == STATE_UNAVAILABLE:
            return
        if sensor.state == STATE_UNAVAILABLE:
            return

        try:
            current = float(number.state)
        except ValueError:  # "unknown" straight after boot
            current = 0.0
        known = number.state != STATE_UNKNOWN

        target = target_steps(
            index=sensor.attributes.get("location_index"),
            count=len(self.clock.locations),
            steps_per_rev=self.steps_per_rev,
            offset=self.offsets.get(str(hand), 0),
            reverse=self.reverse,
            current=current,
            min_value=float(number.attributes.get("min", float("-inf"))),
            max_value=float(number.attributes.get("max", float("inf"))),
        )
        if known and abs(current - target) < 0.5:
            return

        _LOGGER.debug("%s: moving physical hand %s to %s steps", self.clock.name, hand, target)
        self.hass.async_create_task(
            self.hass.services.async_call(
                "number", "set_value", {"entity_id": number_id, "value": target}, blocking=False
            )
        )
