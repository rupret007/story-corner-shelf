## [Unreleased] — r6 Triadic Palatine all-PETG development

Status: **experimental, unrated, model-only, and blocked from overhead
production use**. No tested load rating exists.

### Added

- Original two-level, same-elevation inside-corner L architecture whose shelf
  body, cassettes, tied-arcade halves, X-corbels, joinery, keeper strips,
  facade, pins, cross-keys, and ornament are printed in black PETG.
- Explicit nonprinted boundary limited to suitable metal structural wall screws
  with integral heads or compatible metal washers into verified wood studs or
  purpose-installed blocking.
- Nominal 6 in-deep fitted plan for 60/36 in walls: six through bays plus three
  return bays, nine total bays, and seven plus four independently wall-fastened
  supports per level.
- Two complete independent L levels at provisional +12 in and +33 in shelf-top
  offsets above the outlet top, with 21 in provisional top-to-top spacing and
  upper-first installation.
- Deterministic plan math, position-specific half-bay cassette planning,
  rail-free seam planning, and exact physical-object inventory.
- Per-level installed inventory of 258 printed objects: 225
  chassis/joinery/retention objects plus 33 isolated, removable, zero-credit
  ornament objects; 516 objects for the selected two levels. Coupons and spares
  are additional.
- Repeat-weighted CAD-solid context of 16.000337 kg per level and exactly
  32.000674 kg for the two selected levels at the configured 1.27 g/cm3 density;
  this is neither sliced mass, finished tare, print time, nor a load rating.
- Governing SVG plan, elevation, two-level, exploded joinery, crown, X-corbel,
  and corner sheets with nominal/unverified/model-only warnings.
- Read-only audits of the owner-supplied reference 3MFs and documented research
  provenance without copying or redistributing third-party meshes.
- The exact-6-plus-3 two-level artist rendering as the current visual-intent
  hero, the earlier two-level rendering as preserved visual-development
  history, and the reproducible prompt. Generated drawings govern dimensions
  and counts.

### Changed

- Lowered the hidden structural spring/crown from the original 60/152 mm
  visual order to 46/138 mm after exact solid intersections proved the curved
  rib occupied the cassette front chord. The removable facade preserves the
  60/152 mm palace silhouette with zero structural credit.
- Re-sprung the hidden rib from `u = 28.8 mm` at the inner capital face rather
  than the support center after swept-volume tests proved the old rib occupied
  its compact clevis. This preserves a real 0.4 mm housing clearance and makes
  the through rib essentially semicircular without carving away a collision.
- Replaced the earlier whole-half longitudinal slide with a collision-aware
  final-X vertical lift. Each arcade half now enters three open-bottom cassette
  receivers plus one open-bottom spring receiver at its final run coordinate,
  then receives two accessible top quarter-turn cross-keys and one accessible
  spring cross-key.
- Changed the rear crown stabilizer to an upward-from-below bridge with a hard
  stop and one accessible fixed-right anti-drop/reverse-slide pin. Top-down
  insertion, a second fixed pin, and friction-only retention are prohibited.
- Separated nine locally fixed crown seams from seven thermally floating
  supported-pier seams. Added one left-owned positive diaphragm-key keeper
  opposite the fixed-right pin ear and one independently caught visible-front
  tie at each crown; floating
  pier keys remain trapped by the integral corbel cap through their qualified
  axial travel.
- Replaced eleven separate saddles and eleven saddle pins per level with a
  full-width lock-clearing bearing cap and locator ridges integral to each X-corbel,
  removing two tolerance-sensitive interfaces and reducing printed dead mass.
- Removed the geometry-current optional study's 41 stitch-rail segments, 37
  half-lap joints represented by 74 pins, and 4 end ties per level from the
  installed baseline. The study therefore represents 119 optional printed
  objects, not 122. Interface review found no proven benefit and identified a
  second thermal-loop risk. Rails/half-laps remain only an optional,
  noninstalled, zero-credit rail-on/rail-off research question.
- Formalized the through-arm ownership of the 6 x 6 in corner and a floating,
  nonstructural two-piece corner finish instead of a rigid PETG L tie. The
  structural return now begins at 177.55 mm, beyond the complete 13.2 mm
  removable facade and its 4.4 mm service stroke; its removable return-corner
  finish cantilevers back to a 173.15 mm all-solid leading plane and is removed
  first for service. Asymmetric 27.0325 / 31.4325 mm return insets preserve the
  225.07 mm three-bay rhythm and unchanged far-end station.
- Froze the five canonical package IDs and model-only filenames in the package
  source contract: `print_first_prototypes` /
  `MODEL_ONLY_R6_PRINT_FIRST_PROTOTYPES.3mf`, `unique_parts_catalog` /
  `MODEL_ONLY_R6_UNIQUE_PARTS_CATALOG.3mf`,
  `worst_case_one_bay_qualification` /
  `MODEL_ONLY_R6_WORST_CASE_ONE_BAY_QUALIFICATION.3mf`, `one_level_l` /
  `MODEL_ONLY_R6_ONE_LEVEL_L.3mf`, and `two_level_full_project` /
  `MODEL_ONLY_R6_TWO_LEVEL_FULL_PROJECT.3mf`. The deterministic build now emits
  and validates all five names; a name by itself still does not imply physical
  qualification or permission to install.
- Treated the near-semicircular Roman rib as part of a mixed-action closed
  tied-spandrel candidate frame, not as an assumed pure-compression arch.
- Limited Egyptian influence to a shallow cavetto and Art Deco influence to
  restrained, removable sunbursts, chevrons, and stepped-keystone detail. Fine
  ornament receives zero structural credit.
- Preserved the r5 hybrid architecture under `reference/hybrid_r5/` as a
  separate fallback rather than rebuilding or silently discarding it.

### Safety and qualification

- Kept production wall-fastener bores, head seats, bosses, and driver tunnels
  hard-blocked until the exact screw, head/washer, embedment, wall finish,
  framing, and utility-clearance method are measured and regenerated.
- Prohibited printed wall anchors, primary hollow-wall anchors, structural
  adhesive, cross-level load ties, rigid corner ties, hidden wall-side service,
  and vertical load credit for cross-keys/pins/ornament.
- Kept all 3MFs model-only with no embedded G-code while printer model, nozzle,
  build plate, black-PETG product, and slice settings are unconfirmed.
- Defined staged coupons, representative wall-bearing and component tests,
  worst-case 241.935 mm full-bay testing, matched arch-on/arch-off observation,
  unloaded full-corner fit, separate distributed/front-edge/crown-point/
  asymmetric-torsional load cases, whole-article thermal cycling, sustained
  checkpoints at 1 hour / 24 hours / 7 days / 30 days / 90 days, 72 hours
  unloaded recovery plus teardown, and a separately printed destructive
  load-to-failure specimen.

### Current software-model release-candidate evidence

- Complete mesh integration, exact schedules, all five model-only 3MF packages,
  validation/model/slice reports, and the cryptographic manifest are generated
  and pass the current software release checks. No embedded G-code exists.
- No authoritative print-time estimate exists because no printer, nozzle,
  black-PETG product, drying method, or production slice profile is confirmed;
  the slice report intentionally records `performed: false`.
- Real wall dimensions, corner angle/bow, framing/blocking, wall build-up,
  fastener, storage dimensions/weights, target load, printer, nozzle, build
  plate, black-PETG product, service temperature, and acceptance limits remain
  qualification gates.
- Completion of software validation cannot be represented as physical capacity
  evidence or permission for overhead installation.

### Rights

- The repository currently has no `LICENSE` file. Public visibility does not
  grant permission to copy, modify, redistribute, or sell the project.
