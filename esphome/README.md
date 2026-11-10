# ESPHome configuration

The firmware for the ESP32-S3: ESPHome YAML that reads the sensor board with ESPHome's built-in `as5600` component and gives Home Assistant the tank level. There's no custom component to install.

| File | What it is |
|---|---|
| `propane-monitor.yaml` | The package: I²C, the sensor, the dial tables and the Home Assistant entities. Always awake, for USB power |
| `propane-monitor-battery.yaml` | Optional second package for battery builds: wakes every 8 hours, reports, sleeps ([battery mode](#battery-mode)) |
| `example.yaml` | A complete device configuration that pulls in the package from GitHub |
| `secrets.yaml.example` | The secrets `example.yaml` expects |
| `tests/` | Build tests and a check that the dial tables match [calibration.md](../docs/calibration.md) |

Status: compiles with ESPHome 2026.9.1 and validates with 2026.10.2. Not yet run on a v4 board.

## Install

You need Home Assistant with the ESPHome Device Builder add-on, or the [ESPHome command line](https://esphome.io/install/). ESPHome 2026.9.1 or later.

1. In ESPHome Device Builder, add a new device, give it a name and choose ESP32-S3. The wizard writes the Wi-Fi, API and OTA sections for you.
2. Edit the new device and add the `packages:` block from [example.yaml](example.yaml) at the end:

   ```yaml
   packages:
     propane_monitor: github://Averyy/r3d-propane-monitor/esphome/propane-monitor.yaml@v4.0
   ```

   If ESPHome lists your exact board, put its ID in `esp32: board:`; otherwise `esp32-s3-devkitc-1` works for most ESP32-S3 boards.
3. Install. The first time has to be over USB, from the computer you're using: plug the ESP32-S3 in and choose that option. After that, updates go over Wi-Fi.
   - Boards with two USB ports: use the one wired to the chip itself, usually marked USB (not UART). The device's log comes out on that port.
   - If the board isn't found or the install stops at "Connecting", put it in download mode: hold BOOT, press and release RESET, then release BOOT, and try again. Press RESET once more when it's done.
4. Home Assistant finds the device: add it under Settings → Devices & services.
5. On the device's page, set **Dial type** to match your dial ([dial types](../docs/calibration.md#pick-your-dial-type)), then carry on with the [build guide](../docs/build-guide.md#7-dry-fit-and-check-the-reading).

With the command line instead: copy `example.yaml` and `secrets.yaml.example` into a folder, rename the second to `secrets.yaml`, fill it in, set the board, and run `esphome run example.yaml`.

Wire the board as in the [wiring table](../README.md#wiring). If your ESP32-S3 board can't use GPIO8 and GPIO9, set other pins in `substitutions:` ([settings](#settings)).

## Entities

| Entity | Shows |
|---|---|
| Tank level | Percent full, from the angle and your dial type. Unknown while Sensor problem is on |
| Sensor problem | On when the sensor wasn't found at boot, stopped answering, or the magnet is missing or too close |
| Dial type | Which [dial table](../docs/calibration.md#tables) to use. Configuration |
| Angle offset | Added to the angle before the conversion, −30° to +30° ([calibration](../docs/calibration.md#in-the-firmware)). Configuration |
| Angle | The magnet's angle in degrees, the median of 10 readings. Diagnostic |
| Magnet status | The AS5600 status code: 4 is good ([meanings](../docs/troubleshooting.md#magnet-status)). Diagnostic |
| Gain | The AS5600's automatic gain, 0–128; best near the middle. Diagnostic |
| Magnitude | Magnetic field strength, raw. Diagnostic, disabled by default |
| Restart | Restarts the device. ESPHome only sets up the sensor at boot, so press it after plugging the sensor in |

The sensor is read every second and the angle is the median of the last 10 readings. It's sent to Home Assistant when it moves by 0.5° or more (about 0.2 %), otherwise every 5 minutes. Dial type and Angle offset are kept across reboots.

## Settings

Set any of these in your configuration's `substitutions:`.

| Substitution | Default | |
|---|---|---|
| `propane_sda_pin` | `GPIO8` | I²C data, board pin 3 |
| `propane_scl_pin` | `GPIO9` | I²C clock, board pin 4 |
| `propane_i2c_frequency` | `100kHz` | Lower it (for example `50kHz`) if readings drop out over a long cable |
| `propane_sleep_duration` | `8h` | Battery mode: time asleep between readings |
| `propane_setup_window` | `15min` | Battery mode: time awake after power-on, reset or flashing |
| `propane_setup_mode_entity` | `input_boolean.propane_monitor_setup_mode` | Battery mode: the Home Assistant helper that keeps the device awake |
| `propane_sensor_power_gpio` | `7` | Battery mode: the GPIO number that powers the sensor (board pin 2). GPIO1–21, except 3, 19 and 20 |

The sensor is read once a second; the Sensor problem timings and battery mode's waits depend on that, so it isn't a setting.

**Other I²C devices.** The package has its own I²C bus with the ID `propane_i2c`. To add another sensor, either give it `i2c_id: propane_i2c` (same pins), or add a second bus as a list item:

```yaml
i2c:
  - id: my_bus
    sda: GPIO4
    scl: GPIO5
```

An `i2c:` section without the dash replaces the package's bus, and validation stops with "Couldn't find ID 'propane_i2c'".

## Battery mode

Wire board pin 2 (3V3) to **GPIO7** instead of 3.3 V; the other three pins stay as in the [wiring table](../README.md#wiring). The ESP32 then powers the sensor from that pin and switches it off while it sleeps. A Qwiic port's 3.3 V pin can't do this, so use a cable with jumper ends.

Then add the second package under the first:

```yaml
packages:
  propane_monitor: github://Averyy/r3d-propane-monitor/esphome/propane-monitor.yaml@v4.0
  propane_monitor_battery: github://Averyy/r3d-propane-monitor/esphome/propane-monitor-battery.yaml@v4.0
```

The device then wakes every 8 hours, takes 10 readings a second apart, sends the median to Home Assistant and goes back to deep sleep. It waits up to a minute for Home Assistant on each wake; without it, it sleeps anyway. While it sleeps, Home Assistant keeps showing the last readings. If the entities go unavailable, the device didn't go to sleep cleanly: it lost Wi-Fi, lost power or crashed.

A sleeping device can't take updates or show live readings for fitting the tip, so it stays awake:

- **for 15 minutes after power-on, a reset or flashing.** Timed wakes don't count.
- **while setup mode is on.** Create the helper before you need it: in Home Assistant, Settings → Devices & services → Helpers → Create helper → Toggle, named "Propane monitor setup mode" (entity `input_boolean.propane_monitor_setup_mode`). The device checks it on each wake, so turning it on takes effect at the next wake, up to 8 hours later; power-cycling the device starts its 15-minute window straight away. Turn it off when you're done and the device goes back to sleep.

Power: the sensor draws nothing while the ESP32 sleeps, and each wake takes about 20 seconds on Wi-Fi, so three a day cost only about 2 mAh. What's left is your ESP32-S3 board's own sleep current, which depends on its regulator, LEDs and USB chip: measure it before sizing a battery. If board pin 2 stays on 3.3 V, battery mode still works, but the sensor stays powered and draws about 1.5 mA (36 mAh a day). How the switching works: [firmware notes](../docs/firmware-notes.md#timing-and-power).

Battery mode compiles but hasn't been run on hardware yet.

## Updating

`@v4.0` pins the package to a release, so your device only changes when you change that tag and install again. Releases are listed in the [changelog](../CHANGELOG.md).

## Changing the configuration

To change more than the settings above, copy the package next to your device configuration and include it with `!include propane-monitor.yaml` instead of the GitHub line. How it works, and what ESPHome's `as5600` component does and doesn't do: [firmware notes](../docs/firmware-notes.md).

Checks to run after a change:

```sh
esphome config tests/always-on.yaml
esphome config tests/battery.yaml
python3 tests/tank_level_test.py
```

## Licence

GPLv3, see [LICENSE](LICENSE): the lambdas compile together with ESPHome's GPLv3 C++ runtime. The rest of the repository is CC BY-NC-SA 4.0.
