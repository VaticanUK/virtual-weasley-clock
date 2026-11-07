"""Shared entity base for Weasley Clock."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .clock import ClockRuntime
from .const import DOMAIN, PERSON_ID, PERSON_NAME, VERSION


class WeasleyClockEntity(Entity):
    """Base entity tied to one person on one clock."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, clock: ClockRuntime, person: dict[str, Any], key: str) -> None:
        self.clock = clock
        self.person = person
        self._attr_unique_id = f"{clock.entry_id}_{person[PERSON_ID]}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, clock.entry_id)},
            name=clock.name,
            manufacturer="Weasley Clock",
            model="Virtual clock",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def person_name(self) -> str:
        return self.person[PERSON_NAME]
