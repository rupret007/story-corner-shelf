# R9 qualification assembly and service guide

## Scope

This guide covers **visual dry assembly on a padded tabletop only**. It checks
whether printed interfaces can be identified, seated, released, and serviced
in the intended order. It is not a wall-installation guide and it does not
authorize stored load.

> **HARD STOP:** no drilling, screws, anchors, adhesive, wall mounting, hanging,
> leaning, proof load, or household use. The current capacity is 0 kg / 0 lb.
> Keep people, pets, and valuable objects away from an unsupported dry assembly.

## Planning topology—not an assembly diagram

The eventual per-level topology is:

```text
through run, far-left toward corner
through[0] bookend — through[1] compact — through[2] compact
                    — through[3] compact — through[4] hidden corner half

return run, corner toward far-right
return[0] hidden corner half — return[1] compact — return[2] bookend
```

That is eight candidate stations and six visible supports per level. The bundle
does not contain production quantities, shelf cassettes, full rear-ledger
segments, full front beams, or an authored one-bay assembly. Never line up the
qualification articles and call them a shelf.

The visible bookend body is nominally 4.75 in below the shelf underside and the
compact body is nominally 3.0 in. The complete thin strap remains 6.30 in tall.
These are qualification dimensions, not a capacity claim.

## Article identity

Use the exact filenames in [PRINT_FIRST.md](PRINT_FIRST.md). These distinctions
matter:

- `r9_shortened_outer_bookend_support` is the smooth, unhanded control.
- `r9_compact_support` is one representative compact article, not four parts.
- `r9_concealed_corner_half_control` is untrimmed and is not an assembly hand.
- `r9_through_hidden_corner_half` and `r9_return_hidden_corner_half` are the two
  pre-authored corner hands. Never mirror either one.
- `r9_two_socket_outer_bookend_rail_fit_coupon` is a standalone interface
  coupon; it does not attach to the smooth control.
- `r9_through_outer_bookend_additive_two_socket_candidate` and
  `r9_return_outer_bookend_additive_two_socket_candidate` are different handed,
  one-body first articles. Their receiver rails are fused/additive and are not
  removable.

## Before dry fitting

- [ ] R8 0.4 mm clearance gate passed and was recorded.
- [ ] The package is `r9_compact_bookend_petg_qualification_v2`.
- [ ] `manifest.json` and `validation.json` were verified in the bundle.
- [ ] Every individual 3MF filename and printed label remains traceable.
- [ ] All articles cooled to room temperature.
- [ ] No part has warp, crack, layer separation, missing material, whitening,
      or permanent set.
- [ ] Fit surfaces are clean; no part was sanded, filed, heated, drilled, or
      scaled.
- [ ] The work surface is flat, padded, and large enough for the 160 mm corner
      fixture and upright halves.

Painter's tape labels, a ruler/caliper, flashlight, phone/camera, and notebook
are appropriate. Do not use a mallet, clamp, pry bar, heat gun, drill, wall
screw, or adhesive. Support an upright article gently by hand if needed; the
corner study is not a freestanding structure.

## Exact dry-fit order

### 1. Inspect the three standalone support shapes

Inspect the compact support, smooth outer-bookend control, and untrimmed
corner-half control separately. Check their broad printed face, full thin wall
strap, shortened projecting body, D-window, roots, and front nose. Set each on
its declared datum face and record rocking or warp.

There is no authored support-to-ledger, support-to-front-beam, or cassette seat
in these articles. Do not attempt to mate them to the joint coupons.

### 2. Dry-fit the rear-ledger joint coupons

1. Keep `r9_rear_ledger_male_coupon` fixed on the padded table.
2. Align the open end of `r9_rear_ledger_female_coupon` with the male tongue.
3. Slide the female straight over the tongue through **12.4 mm** of service
   travel until the body shoulder planes meet. Do not twist.
4. The authored running clearance is 0.4 mm on each tongue depth/height face
   and 0.4 mm at the tongue tip. Only the outer body shoulders intentionally
   contact.
5. Remove the female by the exact straight reverse motion.

### 3. Dry-fit the staggered front-beam coupons

1. Keep `r9_front_beam_lower_lap_coupon` fixed.
2. Align `r9_front_beam_upper_lap_coupon` in its labelled upper position.
3. Slide the upper coupon straight over the lower lap through **16.0 mm** of
   service travel.
4. Do not clamp the pair closed. The target intentionally retains 0.4 mm at
   each axial shoulder and 0.8 mm total between opposed lap faces; no lap face
   is intended to contact.
5. Remove the upper coupon by the exact straight reverse motion.

Passing either coupon fit proves only that small interface—not a full ledger,
beam, span, or PETG creep result.

### 4. Assemble the five-part nominal corner study

Use only these five parts: 90-degree tabletop fixture, through handed half,
return handed half, shear-key handling coupon, and cosmetic reveal coupon.

1. Put the 160 mm L fixture flat on the padded table.
2. Keep the through label visible. Hold the through half upright over its
   fixture leg and lower it vertically **8.0 mm** to the fixture plane.
3. Orient the return half perpendicular to the through half without mirroring
   it. Slide it horizontally along the return leg through **16.4 mm** until the
   complementary 45-degree miter faces meet.
4. Lower the L-shaped shear-key coupon vertically **8.0 mm** until it rests on
   the two support tops.
5. Lower the cosmetic-cover coupon vertically **8.0 mm** until it rests on the
   key.
6. Photograph the fixture, miter, key, cover, front, and underside views.
7. Remove in exact reverse: cover up 8.0 mm, key up 8.0 mm, return half straight
   out 16.4 mm, then through half up 8.0 mm.

The fixture proves only handling and reveal at its authored nominal 90 degrees.
The closet angle is unmeasured, and the key/cover do not create a credited
corner load path. Stop if balancing becomes unsafe, a part must bend, or the
cover is needed to pull the halves into alignment.

### 5. Qualify the standalone cable interface

1. Place the standalone two-socket rail coupon securely on the padded table.
2. Hold the flush blank at the upper entry position, push it straight inward
   through the 6.0 mm approach, then lower it exactly **8.0 mm** into the lower
   socket.
3. Remove by lifting 8.0 mm, then moving straight outward. Repeat in the upper
   socket. Keep the unused socket empty.
4. Only after the blank passes both sockets, repeat one socket at a time with
   the comb/hook module.

This coupon proves only rail-to-module fit. It does not prove a rail attachment,
two simultaneously occupied sockets, a cable load, or a snag event.

### 6. Qualify both handed integrated bookends

1. Confirm the exact through and return labels. Do not mirror or swap them.
2. The additive receiver is already fused into each bookend. Never pry or try
   to remove it.
3. On the through bookend, test the blank in the lower and upper sockets one at
   a time using the straight-in, 8.0 mm drop, 8.0 mm lift, straight-out motion.
4. Repeat with the comb/hook, one socket at a time.
5. Repeat Steps 3–4 on the return bookend.
6. Inspect the additive receiver band, print foot, strap, D-window, roots, and
   socket edges after service.

The bookends remain zero-rated first articles. Door/trim, installed cable-loop,
wall, and real snag/service clearances are unqualified.

### 7. Stop: no one-bay or full-L assembly exists

The software deliberately blocks the compact-support/ledger/front-beam/
cassette one-bay pose. The present source has no compact-support member seats,
cassette/member interface and seam, full bay lengths/end conditions, or wall
hardware/framing datums. No one-bay mesh or placed assembly is emitted.

Do not create a substitute with loose coupons, R8 cassettes, tape, glue,
fasteners, scaling, or guessed alignment. Qualification v2 ends after the exact
dry fits above.

## Disassembly and storage

1. Remove every cable module by lift-then-out motion; the integrated receiver
   remains fused to its bookend.
2. Remove corner cover, key, return half, and through half in reverse order.
3. Slide the beam upper lap and ledger female coupon straight off their mates.
4. Inspect all socket, tongue, lap, miter, strap, D-window, key, cover, and root
   surfaces for abrasion, whitening, crack, permanent set, or lost engagement.
5. Store accepted PETG articles unloaded, indoors, flat, and away from direct
   sun or heat. Mark rejected/superseded articles clearly.

## Qualification record

| Check | Pass / fail | Observation or measured value | Photo ID |
|---|---|---|---|
| Smooth bookend control inspection |  |  |  |
| Compact support inspection |  |  |  |
| Untrimmed corner control inspection |  |  |  |
| Rear-ledger male/female dry fit |  |  |  |
| Front-beam lower/upper dry fit |  |  |  |
| Through corner half seat |  |  |  |
| Return corner miter seat |  |  |  |
| Shear-key handling coupon |  |  |  |
| Cosmetic reveal coupon |  |  |  |
| Complete corner reverse disassembly |  |  |  |
| Standalone rail + blank, both sockets |  |  |  |
| Standalone rail + comb/hook, both sockets |  |  |  |
| Through integrated bookend, both modules |  |  |  |
| Return integrated bookend, both modules |  |  |  |
| Complete post-service inspection |  |  |  |

## Wall installation remains blocked

This document intentionally contains no wall-bore coordinates, screw size,
pilot size, anchor pattern, installation torque, proof load, or rated load.
All of the following are required before a separate wall-installation document
can be authored:

- exact long and short clear lengths at both the 68 in and 84 in elevations;
- horizontal outlet centerline from the through-run far-left datum and a verified
  electrical no-drill/service envelope;
- exact corner angle, wall bow, trim and doorway clearances;
- verified stud/blocking locations and wall-substrate thickness;
- approved continuous blocking or an independently verified equivalent;
- exact metal structural screw, washer, pilot, embedment, edge-distance, and
  driver-access schedule;
- declared contents and target load;
- exact load-path CAD and wall-bore validation; and
- successful framed-wall, proof, creep, and destructive physical gates under
  an approved protocol.

Printed wall anchors and hollow-wall anchors are prohibited in the primary
load path. A successful tabletop assembly does not remove any of these stops.
