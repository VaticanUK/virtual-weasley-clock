"""Constants for the Weasley Clock integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "weasley_clock"
VERSION: Final = "0.1.0"

CARD_FILENAME: Final = "weasley-clock-card.js"
CARD_URL: Final = f"/{DOMAIN}/{CARD_FILENAME}"

CONF_LOCATIONS: Final = "locations"
CONF_PEOPLE: Final = "people"
CONF_TITLE: Final = "title"

# Location keys
LOC_ID: Final = "id"
LOC_NAME: Final = "name"
LOC_ZONES: Final = "zones"
LOC_STATES: Final = "states"
LOC_AWAY: Final = "away"  # matches when the person is not_home (no zone)
LOC_UNKNOWN: Final = "unknown"  # matches when the person's state is unknown

# Person keys
PERSON_ID: Final = "id"
PERSON_ENTITY: Final = "entity_id"
PERSON_NAME: Final = "name"
PERSON_COLOR: Final = "color"

PERSON_HAND: Final = "hand"  # physical hand number (1-based), 0 = none
PERSON_CALENDAR: Final = "calendar"  # calendar entity whose events plan positions, "" = none

OVERRIDE_AUTO: Final = "Auto"

# Optional physical clock (an ESPHome device built from "Physical Clock/esphome.yaml").
CONF_PHYSICAL: Final = "physical"
PHYS_DEVICE: Final = "device_id"
PHYS_STEPS_PER_REV: Final = "steps_per_rev"
PHYS_REVERSE: Final = "reverse"
PHYS_PAUSED: Final = "paused"
PHYS_OFFSETS: Final = "offsets"  # {"1": steps from home sensor to 12 o'clock, ...}

# 28BYJ-48 in full-step mode (2048 steps/rev) driving a 20T pinion -> 60T gear.
DEFAULT_STEPS_PER_REV: Final = 6144
DEFAULT_HAND_COUNT: Final = 4

# Generic default locations. Deliberately contains nothing personal; users
# add their own places (and map them to zones) from the options flow.
DEFAULT_LOCATIONS: Final = [
    {LOC_NAME: "Home", LOC_ZONES: ["zone.home"], LOC_STATES: [], LOC_AWAY: False, LOC_UNKNOWN: False},
    {LOC_NAME: "Work", LOC_ZONES: [], LOC_STATES: [], LOC_AWAY: False, LOC_UNKNOWN: False},
    {LOC_NAME: "School", LOC_ZONES: [], LOC_STATES: [], LOC_AWAY: False, LOC_UNKNOWN: False},
    {LOC_NAME: "Shopping", LOC_ZONES: [], LOC_STATES: [], LOC_AWAY: False, LOC_UNKNOWN: False},
    {LOC_NAME: "Travelling", LOC_ZONES: [], LOC_STATES: [], LOC_AWAY: True, LOC_UNKNOWN: False},
    {LOC_NAME: "Mortal Peril", LOC_ZONES: [], LOC_STATES: [], LOC_AWAY: False, LOC_UNKNOWN: False},
    {LOC_NAME: "Hospital", LOC_ZONES: [], LOC_STATES: [], LOC_AWAY: False, LOC_UNKNOWN: False},
    {LOC_NAME: "Friends", LOC_ZONES: [], LOC_STATES: [], LOC_AWAY: False, LOC_UNKNOWN: False},
    {LOC_NAME: "Holiday", LOC_ZONES: [], LOC_STATES: [], LOC_AWAY: False, LOC_UNKNOWN: False},
    {LOC_NAME: "Lost", LOC_ZONES: [], LOC_STATES: [], LOC_AWAY: False, LOC_UNKNOWN: True},
]

# Hand colours assigned to people in order (hex).
DEFAULT_COLORS: Final = [
    "#8b1a1a",  # garnet
    "#1f3a5f",  # navy
    "#2e5e3a",  # bottle green
    "#6b4423",  # walnut
    "#5b2a6e",  # plum
    "#9a6b00",  # old gold
    "#2f4f4f",  # slate
    "#7a2e4d",  # mulberry
]
