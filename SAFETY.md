# Safety boundary

Story Corner r5 is an untested DIY prototype—not a stamped structural design, code approval, certified installation, or rated storage product. The current 55 lb return-arm and 120 lb through-arm evenly distributed values are system-selection targets only. They are not published safe-working loads.

## Nonnegotiable hybrid load path

All generated printable components are PETG, but none are structural. Stored weight must pass through each continuous plywood deck and its continuous steel front angle, then through independently supported steel brackets, locks, standards, appropriate structural fasteners, and verified wood framing or purpose-installed blocking.

Never use a generated PETG component as:

- a wall bracket, standard, anchor, beam, ledger, deck, structural splice, or fastener;
- a connector that lets either plywood arm omit its nearest bracket;
- a substitute for framing, blocking, bracket locks, or mechanical deck attachment;
- a personnel support, ladder step, seat, or climbing surface;
- a rated restraint for hazardous, fragile, dense, or liquid-filled objects.

The Palatine arches, fluted piers, keystones, groin vault, and entablatures are architectural trim. Their Roman appearance does not give them masonry behavior or structural credit. PETG creeps under sustained stress and varies with temperature, formulation, moisture, print orientation, settings, layer adhesion, and stress concentration. A larger or more intricate printed part does not establish a safe long-term overhead rating. A structurally all-PETG shelf is outside this project.

## Corner stop conditions

- Do not overlap two full-depth boards. The 5 ft through deck owns the corner; the shortened return begins beyond it.
- Do not cut from nominal stations until the clear wall lengths and installed shelf-back offset have been measured **separately on both walls**, and wall bow/full-size template are known.
- Stop if the measured included angle differs from 90° by more than **0.25°**, or if the calculated remaining nominal 1.6 mm joint gap is below **0.6 mm**. The residual-derived theoretical limit is approximately 0.282°, but the configured gate is deliberately stricter.
- Do not treat a small printed gauge as a substitute for the full-size template.
- Dry-fit the two nearest perpendicular brackets, locks, fasteners, and both continuous angles. Numerical clearance does not capture actual body width or installation tolerance.
- Trim and deburr the return angle for controlled clearance. Do not force the angle ends together.
- Do not use a keystone, corner pilaster, groin vault, curb, quadrant, fascia, or optional alignment plate to pull misaligned decks coplanar.
- Keep the first return bracket. The plywood seam and optional alignment plates receive no vertical-support credit.
- Treat a completed L level as coupled: unload and move both arms together to one common top elevation.

## Palatine trim and falling-object controls

The full set includes hanging and overlay components. A loose decorative part can still injure someone even though it carries no shelf load.

- Verify that every arcade/fascia half is captured by both full-depth channel flanges without splitting, binding, lifting a tile, or bearing on ornament. Assemble the lateral train before closing it with the two outer endcaps and re-entrant corner cover.
- Use one tiny centered dot of qualified removable neutral-cure silicone inside each fascia channel only to prevent creep and rattle. Do not drill or notch the continuous steel angle for cosmetic retention.
- Retain each entablature overlay to its own fascia half with one tiny centered qualified removable silicone dot; never bridge its 0.6 mm seams.
- Retain each keystone with two pinhead-size qualified removable silicone dots on one half only; let it float over the opposite half's 0.6 mm seam.
- Use two tiny qualified removable silicone dots inside one upper leg of the re-entrant corner pilaster; its perpendicular leg floats and no adhesive crosses the seam.
- Mount the 42 mm groin-vault soffit through its two generated clearance slots with short nonstructural pan-head screws only into the underside of the through-owned corner square after a depth-stop and bracket-clearance check. Preserve at least 10 mm generated clearance to the nearest verified bracket plane and never bridge the plywood joint.
- Use only qualified removable attachment products. Hand pull-check every overlay, endcap, keystone, pilaster, and soffit before loading and after every move.
- Unload immediately for a loose, cracked, warped, whitening, or rattling ornament.

Attachment retains trim only. It does not make the fascia lip, curb, arches, or vault a rated cargo restraint.

## Rear-curb and top-tile controls

The rear curb sits on the printed tile, not directly on bare plywood:

```text
deck top datum             z = 0
top tile                   z = 0–2.0 mm
rear-curb base             z = 2.0–4.4 mm
rear-curb upright top      z = 17.0 mm
```

- Keep the long-wall straight curb and 172.6 mm through-zone piece on the through deck.
- Start the return curb on its own board beyond the 1.6 mm plywood gap. No printed curb or fastener may cross that joint.
- Use each generated curb clearance slot only after field-drilling the matching tile at final layout.
- Verify that every short pan-head screw has safe plywood engagement and cannot emerge below the deck or hit steel/bracket hardware.
- Do not clamp PETG rigidly; keep every 0.6 mm seam free.
- Use one small centered dot of qualified removable neutral-cure silicone per top tile on sealed plywood; remove with floss rather than prying.

## Before drilling

- Verify wall material and framing; the nominal plan assumes wood framing.
- Map both stud edges and centers on both walls, especially within 14 in of the corner, using more than one method.
- Confirm every proposed standard has usable structural backing and passes spacing/overhang limits. Field centers must be finite and independently spaced.
- Locate wiring, pipes, and protective plates around the outlets. Never infer cable paths from outlet position alone.
- Verify the common shelf-top elevation, ceiling clearance, door/trim clearance, the 39 in standard zone, and the complete 168.056 mm Palatine fascia envelope.
- Follow the current instructions for one compatible hardware system, including prescribed fasteners, holes, edge distances, torque, locks, and deck attachment.
- Stop and involve a qualified local professional if framing, wiring, structural fastener selection, any drilling needed for the steel angle's structural connection, wall condition, or injury consequences remain uncertain. Cosmetic fascia retention must not add holes or notches to the angle.

Hollow-wall anchors are excluded from the primary load path. A nominal support coordinate is not permission to drill there.

## Before loading

1. Install and inspect the bare plywood/steel L before adding PETG.
2. Verify standards are plumb, tops are coplanar, brackets do not interfere, every lock is engaged, and each deck is mechanically attached at every support.
3. Record unloaded front-edge position at the center and ends of both arms.
4. Apply known, nonfragile test weights gradually and evenly while keeping people clear.
5. Stop immediately for movement, noise, cracking, whitening, wall damage, ridge formation, bracket contact, permanent deflection, or connection slip.
6. Reinspect after one hour, 24 hours, one week, one month, after every move, and at least annually.

This controlled check can reveal obvious defects; it does not certify a load rating. Keep dense items near and between supports, put the heaviest items low, and avoid point, impact, front-edge, seismic, and accidental loads.

## Before printing

Confirm the exact printer, nozzle diameter and material, plate, slicer version, black PETG product, and filament condition. Print the corner gauge, fascia coupon, and Palatine detail coupon first. The repository intentionally contains model-only 3MFs and no embedded G-code. Arrange and slice for the confirmed machine; never reuse machine instructions from another setup.
