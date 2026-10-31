# R12 production-first print order

1. Print the four qualification objects in order: adhesion-corner coupon,
   fascia-fit coupon (with real plywood, steel angle, and 2.4 mm tile sample),
   Palatine detail coupon (face-up), and corner-fit gauge.
2. After all four pass, print one `MODEL_ONLY_PETG_TopTile_Center_6inPitch.3mf`;
   it is an installed part.
3. After it passes first-layer and cooled-flatness inspection, print the
   remaining 13 long-wall center tiles.
4. Universal rear-curb centers may follow; the long wall uses eight.
5. Regenerate fitted pieces after both installed shelf-back offsets and
   full-size corner geometry are verified.
6. Return-arm production parts remain on hold until its measurements are entered.

A production tile passes only with continuous bonded first-layer lines, no
dragged strand, no lifted corner, no delamination, and no more than 0.5 mm
cooled corner lift on a flat reference surface.
