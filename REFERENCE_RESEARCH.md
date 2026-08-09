# Story Corner r6 reference research

Status: design input only. No third-party mesh is copied into Story Corner, and
none of the referenced models establishes a load rating for this project.

## Attached Mini Wall Shelf profiles

Files inspected read-only on 2026-08-09:

- `Wall-Shelf-Single-Color.3mf` (owner-supplied local reference; not redistributed)
  - SHA-256: `829df972a37ef2553d21b1795628296d98f130a91a5bd424aef812566465c0de`
- `Wall-Shelf+120%.3mf` (owner-supplied local reference; not redistributed)
  - SHA-256: `f9872c236110bbc99c434b07daf0b04162ce48a6571147d962fa99342d0f727d`

Both packages contain the same Andreas Mini Wall Shelf geometry from
<https://makerworld.com/en/models/567136-mini-wall-shelf-no-ams-no-support-a1-mini>.
The second profile applies a uniform 1.2 scale; it is not a different joint or
structural design.

Measured model facts:

| Property | Original profile | 120% profile |
| --- | ---: | ---: |
| Shelf plate | 150 x 90 x 6 mm | 180 x 108 x 7.2 mm |
| Each bracket, unrotated envelope | 15 x 52.134 x 42.421 mm | 18 x 62.560 x 50.905 mm |
| Shelf/bracket bodies | 1 shelf + 2 brackets | same geometry, scaled |
| Embedded G-code payload | none | none |
| License metadata | CC BY-NC | CC BY-NC |

The original profile is configured for an A1 mini with a 0.4 mm nozzle,
0.20 mm layers, three walls, 15% gyroid infill, no supports, and Overture PLA.
Its slice metadata estimates 54.96 g. The 120% project is configured for a
full-size A1 with a 0.4 mm nozzle and PLA; it contains project/plate metadata
but no sliced G-code payload.

The underside of the shelf has two asymmetric recessed locators per bracket.
Each recess is approximately 15.2 mm wide; the two lengths are approximately
5.2 mm and 10.2 mm; recess depth is 3 mm on the original. This is consistent
with about 0.2 mm total clearance over nominal 15 x 5 and 15 x 10 mm bracket
tabs. The asymmetry is a good poka-yoke feature: it establishes orientation and
resists in-plane rocking. The recesses are shallow gravity seats, not a
qualified long-span structural splice.

Useful principles for r6:

- asymmetric keys make wrong-way assembly difficult;
- a triangular bracket should be oriented so its principal force path and
  actual layer-growth path are explicit and testable;
- separate shelf and brackets permit replacement and orientation-specific
  printing;
- a screwdriver access bore can hide the structural wall fastener.

Changes required for Story Corner:

- do not scale the Mini Wall Shelf geometry into a long overhead shelf;
- use broad integral bearing caps rather than 3 mm-deep locator pockets or a
  loose saddle interface;
- use large bearing faces, indexed positive mechanical locks, and accessible
  double-shear pins rather than relying on friction or gravity alone;
- size wall access and bearing seats around the actual selected structural
  screw and metal washer/head after field verification;
- position primary seams over corbel-columns and stagger every remaining seam;
- qualify the actual black PETG, printer, orientation, joints, and wall mockup
  with full-bay and sustained-creep tests.

The 2026 Modern Shelf Stand at
<https://makerworld.com/en/models/3019655-modern-shelf-stand> remains a listing
and photographic reference only. Its MakerWorld Standard Digital File License
does not permit redistribution or derivative geometry in the Story Corner
repository. Its actual `.3mf` has not been supplied.

## Current modular systems and permissive code

### HomeRacker

Source: <https://github.com/kellerlabs/homeracker>

HomeRacker uses modular supports, connectors, and accessible square lock pins.
It makes the pin removable from the opposite side and centralizes its fit
tolerance. Source code is MIT; its `/models` geometry is CC BY-SA 4.0. Story
Corner will not copy those meshes. The transferable ideas are accessible
push-through pins, calibration before production, replaceable locks, and an
explicit layer-by-layer assembly order. HomeRacker itself warns that all
material/printer/configuration combinations have not been load-tested.

### JointSCAD

Source: <https://github.com/HopefulLlama/JointSCAD>

JointSCAD is an MIT-licensed parametric OpenSCAD library covering bridle,
dovetail, finger, mortise-and-tenon, pinned-tenon, and scarf-joint primitives.
It is useful as a catalog of joinery parameterization, not as evidence of FFF
strength. Story Corner will generate original Python geometry and retain an
attribution notice if any algorithmic implementation is ported.

### BOSL2

Source: <https://github.com/BelfrySCAD/BOSL2>

BOSL2 is BSD-2-Clause. Its joiner library exposes tapered sliding dovetails,
snap pins, clips, and configurable print clearance; its truss tools demonstrate
printable cross-bracing. Story Corner uses the same good practices—one
calibrated clearance parameter, lead-ins, stress-relief radii, and test
coupons—but will not silently copy code. Any port will preserve the BSD notice.

### rackstack

Source: <https://github.com/jazwa/rackstack>

rackstack is an MIT-licensed parametric printed rack. Its most important lesson
is procedural: print an evaluation part first, then tune one centralized
tolerance value before committing to the complete set. It uses metal fasteners,
dowels, and magnets, so it is not an all-PETG load-path precedent.

### labrax-shelf

Source: <https://github.com/mix-forever/labrax-shelf>

This CC BY 4.0 parametric OpenSCAD shelf is a useful validation/orientation
reference: face-down support-free panels, generated ribs and gussets, collision
checks around holes, and explicit build-volume assertions. Story Corner will
apply those process principles to original geometry.

## Research incorporated into the r6 architecture

The 2026 study “Wedged mortise-tenon structure for fixed connections in
additive manufacturing assemblies using fused filament fabrication” found that
a self-locking wedged mortise-and-tenon could distribute load and fail more
progressively than the study's adhesive joint. It also used a tenon kerf and
mortise relief to allow controlled deformation. The specimens were PLA and the
reported strengths are not transferable to this PETG shelf. Story Corner adopts
only the geometry principles: long bearing contact, a controlled wedge, relief
at the tenon root, and a removable lock that does not depend on glue.

Source: <https://doi.org/10.1007/s40964-026-01565-3>

PETG is time-dependent and anisotropic. A 2025 creep study validated accelerated
predictions against one-month conventional tests and showed a strength/creep
tradeoff between infill patterns. That supports a minimum 30-day sustained-load
test but does not supply a shelf allowable. A separate PETG study confirms that
FFF process parameters and orientation materially affect tensile response.

- <https://doi.org/10.1016/j.engfailanal.2025.110120>
- <https://doi.org/10.3390/polym11071220>

## r6 design decision

The chosen system is an original structural tied-arcade:

1. The 6 in coffered cassette deck is the diaphragm.
2. 3:4:5 corbel-columns with integral bearing caps transfer each reaction to
   verified wood blocking or studs through nonprinted structural screws and
   metal washer-head bearing surfaces. Their wall-contact-face-down candidate
   orientation remains unqualified until every generated layer is connected
   and the actual printer/toolpath coupon passes.
3. Each Roman curved rib is one member of a closed, mixed-action tied-spandrel
   frame; its shape alone does not establish a pure-compression load path.
4. The cassette-entablature chord, crown bridge, pier nodes, and wall corbel
   complete the candidate frame. Only instrumented comparison testing may
   establish whether the curved rib materially improves stiffness or failure
   behavior.
5. Modules self-jig with overlapping seats, indexed quarter-turn cross-keys,
   and visible positive-retention pins. The wedged mortise-and-tenon study
   remains research input for separate coupons, not the installed baseline.
6. Replaceable printed quarter-turn cross-keys and pins retain the joints; normal vertical load
   is carried through broad PETG bearing faces, not tiny latches.
7. Deck, front tied-arcade, and integral front/rear chord joints are arranged
   so one plane cannot split the entire shelf. The disconnected stitch-rail
   study is excluded from the installed baseline.
8. Fine fluting, dentils, rosettes, cavetto, and Art Deco detail remain
   nonstructural and replaceable. Only the compact capitals, mixed-action
   curved ribs, cassette chords, and X-corbels enter structural qualification.

No load rating exists until the configured coupons, full bay, wall mockup,
front-edge/asymmetric loading, 30-day creep observation, unloaded recovery, and
teardown inspection have passed with the confirmed printer and black PETG.
