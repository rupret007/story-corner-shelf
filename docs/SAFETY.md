# Safety

## Experimental and unrated

Story Corner r6 has **no tested load rating** and is **not approved for
overhead use**. The current files are geometry-development/model-only artifacts.
They do not prove that the shelf, wall, fasteners, printed layers, joints, or
PETG will carry closet contents safely.

Every shelf-body part is intended to be printed in black PETG. The only
nonprinted installation boundary is suitable metal structural screws with
integral heads or compatible metal washers into verified wood studs or
purpose-installed blocking. “All printed shelf” does not mean hardware-free
wall attachment.

## Hard prohibitions

Do not:

- install r6 above people, pets, beds, seating, doors, valuable equipment, or
  an occupied work area before qualification;
- use printed wall anchors or primary hollow-wall anchors;
- assume an outlet, stud finder indication, old screw, trim nail, or wall edge
  proves structural framing;
- drill development X-corbels or copy provisional screw stations into a wall;
- use production wall holes until exact fastener and wall geometry has been
  measured, regenerated, and wall-mockup tested;
- substitute structural adhesive for a missing bearing, screw, pin, cross-key,
  integral corbel cap, keeper, or verified framing connection;
- add a hidden metal shelf member and still describe the design as r6;
- use a tiny latch, key, cross-key, or pin as the intentional vertical load path;
- rigidly join the two L arms at the corner or tie the two shelf levels
  vertically;
- use embedded G-code, inherited slicer settings, or the supplied reference
  3MF profiles as a production recipe;
- scale structural meshes in a slicer to fit a different wall or printer;
- claim capacity from a material datasheet, slicer estimate, short proof test,
  simulation, artist rendering, or another printed shelf;
- load a part showing cracks, layer whitening, warping, poor fusion, burned or
  wet filament artifacts, damaged holes, or forced joinery.

## Wall and electrical risk

Production bores are intentionally blocked because screw and utility geometry
is unknown. Before any drilling, verify the wall finish, finish thickness,
framing material and thickness, station centers and widths, and a documented
method for avoiding electrical, plumbing, and other concealed services. The
nearby outlet makes utility verification especially important. De-energize
relevant circuits and use a qualified electrician or other competent trade
professional where required. Do not open an electrical box or probe a wall
cavity unless you are qualified and permitted to do so.

The regular 3/6 support rhythm requires verified continuous wood blocking
unless all 11 generated support stations per level independently land on
verified framing. If they do not, install suitable blocking or regenerate the
structural layout. Drywall, plaster, or an optional printed study rail is not a
substitute for the required framing in the active design.

The exact structural screw must be selected for the verified substrate and
reviewed for required embedment, edge distance, head/washer bearing, corrosion
environment, and driver access. Do not infer screw suitability from diameter
alone.

## PETG-specific risk

FFF PETG is anisotropic, process-sensitive, temperature-sensitive, and subject
to creep. Apparent short-term stiffness can decay under sustained load.
Printer, nozzle, layer bonding, moisture, extrusion, orientation, cooling,
pigment, product formulation, batch, and service temperature all matter. A
result for one material/profile combination does not qualify another.

Keep stored loads away from heat sources and direct solar heating. Record the
actual closet temperature range during testing. Do not expose the shelf to a
temperature or chemical environment outside the qualified range. If the
closet becomes hotter than the tested service condition, unload the shelf
until it is requalified.

## Safe test setup

Conduct coupons and full-bay tests on a guarded bench or low sacrificial wall
mockup. Exclude people and pets from the fall zone. Use stable, restrained test
weights and add them remotely or from outside the likely failure path. Wear
appropriate eye and foot protection. Never stand beneath or in front of a
loaded experimental bay.

Set the target test load, load increments, deflection stop limit, permanent-set
limit, and emergency removal method in writing before adding load. Those
values are intentionally blank in the configuration until the intended
contents and review basis are known.

Stop, unload from a protected position, and quarantine the specimen if any of
the following occurs:

- audible cracking or layer whitening;
- pin or cross-key migration, or hole ovalization;
- screw-head embedment, PETG crushing, or wall damage;
- joint opening that consumes its movement reserve;
- accelerating front-edge deflection;
- corbel rotation or fastener movement;
- loss of the required 75 mm service path;
- a new noise, visible defect, or measurement trend whose cause is uncertain.

An emergency stop is a failed test, not a near pass.

## Installation and use controls

After qualification, install the upper level first and fully inspect all
wall-fastener, cross-key, spring, crown-pin, keeper, floating seam, and removal access before
installing the lower level. Every level needs its own 7 + 4 support set. Keep
all visible-front and open-underside service paths clear. Ornament must remain
removable and may not conceal an inaccessible structural retainer.

Distribute stored objects as established by the qualified test. Avoid impact,
climbing, hanging, pulling on the front edge, concentrated point loads, and
placing a bin that projects beyond the qualified depth. Do not let children
use the shelf as a step or handhold.

Establish an inspection log. At minimum, inspect after installation and first
loading, after temperature excursions, at the qualification checkpoints, and
periodically thereafter. Compare front-edge deflection to the recorded
baseline. Fully unload before removing a pin, cross-key, bridge, cassette, corbel,
or screw.

Immediately unload and take the shelf out of service after impact, wall work,
water exposure, a moved fastener, damaged PETG, unexplained deflection, or a
change in intended load. Replace parts only with parts made and requalified
under the same controlled material/profile basis.

## Qualification does not erase uncertainty

The required 1 hour, 24 hour, 7 day, 30 day, and 90 day observations plus 72
hour unloaded recovery and teardown reduce uncertainty for the tested specimen.
They do not automatically establish a universal rating. A competent review of
the wall, fastener, test evidence, load case, environment, and desired safety
margin remains necessary before overhead use or any published load claim.
