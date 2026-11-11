# Troubleshooting

The entities named here are the ones the [ESPHome configuration](../esphome/README.md#entities) creates. The angle, magnitude, magnet status and gain are under Diagnostic on the device's page in Home Assistant.

## Tank level shows unknown

Tank level shows unknown when the sensor wasn't found at boot, stopped answering for 30 s, or the magnetic field is missing (Magnitude below 50) or too strong. It comes back about 5 s after the sensor is seen again, at the last good reading, and follows the dial from the next median. **Tank level live** comes back as soon as the magnet is seen. It's also unknown for about 10 s after every restart, until the first reading. Check Magnitude and the device log, then the sections below. To be told about it, use a Home Assistant automation on Tank level being unknown for 10 minutes.

## The sensor isn't found (nothing at 0x36, or the AS5600 is marked failed at boot)

- Measure 3.0–3.6 V between board pins 2 (3V3) and 1 (GND) with everything connected. In battery mode pin 2 is powered from GPIO7, and only while the device is awake.
- Check the ESP32-S3 end: board pin 3 (SDA) to GPIO8, pin 4 (SCL) to GPIO9, or the pins you set in `propane_sda_pin` and `propane_scl_pin`.
- Make sure the plug is fully seated in the board's connector.
- Generic module: check the wires are soldered to VCC, GND, SDA and SCL, and that DIR is tied to VCC. If the module has no pull-up resistors on SDA and SCL, add 4.7 kΩ from each to VCC ([module-cap/](../module-cap/README.md#wiring)).
- ESPHome only sets up the sensor at boot. After fixing the wiring or plugging the sensor in, press **Restart**.
- Battery mode: check board pin 2 goes to GPIO7 (or the pin set in `propane_sensor_power_gpio`), not 3.3 V or another pin. If you changed how the sensor is powered, the power has to be on at least 10 ms before ESPHome sets up the sensor, and should be on before the I²C bus starts ([firmware notes](firmware-notes.md#timing-and-power)).

## Magnet status

**Magnitude** is the field strength the sensor measures, and it's what tells a missing magnet from a weak one. With the author's board in the gauge tip on a dial it reads about 100; with no magnet, 0 to 4. Below 50 (`propane_magnet_min_magnitude`), Tank level shows unknown. If yours reads below 50 with the sensor clipped on, it isn't seated, or your housing holds the chip farther from the magnet: lower `propane_magnet_min_magnitude` to about half your on-dial reading, as long as that's still well above 4.

ESPHome's `status` value for the AS5600:

| Value | Meaning | What to do |
|---|---|---|
| 4 | Magnet detected, field in range | Good |
| 6 | Magnet detected, field weak | Fine if Magnitude is above 50 |
| 5 | Magnet detected, field too strong | Readings may stick, so Tank level shows unknown. The sensor is closer to the magnet than intended: check the tip and dial |
| 2 | The chip calls the field too weak to count as detected | Common on a gauge: the magnet behind the dial is weak. Fine if Magnitude is above 50 and the angle follows the dial. With the sensor off the dial it stays 2, so check Magnitude |
| 0 | Nothing, or the read failed | See "The sensor isn't found" |

**Gain** (0–128 with a 3.3 V supply) is how hard the chip boosts the signal. At 128, the maximum, it's boosting all it can, which is normal with a gauge's weak magnet as long as Magnitude is above 50.

## The percentage doesn't match the dial

- Check the dial type: compare the marks printed on your dial with [the table](calibration.md#pick-your-dial-type), and pick it in **Dial type**.
- Check the tip is fully clipped on and not rotated on the dial.
- If the percentage falls as the tank fills, the angle runs the wrong way: on a generic module, DIR isn't tied to VCC.
- Generic module: if Angle live is about 90°, 180° or 270° away from the [table](calibration.md#tables) angle for the mark the pointer is on, the module is turned in its housing: turn it, or set **Angle offset** to cancel the difference ([module-cap/ → Assembly](../module-cap/README.md#assembly)).
- If it's off by about the same amount at every mark, adjust **Angle offset** ([calibration](calibration.md#in-the-firmware)).
- A reading stuck at the lowest or highest percentage means the angle is outside the table's range: the dial type is wrong or the tip isn't seated.
- Angles near 0° or 360° mean the sensor isn't reading the dial's magnet in the expected frame ([the angle](calibration.md#the-angle)).

## Readings drop out over a long cable

- Lower the I²C speed: set the `propane_i2c_frequency` substitution to `50kHz`. The configuration uses 100 kHz, the recommended maximum over a cable.
- The board has 4.7 kΩ pull-ups, and the configuration turns the ESP32's internal ones off. If your ESP32 board adds its own, the combined value is lower. Keep it at 1 kΩ or more: the sensor and the ESP32 both have to pull that current down to a low.
- Check the cable isn't longer than the bus allows, and the options for longer runs: [build guide → How long can the cable be?](build-guide.md#how-long-can-the-cable-be)

## Battery mode

- **Readings only change every 8 hours, and Wi-Fi updates don't reach the device.** That's expected: it's asleep between readings, and Home Assistant keeps showing the last ones. To keep it awake for fitting the tip or an update, turn on the setup mode helper or power-cycle it ([battery mode](../esphome/README.md#battery-mode)).
- **The entities show unavailable.** The device dropped off without going to sleep cleanly: check its power, Wi-Fi signal and log.
