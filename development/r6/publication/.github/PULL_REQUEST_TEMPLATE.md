## Summary

Describe the r6 design, documentation, test, or model-only artifact change. State whether it affects geometry, package taxonomy, wall attachment, physical gates, or only presentation.

## Required evidence

- [ ] `python -B release_check.py --root . --source-only` passes.
- [ ] `python -B release_check.py --root .` passes with the complete canonical model-only package set.
- [ ] `python -I -B -m unittest discover -s tests -p 'test_*.py'` passes.
- [ ] `python -I -B publish_root.py --audit-publication .` passes for a promoted publication tree.
- [ ] Generated artifacts and `PUBLICATION_MANIFEST.json` are current and no unlisted file is present.

## Safety and release boundaries

- [ ] The shelf remains experimental, unrated, and blocked from overhead use.
- [ ] `physical_installation_qualified` and `production_release_eligible` remain `false`, with nonempty physical qualification blockers.
- [ ] No tested load rating, embedded G-code, slicer profile, printer profile, or printed wall anchor was added or implied.
- [ ] Every wall-fastened support still requires suitable metal structural screws into verified wood studs or purpose-installed blocking.
- [ ] Both shelf levels remain structurally independent and all required keys, pins, housings, and removal/service sweeps remain accessible.
- [ ] Removable ornament retains zero structural credit and does not reduce a frozen structural web, clearance, or isolation threshold.
- [ ] Any changed part still passes one-body, watertight, saved-orientation envelope, actual-parent interface, and package validation checks.
- [ ] Field measurements and physical coupon/full-bay/creep gates remain explicitly unresolved unless supported by reviewed evidence.

## Scope and provenance

- [ ] The exact 6 + 3 two-level hero is identified as visual intent, not engineering evidence.
- [ ] `reference/hybrid_r5` remains byte-identical and clearly labeled as the inactive hybrid fallback.
- [ ] No third-party mesh, personal path/data, cache, temporary output, G-code, or unreviewed license text was introduced.
- [ ] Root documents, their `docs/` mirrors, canonical package labels, and filenames agree.

## Evidence links

Link the relevant validation report, drawing, measurement record, and physical test record. Do not use a rendering as evidence of fit or capacity.
