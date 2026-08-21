# Print the Shelf — All-PETG with Structural Roman Arches

**This is the real deal.** Structural Roman arch brackets that actually carry load, plus ribbed deck segments. 100% PETG. No plywood, no steel. Download the STLs, slice, print, install.

## The Files (Ready to Print)

All files are in [`generated/all_petg_shelf/`](generated/all_petg_shelf/):

| File | What It Is | Dimensions | Quantity |
|------|------------|------------|----------|
| `arch_bracket.stl` | Structural Roman arch wall bracket | 152 × 32 × 160 mm | **3** |
| `deck_segment.stl` | Ribbed deck segment | 160 × 152 × 24 mm | **9** |
| `end_cap.stl` | End cap for exposed deck ends | 6 × 152 × 24 mm | **2** |

**Total: 14 parts**

## What You're Building

```
        ┌─────────────────────────────────────────────────────────┐
        │  DECK SEGMENTS (9 pieces, 160mm each = 1440mm total)    │
        └─────────────────────────────────────────────────────────┘
              │              │              │
           ┌──┴──┐        ┌──┴──┐        ┌──┴──┐
           │     │        │     │        │     │
           │ ╭─╮ │        │ ╭─╮ │        │ ╭─╮ │    ← Roman arch
           │ │ │ │        │ │ │ │        │ │ │ │      brackets (3)
           │ ╰─╯ │        │ ╰─╯ │        │ ╰─╯ │
           │  │  │        │  │  │        │  │  │
           │  │  │        │  │  │        │  │  │
        ───┴──┴──┴────────┴──┴──┴────────┴──┴──┴───  WALL
           17.0"          32.5"          48.5"      (stud positions)
```

The Roman arch shape transfers shelf load through **compression** into the wall — the way arches are supposed to work.

## Specifications

| Spec | Value |
|------|-------|
| Wall length | 61.5 in (1562 mm) |
| Shelf depth | 6 in (152 mm) |
| Deck coverage | ~56.7 in (1440 mm) — 9 segments |
| Bracket positions | 17.0, 32.5, 48.5 in from inside corner (at studs) |
| Material | SUNLU black PETG |
| Printer | Bambu A1 mini (180mm build volume) |

## Print Settings (PETG on A1 mini)

| Setting | Value | Why |
|---------|-------|-----|
| Layer height | 0.2 mm | Balance of speed and strength |
| Wall loops | 4–5 | Thick walls for structural parts |
| Top/bottom layers | 5 | Solid surfaces |
| Infill | 30–40% gyroid | Good strength-to-weight |
| Nozzle temp | 240°C | PETG needs heat |
| Bed temp | 70°C | Textured PEI plate |
| Cooling | 50–70% | Enough to prevent droop |
| Supports | See below | |

### Print Orientations

**Arch Bracket:** Print on its side with the arch opening facing UP. This puts print layers perpendicular to the main load direction (compression), not in the weak peel direction.

```
Print plate
─────────────────────
    ┌───────────┐
    │   ╭───╮   │  ← Arch opening faces UP
    │   │   │   │
    │   ╰───╯   │
    └───────────┘
```

Supports: YES — needed inside the arch opening and for the screw counterbores.

**Deck Segment:** Print with the TOP face DOWN (touching the plate). This gives you a smooth usable top surface.

```
Print plate
─────────────────────
    ┌───────────┐  ← Top surface (smooth)
    │═══════════│  ← Ribs print upward
    └───────────┘
```

Supports: NO — the box structure is self-supporting.

**End Cap:** Print flat, any orientation.

## Print Time Estimates

| Part | Time Each | Quantity | Total |
|------|-----------|----------|-------|
| Arch bracket | ~6 hours | 3 | 18 hours |
| Deck segment | ~4 hours | 9 | 36 hours |
| End cap | ~1 hour | 2 | 2 hours |
| **TOTAL** | | **14** | **~56 hours** |

PETG needed: **~2.5 kg** (buy 3 kg to be safe)

## Hardware

| Item | Quantity | Notes |
|------|----------|-------|
| #10 × 2.5" wood screws | 9 | 3 per bracket, into studs |
| 1/4" flat washers | 9 | Between screw head and PETG |
| M4 × 20mm bolts | 36 | 4 per deck-bracket joint |
| M4 nuts | 36 | Or use threaded inserts |

**Where to buy:**
- Screws/washers: Home Depot, Lowes, any hardware store
- M4 bolts/nuts: Amazon, Home Depot hardware aisle, McMaster-Carr

## Assembly

### Step 1: Mount the Arch Brackets

1. Mark stud centers on wall: **17.0", 32.5", 48.5"** from inside corner
2. Mark shelf height (e.g., 68" from floor to top of bracket)
3. Hold bracket against wall, level it
4. Through the 3 screw holes (with counterbores), drill 7/64" pilot holes into stud
5. Drive #10 screws with washers — **snug, not over-torqued** (PETG cracks if you crank on it)
6. Repeat for all 3 brackets

The brackets have:
- 3 screw holes at 30mm, 80mm, 130mm from top
- 6mm clearance holes for #10 or 1/4" screws
- 14mm counterbores for washer seating

### Step 2: Install Deck Segments

1. Set first deck segment on bracket tops
2. Align bolt holes in deck with holes in bracket top plates
3. Insert M4 bolts from above, secure with nuts below
4. Continue with remaining segments, butting them together
5. Install end caps at the exposed ends

Each deck segment bolts to the brackets below it with 4 bolts (2 at each end where it meets a bracket).

### Step 3: Done

That's it. No glue, no complex joinery. Bolts and screws.

## Load Rating

**Honest answer: 30–50 lb evenly distributed for light/medium duty.**

This is not a 120 lb industrial shelf. PETG creeps under sustained load. But for closet storage — folded clothes, linens, light bins, hats — it will work.

### Safe Uses
- Folded clothes, towels, linens
- Light plastic bins (not full of books)
- Hats, soft goods, small items
- Seasonal storage

### Not Recommended
- Heavy bins of books or tools
- Dense items concentrated at one spot
- Anything you'd be sad about if it fell

### Why the Arches Help

Roman arches work through compression. The curved shape directs load down and into the wall, rather than creating a bending moment that tries to peel the bracket off. This is why arches have been used in architecture for thousands of years.

The thick arch ribs (12mm) and multiple ribs per bracket (3) provide redundancy. The top plate is 16mm thick where the deck sits.

## Regenerating the Parts

If you need to modify dimensions, the generator is at:

```bash
python3 scripts/generate_all_petg_shelf.py
```

Output goes to `generated/all_petg_shelf/`. Edit the constants at the top of the script to change dimensions.

## What This Design Does NOT Include

- Plywood deck (it's all PETG)
- Steel angle stiffener (it's all PETG)
- KV standards and brackets (the arches ARE the brackets)
- The 102-piece Palatine ornamental tile set (this is structural, not decorative)
- The short/return wall (that's a separate project)

## Troubleshooting

**Brackets don't sit flat against wall:**
Check for drywall bumps or paint drips. Sand/scrape if needed.

**Deck segments don't align:**
Print tolerances vary. You may need to file bolt holes slightly larger.

**Screws won't bite:**
You might have missed the stud. Use a stud finder to verify, or drill a small test hole.

**Parts warping during print:**
PETG warps if the bed isn't hot enough or there's a draft. Use 70°C bed, enclosure if possible, and make sure your first layer is well-adhered.

**Creaking/movement under load:**
Tighten bolts. If still moving, add a washer between deck segments at joints.

---

*This is a real, printable shelf. Download the STLs, slice them, print them, bolt them together, screw them to your wall. Go.*
