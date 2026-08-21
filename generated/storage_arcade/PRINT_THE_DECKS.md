# PRINT THE DECKS

100% PETG Two-Deck Storage System

---

## Why No Arches

Arches were removed because **they are not in the load path**.

- Spines screw to studs and carry all vertical load.
- Decks sit on spine crowns.
- Arches would add printed mass without storing anything or carrying load.

Every gram printed must store something or carry load. Arches fail that test.

---

## Height Assumption (UNVERIFIED)

| Measurement | Value | Status |
|-------------|-------|--------|
| Outlet-top to ceiling | 43.5 in (1105 mm) | USER-REPORTED, NOT VERIFIED |
| Ceiling clearance | 25 mm | Design parameter |
| Outlet clearance | 50 mm | Design parameter |
| Inter-deck gap | 200 mm | Space for attachments |

**ACTION:** Field-measure outlet-top to ceiling before finalizing spine heights.

---

## Wall Status

| Wall | Length | Status |
|------|--------|--------|
| Long wall | 61.5 in | **ACTIVE** — Two decks being printed |
| Short wall | ~36 in | **ON HOLD** — Needs measurement |

---

## Part Counts (Long Wall Only)

| Part | Qty | Notes |
|------|-----|-------|
| stud_spine | 6 | 2 per stud × 3 studs |
| deck_module | 20 | 10 per level × 2 levels |
| cable_trough | 2-4 | As needed |
| string_cassette | 1-2 | As needed |
| inter_deck_bracket | 4 | Adds rigidity between levels |
| guitar_hanger | 1 | Bolts to lower spine |

---

## Print Settings (All Parts)

| Setting | Value | Why |
|---------|-------|-----|
| Material | PETG | Creep resistance, humidity tolerance |
| Wall loops | 6 | Load-bearing structure |
| Infill | 40% gyroid | Strength-to-weight, no print artifacts |
| Layer height | 0.2mm | Balance of speed and quality |
| Top/bottom layers | 5 | Deck surface durability |
| Supports | None | Parts designed support-free |

---

## Print Time Estimates (0.2mm layer, 60mm/s)

| Part | Time Each | Total |
|------|-----------|-------|
| stud_spine | ~4h | 24h |
| deck_module | ~3h | 60h |
| cable_trough | ~1.5h | 3-6h |
| string_cassette | ~1h | 1-2h |
| inter_deck_bracket | ~3h | 12h |
| guitar_hanger | ~1.5h | 1.5h |

**Total print time:** ~100-110 hours

---

## Hardware List

| Item | Spec | Qty | Use |
|------|------|-----|-----|
| Wood screws | #10 × 3 in | 18 | Spine to stud (3 per spine) |
| M4 × 25mm | Socket head | 150 | PETG-to-PETG joints |
| M4 nylock | — | 150 | Prevent loosening |
| M4 washers | Flat | 300 | Load distribution |

---

## Assembly Order

### 1. Mount Lower Spines (3)

At each stud position (17.0, 32.5, 48.5 in):

1. Hold spine with crown facing into room
2. Level horizontally
3. Drive three #10 × 3" screws through spine into stud
4. Verify spine is plumb and crown is level

### 2. Install Lower Deck Modules (~10)

1. Place deck modules on spine crowns
2. Push against wall to align
3. Bolt through deck into crown M4 holes
4. Use M4 × 25mm + nylock + washers on both sides

### 3. Install Inter-Deck Brackets (4)

Between stud positions:

1. Position bracket with flanges touching lower deck
2. Bolt bottom flange to lower deck
3. Verify bracket is plumb

### 4. Mount Upper Spines (3)

Above lower spines at each stud:

1. Position upper spine directly above lower
2. Crown level with inter-deck bracket tops
3. Screw to stud (3 screws each)

### 5. Install Upper Deck Modules (~10)

1. Lay decks on upper spine crowns
2. Bolt through deck into crown
3. Bolt to inter-deck bracket top flanges

### 6. Add Functional Attachments

- **Cable troughs:** Bolt to inter-deck bracket side faces
- **String cassettes:** Place on lower deck or bolt to bracket
- **Guitar hanger:** Bolt to lower spine crown using M4 grid

---

## Architecture Diagram

```
        ┌──────────────────────────────────────────────────┐
CEILING │                                                  │
        ├──────────────────────────────────────────────────┤
        │  ┌─────────────────────────────────────────────┐ │
        │  │             UPPER DECK (10 modules)         │ │
        │  └─────────────────────────────────────────────┘ │
        │          ↑              ↑              ↑         │
        │      ┌───┴──┐       ┌───┴──┐       ┌───┴──┐      │
        │      │SPINE │       │SPINE │       │SPINE │      │
        │      │  @   │       │  @   │       │  @   │      │
        │      │17.0" │       │32.5" │       │48.5" │      │
        │      └───┬──┘       └───┬──┘       └───┬──┘      │
        │          │              │              │         │
        │   ┌──────┴──────────────┴──────────────┴──────┐  │
        │   │           INTER-DECK GAP (200mm)         │  │
        │   │      • Cable troughs                     │  │
        │   │      • String cassettes                  │  │
        │   │      • Guitar hanger (on spine)          │  │
        │   └──────┬──────────────┬──────────────┬──────┘  │
        │          │              │              │         │
        │      ┌───┴──┐       ┌───┴──┐       ┌───┴──┐      │
        │      │SPINE │       │SPINE │       │SPINE │      │
        │      │  @   │       │  @   │       │  @   │      │
        │      │17.0" │       │32.5" │       │48.5" │      │
        │      └───┬──┘       └───┬──┘       └───┬──┘      │
        │          ↓              ↓              ↓         │
        │  ┌─────────────────────────────────────────────┐ │
        │  │             LOWER DECK (10 modules)         │ │
        │  └─────────────────────────────────────────────┘ │
        │                                                  │
OUTLET  ├──────────────────────────────────────────────────┤
```

---

## Load Capacity

| Metric | Value |
|--------|-------|
| Lower deck | 30+ kg distributed |
| Upper deck | 30+ kg distributed |
| Guitar hanger | Single acoustic guitar |
| Point load on deck | 3 kg max without spreader |

PETG creep: 6 walls + gyroid infill resists long-term deflection.

---

## Quality Gates

Before installation:

- [ ] All 6 spines are watertight (slicer shows no holes)
- [ ] All 20 deck modules printed with 6 walls
- [ ] All parts fit together dry (no forcing)
- [ ] M4 holes accept bolts without reaming
- [ ] Wood screw holes are correct diameter

During installation:

- [ ] Spines are plumb (use level)
- [ ] Crown surfaces are level (use level)
- [ ] All M4 joints have washers both sides
- [ ] Nylock nuts are finger-tight + 1/4 turn

---

## What's Next: Short Wall

The ~36 in return wall uses the same part vocabulary:

- Same spines screw to corner stud
- Same deck modules span the wall
- Same attachments fit the inter-deck space

**Currently ON HOLD** — field measurement required.

---

## Files

| File | Part |
|------|------|
| stud_spine.stl | Wall-mount spine with crown |
| deck_module.stl | Ribbed box-beam deck |
| cable_trough.stl | U-channel with hooks |
| string_cassette.stl | Divider tray |
| inter_deck_bracket.stl | Level connector |
| guitar_hanger.stl | Neck hanger |

3MF versions also provided for Bambu Studio.
