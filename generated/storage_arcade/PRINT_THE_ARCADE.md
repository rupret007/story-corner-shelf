# Print the Storage Arcade — Two-Level Edition

100% PETG closet system. Two stacked shelf levels on the long wall. Every gram stores or carries.

## Height Assumption (UNVERIFIED)

**Outlet-top to ceiling: 43.5 in (1104.9 mm)**

| Value | Amount | Note |
|-------|--------|------|
| Outlet to ceiling | 43.5 in | **USER-REPORTED, NOT FIELD-VERIFIED** |
| Ceiling clearance | 25 mm | Gap from top deck to ceiling |
| Outlet clearance | 50 mm | Gap from lower bay bottom to outlet top |
| Inter-level gap | 20 mm | Between upper and lower arcade |
| Available for shelves | ~1030 mm | Two levels fit in this band |

**FIELD-MEASURE BEFORE PRINTING SPINES.** If the actual measurement differs significantly, adjust the spine stacking or contact before proceeding.

---

## Wall Status

### Long Wall — ACTIVE
- Length: 61.5 in
- Studs: 17.0, 32.5, 48.5 in from inside corner
- **Two stacked shelf levels** above the electric box

### Short Wall — ON HOLD
- Length: ~36 in (nominal, **NEEDS MEASUREMENT**)
- Same bay/spine system will turn the corner
- **Do not print until field-measured**

---

## The Bed Rule (Non-Negotiable)

**Bambu A1 mini: 180 mm build volume, XY ≤160 mm with brim.**

| Part | XY Footprint | Z Height | Fits? |
|------|--------------|----------|-------|
| Stud Spine | 50 × 40 mm | 158 mm | ✓ |
| Arch Bay | 155 × 150 mm | 155 mm | ✓ |
| Deck Module | 158 × 150 mm | 35 mm | ✓ |
| Cable Insert | 16 × 140 mm | 40 mm | ✓ |
| String Cassette | 16 × 60 mm | 80 mm | ✓ |
| Guitar Hanger | 60 × 100 mm | 55 mm | ✓ |

All parts verified to fit with 3 mm brim + calibration region.

---

## Part Counts — Two Levels on Long Wall

| Part | Per Level | × 2 Levels | Total | Notes |
|------|-----------|------------|-------|-------|
| Stud Spine | 3 | × 2 | **6** | 2 per stud, stacked |
| Arch Bay | 4 | × 2 | **8** | 4 bays span the wall |
| Deck Module | 6 | × 2 | **12** | Top surface per level |
| Cable Insert | — | — | 2-4 | As needed |
| String Cassette | — | — | 1-2 | As needed |
| Guitar Hanger | — | — | **1** | Bolts to any spine |

### Print Time Estimate

| Part | Qty | Hours Each | Total Hours |
|------|-----|------------|-------------|
| Stud Spine | 6 | 4 | 24 |
| Arch Bay | 8 | 8 | 64 |
| Deck Module | 12 | 4 | 48 |
| Inserts | ~5 | ~2 | 10 |
| Guitar Hanger | 1 | 2.5 | 2.5 |
| **TOTAL** | | | **~150 hrs** |

**PETG needed: ~4-5 kg**

---

## Print Settings

```
Material:        PETG (SUNLU black recommended)
Layer height:    0.2 mm
Wall loops:      6 (CRITICAL for PETG creep resistance)
Top/bottom:      6 layers
Infill:          40% gyroid
Nozzle temp:     245°C
Bed temp:        75°C
Brim:            YES - 3mm minimum
Fan:             50-60%
Speed:           60 mm/s
```

---

## Print Orientations

### Stud Spine
- **Orientation:** Wall face down (backplate flat on bed)
- **Supports:** No

### Arch Bay
- **Orientation:** Back wall down (arch opening facing UP)
- **Supports:** YES - organic supports for arch interior

### Deck Module
- **Orientation:** Top surface down (smooth bed finish)
- **Supports:** No

### Cable Insert / String Cassette / Guitar Hanger
- **Orientation:** Base/mounting plate down
- **Supports:** No

---

## Hardware List (Two-Level System)

### Wall Fasteners
| Item | Spec | Qty | Notes |
|------|------|-----|-------|
| Wood screws | #10 × 3" | 18 | 3 per spine × 6 spines |
| Fender washers | 1/4" (1" OD) | 18 | Under screw heads |

### Assembly Fasteners
| Item | Spec | Qty | Notes |
|------|------|-----|-------|
| M4 × 25mm | Socket head cap screw | 100 | Bay-to-spine, deck-to-bay |
| M4 nylock nuts | — | 100 | Resist loosening |
| M4 flat washers | — | 200 | Both sides |

**No hollow-wall anchors.** All load goes into studs.

---

## Assembly Order

### Phase 1: Verify Height
1. **MEASURE** outlet-top to ceiling
2. Compare to 43.5 in assumption
3. If significantly different, recalculate level positions

### Phase 2: Mount Lower Spine Set
1. Mark stud locations (17.0, 32.5, 48.5 in from corner)
2. Position lower spine at outlet clearance height (50 mm above outlet top)
3. Level and pre-drill pilot holes
4. Drive 3 × #10 screws per spine with washers
5. Repeat for all 3 studs

### Phase 3: Install Lower Level
1. Attach arch bays (4 total) to lower spines via M4 bolts
2. Bays bolt through back wall to spine M4 grid
3. Install deck modules (6 total) on top of lower arcade
4. Check level before final torque

### Phase 4: Mount Upper Spine Set
1. Stack upper spine above lower spine (20 mm gap between arcade levels)
2. Upper spine mounts to same stud, higher position
3. Drive 3 × #10 screws per spine
4. Repeat for all 3 studs

### Phase 5: Install Upper Level
1. Attach arch bays (4 total) to upper spines
2. Install deck modules (6 total) on top of upper arcade
3. Check level and alignment with lower level

### Phase 6: Add Inserts & Hanger
1. Slide cable inserts into pier hollows as needed
2. Drop string cassettes into pier hollows
3. Bolt guitar hanger to a lower spine (guitar hangs in room below lower arcade)

---

## Level Configuration

```
CEILING
  ↑ 25mm clearance
┌─────────────────────────────────────────────────────┐
│           UPPER DECK (6 modules)                    │
├─────────────────────────────────────────────────────┤
│   ╭───╮   ╭───╮   ╭───╮   ╭───╮                     │
│   │   │   │   │   │   │   │   │   UPPER BAYS (4)   │
│   │   │   │   │   │   │   │   │                     │
│   ╰───╯   ╰───╯   ╰───╯   ╰───╯                     │
└─────────────────────────────────────────────────────┘
  ↑ 20mm inter-level gap
┌─────────────────────────────────────────────────────┐
│           LOWER DECK (6 modules)                    │
├─────────────────────────────────────────────────────┤
│   ╭───╮   ╭───╮   ╭───╮   ╭───╮                     │
│   │   │   │   │   │   │   │   │   LOWER BAYS (4)   │
│   │   │   │   │   │   │   │   │                     │
│   ╰───╯   ╰───╯   ╰───╯   ╰───╯                     │
└─────────────────────────────────────────────────────┘
  ↑ 50mm clearance
═══════════════════════════════════════════════════════
              ELECTRIC BOX (outlet top)
```

---

## Load Capacity

| Location | Working Load | Notes |
|----------|--------------|-------|
| Per bay floor | 5 kg (11 lb) | Cable bins, string boxes |
| Per deck level | 25 kg (55 lb) | Distributed across modules |
| Two decks total | 50 kg (110 lb) | Combined upper + lower |
| Guitar hanger | 5 kg (11 lb) | One guitar |

**Do not exceed.** PETG creeps under sustained load.

---

## What's Next: Short Wall

The ~36 in return wall uses the same system:
- Same bay modules
- Same spine modules  
- Same deck modules
- Corner connection where walls meet

**Status: ON HOLD until field-measured.**

When ready:
1. Measure actual short wall length
2. Measure stud positions on short wall
3. Calculate bay count for short wall spans
4. Generator can produce corner-turn parts

---

## Quality Gates

Before use, verify:

- [ ] Height measured and matches assumption (±1 in)
- [ ] All 6 spines screwed to studs (18 screws total)
- [ ] Lower level installed and level
- [ ] Upper level installed and level
- [ ] Both levels aligned with each other
- [ ] All M4 joints snug (not over-torqued)
- [ ] No visible layer delamination
- [ ] Guitar hanger secure (push test)

---

**This is a two-level storage system.** Each arch opening stores things. Each pier stores things. Each deck stores things. Sixteen storage bays plus 32 pier columns across two levels.
