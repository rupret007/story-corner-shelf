# R11 design memory — check before every change

Use this checklist before editing CAD, generators, tests, documentation,
packing, slicing, or print order. The detailed controlling contract is
[DESIGN_REQUIREMENTS.md](DESIGN_REQUIREMENTS.md).

## Status and scope

- **0 kg / 0 lb; engineering study only.** R11 v1 hard-forces print,
  drilling-coordinate release, installation, test load, stored load, and
  public capacity claim to false regardless of supplied evidence.
- R11 is the reduced-part successor study. Keep
  [R10 immutable](../r10/README.md); do not treat R10 evidence as an R11 pass.
- First milestone only: 1555.75 mm first wall, lower shelf top at 68 in,
  152.4 mm projection, outlet top approximately 53.5 in.
- Geometry remains provisional until generator integration, saved-mesh
  measurement, manifests, validation, slicing, and physical gates agree.

## Math and architecture

- `n = ceil((L - w) / p_max)`; supports `= n + 1`; pitch
  `p = (L - w) / n`; candidate screws `= 3(n + 1)`.
- First wall: `L=1555.75`, `w=31.75`, `p_max=254` -> six bays, seven supports,
  254 mm pitch, and 21 screw/FW14 pairs.
- Supplied kit: seven supports + 12 authored half-decks + six bay keystones +
  two blanks + one comb/hook = **28 articles**.
- At most **27 articles are simultaneously installed**: the 25
  structural/retention articles plus two modules in S0's two sockets. The third
  cable module remains off the shelf.
- Safe unbatched plan: **28 starts**, one article per plate. Unverified batched
  target: 7 support starts + 12 one-half-deck starts + 1 batched-keystone start
  + 1 batched-cable start = **21 starts**, subject to real packing and Preview.
  Batching changes starts only, never kit count, installed state, identities,
  BOM, or qualification scope.
- Bay 0 and bay 5 each use terminal left and right halves: **four terminal
  halves at 162.175 mm**. Bays 1-4 use **eight regular halves at 154.325 mm**.
  R11 v1 refuses a one-bay wall.
- Keep all seven supports. Lowering part or start count may not increase pitch,
  remove redundancy, reduce bearing, or bypass blocking/obstacle rules.
- Each bay has two integrated three-rib half-decks, a 55 mm initial reciprocal
  cross-lap candidate, broad direct support bearing, and an integral reversible
  capture: lower with 2 mm lug-head clearance, slide 32 mm wallward, then
  gravity-settle 2 mm behind the solid 8.4 mm roof/shoulder. Reverse is lift 2,
  slide 32 outward, lift clear.
- The positive removable keystone blocks only half-to-half X separation. It
  receives zero support-capture, gravity, or bending credit.
- Broad faces and shoulders carry gravity. Keystone, friction, snap, glue,
  shallow locators, ornament, and cable parts receive zero sustained credit.
- No separate splice logs, log retainers, support-retainer bars, hidden metal
  beam, aluminum tube, or permanent adhesive.
- A bay must remain independently removable; no local action may unzip the run.
- Candidate floors: 15.70 mm support bearing, 0.35 mm seams, and true-net
  `I >= 8263.957 mm^4`, `Z >= 949.016 mm^3`. These are geometry comparisons,
  not capacity.

## Supports and hardware

- Full 158.75 mm wall strap; ordinary visible drop 76.2 mm; outer-bookend
  emphasis 120.65 mm only at the real outer endpoints.
- Three 7.0 mm candidate bores per support at 19.05 / 79.375 / 139.7 mm below
  the shelf underside, each with a full-solid 27.025 mm OD washer land.
- First-wall candidate: 21 GRK RSS Climatek 1/4 x 3-1/2 in T25 `90306` screws
  and exactly 21 L.H. Dottie `FW14` washers.
- No counterbores, countersinks, stacked washers, printed wall anchors, generic
  drywall anchors, freehand drilling, reaming, or crushed PETG.
- Every screw axis needs verified continuous blocking or an independently
  engineered equivalent. The loose-washer/PETG stack is outside ESR-2442 and
  requires its own reviewed fixture evidence.

## Appearance and cable features

- Black PETG Roman aqueduct / Art-Deco language; ornament is additive-only and
  receives no structural credit.
- Never thin skins, three load ribs, cross-laps, bearing/capture faces, support
  capitals, compression webs, straps, bores, or washer lands for appearance.
- Cable hardware exists only at the eventual two outer bookends. First wall
  activates only S0: one fused inward-facing two-socket receiver, 0.4 mm per
  face clearance, 8 mm service travel, two flush blanks, and one comb/hook.
- No cable receiver at intermediate supports or the inside corner. Blank every
  unused socket. Cable modules receive zero shelf-load credit.

## Print and release discipline

- A1 mini, physical 0.4 mm standard-flow nozzle, Textured PEI; SUNLU standard
  black PETG 1.75 mm ASIN `B0D1KC72YP`, recorded lot and drying cycle.
- `SUNLU PETG @BBL A1M 0.4 nozzle`; `0.20mm Strength @BBL A1M`; 0.20 mm,
  6 walls, 25% grid, 5 top / 3 bottom, Support Off, 5 mm outer brim, 0.1 mm gap.
- Authored orientation and 100% XYZ only. No auto-scale, auto-orient, casual
  mirror, silent repair, structural sanding/reaming, heat, lubricant, or force.
- R11 v1 always emits `print_authorized: false`,
  `drilling_coordinates_released: false`,
  `wall_installation_authorized: false`, `test_load_authorized: false`, and
  `rated_load_kg: 0.0`. No input or study-gate pass may change those values.
- A later print-capable revision would still require generator/bundle gates,
  an empty clean plate, exact Preview, and a **fresh explicit human yes** for
  that exact job. A prior yes never carries to a retry.
- A later print-capable revision must fail fast: generator/bundle -> actual
  cross-lap pair -> integral support capture -> one actual bay -> cable set ->
  full tabletop -> framed fixtures.
- No drilling/install/load until proof, 1000-hour elevated-temperature creep,
  recovery, destructive testing, and independent review all pass.
