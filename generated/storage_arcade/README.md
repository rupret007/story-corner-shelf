# 100% PETG Two-Shelf System

Two stacked shelves on the long wall. That's it.

## Parts

| Part | File | Qty | Size (mm) |
|------|------|-----|-----------|
| Stud spine | stud_spine.stl | 6 | 40 x 120 x 155 |
| Deck module | deck_module.stl | 20 | 155 x 155 x 25 |

## Wall

- Long wall: 61.5 in (1562 mm)
- Studs at: 17.0, 32.5, 48.5 in from inside corner
- Two levels (upper + lower shelf)

## Hardware

| Item | Spec | Qty |
|------|------|-----|
| Wood screws | #10 x 2.5 in | 18 |
| M4 bolts | M4 x 20mm | ~120 |
| M4 nuts | Nylock | ~120 |
| M4 washers | Flat | ~240 |

## Print Settings

| Setting | Value |
|---------|-------|
| Material | PETG |
| Walls | 5 |
| Infill | 40% gyroid |
| Layer | 0.2mm |
| Supports | None |

Print spine with back plate on bed.
Print deck upside down (smooth top surface on bed).

## Assembly

### 1. Mount spines to studs

At each stud (17.0, 32.5, 48.5 in):

1. Hold spine against wall, ledge facing into room
2. Level horizontally
3. Drive 3x #10 wood screws through back plate into stud

Do lower level first, then upper level directly above.

### 2. Install deck modules

1. Place deck on spine ledges
2. Push against wall
3. Bolt through deck into spine ledge (M4 through top of deck)
4. Bolt adjacent decks to each other (M4 through end walls)

## Load

- Max distributed load per level: ~25 kg
- Avoid point loads >3 kg without spreading
- PETG creeps under sustained load; short spans help

## Files

```
generated/storage_arcade/
├── stud_spine.stl    (6 needed)
├── deck_module.stl   (20 needed)
├── manifest.json
└── README.md
```
