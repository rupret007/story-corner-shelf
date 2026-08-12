# R11 first-outer-bay neutral qualification bundle

This package contains exactly eight R11 qualification articles: the S0 fused
cable support, one ordinary support, two terminal-length bay-0 half-decks, one
bay-local keystone, two flush blanks, and one comb/hook.  It is **not a
full-wall set**, is rated **0 kg / 0 lb**, and grants no permission to print,
drill, install, or load anything.

## Hard boundary

- No slicer profile, G-code, toolpath, printer credential, or print command is
  present.
- The combined 3MF is deliberately off-plate and must not be printed.
- Never auto-scale, auto-orient, mirror, repair, or substitute an R10 part.
- Read `PRINT_FIRST.md`; before every possible future article, inspect the
  exact individual model at 100% XYZ scale in slicer Preview and obtain fresh,
  explicit human permission.  This bundle does not provide that permission.
- Keep all wall bores empty.  Do not drill or attach this candidate to a wall.
- Cable articles and the keystone receive zero sustained-load credit.

Use only the exact individual files in `individual_model_only_3mf/` for
neutral inspection.  The checked qualification-only assembly schematic is at
`visuals/r11_first_outer_bay_exploded_and_wall_topology.svg`.
`layout_report.json`, `normalized_inputs.json`,
`validation.json`, `release_status.json`, and `manifest.json` preserve the
controlling calculation, evidence, safety boundary, and hashes.
