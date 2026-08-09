# Qualification and sustained-creep test protocol

## Purpose and limits

This protocol is a staged evidence plan for one exact Story Corner r6 material,
printer, profile, orientation, wall build-up, fastener, geometry, environment,
and load case. It does not itself establish a load rating. The project remains
**experimental and unrated**, and no overhead use is permitted while the target
load, deflection limit, permanent-set limit, and actual wall connection remain
unconfirmed.

The shelf body is all printed black PETG. The only nonprinted installed
boundary is suitable metal structural screws with integral heads or compatible
metal washers into verified wood studs or purpose-installed blocking. Test the
actual screws and representative wall build-up; do not substitute printed or
primary hollow-wall anchors.

## 1. Freeze the test article

Create a signed test-record header before printing:

| Field | Record |
| --- | --- |
| Configuration/manifest digest | |
| Part/package IDs | |
| Printer model and serial | |
| Nozzle diameter/material/hours | |
| Build plate | |
| Slicer/version/profile export digest | |
| Black-PETG brand/product/color/lot | |
| Filament drying method, time, temperature, and device | |
| Drying/storage record and measured storage RH | |
| Saved part orientations used without scaling | |
| Wall finish/type/thickness | |
| Lower-level through/return support records | |
| Upper-level through/return support records | |
| Stud/blocking material, dimensions, and verification method | |
| Screw/head-or-washer product and dimensions | |
| Thread embedment and driver bit/socket | |
| Maximum driver OD and required straight-approach envelope | |
| Test temperature/RH range | |
| Target contents load and distribution | |
| Test-load increments and maximum | |
| Deflection stop limit | |
| Permanent-set stop limit | |
| Approved emergency unload method | |
| Reviewer/date | |

Any change to a frozen field creates a new test article. Do not transfer results
between materials, nozzle sizes, orientations, profiles, walls, fasteners,
geometry revisions, or target load cases without a documented equivalence
basis and review.

## 2. Safety setup

Use a guarded bench or low sacrificial wall mockup, not the final overhead
closet location. Reproduce the real wall finish, verified wood stud/blocking,
fastener, head/washer bearing, edge distances, and thread embedment. Keep people,
pets, vehicles, and valuables outside the failure zone. Restrain test weights
against sliding and add/remove them from a protected position.

Document the unloaded specimen with orthogonal photographs and a scale.
Establish fixed measurement points at each support, crown, seam, front-edge
midspan, rear chord, wall plate, screw seat, and corner. Use a repeatable
indicator, gauge, or fixed-camera target with resolution appropriate to the
written stop limit. Log temperature and humidity continuously or at every
reading.

## 3. Immediate stop conditions

Stop the test, unload from a protected position, and mark the article failed if
any of these occurs:

- audible cracking or layer whitening;
- pin or cross-key migration, or hole ovalization;
- screw-head/washer embedment or PETG crushing;
- joint opening that consumes the movement reserve;
- accelerating front-edge deflection;
- corbel rotation, wall damage, or fastener movement;
- loss of required cross-key, bridge, or pin access;
- any written deflection, permanent-set, temperature, or load limit is exceeded;
- any unexpected behavior whose cause is unknown.

Do not tighten, shim, glue, repin, or otherwise repair a loaded specimen and
continue the same test. Record the failure load/time and preserve the article
for teardown.

## 4. Stage A — fit and material coupons

Print with the intended production material/profile/orientation:

1. 0.2 / 0.3 / 0.4 / 0.5 mm clearance matrix;
2. representative pins, double-shear holes, pull features, and keepers;
3. cassette-top tenon/receiver/quarter-turn cross-key interface;
4. spring tenon/receiver/quarter-turn cross-key interface;
5. upward crown-bridge keyway and fixed-right pin interface;
6. fixed-crown diaphragm keeper rear bayonet, its underside indexed pin, and
   the visible-front fixed tie with its q-axis indexed pin;
7. tight terminal and 1.2 mm-travel floating locator pockets over the integral
   corbel cap, plus elongated cassette locks;
8. ornament connector pair, which receives zero structural credit;
9. wall-screw bearing coupon generated around the actual screw and metal
   head/washer.

For each coupon record as-printed dimensions, fit force or qualitative class,
repeatability over at least ten assemble/disassemble cycles, whitening,
cracking, hole growth, debris, and tool access. A qualified fit must seat on its
broad positive shoulder without hammering and must be removable using the
intended visible-front/underside path. Freeze one centralized clearance only
after repeatable results; never tune by slicer scaling.

## 5. Stage B — component tests

Test separately:

- one full two-skin cassette plus integral-cap locators, locks, fixed/floating
  seam, keeper, and crown-tie interfaces;
- one complete 3:4:5 X-corbel with its integral full-width bearing cap, locks,
  and actual wall screws on the representative mockup;
- one crown pair, upward bridge, fixed-right anti-drop pin, and three cross-keys per
  half;
- fixed and floating cassette seams, positive key retention, and the complete
  1.2 mm integral-cap/lock thermal travel;
- the two-piece nonstructural corner finish under no load.

Use bearing/contact paper, witness marks, or comparable evidence to confirm
load reaches broad pads and integral corbel caps rather than hanging on cross-keys, pins, keys,
ornament, or interference. Production wall bores remain blocked until this
wall-bearing work uses the approved exact fastener geometry.

## 6. Stage C — worst-case full bay

Build one complete through-arm bay at the nominal worst-case 241.935 mm span on
the sacrificial wall. Include both half cassettes, both bounding X-corbels with
their integral caps and locks, both arcade halves, four top quarter-turn
cross-keys, two spring quarter-turn cross-keys,
three crown diaphragm keys, their one-rear-bayonet-tongue keeper strip and
separate underside indexed pin, the visible-front crown tie and its separate
indexed pin, the upward crown bridge, its one fixed-right pin, and the representative
floating-pier seam class. Preserve all saved print orientations. The baseline
has no stitch rail.

### Arch-on / arch-off comparison

Before proof or creep loading, conduct a matched low-load elastic comparison:

1. preload the complete bay only enough to settle contacts; unload and zero;
2. apply the same low, distributed load with the curved tied-frame installed;
3. record deflection and joint movement after the same dwell;
4. fully unload and allow the same recovery dwell;
5. repeat using an approved comparison configuration that removes the curved
   frame's contribution without changing support, deck, wall, seam, or load
   geometry;
6. repeat enough cycles to distinguish measurement scatter and seating effects;
7. compare stiffness, recovery, local strain signs, and failure progression.

If the curved frame provides no repeatable benefit, or worsens behavior,
reclassify it as decoration and redesign the candidate load path. Ancient form
or visual elegance is not evidence of structural benefit.

### Cyclic service screening

After the comparison and inspection, run a written number of low-load service
cycles below the later sustained-test load. Record progressive pin/receiver
wear, hysteresis, residual deflection, keeper/key migration, floating-seam
travel, and fastener seating. Set the
cycle count before testing; do not stop at a favorable observation.

## 7. Stage D — unloaded full L corner fit

Dry-fit one full L level with no service load. Verify:

- 6 through bays + 3 return bays = 9;
- seven through + four return independent supports;
- through cassette ownership of the 6 x 6 in corner;
- return start, outer clearances, 1.2 mm arm gap, and residual clearance;
- no perpendicular-corbel collision;
- nine fixed crown seams and seven floating supported-pier seams;
- all nine crown diaphragm keepers and visible-front ties positively retained
  by their correctly indexed underside/front quarter-turn pins;
- all seven floating-pier integral caps trapping their three keys while
  preserving the complete 1.2 mm axial travel;
- no stitch rail, rail pin, end tie, or other hidden movement bypass;
- all cross-keys and indexed pins have at least 75 mm straight service access;
- corner ornament floats and creates no rigid L tie;
- no element couples an upper and lower shelf level.

Repeat the dry fit against the distinct lower- and upper-elevation wall-width,
support-center, framing, and obstruction records, or fixtures that reproduce
each record. A lower-level support record cannot stand in for the upper level,
even when the nominal centers match. Artist-rendering appearance is not an
acceptance criterion.

## 8. Stage E — proof-case definition and incremental observations

Do not begin until target contents and their placement are measured. A
competent reviewer must set the test load, increments, dwell, factor/basis,
deflection stop, permanent-set stop, temperature limits, and emergency unload
method in writing. This protocol intentionally supplies no numerical load or
safety factor.

Apply stabilized increments to the full bay or a representative full-level
fixture. At every increment and after the written dwell, record:

- applied mass and exact distribution;
- front-edge and midspan deflection;
- wall-plate rotation and screw-seat displacement;
- crown, cassette, integral-cap, keeper, and floating-seam movement;
- temperature/humidity;
- photographs and noises/visual changes.

The written plan must contain four separately identified nondestructive load
cases. Use separate accepted articles when prior loading could contaminate a
later result; otherwise predeclare the order, unloading, recovery dwell, and
inspection between cases. Never infer one case from another.

### Distributed-load case

Apply the documented distribution over the documented footprint. Record every
individual weight and its station. A center weight or a few point weights do
not establish a distributed-load result unless a qualified spreader fixture
creates and documents the intended distribution.

### Front-edge-load case

Apply the written load along the selected front-edge segment without allowing
the fixture to bear on the wall, corbels, or rear chord. Record front-versus-
rear differential movement, wall-plate rotation, and local cassette response.

### Crown-point-load case

Apply the written crown-point load at the preselected worst fixed crown seam
through a documented small bearing pad that prevents local puncture without
spreading the load into neighboring bays. Record crown opening, bridge and
keeper movement, front-tie movement, cassette deflection, and both adjacent
support reactions. The bridge pin, indexed pins, and cross-keys receive no
vertical-load credit. This is a distinct case; a midspan distributed reading
does not satisfy it.

### Asymmetric/torsional-load case

Apply the written eccentric load to the preselected side and front/rear offset
so the article develops both asymmetric bending and torsion. Record left/right
and front/rear differential deflection, cassette twist, supported-pier travel,
corner gap, corbel rotation, and wall-fastener motion. Repeat the mirrored case
if the geometry, wall, or support records are not demonstrably symmetric. A
centered front-edge case does not satisfy this torsional case.

Fully unload, recover, and inspect as the written plan requires after every
case. Any stop sign ends the case and disqualifies that article from later
nondestructive or sustained-load evidence.

## 9. Stage F — whole-article thermal cycling

Use one complete, independently wall-fastened L-level article on a guarded
fixture: all six through bays, three return bays, eleven X-corbels and wall
connections, nine fixed crown seams, seven floating supported-pier seams, and
the nonstructural corner transition must be present. An isolated coupon,
component, or one-bay specimen cannot close this whole-article gate.

Before testing, a competent reviewer must write the minimum and maximum service
temperatures, ramp rate, dwell needed for the entire article to equilibrate,
cycle count, humidity control, preload (including zero if selected), sensor
locations, acceptance limits, and emergency stop method. First record an
unloaded room-temperature datum. At every hot and cold dwell, record the
article temperature, ambient temperature/RH, all fixed/floating seam positions,
front/rear and left/right deflection, corner gap, cap/lock travel, pin/keeper
position, wall-seat motion, and photographs. Return to the datum condition and
record recovery after each cycle.

Do not choose the number of cycles after seeing favorable behavior. Any
binding, consumed 1.2 mm movement reserve, fastener motion, progressive set,
loss of service access, or other stop sign fails the test. If a full-L guarded
thermal fixture is unavailable, record this stage as incomplete; coupon thermal
cycling is useful screening but is not the whole-article substitute.

## 10. Stage G — sustained-load creep

Use an undamaged, accepted article with the exact qualified material, profile,
wall, fastener, environment, and chosen sustained load. Establish an unloaded
baseline and a time-zero loaded reading. Maintain load and environmental logs
without adjustments intended to improve the result.

Required checkpoints:

| Checkpoint | Required record |
| --- | --- |
| 1 hour | All measurement points, temperature/RH, photographs, joint/fastener inspection |
| 24 hours | Same data; compare rate of change to time zero and 1 hour |
| 7 days | Same data; inspect floating reserves, pin/cross-key position, and wall seats |
| 30 days | Initial creep-screen decision; do not call this a load rating |
| 90 days | Minimum duration before any load claim may even be considered |

Take additional readings whenever temperature changes materially or a trend
accelerates. A 30-day screening specimen may be a separate early development
test. If the 30-day article is intended to continue to the 90-day checkpoint,
do not unload or reset it at day 30.

For every interval calculate and graph deflection change and rate. Any
accelerating deflection, consumed movement reserve, fastener motion, or stop
condition fails the test even if the article has not broken.

## 11. Stage H — 72-hour unloaded recovery and teardown

After the 90-day reading, remove the load safely and record immediate recovery.
Keep the article unloaded and undisturbed, then record the same points at a
minimum of 1 hour, 24 hours, and **72 hours**. Compare permanent set to the
prewritten acceptance limit.

After the 72-hour reading, fully disassemble in the documented order and
inspect with photographs and measurements:

- cassette skins, coffer ribs, perimeter walls, integral corbel caps, and
  compression pads;
- all top/spring tenons, receivers, cross-keys, and access paths;
- crown bridge rails, hard stops, right pin, bosses, and return ear;
- fixed-crown entablature ties and their indexed pins, one-rear-bayonet-tongue
  diaphragm keeper strips and their separate indexed pins, and fixed/elongated
  diaphragm keys (no separate front-entablature key exists at a floating pier);
- every tight/elongated integral-cap pocket, lock seat, keeper catch, and movement
  reserve;
- X-brace roots, crossing boss, wall plate, screw seats, and printed layers;
- actual screws, heads/washers, verified wood, and wall finish;
- isolated ornament only for clearance/contact evidence, never capacity.

Section sacrificial parts if needed to reveal internal layer separation or
crushing. Record hole growth, whitening, cracks, polished bearing, fretting,
permanent deformation, and hidden contact. Preserve failed parts and raw data.

## 12. Stage I — destructive load-to-failure, separate specimen

Fabricate and permanently label a **separate matched destructive specimen**.
It must use the same frozen geometry, material lot and drying method, printer,
profile, saved orientations, wall build-up, fasteners, and environmental basis.
It may not be the article retained for arch-on/arch-off comparison, proof,
thermal cycling, sustained creep, recovery, installation, or display. At
minimum it must be a complete worst-case bay; the competent reviewer must
require a complete L article when bay-only failure cannot exercise the selected
corner or torsional mode.

In a guarded load frame or sacrificial wall fixture, apply the predeclared
worst-case distribution and increase load through logged increments and dwells
until an immediate stop condition or actual loss of load-carrying function.
Measure load with a calibrated device and record deflection, time, temperature,
all visible damage, the first irreversible event, peak measured load, failure
location, and failure mode. Unload only by the protected emergency method.
Preserve and photograph the failed article before teardown.

This destructive result characterizes one matched specimen and helps reveal a
failure mode. It is not a proof load, a safety factor, permission to install,
or a load rating, and it may not be averaged into the nondestructive or creep
record.

## 13. Acceptance and reporting

A complete record contains raw data, photographs, environment log, frozen
profile/material/hardware evidence, all deviations, separate crown-point and
asymmetric/torsional results, the whole-article thermal-cycle log, the separate
destructive specimen record, failed specimens, plots, recovery, teardown, and
reviewer sign-off. Software validation and watertight meshes are supporting
evidence only.

At least 30 days is required for initial prototype evaluation. At least 90 days
plus 72 hours recovery and teardown is required before any load claim may be
considered. Passing those gates still does not automatically create a rating.
Any rating must state the exact geometry, wall, fastener, printer, material,
profile, temperature range, load distribution, acceptance criteria, sample
size, safety basis, and excluded uses, and should receive competent engineering
review.
