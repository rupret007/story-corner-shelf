# R10 physical qualification protocol

> This is a project gate, not a building-code test standard and not a substitute
> for a qualified structural review. Perform every load test, including the
> one-bay gate, only in a purpose-built freestanding fixture inside a controlled,
> barricaded area with remote observation wherever practical. Full-wall tests
> require the authored framed-wall mockup. Never make the real closet wall the
> first test and never test above a person, doorway, electrical equipment, desk,
> or valued property.

## Target, measurement limits, and rating rule

- Distributed contents target: **45 kg / approximately 100 lb**.
- Front-edge point-load target: **9 kg / approximately 20 lb**.
- Proof multiplier: **1.5x**.
- Sustained-creep target dwell: **1000 hours**.
- Qualification temperature: the measured maximum service temperature plus
  **5 degrees C**. Measure and freeze the maximum service temperature before
  authorizing the creep article.
- Measure finished shelf dead mass and include its physical effect exactly once
  in every applicable fixture demand. Because the shelf is already on the
  fixture, never add a second copy of its dead mass as ballast.
- Current and published rating remains **0 kg / 0 lb** until all gates pass and
  an independent structural reviewer defines a final allowable load.

Targets are experiment inputs, not ratings. Do not infer capacity from CAD
mass, section proxies, slicer mass, catalog fastener values, successful fit,
short proof survival, or one destructive peak.

Before testing, write a measurement plan with fixed gauge locations, calibrated
instruments, sampling intervals, stop criteria, and acceptance limits approved
by the structural reviewer. Until those limits exist, a visually successful
test is still incomplete.

## Gate 0—configuration and process lock

1. Freeze the exact source commit, generated-file manifest, STL/3MF hashes,
   Bambu project, saved orientation, scale, and slice report for every article.
2. Record SUNLU standard black PETG ASIN `B0D1KC72YP`, spool lot, drying cycle,
   printer, physical 0.4 mm nozzle, Textured PEI plate, filament/process
   profiles, ambient temperature, and every override.
3. Confirm six walls, 25% grid, five top layers, three bottom layers, Support
   Off, 5 mm outer brim, and 0.1 mm brim-object gap.
4. Print material/process coupons representing wall-strap screw bearing,
   compression-web orientation, cassette skin/web bonding, and splice-log layer
   orientation.
5. Reject a part with cracks, voids, under-extrusion, warp, contamination,
   nonconforming dimensions, missing layers, slicer repair, or any manually
   reamed/sanded structural interface.

Gate 0 establishes repeatability only. It creates no shelf rating.

## Gate 1—actual Lincoln-log midpoint interface

Use the exact one-bay articles rather than an invented miniaturized coupon:
left cassette half, right cassette half, one splice log, and its independent
flush-capped retainer. These are the smallest qualification-bundle candidate
files that preserve the full-scale intended dovetail, positive body shoulder, 0.4
mm-per-face clearance, midpoint keyway, cap, and saved layer orientation.

1. Measure every critical width, height, engagement length, and clearance before
   assembly.
2. Assemble and disassemble each dry interface ten times by hand. Never hammer,
   pry, heat, lubricate, or force it.
3. Confirm that each log reaches its positive shoulder, the key seats without
   preload, and gravity/normal handling cannot cause uncommanded walkout.
4. Record insertion/removal behavior, PETG dust or shaving, whitening, cracks,
   edge damage, permanent looseness, and dimensions after cycling.

Any forced fit, snap dependence, wedge preload, friction-only retention,
cracking, increasing looseness, or loss of positive shoulder contact blocks the
architecture.

## Gate 2—actual one-bay structural article

Print two regular cassette halves, three splice logs, three independent log
retainers, two bay-local support retainers, and two supports, one part per plate in the authored
orientation. This must use the actual shelf geometry rather than a visual
mockup.

Assemble dry on a flat table:

1. slide the rear, center, and front logs into one half until all positive
   shoulders seat;
2. with the mating half still absent, lower one independent retainer through
   each left-half top access into its exposed log notch; its integrated head
   must close the access without debris-catching proud edges;
3. slide the mating half over the exposed log and retainer ends without
   twisting or force so its closed top captures all three keys;
4. place cassette ends directly on the broad half-lands of both support
   capitals, insert one bay-local retainer straight from the front at each
   contact, and shift it exactly 2.4 mm toward that bay so its rear dog sits
   behind the positive shoulder while the front paddle remains 4.0 mm proud
   and hand-graspable; and
5. verify seam closure, flush key closures, positive support-key capture, full
   bearing, square/flat geometry, and independent disassembly without
   disturbing another bay. Disassembly begins by shifting each support key
   2.4 mm away from its bay before pulling it straight forward.

Cycle the bay ten times unloaded. Then move it to a purpose-built,
mechanically restrained one-bay fixture inside the controlled barricade; an
ordinary table is not a load fixture. Observe remotely wherever practical and
load it in 10%, 25%, 50%, 75%, and 100% increments of the reviewer-defined
one-bay tributary test load. At every increment record front/rear deflection,
cassette seam opening, log slip, support rotation, bearing contact, audible
events, whitening, cracks, and recovery after unloading.

The independent retainers, shallow capital locators, anti-lift features, and ornament
receive no sustained vertical-load credit. Nonlinear displacement, progressive
slip, incomplete recovery, damage, or loss of direct bearing stops the test.

## Gate 3—outer-bookend cable-service article

Print the first-wall far-left bookend with its fused two-socket receiver, two
flush blanks, and one multi-cable comb/hook.

1. Confirm both sockets face inward and each has 0.4 mm clearance per face.
2. Cycle each module through the full 8 mm service lift/drop at least ten times.
3. Load the comb/hook only with representative cables, never shelf-test mass.
4. Verify cord bend radius, loop clearance, snag clearance, module removal,
   outlet/plug access, and appearance with both sockets blanked.
5. Confirm no cable hardware exists on intermediate supports or at the inside
   corner.

Cable parts receive zero structural credit. Failure here blocks the furniture
interface even if the one-bay structure passes.

## Gate 4—complete tabletop first-wall set

Print the remaining conforming parts only after Gates 0-3 pass. Assemble all
seven supports and six independent bays dry on a flat reference surface.

1. Confirm exact support centers at 15.875, 269.875, 523.875, 777.875,
   1031.875, 1285.875, and 1539.875 mm from the left wall endpoint.
2. Confirm the support faces terminate flush at 0 and 1555.75 mm.
3. Measure overall length, depth, thickness, rear/front straightness, top
   flatness, every 0.35 mm midpoint/support-line seam, both 0.35 mm endpoint
   clearances, and direct bearing at all support capitals.
4. Remove and reinstall each bay independently. One bay or loose key must not
   release or unzip an adjacent bay.
5. Confirm all 18 log retainers and all 12 support retainers are seated,
   removable by the authored motion, and leave the bearing lands above them in
   full contact.
6. Confirm the far-left cable receiver, flush blanks, and comb/hook preserve
   the measured outlet and intended trim/service clearances.

Do not adapt a dimensional error with adhesive, filler, scaling, heat, forced
assembly, manual drilling, or a hidden beam. Revise the authored geometry and
repeat the affected gates.

## Gate 5—three-fastener wall-support fixtures

Only after continuous blocking and substrate are physically known, build
exactly four fresh sacrificial fixtures using the exact printed support, three GRK RSS
90306 candidates, one listed USS washer per screw, actual substrate, and
representative blocking.

1. Inspect every 7.0 mm printed bore and its full-solid 27.025 mm
   outer-diameter washer land before seating. Confirm candidate drops of 19.05,
   79.375, and 139.7 mm below the shelf underside.
2. Install without countersinking, stacked washers, bore reaming, or PETG
   crushing. Counterbores are forbidden. Record pilot method, embedment,
   edge/end distances, spacing, and controlled final seating. Treat the printed
   bores as fixture candidates, never as a closet-wall drilling schedule.
3. Apply the reviewer-defined outward moment through the authored support
   capital.
4. Measure screw-group slip, support rotation, local indentation, whitening,
   bore growth, cracks, blocking split, and permanent set at the planned
   intervals.
5. Destructively test one of the four fixtures and record first failure mode
   and sequence. The other three remain independent replicates; no fixture or
   hardware from this gate may be installed in the closet.

Gate 5 therefore reserves 12 exact screws and 12 exact washers. Before driving
one, measure the received `90306` dimensions and resolve the current GRK
thread-length documentation conflict. The GRK head / loose FW14 washer / PETG
stack is outside ESR-2442 and needs its own accepted calculation and test plan.

Screw withdrawal, blocking/substrate damage, increasing slip, PETG cracking,
washer-land damage, uncontrolled rotation, or an unreviewed failure mode blocks
the connection. Generic hollow-wall anchors are not a fallback.

## Gate 6—complete framed-wall mockup

Build a fresh full 61.25 in assembly against a freestanding mock wall that
reproduces the accepted continuous blocking, substrate, trim stand-off, screw
group, and installation process. Use seven supports, all six independent bays,
21 GRK candidates, and exactly one washer per screw.

1. Measure the finished shelf dead mass.
2. Instrument exactly 19 stations: rear and front of all six bay midpoints
   plus all seven supports.
3. Apply distributed masses symmetrically in 10% increments to the 45 kg
   contents target, always including dead mass in the fixture demand.
4. Hold the target for 24 hours while recording all planned measurements.
5. Unload and record recovery at 1 hour and 24 hours.
6. On a conforming fixture, apply the separate 9 kg point mass at each
   front-edge bay midpoint, one position at a time, with the dead-load effect
   included.

Stop immediately for any crack, whitening, fastener slip, bore growth,
permanent seam opening, support rotation, progressive/nonlinear deflection,
loss of bearing, blocking damage, or cable/ornament interference.

## Gate 7—proof loads

On a conforming barricaded mockup, run separate reviewer-approved distributed
and front-edge point proof cases. Do not assume that the two targets act
simultaneously unless the reviewer explicitly requires and defines that
additional case.

For the distributed case, calculate total proof demand as
`1.5 x (dead mass + contents target)`. The shelf already supplies its dead
mass, so apply external ballast gradually according to:

```text
1.5 x (measured finished-shelf dead mass + 45 kg contents)
- measured finished-shelf dead mass
```

For the point case, use a fresh or fully recovered conforming fixture. If the
same 1.5 factor applies to the complete dead-plus-point demand, the shelf itself
already supplies `D` and the external proof additions are therefore:

```text
0.5 x measured finished-shelf dead mass, distributed in its representative pattern
+ 1.5 x 9 kg = 13.5 kg at the selected front-edge bay location
```

Apply the point mass at each reviewer-defined bay location, one location at a
time. A reviewer may prescribe different dead/point load factors, but they must
be written before the test; never silently omit the extra `0.5D`, double the
existing `D`, or average a weak bay with a stronger one.

Hold each complete proof case for one hour with remote observation where
practical. Follow the same stop criteria and record complete recovery between
cases. A proof pass is not a service rating and cannot replace the
sustained-creep gate.

## Gate 8—1000-hour elevated-temperature creep and recovery

Measure and freeze the maximum temperature expected in representative service.
Use a fresh conforming assembly in a controlled environment at that measured
maximum plus 5 degrees C. The physical shelf already supplies its measured
dead mass; apply **45 kg of external distributed contents ballast** so the
total fixture demand is measured shelf dead mass plus 45 kg for 1000 hours.
Log temperature, humidity,
front/rear deflection, support rotation, connection slip, log slip, and seam
opening at minimum after 1 hour, 24 hours, 7 days, 14 days, 30 days, and at the
1000-hour endpoint.

After unloading, record recovery after 1 hour, 24 hours, and 7 days.
Progressive creep, loss of temperature control, failure to stabilize,
incomplete reviewer-defined recovery, cracks, whitening, fastener movement,
joint walkout, or hidden damage blocks release. Passing at the qualification
temperature does not authorize service above the measured maximum temperature.

## Gate 9—complete destructive test and independent review

Destructively test a separate fresh full assembly in a barricaded fixture.
Record load, displacement, the first failure, and the complete failure sequence.
Do not convert one peak value into a rating or average a favorable failure with
an unfavorable one.

The independent reviewer must consider at least:

- the lowest credible result and its failure mode;
- PETG anisotropy, lot/process variation, temperature, and sustained creep;
- front-edge point, impact, torsion, and accidental eccentric loads;
- the complete grouped wall connection, blocking, and substrate;
- dead load and permanent-set/recovery evidence;
- progressive-failure behavior and independent-bay replaceability; and
- an explicit safety factor and maintenance/inspection interval.

Only the reviewer may define a nonzero allowable load and the installation
conditions attached to it. Until then, the repository remains **0 kg / 0 lb,
no wall installation**.
