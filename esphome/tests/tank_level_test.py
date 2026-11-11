"""Check the Tank level lambda in propane-monitor.yaml against docs/calibration.md.

Compiles the lambda's C++ on the host with stand-ins for the ESPHome objects, then
checks, for every dial type, that it gives the percentage the method in
calibration.md ("Angle to percent") gives from the tables there. This keeps the
YAML and the docs in step and tests the interpolation itself, for both Tank level
(the median angle) and Tank level live (the latest reading).

The Custom dial type's table comes from the propane_custom_table substitution. It is
tested with the package's default, which must be the Jr/Sr Horizontal table, and with
unusable tables, which must give unknown (NaN).

Needs Python 3.10+ and a C++20 compiler (c++, g++ or clang++). Standard library only:
    python3 esphome/tests/tank_level_test.py
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
YAML = ROOT / "esphome" / "propane-monitor.yaml"
DOC = ROOT / "docs" / "calibration.md"
PLACEHOLDER = "${propane_custom_table}"
MAG_PLACEHOLDER = "${propane_magnet_min_magnitude}"

HARNESS = r"""
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <optional>
#include "config.inc"  // MAG_MIN: the package's propane_magnet_min_magnitude
struct FakeSensor { bool has = true; float state = 0; bool has_state() const { return has; } };
struct FakeBinary { bool state = false; };
struct FakeSelect {
  std::optional<size_t> idx;
  std::optional<size_t> active_index() const { return idx; }
};
static FakeSensor angle_s, offset_s;
static FakeBinary problem_b;
static FakeSelect dial_s;
static FakeSensor &id_propane_angle = angle_s;
static FakeSensor &id_propane_angle_offset = offset_s;
static FakeBinary &id_propane_sensor_problem = problem_b;
static FakeSelect &id_propane_dial_type = dial_s;
// Angle live in, Tank level live out (the lambda publishes it).
struct FakeOut { float state = 0; int count = 0; void publish_state(float v) { state = v; count++; } };
static FakeSensor angle_live_s;
static FakeOut level_live_o;
static FakeSensor &id_propane_angle_live = angle_live_s;
static FakeOut &id_propane_tank_level_live = level_live_o;
// The latest Magnitude reading (a global): Tank level live is unknown below the threshold.
static float magnitude_g = 100;
static float &id_propane_magnitude_raw = magnitude_g;
#define ESP_LOGW(tag, ...) ((void) 0)
#define id(x) id_##x
static std::optional<float> level() {
#include "lambda.inc"
}
int main(int argc, char **argv) {
  // "harness <Custom index>": built with an unusable Custom table, so Custom must
  // give unknown (NaN), for Tank level and Tank level live, at every angle.
  if (argc == 2) {
    dial_s.idx = static_cast<size_t>(atoi(argv[1]));
    int fails = 0;
    for (int x = 0; x <= 720; x++) {
      angle_s.state = angle_live_s.state = x * 0.5f;
      auto v = level();
      if (!v || !std::isnan(*v) || !std::isnan(level_live_o.state)) fails++;
    }
    return fails ? 1 : 0;
  }
  if (argc != 3) return 2;
  const unsigned options = static_cast<unsigned>(atoi(argv[2]));
  FILE *f = fopen(argv[1], "r");
  if (!f) return 2;
  // Each case: dial, median angle, offset, its percent, live angle, its percent.
  unsigned idx; double a, off, want, la, lwant; int n = 0, bad = 0;
  while (fscanf(f, "%u %lf %lf %lf %lf %lf", &idx, &a, &off, &want, &la, &lwant) == 6) {
    dial_s.idx = idx; angle_s.state = a; offset_s.state = off; angle_live_s.state = la; n++;
    const int before = level_live_o.count;
    auto got = level();
    // The reference is always a number, so NaN is a failure (fabs(NaN) > x is false).
    if (!got || !std::isfinite(*got) || std::fabs(*got - want) > 1e-3) {
      if (bad++ < 10)
        printf("dial %u, angle %.3f, offset %.1f: want %.4f, got %s%.4f\n", idx, a, off, want,
               got ? "" : "nothing ", got ? *got : 0.f);
    }
    if (level_live_o.count != before + 1 || !std::isfinite(level_live_o.state) ||
        std::fabs(level_live_o.state - lwant) > 1e-3) {
      if (bad++ < 10)
        printf("dial %u, live angle %.3f, offset %.1f: want %.4f, got %.4f\n", idx, la, off, lwant,
               level_live_o.state);
    }
  }
  int edge = 0;
  angle_s.has = false;
  {
    const int before = level_live_o.count;
    if (level().has_value()) { puts("no angle yet: should publish nothing"); edge++; }
    if (level_live_o.count != before + 1) { puts("no median yet: live should still publish"); edge++; }
    // A problem before the first median (say, a battery wake with the sensor off
    // the dial): unknown, so the last reading doesn't stay on show.
    problem_b.state = true;
    { auto v = level(); if (!v || !std::isnan(*v)) { puts("no median yet, sensor problem: should be NaN"); edge++; } }
    problem_b.state = false;
  }
  angle_s.has = true;
  angle_live_s.has = false;
  {
    const int before = level_live_o.count;
    level();
    if (level_live_o.count != before) { puts("no live angle: live should publish nothing"); edge++; }
  }
  angle_live_s.has = true;
  // Sensor problem still on (waiting out its delay) but the magnet is back:
  // Tank level stays unknown, Tank level live already reads.
  problem_b.state = true;
  { auto v = level(); if (!v || !std::isnan(*v)) { puts("sensor problem: should be NaN"); edge++; } }
  if (!std::isfinite(level_live_o.state)) { puts("sensor problem, magnet back: live should read"); edge++; }
  problem_b.state = false;
  // Magnet missing right now: live is unknown at once, at and below the threshold's edge.
  for (float m : {MAG_MIN - 0.5f, 0.0f, NAN}) {
    magnitude_g = m;
    level();
    if (!std::isnan(level_live_o.state)) { printf("magnitude %.1f: live should be NaN\n", m); edge++; }
  }
  magnitude_g = MAG_MIN;
  level();
  if (!std::isfinite(level_live_o.state)) { puts("magnitude at the threshold: live should read"); edge++; }
  magnitude_g = 100;
  // Angle live is unknown while the magnet is missing: live follows.
  angle_live_s.state = NAN;
  level();
  if (!std::isnan(level_live_o.state)) { puts("angle live unknown: live should be NaN"); edge++; }
  angle_live_s.state = 150;
  dial_s.idx = std::nullopt;
  { auto v = level(); if (!v || !std::isnan(*v)) { puts("no dial type: should be NaN"); edge++; } }
  dial_s.idx = options;
  { auto v = level(); if (!v || !std::isnan(*v)) { puts("dial index past the last: should be NaN"); edge++; } }
  printf("%d cases, %d mismatches, %d edge-case failures\n", n, bad, edge);
  return (bad || edge) ? 1 : 0;
}
"""

# Custom tables the lambda must refuse: falling angle, one mark, percent not rising.
BAD_CUSTOM = ["{5, 37}, {10, 30}", "{5, 37}", "{5, 37}, {5, 60}", "{10, 60}, {5, 70}"]


def yaml_parts(text):
    """Pull the Tank level lambda, the Dial type options and the Custom table default out of the YAML."""
    m = re.search(r"id: propane_tank_level\n(?:.*\n)*?    lambda: \|-\n((?:      .*\n|\s*\n)+)", text)
    if not m:
        sys.exit("Tank level lambda not found in propane-monitor.yaml")
    body = "".join(line[6:] + "\n" for line in m.group(1).rstrip().split("\n"))
    if body.count(PLACEHOLDER) != 1:
        sys.exit(f"{PLACEHOLDER} should appear once in the Tank level lambda")
    m = re.search(r"id: propane_dial_type\n(?:.*\n)*?    options:\n((?:      - .*\n)+)", text)
    if not m:
        sys.exit("Dial type options not found in propane-monitor.yaml")
    options = []
    for line in m.group(1).strip("\n").split("\n"):
        value = line.strip()[2:].strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        options.append(value)
    m = re.search(r'^  propane_custom_table: "(.*)"$', text, re.M)
    if not m:
        sys.exit("propane_custom_table substitution not found in propane-monitor.yaml")
    mag = re.search(r'^  propane_magnet_min_magnitude: "([\d.]+)"$', text, re.M)
    if not mag or MAG_PLACEHOLDER not in body:
        sys.exit("propane_magnet_min_magnitude substitution or its use in Tank level not found")
    # Substituted as ESPHome does; the harness also gets it as MAG_MIN for its checks.
    body = body.replace(MAG_PLACEHOLDER, mag.group(1))
    return body, options, m.group(1), float(mag.group(1))


def doc_tables(text):
    """Parse the Tables section of calibration.md into {dial type: [(percent, angle)]}."""
    section = text.split("## Tables", 1)[1].split("\n## ", 1)[0]
    lines = [l for l in section.splitlines() if l.startswith("|")]
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    tables = {name: [] for name in header[1:]}
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        for name, cell in zip(header[1:], cells[1:]):
            if cell:
                tables[name].append((float(cells[0]), float(re.match(r"[\d.]+", cell).group())))
    return {k: sorted(v) for k, v in tables.items()}


def reference(angle, points):
    """calibration.md, "Angle to percent": clamp to the ends, else interpolate."""
    if angle <= points[0][1]:
        return points[0][0]
    if angle >= points[-1][1]:
        return points[-1][0]
    for (p0, a0), (p1, a1) in zip(points, points[1:]):
        if a0 <= angle <= a1:
            return p0 + (angle - a0) * (p1 - p0) / (a1 - a0)
    raise AssertionError("unsorted table")


def build(compiler, tmp, name, body, mag_min):
    """Compile the harness around one version of the lambda; return the binary's path."""
    folder = tmp / name
    folder.mkdir()
    (folder / "lambda.inc").write_text(body)
    (folder / "config.inc").write_text(f"constexpr float MAG_MIN = {mag_min}f;\n")
    (folder / "harness.cpp").write_text(HARNESS)
    subprocess.run([compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror", "-o", str(folder / "harness"),
                    str(folder / "harness.cpp")], check=True)
    return folder / "harness"


def main():
    body, options, custom_default, mag_min = yaml_parts(YAML.read_text(encoding="utf-8"))
    tables = doc_tables(DOC.read_text(encoding="utf-8"))
    # Custom is the last option and has no column in the docs: its table is the
    # propane_custom_table substitution, which starts as Jr/Sr Horizontal.
    if not options or options[-1] != "Custom":
        sys.exit(f"Custom should be the last Dial type option: {options}")
    if sorted(options[:-1]) != sorted(tables):
        sys.exit(f"Dial types differ.\n  YAML: {options[:-1]}\n  docs: {list(tables)}")
    custom = [(float(p), float(a)) for p, a in re.findall(r"\{\s*([\d.]+)\s*,\s*([\d.]+)\s*\}", custom_default)]
    if custom != tables["Jr/Sr Horizontal"]:
        sys.exit(f"propane_custom_table's default should be the Jr/Sr Horizontal table: {custom_default}")
    tables["Custom"] = custom

    cases = []
    for index, name in enumerate(options):
        points = tables[name]
        angles = [a for _, a in points]
        angles += [(a0 + a1) / 2 for (_, a0), (_, a1) in zip(points, points[1:])]
        angles += [x * 0.5 for x in range(720)]
        for angle in angles:
            # Small offsets for a slightly rotated tip; quarter and half turns for a
            # turned sensor. The firmware wraps angle + offset into 0-360.
            for offset in (0.0, 4.5, -7.0, 90.0, -90.0, 180.0, -180.0):
                live = angle + 2.5
                cases.append(f"{index} {angle:.6f} {offset:.6f} {reference((angle + offset) % 360, points):.6f}"
                             f" {live:.6f} {reference((live + offset) % 360, points):.6f}")

    compiler = next((c for c in ("c++", "g++", "clang++") if shutil.which(c)), None)
    if not compiler:
        sys.exit("No C++ compiler found")
    failed = False
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        harness = build(compiler, tmp, "default", body.replace(PLACEHOLDER, custom_default), mag_min)
        (tmp / "cases.txt").write_text("\n".join(cases) + "\n")
        failed |= subprocess.run([str(harness), str(tmp / "cases.txt"), str(len(options))]).returncode != 0
        for i, table in enumerate(BAD_CUSTOM):
            harness = build(compiler, tmp, f"bad{i}", body.replace(PLACEHOLDER, table), mag_min)
            if subprocess.run([str(harness), str(len(options) - 1)]).returncode != 0:
                print(f"Custom table {table!r}: should give unknown at every angle")
                failed = True
        print(f"{len(BAD_CUSTOM)} unusable Custom tables checked")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
