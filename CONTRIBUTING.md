# Contributing

Thanks for helping. Issues and pull requests are welcome.

## Share a dial table

The most useful contribution is an angle table for a dial type that isn't in [docs/calibration.md](docs/calibration.md), or a corrected one. Open a **Dial table** issue and give the printed marks, the angle the sensor reported at each mark, and a photo of the dial face if you can.

## Report a problem

Open a **Problem report** issue. Include the board revision, gauge tip version, dial type, ESPHome version, whether you use battery mode, and the tank level, angle, magnet status and gain values Home Assistant shows. [Troubleshooting](docs/troubleshooting.md) covers the common cases.

## Change files

- Docs and the ESPHome configuration: send a pull request. For `esphome/` changes, run the checks in [esphome/README.md](esphome/README.md#changing-the-configuration); CI runs them too. A dial table change goes in both `esphome/propane-monitor.yaml` and `docs/calibration.md`.
- The board's EasyEDA project and the gauge tip's CAD source aren't published, so for board or tip changes, open an issue describing the change.
- Wiring is documented by pin number only (1 GND, 2 3V3, 3 SDA, 4 SCL), never by wire colour.

## Licence of contributions

By contributing you agree that your contribution is licensed like the files it changes: CC BY-NC-SA 4.0 for the board, gauge tip and docs, and GPLv3 for anything under `esphome/`.
