# Story Corner Mini — conservative load analysis (ANALYSIS-ONLY)

**Status:** PROVISIONAL / ANALYSIS-ONLY. This document does **not** establish a safe-working load. The official rated load in [SAFETY.md](../SAFETY.md) remains **0 lb (development only)** until a passing physical proof load recorded in [LOAD_TEST.md](LOAD_TEST.md).

**Scope:** Single stud-bay, all-PETG mini ([`config.mini.json`](../config.mini.json), meshes in [`generated/mini/`](../generated/mini/)). Two printed brackets on verified studs at 17.0 and 32.5 in; deck spans **15.5 in** (393.7 mm) between bracket arms.

**Executable model:** [`scripts/mini_load_analysis.py`](../scripts/mini_load_analysis.py) — unit-tested in [`tests/test_mini_load_analysis.py`](../tests/test_mini_load_analysis.py).

---

## Geometry inputs (from repo CAD / config)

| Item | Source | Value |
|---|---|---|
| Deck clear span | `closet.deck_clear_span_in` | 15.5 in → 393.7 mm |
| Shelf depth | `closet.shelf_depth_in` | 6.0 in → 152.4 mm |
| Deck tile thickness | `structural_mini.deck_tile_thickness_mm` | 8.0 mm |
| Deck depth (two tile rows) | `generated/mini/validation.json` `deck_layout.deck_depth_mm` | 152.4 mm |
| Bracket wall strap | `structural_mini` | 72 × 16 × 48 mm (W × through-wall × drop) |
| Bracket shelf arm | `structural_mini` | 152.4 mm long × 12 × 12 mm |
| Brackets | `stud_mounting.bracket_quantity` | 2 |
| Screws | GRK RSS 1/4 × 3-1/2 in candidate | 2 per bracket (geometric clearance only) |
| Bracket print orientation | `bracket_print_arm_layers_along_depth` | Arm built in **+Y** so layers stack **along shelf depth** (see [PRINT_MINI.md](../PRINT_MINI.md)) |

Cross-sections for bending are taken directly from these parameters (rectangular sections; deck modeled as 8 mm × 152.4 mm between supports).

---

## Material properties and safety factors

### Published PETG references (before project factors)

| Property | Value used | Typical source |
|---|---:|---|
| Molded tensile strength | 50 MPa | ASTM D638 / ISO 527 — generic PETG datasheet range (e.g. 48–53 MPa) |
| FDM **Z** (interlayer) tensile | 15 MPa | Additive manufacturing literature on PETG anisotropy (~25–40% of in-plane strength; see e.g. *Materials* 2020, 13(24), 5738 — open-access PETG FDM characterization) |
| FDM Young’s modulus (in-plane) | 1800 MPa | Same class of FDM PETG studies / manufacturer process guides (order-of-magnitude) |

SUNLU PETG is the project filament ([`config.mini.json`](../config.mini.json)); the analysis uses **generic PETG literature values**, not unverified SUNLU lab certificates.

### Layer adhesion safety factor **4.0**

Interlayer strength is sensitive to nozzle temperature, cooling, moisture, surface prep, and operator variance. A re-entrant bracket root also concentrates stress across layer boundaries. Following common conservative FDM practice (treat Z strength as a fraction of bulk and apply an additional factor), the script uses:

- **Allowable interlayer stress** = 15 MPa ÷ **4.0** = **3.75 MPa**

This factor applies to deck bottom-fiber tension (tiles printed flat, 8 mm in Z) and to legacy bracket orientations where arm bending peels Z layers.

### Bulk in-plane factor **3.0**

Allowable bulk bending ≈ 50 MPa ÷ 3.0 ≈ **16.7 MPa** for arm fiber bending when layers run along the arm.

### Connection factors

- Wood screw withdrawal: NDS-style coefficient **138 lb/in²** (AWC NDS Supplement Table 12D, conservative side), divided by **2.5**
- PETG washer bearing: bulk allowable ÷ **3.0** on a **20 mm** OD washer land

GRK RSS values in ESR-2442 apply to **wood**, not to a PETG washer stack — withdrawal here is a **stud-side lower bound**, not an approved connection.

---

## Failure modes checked

1. **Bracket arm cantilever (bulk bending)** — Each bracket carries half the total contents load; uniform load on arm length 152.4 mm; fixed at strap.
2. **Bracket root** — Interlayer peel for old orientation; with arm layers along depth, bulk bending with **1.5×** stress concentration at the strap junction.
3. **Deck span** — Simply supported uniform load over 393.7 mm; **interlayer** tension on bottom fiber (8 mm vertical thickness).
4. **Screw withdrawal** — Two screws per bracket into side-grain stud (conservative penetration after PETG strap).
5. **PETG washer bearing** — Compressible crushing under screw head.

Printed self-weight (~0.8 kg from geometry) is **not** included in the provisional contents figure; it adds to installed stress.

---

## Provisional result (recompute with script)

Run:

```bash
PYTHON_BIN=.venv/bin/python scripts/mini_load_analysis.py
```

The script prints JSON including:

- `provisional_contents_load_lb_analysis_only` — **minimum** of the modes above
- `governing_failure_mode`
- `official_rated_load_lb` — always **0**

After the bracket print-orientation fix (arm layers along shelf depth), **bracket root stress concentration** typically governs before deck interlayer or stud withdrawal in the conservative model. Recompute with the script — expect on the order of **~19 lb** contents (ANALYSIS-ONLY) with the current `config.mini.json` geometry and safety factors.

---

## What this analysis does not cover

- Creep at closet temperature over months (PETG sustained deflection)
- Impact, point loads, climbing, seismic, or dynamic loads
- Hollow wall, mis-located studs, or degraded lumber
- Washer flex, screw shear through PETG, or GRK pull-through of the strap
- Tile interlock slip or stress concentrations at tongues
- Any claim of code compliance or product certification

Physical proof at **2×** the provisional analysis load for **24 h** on a real stud bay is defined in [LOAD_TEST.md](LOAD_TEST.md). Only after Jeff records a **pass** may the rated load in [SAFETY.md](../SAFETY.md) be updated.
