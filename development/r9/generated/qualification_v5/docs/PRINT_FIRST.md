# R9 print-first guide

## Read this before opening Bambu Studio

R9 is a **qualification-only** shelf design. The first prints are small fit
articles, followed by one set of R9 joint/support/corner articles and the
permitted tabletop dry fits. They are not a complete shelf kit.

> **HARD STOP:** do not print the full two-level shelf, drill a wall, select
> wall screws from this document, install a part, or place stored load on any
> R9 article. Wall construction, framing/blocking, fastener geometry, exact
> room dimensions, target contents load, and physical structural tests are not
> complete. The current load rating is 0 kg / 0 lb.

Current planning references—not final fabrication dimensions—are:

- lower and upper shelf tops: nominally **68 in** and **84 in** above the floor;
- long/through clear wall: **61.25 in** at both shelf elevations;
- short/return clear wall: **36.75 in** at both shelf elevations, retained as
  the conservative working value read from the supplied photos;
- top of outlet faceplate: approximately **53.5 in** above the floor; and
- horizontal outlet position from the through-run far-left datum: **not measured**.

Complete [MEASUREMENT_WORKSHEET.md](MEASUREMENT_WORKSHEET.md) before exact
stationing or any installation design.

## Filament and machine baseline

Use only the received **black SUNLU PETG** spool corresponding to Amazon ASIN
`B0D1KC72YP`, selected listing variant `4 kg / 2 Black + 2 Black` (four black
1 kg spools). Confirm that the physical spool label still says **PETG** and
record its lot. Listing variants can change. PLA is not authorized for an R9
printed part, qualification coupon, substitute, or load-path component.

SUNLU's [standard PETG product page](https://store.sunlu.com/products/over-6kg-bundle-sale-petg-3d-printer-filament-1-75mm-1kg-roll)
lists 50 C drying and storage below 20% RH. For this project, use **50 C for
6–8 hours** only when both the received spool label and the dryer instructions
permit it. Never exceed the lower temperature limit stated by either source.
Stop and resolve conflicting instructions instead of guessing. After drying,
keep the spool sealed or in a dry box until use.

Record the drying cycle and then manually verify every value below. A neutral
3MF contains geometry; it does not guarantee these printer settings.

| Setting | Qualification baseline |
|---|---|
| Printer | Bambu Lab A1 mini, 0.4 mm nozzle |
| Plate | Textured PEI; follow the plate maker's PETG release/interface guidance |
| Filament preset | `SUNLU PETG @BBL A1M 0.4 nozzle` |
| Process starting point | `0.20mm Strength @BBL A1M` |
| Scale | 100%; never auto-scale |
| Layer height | 0.20 mm |
| Nozzle | 250 C first layer; 245 C remaining layers |
| Bed | 60 C |
| Flow ratio | 0.94 |
| Maximum volumetric speed | 9 mm^3/s |
| Fan | 10–30% normal; 90% overhang |
| Walls | 6 loops |
| Top / bottom shells | 5 top / 3 bottom layers |
| Infill | 25% grid |
| Brim | Outer brim only, 5.0 mm wide, 0.1 mm object gap; keep at least 2.0 mm between brims |
| Plate reserve | Preserve at least 2.0 mm from every bed edge in addition to the brim |

Never reuse a PLA project or preset. Clean the plate, inspect the nozzle, and
confirm the selected plate and nozzle in the Device/Prepare views before every
qualification job.

The neutral 3MF embeds no filament or process profile. If the exact SUNLU
preset above is not listed, duplicate `Generic PETG`, enter every value in the
table manually, save it as `SUNLU PETG @BBL A1M 0.4 nozzle`, and verify it again
before slicing. Let the plate and PETG part cool fully before removal.

## Exact staged print order

Do not skip ahead after a failure. Record each stage in the table at the end of
this document and use the acceptance rules in [TEST_PROTOCOL.md](TEST_PROTOCOL.md).

### Stage 0 — corrected 0.4 mm clearance gate (print this first)

Use only the individual neutral 3MF files in the current R9 v5 bundle:

```text
development/r9/generated/qualification_v5/stage0_individual_model_only_3mf/
```

Print and test in this order:

1. `MODEL_ONLY_r8_clearance_ladder_receiver.3mf`
2. `MODEL_ONLY_r9_gate0_clearance_key_0p4_handle_down.3mf`

The receiver is geometry-identical to the frozen R8 v2 receiver. A cooled,
inspected R8 v2 receiver may therefore be reused instead of reprinted. The key
has the exact 0.4 mm **per-face** geometry, but v5 applies a proper 180-degree-X
saved pose so its 20 x 16 mm handle begins on the plate. Preserve the imported
pose. Support must remain Off, and Bambu Preview must show no
floating-cantilever warning.

Do **not** print the legacy R8 v2 0.5, 0.4, 0.3, or 0.2 key files in their
identity saved poses. Their common pose contains a large handle cantilever.
V5 deliberately uses the design-target 0.4 key as the fail-fast gate; tighter
and looser diagnostics remain deferred until corrected poses are published.

Let the key cool completely. Inspect both unsupported keyed-head wings before
fit: no loose strand, curl, torn perimeter, layer separation, or visible droop.
Then the 0.4 key must seat and release by hand through ten gentle cycles without
tools, cracking, whitening, permanent set, increasing bind, or destructive
force.

If 0.4 does not qualify, **stop**. Do not sand the key, enlarge the receiver,
change scale, or compensate in CAD. Check moisture, flow calibration, actual
temperatures, plate choice, and slicing settings; record the correction and
reprint a new identified set.

### Stage 1 — verify the frozen R9 bundle

Proceed only after Stage 0 passes at 0.4 mm. The exact bundle is:

```text
development/r9/generated/qualification_v5/
```

Its package identity is `r9_compact_bookend_petg_qualification_v5`. Before
printing, read its `README.md`, open `validation.json`, and verify the current
`manifest.json` in that same directory. Record the manifest file's SHA-256 in
the print log; do not copy a digest from an old message or edit the manifest.
Stop if the package identity, validation result, artifact list, or hashes do
not agree with the files present.

Use only the files in `individual_model_only_3mf/`. This file is a catalog only:

Every individual part follows the exact path rule
`individual_model_only_3mf/MODEL_ONLY_<mesh_id>.3mf`.

```text
model_only_3mf/MODEL_ONLY_R9_QUALIFICATION_CATALOG.3mf
```

Never treat that combined catalog as an arranged A1 mini plate.

### Exact 17-part inventory

The table order is the frozen manifest/object order, not the recommended print
sequence. Every entry is a separate neutral 3MF at 100% scale.

| # | Exact individual filename | Purpose | Saved print orientation |
|---:|---|---|---|
| 1 | `MODEL_ONLY_r9_shortened_outer_bookend_support.3mf` | smooth outer-bookend control | broad minimum run-side face on plate |
| 2 | `MODEL_ONLY_r9_compact_support.3mf` | shortened compact-support article | broad minimum run-side face on plate |
| 3 | `MODEL_ONLY_r9_concealed_corner_half_control.3mf` | untrimmed corner-half control; not an installed hand | broad minimum run-side face on plate |
| 4 | `MODEL_ONLY_r9_through_hidden_corner_half.3mf` | pre-authored through-run corner hand | broad minimum run-side face on plate |
| 5 | `MODEL_ONLY_r9_return_hidden_corner_half.3mf` | pre-authored return-run corner hand | opposite/broad maximum run-side face on plate |
| 6 | `MODEL_ONLY_r9_under_shelf_shear_key_coupon.3mf` | handling/registration coupon only | authored flat face on plate |
| 7 | `MODEL_ONLY_r9_cosmetic_corner_cover_coupon.3mf` | seam/reveal coupon only | authored flat face on plate |
| 8 | `MODEL_ONLY_r9_90_degree_tabletop_angle_fixture.3mf` | nominal 90-degree tabletop reference | authored flat face on plate |
| 9 | `MODEL_ONLY_r9_rear_ledger_male_coupon.3mf` | ledger tongue coupon | minimum member end on plate |
| 10 | `MODEL_ONLY_r9_rear_ledger_female_coupon.3mf` | ledger blind-socket coupon | closed maximum member end on plate |
| 11 | `MODEL_ONLY_r9_front_beam_lower_lap_coupon.3mf` | lower staggered-lap coupon | minimum member end on plate |
| 12 | `MODEL_ONLY_r9_front_beam_upper_lap_coupon.3mf` | upper staggered-lap coupon | maximum member end on plate |
| 13 | `MODEL_ONLY_r9_two_socket_outer_bookend_rail_fit_coupon.3mf` | standalone rail/interface coupon | solid back web on plate; installed X/Z on bed |
| 14 | `MODEL_ONLY_r9_flush_blank_cable_module.3mf` | first cable-interface module | local minimum-Z broad side on plate |
| 15 | `MODEL_ONLY_r9_multi_cable_comb_hook_module.3mf` | three-position cable comb/hook | local minimum-Z broad side on plate |
| 16 | `MODEL_ONLY_r9_through_outer_bookend_additive_two_socket_candidate.3mf` | through/far-left handed integrated first article | broad run-side additive print foot on plate |
| 17 | `MODEL_ONLY_r9_return_outer_bookend_additive_two_socket_candidate.3mf` | return/far-right handed integrated first article | broad run-side additive print foot on plate |

Do not mirror either handed corner half or integrated bookend. The two bookend
SKUs are intentionally different because the keyed sockets are asymmetric.

### Stage 2 — R9 first-article print order

Print one part per plate for its first qualification unless the bundle README
explicitly authorizes another arrangement. Stop at the first failed gate.

1. **Straight joints:** print rear-ledger male + female, dry-fit them, then
   print front-beam lower + upper laps and dry-fit them.
2. **Support shapes:** print one compact support, one smooth outer-bookend
   control, and one untrimmed corner-half control. These are separate shape and
   print-quality articles; no support-to-ledger/beam seat exists yet.
3. **Nominal corner:** print the 90-degree tabletop fixture, through handed
   half, return handed half, shear-key handling coupon, then cosmetic reveal
   coupon. Assemble only in the sequence in [ASSEMBLY.md](ASSEMBLY.md).
4. **Standalone cable fit:** print the two-socket rail coupon and flush blank.
   Qualify the blank in each socket separately. Only then print and qualify the
   comb/hook in each socket.
5. **Integrated bookend first articles:** only after the standalone rail passes,
   print the through and return handed integrated bookends. Preserve their
   labels. Test the blank in both sockets of each hand, then the comb/hook.

The integrated receiver rail is fused/additive geometry. Do not attempt to
remove it from the bookend. Endpoint-to-wall installation, doorway/trim
clearance, cable-loop clearance, snag retention, and accessory load are still
unqualified.

### Stage 3 — exact dry fits, then stop

Follow [ASSEMBLY.md](ASSEMBLY.md) on a padded table. Qualification v5 permits
only the two straight-joint dry fits, the five-part nominal-90-degree corner
handling/reveal study, and module service in the standalone and integrated
two-socket receivers.

The compact-support/ledger/front-beam/cassette one-bay assembly is
**software-blocked**. No support seats, cassette/member interface, exact bay
length/end condition, or hardware/framing datum has been authored. Therefore
there is no printable one-bay kit and no full-L tabletop assembly in this
bundle. Do not invent one by lining up loose parts.

After the permitted dry fits, retain:

- photos of the corrected-pose 0.4 key before fit, seated, and removed;
- all faces of each printed R9 article;
- both straight-joint seated and separated views;
- the nominal corner after each assembly step and after disassembly;
- blank and comb/hook service in both sockets of the standalone rail and each
  integrated handed bookend;
- completed print/test records; and
- the completed field measurement worksheet.

No later printing or wall work is authorized by completing Stage 3.

## Orientation and support review for every plate

All 17 R9 parts are authored **Support Off** in the exact saved orientations
listed above. That classification is software evidence, not permission to skip
Bambu Studio Preview.

1. Start a new A1 mini PETG project.
2. Import one individual neutral 3MF at 100% scale.
3. Do not auto-orient, auto-repair, auto-scale, merge, mirror, or lay the part
   on another face.
4. Confirm the saved pose and exact filename against the bundle README and
   manifest. Pay special attention to the opposite broad face on the return
   corner half and the distinct handed bookends.
5. Set Support Off, slice, and inspect Preview layer by layer for disconnected
   islands, weak first-layer contact, bridges, brim collisions, exclusion-zone
   warnings, and edge-reserve violations.
6. Stop if Preview calls for a repair, scale/orientation change, or support.
   Record the mismatch instead of improvising a new pose.

The largest support/bookend envelopes fit the nominal A1 mini volume only in
their saved poses with the documented brim and reserve. Do not rotate a part to
make the plate look fuller.

## Cooled-part inspection

Quarantine the part and do not fit it if any answer is “yes”:

- [ ] wrong filament, color/lot not recorded, or a PLA preset was used;
- [ ] lifting, rocking, or visible warp on a bearing or mating face;
- [ ] crack, layer split, missing extrusion, burned material, or deep scar;
- [ ] white stress mark or permanent bend before testing;
- [ ] support damage or elephant-foot interference on a key/contact surface;
- [ ] unexplained slicer repair, scale other than 100%, or changed orientation;
- [ ] filename/part identity cannot be traced to the manifest; or
- [ ] dimensions fall outside a tolerance explicitly stated by the exact
      bundle validation record or test protocol.

Do not quietly sand, drill, heat-form, glue, or file a rejected part. Record any
post-processing as a failed-as-printed result and obtain a revised test plan.

## Print record

| Stage / part | Exact filename | Manifest SHA or bundle revision | Spool lot | Dry cycle | Studio version | Settings verified | Result / photo ID |
|---|---|---|---|---|---|---|---|
| R8 receiver |  |  |  |  |  |  |  |
| R9 corrected-pose key 0.4 |  |  |  |  |  |  |  |
| R9 smooth bookend control |  |  |  |  |  |  |  |
| R9 compact support |  |  |  |  |  |  |  |
| R9 corner-half control |  |  |  |  |  |  |  |
| R9 through corner half |  |  |  |  |  |  |  |
| R9 return corner half |  |  |  |  |  |  |  |
| R9 shear-key coupon |  |  |  |  |  |  |  |
| R9 cosmetic-cover coupon |  |  |  |  |  |  |  |
| R9 90-degree fixture |  |  |  |  |  |  |  |
| R9 ledger male |  |  |  |  |  |  |  |
| R9 ledger female |  |  |  |  |  |  |  |
| R9 beam lower lap |  |  |  |  |  |  |  |
| R9 beam upper lap |  |  |  |  |  |  |  |
| R9 standalone rail |  |  |  |  |  |  |  |
| R9 flush blank |  |  |  |  |  |  |  |
| R9 comb/hook |  |  |  |  |  |  |  |
| R9 through integrated bookend |  |  |  |  |  |  |  |
| R9 return integrated bookend |  |  |  |  |  |  |  |

## Do not print yet

- duplicate or production quantities of cassettes, ledger pieces, front beams,
  supports, bookends, cable accessories, or corner parts;
- any file from `development/r8/generated/qualification_v1/`;
- either R8 combined catalog or the R9 qualification catalog as a ready-to-slice
  plate;
- a mirrored, scaled, repaired, or user-modified substitute;
- G-code received from another machine or person; or
- any one-bay/full-L substitute, wall-drilling template, anchor, or
  fastener-locating article.
