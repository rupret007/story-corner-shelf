# R11 integrated Lincoln-log shelf study

> **Engineering study only. Rated load: 0 kg / 0 lb.** R11 hard-forces print,
> drilling-coordinate release, wall installation, test loading, and stored
> load to false. No R11 v1 geometry is a printable release. A later reviewed
> version would still require the generator, saved-mesh, bundle, slicing,
> physical-fit, wall-fixture, creep, destructive, and independent-review gates
> in this directory.

R11 is the reduced-part successor study to the
[immutable R10 qualification baseline](../r10/README.md). R10 remains intact as
historical design evidence and provenance; R11 does not rewrite R10, convert an
R10 pass into an R11 pass, or make an R10 article part of an R11 shelf.

The [qualification-only exploded bay and first-wall topology diagram](visuals/r11_first_outer_bay_exploded_and_wall_topology.svg)
is a visual index to the candidate parts, motions, zero-credit boundaries, and
exact first-wall count arithmetic. It is not a fabrication or drilling drawing.

The objective is a shelf that behaves more like Lincoln logs: large printed
members overlap on broad, inspectable bearing faces and are held against
half-to-half X separation by a small positive keystone. This replaces R10's
separate splice logs, log retainers, and support retainers with geometry
integrated into the two shelf half-decks and the supports.

## Current status

R11 is a **design and generator-integration contract**, not a production model
set. The dimensions and counts below are candidate targets. They become
controlling only when generated files, manifests, saved-mesh measurements,
tests, Bambu Preview records, and physical articles all agree.

- First scope: lower shelf on the measured 61.25 in / 1555.75 mm first wall.
- Shelf top: 68 in above the floor.
- Shelf projection: 6 in / 152.4 mm.
- Outlet faceplate top: approximately 53.5 in; access must remain unobstructed.
- Architecture target: six independent bays on seven supports.
- Supplied-kit target: **28 printed articles**. Because the three supplied
  cable modules share two sockets, no more than **27 articles are installed at
  once**.
- Safe unbatched plan: **28 starts**, one article per plate.
- Batched production target after qualification: **21 starts**, unverified
  until both optional batch plates pass nesting and Preview.
- Wall-hardware candidate count: seven supports x three bores = **21 screws and
  21 FW14 washers**, unchanged from R10.
- Current rating: **0 kg / 0 lb**.

The return wall, 84 in upper shelf, final inside corner, drilling map, load
rating, and public production release remain outside this first R11 milestone.

## Candidate architecture

Each 254 mm planning bay is intended to contain:

1. one authored left half-deck with three integrated load ribs;
2. one authored right half-deck with matching reciprocal cross-laps;
3. a 55 mm initial overlap candidate at the rear, center, and front ribs;
4. direct, broad bearing on the adjacent support capitals;
5. an integral reversible positive support capture using a generated
   lower/slide/gravity-settle motion; and
6. one removable, positive Palatine/Art-Deco wedge or keystone that prevents
   half-to-half X separation but receives no support-capture or sustained
   vertical-load credit.

The expected dry assembly path is:

```text
interlock two three-rib half-decks off the supports
  -> lower with 2 mm clearance over the fixed lug heads
  -> slide 32 mm wallward
  -> gravity-settle 2 mm into terminal pockets behind solid 8.4 mm roof/shoulder
  -> seat one removable bay keystone against half-to-half X separation
```

The generated reverse sequence is lift 2 mm, slide 32 mm outward, then lift
clear. The exact generated assembly map and saved geometry control if any
documentation shorthand differs.

Gravity must travel through the half-deck skins and ribs, broad reciprocal
cross-lap faces, broad support lands, support compression webs and full-height
wall straps, then through the reviewed screw/washer/blocking connection. The
wedge, friction, snap preload, adhesive, ornament, and cable modules receive
zero sustained vertical-load credit. The keystone receives zero
support-capture credit; it does not prevent support-lug reversal.

Every bay remains an independently removable cell. A single loose wedge or a
damaged bay may not unzip the complete wall run. The final generator must prove
the integral support capture and reversible disassembly; if it cannot, the
architecture and the 28-kit/27-installed/21-batched targets must be revised
rather than hidden with extra hardware or forced fits.

## First-wall kit, installed-state, and start arithmetic

The candidate supplied kit is:

| Printed family | Kit articles | Safe unbatched starts | Target batched starts |
|---|---:|---:|---:|
| Supports, including the fused far-left cable receiver | 7 | 7 | 7 |
| Authored half-decks, one per plate in flat high-load orientation | 12 | 12 | 12 |
| Bay wedges / keystones, one per bay | 6 | 6 | 1 optional batched plate |
| Two flush blanks plus one multi-cable comb/hook | 3 | 3 | 1 optional batched plate |
| **Total target** | **28** | **28** | **21** |

Only two cable modules can occupy S0's two sockets at once: either two blanks,
or one blank plus the comb/hook. The third supplied module remains off the
shelf, so the maximum simultaneously installed count is 27. Batch nesting
changes starts only; it never changes kit quantity, installed-state limits,
article identities, BOM, or qualification scope.

The 21-start count is a production-planning target, not a slicing fact. Until
all six wedges fit together on one inspected A1 mini plate and all three cable
modules fit together on another without changing their authored orientations
or process, the safe plan is 28 one-article starts. Qualification prints,
failed prints, spares, and destructive-test duplicates are additional starts.

For the measured first wall:

```text
wall length L       = 1555.75 mm
support width w     = 31.75 mm
maximum pitch p_max = 254.00 mm

bay count n = ceil((L - w) / p_max)
            = ceil(1524 / 254)
            = 6

supports = n + 1 = 7
actual pitch p = (L - w) / n = 254.00 mm
screws = 3 x supports = 21
```

Support centers are therefore 15.875, 269.875, 523.875, 777.875, 1031.875,
1285.875, and 1539.875 mm from the left endpoint. The arithmetic is exact for
the recorded 1555.75 mm wall; it does not establish that any center has
blocking or is free of wiring, plumbing, trim, or outlet conflicts.

The initial CAD sizing worksheet uses a 55.0 mm overlap, 0.35 mm
endpoint/support-line/midpoint clearance, and 15.70 mm minimum physical bearing
target. It closes the first wall exactly:

```text
regular physical span  = 254.0 - 0.35 = 253.65 mm
terminal physical span = 253.65 + 31.75/2 - 0.35/2 = 269.35 mm

wall closure = 2*269.35 + 4*253.65 + 5*0.35 + 2*0.35
             = 1555.75 mm

regular half length = (253.65 + 55.0) / 2 = 154.325 mm
terminal candidate  = (269.35 + 55.0) / 2 = 162.175 mm
```

Bay 0 uses terminal left and terminal right halves, and bay 5 uses terminal
left and terminal right halves: **four terminal halves at 162.175 mm**. Bays
1-4 use **eight regular halves at 154.325 mm**. R11 v1 refuses a one-bay wall;
its two-terminal-end ownership has not been authored or qualified.

With a 5 mm brim, 0.1 mm brim gap, and 2 mm reserve at every bed edge, the
largest candidate half-deck footprint budget is approximately
176.375 x 166.600 mm. That is a planning calculation only. The generator must
measure the true transformed saved mesh and the slicer must confirm the actual
brim footprint inside the A1 mini's 180 x 180 mm bed without scaling.

See [CUSTOMIZATION.md](CUSTOMIZATION.md) for the general wall solver and its
fail-closed rules.

## Appearance and cable interface

R11 retains the black PETG Palatine Moderne language: a Roman aqueduct reduced
to compact structural arches, stepped Art-Deco fascia, and a legible keystone.
Ornament is additive-only and receives no structural credit. It may never thin
a half-deck skin or rib, cross-lap, support capital, compression web, wall
strap, bore land, or washer land.

Cable organization remains an invariant, not an optional memory:

- only the two eventual outer bookends per L-shaped level receive cable
  hardware;
- the first-wall study activates only its far-left S0 bookend;
- S0 has one fused, inward-facing receiver with exactly two keyed sockets;
- the set contains two flush blanks and one multi-cable comb/hook;
- the interface retains 0.4 mm clearance per face and 8 mm service lift/drop;
- intermediate supports and the future inside corner receive no receiver; and
- every cable article receives zero shelf-load credit.

## Exact material and process baseline

- Bambu Lab A1 mini, physical 0.4 mm standard-flow nozzle, Textured PEI plate.
- SUNLU standard black PETG, 1.75 mm, ASIN `B0D1KC72YP`; record label, lot,
  spool changes, and drying cycle.
- Filament profile: `SUNLU PETG @BBL A1M 0.4 nozzle`.
- Process profile: `0.20mm Strength @BBL A1M`.
- 0.20 mm layer height, six walls, 25% grid infill, five top layers, three
  bottom layers, Support Off, 5 mm outer brim, 0.1 mm brim-object gap.
- Authored orientation, 100% XYZ scale, millimetres, no casual mirroring,
  auto-orienting, repairing, reaming, sanding, or heating of structural fits.

No aluminum or steel chassis, hidden beam, printed wall anchor, generic
drywall anchor, glue, snap-fit capacity, or friction-only load path belongs in
the base architecture. Metal is limited to the exact candidate wall screws and
one exact washer per screw.

## Documents and decision order

1. [DESIGN_REQUIREMENTS.md](DESIGN_REQUIREMENTS.md) — controlling product and
   safety requirements.
2. [PLAN.md](PLAN.md) — work packages, exact first-wall closure, and rejected
   shortcuts for the current reduced-piece development plan.
3. [GUIDELINES.md](GUIDELINES.md) — short memory checklist before every change.
4. [CUSTOMIZATION.md](CUSTOMIZATION.md) — inputs, equations, outputs, and
   refusal conditions for other wall lengths.
5. [MATERIALS_AND_HARDWARE.md](MATERIALS_AND_HARDWARE.md) — exact candidate BOM
   and controlled-lot hardware plan.
6. [PRINT_FIRST.md](PRINT_FIRST.md) — generator/bundle gates, fail-fast order,
   slicer contract, and fresh print permission.
7. [ASSEMBLY.md](ASSEMBLY.md) — provisional dry tabletop sequence and stop
   conditions.
8. [LOAD_QUALIFICATION.md](LOAD_QUALIFICATION.md) — physical evidence required
   before any installation or nonzero rating.

The current R11 v1 release record remains hard-forced to
`print_authorized: false`, `drilling_coordinates_released: false`,
`wall_installation_authorized: false`, `test_load_authorized: false`, and
`rated_load_kg: 0.0`, regardless of input completeness. The immediate next
step is generator integration and neutral-bundle validation—not sending a
print. A clean slice, attractive render, good hand fit, or successful R10
article cannot bypass this version boundary.
