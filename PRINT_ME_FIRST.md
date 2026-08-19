# Print me first — Triadic Palatine Order r5

> **Frozen earlier revisions:** the R6–R11 trees under `development/` are historical records governed by their own gate documents, including the R11 print hold, single-use permit protocol, and **0 kg / 0 lb** rating. Nothing in those trees authorizes printing, drilling, installation, or load, and nothing in this r5 document authorizes an R11 job. See [development/r11/README.md](development/r11/README.md), the [R11 print hold](development/r11/PRINT_FIRST.md), the [Gate A-left v2 control overlay](development/r11_print_v2/PRINT_GATE_A_LEFT.md), and the [append-only physical record](development/r11_physical/PHYSICAL_RECORD.md).

The files in `generated/model_only_3mf/` contain geometry only. They deliberately contain **no embedded G-code** because the printer, nozzle, build plate, Bambu Studio version, and exact PETG product remain unconfirmed.

All generated printable components are black PETG finish, ornament, modest item-retention, or fit-check parts. The plywood, steel angles, brackets, standards, locks, alignment hardware, and wall fasteners are nonprinted structural components and are not contained in any 3MF.

## Do not print the full set yet

[`MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_FULL_PRINT_SET.3mf`](generated/model_only_3mf/MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_FULL_PRINT_SET.3mf) contains **101 exact-quantity objects** on a virtual catalog canvas: 98 installed pieces and three print-first test objects. It is not a real plate layout. Its nominal geometry estimate is 2.45 kg packaged PETG and 2.42 kg installed PETG, excluding slicer-dependent purge, supports, failures, spares, fasteners, plywood, and steel.

Before production, confirm:

- both limiting wall lengths, wall bow, and clearances across the full adjustment zone;
- the included corner angle and a full-size corner template;
- the installed shelf-back offset separately on the long and short walls;
- the actual perpendicular-bracket envelope and the groin-vault clearance after support locations are verified;
- the 8 in depth and 168.056 mm Palatine fascia envelope against doors, trim, outlets, people, and bins;
- verified framing or purpose-installed blocking at every support line;
- exact printer model, nozzle diameter and material, build plate, and Bambu Studio version;
- black PETG manufacturer/product line, an appropriate preset, and dry filament;
- the exact removable silicone products, captured fascia-channel fit, rear-curb and groin-vault screws, removal method, and underside clearance below every proposed finish fastener.

Never send or reuse G-code prepared for another printer, nozzle, plate, filament, or design revision.

## First-print and fit sequence

1. Print [`MODEL_ONLY_PRINT_FIRST_CornerFitGauge.3mf`](generated/model_only_3mf/MODEL_ONLY_PRINT_FIRST_CornerFitGauge.3mf) with the confirmed setup.
2. Compare it with the real corner and a full-size cardboard or hardboard template. The configured square-deck gate is **±0.25°**, and the remaining nominal plywood-joint clearance must be at least **0.6 mm**. The full-size template is mandatory even when the small gauge fits.
3. Measure the shelf-back offset separately on both walls. Do not substitute the catalog standard projection for either installed measurement.
4. Obtain the actual 23/32 in plywood and 1 x 1 x 1/8 in steel angle. Measure the completed front stack.
5. Print [`MODEL_ONLY_PRINT_FIRST_FasciaFitCoupon.3mf`](generated/model_only_3mf/MODEL_ONLY_PRINT_FIRST_FasciaFitCoupon.3mf) and fit it to a real plywood/angle scrap **with a printed 2.0 mm top-tile sample in place**. The nominal 46.256 mm opening includes plywood, the 25.4 mm angle leg, the tile, and 0.6 mm clearance. It must slide without splitting, binding, lifting the tile, or excessive rattle.
6. Print [`MODEL_ONLY_PRINT_FIRST_PalatineDetailCoupon.3mf`](generated/model_only_3mf/MODEL_ONLY_PRINT_FIRST_PalatineDetailCoupon.3mf) face-up. Approve the 2.4 mm archivolt shadow reveal, 3:4:5 void, flutes, pier base/capital relief, nine dentils, three triglyph groups, three cornice orders, central patera, bridge quality, edge finish, and removability before printing ornate production parts.
   Compare it with the [nominal Palatine elevation](generated/palatine_elevation.svg), whose stations, counts, and dimensions are exact while its displayed arch curves are schematic. It is not a structural drawing or proof of printer fit.
7. Coupon-test the selected neutral-cure silicone on printed PETG, sealed plywood, and the actual coated steel wherever it will touch. Verify captured-channel fit on the complete fascia stack, and test the selected curb and groin-vault screws in representative plywood with safe underside clearance. Do not drill or notch the continuous steel angle for fascia retention. Attachment prevents loose trim only; it receives no shelf-load credit.
8. If any gauge, coupon, or attachment test fails, update the measured configuration or clearance, rebuild everything, and repeat. Do not selectively scale a fitted part in the slicer.
9. Print and dry-fit one left and one right arcade/fascia half for each arm, one matching entablature overlay, one keystone, one top center, one top end, one corner quadrant, both arm-specific rear-curb ends, the 172.6 mm corner-side curb, the 30 mm corner replacement, the full-height corner pilaster, one endcap, and the groin-vault soffit.
10. Dry-assemble the PETG only on scrap or on the **unloaded, independently supported** plywood-and-steel L. Verify every 0.6 mm seam, the 1.0 mm return-tile overhang, full upper/lower fascia capture without binding, the required lateral assembly order, no rear-curb overlap, a floating keystone/pilaster leg, flush outer caps, and at least 10 mm groin-vault clearance from the nearest verified bracket plane.
11. Only after all checks pass should the remaining production quantities be arranged and sliced.

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
| Corner gauge + fascia coupon + Palatine coupon | — | — | 3 | 3 |
| **Total** |  |  |  | **101** |

The installed set is 98 objects; the gauge and two coupons are not installed.

## Nominal module facts

- Top centers: 151.8 x 101.3 x 2.0 mm; shared top ends: 116.081 x 101.3 x 2.0 mm.
- Corner quadrants: four identical 101.3 x 101.3 x 2.0 mm parts.
- Short-arm arcade halves: 113.994 x 168.056 x 29.0 mm, three left and three right, resolving three bays.
- Long-arm arcade halves: 107.630 x 168.056 x 29.0 mm, six left and six right, resolving six bays.
- Entablature overlays: one per arcade half, 24 mm high and 3.2 mm overall relief thickness.
- Keystones: nine at 18 x 24 x 2.4 mm; retain each to one half and float it across the other.
- Through rear-curb ends: 126.481 mm; return rear-curb ends: 115.581 mm.
- Through-owned corner-side rear curb: 172.6 mm. It stops before the 1.6 mm plywood joint.
- Full-height endcaps and corner pilaster: 168.056 mm tall.
- Groin-vault soffit: 42 mm square and nominally 18.519 mm from the nearest support plane; the configured minimum is 10 mm.

## Attachment and installed stack

Every finish piece attaches with qualified removable products only. The full
build sequence, silicone dot counts, curb drilling procedure, and installed
z-stack are owned by [ASSEMBLY.md](ASSEMBLY.md) (with the geometry defined in
[ENGINEERING_DESIGN.md](ENGINEERING_DESIGN.md) section 6 and the policy in
section 8). Never drill or notch the continuous steel angle, bridge a 0.6 mm
seam or the plywood joint, or clamp PETG rigidly.

## Saved-orientation rule

All r5 meshes fit the declared 180 x 180 x 180 mm minimum model envelope in their generated orientation. The largest arcade halves are 168.056 mm tall, leaving little room for arbitrary rotation or an oversized brim on a 180 mm plate. Use the saved orientation as the starting point, print the Palatine overlay/detail faces up, and re-run arrangement checks on the confirmed printer. The arcade halves are saved front-face-down so their channel flanges grow upward and need no support material. No supports, layer heights, temperatures, speeds, or machine profiles are embedded in the model-only 3MFs.

## Plate-fit and batching cautions for a 180 mm printer

- The 168.056 mm plate footprint of each arcade half, endcap, and corner pilaster — and the 172.6 mm corner-side curb — leaves roughly 6 mm of plate margin per side. Keep any brim to about 5 mm or less on these parts, or place the long curbs diagonally; confirm the slicer's exclusion zones before slicing.
- The 2.0 mm top tiles are large thin PETG flats (up to 151.8 x 101.3 mm) and are the most warp-prone parts in the set. Use a clean, adhesion-checked plate, avoid drafts, and plan a small number of spare tiles — 20 centers are needed and a single lifted corner scraps the tile.
- The full set is roughly a hundred objects across many plates on a 180 mm printer. Batch like parts together (tiles with tiles, halves one or two per plate), print one part from each family for the step-9 dry fit before committing to production quantities, and track finished counts against the production table above.

## Production boundary

The arches, piers, vault, fascia, curbs, and tiles are ornate PETG finish pieces—not structural Roman masonry and not hidden printed brackets. Do not print substitutes for plywood, steel angle, standards, brackets, locks, blocking, or structural fasteners. The selection targets remain untested and are not load ratings.
