# Changelog

Design revisions are named in `config.json`. The project has not been assigned a public semantic version.

## Unreleased — `triadic_palatine_fitted_l_corner_r5`

### Added

- **Triadic Palatine Order** visual system, governed by a 3–6–9 composition rather than unrelated ornament.
- Three segmental arcade bays on the return arm and six on the through arm, split into 18 handed fascia halves that remain within the declared 180 mm saved-orientation envelope.
- Nine floating 18 x 24 mm keystone seam covers.
- Eighteen removable face-up entablature overlays, each with nine dentils, three triglyph groups, and three continuous cornice orders.
- Integrated 3:4:5 spandrel voids, 2.4 mm archivolt shadow reveals, and six-flute shared piers with shallow projected bases and capitals.
- Central 11 mm patera relief on every removable entablature overlay.
- Full-height Palatine outer endcaps and re-entrant corner pilaster.
- A 42 mm through-owned groin-vault soffit with diagonal ribs and nine-petal boss; generated clearance to the nearest support plane must remain at least 10 mm.
- A true-scale Palatine detail coupon in addition to the corner gauge and full-stack fascia coupon.
- Exact nominal decorative elevation: `generated/palatine_elevation.svg`.
- Final r5 design-intent rendering: `generated/artist_rendering_triadic_palatine_order.png`.

### Geometry and engineering changes

- Installed shelf-back offset is now a **per-run field value**. The long and short walls are measured independently; the perpendicular wall's installed offset controls each deck's inside start.
- The square-footprint angle gate is tightened from ±1° to ±0.25°.
- The generator derives angular edge shift across the 203.2 mm depth, enforces at least 0.6 mm residual nominal clearance from the 1.6 mm plywood gap, and rejects a configured angle gate above the approximately 0.282° residual-derived limit.
- Field support centers must be finite and at least 2 in apart under the current independent-support development guard.
- All top tiles now use the common 0.25 mm plan radius, which is no greater than half the 0.6 mm seam.
- The plywood-span sanity check now uses a 30 lb/ft total development line-load proxy. It is above the approximately 24.3 lb/ft contents-selection density only to include a rough unmeasured dead-load allowance; it is not measured demand, a safety factor, or a rating.
- Per-run measured shelf-arm dead-load fields were added.

### Rear-curb and attachment changes

- The return curb now starts on its own plywood at station 8.750 in instead of extending through the corner zone.
- A separate 172.6 mm corner-side curb remains on the through-owned corner square and stops before the plywood joint.
- Rear-curb ends are arm-specific: nominally 115.581 mm return and 126.481 mm through.
- Rear-curb nominal count remains 17: eleven universal centers, four arm-specific ends, one through-zone corner-side piece, and one fitted L replacement.
- The installed curb stack is explicit: 2.0 mm top tile, 2.4 mm curb base above it, and 17.0 mm upright top from the deck datum.
- Straight curb pieces contain one 8 x 4.4 mm clearance slot; the L replacement contains one per arm. Matching tiles are field-drilled only after final layout and underside-clearance verification.
- Each Palatine fascia half now uses holeless, full-depth upper/lower channel capture around the real shelf stack. The lateral train is assembled before the two outer endcaps and re-entrant corner cover; a tiny qualified removable silicone dot inside each channel prevents creep and rattle without drilling or notching the continuous steel angle.
- The finish policy now distinguishes qualified removable silicone, curb and groin-vault screws, captured fascia channels, own-segment entablature retention, floating keystones/pilaster, and removable endcaps.

### Package changes

- The nominal full print set is **101 model-only objects**: 98 installed finish parts plus three print-first objects. The separate parts catalog contains one object per unique mesh family.
- Estimated nominal PETG is **2.45 kg packaged** and **2.42 kg installed**, derived from mesh volume and nominal density.
- Mass estimates exclude purge, supports, failures, spares, fasteners, plywood, and steel.
- Individual r5 meshes plus `MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_PARTS_CATALOG.3mf` and `MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_FULL_PRINT_SET.3mf`, cut/support plans, validation, hashes, and documentation are regenerated under the new names.

### Safety

- The hybrid load path is unchanged: plywood and steel carry storage load; every printed architectural part has zero structural credit.
- A visually all-PETG finish does not authorize a structurally all-PETG shelf or printed wall bracket.
- Both arms remain independently supported, and perpendicular brackets require a physical dry fit.
- Keystones and the corner pilaster are fixed on one side and float across the other; the groin vault stays on the through deck and never bridges the joint.
- No tested load rating is claimed.
- No embedded G-code is included because the printer, nozzle, plate, and PETG product remain unconfirmed.

## Superseded development — `dual_run_modular_fitted_l_corner_r4`

- Established the fitted same-height L with explicit 5 ft through and 3 ft return ownership.
- Added square-mating corner quadrants, fitted fascia/rear-curb corner pieces, absolute support coordinates, model-only 3MFs, and deterministic validation.
- Used one global provisional installed shelf-back offset, a ±1° angle gate, a rear-curb layout that did not yet isolate the plywood joint, and the plain modular fascia.
- Its 68-object / 2.12 kg package figures apply only to r4 and are superseded by r5.

## Archived — `dual_run_modular_full_wall_r3`

- Used two independent nominal 35.75 and 59.75 in wall-to-wall decks.
- Added universal 6 in-pitch centers, symmetric parametric ends, deterministic 3MF packages, artifact hashes, repository checks, and GitHub Actions.
- Superseded because two independent full-depth decks do not define a physically fitted same-height inside corner.
- Preserved locally outside the publishable repository tree.

## Archived — `dual_run_engineered_prototype_r2`

- Used separate exact-width PETG module families for nominal 3 ft and 5 ft runs.
- Superseded by the interchangeable center/end module system.
- Preserved locally outside the publishable repository tree.

## Archived — A1 mini 12 in assumption

- Earlier 12 in-deep, three-level files and A1 mini slicer assumptions.
- Not compatible with the active 8 in fitted-L design and not production-ready.
- Preserved locally outside the publishable repository tree.
