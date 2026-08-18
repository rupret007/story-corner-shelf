# R11 non-negotiable design requirements

This is the controlling memory contract for every R11 generator, model,
drawing, test, bundle, guide, and slice record. If a proposed change conflicts
with this file, stop and issue a reviewed revision. Conversational shorthand,
an attractive render, or a successful R10 article is not permission to omit a
requirement.

> **Engineering study only. Rated load: 0 kg / 0 lb.** R11 v1 hard-forces
> printing, drilling-coordinate release, wall installation, test loading,
> stored load, and public capacity claims to false regardless of input
> completeness.

## Revision boundary

- R11 supersedes R10 only as the active **reduced-part architecture study**.
- [R10](../r10/README.md) remains immutable historical qualification evidence.
- R10 meshes, dimensions, fit observations, and test records are provenance,
  not automatic R11 passes.
- R11 geometry is not finalized until generator integration produces
  deterministic saved meshes, manifests, validation, release-status records,
  assembly identities, and passing tests. Documentation targets never outrank
  measured generated geometry.

## Scope and field facts

- First milestone: lower shelf only on the measured 61.25 in / 1555.75 mm
  first wall, with shelf top at 68 in and projection at 152.4 mm / 6 in.
- The return wall, upper 84 in shelf, and final inside corner are later work.
- The outlet faceplate top remains approximately 53.5 in. Faceplate screws,
  both receptacles, plugs, cords, and removal/service motion must remain usable.
- Wall length was observed at more than one height, but final wall bow, taper,
  trim, corner angle, substrate, utilities, and framing/blocking require
  recorded field verification before any drilling map or installation release.
- Current rating remains exactly **0 kg / 0 lb**.

## First-wall topology and counts

- Use six independent bays and seven 31.75 mm-wide supports for the measured
  first wall. Maximum support-center pitch is 254.0 mm.
- Use exactly three authored candidate wall bores per support; the first-wall
  candidate therefore remains 21 screws and 21 single FW14 washers.
- The supplied-kit target is 28: seven supports, 12 half-decks, six bay
  keystones, two flush cable blanks, and one cable comb/hook.
- Because S0 has two sockets but the kit supplies three interchangeable cable
  modules, the maximum simultaneously installed count is 27: all 25
  structural/retention articles plus exactly two cable modules.
- The safe unbatched plan is 28 one-article starts.
- The unverified batched production-start target is 21: seven support plates, 12
  one-half-deck plates, one six-keystone plate, and one three-cable-module
  plate. It is not valid until actual packing, orientation, brim, and Preview
  are verified.
- Batch nesting changes starts only. It never changes the 28-kit count,
  27-installed limit, manifest identities, BOM, or qualification scope.
- Qualification parts, retries, spares, and destructive duplicates do not
  count toward the 28 kit articles or either production-start plan.
- Bay 0 and bay 5 each use terminal left and terminal right halves: four
  terminal halves at 162.175 mm. Bays 1-4 use eight regular halves at
  154.325 mm. R11 v1 refuses layouts with fewer than two bays.
- Do not reduce the seven-support count merely to lower print count. A support
  may move only through a recomputed, reviewed layout that preserves pitch,
  bearing, obstacle, blocking, and printer-envelope constraints.

## Integrated Lincoln-log structure

- Each bay contains two full-depth, 32.0 mm candidate-height half-decks with
  rear, center, and front integrated load ribs.
- The halves use three reciprocal cross-laps with an initial 55.0 mm overlap
  qualification candidate. The overlap is not finalized until the true saved
  mesh, minimum net sections, print orientation, and physical testing pass.
- Cross-lap faces and positive body shoulders carry gravity and shear through
  broad bearing. Friction, snap preload, wedge preload, glue, and cosmetic
  fascia receive no sustained vertical-load credit.
- Each half-deck end bears directly on the broad land of its adjacent support
  capital. The initial minimum physical bearing target remains 15.70 mm.
- The support/half-deck interface must use the generated integral, reversible
  positive capture: lower with 2.0 mm clearance over fixed lug heads, slide
  32.0 mm wallward, then gravity-settle 2.0 mm into the higher terminal
  pockets behind a solid 8.4 mm roof/shoulder. Reverse is lift 2.0 mm, slide
  32.0 mm outward, then lift clear. Generator validation and physical cycling
  must prove every pocket, shoulder, clearance, stop, and sweep.
- Each bay has one separate removable positive keystone that blocks only
  half-to-half X separation. The keystone receives zero support-capture,
  sustained vertical-load, and bending credit; it may not be credited with
  preventing reversal from the fixed support lugs.
- No separate R10-style splice logs, log retainers, support-retainer bars,
  hidden metal beam, aluminum tube, steel strap, or permanent adhesive belongs
  in the R11 base architecture.
- A damaged bay must be removable independently. One missing keystone, one
  local failure, or one disassembly action may not unzip an adjacent bay.
- Preserve 0.35 mm candidate clearances at midpoint seams, interior support
  lines, and wall endpoints unless a versioned tolerance study demonstrates a
  safer value. Zero-gap assembly and forced closure are forbidden.
- The final-mesh governing rib section, including every cross-lap, notch, and
  access, must meet or exceed the R10 comparison floors of
  `I = 8263.957 mm^4` and `Z = 949.016 mm^3`. These are geometry floors only;
  they contain no PETG allowable and create no load rating.
- The generator must report actual net area, centroidal second moment, elastic
  section modulus, bearing length, engagement, minimum wall, and transformed
  build envelope from the saved meshes—not from an uncut rectangle or source
  intent.

## Wall support and hardware interface

- Every support retains a complete 158.75 mm structural wall strap and three
  7.0 mm candidate bores at 19.05, 79.375, and 139.7 mm below the shelf
  underside.
- Every bore retains a full-solid 27.025 mm outer-diameter surface-bearing
  washer land. Counterbores, countersinks, stacked washers, and crushed PETG
  are forbidden.
- Candidate hardware remains GRK RSS Climatek 1/4 in x 3-1/2 in T25 part
  `90306` plus exactly one L.H. Dottie `FW14` washer per screw.
- Every primary screw axis requires verified continuous solid-wood blocking or
  an independently engineered equivalent. Generic hollow-wall and drywall
  anchors receive no primary structural credit.
- The GRK head / loose FW14 washer / PETG land stack is outside ESR-2442. The
  complete connection requires reviewed calculations and physical fixtures.
- Current GRK documents conflict on thread length. Measure the received 90306
  lot and resolve controlling dimensions before connection calculations.
- Printed bores are candidate fixture geometry, not a drilling schedule. Do
  not freehand drill or ream a structural R11 support.

## Structural appearance

- Visual language remains black PETG Palatine Moderne: compact Roman arcade,
  Art-Deco stepping, and a legible bay keystone.
- Ordinary intermediate supports retain the compact 76.2 mm visible drop while
  the full 158.75 mm wall strap remains structurally present.
- The far-left first-wall bookend may use the 120.65 mm visible emphasis. The
  future far-right return-wall endpoint may mirror the design intent only after
  authored geometry exists. The inside corner is not an outer bookend.
- Ornament is additive-only. It may not thin a wall strap, screw land, washer
  land, compression web, support capital, half-deck skin, load rib, cross-lap,
  bearing shoulder, or capture stop.
- Curves, arches, steps, fascia, and decorative keystone faces receive zero
  independent structural credit.

## Cable receiver invariant

- The eventual L-shaped level has exactly two outer cable bookends: far-left
  first-wall endpoint and far-right return-wall endpoint.
- This first-wall milestone activates only the far-left S0 receiver.
- S0 integrates exactly one inward-facing receiver with exactly two sockets.
- Each socket uses 0.4 mm clearance per face and 8 mm service lift/drop.
- The first-wall supplied module set contains exactly two flush blanks and one
  multi-cable comb/hook. This is a three-module supplied set, not a
  three-module installed state: exactly two sockets may be occupied at once,
  either by two blanks or by one blank and the comb/hook. Every unused socket
  is blanked in normal furniture use.
- No receiver, rail, peg, or module belongs on an intermediate support or the
  future inside corner.
- Cable articles receive zero shelf-load credit and may carry representative
  cables only.

## Printer and saved-mesh requirements

- Printer baseline: Bambu Lab A1 mini, physical 0.4 mm standard-flow nozzle,
  Textured PEI plate.
- Material: SUNLU standard black PETG, 1.75 mm, ASIN `B0D1KC72YP`, with label,
  lot, drying, ambient, and spool-change records.
- Filament profile: `SUNLU PETG @BBL A1M 0.4 nozzle`.
- Process profile: `0.20mm Strength @BBL A1M`.
- Use 0.20 mm layers, six walls, 25% grid, five top and three bottom layers,
  Support Off, 5 mm outer brim, and 0.1 mm brim-object gap.
- Half-decks print one per plate in their authored flat high-load orientation.
  Supports print one per plate in their authored orientation. A batched
  keystone or cable plate is allowed only after actual nesting and first-layer
  separation are proven.
- Every part must fit the true A1 mini envelope at 100% XYZ scale after brim,
  gap, and 2 mm edge reserve are included. No auto-scaling, auto-orienting,
  casual mirroring, silent mesh repair, or orientation change to suppress a
  warning.
- Generated neutral bundles contain no G-code, BG-code, embedded toolpath, or
  print authorization. Slice locally from identified model-only files.

## Customization and refusal

- The layout solver accepts measured wall length, shelf depth, printer build
  volume, support width, maximum pitch, joinery candidates, seam/endpoint
  clearances, obstacles/services, trim/corner envelopes, and verified blocking
  data. [CUSTOMIZATION.md](CUSTOMIZATION.md) defines the equations.
- Exact input records must include measurement locations and uncertainty,
  wall bow/taper/corner angle, endpoint/trim/service envelopes, every protected
  utility/no-drill envelope, substrate layers and thicknesses, blocking
  geometry and verification method, printer/nozzle/plate/process identity,
  filament lot/drying, service temperature/humidity/sunlight or heat sources,
  intended contents and load envelope, and cable bend/service sweeps. Unknown
  values remain unknown and block installation-oriented output.
- For arbitrary walls, use `n = ceil((L - w) / p_max)`, supports `n + 1`,
  actual pitch `p = (L - w) / n`, and screw candidates `3(n + 1)`.
- R11 v1 must refuse a wall requiring fewer than two bays. The single-bay
  double-terminal ownership and capture topology are not authored or qualified.
- The solver must refuse, or emit an explicit non-installable study result,
  when inputs are missing, a part cannot fit the printer with reserve, a
  support/fastener conflicts with a protected envelope, pitch or bearing floors
  fail, blocking is unknown, or any required validation is absent.
- Never delete a support, shrink a load rib, scale a structural model, or move
  a screw around an obstacle without recomputing and requalifying the complete
  system.

## Release and evidence requirements

- R11 v1 always emits `print_authorized: false`,
  `drilling_coordinates_released: false`,
  `wall_installation_authorized: false`, `test_load_authorized: false`, and
  `rated_load_kg: 0.0`. Input changes and passed study gates cannot flip them;
  doing so requires a later reviewed version.
- No print from R11 v1. A later print-capable revision would still require
  generator integration, deterministic regeneration, manifests, model-only
  files, transformed-envelope checks, topology/mesh validation, documentation
  checks, slice Preview, and fresh explicit human permission for that exact
  job.
- No wall drilling or installation until field blocking/substrate verification,
  exact connection review, support fixtures, full framed-wall mockup, proof,
  creep, recovery, destructive testing, and independent structural review pass.
- The 45 kg distributed and 9 kg front-edge point values are qualification
  objectives, not ratings. Dead mass is measured and included exactly once.
- Sustained creep uses a fresh conforming assembly for 1000 hours at measured
  maximum service temperature plus 5 degrees C.
- Only an independent structural reviewer may define a nonzero allowable load,
  installation conditions, inspection interval, and retirement criteria.
- A failed gate blocks all later gates. Never spend the next print tranche to
  conceal an unresolved failure.

The compact day-to-day checklist is [GUIDELINES.md](GUIDELINES.md). This file
controls if the two are ever read differently.
