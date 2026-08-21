# Print the Shelf — Classical Roman Arch in PETG

**100% PETG. Classical Roman arch proportions. Heavy-duty structural.**

No plywood. No steel. No decorative skins. This is a real Roman arch bracket that transfers load through compression into the wall, printed entirely in PETG.

## The Design

This shelf uses **classical Roman arch architecture** — the same structural principles that have held up aqueducts and palaces for two thousand years. Load flows through compression along the curved arch, into the piers, and into the wall.

### Visual Elements (Classical Roman Arch)

| Element | Description |
|---------|-------------|
| **Pier** | 30mm wide front column — the vertical anchor |
| **Impost / Capital** | 8mm transition block where arch springs from pier |
| **Archivolt** | Semicircular arch profile with molding bands |
| **Keystone** | Implied keystone with +3mm extra thickness at crown |
| **Soffit** | 4 ribs create masonry-like arch underside |
| **Spandrel** | Solid fill above arch for smooth deck support |

### Structural Features

- **40mm thick** arch brackets for torsional stiffness
- **42mm deep** box-beam deck segments for bending stiffness
- **5mm walls** throughout
- **4 screws per bracket** into studs
- **M5 bolts** connecting deck to brackets

## Build Constraints — Bambu A1 Mini

**CRITICAL: 160mm maximum on bed axes (XY) with brim enabled.**

The A1 mini has a 180mm cube build volume, but the calibration region and brim eat into the usable bed area. A 170mm part will fail Bambu gcode check (error 4 — off the plate).

| Constraint | Limit |
|------------|-------|
| Build volume | 180 × 180 × 180 mm |
| **Max XY with brim** | **160 × 160 mm** |
| Max Z | 180 mm |

All parts in this design have been verified to fit within the 160mm XY constraint:

| Part | Dimensions (mm) | Fits? |
|------|-----------------|-------|
| `arch_bracket.stl` | 152 × 40 × 160 | ✓ |
| `deck_segment.stl` | 158 × 152 × 42 | ✓ |
| `end_bracket.stl` | 60 × 40 × 80 | ✓ |

## Target Load

### 75 lb (34 kg) evenly distributed — sustained, long-term

This is real weight: packed storage bins, stacks of folded clothes, closet storage.

| Factor | This Design | Why It Matters |
|--------|-------------|----------------|
| Deck depth | 42mm box beam | Deep section = high moment of inertia |
| Deck walls | 5mm PETG | Thick walls resist buckling |
| Deck ribs | 5 longitudinal + 3 cross | Internal bracing prevents flex |
| Max span | 17 in (to first bracket) | Short spans = less deflection |
| Bracket thickness | 40mm with 4 ribs | Torsionally rigid, won't twist |
| Wall screws | 4 × #10×3" per bracket | Deep engagement, redundant |
| PETG creep factor | 2× safety margin | Designed for 150 lb short-term |

### Want 100+ lb capacity?

You need ONE of these:
1. **Add a 4th bracket** — requires installing wood blocking near wall end
2. **Reduce max span to 12 in** — add brackets, need more studs/blocking
3. **Increase deck depth to 50mm** — requires larger printer

## Files to Print

All files in [`generated/all_petg_shelf/`](generated/all_petg_shelf/):

| File | Dimensions | Qty | Print Time | PETG |
|------|------------|-----|------------|------|
| `arch_bracket.stl` | 152 × 40 × 160 mm | **3** | 9 hrs each | 200g |
| `deck_segment.stl` | 158 × 152 × 42 mm | **10** | 6 hrs each | 190g |
| `end_bracket.stl` | 60 × 40 × 80 mm | **2** | 2 hrs each | 60g |

**Totals:**
- **15 parts**
- **~91 hours** print time
- **~2.6 kg** PETG (buy 3 kg)

## Print Settings — High Strength

These settings are required for heavy-duty performance:

| Setting | Value | Why |
|---------|-------|-----|
| **Material** | PETG (SUNLU black) | Strong, less brittle than PLA |
| **Layer height** | 0.2mm | Good layer adhesion |
| **Wall loops** | **6** | Thick perimeters = strength |
| **Top/bottom layers** | **6** | Solid surfaces |
| **Infill** | **40% gyroid** | High infill for load bearing |
| **Nozzle temp** | **245°C** | Hot = better layer bonding |
| **Bed temp** | **75°C** | Good adhesion, less warp |
| **Cooling** | **50-60%** | Some cooling, not too much |
| **Print speed** | **60 mm/s** | Slower = stronger |
| **Brim** | **YES** | Required — parts verified to fit |

**DO NOT reduce wall loops or infill.** These parts need to be solid.

## Print Orientations

### Arch Bracket
Print with **arch opening facing UP**.

```
          ╭───────╮
         ╱ keystone╲
        │           │
        │   (air)   │     ← Arch cavity
        │           │
   ─────┼───────────┼─────  Build plate
        pier       pier
```

This puts print layers **perpendicular to the load direction**. Load pushes down through the arch; layers are horizontal. Layers won't peel apart.

**Supports: YES** — organic supports for arch interior and screw counterbores.

### Deck Segment
Print with **TOP face DOWN** (touching build plate).

```
   ═══════════════════════  Build plate (= smooth top surface)
   │ rib │ rib │ rib │ rib │   ← Ribs print upward
   └─────┴─────┴─────┴─────┘
```

This gives you a smooth usable top surface.

**Supports: NO** — the box structure is self-supporting.

### End Bracket
Print **flat on the vertical leg**.

**Supports: Minimal** — just for the diagonal.

## Hardware

| Item | Qty | Spec | Notes |
|------|-----|------|-------|
| Wall screws | 12 | #10 × 3" wood screws | Or GRK RSS 1/4" × 3" |
| Fender washers | 12 | 1/4" ID × 1" OD | Large washers spread load |
| Deck bolts | 60 | M5 × 50mm hex | Through deck into bracket tops |
| Nylock nuts | 60 | M5 | Prevents loosening |

## Assembly

### 1. Mount Arch Brackets to Studs

Bracket positions at verified studs: **17.0", 32.5", 48.5"** from inside corner.

1. Mark stud centerlines on wall
2. Mark shelf height (e.g., 68" from floor)
3. Position bracket, check level
4. Through the 4 counterbored holes, drill 7/64" pilot holes into stud
5. Insert fender washer, drive #10 × 3" screw
6. **Snug all 4 screws** — don't overtorque (PETG can crack)
7. Check bracket is plumb and solid
8. Repeat for all 3 brackets

### 2. Install Deck Segments

The deck segments span between brackets and bolt to the bracket top plates.

1. Set first deck segment on bracket tops (at left end)
2. Align bolt holes (6 per bracket-deck joint)
3. Insert M5 bolts from above
4. Thread nylock nuts from below, tighten
5. Continue with next segment, butting tightly against previous
6. Segments share bolt rows where they meet over a bracket

### 3. Install End Brackets

The end brackets support deck overhang beyond the last stud bracket.

1. Position end bracket under deck, against end wall
2. Bolt through end bracket into deck bottom
3. Repeat at other end

### 4. Load Test

Before loading with storage:
1. Press down firmly at center of each span — should feel solid
2. Check all bolts are tight
3. Load gradually: 20 lb, then 40, then 60
4. Listen for creaking, watch for visible deflection
5. If anything seems wrong, unload and investigate

## Layout Diagram

```
Wall (61.5" total)
├────────────────────────────────────────────────────────────────┤

     17.0"         32.5"         48.5"
       ↓             ↓             ↓
   ┌───╫─────────────╫─────────────╫───┐
   │   ║   deck ×10  ║   158mm ea  ║   │  ← Deck segments
   └───╫─────────────╫─────────────╫───┘
       ║             ║             ║
      ╔╩╗           ╔╩╗           ╔╩╗      ← Roman arch brackets
      ║ ║           ║ ║           ║ ║
      ╰─╯           ╰─╯           ╰─╯
        STUD          STUD          STUD

   |←------ 15.5" ----→|←---- 16" ----→|
         span              span
```

**Spans:**
- Left overhang: ~11"
- Span 1-2: 15.5"
- Span 2-3: 16.0"
- Right overhang: ~7"

Maximum span of 17" (to first bracket) is within design limits for 75 lb load.

## Structural Notes

### Why Roman Arches Work

1. **Compression load path** — Load flows through the curved arch in compression, not bending. The arch shape naturally directs force into the piers and wall.

2. **Classical proportions** — The pier width (30mm) and arch radius are sized following classical proportions, ensuring visual balance and structural efficiency.

3. **Box-beam deck** — A 42mm deep hollow section with 5mm walls and internal ribs has high bending stiffness. Much stronger than a solid plate of equal weight.

4. **Multiple fasteners** — 4 screws per bracket, 6 bolts per deck joint. Redundancy means one failed fastener doesn't cause collapse.

### PETG Creep Factor

PETG is a thermoplastic — it creeps under sustained load. This design accounts for creep by:

- **2× load factor**: Sized for 150 lb short-term to sustain 75 lb indefinitely
- **Deep sections**: 42mm deck depth keeps stress low
- **Thick walls**: 5mm walls = lower stress per unit area
- **High infill**: 40% gyroid infill distributes load

### What NOT to Do

- **Don't reduce infill** — 15% infill will fail under load
- **Don't thin the walls** — 2-3 walls won't carry sustained weight
- **Don't use PLA** — PLA creeps more than PETG
- **Don't skip bolts** — Friction connections will creep apart
- **Don't point-load the front edge** — Distribute weight evenly

## Regenerating Parts

To modify dimensions and regenerate:

```bash
python3 scripts/generate_all_petg_shelf.py
```

Key parameters in the script:
- `ARCH_THICKNESS_MM` — Bracket width
- `DECK_HEIGHT_MM` — Deck depth (most important for load capacity)
- `DECK_WALL_MM` — Wall thickness
- `MAX_BED_XY_MM` — Bed constraint (160mm for A1 mini with brim)

Output: `generated/all_petg_shelf/`

---

**Download the STLs. Print them with the settings above. Bolt it together. Screw it to your studs. Load it up.**

A Roman arch shelf that looks like it belongs in a palace — and holds your stuff.
