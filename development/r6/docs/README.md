# Story Corner

Story Corner is a fitted, two-level, inside-corner shelf whose entire shelf
body is printed in black PETG. The deck cassettes, tied-arcade halves,
X-corbels with integral bearing caps, joinery, keeper strips, pins, cross-keys,
facade, and ornament
are printed.
The only nonprinted installation boundary is suitable metal structural screws
with integral heads or compatible metal washers, driven into verified wood
studs or purpose-installed blocking.

> **EXPERIMENTAL / UNRATED / NOT READY FOR OVERHEAD USE.** No tested load
> rating exists. Production wall holes are deliberately blocked, the real wall
> and storage measurements are incomplete. The intended local printer, nozzle,
> build plate, and black-PETG product are now identified, but their exact
> spool/lot, saved slicer profile, print behavior, and target load are not
> qualified. Do not install or load this design until the measurement, coupon,
> wall-mockup, full-bay,
> whole-article thermal-cycle, sustained-creep, recovery, teardown, and
> separate destructive-specimen gates are completed.

There is no embedded G-code. Release artifacts remain model-only so that an
unqualified machine or material profile cannot be mistaken for a safe print
recipe.

## The nominal fitted L

The current reference geometry fits nominal 60 in and 36 in finished walls at
one elevation. It is 6 in (152.4 mm) deep. The long-wall run passes through the
corner; its 6 x 6 in corner cassette visually completes the short wall, whose
independent return begins beyond that front plane.

| Item | Nominal value |
| --- | ---: |
| Long-wall through run | 1514.475 mm (59.625 in) |
| Short-wall structural return start from the corner datum | 177.55 mm (6.990 in) |
| Short-wall printed return length | 733.675 mm (28.885 in) |
| Shelf depth | 152.4 mm (6 in) |
| Chassis-to-return structural clearance | 18.8 mm |
| Locked all-solid / relieved visible-base corner gap | 1.2 / 2.0 mm |
| Long / return visible bays | 6 / 3 |
| Total visible bays | 9 |
| Long / return wall-fastened supports per level | 7 / 4 |
| Half-bay cassettes per level | 18 |

This is the design's 3 / 6 / 9 rhythm: three return bays plus six through bays
make nine. The support equation is `(3 + 1) + (6 + 1) = 11` independently
wall-fastened X-corbel/pier stations per level. Dimensions are nominal
regression fixtures, not permission to print or drill; field measurements must
regenerate them.

Field qualification requires four distinct elevation/run support records:
lower-through, lower-return, upper-through, and upper-return. Each record must
contain the exact clear width, every verified support center, wood
stud/blocking material, and framing verification method. Matching nominal
centers do not permit one elevation's record to stand in for the other. The
fastener record must also include maximum driver outside diameter and required
straight approach, and the material record must name the filament drying
method.

The corner datums are deliberately distinct: chassis front 158.75 mm,
integral-boss front 165.95 mm, full locked removable-facade front 171.95 mm,
floating return-finish solid/visible leading planes 173.15/173.95 mm, maximum
through-facade service face 176.35 mm, and return structural start 177.55 mm.
The floating return finish cantilevers 4.4 mm back from its cassette and must
be removed first before servicing the fixed through rosette.

Each complete level contains 258 installed printed objects: 225 chassis,
joinery, and retention objects plus 33 removable ornament objects. The two
selected, structurally independent levels contain 516 installed printed
objects. Calibration coupons and destructive test pieces are additional and
are not included in those totals.

At a contextual PETG density of 1.27 g/cm³, the current repeat-weighted CAD
solids total about **16.000 kg per level** and **32.001 kg for two levels**
(current exact software report: 16.000337 / 32.000674 kg).
Those are model-solid context values—not slicer estimates, finished tare, or a
load rating—but they expose the project's substantial possible material and
dead-load demand. The generated package report must derive these totals from
the actual meshes and repeat counts. Confirmed Bambu Studio sliced mass and a
weighed finished-level tare are mandatory before any wall-fastener, full-bay,
or wall-mockup qualification; contents load is additional.

No authoritative print-time estimate is available. The printer, nozzle,
and plate intended for local qualification are now known, but the exact PETG
spool/lot, drying record, saved profile, calibration, supports, brim, and plate
layout remain unqualified. `slice_report.json` correctly records that release
slicing was not performed. Print time must come from a retained local slice
report for the exact qualified machine/material/profile; CAD volume is not a
time estimate.

## Confirmed local qualification setup

The intended qualification setup is a **Bambu Lab A1 mini**, **0.4 mm nozzle**,
**Bambu Textured PEI Plate**, and **SUNLU standard black PETG 1.75 mm**, retail
ASIN [`B0D1KC72YP`](https://www.amazon.com/dp/B0D1KC72YP). This confirms what
to test; it does not qualify a production profile or any structural part. The
listing identifies the product as GRS-certified with at least 50% recycled
content. That is not a disqualification, but results must remain specific to
this product, color, lot, spool, drying record, and saved profile. Do not carry
results to a different PETG product or lot.

> **Do not reuse the current Bambu Studio PLA profile.** Select the installed
> Bambu Studio **system** filament profile named exactly
> `SUNLU PETG @BBL A1M 0.4 nozzle`, and verify that the project says PETG—not
> PLA—before every slice and print.

The following is a **candidate qualification starting point**, not a SUNLU- or
Bambu-certified A1 mini preset and not a production recipe:

| Bambu Studio field | Candidate value |
| --- | --- |
| Printer | Bambu Lab A1 mini, 0.4 mm nozzle |
| Plate | Textured PEI Plate |
| Filament | Installed Bambu Studio system profile `SUNLU PETG @BBL A1M 0.4 nozzle`; SUNLU standard black PETG 1.75 mm, ASIN `B0D1KC72YP` |
| Nozzle temperature | 250 °C first layer; 245 °C other layers |
| Textured-bed temperature | 60 °C first and other layers |
| Flow ratio | 0.94 |
| Maximum volumetric speed | 9 mm³/s |
| Process | `0.20 mm Strength`; 0.20 mm layer height |
| Wall loops | 6 |
| Top / bottom shell layers | 5 / 3 |
| Sparse infill | 25%, grid |
| Brim | 5 mm baseline; a qualification-project plate may require an explicit override |
| Supports | Off by system default; review each plate and retain any project-specific override |
| Part cooling | 10% minimum, 30% maximum, 90% for overhangs |

For the first baseline, leave those embedded system/process values in place;
do not improvise cooling, shell, infill, support, or brim changes. The local
qualification builder may deliberately override support or brim per plate, in
which case its plate value governs and must be recorded.

Before a qualification print, dry this spool at **60–65 °C for 6 hours** and
record the dryer, indicated/verified temperature, time, spool/lot, and date.
Wash the Textured PEI Plate with detergent and water, rinse and dry it fully,
and avoid touching the print area. SUNLU's current pages differ in some
details, so the saved values above remain a conservative, lot-specific test
baseline that must be calibrated and inspected.

Beginner sequence:

1. Clean and fully dry the plate; dry and record the exact PETG spool, then
   load PETG into the A1 mini.
2. Open the local qualification project—not a canonical model-only package as
   a direct print job—and select A1 mini / 0.4 mm / Textured PEI Plate.
3. Select the installed system profile `SUNLU PETG @BBL A1M 0.4 nozzle`.
   Confirm **PETG, not PLA**, and confirm every object's scale remains exactly
   100% on all axes.
4. Slice locally. Inspect the first layer, supports, brim, every layer/toolpath,
   plate boundaries, and warnings in Preview before sending anything.
5. Run supported A1-series Flow Dynamics calibration when the firmware allows
   it. On A1 mini, run Bambu Studio's **manual coarse and fine Flow Rate**
   calibration and save the result as a new filament preset.
6. Print only one qualification plate at a time, watch the first layer, and
   stop on lifting, scraping, skipped paths, severe stringing, or extrusion
   trouble. Let the plate cool to **35 °C or below** before removal.

The local qualification helper is development tooling, not a release builder.
Use the command that matches the tree you actually have, with the same exact
fresh sibling output path.

From the source-workspace repository root:

```text
.venv/bin/python development/r6/build_bambu_qualification_projects.py --output ../story-corner-r6-bambu-a1mini-sunlu-petg-qualification-v1
```

From the flattened published-project root:

```text
.venv/bin/python build_bambu_qualification_projects.py --output ../story-corner-r6-bambu-a1mini-sunlu-petg-qualification-v1
```

The helper atomically creates that fresh workspace sibling and must refuse to
replace an existing destination or write anywhere else. Keep
`../story-corner-r6-bambu-a1mini-sunlu-petg-qualification-v1/` local and separate
from `development/r6/generated/`; it is unsliced, contains no G-code, and is
not covered by the release manifest.

For now, print only non-wall qualification coupons. Do **not** print the solid
wall-screw placeholder/coupon, an X-corbel, the one-level package, or the
two-level installation set until actual fastener, wall, driver-clearance, and
physical gates are resolved. The A1 mini advertises a 180 x 180 x 180 mm build
volume, while a saved X-corbel plus the required 6 mm brim consumes exactly
180 mm on one bed axis. That is zero nominal margin before plate keep-outs,
placement tolerance, or slicer constraints; scaling, cropping, omitting the
brim, or changing orientation is not an acceptable workaround. The X-corbel
is not part of the initial campaign; its 6 mm brim is a deliberate
project-specific override to the general 5 mm candidate baseline.

Official setup references: [Bambu Lab A1 mini specifications](https://us.store.bambulab.com/products/a1-mini),
[Bambu Textured PEI Plate care and PETG guidance](https://us.store.bambulab.com/products/bambu-textured-pei-plate),
[Bambu Flow Dynamics calibration](https://wiki.bambulab.com/en/software/bambu-studio/calibration_pa),
[Bambu Flow Rate calibration](https://wiki.bambulab.com/en/software/bambu-studio/calibration_flow_rate),
[SUNLU standard PETG product guidance](https://www.sunlu.com/products/petg-3d-printing-filament),
[SUNLU filament drying guide](https://www.sunlu.com/wiki/filament-usage-guide),
and [SUNLU printer-preset selector](https://www.sunlu.com/materials-lab/printer-presets).

## Two independent levels

The provisional layout places shelf tops at +12 in and +33 in above the top of
the outlet, giving 21 in top-to-top spacing. Those positions use the reported
43.5 in outlet-top-to-ceiling zone and must be remeasured from a common level
datum. Install and service-check the upper level first, then the lower level.
No column, arch, key, or corner trim transfers load between levels.

## How the system works

The coffered deck, integral front/rear cassette chords, front tied-spandrel
arcade, and wall-fastened 3:4:5 X-corbels form a candidate load-sharing
chassis. The
curved Roman rib is not treated as a pure-compression arch: it may see mixed
compression, bending, tension, and shear. Only matched full-bay testing with
and without the curved frame may establish whether it earns structural credit.

Assembly uses a final-position vertical lift. Each arcade half rises at its
final run coordinate so two top tenons and one spring tenon enter three
open-bottom receivers together. Two top positive quarter-turn cross-keys plus
one spring cross-key are then inserted and visibly indexed from the front. A separate crown bridge rises from below
to a hard stop and receives one accessible anti-drop pin on the fixed right
half. No whole-half longitudinal slide is allowed; the rejected sliding motion
would deadlock at the crown.

Nine crown seams are locally fixed within their bays. After three diaphragm
keys are installed at each fixed crown, one left-owned keeper lifts from below
and slides rearward so its single rear-bayonet tongue is captured. A separate underside keeper-reach
indexed quarter-turn pin blocks the full forward unlock slide.
The front crown tie inserts from the visible edge and has its own
separate visible-front indexed quarter-turn pin.
Seven supported pier seams float axially to accommodate movement and their
three keys remain trapped by the X-corbel's integral bearing cap. Cross-keys, alignment keys,
keeper strips, and retention pins receive no independent vertical load rating.

The earlier stitch-rail study is deliberately excluded from the installed
baseline. At the geometry-current return length it would add 119 unqualified
pieces per level and an unproven second
thermal/load path. Any future rail must earn its way back through a named,
rail-on/rail-off full-bay experiment; the active design assigns it no capacity
credit.

Roman arcade and entablature are the primary visual language, disciplined by
Greek proportion and fluting. Egyptian influence is limited to a shallow
cavetto, and Art Deco appears only as restrained sunbursts, chevrons, and a
stepped keystone. Fine ornament is isolated, removable, and assigned zero
structural credit.

## Visual-intent assets

The [exact 6 + 3 two-level rendering](assets/artist_rendering_all_petg_two_level_exact_6_plus_3.png)
is the current visual-intent hero. The [earlier two-level rendering](assets/artist_rendering_all_petg_two_level.png)
is preserved as visual-development history, and the
[rendering prompt](assets/artist_rendering_all_petg_two_level.prompt.md) records
the intended scene. Both images are illustrative only: generated drawings,
schedules, and the manifest govern dimensions, bay counts, object counts, and
geometry.

## Start here

1. Read [PRINT_ME_FIRST.md](PRINT_ME_FIRST.md) and [SAFETY.md](SAFETY.md).
2. Complete [MEASUREMENT_WORKSHEET.md](MEASUREMENT_WORKSHEET.md), including
   photos, framing verification, storage, printer, material, and fastener data.
3. Review the governing [plan drawing](generated/drawings/plan_layout.svg),
   [two-level layout](generated/drawings/two_level_vertical_layout.svg), and
   [joinery sequence](generated/drawings/exploded_joinery.svg). Drawings govern;
   renderings are visual intent only.
4. Follow [TEST_PROTOCOL.md](TEST_PROTOCOL.md) before any overhead installation.
5. Use [ASSEMBLY.md](ASSEMBLY.md) only after every hard gate has passed.

The design rationale and exact load-path boundaries are in
[ENGINEERING_DESIGN.md](ENGINEERING_DESIGN.md). Research and the supplied-file
audit are recorded in [REFERENCE_RESEARCH.md](REFERENCE_RESEARCH.md) and
[REFERENCE_3MF_AUDIT.md](REFERENCE_3MF_AUDIT.md).

## Artifact status

The deterministic r6 build has emitted all five canonical **software-model
packages**. Their current manifest, package, mesh, source-map, real-parent
Boolean-sweep, and neutral-3MF checks pass; this is software evidence only:

| Canonical package ID | Frozen model-only filename | Current model count |
| --- | --- | ---: |
| `print_first_prototypes` | `MODEL_ONLY_R6_PRINT_FIRST_PROTOTYPES.3mf` | 8 |
| `unique_parts_catalog` | `MODEL_ONLY_R6_UNIQUE_PARTS_CATALOG.3mf` | 49 |
| `worst_case_one_bay_qualification` | `MODEL_ONLY_R6_WORST_CASE_ONE_BAY_QUALIFICATION.3mf` | 25 |
| `one_level_l` | `MODEL_ONLY_R6_ONE_LEVEL_L.3mf` | 258 |
| `two_level_full_project` | `MODEL_ONLY_R6_TWO_LEVEL_FULL_PROJECT.3mf` | 516 |

`software_model_package_eligible: true` means only that the geometry and
neutral package conform to the checked software contract. Every package must
still state `physical_installation_qualified: false` and
`production_release_eligible: false`. The one-bay qualification file is a
specimen model for future tests, not evidence that any qualification test
passed. None of the five files is a print recipe, safety approval, load rating,
or permission to install overhead.

Naming alone is not release evidence. The generated model-only packages,
49 individual STL files under `generated/stl/`, and their exact 49 one-part
model-only 3MF counterparts under `generated/individual_model_only_3mf/`,
parts schedules, `model_3mf_report.json`,
`slice_report.json`, validation report, and cryptographic manifest form one
checked artifact set and must remain digest-aligned. Do not rename a
development prototype to a canonical filename. `slice_report.json` says
`performed: false` because the printer, nozzle, plate, PETG, and settings are
unconfirmed; it is neither a print-time estimate nor a substitute for slicing
or physical qualification.

## Project map

- `config.json` — authoritative parameters, hard gates, and nominal snapshot
- `design_math.py` — fitted plan and geometry calculations
- `release_plan.py` — exact cassette and support stationing
- `release_inventory.py` — 258-object per-level physical inventory
- `generate_all_petg_r6.py` — deterministic mesh/package generator
- `generate_drawings.py` — deterministic governing SVG sheets
- `generated/` — reproducible development/release artifacts and reports
- `assets/` — current hero, preserved earlier rendering, and reproducible prompt
- `reference/hybrid_r5/` — preserved r5 hybrid fallback; it is not the active
  all-PETG design

## Rights and references

No third-party mesh is copied into Story Corner. Supplied MakerWorld packages
were inspected read-only for functional principles and are not redistributed.
See the reference documents for provenance and applicable upstream licenses.

This repository currently has no `LICENSE` file. Public visibility does not
grant permission to copy, modify, redistribute, or sell the project. A project
license must be selected deliberately before reuse rights can be assumed.
