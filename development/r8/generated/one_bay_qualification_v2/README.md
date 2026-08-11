# R8 one-bay PETG qualification bundle

This is an **unsliced, zero-rated, five-part fit qualification**, not an
installed shelf release. It contains exactly one registered cassette, one
left rail-ready locator D-frame, one right smooth locator/keeper D-frame, one
mounted rail, and one retained blank. It contains no G-code, toolpath, printer
profile, wall-fastener bores, or load rating.

The frozen filament identity is **SUNLU
PETG black**, ASIN
`B0D1KC72YP`: [selected listing](https://www.amazon.com/dp/B0D1KC72YP?ref=ppx_yo2ov_dt_b_fed_asin_title&th=1).
Selected variant: `4 kg bundle; 2 Black + 2 Black (four 1 kg black spools); 1.75 mm +/-0.02 mm`. Confirm the received
spool label; the label and dryer limit control, and the lower stated temperature
limit must never be exceeded.

## Gate 0: qualify 0.4 mm first

Before printing this bundle, use the clearance ladder in the exact
`r8_16b_petg_qualification_v2` bundle and verify its receiver plus four key
digests against this package's `prior_clearance_qualification` record. Test
0.5, then **0.4 mm per face**. The one-bay
locator, rail, and blank interfaces are authored around 0.4 mm. If 0.4 mm
does not pass cleanly after cooling, stop and correct drying/flow/process;
never scale these parts to force a fit.

## Bambu Studio and PETG settings

1. Open a new `Bambu Lab A1 mini 0.4 nozzle` Textured
   PEI project. Import one
   individual neutral 3MF at **100% scale**. Do not auto-scale, auto-orient,
   repair, or merge it. The combined 3MF is a catalog, **not one build plate**;
   do not slice its layout as-is.
2. Select `SUNLU PETG @BBL A1M 0.4 nozzle` and manually verify PETG only:
   0.20 mm layers, 6 wall
   loops, 5 top and
   3 bottom shell layers,
   25% grid infill,
   250 C first layer,
   245 C later layers,
   60 C bed,
   0.94 flow,
   9 mm^3/s maximum volumetric
   speed, 10-30% normal fan, and
   90% overhang fan.
   Never use a PLA preset.
3. The SUNLU standard-PETG baseline is 50 C (validated lower/upper
   values: 50 C / 50 C) for
   6-8 hours, conditional on the
   received spool label and dryer limit. Record spool lot, exact drying cycle,
   flow calibration, Studio version, plate, and every manual setting. Source:
   https://store.sunlu.com/products/over-6kg-bundle-sale-petg-3d-printer-filament-1-75mm-1kg-roll
4. Preserve the saved orientations: cassette visible front down at 45 degrees;
   both D-frames broad face down; rail broad rear down; blank local XY on the
   bed with its common body down and local negative Z building upward.
5. All five exact saved meshes pass the deposited-layer support gate; the blank
   begins on at least 64 mm^2 of common-body contact. Start with Support OFF and
   inspect Preview. If Studio shows a new island, changes orientation, or wants
   support on cap-bearing, locator, keeper, rail, or latch contact geometry,
   stop and record the mismatch instead of accepting an automatic repair.
6. Start with a 5.0 mm outer brim and
   0.1 mm brim-object gap, then inspect the
   preview for plate-edge, exclusion-zone, support, and brim conflicts. The
   cassette and D-frames reserve an additional
   2 mm per bed edge. Do not reduce
   the reserve or scale a part to make a warning disappear.

## Safe service order

Install: hold the right keeper deflected; lower the cassette through its full
2.0 mm clear approach; seat it; release the keeper; mount the **empty** rail
through its approach and 4.0 mm drop; then install the blank through its entry,
8.0 mm drop, and front-release latch.

Remove in reverse: release/lift/remove the blank first; lift/remove the empty
rail second; hold the keeper deflected; then lift the cassette 2.0 mm and
remove it. Never pull the rail outward while it is loaded or before its service
lift. Never force the cassette past a seated keeper.

## Required one-bay physical tests

- Inspect all five cooled PETG parts for warp, layer separation, poor support
  interfaces, cracks, whitening, and dimension drift.
- Verify both locator fits, full end-land/cap bearing, no rocking, 0.35 mm seam
  intent, keeper contact, and non-destructive release.
- Cycle cassette installation/removal, keeper release/retention, blank latch,
  and empty-rail service in the safe order; record cycle count and damage.
- Stop on binding, permanent set, cracking, whitening, lost latch engagement,
  or bearing gaps. Do not sand load/contact features into an unrecorded fit.
- Thermal, creep, proof-load, and destructive protocols remain separate future
  gates. This coupon cannot establish an installed shelf load rating.

All printed parts are PETG. Any later wall installation still requires verified
framing/blocking and an approved metal structural screw/washer schedule. Printed
or hollow-wall anchors are not authorized in the primary load path.
