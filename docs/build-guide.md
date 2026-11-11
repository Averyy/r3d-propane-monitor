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

### How long can the cable be?

About 2 m with a typical thin cable, and up to about 4.5 m with a low-capacitance one, with nothing added.

The limit is the cable's capacitance. At 100 kHz, I²C allows the lines 1 µs to rise. With the board's 4.7 kΩ pull-ups, that's about 250 pF for the whole bus, about 230 pF of it for the cable. Thin 4-wire cables are usually 50–100 pF per metre. To check yours, measure the capacitance between SDA and the other three wires twisted together: under about 230 pF is within the I²C spec.

For longer runs (none of these has been tested with this board):

- **Up to about 4–7.5 m:** add 2.2 kΩ pull-ups from SDA and SCL to the sensor's supply at the ESP32 end. Together with the board's 4.7 kΩ that's about 1.5 kΩ, and the limit becomes I²C's maximum of 400 pF on the bus. Use a low-capacitance cable, such as Cat5 or Cat6 with SDA and SCL each paired with a ground wire. On a battery build, connect the pull-ups to GPIO7, not 3.3 V: otherwise they feed the sensor through its SDA and SCL pins while it's switched off. GPIO7 then also carries the pull-up current, so check there's still at least 3.0 V between board pins 2 and 1 while the device is awake.
- **Up to about 30 m:** use a differential I²C extender, one board at each end, joined by an Ethernet cable. SparkFun's QwiicBus EndPoint (PCA9615, two needed) has Qwiic connectors, so the chain is ESP32 → Qwiic cable → EndPoint → Ethernet cable → EndPoint → Qwiic cable → sensor board, with no change to the configuration. It's rated to 30 m (100 ft). Keep both boards on their default 3.3 V power setting: the others put 5 V on the far board's Qwiic connector, which can damage the sensor. The far board needs a weatherproof box. This is for the standard configuration: a battery build's GPIO7 can't power the extender boards as well.
- **Or put the ESP32 at the tank** and keep the cable short. It reports over Wi-Fi, so only power has to reach it: a battery build ([battery mode](../esphome/README.md#battery-mode)) or a power cable.

Past these limits you're outside the I²C spec. Lowering the speed to 50 kHz gives some margin, but test on the real cable and watch **Angle live** for dropouts ([troubleshooting](troubleshooting.md#readings-drop-out-over-a-long-cable)).

## 5. Wire the ESP32

Use an ESP32-S3 board that runs ESPHome. Wire by pin number as in the [wiring table](../README.md#wiring): GND, 3.3 V, SDA to GPIO8, SCL to GPIO9. Use 3.3 V only: the sensor can be permanently damaged above 4.0 V, and some Qwiic / STEMMA QT ports supply 5 V. For a battery build, wire board pin 2 to GPIO7 instead of 3.3 V ([battery mode](../esphome/README.md#battery-mode)).

## 6. Flash ESPHome

Create a device in ESPHome, add the package from [esphome/](../esphome/README.md#install) and install it over USB. Then add the device to Home Assistant and set **Dial type** to your dial.

The standard configuration stays awake and shows a change in the angle within about 20 seconds, which the next step needs. For a battery build, which sleeps between readings, the [battery mode](../esphome/README.md#battery-mode) section says how to keep it awake while you fit the tip.

## 7. Dry-fit and check the reading

1. Plug the cable into the board and slide the board into the gauge tip, components towards the dial ([gauge tip → Assembly](../gauge-tip/README.md#assembly)). Don't glue anything yet.
2. Clip the gauge tip onto the dial.
3. Press **Restart** on the device's page in Home Assistant, or unplug and replug its power. ESPHome only sets up the sensor at boot, so a sensor plugged in after the device started isn't found until then.
4. In Home Assistant, check that:
   - **Tank level** shows a percentage and **Magnitude** is above 50 (about 100 with the author's board). **Magnet status** 2 is common with a gauge's weak magnet ([troubleshooting](troubleshooting.md#magnet-status));
   - **Angle live** is between about 37° and 322° ([the angle](calibration.md#the-angle)). It and **Tank level live** update every second, so use them while fitting; Angle and Tank level take up to 10 seconds;
   - **Tank level live** matches the dial. If it's off by about the same amount at every mark, adjust **Angle offset** ([calibration](calibration.md#in-the-firmware)), with no reflashing. If the marks are off by different amounts, measure a [Custom table](calibration.md#measuring-your-own-table) and install again.

If any of these is off, see [troubleshooting](troubleshooting.md).

## 8. Seal and refit

Take the gauge tip off and seal it with waterproof, PCB-safe glue: in the two-piece's glue grooves, or by filling the one-piece's well ([gauge tip → Assembly](../gauge-tip/README.md#assembly)). Once sealed, the board can't be taken out. Let it cure, clip it back onto the dial and check the reading again.
