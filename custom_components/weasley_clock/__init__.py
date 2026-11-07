"""The Weasley Clock integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .clock import ClockRuntime
from .const import CARD_FILENAME, CARD_URL, CONF_PHYSICAL, DOMAIN, PERSON_ID, PHYS_DEVICE, VERSION
from .physical import PhysicalClock

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SELECT]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type WeasleyClockConfigEntry = ConfigEntry[ClockRuntime]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the bundled Lovelace card and load it on every dashboard."""
    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(card_path), cache_headers=False)]
    )
    add_extra_js_url(hass, f"{CARD_URL}?v={VERSION}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: WeasleyClockConfigEntry) -> bool:
    """Set up a clock from a config entry."""
    entry.runtime_data = ClockRuntime(
        hass=hass,
        entry_id=entry.entry_id,
        name=entry.title,
        options=dict(entry.options),
    )
    _async_remove_stale_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if (entry.options.get(CONF_PHYSICAL) or {}).get(PHYS_DEVICE):
        physical = PhysicalClock(hass, entry.runtime_data)
        physical.async_start()
        entry.async_on_unload(physical.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: WeasleyClockConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: WeasleyClockConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _async_remove_stale_entities(hass: HomeAssistant, entry: WeasleyClockConfigEntry) -> None:
    """Drop entities for people that have been removed from the clock."""
    valid = {
        f"{entry.entry_id}_{person[PERSON_ID]}_{key}"
        for person in entry.runtime_data.people
        for key in ("location", "override")
    }
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.unique_id not in valid:
            registry.async_remove(reg_entry.entity_id)
