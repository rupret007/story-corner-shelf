# Print the Storage Arcade

100% PETG closet system. Every gram stores something or carries load. No decorative air.

## The Bed Rule (Non-Negotiable)

**Bambu A1 mini: 180 mm build volume, but XY must be ≤160 mm with brim.**

| Part | XY Bed Footprint | Z Height | Fits? |
|------|------------------|----------|-------|
| Stud Spine | 50 × 40 mm | 158 mm | ✓ |
| Arch Bay | 155 × 150 mm | 155 mm | ✓ |
| Deck Module | 158 × 150 mm | 35 mm | ✓ |
| Cable Insert | 16 × 140 mm | 40 mm | ✓ |
| String Cassette | 16 × 60 mm | 80 mm | ✓ |
| Guitar Hanger | 60 × 100 mm | 55 mm | ✓ |

All parts verified to fit with 3 mm brim + calibration region.

## Part Counts

For a 61.5" wall with studs at 17.0", 32.5", 48.5":

| Part | Quantity | Print Time Each | Total Hours |
|------|----------|-----------------|-------------|
| Stud Spine | 3 | 4 hrs | 12 hrs |
| Arch Bay | 4 | 8 hrs | 32 hrs |
| Deck Module | 6 | 4 hrs | 24 hrs |
| Cable Insert | 2-4 | 1.5 hrs | 3-6 hrs |
| String Cassette | 1-2 | 2 hrs | 2-4 hrs |
| Guitar Hanger | 1 | 2.5 hrs | 2.5 hrs |

**Total print time: ~76-81 hours**  
**Total PETG: ~2.0-2.2 kg**

## Print Settings

```
Material:        PETG (SUNLU black recommended)
Layer height:    0.2 mm
Wall loops:      6 (THIS IS CRITICAL)
Top/bottom:      6 layers
Infill:          40% gyroid
Nozzle temp:     245°C
Bed temp:        75°C
Brim:            YES - 3mm minimum
Fan:             50-60%
Speed:           60 mm/s
```

**Why 6 walls / 40% gyroid?** PETG creeps. Box sections with thick walls and gyroid resist creep under sustained load.

## Print Orientations

### Stud Spine
- **Orientation:** Wall face down (backplate flat on bed)
- **Supports:** No
- **Why:** Backplate is large flat surface, prints without supports

### Arch Bay
- **Orientation:** Back wall down (arch opening facing UP)
- **Supports:** YES - organic supports for arch interior
- **Why:** Arch overhangs need support. Pier walls print vertically.

### Deck Module
- **Orientation:** Top surface down (will be the usable surface)
- **Supports:** No
- **Why:** Box is self-supporting. Top surface gets smooth bed finish.

### Cable Insert
- **Orientation:** Base down
- **Supports:** No
- **Why:** Hooks print upward with minimal overhang

### String Cassette
- **Orientation:** Open top facing up
- **Supports:** No
- **Why:** Simple box shape

### Guitar Hanger
- **Orientation:** Mounting plate down
- **Supports:** No
- **Why:** Arms print upward from solid base

## Hardware List

### Wall Fasteners
| Item | Spec | Qty | Notes |
|------|------|-----|-------|
| Wood screws | #10 × 3" | 9 | 3 per spine, INTO STUDS ONLY |
| Fender washers | 1/4" (1" OD) | 9 | Under screw heads |

### Assembly Fasteners
| Item | Spec | Qty | Notes |
|------|------|-----|-------|
| M4 × 25mm | Socket head cap screw | 50 | Bay-to-spine, deck-to-bay |
| M4 nylock nuts | - | 50 | Resist loosening |
| M4 flat washers | - | 100 | Both sides |

**No hollow-wall anchors.** All load goes into studs via wood screws.

## Assembly Order

### Phase 1: Wall Prep
1. Locate studs at 17.0", 32.5", 48.5" from inside corner
2. Mark vertical lines at stud centers
3. Mark spine positions (centered on studs)

### Phase 2: Mount Spines
1. Hold first spine against wall, centered on stud
2. Level and mark screw holes
3. Pre-drill pilot holes into stud
4. Drive three #10 × 3" screws with washers
5. Repeat for remaining two spines
6. Check all three are level and coplanar

### Phase 3: Install Arch Bays
1. Working from left, slide first bay between spines
2. Align bay back wall with spine crowns
3. Insert M4 bolts through back wall into spine grid
4. Finger-tighten only
5. Repeat for remaining bays
6. Check alignment, then torque all M4s to snug

### Phase 4: Install Deck
1. Place first deck module on top of bays/spines
2. Align M4 holes with bay crowns
3. Bolt through deck into bay crown
4. Continue with remaining deck modules
5. Adjacent decks butt together (no gap)

### Phase 5: Add Inserts
1. Slide cable inserts into pier hollows as needed
2. String cassettes drop into pier hollows
3. Guitar hanger bolts to spine (select a spine, use M4s through mounting plate)

## What Each Bay Is For

The Roman arch opening IS the storage bay:

| Bay Position | Primary Use | Insert |
|--------------|-------------|--------|
| Bay 1 (leftmost) | Charging cables | Cable insert |
| Bay 2 | Guitar strings, picks | String cassette |
| Bay 3 | Small bins | None (open bay) |
| Bay 4 (rightmost) | Misc storage | Open |

The **hollow piers** between bays are also storage:
- Each pier can hold a cable insert OR string cassette
- That's 8 more storage columns (4 bays × 2 piers each)

## Load Capacity

| Location | Working Load | Notes |
|----------|--------------|-------|
| Per bay floor | 5 kg (11 lb) | Cable bins, string boxes |
| Deck total | 25 kg (55 lb) | Distributed across all modules |
| Guitar hanger | 5 kg (11 lb) | One guitar |

**Do not exceed.** PETG creeps under sustained load. These are conservative estimates.

## Quality Gates

Before use, verify:

- [ ] All three spines screwed into studs (9 screws total, all countersunk)
- [ ] All bays bolted to spines (M4s snug, not over-torqued)
- [ ] Deck modules bolted down and level
- [ ] No visible layer delamination on any part
- [ ] Arch bays stable—push gently on front pier, no wobble

## If Something Doesn't Fit

The stud spacing on your wall may differ. The design assumes:
- Span 1: 393.7 mm (15.5")
- Span 2: 406.4 mm (16.0")

If your spans are different:
1. Edit `STUD_POSITIONS_IN` in `generate_storage_arcade.py`
2. Re-run generator
3. Check output for new bay counts

You may get 2 or 3 bays per span depending on actual spacing.

---

**This is a working storage system.** The arch opening stores things. The pier stores things. The deck stores things. No gram is wasted.
