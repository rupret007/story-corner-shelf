# R11 provisional dry tabletop assembly

> **Engineering-study sequence only — rated load 0 kg / 0 lb.** Do not use this
> document to drill a wall, install hardware, place load, or start a printer.
> R11 v1 hard-forces all four authorizations to false regardless of input or
> fit evidence.
> R11 generator integration must first publish the exact handed identities,
> motion arrows, positive stops, and saved meshes. If generated geometry differs
> from this invariant sequence, stop and revise the documents and/or geometry.

Use the [qualification-only exploded bay and first-wall topology diagram](visuals/r11_first_outer_bay_exploded_and_wall_topology.svg)
as an orientation aid for this provisional tabletop sequence. The generated
assembly map and saved geometry remain controlling; the diagram releases no
print, drilling coordinate, installation, test load, or stored load.

## What this sequence is meant to prove

The first actual bay is intended to contain five printed articles:

- one authored left three-rib half-deck;
- one authored right three-rib half-deck;
- one positive removable bay keystone; and
- two adjacent supports.

The fit test asks whether the two large shelf members can cross-lap like
Lincoln logs, whether the joined bay can complete the generated
lower/slide/gravity-settle motion into broad direct support bearing, whether
the keystone blocks half-to-half X separation without carrying gravity or
support-capture duty, and whether every motion reverses by hand. It proves no wall connection,
long-term PETG behavior, complete-wall fit, or allowable load.

The complete first-wall **kit target** is 28 articles: seven supports, 12
half-decks, six keystones, two flush cable blanks, and one comb/hook. Only two
of the three supplied cable modules fit S0's two sockets, so the maximum
simultaneously installed count is 27. R10's separate splice logs and
support/log retainers are not part of this assembly.

## Do not assemble until the bundle supplies these facts

The generated manifest and assembly map must identify:

1. left/right hand and front/rear orientation for every half-deck;
2. terminal versus regular identity and owning bay—both halves of bay 0 and
   both halves of bay 5 are terminal, for four terminal halves at 162.175 mm;
   both halves of bays 1-4 are regular, for eight regular halves at
   154.325 mm;
3. which three rib faces overlap and the measured overlap/bearing lengths;
4. the exact off-support cross-lap motion;
5. the exact lower/slide/gravity-settle direction and travel at each support
   capture;
6. the keystone entry, seat, positive stop, grip, and reverse motion;
7. the support center and broad-bearing contact for each bay; and
8. disassembly clearance without moving an adjacent bay.

Do not guess a motion from a render or mirror one side in the slicer. Until
these generated facts and corresponding physical gates exist, this document is
a design plan rather than an executable installation guide.

## Prepare the unloaded work area

Use a clean, padded, verified-flat table, calipers, square, straightedge,
feeler gauges, soft brush, labels, camera, generated manifest, assembly map,
and completed print records from [PRINT_FIRST.md](PRINT_FIRST.md).

No adhesive, lubricant, heat gun, hammer, mallet, pry bar, clamp, power tool,
wall screw, washer, or test mass is permitted.

Confirm before touching two parts:

- every article ID, hand, source/mesh hash, PETG lot, drying record, scale,
  orientation, slice record, and photo is traceable;
- each article cooled before removal and passed dimensional/visual inspection;
- only the sacrificial outer brim was removed;
- no structural face, lap, rib, shoulder, capture, stop, bore, or washer land
  was sanded, filed, reamed, drilled, heated, bent, or forced; and
- there is no warp, crack, layer separation, under-extrusion, contamination,
  whitening, loose fragment, missing feature, or unreviewed slicer repair.

Quarantine and record any failed part. Do not rescue the fit by modifying it.

## Candidate one-bay Lincoln-log sequence

The invariant order is precise even though the generated left/right movement
directions remain a Gate-0 deliverable:

1. **Orient off the supports.** Place the authored left and right half-decks on
   the padded table with rear/front and top/bottom matching the generated map.
2. **Engage all three reciprocal laps.** Use the one linear/vertical motion
   shown by the map to interleave rear, center, and front integrated ribs. Move
   by hand until all broad lap faces and positive body shoulders seat. Preserve
   the authored midpoint seam; do not clamp it to zero.
3. **Check the joined deck.** Verify continuous top alignment, full three-rib
   engagement, no rock/twist, and no daylight at required bearing faces. Do not
   install the keystone to pull a structural gap closed.
4. **Place two supports.** Set the two manifest-matched supports upright on the
   table at the generated centers, capitals level and wall faces aligned. This
   is a tabletop arrangement; leave all three printed bores empty.
5. **Lower over the fixed lugs.** Hold the joined bay 2.0 mm above its final
   seat so its pockets clear the fixed lug heads, then lower onto the generated
   approach lands. Do not force past a lug.
6. **Slide and gravity-settle into positive capture.** Slide the joined bay
   32.0 mm wallward, then let it settle 2.0 mm into the higher terminal pockets
   behind the solid 8.4 mm roof/shoulder. Each end must retain at least the
   generated broad direct bearing target (initial candidate 15.70 mm). The
   motion must be hand-operated, reversible, and free of snap or friction
   dependence.
7. **Seat the bay keystone.** Insert the correct authored keystone through its
   labeled entry and move it to its positive seat. It blocks half-to-half X
   separation only; it may not prevent reversal from the support lugs, preload
   the laps, carry a support gap, or be credited with support-capture,
   gravity, or bending capacity.
8. **Inspect.** Confirm three full cross-laps, both broad support contacts,
   both capture stops, the physical seam, square/flat geometry, a serviceable
   keystone grip, and no contact with an adjacent-bay envelope.

If the physical geometry cannot follow those eight actions without force or an
extra loose piece, the integral capture concept has failed. Revise the R11
architecture and counts; do not add hidden hardware ad hoc.

## Exact reverse principle

Disassembly must reverse one bay without disturbing another:

1. remove the bay keystone by its authored hand motion;
2. lift the joined bay 2.0 mm clear of both terminal-pocket shoulders;
3. slide 32.0 mm outward until both fixed lug heads clear their paths;
4. lift vertically clear of both support capitals;
5. move the supports aside only in the isolated one-bay tabletop test;
6. reverse the authored three-rib cross-lap motion to separate the halves; and
7. inspect every lap, shoulder, skin, rib, capture, stop, land, and keystone
   before the next cycle.

Never twist, rock, pry, or use the keystone as a disassembly lever.

## Ten-cycle unloaded acceptance

Perform ten complete assembly/disassembly cycles and record them in
[PRINT_FIRST.md](PRINT_FIRST.md). Stop for force, shaving, accumulating PETG
dust, whitening, crack, progressive looseness, blocked movement, proud or
uncommanded keystone, incomplete lap shoulder, capture-stop bypass, partial
support bearing, rocking, twist, permanent set, or damage that grows with
cycling.

No books, tools, test weights, body weight, or cable-hook mass are permitted.

## Complete first-wall tabletop target

Only after the one-bay and cable fit gates pass, arrange the seven supports on
a flat reference surface at these ideal first-wall centers:

```text
S0    15.875 mm
S1   269.875 mm
S2   523.875 mm
S3   777.875 mm
S4  1031.875 mm
S5  1285.875 mm
S6  1539.875 mm
```

Assemble one bay at a time by the same invariant sequence. Keep all six cells
independent. The finished tabletop study must show:

- six 254 mm planning pitches and support faces at the 0 / 1555.75 mm ideal
  wall endpoints before field-clearance adjustment;
- 12 manifest-correct half-decks and six independently removable keystones;
- direct broad bearing at every support contact;
- authored 0.35 mm candidate seams, without forced zero-gap closure;
- flat rear/front edges and top surface within reviewer-defined tolerances;
- removal/reinstallation of each bay without releasing its neighbor; and
- S0 as the only first-wall cable receiver.

The tabletop uses exactly two installed cable modules at once. Store the third
supplied module off the shelf; the normal states are two blanks, or one blank
plus one comb/hook.

This remains an unloaded tabletop check. Do not put the 21 candidate screws
through the supports.

## S0 cable-module service sequence

Test the cable interface separately from structural fit:

1. Inspect the fused S0 receiver/root; any separation or crack fails S0.
2. At a socket's upper entry, move one blank straight inward through the
   authored approach, then lower exactly 8 mm to its gravity seat.
3. Lift 8 mm and move straight outward. Repeat ten times in each socket, one
   occupied socket at a time.
4. Repeat with the comb/hook, then verify both normal furniture states: two
   blanks, or one blank plus one comb/hook.
5. Use representative loose cables only for later snag/clearance observation.

Do not bend or snap a module into place. Intermediate supports and the future
inside corner receive no module. Cable parts receive zero structural credit.

## Boundary after a fit pass

Preserve all parts, measurements, source/mesh/slice records, photos, and cycle
logs. A fit pass advances only to a reviewed fixture decision under
[LOAD_QUALIFICATION.md](LOAD_QUALIFICATION.md). It does not authorize printing
the remainder automatically, hardware procurement, wall drilling,
installation, test load, stored load, or a rating.
