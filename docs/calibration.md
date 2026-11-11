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
| Custom | Any: your own table, set in the device configuration ([measuring your own table](#measuring-your-own-table)) |

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

| % | Jr/Sr Horizontal | Jr/Sr Vertical | Jr/Sr Fractional | 8" Magnetel | 4" Magnetel | Drop-In |
|---|---|---|---|---|---|---|
| 0 | | 37 (E) | 37 (E) | | | |
| 3 | | | | 37 | | |
| 5 | 37 | | | 45 | 37 | |
| 10 | 63 | 57 | | 63 | 63 | 37 |
| 20 | 105 | 74 | | 95 | 105 | 68 |
| 25 | | | 108 (¼) | | | |
| 30 | 134 | 111 | | 126 | 134 | 99 |
| 40 | 160 | 148 | | 158 | 160 | 130 |
| 50 | 183 | 185 | 179 (½) | 189 | 183 | 161 |
| 60 | 200 | 222 | | 221 | 200 | 192 |
| 70 | 229 | 259 | | 252 | 229 | 223 |
| 75 | | | 250 (¾) | | | |
| 80 | 258 | 302 | | 274 | 258 | 254 |
| 90 | 296 | | | 296 | 296 | 285 |
| 94 | | | | | | 322 |
| 95 | 322 | | | 309 | 322 | |
| 97 | | | | 322 | | |
| 100 | | 322 (F) | 322 (F) | | | |

Every table runs from 37° at its lowest mark to 322° at its highest; they differ in how the marks are spaced. The tables were measured on a live device, so uneven spacing between marks is real. The 4" Magnetel values are the same as Jr/Sr Horizontal.

## Angle to percent

1. Sort the table's points by percent.
2. At or below the lowest point's angle, report the lowest percent; at or above the highest, report the highest percent. Don't extrapolate: a 5–95 % table never reports below 5 % or above 95 %.
3. Otherwise interpolate linearly between the two neighbouring points.
4. For litres: percent / 100 × tank capacity.

### In the firmware

The [ESPHome configuration](../esphome/README.md) does this conversion on the device, on the angle plus an offset. In Home Assistant:

- **Dial type** picks the table. It starts as Jr/Sr Horizontal. **Custom** uses your own table ([below](#measuring-your-own-table)).
- **Angle offset** (−180° to +180°) is added to the angle before the conversion, and the result wrapped into 0–360°. It's for a tip that sits slightly rotated on the dial, or a sensor that's turned: a generic module fitted a quarter turn out reads 90° high or low everywhere, and −90° or +90° fixes it. If the percentage reads low at every mark, raise it; if high, lower it. About 3° is 1 % on a Jr/Sr Horizontal dial.

Both are kept across reboots, with no reflashing. The tables above mirror the ones in `esphome/propane-monitor.yaml`.

## Measuring your own table

If no table matches your dial, or you want readings that match your own gauge more closely, use the Custom dial type:

1. Set **Angle offset** to 0.
2. Each time the dial pointer sits on a mark, note the **Angle live** reading (under Diagnostic in Home Assistant). It updates every second.
3. In your device configuration, set `propane_custom_table` to those marks as `{percent, angle}` pairs, lowest first, and install it again:

   ```yaml
   substitutions:
     propane_custom_table: "{5, 37}, {10, 63}, {20, 105}, {30, 134}, {40, 160}, {50, 183}, {60, 200}, {70, 229}, {80, 258}, {90, 296}, {95, 322}"
   ```

4. Set **Dial type** to **Custom**, and check **Tank level live** against the dial.

The tank level is interpolated between your marks, as for the other tables. Use any marks your dial has (3 %, 94 %, ¼ as 25, and so on). It needs at least two, with both the percent and the angle rising from each mark to the next; otherwise Tank level shows as unknown and the device log says so. Without the setting, Custom uses the Jr/Sr Horizontal table shown above.

Please share your table too, so it can become a named dial type: [CONTRIBUTING](../CONTRIBUTING.md#share-a-dial-table).
