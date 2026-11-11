"""Config and options flows for Weasley Clock."""

from __future__ import annotations

import copy
import uuid
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_LOCATIONS,
    CONF_PEOPLE,
    CONF_PHYSICAL,
    CONF_TITLE,
    DEFAULT_COLORS,
    DEFAULT_HAND_COUNT,
    DEFAULT_LOCATIONS,
    DEFAULT_STEPS_PER_REV,
    DOMAIN,
    PERSON_CALENDAR,
    PERSON_HAND,
    PHYS_DEVICE,
    PHYS_OFFSETS,
    PHYS_PAUSED,
    PHYS_REVERSE,
    PHYS_STEPS_PER_REV,
    LOC_AWAY,
    LOC_ID,
    LOC_NAME,
    LOC_STATES,
    LOC_UNKNOWN,
    LOC_ZONES,
    PERSON_COLOR,
    PERSON_ENTITY,
    PERSON_ID,
    PERSON_NAME,
)
from .physical import async_find_hand_numbers

CONF_NAME = "name"
CONF_INITIAL_PEOPLE = "initial_people"
CONF_POSITION = "position"
CONF_DELETE = "delete"
CONF_TARGET = "target"


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _hex_to_rgb(value: str | None) -> list[int]:
    value = (value or DEFAULT_COLORS[0]).lstrip("#")
    try:
        return [int(value[i : i + 2], 16) for i in (0, 2, 4)]
    except ValueError:
        return [139, 26, 26]


def _rgb_to_hex(rgb: list[int] | tuple[int, ...]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, int(c))) for c in rgb[:3]])


def _split_states(raw: str | None) -> list[str]:
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


def _default_locations() -> list[dict[str, Any]]:
    return [{LOC_ID: _new_id(), **copy.deepcopy(loc)} for loc in DEFAULT_LOCATIONS]


def _make_person(hass, entity_id: str, index: int, name: str | None = None) -> dict[str, Any]:
    if not name:
        state = hass.states.get(entity_id)
        name = state.name if state else entity_id.split(".", 1)[-1].replace("_", " ").title()
    return {
        PERSON_ID: _new_id(),
        PERSON_ENTITY: entity_id,
        PERSON_NAME: name,
        PERSON_COLOR: DEFAULT_COLORS[index % len(DEFAULT_COLORS)],
    }


PERSON_ENTITY_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["person", "device_tracker"])
)


class WeasleyClockConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create a new clock."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            if not name:
                errors[CONF_NAME] = "name_required"
            else:
                people = [
                    _make_person(self.hass, entity_id, i)
                    for i, entity_id in enumerate(user_input.get(CONF_INITIAL_PEOPLE, []))
                ]
                return self.async_create_entry(
                    title=name,
                    data={},
                    options={
                        CONF_TITLE: user_input.get(CONF_TITLE, "").strip(),
                        CONF_LOCATIONS: _default_locations(),
                        CONF_PEOPLE: people,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Family Clock"): str,
                vol.Optional(CONF_TITLE, default=""): str,
                vol.Optional(CONF_INITIAL_PEOPLE, default=[]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["person", "device_tracker"], multiple=True)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WeasleyClockOptionsFlow()


class WeasleyClockOptionsFlow(OptionsFlow):
    """Manage locations, people and display settings."""

    def __init__(self) -> None:
        self._options: dict[str, Any] | None = None
        self._editing: str | None = None

    @property
    def opts(self) -> dict[str, Any]:
        if self._options is None:
            self._options = copy.deepcopy(dict(self.config_entry.options))
            self._options.setdefault(CONF_LOCATIONS, [])
            self._options.setdefault(CONF_PEOPLE, [])
        return self._options

    # ------------------------------------------------------------------ menu
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        menu = ["add_location"]
        if self.opts[CONF_LOCATIONS]:
            menu.append("pick_location")
        menu.append("add_person")
        if self.opts[CONF_PEOPLE]:
            menu.append("pick_person")
        menu += ["settings", "physical", "save"]
        locs = ", ".join(l[LOC_NAME] for l in self.opts[CONF_LOCATIONS]) or "-"
        people = ", ".join(p[PERSON_NAME] for p in self.opts[CONF_PEOPLE]) or "-"
        return self.async_show_menu(
            step_id="init",
            menu_options=menu,
            description_placeholders={"locations": locs, "people": people},
        )

    async def async_step_save(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_create_entry(data=self.opts)

    # ------------------------------------------------------------- settings
    async def async_step_settings(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self.opts[CONF_TITLE] = user_input.get(CONF_TITLE, "").strip()
            return await self.async_step_init()
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {vol.Optional(CONF_TITLE, default=self.opts.get(CONF_TITLE, "")): str}
            ),
        )

    # ------------------------------------------------------- physical clock
    @property
    def physical(self) -> dict[str, Any]:
        return self.opts.get(CONF_PHYSICAL) or {}

    def _hand_count(self, device_id: str | None = None) -> int:
        device_id = device_id if device_id is not None else self.physical.get(PHYS_DEVICE)
        hands = async_find_hand_numbers(self.hass, device_id) if device_id else {}
        return max(hands, default=DEFAULT_HAND_COUNT)

    async def async_step_physical(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        phys = self.physical
        errors: dict[str, str] = {}
        if user_input is not None:
            device_id = user_input.get(PHYS_DEVICE) or ""
            if device_id and not async_find_hand_numbers(self.hass, device_id):
                errors[PHYS_DEVICE] = "not_a_clock"
            else:
                self.opts[CONF_PHYSICAL] = {
                    PHYS_DEVICE: device_id,
                    PHYS_STEPS_PER_REV: int(user_input[PHYS_STEPS_PER_REV]),
                    PHYS_REVERSE: bool(user_input.get(PHYS_REVERSE)),
                    PHYS_PAUSED: bool(user_input.get(PHYS_PAUSED)),
                    PHYS_OFFSETS: {
                        key.split("_")[1]: int(value)
                        for key, value in user_input.items()
                        if key.startswith("hand_") and key.endswith("_offset")
                    },
                }
                return await self.async_step_init()

        offsets = phys.get(PHYS_OFFSETS) or {}
        steps = phys.get(PHYS_STEPS_PER_REV) or DEFAULT_STEPS_PER_REV
        fields: dict[Any, Any] = {
            vol.Optional(PHYS_DEVICE, description={"suggested_value": phys.get(PHYS_DEVICE) or None}): (
                selector.DeviceSelector(selector.DeviceSelectorConfig(integration="esphome"))
            ),
            vol.Required(PHYS_STEPS_PER_REV, default=steps): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=100000, step=1, mode=selector.NumberSelectorMode.BOX)
            ),
            vol.Optional(PHYS_REVERSE, default=bool(phys.get(PHYS_REVERSE))): bool,
            vol.Optional(PHYS_PAUSED, default=bool(phys.get(PHYS_PAUSED))): bool,
        }
        for hand in range(1, self._hand_count() + 1):
            fields[vol.Required(f"hand_{hand}_offset", default=int(offsets.get(str(hand), 0)))] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-steps, max=steps, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                )
            )
        return self.async_show_form(step_id="physical", data_schema=vol.Schema(fields), errors=errors)

    # ------------------------------------------------------------ locations
    def _location_schema(self, loc: dict[str, Any] | None, is_new: bool) -> vol.Schema:
        loc = dict(loc or {})
        if isinstance(loc.get(LOC_STATES), str):
            loc[LOC_STATES] = _split_states(loc[LOC_STATES])
        count = len(self.opts[CONF_LOCATIONS]) + (1 if is_new else 0)
        position = count
        if not is_new:
            position = next(
                i + 1 for i, l in enumerate(self.opts[CONF_LOCATIONS]) if l[LOC_ID] == loc[LOC_ID]
            )
        fields: dict[Any, Any] = {
            vol.Required(LOC_NAME, default=loc.get(LOC_NAME, "")): str,
            vol.Optional(LOC_ZONES, default=loc.get(LOC_ZONES, [])): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="zone", multiple=True)
            ),
            vol.Optional(LOC_STATES, default=", ".join(loc.get(LOC_STATES, []))): str,
            vol.Optional(LOC_AWAY, default=loc.get(LOC_AWAY, False)): bool,
            vol.Optional(LOC_UNKNOWN, default=loc.get(LOC_UNKNOWN, False)): bool,
            vol.Required(CONF_POSITION, default=position): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=max(count, 1), step=1, mode=selector.NumberSelectorMode.BOX)
            ),
        }
        if not is_new:
            fields[vol.Optional(CONF_DELETE, default=False)] = bool
        return vol.Schema(fields)

    def _validate_location(self, user_input: dict[str, Any], current_id: str | None) -> dict[str, str]:
        name = user_input[LOC_NAME].strip()
        if not name:
            return {LOC_NAME: "name_required"}
        if any(
            l[LOC_NAME].casefold() == name.casefold() and l[LOC_ID] != current_id
            for l in self.opts[CONF_LOCATIONS]
        ):
            return {LOC_NAME: "duplicate_location"}
        return {}

    def _store_location(self, user_input: dict[str, Any], loc_id: str) -> None:
        locations = [l for l in self.opts[CONF_LOCATIONS] if l[LOC_ID] != loc_id]
        loc = {
            LOC_ID: loc_id,
            LOC_NAME: user_input[LOC_NAME].strip(),
            LOC_ZONES: list(user_input.get(LOC_ZONES, [])),
            LOC_STATES: _split_states(user_input.get(LOC_STATES)),
            LOC_AWAY: bool(user_input.get(LOC_AWAY)),
            LOC_UNKNOWN: bool(user_input.get(LOC_UNKNOWN)),
        }
        pos = int(user_input.get(CONF_POSITION, len(locations) + 1)) - 1
        locations.insert(max(0, min(pos, len(locations))), loc)
        self.opts[CONF_LOCATIONS] = locations

    async def async_step_add_location(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_location(user_input, None)
            if not errors:
                self._store_location(user_input, _new_id())
                return await self.async_step_init()
        return self.async_show_form(
            step_id="add_location", data_schema=self._location_schema(user_input, True), errors=errors
        )

    async def async_step_pick_location(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._editing = user_input[CONF_TARGET]
            return await self.async_step_edit_location()
        options = [
            selector.SelectOptionDict(value=l[LOC_ID], label=f"{i + 1}. {l[LOC_NAME]}")
            for i, l in enumerate(self.opts[CONF_LOCATIONS])
        ]
        return self.async_show_form(
            step_id="pick_location",
            data_schema=vol.Schema(
                {vol.Required(CONF_TARGET): selector.SelectSelector(selector.SelectSelectorConfig(options=options))}
            ),
        )

    async def async_step_edit_location(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        loc = next((l for l in self.opts[CONF_LOCATIONS] if l[LOC_ID] == self._editing), None)
        if loc is None:
            return await self.async_step_init()
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_DELETE):
                self.opts[CONF_LOCATIONS] = [l for l in self.opts[CONF_LOCATIONS] if l[LOC_ID] != loc[LOC_ID]]
                return await self.async_step_init()
            errors = self._validate_location(user_input, loc[LOC_ID])
            if not errors:
                self._store_location(user_input, loc[LOC_ID])
                return await self.async_step_init()
        return self.async_show_form(
            step_id="edit_location",
            data_schema=self._location_schema(loc, False),
            errors=errors,
            description_placeholders={"name": loc[LOC_NAME]},
        )

    # --------------------------------------------------------------- people
    def _person_schema(self, person: dict[str, Any] | None, is_new: bool) -> vol.Schema:
        person = person or {}
        fields: dict[Any, Any] = {}
        if person.get(PERSON_ENTITY):
            fields[vol.Required(PERSON_ENTITY, default=person[PERSON_ENTITY])] = PERSON_ENTITY_SELECTOR
        else:
            fields[vol.Required(PERSON_ENTITY)] = PERSON_ENTITY_SELECTOR
        fields[vol.Optional(PERSON_NAME, default=person.get(PERSON_NAME, ""))] = str
        color = person.get(PERSON_COLOR) or DEFAULT_COLORS[len(self.opts[CONF_PEOPLE]) % len(DEFAULT_COLORS)]
        fields[vol.Required(PERSON_COLOR, default=_hex_to_rgb(color))] = selector.ColorRGBSelector()
        # suggested_value rather than default, so the calendar can be cleared again.
        fields[
            vol.Optional(PERSON_CALENDAR, description={"suggested_value": person.get(PERSON_CALENDAR) or None})
        ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="calendar"))
        if self.physical.get(PHYS_DEVICE):
            hand_options = [selector.SelectOptionDict(value="0", label="None")] + [
                selector.SelectOptionDict(value=str(h), label=f"Hand {h}")
                for h in range(1, self._hand_count() + 1)
            ]
            fields[vol.Optional(PERSON_HAND, default=str(person.get(PERSON_HAND) or 0))] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=hand_options, mode=selector.SelectSelectorMode.DROPDOWN)
            )
        if not is_new:
            fields[vol.Optional(CONF_DELETE, default=False)] = bool
        return vol.Schema(fields)

    def _store_person(self, user_input: dict[str, Any], person_id: str) -> None:
        entity_id = user_input[PERSON_ENTITY]
        built = _make_person(self.hass, entity_id, 0, user_input.get(PERSON_NAME, "").strip() or None)
        built[PERSON_ID] = person_id
        built[PERSON_COLOR] = _rgb_to_hex(user_input.get(PERSON_COLOR, [139, 26, 26]))
        built[PERSON_CALENDAR] = user_input.get(PERSON_CALENDAR) or ""
        people = self.opts[CONF_PEOPLE]
        existing = next((p for p in people if p[PERSON_ID] == person_id), {})
        built[PERSON_HAND] = int(user_input.get(PERSON_HAND, existing.get(PERSON_HAND) or 0))
        for i, p in enumerate(people):
            if p[PERSON_ID] == person_id:
                people[i] = built
                return
        people.append(built)

    def _validate_person(self, user_input: dict[str, Any], person_id: str | None) -> dict[str, str]:
        hand = int(user_input.get(PERSON_HAND) or 0)
        if hand and any(
            int(p.get(PERSON_HAND) or 0) == hand and p[PERSON_ID] != person_id for p in self.opts[CONF_PEOPLE]
        ):
            return {PERSON_HAND: "hand_taken"}
        return {}

    async def async_step_add_person(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_person(user_input, None)
            if not errors:
                self._store_person(user_input, _new_id())
                return await self.async_step_init()
        return self.async_show_form(
            step_id="add_person", data_schema=self._person_schema(None, True), errors=errors
        )

    async def async_step_pick_person(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._editing = user_input[CONF_TARGET]
            return await self.async_step_edit_person()
        options = [
            selector.SelectOptionDict(value=p[PERSON_ID], label=p[PERSON_NAME]) for p in self.opts[CONF_PEOPLE]
        ]
        return self.async_show_form(
            step_id="pick_person",
            data_schema=vol.Schema(
                {vol.Required(CONF_TARGET): selector.SelectSelector(selector.SelectSelectorConfig(options=options))}
            ),
        )

    async def async_step_edit_person(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        person = next((p for p in self.opts[CONF_PEOPLE] if p[PERSON_ID] == self._editing), None)
        if person is None:
            return await self.async_step_init()
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get(CONF_DELETE):
                self.opts[CONF_PEOPLE] = [p for p in self.opts[CONF_PEOPLE] if p[PERSON_ID] != person[PERSON_ID]]
                return await self.async_step_init()
            errors = self._validate_person(user_input, person[PERSON_ID])
            if not errors:
                self._store_person(user_input, person[PERSON_ID])
                return await self.async_step_init()
        return self.async_show_form(
            step_id="edit_person",
            data_schema=self._person_schema(person, False),
            errors=errors,
            description_placeholders={"name": person[PERSON_NAME]},
        )
