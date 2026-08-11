# R9 compact-bookend PETG qualification v4

**QUALIFICATION ARTICLES ONLY — RATED LOAD 0 KG / 0 LB.**

This directory does not contain a full shelf set, wall bores, G-code,
or an installed release. The combined 3MF is an off-plate catalog, not
a print plate. Open individual 3MF files one at a time at 100% scale.

## Enter these settings manually in Bambu Studio

- Machine: `Bambu Lab A1 mini 0.4 nozzle`.
- Plate: `Textured PEI Plate`.
- Filament: `SUNLU PETG @BBL A1M 0.4 nozzle`; SUNLU black PETG, ASIN `B0D1KC72YP`.
  If that exact preset is absent, duplicate Generic PETG, enter every
  value below, save it under the exact SUNLU preset name, and recheck it.
- Process starting point: `0.20mm Strength @BBL A1M`.
- 0.20 mm layer, 6 walls, 5 top / 3 bottom, 25% grid infill.
- Nozzle 250 C first / 245 C other; Textured PEI 60 C.
- Flow 0.94; max volumetric speed 9.0 mm3/s.
- Outer brim 5.0 mm, object gap 0.1 mm; keep at least 2.0 mm extra plate reserve.
- Dry at 50 C for 6–8 h only if the received spool and dryer permit it;
  never exceed the lower stated limit. Record spool lot, drying, and flow
  calibration. Do not reuse a PLA profile.
- Never Auto-orient, scale, repair, or arrange. Inspect Preview before print.

## Print in this order

0. From the frozen R8 v2 bundle, print the receiver and keys in this
   order: receiver, 0.5, 0.4, 0.3, then 0.2 mm per-face key. Proceed only
   if the 0.4 mm key qualifies. Dependency manifest: `../../../r8/generated/qualification_v2/manifest.json`.
1. Print `r9_rear_ledger_male_coupon` + `r9_rear_ledger_female_coupon`,
   then `r9_front_beam_lower_lap_coupon` +
   `r9_front_beam_upper_lap_coupon`. Dry-fit only; no load credit.
2. Print `r9_compact_support`, `r9_shortened_outer_bookend_support`,
   and `r9_concealed_corner_half_control`. Inspect each separately; any
   detectable rocking or visible warp fails the first article. The R8
   structural-control comparison is a future gated test, not this print stage.
3. Print `r9_90_degree_tabletop_angle_fixture`, the through and return
   hidden halves, the shear-key coupon, and cosmetic cover. This proves
   nominal-square handling/reveal only; the closet angle is unverified.
4. Print `r9_two_socket_outer_bookend_rail_fit_coupon` and
   `r9_flush_blank_cable_module`; qualify both sockets. Then print
   `r9_multi_cable_comb_hook_module`. Insert straight inward at the upper
   entry, drop exactly 8 mm, and remove by the exact reverse path.
5. Only after the standalone interface passes, print the distinct through
   and return `outer_bookend_additive_two_socket_candidate` articles.
   Their receivers are fused/additive, not removable rails. Test blank and
   comb in both sockets on the table. Do not attach them to a wall.
6. Stop after the required tabletop articles and service checks. Do not
   print duplicates as a shelf set.

## Per-part saved orientation and support rule

- `r9_shortened_outer_bookend_support` — Support OFF; `broad_min_z_constant_profile`.
- `r9_compact_support` — Support OFF; `broad_min_z_constant_profile`.
- `r9_concealed_corner_half_control` — Support OFF; `broad_min_z_constant_profile`.
- `r9_through_hidden_corner_half` — Support OFF; `broad_min_z_miter_only_subtracts`.
- `r9_return_hidden_corner_half` — Support OFF; `broad_max_z_miter_only_subtracts`.
- `r9_under_shelf_shear_key_coupon` — Support OFF; `flat_authored_face_on_plate`.
- `r9_cosmetic_corner_cover_coupon` — Support OFF; `flat_authored_face_on_plate`.
- `r9_90_degree_tabletop_angle_fixture` — Support OFF; `flat_authored_face_on_plate`.
- `r9_rear_ledger_male_coupon` — Support OFF; `minimum_member_end_on_plate`.
- `r9_rear_ledger_female_coupon` — Support OFF; `closed_maximum_member_end_on_plate`.
- `r9_front_beam_lower_lap_coupon` — Support OFF; `minimum_member_end_on_plate`.
- `r9_front_beam_upper_lap_coupon` — Support OFF; `maximum_member_end_on_plate`.
- `r9_two_socket_outer_bookend_rail_fit_coupon` — Support OFF; `solid_back_web_on_plate_installed_xz_bed`.
- `r9_flush_blank_cable_module` — Support OFF; `local_minimum_z_broad_side_on_plate`.
- `r9_multi_cable_comb_hook_module` — Support OFF; `local_minimum_z_broad_side_on_plate`.
- `r9_through_outer_bookend_additive_two_socket_candidate` — Support OFF; `broad_run_side_additive_print_foot_on_plate`.
- `r9_return_outer_bookend_additive_two_socket_candidate` — Support OFF; `broad_run_side_additive_print_foot_on_plate`.

Support-off inventory: r9_shortened_outer_bookend_support, r9_compact_support, r9_concealed_corner_half_control, r9_through_hidden_corner_half, r9_return_hidden_corner_half, r9_under_shelf_shear_key_coupon, r9_cosmetic_corner_cover_coupon, r9_90_degree_tabletop_angle_fixture, r9_rear_ledger_male_coupon, r9_rear_ledger_female_coupon, r9_front_beam_lower_lap_coupon, r9_front_beam_upper_lap_coupon, r9_two_socket_outer_bookend_rail_fit_coupon, r9_flush_blank_cable_module, r9_multi_cable_comb_hook_module, r9_through_outer_bookend_additive_two_socket_candidate, r9_return_outer_bookend_additive_two_socket_candidate.
Support-required inventory: none.
Support classification is software evidence only; Preview remains mandatory.

## Hard stop

Do not drill, mount, print the full shelf, store anything on these
parts, or infer a load rating. Endpoint doorway/trim/cable-loop clearance, a complete
one-bay support/member interface, exact corner field geometry, framing,
hardware, proof, creep, recovery, and destructive tests remain open.
Start with `docs/PRINTER_KICKOFF.md`, then use this bundle's
remaining `docs/` guides for records and gates.
