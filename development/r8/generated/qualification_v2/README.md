# R8 PETG qualification bundle

This is an **unsliced, zero-rated qualification set**, not an installed shelf
release. It contains 15 one-body test models, no wall-fastener
bores, no G-code, no toolpaths, and no embedded Bambu Studio process profile.

The frozen filament identity is **SUNLU
PETG black**, ASIN
`B0D1KC72YP`: [selected listing](https://www.amazon.com/dp/B0D1KC72YP?ref=ppx_yo2ov_dt_b_fed_asin_title&th=1).
Selected variant: `4 kg bundle; 2 Black + 2 Black (four 1 kg black spools); 1.75 mm +/-0.02 mm`. Confirm the received
spool label before use; the label and dryer limit control, and the lower stated
temperature limit must never be exceeded.

## Open in Bambu Studio

1. Start a new `Bambu Lab A1 mini 0.4 nozzle` project
   with the Textured PEI
   plate. These neutral 3MFs do **not** select a printer, filament, or process
   preset. Never reuse a PLA preset for these PETG qualification parts.
2. Import one file from `individual_model_only_3mf/` at **100% scale**. Do not
   auto-scale, auto-orient, or repair it. The combined 3MF is an all-parts catalog;
   it is not one A1 mini plate, so do not slice the combined layout as-is.
3. Select `SUNLU PETG @BBL A1M 0.4 nozzle` and `0.20mm Strength @BBL A1M`.
   Explicitly verify: 0.20 mm layers,
   6 wall loops,
   5 top / 3 bottom
   shell layers, 25% **grid**
   infill, Brim type `Outer brim only`, 5.0 mm brim width,
   and 0.1 mm brim-object gap.
4. Verify 250 C first layer /
   245 C later layers,
   60 C bed,
   0.94 flow ratio,
   9 mm^3/s maximum volumetric
   speed, 10-30% normal fan, and
   90% overhang fan. The SUNLU standard-PETG
   baseline is 50 C (validated lower/upper values:
   50 C / 50 C)
   for 6-8 hours, conditional on the
   received spool label and dryer limit. Record the spool lot, exact drying
   cycle, and flow calibration before printing. Source:
   https://store.sunlu.com/products/over-6kg-bundle-sale-petg-3d-printer-filament-1-75mm-1kg-roll
5. Print the clearance receiver and keys first, testing **loosest to tightest**:
   0.5, 0.4, 0.3, then 0.2 mm per face. The authored interface is 0.4 mm; if
   0.4 does not qualify, stop and correct the process rather than scaling parts.
6. Continue only in this order: mounted rail + blank; one D-frame + rail fit;
   the remaining cable modules; then one selected U-box cassette. Curved,
   straight, and heavy-coffer controls are comparison articles, not shelf-set
   production parts.

## Support rules are part-specific

- The saved blank, rail, D-frames, clearance articles, and cassette candidates
  pass the deposited-layer connectivity gate. Start with Support OFF for those
  exact saved orientations, inspect Preview, and stop if Studio reports a new
  island or changes the orientation.
- The single peg, three-cable comb, and coil J-hook have intentional cable
  features that begin as unsupported islands in the saved orientation. Use
  manually reviewed/painted support for those three parts only, while keeping
  support out of the keyed head, latch, receiver, and rail-contact surfaces.
- Install combs from the bottom socket upward. Remove combs from the top socket
  downward; a moving comb is not independently serviceable beneath an occupied
  neighboring socket.

The selected U-box is already oriented with its **visible front long edge on
the plate** and a 45
degree bed yaw. Its validated part envelope is 163.4367 x 163.4367 mm
by 152.4 mm high; 5.0 mm brim,
0.1 mm brim-object gap, and the independent
2
mm-per-edge reserve require 177.6367 x 177.6367 mm. Center it
on the plate. If
Studio reports an exclusion-zone
conflict, stop—never auto-scale it to force a fit.

The clean default layout equips alternating supports: through-run indices
1/3/5/7 and return-run indices 1/3. That is 6 rails / 18 sockets per level
(12 / 36 across two levels). All 10 interior supports per level remain
geometrically eligible, but are not all equipped by default.

Do not install or load these parts yet. Target shelf load, wall/framing survey,
metal structural screw schedule, cassette print proof, dimensional fit, cyclic
retention, thermal cycling, creep, proof-load, and destructive testing remain
unresolved. Printed wall anchors and hollow-wall anchors are not authorized in
the primary load path.
