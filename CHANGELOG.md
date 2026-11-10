# Changelog

## Sensor board

### v4 (2026-11-08)

Changes from v3:

- 4.7 kΩ I²C pull-ups (JLC Basic part) replace the 10 kΩ pair.
- Connector ground connection corrected.
- Decoupling capacitor moved closer to the sensor.
- All power and signals routed on the top layer; the underside is one continuous ground area.
- CJT A1002WR-S-4P connector with the same cable pin order.
- Four unplated tooling holes.
- Sensor position and board outline unchanged.

Not built yet.

### Earlier boards

v1 to v3 were the author's prototypes. v1 had the cable soldered to four pads. An earlier revision with the same AS5600 sensor was built and worked.

## Gauge tip

### Two-piece v2 (2026-11-09)

Tip plus a snap-in cable piece that holds the board forward and anchors the cable; sealed with waterproof, PCB-safe glue. Test-printed and worked for the author.

### One-piece v1 (2026-11-09)

Same outside shape and length as the assembled two-piece, with an open well behind the board that is filled with waterproof, PCB-safe glue. Printed, glue-filled and worked for the author.

## Generic module housing

### First version (2026-11-10)

Gauge reader and cap for a generic 23 × 23 mm AS5600 module, located by four pins. The module sits chip side down; the cable wires are soldered to its pads and DIR is tied to VCC. Printed and worked well in the author's testing.

## ESPHome configuration

### First version (unreleased)

- `propane-monitor.yaml` package: AS5600 on I²C (GPIO8/GPIO9, 100 kHz), angle as the median of 10 readings, tank level from the dial tables, Sensor problem flag.
- Dial type and angle offset set from Home Assistant and kept across reboots.
- `propane-monitor-battery.yaml`: 8-hour deep-sleep cycle, 15 minutes awake after power-on, setup mode from a Home Assistant helper. The sensor is powered from GPIO7 and switched off while the ESP32 sleeps.
- Compiles with ESPHome 2026.9.1 and validates with 2026.10.2. Not yet run on a v4 board.
