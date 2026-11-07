# Weasley Clock for Home Assistant

A magical brass-and-paper clock face that shows where everyone is. Each person gets a hand
that points to the place they are now: Home, Work, School, Travelling, Mortal Peril, or
any other place you add.

* **Every position is configurable**: add, rename, reorder and remove positions, and map each one to one or more HA zones.
* **Every person is configurable**: choose any `person` or `device_tracker` entity, the name shown on the hand, and the hand colour.
* **Manual overrides**: each person gets a select entity, so an automation (or you) can send their hand to *Mortal Peril*, *Hospital* or anywhere else.
* **Bundled Lovelace card**: installing the integration also installs the card. You don't need to add a separate resource.
* **Nothing personal lives in this repository**: your people, places and zones are stored in your own Home Assistant config entry.

## Installation

### HACS (recommended)

1. In HACS, open the menu → **Custom repositories**. Add `https://github.com/VaticanUK/virtual-weasley-clock` with category **Integration**.
2. Search for **Weasley Clock**, install it, then restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration → Weasley Clock**.

### Manual

Copy `custom_components/weasley_clock` into your `config/custom_components/` folder, then restart Home Assistant.

## Setup

When you add the integration, you give the clock a name, optional centre text and the people to show.
It starts with a set of generic positions:

> Home · Work · School · Shopping · Travelling · Mortal Peril · Hospital · Friends · Holiday · Lost

Open **Configure** on the integration to:

| Menu item | What it does |
| --- | --- |
| Add a position | Label, zones, extra states, flags and where it sits on the dial (1 = 12 o'clock, then clockwise). |
| Edit, move or remove a position | Change any of the above, or delete the position. |
| Add a person / Edit or remove a person | Choose the entity, the name on the hand and the hand colour. |
| Display settings | Centre text. |
| Save and close | Applies your changes. |

### How a hand chooses its position

1. **Override**: if `select.<clock>_<person>_override` isn't `Auto`, the hand goes there.
2. **Zone / state match**: the person's state matches one of the position's zones (e.g. `zone.home` → `home`, `zone.work` → `Work`), or one of the extra states you listed.
3. **Away**: the person is `not_home`, or is in a zone that doesn't have a position, so the hand goes to the position flagged *"Use when away"* (e.g. Travelling).
4. **Unknown**: the person's state is unknown or unavailable, so the hand goes to the position flagged *"Use when unknown"* (e.g. Lost). If no position has that flag, the hand points to 12 o'clock, greyed out.

## Entities

For each person on each clock:

* `sensor.<clock>_<person>` is the current position (an enum sensor). Its attributes include `location_index`, `source_state` and `overridden`.
* `select.<clock>_<person>_override` is `Auto` or any position.

## The card

```yaml
type: custom:weasley-clock-card
# all optional:
clock: Family Clock    # clock name or entry id; defaults to the first clock
title: The Burrow      # override the centre text
show_legend: true      # list each person and their position under the dial
flip_labels: true      # false = authentic (labels in the lower half read upside down)
wood: true             # wooden case background
title_font: UnifrakturMaguntia  # font for the centre text (any loaded font)
hand_color: "#141414"  # colour of the scissor-blade hands
person_colors: false   # true = colour each hand with the person's colour from the integration
entities:              # optional explicit list instead of auto-discovery
  - sensor.family_clock_alice
```

Click a hand or a legend chip to open that person's details.
The card loads the *Pirata One* and *IM Fell English* fonts from Google Fonts. If they aren't available, it falls back to local serif fonts.

## Automation ideas

```yaml
# Send someone to Mortal Peril when their phone detects a fall
automation:
  - alias: Weasley clock - mortal peril
    triggers:
      - trigger: state
        entity_id: binary_sensor.phone_fall_detected
        to: "on"
    actions:
      - action: select.select_option
        target:
          entity_id: select.family_clock_alice_override
        data:
          option: Mortal Peril
```

Set the select back to `Auto` to return to normal tracking.

## Privacy

This repository contains no names, places or coordinates. Everything about your household
(the people, the positions and the zones they map to) is stored in your Home Assistant
config entry and never leaves your instance.

## License

MIT
