# USAGE

100% PETG Two-Deck Storage System

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      UPPER DECK                              │
│  • Less frequent access                                      │
│  • Cases, boxes, seasonal items                              │
└──────────────────────────────────────────────────────────────┘
                              ↕ 200mm gap
┌──────────────────────────────────────────────────────────────┐
│                    INTER-DECK SPACE                          │
│  • Cable troughs with hooks                                  │
│  • String cassettes (picks, strings, capos)                  │
│  • Guitar hanger on spine (guitar hangs into room)           │
└──────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────┐
│                      LOWER DECK                              │
│  • Daily access                                              │
│  • Pedalboard, amp head, frequently used gear                │
└──────────────────────────────────────────────────────────────┘
```

---

## Storage Zones

| Zone | What Lives There |
|------|-----------------|
| Upper deck | Cases, boxes, backup gear, seasonal items |
| Inter-deck | Cables (trough), strings/picks (cassette), guitar (hanger) |
| Lower deck | Daily gear — pedalboard, amp head, practice items |

---

## Part Functions

### Stud Spine

The **only** wall-load part. Everything hangs from spines.

- Screws to stud with 3× #10 wood screws
- Crown projects into room to support deck
- M4 grid on crown for attachments

**Where:** At 17.0", 32.5", 48.5" stud positions. Two per stud (upper + lower level).

### Deck Module

Ribbed box-beam for flat storage surface.

- Sits on spine crowns
- M4 holes align with crown grid
- Cross-ribs prevent deflection under point loads

**Where:** ~10 modules per level, spanning full wall length.

### Cable Trough

U-channel with integrated hooks.

- Mounts between decks
- Hooks hold coiled cables
- Trough catches loose ends

**Where:** Bolts to inter-deck bracket or spine crown in the 200mm gap.

### String Cassette

Drawer-style tray with dividers.

- Open top for easy access
- Four compartments for strings, picks, capos, slides
- Handle cutout on front

**Where:** Sits on lower deck or bolts to inter-deck bracket.

### Inter-Deck Bracket

Vertical connector between upper and lower decks.

- Top flange bolts to upper deck
- Bottom flange bolts to lower deck
- Side panel has M4 grid for mounting cable troughs

**Where:** Between spines, typically 2 per span (4 total for long wall).

### Guitar Hanger

Neck cradle that bolts to spine.

- Padded slot holds guitar neck
- Guitar body hangs into room (not on deck)
- Bolts to M4 grid on spine crown

**Where:** On lower spine, typically at middle stud (32.5") for centered access.

---

## Example Layout

```
│← 17.0" →│← 15.5" →│← 16.0" →│← wall end
│         │         │         │
│  SPINE  │ BRACKET │  SPINE  │ BRACKET │  SPINE  │
│         │         │         │         │         │
│  trough │ cassette│  trough │ (empty) │ guitar  │
│         │         │         │         │ hanger  │
```

---

## Load Guidelines

| Location | Max Load | Notes |
|----------|----------|-------|
| Upper deck (total) | 30 kg | Distributed across span |
| Lower deck (total) | 30 kg | Distributed across span |
| Single deck module | 5 kg | Centered point load |
| Guitar hanger | 1 guitar | Acoustic or electric |
| Cable trough | 2 kg | Full of cables |
| String cassette | 1 kg | Full of accessories |

PETG creep note: These limits assume 6 walls, 40% gyroid infill, and loads that sit there long-term. Short-term handling can exceed these.

---

## Access Patterns

| Frequency | Store On | Example Items |
|-----------|----------|---------------|
| Daily | Lower deck, inter-deck hangers | Practice guitar, patch cables |
| Weekly | Lower deck edges | Tuner, capo, metronome |
| Monthly | Upper deck | Extra strings, backup cables |
| Rarely | Upper deck back | Cases, seasonal, archives |

---

## Cable Management

The cable trough system:

1. **Hooks** — wrap coiled cables, prevent tangling
2. **Trough floor** — catches loose ends
3. **Open back** — allows cable runs to devices below

Suggested arrangement:
- Group cables by function (power, audio, data)
- Hang longest cables in back, shortest in front
- Label cables with tape if needed

---

## Guitar Storage

The guitar hanger mounts to the **lower** spine so the guitar hangs in the room at accessible height.

1. Bolt hanger to spine crown M4 grid
2. Guitar neck rests in padded slot
3. Body hangs free in room (not touching deck or wall)

Weight is carried entirely by the spine → stud path.

---

## Future: Short Wall

The ~36" return wall (on hold) will use:

- Same spine vocabulary
- Same deck modules
- Corner bracket (future part) to turn the system

When measured, add parts without changing existing long-wall installation.

---

## Customization

All parts are parametric in `scripts/generate_storage_arcade.py`. To customize:

1. Edit constants at top of script
2. Run `python3 scripts/generate_storage_arcade.py`
3. New STL/3MF files appear in `generated/storage_arcade/`

Adjustable parameters:
- Spine dimensions (width, height, crown depth)
- Deck dimensions (length, width, rib count)
- M4 grid positions
- Trough hook count
- Cassette compartment layout
