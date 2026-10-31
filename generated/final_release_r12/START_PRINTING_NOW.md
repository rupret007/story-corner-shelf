# Start printing now — qualification first

Use the A1 Mini 0.4 mm nozzle, Textured PEI Plate, SUNLU clear PETG, the
supplied R12 strength profile in `profiles/`, saved orientation, and 100%
scale. Confirm six walls, five top/bottom shells, 60% gyroid, supports off,
3 mm outer brim, 240 C nozzle, 70 C bed, 20 mm/s first layer, and calibrated
flow. Watch the first layer on every job before leaving.

Print these four qualification objects in order before any production tile:

1. `models/MODEL_ONLY_PRINT_FIRST_R12_AdhesionCornerCoupon.3mf`
2. `models/MODEL_ONLY_PRINT_FIRST_FasciaFitCoupon.3mf` (fit with actual plywood,
   steel angle, and a printed 2.4 mm top-tile sample; nominal opening 46.656 mm)
3. `models/MODEL_ONLY_PRINT_FIRST_PalatineDetailCoupon.3mf` (face-up)
4. `models/MODEL_ONLY_PRINT_FIRST_CornerFitGauge.3mf`

After all four pass per [SAFETY.md](../../SAFETY.md) and
[PRINT_ME_FIRST.md](../../PRINT_ME_FIRST.md), open
`models/MODEL_ONLY_PETG_TopTile_Center_6inPitch.3mf`. It is a 151.8 x 101.3 x
2.4 mm installed top-finish tile (not a coupon). The measured long wall needs
14 identical copies. Let each tile cool on the plate before removal.

Generated groin-vault clearance to the nearest through support at
6.0 in is 25.662 mm (minimum 10 mm).

Do not print fitted fascia, parametric ends, or corner pieces yet. Those remain
on hold until installed shelf-back offsets and the full-size corner geometry are
verified. Do not cut or mount the shelf until end blocking is installed at 6.0
and 60.5 in from the inside corner.
