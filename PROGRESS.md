# Story Corner r6 development checkpoints

This log records software/design evidence only. It is not evidence of physical
capacity, installation readiness, or a load rating.

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
