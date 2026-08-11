# R10 non-negotiable design requirements

This file is the memory contract for every later R10 model, drawing, bundle,
README, and print instruction. A later revision must fail closed if it violates
one of these rules; conversational shorthand is not permission to drop one.

## Project and field scope

- The first deliverable is the **lower shelf only**, on the measured 61.25 in
  through/outlet wall, with its top at 68 in.
- The eventual upper shelf top remains 84 in. The measured return wall remains
  36.75 in. Neither is part of the first-wall release.
- Shelf projection remains 152.4 mm / 6.0 in.
- The top of the outlet faceplate remains approximately 53.5 in. No support,
  cable module, stored item, or cord path may obstruct the plate or plug access.
- Exact corner, wall bow, trim, framing/blocking, and substrate records remain
  required before wall drilling or installation.

## Structural intent

- Maximize practical capacity while keeping the shelf **predominantly 3D
  printed**. The active R10 architecture contains no aluminum or steel shelf
  chassis. Metal is limited to the exact wall screws and one washer per screw.
- Current rating remains **0 kg / 0 lb**. A target, simulation, catalog value,
  proof mass, or attractive print is never a released rating.
- Use seven 31.75 mm-wide supports on exact 10 in centers. Every bay is an
  independent structural cell; a failure may not unzip the full 61.25 in run.
- Every ordinary support is structural. Supports may not be deleted merely to
  simplify the appearance.
- Each support retains a full-height wall strap and three authored wall bores:
  7.0 mm candidate bores at 19.05 / 79.375 / 139.7 mm below the shelf underside.
  Each bore uses the selected GRK 90306 screw candidate, one USS Type A washer
  candidate fixed as L.H. Dottie part FW14, and a full-solid 27.025 mm
  outer-diameter surface-bearing land.
  Counterbores are forbidden. This candidate geometry is not a drilling
  schedule or wall-install authorization.
- The primary wall load path requires verified framing or continuous blocking.
  A generic drywall or hollow-wall anchor receives no structural credit.
- The GRK head/loose-FW14/PETG stack is outside ESR-2442 and requires an exact
  reviewed fixture program. Current GRK documents conflict on thread length;
  the received 90306 dimensions must be measured and reconciled before any
  connection calculation.
- Qualification hardware is a controlled 100/100 lot allocated as 12 for four
  support fixtures, 21 for mock-wall/proof, 21 for fresh creep, 21 for fresh
  destructive test, 21 quarantined for possible final installation, and four
  spares. Fixture hardware may never be reused in the closet.
- Long-term PETG creep, recovery, proof loading, and destructive testing are
  mandatory before any load rating. First measure the maximum service
  temperature; the sustained creep gate is 1000 hours at that measured maximum
  plus 5 degrees C.

## Lincoln-log modular architecture

- Each 10 in bay contains two printable cassette halves that bear directly on
  the two adjacent support capitals.
- Rear, center, and front printed **splice logs** bridge each cassette midpoint
  seam. All three use captured dovetail channels and broad shoulder bearing.
- Three independent removable retainers prevent axial log walkout, one per log,
  but receive no sustained vertical-load credit. No snap flexure, wedge
  preload, adhesive, or friction-only joint receives structural credit.
- Each log retainer carries its own integrated flush top-access cap; separate
  loose debris closures are forbidden. All section studies must use the true
  final-mesh notched midpoint properties, not a gross rectangular proxy.
- Each support capital is the crosswise Lincoln log: adjacent cassette ends
  bear on its two broad half-lands and use shallow locators plus an independent
  underside anti-lift key.
- There are 12 bay-local front-inserted support retainers, one per
  cassette/support contact, in addition to 18 independent log retainers. All
  30 are retention-only; the broad bearing land above every key remains
  uninterrupted. Interior left/right functions stay physically separate. Each
  support retainer inserts straight and then shifts 2.4 mm toward its bay to
  put a rear dog behind a positive shoulder. Its front paddle remains 4.0 mm
  proud for reversible hand removal; friction and snap receive no retention
  credit.
- The six bays are redundant structural cells. No joint creates one progressive
  61 in chain. No single loose key may release all three splice logs or affect
  an adjacent bay.
- Shelf cassette halves are 32.0 mm-high, full-depth printed torsion boxes with
  top and bottom skins plus rear, center, and front load webs.
- Preserve 0.35 mm at each midpoint seam and interior support line plus 0.35 mm
  at each wall endpoint. The fascia may look continuous but remains physically
  bay-segmented; zero-gap assembly is forbidden.
- Parts must remain replaceable one bay at a time. Permanent glue, solvent
  welding, hidden metal beam inserts, and destructive disassembly are outside
  the base design.

## Palatine Moderne appearance

- The shelf reads as a black PETG Roman aqueduct / Art-Deco arcade: repeated
  short structural arches, stepped keystones, and a continuous stepped fascia.
- Ordinary intermediate corbels have a compact 76.2 mm visible drop so the
  storage below remains useful. Their complete 158.75 mm structural wall strap
  remains hidden behind that shorter visual body; the visible outline is never
  permission to shorten the structural load path.
- The far-left outer bookend on this first wall may use a 120.65 mm visible
  drop for deliberate endpoint emphasis. The later far-right outer bookend on
  the return wall uses the corresponding emphasis; intermediate and corner
  stations do not.
- Ornament is additive-only. It may not thin a wall strap, compression web,
  saddle, log tongue, cassette web, screw land, washer land, or keyed interface.
- Intermediate arches stay short and storage-friendly. Stronger visual emphasis
  belongs only at the two outer bookends.

## Cable pegs and modules—never omit

- Cable organization exists **only on the two outer bookends per shelf level**:
  far-left through-wall endpoint and far-right return-wall endpoint.
- Each outer bookend carries exactly one fused two-socket receiver. The sockets
  face inward and use the proven 0.4 mm-per-face keyed gravity interface with an
  8 mm service lift/drop.
- R10 must port and requalify the fused receiver on its 31.75 / 19.05 / 158.75
  mm bookend; an R9 attachment mesh is provenance, not a drop-in R10 part.
- Print two flush blanks and one multi-cable comb/hook module for each active
  bookend. Unused sockets get blanks so the shelf reads as ordinary furniture.
- No cable rail, peg, receiver, or module is allowed on an intermediate support
  or at the inside corner. In particular, the replaceable through-side terminal
  / corner placeholder has no cable hardware; it is not the second outer
  bookend or a final measured corner.
- Cable hardware receives zero shelf-load or structural credit. Door/trim,
  cable-loop, snag, and removal clearances require physical verification.

## Printing contract

- Printer: Bambu Lab A1 mini, physical 0.4 mm nozzle, Textured PEI plate.
- Material: SUNLU standard black PETG, ASIN B0D1KC72YP, received-label and lot
  record required.
- Process baseline: `SUNLU PETG @BBL A1M 0.4 nozzle` plus
  `0.20mm Strength @BBL A1M`, six walls, 25% grid, five top and three bottom
  layers, Support Off, 5 mm outer brim, and 0.1 mm brim-object gap.
- Every saved part must fit 180 × 180 × 180 mm including brim, gap, and 2 mm
  extra reserve at every bed edge.
- Saved orientation, 100% scale, one-part plate, manifoldness, layer connection,
  Bambu Preview, and first-layer inspection remain mandatory. Auto-orient,
  auto-scale, casual mirroring, and slicer repair are forbidden.

## Release boundary

No R10 source may claim production readiness, wall-install authorization,
**field drilling or installation coordinates**, or a load rating until its
exact full-wall set has passed the staged fit, one-bay, full-wall, proof, creep,
recovery, destructive, and independent-review gates. Authored bore locations
inside a qualification support are permitted only when labeled prototype-
fixture candidates—not a closet-wall drilling schedule.

The short day-to-day checklist is [`GUIDELINES.md`](GUIDELINES.md). This file
remains the detailed controlling contract if the two are ever read differently.
