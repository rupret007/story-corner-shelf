# Measurement worksheet — Triadic Palatine Order r5

Print or copy this file, fill it in the closet, then transcribe section H
into [config.json](config.json) and rebuild. Empty config values keep every
generated artifact explicitly nominal; nothing here creates a load rating.

Datum for every station measurement: the **intersection of the two finished
wall planes** at the inside corner — never a board end.

| Header | Value |
|---|---|
| Date / measured by | |
| Room temperature / humidity | |
| Tools used and their stated accuracy | |

## A. Photo schedule

Take and keep (crop or blur anything private before sharing in an issue):

1. Both walls square-on, corner to outer end.
2. The inside corner at each candidate shelf elevation with a square held in.
3. Straightedge or laser against each wall showing bow at shelf height.
4. The outlet and its service envelope with a tape in frame.
5. Stud-finding evidence on both walls (marks plus the method used).
6. Wall build-up at the corner (drywall edge, mud, caulk).
7. The candidate fastener next to calipers.
8. The largest storage bins to be used.
9. Printer and filament spool label.

## B. Clear wall width (per wall, per elevation)

Measure the clear length from the finished corner to the first obstruction at
the **rear, middle, and front** shelf planes for every candidate elevation.
The value that goes in config is the **smallest** reading for that wall.

3 ft return wall:

| Elevation (in from floor) | Rear (in) | Middle (in) | Front (in) |
|---|---|---|---|
| | | | |
| | | | |

Minimum used for generation: ______ in

5 ft through wall:

| Elevation (in from floor) | Rear (in) | Middle (in) | Front (in) |
|---|---|---|---|
| | | | |
| | | | |

Minimum used for generation: ______ in

## C. Corner geometry

| Item | Value |
|---|---|
| Included corner angle at each candidate elevation (deg) | |
| Worst deviation from 90.0° (deg) | |
| Maximum wall bow under a straightedge (mm) | |
| Full-size corner template made and checked? | yes / no |

The generation gate is **±0.25°**; the residual 1.6 mm joint clearance must
stay ≥ 0.6 mm. If the worst measured angle exceeds the gate, stop — see
[SAFETY.md](SAFETY.md) corner stop conditions.

## D. Framing map (one row per support line)

Desired nominal centers (from [generated/support_plan.csv](generated/support_plan.csv)):
return 10.750, 22.313, 33.875 in; through 6.281, 22.281, 38.281, 54.281 in.
Field centers must land on verified wood framing or installed blocking, stay
≤ 16 in apart, ≥ 2 in distinct, and leave ≤ 6 in end overhang.

| Wall | Station | Verified center from corner (in) | Wood width (in) | Material / verification method | Utilities clear? |
|---|---|---|---|---|---|
| return | 1 | | | | |
| return | 2 | | | | |
| return | 3 | | | | |
| through | 1 | | | | |
| through | 2 | | | | |
| through | 3 | | | | |
| through | 4 | | | | |

If a nominal station misses framing: [ ] blocking will be installed, or
[ ] the centers above will be entered so the plan regenerates around them.

## E. Installed hardware (measure after standards are mounted)

| Item | Value |
|---|---|
| Wall-to-plywood-back offset, return wall (in) | |
| Wall-to-plywood-back offset, through wall (in) | |
| Bracket wall-to-tip reach, real bracket seated (in) | |
| Bracket body width / lock type | |
| Wall-to-fascia projection with the exact hardware (in) | |

The offset is measured from the **finished wall face to the plywood back
plane** with the real standard and bracket seated — do not substitute the
catalog projection (nominal fallback is 0.6875 in).

## F. Stored contents

| Item | Value |
|---|---|
| Bin outside width × depth × height (largest) | |
| Loaded weight of heaviest bin (lb) | |
| Bin count per arm | |
| Measured shelf-arm dead load, return (lb) | |
| Measured shelf-arm dead load, through (lb) | |

## G. Printer and filament

| Item | Value |
|---|---|
| Printer model / usable build volume (mm) | |
| Nozzle diameter and material | |
| Build plate type and condition | |
| Bambu Studio version | |
| Black PETG brand, product line, lot | |
| Spool opened date / storage RH / drying method | |

## H. Transcribe into config.json

Units: every `_in` key is inches, `_deg` degrees, `_lb` pounds. The runs
array holds the 3 ft wall at `id: "short_wall_3ft"` and the 5 ft wall at
`id: "long_wall_5ft"`.

| Worksheet source | config.json key (JSON path) |
|---|---|
| B minimum, return wall | `closet.runs[id=short_wall_3ft].field_verified_min_clear_wall_width_in` |
| B minimum, through wall | `closet.runs[id=long_wall_5ft].field_verified_min_clear_wall_width_in` |
| C worst included angle | `closet.inside_corner.field_verified_angle_deg` |
| D verified centers, return (3 numbers) | `closet.runs[id=short_wall_3ft].field_verified_support_centers_in` |
| D verified centers, through (4 numbers) | `closet.runs[id=long_wall_5ft].field_verified_support_centers_in` |
| E offset, return wall | `closet.runs[id=short_wall_3ft].field_verified_installed_shelf_back_offset_in` |
| E offset, through wall | `closet.runs[id=long_wall_5ft].field_verified_installed_shelf_back_offset_in` |
| E bracket reach | `structural.field_verified_bracket_reach_in` |
| F dead load, return | `closet.runs[id=short_wall_3ft].field_verified_shelf_arm_dead_load_lb` |
| F dead load, through | `closet.runs[id=long_wall_5ft].field_verified_shelf_arm_dead_load_lb` |

Worked example (return run, values invented for illustration only):

```json
{
  "id": "short_wall_3ft",
  "field_verified_min_clear_wall_width_in": 35.75,
  "field_verified_installed_shelf_back_offset_in": 0.71875,
  "field_verified_support_centers_in": [10.5, 22.0, 33.5],
  "field_verified_shelf_arm_dead_load_lb": 9.4
}
```

## I. Rebuild and verify the entry took effect

```sh
PYTHON_BIN=.venv/bin/python SKIP_BAMBU=1 scripts/build_all.sh
```

Then open [generated/validation.json](generated/validation.json) and confirm
the `*_source` fields report `field_verified_*` (for example
`installed_shelf_back_offset_source`, `clear_width_source`,
`support_geometry_source`, `bracket_reach_source`) instead of a nominal
fallback. The generator hard-stops on out-of-gate angle or support values —
a stop is the design protecting you, not an error to work around. Re-measure,
correct the entry, and rebuild.
