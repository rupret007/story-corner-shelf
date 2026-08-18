# R11 print-first plan — integration and fail-fast gates

> **Nothing in this document grants permission to start a printer.** R11 v1
> hard-forces `print_authorized: false`; a clear printer and human readiness do
> not override that boundary. If a later reviewed revision becomes
> print-capable, every physical job—including an unchanged retry—must stop
> after slicing and Preview for fresh explicit human permission.
> **Earlier permission never carries forward.**

R11 is currently a reduced-part development plan. It has no print-authorized
production bundle. The target is a 28-article supplied kit, at most 27 articles
simultaneously installed, 28 safe unbatched starts, and 21 target batched
starts. The 21 target remains unverified until generator integration, saved
artifacts, manifests, packing, slicing, and physical gates prove it. Current
rating is **0 kg / 0 lb**.

## Gate 0 — do not print before generator integration

An R11 neutral bundle must exist and pass all of these checks before opening a
model in Bambu Studio:

1. deterministic regeneration from the pinned R11 source revision;
2. normalized input/layout report showing 1555.75 mm wall, six bays, seven
   supports, 254 mm pitch, 28 kit articles, 27 maximum installed articles,
   28 safe unbatched starts, 21 target batched starts, and 21 hardware pairs;
3. manifest enumerating exactly the eight first-outer-bay qualification
   articles: S0 fused two-socket support, S1 ordinary support, bay-0 terminal
   left and right half-decks, bay-0 keystone, two separately identified
   blanks, and one comb/hook;
4. individual neutral STL and model-only 3MF files at 100% scale with authored
   orientations and hashes;
5. saved-mesh validation for manifold/topology, bounds, volume, minimum walls,
   cross-lap overlap, true-net section, direct support bearing, integral
   lower-2/slide-32/settle-2 support capture, terminal pockets and solid
   roof/shoulder, positive stops, and independent reverse motion;
6. printer-envelope validation including 5 mm brim, 0.1 mm gap, and 2 mm bed
   reserve;
7. one-article saved-envelope evidence for both supports and both terminal
   half-decks, plus individual qualification treatment for the keystone and
   all three modules; the six-wedge and three-module full-wall batch targets
   remain future plate-validation work and are not implied by this bundle;
8. documentation tests and cross-links; and
9. release status that still explicitly records
   `print_authorized: false`, `drilling_coordinates_released: false`,
   `wall_installation_authorized: false`, `test_load_authorized: false`, and
   `rated_load_kg: 0.0`.

Those flags are immutable in R11 v1: complete inputs, a valid bundle, a clean
Preview, or passed study gates may not flip them. Neutral generation may not
create or embed G-code, BG-code, a sliced toolpath, printer credentials, or a
print command. Do not substitute an R10 file, rename an R10 mesh, invent an
R11 filename, or print a combined inspection catalog.

## Exact slicer contract for every future R11 article

Confirm each row independently before each slice:

| Field | Required value |
|---|---|
| Printer | Bambu Lab A1 mini |
| Physical nozzle | 0.4 mm standard-flow |
| Plate | Textured PEI; empty, clean, cool, correctly seated |
| Material | SUNLU standard black PETG, 1.75 mm, ASIN `B0D1KC72YP`, recorded and dried |
| Project mapping | `SUNLU PETG @BBL A1M 0.4 nozzle` mapped to the physically loaded external PETG |
| Process | `0.20mm Strength @BBL A1M` |
| Layers | 0.20 mm; 6 walls; 25% grid; 5 top / 3 bottom |
| Support | Off |
| Brim | Outer only, 5 mm; 0.1 mm brim-object gap |
| Scale / units | 100% X/Y/Z; millimetres |
| Orientation | Authored saved orientation; never auto-orient or rotate to hide a warning |
| Structural plate population | One support or one half-deck only |

For the future six-keystone and three-cable-module batch plates, confirm every
part remains in its saved orientation, brims do not merge unexpectedly,
first-layer toolpaths remain separated, and a single failed article cannot
damage another. If not, use one article per plate and 28 starts. Batching
changes starts only; it never changes the 28-kit inventory, 27-installed
limit, identities, BOM, or qualification obligations.

Inspect Preview layer by layer. Confirm no detached island, unintended bridge,
blocked channel/capture, omitted wall, self-intersection repair, scale change,
or support toolpath. A slicer warning requires a written, layer-level
disposition against the saved mesh; clicking through it is not a disposition.

Record model hash, plate population, source revision, orientation, scale,
profiles, all overrides, time, mass, layer count, warnings, screenshots,
printer state, and human authorization. Then stop at the final Send/Print
control for fresh permission.

## Conditional fail-fast physical sequence for a later print-capable revision

Use the exact eight manifest identities listed in Gate 0. Do not invent
role-to-file mappings or substitute a regular half-deck for bay 0. Gate 0
passing in R11 v1 does not authorize these prints.

### Gate A — first actual reciprocal cross-lap

1. Print the actual bay-0 terminal left half-deck, one per plate.
2. Inspect and measure it before spending the next plate.
3. Print the actual bay-0 terminal right mate, one per plate.
4. On a padded tabletop, use only the generated authored motion to engage all
   three 55 mm candidate reciprocal cross-laps and positive shoulders.
5. Cycle the dry halves ten times. No support, wedge, or load is used here.

Fail for force, shaving, PETG dust, whitening, crack, warp, proud/misaligned
skin, incomplete broad-face contact, growing looseness, or inability to reverse
the authored motion. A failure blocks later prints.

### Gate B — positive bay keystone

3. Print one actual matching bay keystone. For fail-fast work this may be a
   one-article plate; the future one-plate/six-keystone production target does
   not override qualification order.
4. With the half-decks unloaded on the table, seat and remove the keystone by
   its generated motion ten times.

The keystone must prevent only half-to-half X separation while remaining
hand-removable. It may not retain either half against the fixed support lugs,
wedge structural faces into preload, carry a gap, depend on snap/friction, or
receive support-capture or vertical-load credit.

### Gate C — first integral support capture

5. Print one actual ordinary support, one per plate.
6. Engage one conforming half-deck end by the generated sequence: lower with
   2 mm clearance over the fixed lug heads, slide 32 mm wallward, then
   gravity-settle 2 mm into the higher terminal pocket behind the solid
   8.4 mm roof/shoulder. Reverse by lift 2 mm, slide 32 mm outward, then lift
   clear. Confirm direct bearing, every positive stop, and reversible hand
   removal for ten unloaded cycles.

Fail for incomplete bearing, rocking, stop bypass, interference, damage, forced
motion, or dependence on the future wall screw/washer connection.

### Gate D — one complete actual bay

7. Print the actual S0 fused two-socket support, one per plate; this is the
   second support for the outer terminal bay.
8. Assemble the two passing half-decks and passing keystone off the supports,
   then perform the complete generated lower-2/slide-32/settle-2 capture
   sequence at both broad contacts. The keystone locks half-to-half X
   separation only; it does not lock support capture.
9. Perform ten complete unloaded assembly/disassembly cycles and all
   dimensional checks in [ASSEMBLY.md](ASSEMBLY.md).

This is the first actual R11 bay, not a scale mockup. Passing it authorizes no
additional print automatically, no wall hardware, no drilling, no test load,
and no stored load.

### Gate E — S0 cable furniture interface

10. Inspect the already-passing S0 fused support after Gate D; do not print a
    duplicate.
11. Print socket-0's actual flush blank and cycle it ten times in each socket
    using 8 mm lift/drop.
12. Only if both sockets pass, print socket-1's actual blank and the actual
    comb/hook as separate qualification articles. Confirm both normal states:
    two blanks, or one blank plus one comb/hook.

Cable modules carry representative cables only and receive zero shelf-load
credit. Socket/root damage blocks the furniture interface.

### Gate F — complete tabletop first-wall set

Only after Gates A-E and a future full-wall generator reconciliation pass may
a reviewed decision release articles beyond the eight-article outer-bay
bundle. Reuse only conforming, undamaged articles. Do not print the whole wall
in advance. That later manifest must add the remaining five supports, eight
regular half-decks, two terminal half-decks for bay 5, and five bay keystones.

Verify the future kit and installed-state targets rather than assuming them:

- seven supports total;
- 12 half-decks total;
- six keystones total;
- two blanks and one comb/hook supplied; and
- exactly 28 kit articles, with exactly two cable modules occupying the two
  sockets and therefore no more than 27 articles installed at once.

Assemble dry on a flat reference surface. Verify all seven centers, six
independent bays, endpoint fit, flatness, direct bearing, independent removal,
outlet/trim/cable envelopes, and that one absent keystone cannot release an
adjacent bay. No wall screws or load at this gate.

## First-article record

| Job / manifest ID | Photo ID | Source + mesh hash | Spool lot / drying | 100% scale | Authored orientation | Support Off | Slice time / mass / layers | Warning disposition | Cooled before removal | Dimensions / defects | Pass / fail |
|---|---|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |  |  |  |

## Ten-cycle dry-fit record

| Cycle | Three cross-laps fully bearing | Positive shoulder seated | Lower-2 / slide-32 / settle-2 capture complete | Keystone locks X-separation only | Lift-2 / slide-32 / lift-clear reverse clean | Dust / whitening / crack / looseness | Pass / fail | Photo ID |
|---:|---|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |  |  |
| 9 |  |  |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |  |  |

## Immediate stop conditions

Stop for missing/changed generator artifacts, wrong material mapping, changed
orientation, non-100% scale, Support enabled, unexpected repair, floating
island, blocked interface, incomplete brim, printer/HMS error, occupied or
dirty plate, cancellation, force, crack, whitening, shaving, growing dust,
progressive looseness, incomplete bearing, capture-stop bypass, damaged
keystone, or cable socket/root damage.

Cool the plate before removal. After a cancellation, failure, setting change,
power cycle, reseat, or retry, inspect the machine and plate, re-slice/review as
needed, and obtain a new explicit permission. The next decision after fit gates
is a reviewed qualification step under
[LOAD_QUALIFICATION.md](LOAD_QUALIFICATION.md), never automatic production.
