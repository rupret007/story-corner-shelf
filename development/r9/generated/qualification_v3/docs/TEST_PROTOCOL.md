# R9 qualification test protocol

## Status and limits

This protocol qualifies fit, reversible service, and visual tabletop assembly
in stages. It does **not** establish wall attachment, shelf strength, creep
life, a safe working load, or an installed release.

> **HARD STOP:** do not drill, wall-mount, hang, lean, proof-load, destructively
> test, or store anything on these articles. The current rating is 0 kg / 0 lb.
> Framed-wall, proof, creep, and destructive tests require separate approved
> fixtures and numeric protocols after the missing field and hardware inputs
> are resolved.

Only PETG articles printed from exact versioned bundles are eligible. PLA,
scaled meshes, mirrored substitutes, sanded-to-fit parts, combined catalog
layouts, and untraceable G-code are not eligible.

## Test record header

| Record item | Value |
|---|---|
| Test date / operator |  |
| Printer / nozzle | Bambu Lab A1 mini / 0.4 mm |
| Bambu Studio version |  |
| Plate | Textured PEI / other: |
| Filament brand, material, color | SUNLU PETG, black / confirmed: |
| Spool lot |  |
| Dryer, setpoint, actual time |  |
| Post-dry storage and RH if known |  |
| Flow calibration record |  |
| Exact bundle revision / manifest SHA |  |
| Photo folder or identifiers |  |

Attach the exact settings record from [PRINT_FIRST.md](PRINT_FIRST.md). A test
without a traceable part identity, material lot, orientation, and settings is
an observation, not a qualification result.

## Universal pre-test inspection

Test only after the part has cooled to room temperature.

| Inspection | Pass / fail | Observation / measurement | Photo ID |
|---|---|---|---|
| Correct exact filename and manifest identity |  |  |  |
| PETG spool and lot traceable |  |  |  |
| 100% scale and saved orientation confirmed |  |  |  |
| No warp/rocking on defined datum face |  |  |  |
| No crack, layer split, void, burn, or missing feature |  |  |  |
| No whitening or permanent set before fit |  |  |  |
| Fit, bearing, latch, and key faces undamaged |  |  |  |
| Critical dimensions meet exact bundle validation record |  |  |  |

Reject and quarantine an article on any unexplained failure. Do not sand,
drill, heat, glue, file, or force it into a passing condition.

## Gate 0 — inherited R8 clearance qualification

### Articles and order

Use the five exact individual files from
`development/r8/generated/qualification_v2/individual_model_only_3mf/`:

1. `MODEL_ONLY_r8_clearance_ladder_receiver.3mf`;
2. `MODEL_ONLY_r8_clearance_key_0p5.3mf`;
3. `MODEL_ONLY_r8_clearance_key_0p4.3mf`;
4. `MODEL_ONLY_r8_clearance_key_0p3.3mf`; and
5. `MODEL_ONLY_r8_clearance_key_0p2.3mf`.

### Method

1. Identify each key so the clearance cannot be confused after removal.
2. Place the receiver on a stable table; do not hold it where hand pressure can
   flex the opening.
3. Insert and remove 0.5 first using the intended straight service motion.
4. Repeat with 0.4. If it binds, needs a tool, visibly deforms the receiver, or
   causes whitening/cracking, stop before 0.3 and 0.2.
5. If 0.4 passes, try 0.3 and then 0.2 only as diagnostic fits. Never force a
   tighter key.
6. For each freely serviceable key, perform ten gentle full seat/release cycles
   and inspect after cycles 1, 5, and 10. Record any change in feel; do not add
   lubricant.

### Gate 0 result

The authored 0.4 interface passes only when it fully seats and releases by hand
through ten gentle cycles without tools, destructive force, crack, whitening,
permanent set, lost engagement, or increasing bind. A 0.5-only pass is not an
R9 interface pass. A 0.3 or 0.2 fit does not justify rescaling production parts.

| Key | Fully seats? | Releases by hand? | Cycles completed | Damage/change | Pass / fail | Photo ID |
|---|---|---|---:|---|---|---|
| 0.5 mm/face |  |  |  |  |  |  |
| 0.4 mm/face |  |  |  |  |  |  |
| 0.3 mm/face |  |  |  |  | diagnostic |  |
| 0.2 mm/face |  |  |  |  | diagnostic |  |

On a 0.4 failure, stop and correct the printing process. Create a new record
for every reprint; never overwrite the failed observation.

## Gate 1 — R9 straight-joint coupons

### Purpose

Check the authored assembly motion and seated geometry of the candidate rear
ledger and stiff front beam/fascia splices. This is a fit test only; it gives no
span, bending, shear, or creep credit.

### Method

1. Verify that Stage 0 passed with the same controlled process or document any
   new spool/process and requalify Stage 0.
2. Hold `r9_rear_ledger_male_coupon` fixed. Slide
   `r9_rear_ledger_female_coupon` straight over its tongue through 12.4 mm of
   service travel until the outer body shoulders meet.
3. Preserve 0.4 mm clearance on each tongue depth/height face and 0.4 mm at the
   tongue tip. The body shoulder plane is the only intended target contact.
4. Remove the female by the exact straight reverse motion. Repeat ten gentle
   cycles, inspecting after cycles 1, 5, and 10.
5. Hold `r9_front_beam_lower_lap_coupon` fixed. Slide
   `r9_front_beam_upper_lap_coupon` straight over it through 16.0 mm of service
   travel.
6. Preserve the intended 0.4 mm gap at each axial shoulder and 0.8 mm total gap
   between opposed lap faces. Do not clamp the lap faces together.
7. Remove by the exact straight reverse and complete ten gentle cycles.

### Acceptance

- full authored seat and reversible release by hand;
- no unintended rocking, step, trapped condition, or gap beyond the declared
  ledger/beam clearances;
- no crack, whitening, wear-through, permanent set, or loss of engagement; and
- no need for clamp force, impact, adhesive, heat, sanding, or scale change.

| Joint | Seat/release | Datum/seam result | Cycles | Damage/change | Pass / fail | Photo ID |
|---|---|---|---:|---|---|---|
| rear ledger |  |  |  |  |  |  |
| front beam/fascia |  |  |  |  |  |  |

## Gate 2 — standalone support first articles

### Purpose

Check print quality, saved orientation, flatness, and shortened shape for the
three standalone support articles. No member seat or one-bay fixture is emitted.

### Method

1. Inspect `r9_compact_support`, `r9_shortened_outer_bookend_support`, and
   `r9_concealed_corner_half_control` separately.
2. Verify each exact filename, saved broad-face print orientation, and raw
   dimensions against the bundle validation record.
3. Put the declared datum face on a flat padded table. Record rocking and any
   visible warp with a light behind the face.
4. Inspect the complete thin wall strap, D-window, shortened projecting body,
   front nose, arch/root transitions, and all layers.
5. Do not join these articles to a ledger coupon, beam coupon, cassette, wall,
   or each other. The untrimmed corner control is not a handed corner part.

### Acceptance

Each article remains one undamaged PETG body, matches its validation identity
and dimensions, lies on its datum without any detectable rocking or visible
warp, and has no crack, split, missing feature, or pre-test whitening. This
gate gives no support strength or station-count credit.

| Article | Identity/dimensions | Datum rock/warp | Surface/root result | Pass / fail | Photo ID |
|---|---|---|---|---|---|
| compact support |  |  |  |  |  |
| smooth bookend control |  |  |  |  |  |
| untrimmed corner-half control |  |  |  |  |  |

## Gate 3 — concealed two-wall corner fixture

### Purpose

Check the five-part nominal-90-degree handling/reveal study: tabletop fixture,
pre-authored through and return halves, under-shelf key coupon, and cosmetic
cover coupon. It gives no field-angle or structural corner credit.

### Method

1. Record the fixture revision and its authored 90-degree angle.
2. Put `r9_90_degree_tabletop_angle_fixture` flat on the padded table.
3. Lower `r9_through_hidden_corner_half` vertically 8.0 mm to its fixture leg.
4. Without mirroring it, slide `r9_return_hidden_corner_half` horizontally
   16.4 mm until the complementary 45-degree miter faces meet.
5. Lower `r9_under_shelf_shear_key_coupon` vertically 8.0 mm onto both support
   tops, then lower `r9_cosmetic_corner_cover_coupon` vertically 8.0 mm onto
   the key.
6. Remove in exact reverse: cover, key, return half, then through half.
7. Complete ten gentle cycles. Inspect after cycles 1, 5, and 10.

### Acceptance

The fixture remains flat; labels/hands remain correct; the 45-degree miters
meet without overlap or forced bend; key and cover lower/release in the exact
order; the cover is not needed to pull the halves together; and no damage or
progressive binding appears. This is only a nominal-90-degree tabletop result.

| Corner check | Cycle 1 | Cycle 5 | Cycle 10 | Pass / fail | Photo ID |
|---|---|---|---|---|---|
| through half independent seat |  |  |  |  |  |
| return half independent seat |  |  |  |  |  |
| key service |  |  |  |  |  |
| cover install/remove |  |  |  |  |  |
| seam/alignment |  |  |  |  |  |
| post-disassembly condition |  |  |  |  |  |

## Gate 4 — cable interface and integrated bookend service

### Purpose

First qualify the standalone two-socket rail/module interface. Only then check
no-load module service in both distinct integrated bookend hands. Cable hardware
receives no shelf or structural capacity credit.

### Method

1. On `r9_two_socket_outer_bookend_rail_fit_coupon`, hold the flush blank at the
   upper entry position, move it straight inward through the 6.0 mm approach,
   and drop it 8.0 mm to seat. Lift 8.0 mm and move straight outward to remove.
2. Complete ten gentle cycles in the lower socket and then ten in the upper,
   keeping the other socket empty.
3. Only after the blank passes, repeat in both standalone sockets with
   `r9_multi_cable_comb_hook_module`, one socket at a time.
4. Confirm the exact through/return labels on the two integrated bookends.
   Never mirror or swap them.
5. Repeat blank-then-comb service in both sockets of
   `r9_through_outer_bookend_additive_two_socket_candidate`, then in both
   sockets of `r9_return_outer_bookend_additive_two_socket_candidate`.
6. The integrated receiver is fused/additive. Never attempt to remove or pry it
   from the bookend.
7. Inspect socket edges, common keys, additive receiver band/foot, wall strap,
   D-window, and roots after cycles 1, 5, and 10.

### Acceptance

The standalone interface passes before either integrated first article; both
bookend hands are correctly identified; each module seats/releases by the exact
motion in each socket; and no key, socket, additive band/foot, strap, root, or
module shows damage or lost engagement. Adjacent occupied-socket service,
door/trim, installed cable-loop, snag, wall, and load clearances remain
unqualified.

| Article/socket | Blank cycles | Comb/hook cycles | Service result | Damage/change | Pass / fail | Photo ID |
|---|---:|---:|---|---|---|---|
| standalone lower socket |  |  |  |  |  |  |
| standalone upper socket |  |  |  |  |  |  |
| through bookend lower |  |  |  |  |  |  |
| through bookend upper |  |  |  |  |  |  |
| return bookend lower |  |  |  |  |  |  |
| return bookend upper |  |  |  |  |  |  |

## Gate 5 — qualification-v3 review and stop

Follow [ASSEMBLY.md](ASSEMBLY.md) and review the complete record. Gate 5 is not
a one-bay, full-L, or shelf assembly. The software explicitly blocks a
compact-support/ledger/front-beam/cassette one-bay pose because member seats,
cassette interface/seam, full bay lengths/end conditions, and wall hardware/
framing datums are unauthored. It emits no one-bay mesh or placed assembly.

The final v3 result may be called **qualification-article dry-fit pass** only
when Gates 0–4 pass and all reverse service/disassembly steps remain clean. It
must never be called “shelf pass,” “one-bay pass,” “structural pass,” or
“installation ready.”

| Final review | Pass / fail | Observation | Photo ID |
|---|---|---|---|
| exact package/manifest/part traceability |  |  |  |
| straight-joint reverse service |  |  |  |
| standalone support inspection |  |  |  |
| nominal corner reverse service |  |  |  |
| standalone cable interface |  |  |  |
| both integrated bookend hands |  |  |  |
| complete post-test damage inspection |  |  |  |
| one-bay/full-L work stopped |  |  |  |

## Stop conditions for every gate

Stop immediately and quarantine the affected article on:

- a 0.4 clearance-gate failure;
- crack, layer split, audible snap, whitening, permanent bend, or missing
  extrusion;
- increasing bind, loss of key/socket engagement, or progressive wear;
- incomplete bearing/contact, rocking, twist, trapped service part, or a need
  for tools/force;
- an incorrect hand, scale, orientation, filament, file identity, or slicer
  repair;
- a required dimension outside the exact bundle's stated tolerance;
- an outlet, door, trim, cable, driver, or storage-envelope conflict; or
- any proposed action involving a wall, household load, or unapproved test
  weight.

Write the failure as observed. Do not convert a failed gate into a pass by
post-processing or by changing the acceptance rule after the test.

## Future structural gates—not authorized here

The following tests remain mandatory before any installed release, but this
document intentionally provides no fixture loads, proof factors, duration,
fastener schedule, or pass limits:

1. compact support versus the R8 structural control;
2. the currently blocked one-bay ledger/front-beam/support/cassette fixture;
3. exact two-wall concealed-corner structural fixture;
4. framed-wall hardware and driver-access fixture;
5. declared-load proof test;
6. PETG creep test at the declared load and service temperature;
7. cyclic/service testing at declared conditions; and
8. controlled destructive testing with a defined safe exclusion area.

Those protocols require exact field dimensions, verified framing/blocking,
approved metal structural screws/washers, target contents load, exact CAD bore
geometry, instrumentation, duration, environmental conditions, and acceptance
criteria. Printed anchors and hollow-wall anchors are prohibited in the primary
load path. Until all are authored, executed, and reviewed, full shelf printing,
wall installation, and stored load remain **NO-GO**.

## Gate summary

| Gate | Result | Tester/date | Record/photo location | Authorized next action |
|---|---|---|---|---|
| 0 — R8 0.4 clearance |  |  |  | R9 coupons only if pass |
| 1 — straight joints |  |  |  | support articles only if pass |
| 2 — support first articles |  |  |  | nominal corner only if pass |
| 3 — nominal corner |  |  |  | cable interfaces only if pass |
| 4 — cable/bookend service |  |  |  | v3 review only if pass |
| 5 — qualification-v3 review |  |  |  | stop; no one-bay or wall work |
