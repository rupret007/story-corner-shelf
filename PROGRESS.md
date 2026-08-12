# Story Corner development checkpoints

This log records software/design evidence only. It is not evidence of physical
capacity, installation readiness, or a load rating.

## Current development — frozen R11 evidence and separate physical handoff

Historical/frozen R6-R10 evidence remains preserved; it is not a substitute
for the current R11 source, physical record, or per-job control boundary. The
controlling rating remains **0 kg / 0 lb**.

Current work is routed through [development/r11/README.md](development/r11/README.md)
and [development/r11/PRINT_FIRST.md](development/r11/PRINT_FIRST.md), with the
separate one-attempt control pathway in
[development/r11_print_v2/README.md](development/r11_print_v2/README.md) and
[development/r11_print_v2/PRINT_GATE_A_LEFT.md](development/r11_print_v2/PRINT_GATE_A_LEFT.md).
R11 is a qualification/development study for the measured **1555.75 mm** first
wall. Its planning targets remain a **28-article supplied kit**, no more than
**27 articles simultaneously installed**, **28 safe unbatched starts**, and an
**unverified 21-start batched target**.

The immutable v1 neutral bundle contains model-only qualification evidence and
is never print-authorized. The isolated v2 checked-in package is also
permanently non-authorizing. **No print is authorized by the checked-in files
themselves.** It binds a controlled external pathway to exactly
one bay-0 **left** terminal half-deck, quantity one: the exact final slice,
Preview and live-state evidence, fresh exact human permission, and a fresh
single-use permit must all bind the same job. The permit is consumed before
one Send attempt, including a failed, cancelled, rejected, or ambiguous
attempt. It is not reusable; every retry requires a new slice, review,
live-state check, and fresh permission.

Current real-world observations are kept outside those frozen trees in
[development/r11_physical/README.md](development/r11_physical/README.md) and
[development/r11_physical/PHYSICAL_RECORD.md](development/r11_physical/PHYSICAL_RECORD.md).
The bay-0 left terminal half-deck was printed, cooled, and removed. The user
reports that it lies flat without rocking, shows no visible finger flex, and
was not sanded. A later bay-0 right-half print was initiated outside the frozen
left-only overlay; its completed-part outcome is not yet recorded. These facts
do not retroactively alter v1/v2. The next decision after both halves are cool
and inspected is an unloaded tabletop dry-fit, not bulk printing.

Neither v1 nor v2 authorizes drilling, wall installation, test load, stored
load, production/full-wall printing, or a nonzero load rating; the rating
remains **0 kg / 0 lb**. The R6 record below and the R7-R10 trees under
`development/` remain historical/frozen and must not be substituted for
current R11 geometry, evidence, or permission.

## Historical R6 checkpoint

## 2026-08-09

- Reconciled the 6-inch, same-height L plan and exact 3/6/9 stationing.
- Selected two complete, independently wall-fastened shelf levels at provisional
  +12 inch and +33 inch shelf-top offsets above the outlet top.
- Preserved the verified hybrid r5 source under `reference/hybrid_r5/`.
- Added original all-PETG design math and regression tests.
- Preserved both two-level Palatine visual-intent assets and their reproducible
  prompt: the exact-6-plus-3 image is the current hero, while the earlier image
  remains visual-development history. Generated drawings govern dimensions and
  counts.
- Inspected the two owner-supplied reference 3MFs without copying their meshes.
- Generated the first isolated model-only r6 fit and geometry specimens; all
  were watertight, single-body, within the 180 mm design envelope, deterministic,
  and free of embedded G-code.
- Rejected an assembly motion that made the two crown halves collide. The active
  design now requires final-position vertical insertion with accessible,
  replaceable positive quarter-turn capture cross-keys and a separate
  upward-inserted crown bridge.
- Froze an exact physical-object inventory: 258 installed printed objects per
  level and 516 for the selected two-level project, with integral tenons and
  receivers tracked separately instead of miscounted as loose parts.
- Evaluated the geometry-current 41-segment/37-joint/74-pin/4-end-tie
  stitch-rail study, then deliberately excluded all 119 optional printed
  pieces per level from the baseline because it lacked a proven interface
  benefit and risked a second thermal loop. The active cassette chassis is
  rail-free; optional half-laps, combs, pins, and ties receive zero installed
  count and zero structural credit.
- Added nine positively caught diaphragm-key keeper strips per level. Each
  fixed crown has one left-owned keeper opposite the fixed-right crown pin,
  plus one independently caught
  visible-front tie; floating-pier keys are trapped by the integral corbel
  bearing caps.
- Replaced eleven separate saddles and eleven saddle pins per level with
  full-width lock-clearing bearing caps integral to the X-corbels.
- Added seven deterministic nominal drawings covering the plan, 3/6 elevation,
  two-level placement, exploded joinery, crown sequence, X-corbel paths, and
  corner ownership/clearance.
- Added a compact neutral-3MF instance writer and strict package inspector so
  the 258/516-object sets can share repeated mesh payloads while preserving one
  uniquely named build object per physical print.
- Completed all 49 watertight source STL families and all five neutral,
  model-only 3MF packages: 8 print-first prototypes, 49 unique catalog objects,
  25 worst-case-bay objects, 258 one-level objects, and 516 selected two-level
  objects.
- Generated and reconciled the one-/two-level schedules, seven drawings,
  model/slice/validation reports, and cryptographic artifact manifest. The
  software release checker passes while retaining explicit physical blockers,
  zero wall bores, no G-code, no load rating, and `performed: false` slicing.
- Recorded repeat-weighted CAD-solid context of 16.000337 kg per level and
  32.000674 kg for two levels. No print-time estimate is available until the
  exact printer, nozzle, black-PETG product/drying method, profile, supports,
  and plate layout receive an authoritative retained slice.
