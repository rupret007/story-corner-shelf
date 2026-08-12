# R11 physical qualification protocol

> This is a project gate plan, not a building-code test standard and not a
> substitute for a qualified structural review. **Current rating: 0 kg / 0 lb.**
> No test is authorized merely because it is described here. Never use the
> closet wall as the first fixture, and never test above a person, doorway,
> desk, electrical equipment, or valued property.
>
> R11 v1 hard-forces print, drilling-coordinate release, wall installation,
> and test-load authorization to false. This protocol defines possible future
> evidence; it cannot flip those flags.

Every loaded test requires an independently reviewed plan, purpose-built
freestanding fixture, calibrated instruments/masses, barricade, restraints,
written stop criteria, and remote observation wherever practical.

## Objectives, not ratings

- Distributed external contents objective: **45 kg / approximately 100 lb**.
- Front-edge point objective: **9 kg / approximately 20 lb**.
- Candidate proof multiplier: **1.5x**.
- Sustained-creep dwell objective: **1000 hours**.
- Creep environment: measured maximum representative service temperature plus
  **5 degrees C**.
- Current published rating: **0 kg / 0 lb** until every gate and independent
  review passes.

Measure the finished shelf dead mass `D`. The installed fixture already
contains `D`, so include its effect exactly once—never omit it and never add a
second full copy as ballast.

For the distributed proof objective:

```text
total demand = 1.5 * (D + 45 kg)
external ballast = 1.5 * (D + 45 kg) - D
```

For the separate point-proof objective under the same factor:

```text
external addition = 0.5D distributed in its representative pattern
                  + 13.5 kg at the selected front-edge location
```

The independent reviewer may specify other load combinations or factors, but
they must be written before testing. A target, CAD mass, section proxy, slicer
mass, catalog fastener value, attractive print, fit pass, short proof survival,
or destructive peak is not an allowable load.

## Gate 0 — generator, configuration, and process lock

1. Freeze source revision, normalized customization inputs, layout report,
   generated manifest, validation, neutral STL/3MF hashes, authored
   orientations, Bambu projects, and slice reports.
2. Confirm the measured first-wall result is six bays, seven supports, 254 mm
   pitch, four terminal halves (both halves of bay 0 and bay 5), eight regular
   halves (both halves of bays 1-4), six keystones, two blanks, one comb/hook,
   and 21 candidate screw/FW14 pairs. The kit contains 28 articles; two sockets
   limit the simultaneous installed state to 27.
3. Verify true saved-mesh overlap, bearing, net sections, walls, capture stops,
   reverse motions, volume, topology, bounds, and A1 mini fit. Source intent or
   a gross rectangular proxy is insufficient.
4. Record SUNLU standard black PETG ASIN `B0D1KC72YP`, spool lot, drying cycle,
   printer, physical 0.4 mm standard-flow nozzle, Textured PEI plate, profiles,
   ambient conditions, and every override.
5. Confirm `SUNLU PETG @BBL A1M 0.4 nozzle`, `0.20mm Strength @BBL A1M`,
   0.20 mm layers, six walls, 25% grid, five top, three bottom, Support Off,
   5 mm outer brim, and 0.1 mm gap.
6. Print reviewer-defined process coupons representing half-deck skin/rib
   bonding, reciprocal cross-lap orientation, support compression web, and
   screw/washer-land bearing before structural load articles.
7. Reject any part with crack, void, under-extrusion, warp, contamination,
   nonconforming dimensions, missing layers, slicer repair, manually modified
   structural fit, or untraceable process.

Gate 0 establishes configuration traceability only. It authorizes neither a
printer start nor a rating.

## Gate 1 — actual three-rib reciprocal cross-lap

Use one actual authored left half-deck and its actual right mate, not a
miniature or invented coupon.

1. Measure all three overlap lengths, lap thicknesses, broad bearing faces,
   positive shoulders, skins, rib walls, seams, and true net sections.
2. Join and separate the halves dry by the generated motion ten times.
3. Confirm all three broad faces and positive shoulders seat without force,
   friction-only retention, snap preload, glue, clamp pressure, shaving, or
   zero-gap seam forcing.
4. Record insertion/removal force qualitatively or with a reviewer-approved
   method, dust/shaving, whitening, cracks, edge damage, permanent looseness,
   and pre/post dimensions.

Forced fit, incomplete bearing, crack, progressive wear, growing looseness, or
loss of independent reverse motion blocks the architecture.

## Gate 2 — integral lower-slide-settle support capture and keystone

Use one conforming half-deck end, one actual support, and one actual bay
keystone. Keep the support off the wall and all printed bores empty.

1. Lower the half-deck with 2.0 mm clearance over the fixed lug heads.
2. Slide 32.0 mm wallward, then gravity-settle 2.0 mm into the higher terminal
   pocket behind the solid 8.4 mm roof/shoulder. Reverse by lifting 2.0 mm,
   sliding 32.0 mm outward, then lifting clear. Repeat both exact paths ten
   times.
3. Measure direct bearing length, stop engagement, capture clearance, local
   wall thickness, and any wear or permanent set.
4. Separately cycle the keystone ten times in the unloaded joined deck.
5. Confirm the keystone blocks only half-to-half X separation. It must not
   retain a half against a fixed support lug, pull a structural gap closed,
   preload the joint, bypass the support stop, or carry the vertical load path.
   It receives zero support-capture credit.

Partial bearing, rocking, stop bypass, snap/friction dependence, forced motion,
crack, wear, or irreversible assembly blocks the architecture and invalidates
the 28-article kit target.

## Gate 3 — complete actual one-bay structural article

Use two conforming authored half-decks, one keystone, and two actual supports.
Assemble dry on a flat table exactly as [ASSEMBLY.md](ASSEMBLY.md) specifies and
complete ten unloaded cycles.

Then move a fresh or demonstrably conforming bay to a purpose-built restrained
one-bay fixture inside the barricade. The fixture must reproduce the intended
broad support boundaries without pretending to qualify the wall connection.
Apply reviewer-defined tributary test load in 10%, 25%, 50%, 75%, and 100%
increments. At each step record:

- front and rear deflection;
- midpoint seam/cross-lap opening and slip;
- support rotation and direct bearing contact;
- capture and keystone movement;
- audible events, whitening, crack, and permanent set; and
- recovery after unloading.

The keystone, ornament, cable features, and friction receive zero sustained
vertical-load credit. Nonlinear/progressive displacement, incomplete recovery,
damage, loss of bearing, or adjacent-bay dependency stops the gate.

## Gate 4 — S0 cable service article

Use the actual far-left S0 support/bookend with fused two-socket receiver, two
flush blanks, and one comb/hook.

1. Confirm both sockets face inward with 0.4 mm clearance per face.
2. Cycle each module through the full 8 mm service lift/drop at least ten times
   in each socket.
3. Use representative cables only; never hang shelf-test mass from a module.
4. Verify cable bend, loop, snag, removal, outlet/plug, trim, and human-access
   clearances in a representative room mockup.
5. Confirm no intermediate support or inside-corner part has a receiver.

Cable parts receive zero structural credit. Receiver/root or clearance failure
blocks the furniture interface even if structural gates pass.

## Gate 5 — complete unloaded tabletop first wall

Only under a later print/test-capable revision and after Gates 0-4 pass,
assemble the 28-article target kit dry on a flat reference surface, with no
more than 27 articles installed at once:

- seven supports at 15.875, 269.875, 523.875, 777.875, 1031.875, 1285.875,
  and 1539.875 mm;
- 12 manifest-correct half-decks in six independent bays;
- six independently removable positive keystones; and
- S0's three supplied service modules, using only two at once: two blanks, or
  one blank plus one comb/hook.

Measure overall length, depth, thickness, rear/front straightness, top
flatness, every midpoint/support/endpoint seam, cross-lap engagement, direct
bearing, positive capture, endpoint/obstacle envelope, and cable service path.
Remove and reinstall every bay without releasing a neighbor.

No screws, wall, or load are used at Gate 5. Do not correct errors with heat,
scaling, sanding, drilling, filler, glue, force, or a hidden beam.

## Gate 6 — three-fastener support fixtures

After wall blocking and substrate are physically known and the connection plan
is independently reviewed, build four fresh sacrificial fixtures. Each uses one
exact printed support, three fresh GRK RSS 90306 candidates, exactly one fresh
FW14 washer per screw, actual representative substrate, and representative
blocking.

1. Inspect the three 7.0 mm printed bores and full-solid 27.025 mm OD lands at
   19.05, 79.375, and 139.7 mm below the shelf underside.
2. Measure received screw/washer dimensions and resolve the GRK thread-length
   documentation conflict.
3. Record pilot method, embedment, blocking properties, edge/end distances,
   group spacing, substrate, intervening layers, and controlled seating.
4. Never counterbore, countersink, stack washers, ream PETG, or crush the strap.
5. Apply reviewer-defined outward moment through the authored support capital
   while measuring group slip, support rotation, local indentation, bore
   growth, whitening, crack, blocking split, and permanent set.
6. Destructively test one fixture and preserve the other independent
   replicates as the reviewed plan specifies.

This gate consumes 12 fresh screws and 12 fresh washers. None may later be used
in the closet. The loose-washer/PETG connection is outside ESR-2442. Generic
hollow-wall anchors are not a fallback.

## Gate 7 — complete framed-wall mockup and service objectives

Build a fresh 1555.75 mm freestanding wall reproducing accepted continuous
blocking, substrate, trim stand-off, screw group, pilot/seating procedure, and
the complete 28-article kit target with 27 articles installed. Use 21 fresh
GRK candidates and 21 fresh FW14 washers.

1. Measure finished shelf dead mass `D`.
2. Instrument exactly 19 stations: rear and front of all six bay midpoints plus
   all seven supports.
3. Apply external distributed contents mass symmetrically in 10% increments to
   45 kg while the fixture already supplies `D`.
4. Hold the service objective for 24 hours; record all planned measurements.
5. Unload and record recovery at 1 hour and 24 hours.
6. On a conforming/recovered fixture, apply the separate 9 kg front-edge point
   objective at each reviewer-defined bay midpoint, one position at a time.

Stop for crack, whitening, fastener slip, bore/land damage, seam opening,
cross-lap or capture walkout, support rotation, progressive/nonlinear
deflection, loss of bearing, blocking damage, cable interference, or failed
recovery.

## Gate 8 — proof objectives

On a conforming barricaded fixture, apply the distributed and front-edge proof
cases separately unless the reviewer specifies a combined case.

Distributed external ballast:

```text
1.5 * (D + 45 kg) - D
```

Point proof external additions under the candidate 1.5 rule:

```text
0.5D distributed representatively + 13.5 kg at one selected front-edge bay
```

Apply gradually, hold each completed case for one hour, record all 19 stations
and connection/joinery observations, unload, and demonstrate reviewer-defined
recovery before another location. A proof pass is not a service rating and
does not replace creep testing.

## Gate 9 — 1000-hour elevated-temperature creep and recovery

Use a separate fresh conforming wall with 21 fresh hardware pairs. First
measure and freeze the maximum representative service temperature. Control the
test environment at that maximum plus 5 degrees C.

The shelf already supplies `D`; apply **45 kg external distributed contents
ballast** for 1000 hours. Log temperature, humidity, front/rear deflection,
support rotation, connection slip, cross-lap/capture slip, seam opening, and
keystone movement at minimum after 1 hour, 24 hours, 7 days, 14 days, 30 days,
and 1000 hours. After unloading, record recovery after 1 hour, 24 hours, and
7 days.

Progressive creep, temperature-control loss, failure to stabilize, incomplete
reviewer-defined recovery, crack, whitening, fastener movement, joint walkout,
or hidden damage blocks release. Passing does not authorize service above the
measured maximum temperature.

## Gate 10 — fresh destructive wall and independent review

Destructively test a separate fresh complete wall with 21 fresh hardware pairs
inside the barricade. Record applied load, all 19 displacement stations, first
failure, and complete failure sequence. Never convert one peak value into a
rating or average a weak bay with a stronger bay.

The independent reviewer must consider at least:

- lowest credible result and failure mode;
- PETG anisotropy, lot/process variation, environment, fatigue, impact, and
  sustained creep;
- three-rib cross-laps, integral captures, direct bearing, keystone retention,
  independent-bay/progressive-failure behavior;
- front-edge point, torsion, accidental eccentric, and snag loads;
- complete grouped screw/washer/PETG/substrate/blocking connection;
- dead mass, permanent set, recovery, inspection access, and damage detection;
  and
- explicit safety factor, allowable load, installation conditions, inspection
  interval, and retirement criteria.

Only that review may create a nonzero allowable. Until then the R11 repository
and every generated artifact remain **0 kg / 0 lb, no wall installation**.
