# Story Corner Mini — physical proof load protocol

**Purpose:** Convert the ANALYSIS-ONLY provisional load from [LOAD_ANALYSIS.md](LOAD_ANALYSIS.md) into an evidence-backed rated load entry in [SAFETY.md](../SAFETY.md). Until this test **passes and is recorded below**, the official rated load remains **0 lb (development only)**.

---

## Prerequisites

- [ ] Brackets and deck tiles printed per [PRINT_MINI.md](../PRINT_MINI.md) and [`generated/mini/validation.json`](../generated/mini/validation.json) bed-fit checks
- [ ] **SUNLU PETG**, Bambu Lab A1 mini, **0.4 mm** nozzle, **Textured PEI**, process preset **0.20mm Story Corner R12 Durable Strength @BBL A1M** (or equivalent locked profile documented here)
- [ ] Bracket saved orientation: wall strap on build plate, arm length in **+Y** (layers along shelf depth)
- [ ] Deck tiles printed **flat** (8 mm in Z)
- [ ] Two **GRK RSS 1/4 × 3-1/2 in** (or equivalent) with flat washers; **verified 2×4 studs** at **17.0** and **32.5 in** from inside corner
- [ ] Read [SAFETY.md](../SAFETY.md) — no climbing, no hollow-wall anchors, stop on any distress

Record slicer preset revision / filament lot here before testing: ____________________

---

## Proof load magnitude

Let **P** = `provisional_contents_load_lb_analysis_only` from:

```bash
PYTHON_BIN=.venv/bin/python scripts/mini_load_analysis.py
```

**Proof load (contents equivalent):** **2 × P** (lb), evenly distributed on the deck, sustained **24 hours**.

Add printed part self-weight (~0.8 kg / 1.8 lb) as part of the installed assembly; the proof **2×P** target applies to **contents ballast**, not double-counting dead weight unless you explicitly document combined loading.

---

## Setup

1. Mount both brackets to verified studs; confirm 7 mm bores clear, washers seat without cracking PETG, screws driven per GRK guidance with sensible pilot if used.
2. Dry-fit then load deck tiles on bracket arms; verify interlocks engaged along the 15.5 in span.
3. Mark unloaded front-edge height at deck center and both bracket stations (tape marker or dial indicator).
4. Prepare known ballast (water jugs on a plywood pad, sandbags, or calibrated weights). Estimate **center of mass** over the deck, spread to approximate **even distribution** (no single-point stack at the front lip).
5. Clear the area below the shelf; keep people out of the fall zone during loading.

---

## Loading procedure

1. Add ballast in **~1 lb** steps until reaching **P**; pause **10 min**; inspect brackets, bores, wall, and deck.
2. Increase to **2×P**; start the **24 h** clock.
3. At **1 h**, **6 h**, and **24 h**, record deflection marks, photos, and notes.
4. Do not bump, lean on, or reload during the hold except to replace slipped ballast (document if this occurs).

---

## Pass / fail criteria

### Pass (all required)

- Holds **2×P** for **24 h** without failure
- Front-edge deflection **≤ 3 mm** increase vs unloaded at center
- No new cracks, whitening, or creaking in PETG
- No screw loosening, washer pull-through, or stud pull-out
- No tile disengagement or bracket arm rotation visible to the eye
- Wall finish intact (cosmetic cracking may still fail if strap moves)

### Fail (any one)

- Sudden slip, drop, or fastener withdrawal
- Deflection **> 3 mm** permanent at center after unload
- Visible crack or bracket arm separation at root
- Any doubt about stud engagement → treat as fail, unload, and reassess

---

## Results log (fill in after test)

| Field | Value |
|---|---|
| Date / location | |
| `P` from analysis (lb) | |
| Proof load 2×P (lb) | |
| Ballast description | |
| Ambient temp (°C) | |
| Preset / filament lot | |
| Max center deflection (mm) | |
| **PASS / FAIL** | |
| Tester signature | |

**If PASS:** Jeff may update [SAFETY.md](../SAFETY.md) rated load to **P** (not 2×P) with date and reference to this log.

**If FAIL:** Rated load stays **0 lb**; do not raise the analysis provisional number without geometry or process changes and a new analysis run.

---

## Optional follow-up (recommended, not required for first rating)

- One-week creep check at **P** (not 2×P)
- Front-edge point load trial at **0.5×P** for 1 h (document separately; not a rating input unless protocol extended)
