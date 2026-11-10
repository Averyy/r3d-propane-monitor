# Troubleshooting

The entities named here are the ones the [ESPHome configuration](../esphome/README.md#entities) creates. The angle, magnet status and gain are under Diagnostic on the device's page in Home Assistant.

## Sensor problem is on

It turns on when the sensor wasn't found at boot, stopped answering for 30 s, or can't see the magnet properly. The tank level shows unknown meanwhile. Check the magnet status and the device log, then the sections below.

## The sensor isn't found (nothing at 0x36, or the AS5600 is marked failed at boot)

- Measure 3.0–3.6 V between board pins 2 (3V3) and 1 (GND) with everything connected. In battery mode pin 2 is powered from GPIO7, and only while the device is awake.
- Check the ESP32-S3 end: board pin 3 (SDA) to GPIO8, pin 4 (SCL) to GPIO9, or the pins you set in `propane_sda_pin` and `propane_scl_pin`.
- Make sure the plug is fully seated in the board's connector.
- ESPHome only sets up the sensor at boot. After fixing the wiring or plugging the sensor in, press **Restart**.
- Battery mode: check board pin 2 goes to GPIO7 (or the pin set in `propane_sensor_power_gpio`), not 3.3 V or another pin. If you changed how the sensor is powered, the power has to be on at least 10 ms before ESPHome sets up the sensor, and should be on before the I²C bus starts ([firmware notes](firmware-notes.md#timing-and-power)).

## Magnet status

ESPHome's `status` value for the AS5600:

| Value | Meaning | What to do |
|---|---|---|
| 4 | Magnet detected, field in range | Good |
| 6 | Magnet detected, field weak | Usually still reads. Check the tip is fully clipped on and seated |
| 5 | Magnet detected, field too strong | Readings may stick, so Sensor problem turns on. The sensor is closer to the magnet than intended: check the tip and dial |
| 2 | No magnet detected | Tip not on the dial, or not seated |
| 0 | Nothing, or the read failed | See "The sensor isn't found" |

The **Gain** value (0–128 in this board's 3.3 V mode) is best near the middle of its range. Far from the middle usually means the gap between the sensor and the magnet is off; temperature and an ageing magnet move it too.

## The percentage doesn't match the dial

- Check the dial type: compare the marks printed on your dial with [the table](calibration.md#pick-your-dial-type), and pick it in **Dial type**.
- Check the tip is fully clipped on and not rotated on the dial.
- If it's off by about the same amount at every mark, adjust **Angle offset** ([calibration](calibration.md#in-the-firmware)).
- A reading stuck at the lowest or highest percentage means the angle is outside the table's range: the dial type is wrong or the tip isn't seated.
- Angles near 0° or 360° mean the sensor isn't reading the dial's magnet in the expected frame ([the angle](calibration.md#the-angle)).

## Readings drop out over a long cable

- Lower the I²C speed: set the `propane_i2c_frequency` substitution to `50kHz`. The configuration uses 100 kHz, the recommended maximum over a cable.
- The board has 4.7 kΩ pull-ups, and the configuration turns the ESP32's internal ones off. If your ESP32 board adds its own, the combined value is lower; check it's within what your ESP32 pins can sink.

## Battery mode

- **Readings only change every 8 hours, and Wi-Fi updates don't reach the device.** That's expected: it's asleep between readings, and Home Assistant keeps showing the last ones. To keep it awake for fitting the tip or an update, turn on the setup mode helper or power-cycle it ([battery mode](../esphome/README.md#battery-mode)).
- **The entities show unavailable.** The device dropped off without going to sleep cleanly: check its power, Wi-Fi signal and log.
