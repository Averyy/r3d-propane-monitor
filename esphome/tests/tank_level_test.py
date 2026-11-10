"""Check the Tank level lambda in propane-monitor.yaml against docs/calibration.md.

Compiles the lambda's C++ on the host with stand-ins for the ESPHome objects, then
checks, for every dial type, that it gives the percentage the method in
calibration.md ("Angle to percent") gives from the tables there. This keeps the
YAML and the docs in step and tests the interpolation itself.

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

HARNESS = r"""
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <optional>
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
#define id(x) id_##x
static std::optional<float> level() {
#include "lambda.inc"
}
int main(int argc, char **argv) {
  if (argc != 2) return 2;
  FILE *f = fopen(argv[1], "r");
  if (!f) return 2;
  unsigned idx; double a, off, want; int n = 0, bad = 0;
  while (fscanf(f, "%u %lf %lf %lf", &idx, &a, &off, &want) == 4) {
    dial_s.idx = idx; angle_s.state = a; offset_s.state = off; n++;
    auto got = level();
    if (!got || std::fabs(*got - want) > 1e-3) {
      if (bad++ < 10)
        printf("dial %u, angle %.3f, offset %.1f: want %.4f, got %s%.4f\n", idx, a, off, want,
               got ? "" : "nothing ", got ? *got : 0.f);
    }
  }
  int edge = 0;
  angle_s.has = false; if (level().has_value()) { puts("no angle yet: should publish nothing"); edge++; }
  angle_s.has = true;
  problem_b.state = true;
  { auto v = level(); if (!v || !std::isnan(*v)) { puts("sensor problem: should be NaN"); edge++; } }
  problem_b.state = false;
  dial_s.idx = std::nullopt;
  { auto v = level(); if (!v || !std::isnan(*v)) { puts("no dial type: should be NaN"); edge++; } }
  printf("%d cases, %d mismatches, %d edge-case failures\n", n, bad, edge);
  return (bad || edge) ? 1 : 0;
}
"""


def yaml_lambda_and_options(text):
    """Pull the Tank level lambda and the Dial type options out of the YAML."""
    m = re.search(r"id: propane_tank_level\n(?:.*\n)*?    lambda: \|-\n((?:      .*\n|\s*\n)+)", text)
    if not m:
        sys.exit("Tank level lambda not found in propane-monitor.yaml")
    body = "".join(line[6:] + "\n" for line in m.group(1).rstrip().split("\n"))
    m = re.search(r"id: propane_dial_type\n(?:.*\n)*?    options:\n((?:      - .*\n)+)", text)
    if not m:
        sys.exit("Dial type options not found in propane-monitor.yaml")
    options = []
    for line in m.group(1).strip("\n").split("\n"):
        value = line.strip()[2:].strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        options.append(value)
    return body, options


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


def main():
    body, options = yaml_lambda_and_options(YAML.read_text(encoding="utf-8"))
    tables = doc_tables(DOC.read_text(encoding="utf-8"))
    if sorted(options) != sorted(tables):
        sys.exit(f"Dial types differ.\n  YAML: {options}\n  docs: {list(tables)}")

    cases = []
    for index, name in enumerate(options):
        points = tables[name]
        angles = [a for _, a in points]
        angles += [(a0 + a1) / 2 for (_, a0), (_, a1) in zip(points, points[1:])]
        angles += [x * 0.5 for x in range(720)]
        for angle in angles:
            for offset in (0.0, 4.5, -7.0):
                cases.append(f"{index} {angle:.6f} {offset:.6f} {reference(angle + offset, points):.6f}")

    compiler = next((c for c in ("c++", "g++", "clang++") if shutil.which(c)), None)
    if not compiler:
        sys.exit("No C++ compiler found")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "lambda.inc").write_text(body)
        (tmp / "harness.cpp").write_text(HARNESS)
        (tmp / "cases.txt").write_text("\n".join(cases) + "\n")
        subprocess.run([compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror", "-o", str(tmp / "harness"),
                        str(tmp / "harness.cpp")], check=True)
        result = subprocess.run([str(tmp / "harness"), str(tmp / "cases.txt")])
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
