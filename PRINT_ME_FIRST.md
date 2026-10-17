# Print me first — Triadic Palatine Order R12 final durable

> **Frozen earlier revisions:** the R6–R11 trees under `development/` are historical records governed by their own gate documents, including the R11 print hold, single-use permit protocol, and **0 kg / 0 lb** rating. Nothing in those trees authorizes printing, drilling, installation, or load, and nothing in this r5 document authorizes an R11 job. See [development/r11/README.md](development/r11/README.md), the [R11 print hold](development/r11/PRINT_FIRST.md), the [Gate A-left v2 control overlay](development/r11_print_v2/PRINT_GATE_A_LEFT.md), and the [append-only physical record](development/r11_physical/PHYSICAL_RECORD.md).

The files in `generated/model_only_3mf/` contain geometry only. They deliberately contain **no embedded G-code** because the printer, nozzle, build plate, Bambu Studio version, and exact PETG product remain unconfirmed.

All generated printable components are SUNLU clear PETG finish, ornament, modest item-retention, or fit-check parts. The plywood, steel angles, brackets, standards, locks, blocking, alignment hardware, and wall fasteners are nonprinted structural components and are not contained in any 3MF.

Use only [`generated/final_release_r12/`](generated/final_release_r12/). Its locked A1 Mini profile uses 0.20 mm layers, six walls, five top/bottom shells, 60% gyroid, supports off, a 3 mm outer brim, 240 C nozzle, 70 C Textured PEI bed, 20 mm/s first layer, calibrated flow, and no fan for the first three layers. The old 8 mm brim, 90–100 C bed, and forced 105% flow instructions are superseded.

## Do not print the full set yet

[`MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_FULL_PRINT_SET.3mf`](generated/model_only_3mf/MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_FULL_PRINT_SET.3mf) contains **102 exact-quantity objects** on a virtual catalog canvas: 98 installed pieces and four print-first qualification objects. It is not a real plate layout. Its R12 geometry estimate is 3.12 kg packaged PETG and 3.06 kg installed PETG, excluding slicer-dependent purge, supports, failures, spares, fasteners, plywood, and steel.

Before production, confirm:

- both limiting wall lengths, wall bow, and clearances across the full adjustment zone;
- the included corner angle and a full-size corner template;
- the installed shelf-back offset separately on the long and short walls;
- the actual perpendicular-bracket envelope and the groin-vault clearance after support locations are verified;
- the 8 in depth and 170.056 mm Palatine fascia envelope against doors, trim, outlets, people, and bins;
- verified framing or purpose-installed blocking at every support line;
- exact printer model, nozzle diameter and material, build plate, and Bambu Studio version;
- SUNLU clear PETG lot, the supplied R12 preset, and dry filament;
- the exact removable silicone products, captured fascia-channel fit, rear-curb and groin-vault screws, removal method, and underside clearance below every proposed finish fastener.

Never send or reuse G-code prepared for another printer, nozzle, plate, filament, or design revision.

## First-print and fit sequence

1. Print one [`MODEL_ONLY_PETG_TopTile_Center_6inPitch.3mf`](generated/model_only_3mf/MODEL_ONLY_PETG_TopTile_Center_6inPitch.3mf). This is an actual installed part; the long wall uses 14. Reject lifted edges, dragged strands, separated first-layer lines, delamination, or more than 0.5 mm cooled corner lift.
2. After that tile passes, print the remaining 13 long-wall center tiles. Universal rear-curb centers may follow; the long wall uses eight.
3. Before fitted fascia or corner production, print [`MODEL_ONLY_PRINT_FIRST_R12_AdhesionCornerCoupon.3mf`](generated/model_only_3mf/MODEL_ONLY_PRINT_FIRST_R12_AdhesionCornerCoupon.3mf).
4. Obtain the actual 23/32 in plywood and 1 x 1 x 1/8 in steel angle. Print [`MODEL_ONLY_PRINT_FIRST_FasciaFitCoupon.3mf`](generated/model_only_3mf/MODEL_ONLY_PRINT_FIRST_FasciaFitCoupon.3mf) and fit it to that stack **with a printed 2.4 mm top-tile sample in place**. The nominal 46.656 mm opening must slide without splitting, binding, lifting the tile, or excessive rattle.
5. Print [`MODEL_ONLY_PRINT_FIRST_PalatineDetailCoupon.3mf`](generated/model_only_3mf/MODEL_ONLY_PRINT_FIRST_PalatineDetailCoupon.3mf) face-up. Approve the 2.4 mm archivolt shadow reveal, 3:4:5 void, flutes, pier base/capital relief, nine dentils, three triglyph groups, three cornice orders, central patera, bridge quality, edge finish, and removability before printing ornate production parts.
   Compare it with the [nominal Palatine elevation](generated/palatine_elevation.svg), whose stations, counts, and dimensions are exact while its displayed arch curves are schematic. It is not a structural drawing or proof of printer fit.
6. Print [`MODEL_ONLY_PRINT_FIRST_CornerFitGauge.3mf`](generated/model_only_3mf/MODEL_ONLY_PRINT_FIRST_CornerFitGauge.3mf), compare it with the real corner and a full-size cardboard or hardboard template, and confirm the ±0.25° gate and at least 0.6 mm residual joint clearance.
7. Measure the shelf-back offset separately on both walls. Do not substitute the catalog standard projection for either installed measurement.
8. Coupon-test attachments, rebuild fitted pieces, then inspect one long-wall fascia half before its remaining production queue.
9. Dry-assemble PETG only on the unloaded, independently supported plywood-and-steel structure and verify every seam, capture, floating joint, cap, curb, and soffit clearance.
10. Do not print return-arm production quantities until its field measurements are entered and regenerated.

## Current nominal production counts

| PETG part family | 3 ft return | 5 ft through / corner | Shared / test | Total |
|---|---:|---:|---:|---:|
| Universal center top tile | 6 | 14 | — | 20 |
| Square-mating corner quadrant | — | 4 | — | 4 |
| Shared parametric top end | 4 | 4 | — | 8 |
| Palatine arcade/fascia left half | 3 | 6 | — | 9 |
| Palatine arcade/fascia right half | 3 | 6 | — | 9 |
| Removable Palatine entablature overlay | 6 | 12 | — | 18 |
| Universal center rear curb | 3 | 8 | — | 11 |
| Arm-specific rear-curb end | 2 | 2 | — | 4 |
| Through-owned corner-side rear curb | — | 1 | — | 1 |
| Palatine keystone seam cover | 3 | 6 | — | 9 |
| Palatine full-height outer endcap | 1 | 1 | — | 2 |
| Palatine re-entrant corner pilaster | — | — | 1 | 1 |
| Palatine groin-vault corner soffit | — | 1 | — | 1 |
| Rear-curb fitted corner replacement | — | — | 1 | 1 |
| Adhesion corner + corner gauge + fascia + Palatine coupons | — | — | 4 | 4 |
| **Total** |  |  |  | **102** |

The installed set is 98 objects; the gauge and three coupons are not installed.

## Nominal module facts

- Top centers: 151.8 x 101.3 x 2.4 mm; arm-specific ends regenerate from measured length.
- Corner quadrants: four identical 101.3 x 101.3 x 2.4 mm parts.
- Short-arm arcade halves: 113.827 x 170.056 x 29.0 mm, three left and three right, resolving three bays; nominal/on hold.
- Long-arm arcade halves: 110.722 x 170.056 x 29.0 mm, six left and six right, resolving six bays.
- Entablature overlays: one per arcade half, 24 mm high and 3.2 mm overall relief thickness.
- Keystones: nine at 18 x 24 x 2.4 mm; retain each to one half and float it across the other.
- Through rear-curb ends: 126.481 mm; return rear-curb ends: 115.581 mm.
- Through-owned corner-side rear curb: 172.6 mm. It stops before the 1.6 mm plywood joint.
- Full-height endcaps and corner pilaster: 170.056 mm tall.
- Groin-vault soffit: 42 mm square and nominally 18.519 mm from the nearest support plane; the configured minimum is 10 mm.

## Attachment and installed stack

Every finish piece attaches with qualified removable products only. The full
build sequence, silicone dot counts, curb drilling procedure, and installed
z-stack are owned by [ASSEMBLY.md](ASSEMBLY.md) (with the geometry defined in
[ENGINEERING_DESIGN.md](ENGINEERING_DESIGN.md) section 6 and the policy in
section 8). Never drill or notch the continuous steel angle, bridge a 0.6 mm
seam or the plywood joint, or clamp PETG rigidly.

## Saved-orientation rule

All R12 meshes fit the declared 180 x 180 x 180 mm model envelope in their generated orientation. The largest arcade halves are 170.056 mm tall. Preserve saved orientation and use the supplied 3 mm brim; a larger brim does not fit the A1 Mini plate safely. Arcade halves are saved front-face-down so their channel flanges grow upward without supports. Model-only 3MFs contain no G-code.

## Plate-fit and batching cautions for a 180 mm printer

- The 170.056 mm fascia footprint leaves less than 5 mm per side before brim. Center it, use exactly the 3 mm brim, and confirm exclusion zones in Preview.
- The 2.4 mm top tiles are large PETG flats and remain warp-sensitive. Use a detergent-washed, fingerprint-free plate, avoid drafts, and reject any lifted corner.
- The full set is roughly a hundred objects across many plates on a 180 mm printer. Batch like parts together (tiles with tiles, halves one or two per plate), print one part from each family for the step-9 dry fit before committing to production quantities, and track finished counts against the production table above.

## Production boundary

The arches, piers, vault, fascia, curbs, and tiles are ornate PETG finish pieces—not structural Roman masonry and not hidden printed brackets. Do not print substitutes for plywood, steel angle, standards, brackets, locks, blocking, or structural fasteners. The selection targets remain untested and are not load ratings.
