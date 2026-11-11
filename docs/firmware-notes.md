# Firmware notes

For whoever changes the ESPHome configuration in [esphome/](../esphome/README.md). Builders don't need this page; the [build guide](build-guide.md) covers flashing and setup.

Sources: the sensor board design, the ams AS5600 datasheet v1-06, and the ESPHome 2026.9.1 and 2026.10.2 `as5600`, `i2c`, `sensor`, `template` and `deep_sleep` source code.

## Target

- **Board:** ESP32-S3. I²C on GPIO8 (SDA) and GPIO9 (SCL), the ESP32-S3 defaults in the Arduino-ESP32 core (`variants/esp32s3/pins_arduino.h`). Set them explicitly: for boards without their own pin map (such as `esp32-s3-devkitc-1`), ESPHome resolves the `SDA`/`SCL` aliases to the classic ESP32's GPIO21/22, and the ESP32-S3 has no GPIO22. ESP-IDF is ESPHome's default framework; a known `board:` or a `variant:` is enough.
- **ESPHome version:** these notes were checked against 2026.9.1 and 2026.10.2. The package sets `esphome: min_version: 2026.9.1`.
- **Power:** the builder's choice. `propane-monitor.yaml` keeps the device awake (USB power); adding `propane-monitor-battery.yaml` gives the [reading cycle](#reading-cycle) below and switches the sensor off while asleep ([timing and power](#timing-and-power)). If a build runs on battery, set its low-battery threshold from its own regulator.
- **Output:** tank percentage, unknown when the reading can't be trusted, plus the angle, magnet status, gain and magnitude as diagnostics. No litres.
- **Dial type and calibration** change at runtime from Home Assistant, kept across reboots, with no reflashing: a template `select` for the dial type, a template `number` for an angle offset, both `optimistic: true` and `restore_value: true` (ESPHome rejects `restore_value` together with `lambda:`). `calibrate_linear` datapoints are fixed at compile time, so the conversion is a lambda that interpolates the selected table. The YAML holds the numbers and [calibration.md](calibration.md#tables) mirrors them; `esphome/tests/tank_level_test.py` checks that the two match.
- **Licence:** `esphome/` is GPLv3 (`esphome/LICENSE`), because lambdas and any external component compile together with ESPHome's GPLv3 C++ runtime. The rest of the repo is CC BY-NC-SA 4.0.

## Sensor board interface

| Item | Value | Source |
|---|---|---|
| Sensor | ams AS5600, 12-bit angle, 0–360° | datasheet |
| I²C address | 0x36, fixed; one sensor per bus | datasheet |
| Supply | 3.0–3.6 V (3.3 V mode: VDD5V and VDD3V3 tied together). Absolute maximum 4.0 V: VDD3V3's limit, which the tied supply inherits (VDD5V's own is 6.1 V) | datasheet Figures 5 and 6 |
| Pull-ups | 4.7 kΩ from SDA and SCL to the board's 3V3 | schematic |
| Decoupling | 100 nF only. The chip's one-time programming (BURN_ANGLE for ZPOS/MPOS, BURN_SETTING for MANG/CONF) needs 10 µF on VDD3V3, which the board doesn't have, so it isn't used: all configuration lives in the YAML | datasheet Figure 13, pages 20–21 |
| DIR | Hard-wired to VDD: the angle increases with counter-clockwise rotation (datasheet convention). It can't float. Don't set the `as5600` `dir_pin`; without it, `direction:` does nothing | datasheet pin table; schematic |
| OUT, PGO | Not connected. Use I²C only | schematic |
| Connector | 4-pin JST SH, 1.00 mm: 1 GND, 2 3V3, 3 SDA, 4 SCL | board |
| I²C speed | Chip supports up to 1 MHz. Use 100 kHz over the cable (the package's default). ESPHome's ESP32 default is 50 kHz unless `frequency:` is set | datasheet I²C timing; ESPHome `i2c` |
| Chip orientation | Pads 1–4 (VDD5V, VDD3V3, OUT, GND) face the connector end. Board fits the tip components-first, facing the dial | board layout; [gauge tip](../gauge-tip/README.md#assembly) |

## Registers

| Register | Address | Use |
|---|---|---|
| RAW ANGLE | 0x0C–0x0D | Unscaled 12-bit angle. The [dial tables](calibration.md) assume this, × 360 / 4096 |
| ANGLE | 0x0E–0x0F | Scaled by ZPOS/MPOS/MANG, 10-LSB hysteresis at the limits |
| STATUS | 0x0B | Bit 5 MD (magnet detected), bit 4 ML (too weak), bit 3 MH (too strong) |
| AGC | 0x1A | Gain, 0–128 in 3.3 V mode. Best near the middle; the air gap sets it |
| MAGNITUDE | 0x1B–0x1C | Field magnitude |
| CONF | 0x07–0x08 | Watchdog, fast-filter threshold, slow filter, PWM, output stage, hysteresis, power mode. The datasheet says read-modify-write: blank bits may hold factory settings |
| ZPOS / MPOS / MANG | 0x01–0x06 | Start, stop and maximum angle. Writable without burning; lost at power-off |

Field at the chip: 30–90 mT for specified performance. The gauge and the printed tip set the air gap; firmware can only report it through STATUS and AGC.

## Timing and power

| Item | Value | Source |
|---|---|---|
| Power-up | Up to 10 ms (maximum power-up time) after the supply is up; wait that long before talking to it | datasheet Figure 10, T_PU |
| Settling | 2.2 ms with the 16× slow filter. Low-power modes force 16× | datasheet Figures 10 and 22 |
| Polling in low-power modes | LPM1 5 ms, LPM2 20 ms, LPM3 100 ms: a fresh angle can take that long | datasheet Figure 6 |
| Supply current, maximum | 6.5 mA normal (an unprogrammed chip starts here until PM is written), 3.4 mA LPM1, 1.8 mA LPM2, 1.5 mA LPM3 | datasheet Figure 6 |

The standard package keeps the sensor on the 3.3 V rail. Battery mode (`propane-monitor-battery.yaml`) switches it off while the ESP32 sleeps: board pin 2 (3V3) is wired to a GPIO (`propane_sensor_power_gpio`, GPIO7 by default) instead, and the GPIO powers the sensor directly. How, and why:

- **High side.** The GPIO feeds 3V3. Switching ground instead would leave 3V3 and the pull-ups connected while the chip's ground floats.
- **Current.** At most about 8 mA: 6.5 mA for the chip plus 0.7 mA through each 4.7 kΩ pull-up while its line is low. The package sets the strongest drive (`GPIO_DRIVE_CAP_3`). Check for 3.0–3.6 V between board pins 2 and 1 while the device is awake.
- **On.** An `on_boot` lambda at priority 1100 drives the pin high and waits 20 ms, before the I²C bus (priority 1000) and the sensor (600) set up. It uses ESP-IDF calls because ESPHome's `gpio` components set up later. The pin is also an internal `gpio` switch with `restore_mode: ALWAYS_ON`, which keeps it high when it sets up and makes ESPHome check it: a pin used twice (say, also as SDA) or a strapping pin is reported at validation. The early start matters: the I²C bus's `setup()` always runs a bus recovery that enables both internal pull-ups and clocks SCL, even with `sda_pullup_enabled` and `scl_pullup_enabled` set to `false`, and that would back-feed an unpowered sensor through its pull-ups.
- **Off.** Just before `deep_sleep.enter`, `component.suspend` stops polling the sensor (failed reads from an unpowered sensor would turn on Sensor problem while Home Assistant is still connected; `deep_sleep` runs `on_shutdown` before it disconnects the API). Then `switch.turn_off` drives the pin low and `gpio_hold_en` holds it low through deep sleep. The next wake releases the hold first.
- **Which pin.** On the ESP32-S3, `gpio_hold_en` only lasts through deep sleep on the RTC pins, GPIO0–21, and the USB pins 19 and 20 can't hold low. So the pin must be GPIO1–21 except 3 (strapping), 19 and 20, and a compile-time check enforces that.
- **While the sensor is off**, nothing may drive SDA or SCL high: the board's 4.7 kΩ pull-ups would back-feed its supply. In deep sleep the ESP32's I²C pins are released. Measure the sleep current on real hardware.

## ESPHome `as5600` behaviour

Checked against ESPHome 2026.9.1 and 2026.10.2 source; the two behave the same here.

1. **Power before setup.** `setup()` reads STATUS once and marks the component failed, with no retry, if there's no answer. Its setup priority is 600, the same as `on_boot`'s default. A switched supply must be on, plus up to 10 ms, before then; turning it on before the I²C bus sets up (priority 1000) also avoids back-feeding during bus recovery ([above](#timing-and-power)). The `delay:` action doesn't block other components' setup; a blocking `lambda: "delay(20);"` does.
2. **Setup rewrites the chip every boot.** It writes CONF (built from zero, not read-modify-write), ZPOS and MPOS/MANG, and never burns OTP.
3. **Which angle, in what unit.** The main sensor reads ANGLE (0x0E). With no start or end position set, that equals RAW ANGLE except for hysteresis at the limits. The `raw_position:` sub-sensor reads RAW ANGLE (0x0C) directly. Both publish counts, 0–4095, not degrees: convert with `x * as5600::RAW_TO_DEGREES` (360 / 4096) before using the dial tables. Setting `unit_of_measurement: "°"` doesn't convert anything.
4. **Failed reads.** If either angle read fails, neither the angle nor `raw_position` publishes. The `status`, `gain` and `magnitude` sub-sensors publish first and don't check their reads, so a failed read publishes 0. A config that reports from `on_value` needs a timeout path.
5. **A missing magnet still publishes an angle.** The `status` sub-sensor reports STATUS bits 5–3 as a number: 4 = detected and good, 6 = detected but weak, 5 = detected but too strong, 2 = not detected (ML set: gain at maximum), 0 = nothing or a failed read. On a gauge it can't tell a weak magnet from none: on the author's board it reads 2 both on the dial (angle following the dial, magnitude about 100) and off it (magnitude 0–4, angle wandering). Use the `magnitude` sub-sensor for "no magnet", and MH (`s & 1`) for too strong.
6. **NaN through `clamp`.** With a finite `min_value` and the default `ignore_out_of_range: false`, `clamp` turns NaN into `min_value`, so publishing NaN through the percentage sensor reports the lowest percentage, not unknown. With `ignore_out_of_range: true` it drops the value instead. Publish unknown on a path without `clamp`.

## How the configuration works

`esphome/propane-monitor.yaml`:

- **Angle:** the `as5600` sensor, read every second, converted to degrees, then the median of 10 readings. It's sent when it moves 0.5° or more, otherwise every 5 minutes. The median is safe only because a fitted sensor never reads near the 0°/360° wrap.
- **Tank level:** a template sensor with `update_interval: never`, recomputed when the angle, dial type, angle offset or sensor problem changes. Its lambda holds the dial tables, with Custom's taken from the `propane_custom_table` substitution at compile time (a table without two or more marks, percent and angle both rising, gives unknown), and does the [angle to percent](calibration.md#angle-to-percent) conversion on angle + offset, wrapped into 0–360° (`fmod`), so offsets up to ±180° work across the 0/360 point. It publishes nothing before the first angle, and unknown (NaN, no `clamp`) while there's a sensor problem. The same lambda also publishes **Tank level live** from **Angle live**, a template sensor set from every raw read in the angle sensor's `on_raw_value` (no median, `delta: 0.5`, above the few counts of noise at rest), unknown while the magnitude is below the threshold, whose `on_value` re-runs Tank level. Going to or from unknown passes the delta filter, so removing or refitting the sensor re-runs Tank level live at once even when the angle hasn't moved. Because Tank level now runs on every live change, it has its own `or: [throttle: 5min, delta: 0.05]` so unchanged values aren't re-sent.
- **Sensor problem** (internal, not sent to Home Assistant; while it's on, Tank level is unknown): on when the `as5600` component failed at boot, no angle has been read for 30 s, the magnitude's raw value (read every second) is below `propane_magnet_min_magnitude` (50), or the status has MH set (item 5). A single `delayed_on_off` filter turns it on after 3 s and off after 5 s, so a brief dip is ignored and it doesn't flicker while the sensor is seated. (Separate `delayed_on` and `delayed_off` filters in a row could let it clear while a new fault waited out its 3 s.) The angle sensor's first filter drops any read whose magnitude (published just before the angle in the same update, and copied to the `propane_magnitude_raw` global because the filter can't refer to its own sub-sensor) is below the threshold, so the median only ever holds reads taken with the magnet present and there's nothing to wait out when the problem clears. The same filter keeps consecutive reads continuous across 0°/360° (359.9° then 0.1° becomes 360.1°), and a filter after the median wraps the result back into 0–360°. ESPHome's median of an even window is the mean of the two middle values, so reads split across that point, which a sensor turned on the dial can produce, would otherwise give about 180°. `esphome/tests/tank_level_test.py` runs these two filters around the same median. Tank level live doesn't wait: it's unknown only while the magnitude's latest raw value is below the threshold.
- **Dial type and Angle offset:** as in [Target](#target). The dial type is stored as its position in the options list, so new dial types go at the end.
- **Restart button:** the sensor is only set up at boot (item 1), so a sensor connected later needs a restart.

## Reading cycle

`esphome/propane-monitor-battery.yaml`. Wake every 8 h, take 10 samples 1 s apart and publish the median: propane levels move slowly, and the radio dominates the power budget.

- A script started from `on_boot` waits until Home Assistant is connected and there's a tank level or a sensor problem (at most 60 s), waits 5 s more, then calls `deep_sleep.enter`. There's no `run_duration`. The wait uses `api.connected` with `state_subscription_only: true`: by default any API client counts, including a log viewer, which would let the device sleep before Home Assistant connects.
- `wifi: fast_connect: true`: from the second boot, ESPHome connects straight to the BSSID and channel saved after the last successful connection (in flash on ESP32, rewritten only when it changes), and falls back to scanning if that fails. The first boot after flashing still scans, so it also picks the strongest access point on a network with several.
- `deep_sleep: sleep_duration` counts from sleep entry, so a long wake pushes later readings back.
- `deep_sleep: run_duration`, if you add one, isn't a hard cap: it's a software timer scheduled when deep sleep sets up. Blocking code, `deep_sleep.prevent` and wake-pin conditions can hold it off, and shutdown can add up to 5 s.
- A wake that can't read the sensor still reports Tank level as unknown, so a dead sensor isn't mistaken for a dead device.
- The sensor is powered only while the ESP32 is awake ([timing and power](#timing-and-power)). Asleep, the remaining draw is the ESP32 board's own sleep current.
- With long sleeps there's no window for over-the-air updates or fitting the tip. The device stays awake for 15 minutes after any start that isn't a timed wake (power-on, reset, flashing), and while a Home Assistant toggle helper (`input_boolean.propane_monitor_setup_mode` by default) is on; it reads the helper on each wake.
- `api:` and `wifi:` `reboot_timeout` are set to 0 so that a missing Wi-Fi or Home Assistant doesn't reboot the device into another 15-minute window.
