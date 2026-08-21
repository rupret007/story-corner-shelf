# The Classic Look — Roman Arch Visual Language

This document explains the intentional architectural design choices that make this shelf look like a proper Roman arch, not just "a plastic bracket with a hole in it."

## Design Philosophy

The goal was to create a shelf bracket that:
1. **Looks like classical architecture** — recognizably Roman, palace-adjacent
2. **Uses the arch as the actual load path** — not decoration
3. **Prints as a single solid piece** — no assembly, no snap-fit
4. **Fits an A1 mini** — 160mm XY constraint with brim

## Classical Roman Arch Elements

### 1. Pier (30mm wide)

The **pier** is the vertical column that supports the arch. In classical architecture, pier width determines visual mass and structural capacity.

```
    ┌─────┐
    │     │  ← Pier (front column)
    │     │
    │     │
    └─────┘
```

**Design choice:** 30mm width gives substantial visual presence while leaving room for the arch opening. Classical proportion: pier width is roughly 1/3 to 1/4 of the arch span.

### 2. Impost / Capital (8mm)

The **impost** (also called **capital** or **springer block**) is the transition element where the vertical pier meets the curved arch. It projects slightly beyond the pier face.

```
         ╭───╮
        ╱     ╲
   ┌───┼       ┼───┐  ← Impost projects 3mm
   │   │       │   │
   │   │       │   │
```

**Design choice:** 8mm height with 3mm projection creates a visible "ledge" that breaks the visual monotony and signals "the arch starts here."

### 3. Archivolt (Semicircular Arch)

The **archivolt** is the main curved arch profile. In Roman architecture, it's always a **true semicircle** (180°), not a pointed Gothic arch or a segmental arc.

```
          ╭───────╮
         ╱         ╲
        │           │
        │           │
```

**Design choice:** The arch radius equals half the span between the two pier faces. This creates a perfect semicircle — the signature of Roman architecture.

The archivolt has **multiple bands** (the front and back walls of the bracket) that create depth and shadow, suggesting carved stone molding.

### 4. Keystone (Implied, +3mm at crown)

The **keystone** is the wedge-shaped block at the very top (crown) of the arch. In masonry, it's the last block placed and locks the arch together.

```
          ╭─╲█╱─╮     ← Keystone (thickened at crown)
         ╱       ╲
```

**Design choice:** Rather than a separate block, the keystone is **implied** by thickening the arch rib by 3mm at the crown. This creates a subtle visual emphasis at the top of the arch — the eye recognizes it as a keystone even without a sharp outline.

### 5. Soffit (4 Ribs)

The **soffit** is the underside surface of the arch — what you see when looking up into the arch opening. In masonry, the soffit shows individual voussoir (wedge-shaped) stones.

```
        │ ║ ║ ║ ║ │
        │ ║ ║ ║ ║ │   ← 4 ribs create masonry-like texture
        │ ║ ║ ║ ║ │
```

**Design choice:** 4 parallel ribs (the internal walls of the bracket) create a **masonry-like texture** on the soffit. This suggests individual stones rather than smooth plastic.

### 6. Spandrel (Solid Fill)

The **spandrel** is the roughly triangular area between the curved extrados (outer surface) of the arch and the rectangular top plate.

```
   ┌─────────────────────┐  ← Top plate
   │███████████████████│
   │██╭───────────╮████│  ← Spandrel fill (shaded)
   │█╱             ╲███│
```

**Design choice:** The spandrel is **solid filled**, not hollow. This:
- Transfers deck load smoothly into the arch
- Looks like proper masonry construction (not skeletal)
- Adds structural material where load concentrates

## Proportions

The proportions follow classical Roman guidelines:

| Element | Dimension | Ratio |
|---------|-----------|-------|
| Arch span | ~97mm | 1.0 |
| Pier width | 30mm | 0.31 |
| Impost height | 8mm | 0.08 |
| Keystone extra | 3mm | 0.03 |

**Pier-to-span ratio of ~1:3** is within the classical range (1:4 to 1:3 for heavy construction).

## Why It Reads as "Roman"

1. **True semicircle** — The defining feature of Roman arches vs. Gothic pointed arches
2. **Visual mass** — Thick piers and solid spandrels suggest stone, not wire
3. **Transition elements** — Impost blocks signal "this is architecture, not just structure"
4. **Implied depth** — Multiple ribs and keystone thickening create shadow lines
5. **Masonry texture** — Rib spacing on soffit suggests individual stones

## What We Avoided

| Wrong Choice | Why It Looks Cheap |
|--------------|-------------------|
| Thin 2mm walls | Looks like a plastic toy |
| Single arch outline | Looks like wire sculpture |
| No impost | Arch springs abruptly from column |
| Pointed arch | Gothic, not Roman |
| Hollow spandrel | Looks skeletal, incomplete |
| Smooth soffit | Looks like PVC pipe |

## The Result

A stranger looking at this bracket should think:

> "That looks like a Roman arch — like something from an aqueduct or a palace."

Not:

> "That's a plastic bracket with a curved hole."

The visual language works because every element — pier, impost, archivolt, keystone, soffit, spandrel — is present and proportioned according to classical precedent.

---

**This is intentional design, not accidental.**
