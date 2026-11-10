# Build guide

From nothing to a tank reading in Home Assistant. Each step links to the detail.

## 1. Check your gauge

You need a Remote Ready (R3D) dial on your tank gauge: the gauge tip clips onto that dial and the sensor reads the magnet behind it. Find your dial type from the marks printed on it: [dial types](calibration.md#pick-your-dial-type).

## 2. Order the boards

Order from JLCPCB with the parts fitted, following [sensor board → Ordering](../sensor-board/README.md#ordering). The minimum order is 5 boards ([cost](../sensor-board/README.md#cost)). No soldering is needed.

Or use a generic AS5600 module instead of the custom board: [module-cap/](../module-cap/README.md) covers its housing, preparation and wiring. The steps below still apply, with the module housing in place of the gauge tip.

## 3. Print the gauge tip

Choose a version ([gauge tip](../gauge-tip/README.md)):

- **Two-piece:** the tip plus a cable piece that snaps in behind the board and anchors the cable. Takes cables up to 3.4 mm thick, which a generic Qwiic cable is.
- **One-piece:** an open well behind the board that you fill with glue. Takes any cable.

Print in ASA, ABS or TPU so it stands up to the weather. Orientation and supports: [gauge tip → Printing](../gauge-tip/README.md#printing).

## 4. Get a cable

Any generic Qwiic / STEMMA QT cable works: the board takes its 4-pin JST SH plug (1.00 mm pitch). Use one with an SH plug at both ends if your ESP32-S3 board has a Qwiic port, or SH to jumper wires for header pins. Tested with a 1.22 m cable. Cable size for the two-piece tip: [gauge tip → Cable](../gauge-tip/README.md#cable).

## 5. Wire the ESP32

Use an ESP32-S3 board that runs ESPHome. Wire by pin number as in the [wiring table](../README.md#wiring): GND, 3.3 V, SDA to GPIO8, SCL to GPIO9. Use 3.3 V only: the sensor can be permanently damaged above 4.0 V, and some Qwiic / STEMMA QT ports supply 5 V. For a battery build, wire board pin 2 to GPIO7 instead of 3.3 V ([battery mode](../esphome/README.md#battery-mode)).

## 6. Flash ESPHome

Create a device in ESPHome, add the package from [esphome/](../esphome/README.md#install) and install it over USB. Then add the device to Home Assistant and set **Dial type** to your dial.

The standard configuration stays awake and shows a change in the angle within about 20 seconds, which the next step needs. For a battery build, which sleeps between readings, the [battery mode](../esphome/README.md#battery-mode) section says how to keep it awake while you fit the tip.

## 7. Dry-fit and check the reading

1. Plug the cable into the board and slide the board into the gauge tip, components towards the dial ([gauge tip → Assembly](../gauge-tip/README.md#assembly)). Don't glue anything yet.
2. Clip the gauge tip onto the dial.
3. In Home Assistant, check that:
   - **Sensor problem** is off and **Magnet status** is 4 (or 6, weak but usually fine) ([troubleshooting](troubleshooting.md#magnet-status));
   - **Angle** is between about 37° and 322° ([the angle](calibration.md#the-angle));
   - **Tank level** matches the dial. If it's off by about the same amount at every mark, adjust **Angle offset** ([calibration](calibration.md#in-the-firmware)); no reflashing needed.

If any of these is off, see [troubleshooting](troubleshooting.md).

## 8. Seal and refit

Take the gauge tip off and seal it with waterproof, PCB-safe glue: in the two-piece's glue grooves, or by filling the one-piece's well ([gauge tip → Assembly](../gauge-tip/README.md#assembly)). Once sealed, the board can't be taken out. Let it cure, clip it back onto the dial and check the reading again.
