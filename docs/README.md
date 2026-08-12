# Story Corner

> **CURRENT DEVELOPMENT ROUTER — frozen R11 engineering evidence plus a
> separate physical handoff.** Historical/frozen R6-R10 evidence remains
> preserved below and under `development/`. The qualification-only first-wall design at
> [development/r11/README.md](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11/README.md) is for the measured
> **1555.75 mm** wall. Its v1 neutral bundle is immutable, model-only, and
> **never print-authorized**; read its
> [v1 print hold](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11/PRINT_FIRST.md). For the separately controlled pathway covering
> exactly one fail-fast tabletop attempt of the bay-0 **left** terminal
> half-deck, quantity one, read the
> [v2 overlay](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11_print_v2/README.md) and its
> [Gate A-left contract](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11_print_v2/PRINT_GATE_A_LEFT.md).
> The checked-in v2 package also never self-authorizes: any eligibility exists
> only in an external, exact-job, fresh, single-use permit consumed before one
> Send attempt. **No print is authorized by the checked-in files themselves.**
> A failed, cancelled, rejected, or ambiguous attempt consumes
> it; every retry requires a new slice, review, live-state check, and fresh
> permission. Within that frozen overlay, the right half and every later
> article remain blocked.
>
> The full-wall planning targets remain a **28-article supplied kit**, no more
> than **27 articles simultaneously installed**, **28 safe unbatched starts**,
> and an **unverified 21-start batched target**. Neither v1 nor v2 authorizes
> wall drilling, installation, test load, stored load, production/full-wall
> printing, or a nonzero load rating; the rating remains **0 kg / 0 lb**.
>
> Current real-world observations are recorded separately in the
> [beginner physical guide](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11_physical/README.md) and
> [append-only physical record](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11_physical/PHYSICAL_RECORD.md), so the frozen v1/v2 evidence is not silently rewritten.
> The bay-0 left terminal half-deck was printed, cooled, and removed; the user
> reports that it lies flat without rocking, shows no visible finger flex, and
> was not sanded. A later right-half job was initiated outside the frozen
> left-only v2 overlay; its completed-part outcome has not yet been recorded.
> Neither event retroactively changes v1/v2 or authorizes another print.
> After the right half is cool, removed, and inspected, the next decision is an
> **unloaded tabletop dry-fit of those two halves**, not bulk printing, wall
> work, or load testing.
>
> Start with the physical guide and the current R11/v2 documents above, not
> the historical R6 instructions below.
>
> The R6 material below and the R7-R10 trees under `development/` are preserved
> historical/frozen evidence. They are not substitutes for an R11 part or
> permission to print. A standalone historical R6 publication may omit the
> `development/` tree; use the full source repository for current R11 work.

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
> and storage measurements are incomplete, and the printer, nozzle, build
> plate, black-PETG product, and target load are unconfirmed. Do not install or
> load this design until the measurement, coupon, wall-mockup, full-bay,
> whole-article thermal-cycle, sustained-creep, recovery, teardown, and
> separate destructive-specimen gates are completed.

There is no embedded G-code. Release artifacts remain model-only so that an
unconfirmed machine or material profile cannot be mistaken for a safe print
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
black-PETG product, drying method, layer/profile settings, supports, brim, and
plate layout are unconfirmed, and `slice_report.json` correctly records that
slicing was not performed. Print time must come from a retained slice report
for the exact qualified machine/material/profile; CAD volume is not a time
estimate.

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

The [exact 6 + 3 two-level rendering](https://github.com/rupret007/story-corner-shelf/blob/main/assets/artist_rendering_all_petg_two_level_exact_6_plus_3.png)
is the current visual-intent hero. The [earlier two-level rendering](https://github.com/rupret007/story-corner-shelf/blob/main/assets/artist_rendering_all_petg_two_level.png)
is preserved as visual-development history, and the
[rendering prompt](https://github.com/rupret007/story-corner-shelf/blob/main/assets/artist_rendering_all_petg_two_level.prompt.md) records
the intended scene. Both images are illustrative only: generated drawings,
schedules, and the manifest govern dimensions, bay counts, object counts, and
geometry.

## Start here

1. Read [PRINT_ME_FIRST.md](PRINT_ME_FIRST.md) and [SAFETY.md](SAFETY.md).
2. Complete [MEASUREMENT_WORKSHEET.md](MEASUREMENT_WORKSHEET.md), including
   photos, framing verification, storage, printer, material, and fastener data.
3. Review the governing [plan drawing](https://github.com/rupret007/story-corner-shelf/blob/main/generated/drawings/plan_layout.svg),
   [two-level layout](https://github.com/rupret007/story-corner-shelf/blob/main/generated/drawings/two_level_vertical_layout.svg), and
   [joinery sequence](https://github.com/rupret007/story-corner-shelf/blob/main/generated/drawings/exploded_joinery.svg). Drawings govern;
   renderings are visual intent only.
4. Follow [TEST_PROTOCOL.md](TEST_PROTOCOL.md) before any overhead installation.
5. Use [ASSEMBLY.md](ASSEMBLY.md) only after every hard gate has passed.

The design rationale and exact load-path boundaries are in
[ENGINEERING_DESIGN.md](ENGINEERING_DESIGN.md). Research and the supplied-file
audit are recorded in [REFERENCE_RESEARCH.md](https://github.com/rupret007/story-corner-shelf/blob/main/REFERENCE_RESEARCH.md) and
[REFERENCE_3MF_AUDIT.md](https://github.com/rupret007/story-corner-shelf/blob/main/REFERENCE_3MF_AUDIT.md).

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
