# R11 physical-photo provenance

> Photos document appearance and reported handling only. They do not prove
> dimensions, hidden contact, material properties, load capacity, or a passed
> qualification gate.

## Source observations

The left article observation in [../PHYSICAL_RECORD.md](../PHYSICAL_RECORD.md)
references these user-supplied attachment sets without publishing local or
temporary filesystem paths:

| Evidence ID | Images | What is visible | Limits |
|---|---:|---|---|
| `925CA0D3-6200-496B-A109-CA4D2610463B` | 1–8 | Multiple views of the completed left half-deck, including top, bottom, edges, fingers, and end views | No scale, no right mate, no measured fit, no load |
| `83787EA1-DE26-4497-BB8C-7FC25D665434` | 1 | Left half-deck standing on the table after the user reported no rocking | A still image cannot independently prove flatness or absence of motion |

Cryptographic source references, in image order:

- `925CA...` image 1: `646c31b35bb67188e77abfd92c3c09e2c420d675fdaab9f34cffaf3cc2e8583c`
- `925CA...` image 2: `631b42988708b731505988ef9e332e2ae5fa77266d86bb25008347c0b089ddac`
- `925CA...` image 3: `e8334c57ccf887436a1bdffefe264ca654a92a457f584e462b8a34316656d03d`
- `925CA...` image 4: `917b03245b5172897cb30f4c11e0f384d5a3abc514988e67968b74a1104fb8ae`
- `925CA...` image 5: `96b0d66046600eb1dbbf3e7494eed748a388058abdfeb445df750eaa8fd37016`
- `925CA...` image 6: `cb4d2d05cf6f2a443a67ef170cbc41339ac437c3c163f4d98e6c07a6b36faef9`
- `925CA...` image 7: `c5673ec24bef7b7bd1cad602716335ee2f3bdfb6fc85e955b5dc6f59d4367483`
- `925CA...` image 8: `87546c71d436c587fe3f742a41212e9cd5d60cb642de905d059456c0ed6b68a9`
- `83787...` image 1: `6636e852ba4d0e40dd4f7dcdac8304c59b4267f397bee0f5a03f3d9f9ca37fe2`

These hashes identify the private source attachments without publishing their
temporary local paths. The attachments themselves, not the transformed image
below, remain the controlling visual observations.

The original attachments remain the observation sources. If copies are added
to a future release, record the repository filename, byte count, SHA-256, and
any metadata removal without changing the evidence ID.

## Cleaned presentation reference

Expected repository asset:

- `left-half-clean-reference.png`

This is a background-cleaned documentation aid derived from a user photo. It
is for orientation and presentation only. It is **not** a measurement image,
not a substitute for an original, and not evidence of a feature that the
source photo did not clearly show.

Image-edit provenance:

- Source evidence ID: `925CA0D3-6200-496B-A109-CA4D2610463B`, image 8.
- Mode: image edit; preserve the printed article, remove only background
  distraction, and use a neutral documentation background.
- Exact generation prompt:

  > Use case: precise-object-edit
  > Asset type: engineering assembly guide reference photograph
  > Primary request: Create a clean, documentation-ready version of this
  > exact photograph of the black PETG R11 left terminal integrated half-deck.
  > Rotate the image so the part is upright and easy to understand, crop
  > tightly but keep the complete printed part visible, replace only the
  > distracting desk/keyboard/background with a plain neutral matte
  > background, and improve exposure so black surfaces and openings remain
  > legible.
  > Input image: edit target and sole source of part geometry.
  > Constraints: Preserve the printed part's geometry, proportions, openings,
  > fingers, capture slot, surface texture, layer lines, seams, and any visible
  > imperfections exactly. Do not add, remove, straighten, repair, smooth,
  > reshape, mirror, or invent any feature. Do not add arrows, labels,
  > dimensions, text, watermark, hands, tools, supports, or other parts. This
  > is a presentation reference only, not fabricated evidence.

- Final asset SHA-256:
  `a8d6ae08c5cc06fe8967a1790233a1adceac7dd102651eadc38584cd67bccbd4`
- Authenticity metadata: the PNG intentionally retains its C2PA/JUMBF
  generative-edit provenance. This is kept for transparency; it is not relied
  on as dimensional or qualification evidence and must not be stripped without
  producing a new asset hash and provenance record.
- Review: visually compared with source image 8. The overall article outline,
  three reciprocal rows, center body, edge walls, visible capture feature, and
  visible surface seams remain recognizable. Because generative editing is
  not pixel-preserving, the original attachment remains controlling evidence.

Do not use the cleaned image to infer gaps, dimensions, flatness, contact, or
capacity.

## Photos still needed for the one-bay dry fit

Take these only after the right half has finished, cooled, been removed, and
passed its visual check:

1. Both complete halves side by side, top faces up, with left/right labels in
   frame.
2. Both wall-side edges aligned and both front edges visible before contact.
3. Close view of the rear lap row aligned but not engaged.
4. Close view of the center lap row aligned but not engaged.
5. Close view of the front lap row aligned but not engaged.
6. Full top view after the first gentle join.
7. Low front-edge view showing top alignment and the center seam.
8. Low wall-side view showing all three lap rows.
9. One close view per lap row after cycle 1.
10. Full top and low edge views after cycle 5.
11. Full top and low edge views after cycle 10.
12. Both separated halves after cycle 10, showing every lap face and finger.

Use the same lighting and camera direction for the cycle 1, 5, and 10 views so
changes are easy to compare. Include a handwritten card with article IDs and
cycle number; do not rely on filename order alone.

## Short video still needed

Record one continuous, stationary-camera clip after the first still-photo fit
passes:

1. Show both labels and both separated halves.
2. Point to rear, center, and front lap rows.
3. Align all three rows.
4. Join once with the gentle straight hand motion.
5. Pause on the seated top and seam.
6. Reverse the same motion and show both separated lap faces.
7. End on a card reading `cycle 1` and the date.

Keep the complete motion and both hands in frame. Do not speed up, cut around a
bind, or add a reenacted take to the evidence clip. A later edited copy may be
made for teaching, but preserve and hash the original continuous file first.
