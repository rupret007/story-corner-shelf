# Supplied 3MF reference audit

This is a read-only functional audit. The supplied meshes are **not** copied,
ported, bundled, or used as load evidence for Story Corner.

## Files inspected

- `Wall-Shelf-Single-Color.3mf`
- `Wall-Shelf+120%.3mf`

Both packages identify the Mini Wall Shelf design as BY-NC material. Story
Corner is independently modeled and does not redistribute or derive geometry
from either package.

## Package facts

Each package contains the same three watertight, single-body source meshes:

| Source object | Source bounds (mm) | Source volume (cm³) |
|---|---:|---:|
| Shelf plate | 150 × 90 × 6 | 78.891 |
| Wall mount A | 15 × 52.133 × 42.421 | 7.921 |
| Wall mount B | 15 × 52.133 × 42.421 | 7.921 |

The `+120%` package does not contain a newly engineered mesh. Its 3MF build
transforms uniformly scale the same three source objects by 1.2, producing a
nominal 180 × 108 × 7.2 mm plate and correspondingly enlarged mounts.

The supplied print profiles mention 0.2 mm layers, three walls, and 15% infill.
Those are profile choices for a small shelf, not structural qualification or
transferable settings for Story Corner. The packages also contain Bambu Studio
metadata and are therefore treated only as references; Story Corner release
packages remain neutral model-only 3MFs with no slicer payload or G-code.

## Principles retained, without copying geometry

- Separate, replaceable mounts can make a shelf easier to print and service.
- Broad plug/bearing lands are preferable to small snap tabs.
- Fastener access should remain visible and reachable after assembly.
- A no-glue fit can be practical when the load-bearing shoulder and the
  anti-withdrawal feature are deliberately separated.
- A small calibration part should precede a full print.

## Principles explicitly not inferred

- Uniformly scaling a shelf does not establish a new safe load capacity.
- The supplied mounts do not validate a 5-foot run, an inside-corner L, two
  shelf levels, long-duration PETG creep, front-edge loading, or Story Corner's
  modular seams.
- The supplied screw openings do not determine Story Corner wall-bore sizes.
  Production wall bores remain blocked until the real screw shank, head or
  washer, embedment, wall material, and verified framing are entered.
