"""Select platform: manual override of a person's clock position.

Set it from the UI or from automations (e.g. a fall detector moving someone to
"Mortal Peril"). Choose "Auto" to go back to zone-based tracking.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import WeasleyClockConfigEntry
from .clock import ClockRuntime
from .const import LOC_ID, LOC_NAME, OVERRIDE_AUTO, PERSON_ID
from .entity import WeasleyClockEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WeasleyClockConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    clock = entry.runtime_data
    async_add_entities(WeasleyClockOverrideSelect(clock, person) for person in clock.people)


class WeasleyClockOverrideSelect(WeasleyClockEntity, SelectEntity, RestoreEntity):
    """Force a person's hand to a given position."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:hand-pointing-right"

    def __init__(self, clock: ClockRuntime, person: dict[str, Any]) -> None:
        super().__init__(clock, person, "override")
        self._attr_name = f"{self.person_name} override"
        self._attr_options = [OVERRIDE_AUTO, *clock.location_names]
        self._attr_current_option = OVERRIDE_AUTO

    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_state()) is not None and last.state in self.options:
            self._attr_current_option = last.state
        self._apply()

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self._apply()
        self.async_write_ha_state()

    def _apply(self) -> None:
        location_id = None
        if self._attr_current_option != OVERRIDE_AUTO:
            location_id = next(
                (loc[LOC_ID] for loc in self.clock.locations if loc[LOC_NAME] == self._attr_current_option),
                None,
            )
        self.clock.set_override(self.person[PERSON_ID], location_id)
