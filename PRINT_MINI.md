# Print order — Story Corner Mini (single stud bay)

Model-only SUNLU PETG files live under [`generated/mini/`](generated/mini/). They contain **no embedded G-code**. Use the R12 A1 mini process preset from [`profiles/`](profiles/) or [`generated/final_release_r12/profiles/`](generated/final_release_r12/profiles/) unless you have a dedicated mini tune.

## Print sequence

1. **Two × `MINI_PETG_StudBracket`** — print first. Saved orientation places the wall strap on the build plate with the shelf arm extending in **+Y** (layers stack along shelf depth for cantilever bending). Confirm both 7 mm bores are clean and that a flat washer seats on the outer face without cracking PETG.
2. **Deck tiles** (six unique prints, eight total parts) — batch by type after brackets pass visual inspection:
   - 2 × `MINI_PETG_DeckTile_End_Left`
   - 2 × `MINI_PETG_DeckTile_Center`
   - 2 × `MINI_PETG_DeckTile_End_Right`

Orient each deck tile **flat** (8 mm thickness in Z). Preserve saved orientation from the STL/3MF.

## Part count

| Part | Qty |
|---|---:|
| `MINI_PETG_StudBracket` | 2 |
| `MINI_PETG_DeckTile_End_Left` | 2 |
| `MINI_PETG_DeckTile_Center` | 2 |
| `MINI_PETG_DeckTile_End_Right` | 2 |
| **Total printed objects** | **8** |

## Bed-fit envelope (saved orientation)

Effective check uses the A1 mini 180 mm cube minus a **5 mm per-side margin** (170 mm). Dimensions come from [`generated/mini/validation.json`](generated/mini/validation.json).

| Part | Size (mm, X×Y×Z) | Fits 170 mm |
|---|---|---|
| Stud bracket | 72.0 × 168.4 × 48.0 | yes |
| Deck tile center | 154.5 × 75.9 × 8.0 | yes |
| Deck tile end (left / right) | 123.0 × 75.9 × 8.0 / 120.4 × 75.9 × 8.0 | yes |

## Fasteners

- **Stud brackets:** geometric candidate **GRK RSS 1/4 in × 3-1/2 in** (7 mm printed bore clears a 1/4 in-class shank; same family as `development/r9/one_bay_geometry.py`). Two screws per bracket into **verified wood studs** at 17.0 and 32.5 in from the inside corner. This is compatibility geometry only—not an approved connection.
- **Deck:** dry-fit interlocking tiles on the bracket arms; no separate screw spec in this mini set (tiles are not retained with the rear-curb pan-head screws used on R12 finish).

## Filament estimates (geometry only)

| Source | Packaged PETG mass |
|---|---:|
| R12 full set — `generated/validation.json` `estimated_packaged_petg_mass_kg` | 3.12 kg |
| Mini — `generated/mini/validation.json` `estimated_packaged_petg_mass_kg` | 0.801 kg |

Print time: **unverified** — the repository does not store slicer time metadata for mini or R12.

## Load and safety (read with [SAFETY.md](SAFETY.md))

This mini is an **all-PETG, untested prototype** for one 15.5 in stud bay at ~6 in depth. It is **outside** the R12 hybrid load path (plywood, steel angle, KV standards/brackets). [SAFETY.md](SAFETY.md) states that a structurally all-PETG shelf is outside the main project and inherits **no** R12 selection targets or ratings.

- **Rated load:** 0 lb (development only).
- **Provisional analysis (not a rating):** [docs/LOAD_ANALYSIS.md](docs/LOAD_ANALYSIS.md); proof protocol [docs/LOAD_TEST.md](docs/LOAD_TEST.md).
- **Design-selection hint:** 15 lb evenly distributed contents — not a safe-working load.
- Verify stud location, screw engagement, creep, and deflection with gradual test weights before normal use; stop for movement, cracking, or wall damage.
- Do not climb on the shelf, mount it without confirmed studs, or treat printed plastic as code-approved structure.
