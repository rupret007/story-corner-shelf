# Contributing

Changes are welcome after the repository owner selects a license and contribution policy. Until then, this is the required local change workflow rather than permission to reuse the design.

## Design invariants

Every change must preserve these boundaries unless the project is explicitly re-scoped and independently reviewed:

- PETG parts are nonstructural finish, ornament, fit-check, and modest item-retention components.
- Each plywood deck and steel front angle remains continuous within its own arm.
- The 5 ft through deck owns the corner square; the 3 ft return starts beyond its front plane; plywood footprints do not overlap.
- Both arms retain independent steel-bracket support. PETG, the wood seam, angle contact, and optional alignment plates receive no capacity credit.
- A visually all-PETG Palatine finish is not permission to substitute printed brackets, a printed deck, or printed wall anchors.
- Primary wall attachment uses verified framing or purpose-installed structural blocking.
- Support intervals do not exceed 16 in, end overhangs do not exceed 6 in, field centers remain independently spaced, and nominal conservative perpendicular-bracket clearance does not fall below 1 in.
- Installed shelf-back offset is measured and stored independently for both wall runs.
- The square-footprint corner gate is ±0.25°, the nominal plywood gap is 1.6 mm, and the remaining nominal clearance must be at least 0.6 mm. A full-size template remains required.
- No rear curb, curb fastener, Palatine corner piece, or groin-vault soffit crosses the plywood joint.
- Every entablature remains attached to its own fascia half; keystones and the corner pilaster retain one fixed side and one floating side.
- The groin-vault soffit stays entirely on the through-owned corner square and retains at least 10 mm generated clearance to the nearest verified support plane.
- A same-height L level is unloaded and moved as one coupled assembly.
- No untested load rating or machine-specific G-code is committed.

The R12 3/6-bay arcade, nine-keystone rhythm, reinforced thickness standard, and related 3–6–9 details are edition-level parameters. Changing them creates a new reviewed edition rather than an incidental cosmetic patch.

## Change workflow

1. Create a focused branch.
2. Update `config.json`; do not hard-code project measurements or Palatine proportions in the generator.
3. Update documentation whenever an assumption, datum, measurement, part name, count, attachment policy, mass, safety boundary, rendering, or workflow changes.
4. Add or update regression tests for every changed parameter relationship.
5. Rebuild with Python 3.12 and the pinned dependencies:

   ```sh
   PYTHON_BIN=.venv/bin/python SKIP_BAMBU=1 scripts/build_all.sh
   ```

6. On a Mac with Bambu Studio installed, run the strict integration check before a printable release:

   ```sh
   PYTHON_BIN=.venv/bin/python REQUIRE_BAMBU=1 scripts/build_all.sh
   ```

7. Review the complete generated diff, including `corner_layout.svg`, `palatine_elevation.svg`, `validation.json`, structural/cut/support reports, every STL/3MF filename, object counts, packaged/installed mass estimates, and artifact hashes.
8. Confirm the final rendering referenced by documentation is `generated/artist_rendering_triadic_palatine_order.png`.
9. Run the build again and require a clean generated diff. Renamed parts must not leave stale artifacts or stale r4 counts.
10. Keep commits small enough to distinguish source changes from regenerated artifacts.

## Measurement changes

The common coordinate datum is the intersection of the two finished wall planes. A measurement update must include:

- limiting clear length for both walls at the rear, center, and front planes of every proposed elevation;
- installed shelf-back offset for the long wall and short wall as separate measurements;
- support centers as absolute distances from the corner datum, with stud edges/centers and framing material;
- included corner angle, wall bow, drywall/caulk profile, calculated residual joint clearance, and a full-size template;
- exact bracket width/reach/body envelope, locks, fasteners, and perpendicular dry-fit result;
- regenerated groin-vault-to-bracket clearance;
- common shelf-top elevation, 170.056 mm Palatine fascia clearance, door/trim clearance, electrical/plumbing constraints, and number of loaded levels;
- bin dimensions, heaviest object, intended evenly distributed contents, and measured shelf-arm dead load;
- confirmed Bambu Lab A1 mini, 0.4 mm nozzle, Textured PEI Plate, slicer version, SUNLU clear PETG lot, and filament condition;
- selected removable silicone, captured fascia-channel fit, curb/groin-vault screw stack, and removal method with qualification results on printed PETG, sealed plywood, and actual coated steel where applicable.

Photographs must exclude faces, addresses, serial numbers, and other private information before being added to a public issue.

## Pull-request checklist

- [ ] Field values are clearly measured, nominal, or unconfirmed.
- [ ] Both per-wall installed shelf-back offsets are represented correctly.
- [ ] Through/return ownership is unchanged or separately reviewed; plywood footprints do not overlap.
- [ ] Both arms remain independently supported and no PETG/alignment detail entered the permanent load path.
- [ ] Spacing, overhang, distinct-center, perpendicular-bracket, and groin-vault-clearance gates pass.
- [ ] Exact perpendicular brackets, locks, angles, and fasteners were dry-fitted when field hardware changed.
- [ ] Corner angle is within ±0.25°, remaining nominal joint clearance is at least 0.6 mm, and the full-size template was reviewed—or the footprints were redesigned and reviewed.
- [ ] Rear-curb pieces, slots, tile drill paths, and fasteners remain separated from the plywood joint and have underside clearance.
- [ ] Palatine overlays, keystones, pilaster, endcaps, and soffit follow their own-segment/floating/removable attachment rules.
- [ ] All STL meshes are one closed, consistently wound body in saved orientation and fit the declared 180 mm envelope.
- [ ] All 3MF packages contain no embedded G-code and pass archive/Bambu checks as applicable.
- [ ] The full-set count, installed count, packaged/installed mass, cut/print plans, reports, and hashes agree.
- [ ] Documentation links, final rendering filename, and a clean deterministic rebuild pass.
- [ ] No local archives, virtual environments, slicer scratch files, machine code, or personal data are included.
