# R10 design memory: never omit these rules

Use this as the short checklist before changing CAD, generators, tests,
documentation, slicing, or print order. The detailed controlling contract is
[`DESIGN_REQUIREMENTS.md`](DESIGN_REQUIREMENTS.md). If a proposed change
conflicts with either file, stop and resolve the conflict explicitly; a chat
summary is not permission to drop a rule.

## Scope and safety

- First release candidate: lower shelf only, 61.25 in first wall, top at 68 in,
  152.4 mm projection.
- Outlet top is approximately 53.5 in; keep the faceplate, plugs, cords, and
  service screws usable.
- Current rating is **0 kg / 0 lb**. No wall drilling, installation, stored
  load, or production claim until every physical gate and independent review
  passes.
- The 45 kg distributed and 9 kg front-point values are qualification targets,
  never ratings. Measure finished dead mass and include its physical effect
  exactly once in service demand. At 1.5x proof, the installed shelf supplies
  `D`; add `0.5D` in a representative distributed pattern plus the factored
  external contents/point load. Never omit or double-count dead mass.

## Printed Lincoln-log structure

- Predominantly SUNLU PETG; no aluminum or steel shelf chassis. Metal is
  limited to the candidate wall screws and one washer per screw.
- Seven 31.75 mm-wide supports on exact 10 in centers create six independent
  bays. Do not remove an intermediate support for appearance.
- Each bay: two cassette halves, three captured PETG splice logs at rear /
  center / front, positive shoulders, and three independent one-log retainers.
- Each log retainer closes its own left-half top access with an integrated
  flush cap; a separate loose debris cover is forbidden. Use the true notched
  final-mesh midpoint section, never the gross 20 x 24 mm rectangle, in every
  geometry comparison.
- Each cassette/support contact gets its own bay-local front-inserted retainer.
  Insert straight, then shift exactly 2.4 mm toward that bay so the rear dog
  sits behind its positive shoulder; keep the authored front paddle 4.0 mm
  proud so it remains hand-removable. All 30 keys are retention-only;
  uninterrupted lands and shoulders carry gravity. Interior left/right
  functions may never be shared; friction and snap receive no credit.
- Each cassette end bears directly on one broad support half-land. Locators,
  anti-lift retention, keys, friction, snaps, and adhesive receive no sustained
  vertical-load credit.
- A damaged bay must remain independently removable; no joint may unzip the
  full run.
- Preserve 0.35 mm midpoint, support-line, and endpoint seams. The fascia is
  visually continuous but physically segmented; zero-gap assembly is forbidden.
- Seven supports x three 7.0 mm authored candidate bores = 21 GRK RSS 90306
  candidates and 21 single L.H. Dottie FW14 washers in one wall. Bore drops
  below the shelf underside are 19.05 / 79.375 / 139.7 mm. Every washer bears
  on a full-solid 27.025 mm outer-diameter surface land; no counterbores. This
  is not a drilling schedule. After the field stack and fixture plan are
  reviewed, the controlled-lot plan is 100 exact screws and 100 FW14 washers:
  96 reserved across qualification plus possible final installation and four
  unallocated spares.
- All primary screws require verified continuous blocking or an independently
  engineered equivalent. Generic hollow-wall anchors receive no primary
  structural credit.
- The loose washer over PETG is outside ESR-2442, and current GRK documents
  conflict on nominal thread length. Received dimensions and independent
  connection review control; catalog assumptions do not.

## Form follows the load path

- Visual language: black PETG Roman aqueduct / Art-Deco arcade with stepped
  keystones and fascia.
- Intermediate visible corbel drop: **76.2 mm**. The complete **158.75 mm**
  structural wall strap remains hidden and may not be shortened.
- Outer-bookend visible emphasis: **120.65 mm**. Use it only at the far-left
  endpoint of this wall and the eventual far-right endpoint of the return wall.
- Roman recesses, curves, steps, and keystones are additive ornament and receive
  zero independent structural credit. Never thin a strap, compression web,
  chord, bearing land, cassette skin/web, dovetail, screw land, or washer land.

## Cable pegs: exact frozen interface

- The eventual L-shaped level has exactly **two outer cable bookends**: far-left
  through-wall endpoint and far-right return-wall endpoint.
- Each outer bookend has exactly one fused **two-socket** receiver. Both sockets
  face inward and use 0.4 mm clearance per face plus 8 mm service lift/drop.
- Rebuild and requalify that fusion on the R10 bookend dimensions; never paste
  the R9 attachment mesh onto the new structural core and call it inherited.
- Print two flush blanks and one multi-cable comb/hook for each active
  bookend. Blank unused
  sockets so the installation reads as normal furniture.
- The first-wall prototype activates only the far-left receiver.
- No cable rail, peg, receiver, or module belongs on an intermediate support,
  the through-side terminal/corner placeholder, or the inside corner.
- Cable parts receive **zero structural credit**.

## Print and release discipline

- Bambu Lab A1 mini, physical 0.4 mm nozzle, Textured PEI plate; SUNLU standard
  black PETG ASIN `B0D1KC72YP` with lot and drying record.
- `SUNLU PETG @BBL A1M 0.4 nozzle`; `0.20mm Strength @BBL A1M`; 6 walls,
  25% grid, 5 top / 3 bottom, Support Off, 5 mm outer brim, 0.1 mm gap.
- Authored orientation, 100% scale, one structural part per plate, Preview and
  first-layer checks. No auto-orient, auto-scale, casual mirroring, structural
  sanding/reaming, or silent slicer repair.
- Fail-fast order: actual midpoint interface articles -> one actual bay -> far-left cable set ->
  complete tabletop set -> sacrificial framed-wall mockup. Confirm the plate is
  empty and ask the operator before every printer start.
- First measure the maximum service temperature. Proof, 1000-hour creep at that
  measured maximum plus 5 degrees C, recovery, destructive testing, and
  independent review are all mandatory. A pass at one gate never creates a
  rating.
