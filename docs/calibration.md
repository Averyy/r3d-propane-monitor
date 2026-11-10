# Dial types and calibration

The sensor reads the angle of the magnet behind the gauge dial. The firmware turns that angle into a tank percentage using a table for your dial type. This page lists the dial types, what the angle means, and how the conversion works.

## Pick your dial type

Match the marks printed on your dial.

| Dial type | Printed marks |
|---|---|
| Jr/Sr Horizontal | 5 % to 95 % |
| Jr/Sr Vertical | 10 % to 80 %, plus E and F |
| Jr/Sr Fractional | E, ¼, ½, ¾, F |
| 8" Magnetel | 3 % to 97 % |
| 4" Magnetel | 5 % to 95 % |
| Drop-In | 10 % to 94 % |
| Default | A measured curve, 0 % to 95 % |

Jr/Sr means the Junior and Senior gauge sizes.

## The angle

Higher angle means more propane. As the tank empties the pointer turns toward E and the angle goes down. On a Jr/Sr Horizontal dial:

| Dial | Angle |
|---|---|
| 5 % (lowest mark) | about 37° |
| 50 % | about 183° |
| 95 % (highest mark) | about 322° |

The sweep is about 285°. The 0°/360° wrap sits in the dead zone below E and above F, so a fitted sensor never reads near 0° or 360°.

The tables were measured on the author's earlier mount in this frame:

- angle = raw angle × 360 / 4096, no zero offset;
- DIR high (counter-clockwise), as on the v4 board;
- chip power and ground edge facing the cable.

The v4 board in the gauge tip is designed to hold the chip in the same frame, so the tables should apply without an offset. That hasn't been checked on a built v4 yet. A small difference shows up as the same shift at every mark, which the [angle offset](#in-the-firmware) corrects. If you change the chip's orientation, DIR or zero offset, measure your own table.

## Tables

Angle in degrees for each printed mark.

| % | Default | Jr/Sr Horizontal | Jr/Sr Vertical | Jr/Sr Fractional | 8" Magnetel | 4" Magnetel | Drop-In |
|---|---|---|---|---|---|---|---|
| 0 | 35.288 | | 37 (E) | 37 (E) | | | |
| 3 | | | | | 37 | | |
| 5 | 43.374 | 37 | | | 45 | 37 | |
| 10 | 67.675 | 63 | 57 | | 63 | 63 | 37 |
| 15 | 89.824 | | | | | | |
| 20 | 107.753 | 105 | 74 | | 95 | 105 | 68 |
| 25 | 120.761 | | | 108 (¼) | | | |
| 30 | 135.043 | 134 | 111 | | 126 | 134 | 99 |
| 40 | 160.532 | 160 | 148 | | 158 | 160 | 130 |
| 50 | 181.977 | 183 | 185 | 179 (½) | 189 | 183 | 161 |
| 60 | 202.28 | 200 | 222 | | 221 | 200 | 192 |
| 70 | 226.538 | 229 | 259 | | 252 | 229 | 223 |
| 75 | | | | 250 (¾) | | | |
| 80 | 253.74 | 258 | 302 | | 274 | 258 | 254 |
| 90 | 296.586 | 296 | | | 296 | 296 | 285 |
| 94 | | | | | | | 322 |
| 95 | 323.964 | 322 | | | 309 | 322 | |
| 97 | | | | | 322 | | |
| 100 | | | 322 (F) | 322 (F) | | | |

Every table except Default runs from 37° at its lowest mark to 322° at its highest; they differ in how the marks are spaced. The tables were measured on a live device, so uneven spacing between marks is real. The 4" Magnetel values are the same as Jr/Sr Horizontal.

## Angle to percent

1. Sort the table's points by percent.
2. At or below the lowest point's angle, report the lowest percent; at or above the highest, report the highest percent. Don't extrapolate: a 5–95 % table never reports below 5 % or above 95 %.
3. Otherwise interpolate linearly between the two neighbouring points.
4. For litres: percent / 100 × tank capacity.

### In the firmware

The [ESPHome configuration](../esphome/README.md) does this conversion on the device, on the angle plus an offset. In Home Assistant:

- **Dial type** picks the table. It starts as Default.
- **Angle offset** (−30° to +30°) is added to the angle before the conversion, for a tip that sits slightly rotated on the dial. If the percentage reads low at every mark, raise it; if high, lower it. About 3° is 1 % on a Jr/Sr Horizontal dial.

Both are kept across reboots, with no reflashing. The tables above mirror the ones in `esphome/propane-monitor.yaml`.

## Measuring your own table

With the sensor fitted and the angle offset at 0, note the **Angle** reading (under Diagnostic in Home Assistant) each time the dial pointer sits on a printed mark. Those angle and percent pairs are your table.

To use it, copy `esphome/propane-monitor.yaml` next to your device configuration, add the table to the Tank level lambda and its name to the end of the Dial type options, and include the copy instead of the GitHub package. Please share it too: [CONTRIBUTING](../CONTRIBUTING.md#share-a-dial-table).
