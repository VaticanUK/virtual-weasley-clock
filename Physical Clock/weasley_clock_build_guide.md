# Custom Home Assistant Weasley Clock

Build your own magical, fully functional Weasley Clock powered by an **ESP32**, four **28BYJ-48 stepper motors with ULN2003 driver boards**, **A3144 Hall-effect homing sensors**, and custom 3D-printed antique scissor-blade hands designed in **OpenSCAD**.

---

## 1. Bill of Materials (BOM)
- **Microcontroller:** ESP32 DevKit V1 (30-pin board)
- **Motors:** 4x 28BYJ-48 5V Unipolar Stepper Motors (with internal 64:1 gear reduction)
- **Drivers:** 4x ULN2003 Motor Driver Boards
- **Homing Sensors:** 4x A3144 Hall-effect sensors + 4x Tiny Neodymium Magnets
- **Pull-Up Resistors:** 4x 10k$\Omega$ resistors (Brown-Black-Orange-Gold) for the Hall sensor outputs
- **Power Supply:** 5V, 500mA+ DC power supply (GND tied to ESP32 GND and driver `-`; 5V+ tied to ESP32 `VIN` and driver `+`)
- **Mechanicals:** Assorted metric brass tubing for coaxial nesting of hands (diameters accommodating 2mm, 3mm, 4mm, and 5mm bores)

---

## 2. Wiring & Pin Mapping

### Stepper Motors (ULN2003)
Because the 28BYJ-48 unipolar coils use shared center-taps, the step sequence requires swapping `pin_b` and `pin_c` in ESPHome YAML (equivalent to a swapped middle-phase wiring order) so the motors rotate instead of locking in a magnetic well.

| Hand / Motor | ESP32 GPIO Pins (IN1, IN2, IN3, IN4) | Board Pin Labels | Notes |
| :--- | :--- | :--- | :--- |
| **Motor 1** | `GPIO18`, `GPIO17`, `GPIO5`, `GPIO16` | `D18`, `D17`, `D5`, `D16` | Contiguous 4-pin block |
| **Motor 2** | `GPIO23`, `GPIO21`, `GPIO22`, `GPIO19` | `D23`, `D21`, `D22`, `D19` | Standard sequence |
| **Motor 3** | `GPIO13`, `GPIO12`, `GPIO14`, `GPIO27` | `D13`, `D12`, `D14`, `D27` | Contiguous 4-pin block |
| **Motor 4** | `GPIO4`, `GPIO15`, `GPIO2`, `GPIO26` | `D4`, `D15`, `D2`, `D26` | Uses `D2` (onboard LED) & `D26` (bypasses missing GPIO 0) |

### Hall-Effect Homing Sensors (A3144)
*Note: Pins 34–39 on the ESP32 are input-only and **do not support internal pull-up resistors**. Therefore, each sensor requires an **external 10k$\Omega$ pull-up resistor** connected between its Output pin and the 3.3V rail.*

- **Pin 1 (VCC):** 5V Rail
- **Pin 2 (GND):** System Ground
- **Pin 3 (OUTPUT):** Connected to ESP32 GPIO **AND** tied to 3.3V via a dedicated 10k$\Omega$ resistor.
  - **Sensor 1:** `GPIO32` (Hand 1)
  - **Sensor 2:** `GPIO34` (Hand 2)
  - **Sensor 3:** `GPIO35` (Hand 3)
  - **Sensor 4:** `GPIO33` (Hand 4)

---

## 3. OpenSCAD Custom Scissor Hands Script

This script generates watertight, 3D-printable antique scissor-blade hands with compact ~50mm pointer lengths, through-cut filigree lettering bridging across the open blade, an offset scissor bow ring, and your family initials. 

*(Requires fonts `KellsFLF` and `Goudy Old Style` installed on your system).*

```openscad
// ============================================================================
// AUTHENTIC WEASLEY CLOCK "SCISSOR-BLADE" HANDS (~50mm Pointer Length)
// ============================================================================

/* [Choose Hand to Render] */
hand_to_render = "richard_hand_2mm"; // ["all_preview", "richard_hand_2mm", "anna_hand_3mm", "esmae_hand_4mm", "cerys_hand_5mm"]

/* [Typography] */
name_font    = "KellsFLF:style=Bold"; 
initial_font = "Goudy Old Style:style=Bold";

/* [Pointer Lengths (~50mm)] */
len_richard = 54;
len_anna    = 51;
len_esmae   = 48;
len_cerys   = 45;

/* [Dimensions & Print Tolerances] */
bore_clearance  = 0.08; // Radial clearance for brass tubes
blade_thickness = 2.0;  // Hand thickness (mm)
collet_height   = 4.0;  // Central shaft collar height (mm)

$fn = 64;

if (hand_to_render == "all_preview") {
    translate([  0, 0, 0]) weasley_filigree_hand("RICHARD", "R", 2.0 + bore_clearance, len_richard);
    translate([ 30, 0, 0]) weasley_filigree_hand("ANNA",    "A", 3.0 + bore_clearance, len_anna);
    translate([ 60, 0, 0]) weasley_filigree_hand("ESMAE",   "E", 4.0 + bore_clearance, len_esmae);
    translate([ 90, 0, 0]) weasley_filigree_hand("CERYS",   "C", 5.0 + bore_clearance, len_cerys);
} else if (hand_to_render == "richard_hand_2mm") {
    weasley_filigree_hand("RICHARD", "R", 2.0 + bore_clearance, len_richard);
} else if (hand_to_render == "anna_hand_3mm") {
    weasley_filigree_hand("ANNA",    "A", 3.0 + bore_clearance, len_anna);
} else if (hand_to_render == "esmae_hand_4mm") {
    weasley_filigree_hand("ESMAE",   "E", 4.0 + bore_clearance, len_esmae);
} else if (hand_to_render == "cerys_hand_5mm") {
    weasley_filigree_hand("CERYS",   "C", 5.0 + bore_clearance, len_cerys);
}

module scissor_bow_2d(initial_str) {
    bow_cx = -3.4;
    bow_cy = -21.0;
    translate([bow_cx, bow_cy]) {
        difference() {
            union() {
                scale([1.0, 1.28]) circle(r = 9.0);
                for (a = [0 : 18 : 342]) {
                    translate([8.9 * cos(a), 11.4 * sin(a)]) circle(r = 1.0);
                }
                translate([-9.4, 0]) circle(r = 1.6);
            }
            scale([1.0, 1.28]) circle(r = 6.2);
        }
        offset(delta = 0.18, chamfer = true)
        scale([1.22, 1.48])
            text(initial_str, size = 11.0, font = initial_font, halign = "center", valign = "center", $fn = 32);
    }
}

module scissor_blade_cutout_2d(name_str, hand_len) {
    win_start_y = 6.5;
    win_end_y   = hand_len - 11.5;
    win_len     = win_end_y - win_start_y;
    outer_half_w = 3.6;
    win_half_w   = 2.10;

    union() {
        hull() {
            circle(r = 3.8);
            translate([-1.3, -7.5]) circle(r = 2.7);
        }
        hull() {
            translate([-1.3, -7.5]) circle(r = 2.7);
            translate([-3.0, -13.5]) circle(r = 2.6);
        }
        translate([-2.2, -10.8]) scale([1.65, 0.7]) circle(r = 2.6);

        difference() {
            polygon(points = [
                [-3.4, 0.0], [-outer_half_w, 4.5], [-outer_half_w, win_end_y],
                [-2.0, hand_len - 6.0], [0.0, hand_len], [2.3, hand_len - 6.0],
                [outer_half_w + 0.3, win_end_y], [outer_half_w + 0.5, 6.5], [3.5, 0.0]
            ]);
            hull() {
                translate([0, win_start_y + 1.0]) circle(r = win_half_w);
                translate([0, win_end_y   - 1.0]) circle(r = win_half_w);
            }
            translate([0, hand_len - 7.5]) rotate([0, 0, 45]) square([1.7, 1.7], center = true);
            translate([0, hand_len - 9.8]) circle(r = 0.6);
            translate([0, hand_len - 4.8]) circle(r = 0.55);
        }

        n_chars = len(name_str);
        step_y  = (win_len - 1.6) / n_chars;
        char_scale = min(0.95, step_y / 4.2);

        for (i = [0 : n_chars - 1]) {
            char_y = (win_start_y + 0.8) + (i + 0.5) * step_y;
            translate([0, char_y])
            rotate([0, 0, 90])
            offset(delta = 0.14, chamfer = true)
            scale([char_scale, 1.45])
                text(name_str[i], size = 3.5, font = name_font, halign = "center", valign = "center", $fn = 32);
        }
    }
}

module complete_hand_2d(name_str, initial_str, bore_d, collet_od, hand_len) {
    difference() {
        offset(delta = 0.01) offset(delta = -0.01)
        union() {
            scissor_bow_2d(initial_str);
            scissor_blade_cutout_2d(name_str, hand_len);
            circle(d = collet_od + 1.2);
        }
        circle(d = bore_d);
    }
}

module weasley_filigree_hand(name_str, initial_str, bore_d, hand_len) {
    collet_od = bore_d + 4.0;
    union() {
        linear_extrude(height = blade_thickness, convexity = 20)
            complete_hand_2d(name_str, initial_str, bore_d, collet_od, hand_len);

        translate([0, 0, blade_thickness - 0.1])
        linear_extrude(height = 0.5, convexity = 4)
        difference() {
            circle(d = collet_od + 1.2);
            circle(d = bore_d);
        }

        translate([0, 0, blade_thickness - 0.1])
        linear_extrude(height = collet_height - blade_thickness + 0.1, convexity = 4)
        difference() {
            circle(d = collet_od);
            circle(d = bore_d);
        }
    }
}
```

---

## 4. ESPHome YAML Configuration

```yaml
esphome:
  name: weasley-clock
  friendly_name: Weasley Clock
  on_boot:
    priority: 600
    then:
      - delay: 10s
      - script.execute: home_all_hands

esp32:
  variant: esp32
  framework:
    type: esp-idf

logger:
api:
ota:
  - platform: esphome

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "Weasley Fallback Hotspot"
    password: !secret hotspot_password

captive_portal:

stepper:
  - platform: uln2003
    id: hand_1_stepper
    pin_a: GPIO18
    pin_b: GPIO5
    pin_c: GPIO17
    pin_d: GPIO16
    max_speed: 600 steps/s
    sleep_when_done: true

  - platform: uln2003
    id: hand_2_stepper
    pin_a: GPIO23
    pin_b: GPIO22
    pin_c: GPIO21
    pin_d: GPIO19
    max_speed: 600 steps/s
    sleep_when_done: true

  - platform: uln2003
    id: hand_3_stepper
    pin_a: GPIO13
    pin_b: GPIO12
    pin_c: GPIO14
    pin_d: GPIO27
    max_speed: 600 steps/s
    sleep_when_done: true

  - platform: uln2003
    id: hand_4_stepper
    pin_a: GPIO4
    pin_b: GPIO2
    pin_c: GPIO15
    pin_d: GPIO26
    max_speed: 600 steps/s
    sleep_when_done: true

script:
  - id: home_all_hands
    mode: queued
    then:
      - logger.log: "Starting Weasley Clock Homing Routine..."
      - script.execute: home_motor_1
      - script.execute: home_motor_2
      - script.execute: home_motor_3
      - script.execute: home_motor_4

  - id: home_motor_1
    mode: parallel
    then:
      - stepper.set_speed: {id: hand_1_stepper, speed: 150 steps/s}
      - stepper.set_target: {id: hand_1_stepper, target: !lambda "return id(hand_1_stepper).current_position + 7000;"}
      - wait_until: {binary_sensor.is_on: home_sensor_1}
      - stepper.set_target: {id: hand_1_stepper, target: !lambda "return id(hand_1_stepper).current_position;"}
      - lambda: "id(hand_1_stepper).current_position = 0;"
      - number.set: {id: hand_1_pos, value: 0}
      - stepper.set_speed: {id: hand_1_stepper, speed: 600 steps/s}

  - id: home_motor_2
    mode: parallel
    then:
      - stepper.set_speed: {id: hand_2_stepper, speed: 150 steps/s}
      - stepper.set_target: {id: hand_2_stepper, target: !lambda "return id(hand_2_stepper).current_position + 7000;"}
      - wait_until: {binary_sensor.is_on: home_sensor_2}
      - stepper.set_target: {id: hand_2_stepper, target: !lambda "return id(hand_2_stepper).current_position;"}
      - lambda: "id(hand_2_stepper).current_position = 0;"
      - number.set: {id: hand_2_pos, value: 0}
      - stepper.set_speed: {id: hand_2_stepper, speed: 600 steps/s}

  - id: home_motor_3
    mode: parallel
    then:
      - stepper.set_speed: {id: hand_3_stepper, speed: 150 steps/s}
      - stepper.set_target: {id: hand_3_stepper, target: !lambda "return id(hand_3_stepper).current_position + 7000;"}
      - wait_until: {binary_sensor.is_on: home_sensor_3}
      - stepper.set_target: {id: hand_3_stepper, target: !lambda "return id(hand_3_stepper).current_position;"}
      - lambda: "id(hand_3_stepper).current_position = 0;"
      - number.set: {id: hand_3_pos, value: 0}
      - stepper.set_speed: {id: hand_3_stepper, speed: 600 steps/s}

  - id: home_motor_4
    mode: parallel
    then:
      - stepper.set_speed: {id: hand_4_stepper, speed: 150 steps/s}
      - stepper.set_target: {id: hand_4_stepper, target: !lambda "return id(hand_4_stepper).current_position + 7000;"}
      - wait_until: {binary_sensor.is_on: home_sensor_4}
      - stepper.set_target: {id: hand_4_stepper, target: !lambda "return id(hand_4_stepper).current_position;"}
      - lambda: "id(hand_4_stepper).current_position = 0;"
      - number.set: {id: hand_4_pos, value: 0}
      - stepper.set_speed: {id: hand_4_stepper, speed: 600 steps/s}

binary_sensor:
  - platform: gpio
    pin: {number: GPIO34, inverted: true}
    id: home_sensor_2
    name: Home Sensor 2

  - platform: gpio
    pin: {number: GPIO35, inverted: true}
    id: home_sensor_3
    name: Home Sensor 3

  - platform: gpio
    pin: {number: GPIO32, inverted: true}
    id: home_sensor_1
    name: Home Sensor 1

  - platform: gpio
    pin: {number: GPIO33, inverted: true}
    id: home_sensor_4
    name: Home Sensor 4

button:
  - platform: template
    name: "Home All Clock Hands"
    on_press: {then: [{script.execute: home_all_hands}]}

number:
  - platform: template
    name: "Hand 1 Position (Steps)"
    id: hand_1_pos
    min_value: -30720
    max_value: 30720
    step: 1
    optimistic: true
    set_action:
      then:
        - stepper.set_target: {id: hand_1_stepper, target: !lambda 'return x;'}

  - platform: template
    name: "Hand 2 Position (Steps)"
    id: hand_2_pos
    min_value: -30720
    max_value: 30720
    step: 1
    optimistic: true
    set_action:
      then:
        - stepper.set_target: {id: hand_2_stepper, target: !lambda 'return x;'}

  - platform: template
    name: "Hand 3 Position (Steps)"
    id: hand_3_pos
    min_value: -30720
    max_value: 30720
    step: 1
    optimistic: true
    set_action:
      then:
        - stepper.set_target: {id: hand_3_stepper, target: !lambda 'return x;'}

  - platform: template
    name: "Hand 4 Position (Steps)"
    id: hand_4_pos
    min_value: -30720
    max_value: 30720
    step: 1
    optimistic: true
    set_action:
      then:
        - stepper.set_target: {id: hand_4_stepper, target: !lambda 'return x;'}
```