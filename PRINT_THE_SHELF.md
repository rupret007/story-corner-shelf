# Print the Shelf — All-PETG Long Wall (61.5 in)

This is the minimum-viable **all-PETG structural shelf** for Jeff's closet long wall. No plywood, no steel angle, no KV standards. Just printed PETG parts screwed into studs.

## What You're Building

One 61.5-inch shelf along the long wall only. The short/return wall is deferred until this works.

| Specification | Value |
|---|---|
| Wall clear length | 61.5 in (1562 mm) |
| Verified studs from corner | 17.0, 32.5, 48.5 in |
| Shelf depth | 6 in (152 mm) — see note below |
| Deck thickness | 30 mm (ribbed box cassette) |
| Material | SUNLU black PETG |
| Printer | Bambu A1 mini (180 mm build cube) |

### Why 6 in depth instead of 8 in?

An 8-inch (203 mm) PETG cantilever from a printed wall bracket will sag under load. PETG creeps. The R9 cassette geometry uses 152.4 mm (6 in) depth because:

1. It fits the A1 mini build plate in one piece
2. Shorter cantilever = less moment at the bracket
3. The existing tested geometry uses this depth

If you absolutely need 8 in depth, you'd need either (a) a second row of brackets at 4 in from the wall, or (b) accepting significant sag. This guide uses 6 in.

## Honest Load Expectation

**Light closet storage only: 20–30 lb evenly distributed.**

This is NOT a 120 lb shelf. PETG creeps under sustained load. The printed brackets are fastened into only three studs. There is no continuous steel stiffener.

Safe uses:
- Folded clothes, linens
- Light boxes, small bins
- Hats, soft goods

Not safe:
- Heavy bins of books
- Dense stored items
- Point loads at the front edge

## The Design

### Support Layout (3 brackets at studs)

```
Wall (inside corner at left)
|                                                              |
0"   6"        17"        32.5"       48.5"       55.5"    61.5"
     [end]     [STUD]     [STUD]      [STUD]      [end]
              bracket    bracket     bracket
```

The three brackets land on the verified studs at 17.0, 32.5, and 48.5 inches. This gives:
- Left overhang: 17.0 - 6.0 = 11.0 in (from first bracket to shelf start at ~6 in)
- Middle span: 32.5 - 17.0 = 15.5 in
- Right span: 48.5 - 32.5 = 16.0 in
- Right overhang: 55.5 - 48.5 = 7.0 in (from last bracket to shelf end at ~55.5 in)

**Important:** The original plan called for blocking at 6.0 and 60.5 in. Without that blocking, the shelf cannot safely extend to those points with only PETG brackets. This design shortens the shelf to fit what the three verified studs can support:

- **Shelf start:** ~6 in from corner (11 in overhang from first bracket — at the limit)
- **Shelf end:** ~55.5 in from corner (7 in overhang from last bracket)
- **Usable shelf length:** ~49.5 in (not the full 61.5 in wall)

To use the full wall length, you MUST install wood blocking at 6.0 and 60.5 in as originally planned, then add two more printed brackets at those locations.

### Parts List (what to print)

All parts from the R9 one-bay geometry, scaled to this wall:

| Part | Quantity | Print Time (est.) | Notes |
|---|---|---|---|
| Wall bracket (compact support) | 3 | ~4 hr each | Prints flat, 32 mm wide |
| Deck cassette segment (160 mm) | 3 | ~6 hr each | Prints top-down |
| End cassette (shorter) | 2 | ~4 hr each | Custom length for ends |
| Rear ledger segment | 3 | ~2 hr each | Joins cassettes at wall |
| Front beam segment | 3 | ~2 hr each | Joins cassettes at front |

**Total: ~14 parts, ~50–60 hours of print time**

### Part Geometry

**Wall Bracket (R9 compact support)**
- 32 mm wide × 152 mm deep × 190 mm tall
- Three 7mm screw holes at 16, 80, 144 mm below shelf
- Fits A1 mini printing on its side
- Uses existing `development/r9/one_bay_geometry.py` → `build_left_compact_support()` / `build_right_compact_support()`

**Deck Cassette**
- 160 mm wide × 152 mm deep × 30 mm tall
- Box construction with 3 internal webs (2.4 mm walls)
- Prints top-face-down (smooth top surface)
- Uses existing `build_shelf_cassette()` from R9

**Ledger and Beam**
- 96 mm long × 16 mm deep × 30 mm tall
- Connect cassettes and provide rear/front stiffening
- Tongue-and-socket fit into brackets

## Print Settings

Use these settings for SUNLU black PETG on A1 mini:

| Setting | Value |
|---|---|
| Layer height | 0.2 mm |
| Wall loops | 4 |
| Top/bottom layers | 5 |
| Infill | 25% gyroid |
| Nozzle temp | 240°C |
| Bed temp | 70°C (textured plate) |
| Speed | 80 mm/s walls, 120 mm/s infill |
| Cooling | 60–80% |
| Supports | OFF for cassettes; Bracket needs support for screw holes |

**Critical:** Dry your PETG before printing. Wet PETG = weak parts. Use a filament dryer or oven at 65°C for 4+ hours.

## Assembly Order

### 1. Mount the brackets

Each bracket has three 7mm holes. Use:
- **Screws:** #10 × 2.5 in wood screws (or GRK RSS 1/4 × 2.5 in if available)
- **Washers:** 1/4 in USS flat washers (≤20 mm OD) between screw head and PETG

Steps:
1. Mark stud centers at 17.0, 32.5, 48.5 in from corner
2. Mark shelf height (e.g., 68 in from floor to top of bracket)
3. Hold bracket to wall, check level
4. Drill pilot holes (7/64 in) through bracket holes into stud
5. Drive screws with washers — **snug, not cranked tight** (PETG can crack)

### 2. Install rear ledgers

The ledger pieces tongue into slots in the bracket backs. Slide them in from above or the side. They do not need separate fasteners if the fit is correct.

### 3. Install front beams

Same as ledgers, but at the front of the brackets. These stiffen the front edge.

### 4. Drop in deck cassettes

The cassettes sit on the bracket tops with locator bosses. They're captured by the ledger and beam. No screws needed in the deck itself — gravity and the frame hold them.

### 5. Install end pieces

The end cassettes are shorter to fit the remaining space. They may need to be generated at custom lengths (see "Generator Status" below).

## Hardware Shopping List

| Item | Quantity | Where to Buy |
|---|---|---|
| #10 × 2.5 in wood screws | 12 (9 + spares) | Home Depot / Lowes |
| 1/4 in USS flat washers | 12 | Home Depot / Lowes |
| SUNLU black PETG 1.75mm | 2 kg | Amazon (ASIN B0D1KC72YP) |

Optional but recommended:
- Stud finder (if not already verified)
- Level (24 in or longer)
- Drill with 7/64 in bit
- Torx T25 or Phillips driver

## Generator Status

**The existing R9 generator can produce the structural parts.** The geometry is in:

```
development/r9/one_bay_geometry.py
```

Functions:
- `build_shelf_cassette()` — the ribbed deck segment
- `build_left_compact_support()` / `build_right_compact_support()` — wall brackets
- `build_rear_ledger()` — rear connecting member
- `build_front_beam()` — front connecting member

**What the generator cannot currently do:**
- Custom-length end cassettes (you'd need to manually scale or edit)
- A full-wall parametric layout for 61.5 in with variable bracket positions

For now, print the standard 160mm cassettes and brackets. The end pieces may need hand-editing or accepting a slight gap at the ends covered by a simple printed cap.

### To generate the parts:

```bash
cd development/r9
python3 generate_one_bay_prototype.py
```

Output goes to `development/r9/generated/one_bay_prototype_v3/`. Open the STL or 3MF files in Bambu Studio.

## Limitations and Risks

1. **No blocking = shorter shelf.** Without wood blocking at the ends, this design only spans ~49.5 in, not 61.5 in.

2. **PETG creep.** Under sustained load, PETG slowly deforms. Keep loads light and distributed.

3. **Three-screw brackets.** Each bracket has only 3 screws into one stud. This is adequate for light loads but not for heavy storage.

4. **Printed tolerances.** The tongue-and-socket joints depend on accurate printing. Do a test fit before committing.

5. **Not fire rated.** PETG burns. Don't put this near heat sources.

## What This Is NOT

- Not a 120 lb shelf (that was the plywood/steel design target)
- Not using the Triadic Palatine ornamental skin (that's separate/optional)
- Not the full L-corner configuration (return wall is deferred)
- Not rated or certified — this is a DIY project

## Next Steps After This Works

Once the long-wall shelf is installed and holding light loads successfully:

1. **Add blocking** at 6.0 and 60.5 in if you want full wall coverage
2. **Extend to return wall** using the same bracket/cassette system
3. **Optional:** Add the Palatine decorative fascia over the structural cassettes

---

*This file replaces the plywood/steel INSTALL_NOW.md and SHOPPING_LIST.md. The goal is a printable PETG shelf you can build this week.*
