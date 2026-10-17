# Assembly — Triadic Palatine Order R12 final durable

> **Installation holds:** The measured 61.5 in long wall requires verified structural blocking at 6.0 and 60.5 in from the inside corner in addition to measured studs at 17.0, 32.5, and 48.5 in. The 36 in return remains nominal; do not cut, mount, or bulk-print return production parts until its dimensions and framing are entered and regenerated.

Before staging production parts, pass the R12 adhesion-corner coupon, fascia fit coupon, Palatine detail coupon, and corner gauge in the order listed in `generated/final_release_r12/PRINT_ORDER.md`. A rough, dragged, lifted, or delaminated plate-facing corner is a failed part, not a cosmetic acceptance.

This document owns the build sequence and the attachment rules. Where another
document mentions assembly, this file is the authority; if a statement here
ever disagrees with a summary elsewhere, fix the summary. The structural rules
in [SAFETY.md](SAFETY.md) and the geometry in
[ENGINEERING_DESIGN.md](ENGINEERING_DESIGN.md) still govern what may be built
at all.

Nothing in this sequence gives any PETG part structural credit. The load path
is plywood + continuous steel angle + brackets + locks + standards + structural
fasteners + verified framing, in that order, always.

## Entry gate — all boxes before Stage 1

- [ ] [MEASUREMENT_WORKSHEET.md](MEASUREMENT_WORKSHEET.md) completed through
      section H, values entered in [config.json](config.json), artifacts
      rebuilt, and every `*_source` field in
      [generated/validation.json](generated/validation.json) confirmed to read
      `field_verified_*` rather than a nominal fallback.
- [ ] R12 adhesion-corner coupon, corner gauge, fascia fit coupon (with 2.4 mm tile sample in place), and
      Palatine detail coupon all passed per
      [PRINT_ME_FIRST.md](PRINT_ME_FIRST.md) steps 1–8.
- [ ] Neutral-cure removable silicone qualified on printed PETG, sealed
      plywood, and the actual coated steel; curb/vault screws qualified in
      representative plywood with underside clearance.
- [ ] Full-size corner template made and checked against the real corner.
- [ ] Wall cleared, wiring/pipes mapped, framing verified at every support
      line per [SAFETY.md](SAFETY.md) "Before drilling".

## Stage 1 — Structural install (no PETG yet)

The ordering below is load-bearing information: two of the config inputs can
only be measured after the standards are on the wall, so cutting plywood
before step 6 risks cutting to a stale offset.

1. Establish one laser (or equivalent) common datum across both walls at the
   chosen shelf-top elevation. Verify the 39 in standard zone: the reported
   outlet-top-to-ceiling distance is 43.5 in, leaving only 4.5 in total
   placement margin for a 39 in standard.
2. Transfer the verified support centers from the worksheet framing map to
   both walls. Re-scan every fastener path for wiring and plates.
3. Mount the standards on verified framing or purpose-installed blocking with
   the manufacturer-prescribed fasteners. Check each standard plumb before
   final torque.
4. Hang the brackets at the common elevation and engage a bracket lock at
   every station.
5. Dry-fit the two nearest perpendicular corner brackets together with locks
   and both steel angles; confirm no interference (SAFETY.md corner stop
   conditions).
6. **Measure the installed wall-to-plywood-back offset separately on each
   wall**, and the actual bracket wall-to-tip reach, with the real hardware
   seated. Enter them in config.json (worksheet section H shows the exact
   keys), rebuild, and re-check the regenerated
   [cut plan](generated/cut_plan.csv) and
   [corner plan](generated/corner_layout.svg). Only now are the cut lengths
   real.
7. Cut the 5 ft through deck, then the 3 ft return deck, from the same
   plywood panel where practical, long arm parallel to the face grain.
8. Trim and deburr the return steel angle for controlled clearance; never
   force the angle ends together. Fasten each continuous angle under its deck
   front edge with reviewed predrilling and edge distances.
9. Seal the plywood — top face and cut edges — with a suitable clear sealer
   and let it cure. Every later silicone dot lands on sealed wood, and the
   silicone qualification coupon must have used the same sealer.
10. Set the through deck (it owns the 8 × 8 in corner square), then the
    return deck beyond the through front plane, and mechanically attach each
    deck at every bracket per the hardware instructions.
11. Verify: standards plumb, tops coplanar with no ridge at the corner, every
    lock engaged, every deck attached, 1.6 mm wood gap present, nothing
    touching that shouldn't. Then run the bare-structure load check
    (SAFETY.md "Before loading", steps 1–5) **before any PETG goes on**.

## Stage 2 — Stage and label the printed parts

Several part families are handed or arm-specific and easy to confuse. Sort
everything before opening any silicone.

| Confusable set | How to tell apart |
|---|---|
| 9 left vs 9 right arcade/fascia halves | Mirror-image handing: hold the half channel-up, arch outward — the half-pier lands on opposite ends. Label L/R on painter's tape inside the channel at print time. |
| Short-arm vs long-arm halves | Width: return (3 ft) halves are 113.99 mm; through (5 ft) halves are 107.63 mm. Measure — the 6.4 mm difference is invisible at a glance. |
| Entablature overlays | Same widths as their host halves (113.99 vs 107.63 mm); pair each overlay with a half of the same width. |
| Rear-curb ends | Through ends are 126.48 mm; return ends are 115.58 mm. |
| Top-tile ends vs centers | Ends are 116.08 mm; centers are 151.8 mm. |
| Corner quadrants | Four identical 101.3 mm squares — no handing. |

Reconcile physical counts against the production table in
[PRINT_ME_FIRST.md](PRINT_ME_FIRST.md) (98 installed pieces) before starting.
Quarantine any part with cracks, whitening, warp, or failed dimensions.

## Stage 3 — Top tiles

1. Place the four corner quadrants on the through-owned corner square first —
   they set the corner datum for both straight runs, which start 0.6 mm
   beyond the through corner front line.
2. Lay each straight run dry from the corner outward: centers on the 152.4 mm
   pitch, parametric ends last. Confirm every 0.6 mm seam and the return
   inner tile's 1.0 mm overhang of the hidden plywood gap.
3. Fix each tile with **one small centered dot** of qualified removable
   neutral-cure silicone on the sealed plywood. Keep every edge and seam
   free. Removal later is by floss, never prying.

## Stage 4 — Rear curbs

1. Seat the 30 mm fitted L corner replacement first, then the long-wall
   straight curb from station 1.892 in, then the separate 172.6 mm
   corner-side piece (through deck only, stopping at the through front
   plane), then the return curb starting on its own board at 8.750 in. No
   curb or fastener crosses the 1.6 mm wood joint.
2. At final layout, mark each curb clearance slot (8 × 4.4 mm; one per
   straight piece, one per replacement arm) onto the tile below. Remove the
   curb, drill the tile with a clearance hole sized to the qualified screw's
   shank, and set a drill depth stop so the bit cannot mark the plywood more
   than needed.
3. Drive each **short pan-head screw** through slot and tile into plywood
   only, after verifying it cannot emerge below the deck or reach steel.
   Snug, never clamped: the slot must still allow movement, and no seam may
   be bridged.

## Stage 5 — Fascia train

Direction matters: **start at the inside corner and train outward** on each
arm. The corner sets the bay layout's datum, and any accumulated seam error is
pushed to the outer ends, where the endcap's reserved 2.0 mm and the 1/8 in
exposed-end clearance absorb it.

1. Bench-fit each entablature overlay to its own half first (Stage 6 rule 1)
   so each half arrives at the wall complete.
2. Slip the first half over the shelf stack at the inside corner end of the
   through arm: both full-depth flanges must capture the plywood + angle +
   tile stack without splitting, binding, or lifting the tile. The nominal
   channel opening is 46.656 mm and must be proven by the R12 coupon.
3. Before seating each half fully home, place **one tiny centered dot** of
   qualified silicone inside its channel, then seat it and slide it laterally
   against its neighbor to the 0.6 mm seam.
4. Repeat outward: alternate left/right halves per the elevation drawing
   ([generated/palatine_elevation.svg](generated/palatine_elevation.svg)),
   three bays on the return, six on the through arm.
5. Never drill, notch, or otherwise modify the continuous steel angle for
   fascia retention — capture and silicone dots are the only retention.
6. Close each arm with its compound endcap: **two tiny dots** inside the
   final channel, then a hand pull-check. Fit the re-entrant corner pilaster
   slip-cover last at the inside corner: **two tiny dots inside one upper leg
   only**; the perpendicular leg floats with no adhesive across the seam.

## Stage 6 — Ornament

1. **Entablature overlays** (done on the bench in Stage 5): one tiny centered
   dot on the overlay's own fascia half; no overlay bridges a 0.6 mm seam.
2. **Keystones** go on after both adjacent halves are seated, since each
   bridges a bay-center seam visually: **two pinhead-size dots on one half
   only**; the other side floats.
3. **Groin-vault soffit** goes on last: through-owned corner square underside
   only, mounted through its two generated clearance slots with short
   nonstructural pan-head screws after a depth-stop check, preserving at
   least 10 mm to the nearest verified bracket plane, never bridging the
   plywood joint.

## Stage 7 — Close-out

Count the installed set — it must total **98**:

| Family | Count |
|---|---:|
| Center top tiles | 20 |
| Corner quadrants | 4 |
| Parametric top ends | 8 |
| Arcade/fascia halves | 18 |
| Entablature overlays | 18 |
| Rear curbs (11 centers + 4 ends + corner-side + L replacement) | 17 |
| Keystones | 9 |
| Endcaps | 2 |
| Corner pilaster | 1 |
| Groin-vault soffit | 1 |

Hand pull-check every overlay, keystone, endcap, pilaster leg, and the
soffit. Confirm every 0.6 mm seam is free, nothing bears on ornament, and no
tile has lifted. The gauge and two coupons are not installed.

## Stage 8 — Load acceptance and record

Follow SAFETY.md "Before loading". Before placing the first test weight,
write down your own stop limits in the record below — a deflection limit and
a permanent-set limit chosen before the test, not after. This record
documents a controlled check; it does not create a load rating.

| Record field | Value |
|---|---|
| Date / by | |
| Front-edge reference points (locations) | |
| Unloaded readings | |
| Test weights and placement | |
| Chosen deflection stop limit | |
| Chosen permanent-set stop limit | |
| Readings under load | |
| Readings after unload (permanent set) | |
| Temperature / humidity | |

Re-inspect on the schedule in [SAFETY.md](SAFETY.md) "Before loading"
(1 hour through annually). Unload immediately for movement, noise, cracking,
whitening, wall damage, ridge formation, bracket contact, permanent
deflection, connection slip, or any loose ornament.

## Stage 9 — Disassembly and service

The finish system is designed to come off without damage. Removal order is
the reverse of installation, and no step may require removing a part under
load — unload the shelf first, always.

1. Groin-vault soffit (unscrew).
2. Endcaps and the corner pilaster slip-cover (release their silicone dots).
3. Keystones (release the two dots on their fixed half).
4. Fascia halves, trained back toward the corner one at a time, each with its
   overlay still attached.
5. Rear curbs (unscrew; the tiles keep their drilled holes for reinstall).
6. Top tiles (floss under the single dot; never pry).

Quarantine and replace any part that cracked, whitened, or warped in
service. Moving the shelf itself: unload completely and move both arms as one
coupled assembly to a single new common elevation, then repeat Stage 8.
