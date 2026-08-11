# R9 Palatine Moderne tabletop one-bay prototype v3

This is the first R9 package that assembles into an actual shelf section.  It
is a **160 mm-wide, 152.4 mm-deep, 30 mm-high no-load tabletop prototype**.
It contains two handed compact supports, a rear ledger, a front beam, and one
open-bottom three-web shelf cassette. The compressed Roman support arches now
carry additive stepped keystones, and the front beam has a stepped Art-Deco
center relief. Each support has three authored diamond mounting bores at 16,
80, and 144 mm below the shelf underside. They clear a 7.0 mm round metal-
fastener envelope; do not drill or enlarge the PETG after printing.

## Hard boundary

This package is for fit, printability, appearance, mounting-hole inspection,
and hand-assembly evidence.  It has **0 kg / 0 lb rating**.  Do not drill a
wall, mount it, store anything on it, or print production quantities.  The
selected screw/washer candidate is documented in `MATERIALS_AND_HARDWARE.md`,
but substrate, continuous blocking, the PETG clamping interface, long-span,
corner, and load paths remain intentionally unapproved.

## What to print

Use only the five files in `individual_model_only_3mf/`.  Do not print the
assembly-reference 3MF or the STLs unless a documented recovery requires an
STL.  Each individual 3MF contains one object at 100% scale in its authored
print orientation.

1. `MODEL_ONLY_r9_one_bay_left_compact_support.3mf`
2. `MODEL_ONLY_r9_one_bay_right_compact_support.3mf`
3. `MODEL_ONLY_r9_one_bay_rear_ledger.3mf`
4. `MODEL_ONLY_r9_one_bay_front_beam.3mf`
5. `MODEL_ONLY_r9_one_bay_shelf_cassette.3mf`

Print one file at a time.  The rear and front members intentionally share the
same physical interface but are separate required articles.  Stop after every
part for cooling and inspection.  Any crack, layer split, rocking, visible
warp, whitening, increasing bind, or forced fit is a failure.

## Frozen slicer process

- Bambu Lab A1 mini, 0.4 mm nozzle, Textured PEI plate
- SUNLU PETG `@BBL A1M 0.4 nozzle`
- `0.20mm Strength @BBL A1M`
- 0.20 mm layers; 6 walls; 25% grid; 5 top / 3 bottom
- Support OFF
- Outer brim only, 5.0 mm width, 0.1 mm object gap
- 100% scale; no auto-orient, auto-arrange, or repair

The 3MF files are neutral and contain no slicer profile or G-code.  Verify the
settings and Preview for every part.  Codex must report time/material and wait
for explicit approval before every physical print.

## Assembly

Read `MATERIALS_AND_HARDWARE.md`, `DESIGN_LANGUAGE.md`, then `ASSEMBLY.md`.
First verify all six printed mounting bores are open and clean without
reaming. Then stand both supports on a padded
table, lower the rear ledger and front beam into their top-open sockets, then
lower the cassette onto the four top locator bosses.  Never hammer, clamp,
twist, sand, file, lubricate, or load it.

## Measured-wall continuation

After this bay passes, the first installed-design phase is the 61.25 in outlet
wall at the 68 in shelf-top elevation.  Its exact candidate is six stations at
equal 304.75 mm / 11.998 in pitch: one far-left bookend, four short compact
supports, and one concealed corner-end support.  These are design centers, not
released drilling coordinates; trim, wall bow, framing/blocking, substrate,
and one exact fastener system still have to be bound.
