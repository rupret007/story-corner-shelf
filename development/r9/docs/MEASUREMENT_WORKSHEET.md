# R9 field measurement worksheet

## Purpose and datum

Use this worksheet to replace the current approximate room references with
repeatable measurements. These measurements support the next exact CAD pass;
they do not authorize drilling or installation.

Use two separate, run-local horizontal datums:

- **Through/long run:** zero is the far-left clear endpoint; values increase
  toward the inside corner.
- **Return/short run:** zero is the inside corner; values increase toward the
  far-right clear endpoint.

Write `through` or `return` beside every horizontal value. Never merge the two
coordinate systems, continue one through the corner, or treat a worksheet
coordinate as a drilling coordinate. These are survey coordinates only.

Use the finished floor directly below each measurement as the vertical datum.
Do not assume the floor, ceiling, or walls are level, plumb, square, or straight.
Record inches to the nearest 1/16 in, or millimetres to the nearest 1 mm. Take
each critical length three times and record the raw readings rather than
averaging from memory.

> **HARD STOP:** mark and photograph suspected stud/blocking positions, but do
> not drill exploratory holes. Wiring and plumbing may be present even when a
> stud finder reports framing. Uncertain construction or electrical routing
> requires qualified local verification before wall work. Nothing recorded on
> this worksheet is a wall-bore coordinate.

## Known planning references to confirm

| Item | Current nominal/approximate value | Reading 1 | Reading 2 | Reading 3 | Accepted field value | Photo ID |
|---|---:|---:|---:|---:|---:|---|
| Floor to ceiling | 96 in |  |  |  |  |  |
| Floor to outlet faceplate top | 53.5 in |  |  |  |  |  |
| Proposed lower shelf top | 68 in |  |  |  | confirm/change: |  |
| Proposed upper shelf top | 84 in |  |  |  | confirm/change: |  |

The proposed 68/84 in shelf tops produce a nominal 16 in top-to-top interval.
This is a planning choice, not a structural or accessibility approval.

## Recorded clear wall lengths

At each elevation, measure the through run from the far-left clear boundary to
the inside corner and the return run from the inside corner to the far-right
clear boundary. Do not measure along the floor and assume the upper wall is
identical. Record the endpoint obstruction—door trim, casing, wall return,
cabinet, or other feature—and the usable clearance before it.

| Run and elevation | Reading 1 | Reading 2 | Reading 3 | Shortest confirmed clear length | End obstruction / photo ID |
|---|---:|---:|---:|---:|---|
| Through/long wall at 68 in | 61.25 in | same reported value | — | **61.25 in / 1555.75 mm** | user field report |
| Through/long wall at 84 in | 61.25 in | same reported value | — | **61.25 in / 1555.75 mm** | user field report |
| Return/short wall at 68 in | 36.75 in | photo review | — | **36.75 in / 933.45 mm** | supplied short-wall photos |
| Return/short wall at 84 in | 36.75 in | photo review | — | **36.75 in / 933.45 mm** | supplied short-wall photos |

The 36.75-in return value is a conservative working measurement read from the
supplied photos. These four values establish clear-wall envelopes only. They
are not shelf cut lengths, support centers, endpoint clearances, or drilling
coordinates; those remain blocked by the corner, trim, outlet, framing, and
member-interface work below.

Use [MATERIALS_AND_HARDWARE.md](MATERIALS_AND_HARDWARE.md) when recording the
framing and hardware sections below. Its GRK screw and washer are selected
fixture candidates, not permission to skip the measurements.

## Outlet and electrical service envelope

The horizontal outlet datum is currently missing and blocks exact support,
ledger, cable-rail, and no-drill-envelope study. Record it from the **through
far-left zero** toward the corner.

| Measurement from through far-left zero | Reading 1 | Reading 2 | Reading 3 | Accepted value | Photo ID |
|---|---:|---:|---:|---:|---|
| Through wall to outlet faceplate left edge |  |  |  |  |  |
| Through wall to outlet faceplate centerline |  |  |  |  |  |
| Through wall to outlet faceplate right edge |  |  |  |  |  |
| Floor to faceplate bottom |  |  |  |  |  |
| Floor to faceplate center |  |  |  |  |  |
| Floor to faceplate top |  |  |  |  |  |
| Faceplate width |  |  |  |  |  |
| Faceplate height |  |  |  |  |  |

Record the largest plug/adapter expected to remain connected:

| Item | Width | Height | Projection from wall | Cord bend/service clearance needed | Photo ID |
|---|---:|---:|---:|---:|---|
|  |  |  |  |  |  |
|  |  |  |  |  |  |

Do not place a support, ledger splice, cable module, or drill location from
these measurements alone. A verified electrical routing/no-drill envelope is a
separate requirement.

## Inside corner and wall straightness

| Check | Method / location | Reading(s) | Accepted field value | Photo ID |
|---|---|---|---|---|
| Inside-corner angle near 68 in | angle gauge/template, both walls |  |  |  |
| Inside-corner angle near 84 in | angle gauge/template, both walls |  |  |  |
| Through wall bow at 68 in | straightedge/string with offsets |  | max offset: |  |
| Through wall bow at 84 in | straightedge/string with offsets |  | max offset: |  |
| Return wall bow at 68 in | straightedge/string with offsets |  | max offset: |  |
| Return wall bow at 84 in | straightedge/string with offsets |  | max offset: |  |
| Corner buildup/rounded texture | note radius or interference |  |  |  |

For a bowed wall, record offsets from the applicable run-local zero and include
the run name. Do not force a rigid PETG ledger flat against a wall with
fasteners.

## Door, trim, and working clearances

| Feature | Horizontal datum and size | Projection | Clearance at 68 in | Clearance at 84 in | Photo ID |
|---|---|---:|---:|---:|---|
| Through-run outer trim/door casing |  |  |  |  |  |
| Return-run outer trim/door casing |  |  |  |  |  |
| Door swing / handle sweep |  |  |  |  |  |
| Light fixture / ceiling obstruction |  |  |  |  |  |
| Existing furniture/equipment |  |  |  |  |  |
| Other obstruction |  |  |  |  |  |

Confirm that inward-facing cable rails and their removal paths do not enter a
door/trim, outlet/plug, walkway, or snag envelope.

## Stud, blocking, substrate, and concealed-service survey

Use one row for every candidate framing center. Through positions increase from
the far-left zero toward the corner; return positions increase from the corner
toward the far-right endpoint. Make marks at both shelf elevations; do not assume a
detection at one height continues unobstructed through another.

| Run | Elevation | Center from that run's zero | Detection method | Repeated from opposite direction? | Confidence / notes | Photo ID |
|---|---:|---:|---|---|---|---|
| through | 68 in |  |  |  |  |  |
| through | 68 in |  |  |  |  |  |
| through | 84 in |  |  |  |  |  |
| through | 84 in |  |  |  |  |  |
| return | 68 in |  |  |  |  |  |
| return | 68 in |  |  |  |  |  |
| return | 84 in |  |  |  |  |  |
| return | 84 in |  |  |  |  |  |

Add rows as needed. A stud-finder indication is survey evidence, not permission
to drill or proof of a safe fastener path.

| Construction input | Field value | How verified | Photo/document ID |
|---|---|---|---|
| Wall finish/substrate type |  |  |  |
| Measured substrate thickness |  |  |  |
| Framing type and nominal size |  |  |  |
| Continuous blocking present? | unknown / yes / no |  |  |
| Blocking material, thickness, elevation and extent |  |  |  |
| Known wiring/plumbing/HVAC routes |  |  |  |
| Corner framing/blocking on through wall |  |  |  |
| Corner framing/blocking on return wall |  |  |  |
| Driver access obstruction |  |  |  |

If continuous blocking or an independently verified equivalent is absent, the
current minimized station concept cannot receive structural credit merely by
moving printed supports to convenient locations.

## Intended contents—not a load rating

List realistic contents, including unusually dense items and cable bundles.
This defines a future target test load; it does not establish an allowable load.

| Item / container | Quantity | Individual measured weight | Footprint (W × D) | Height | Intended level/run/location |
|---|---:|---:|---:|---:|---|
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

Largest desired container height: ________<br>
Largest desired container depth: ________<br>
Desired cable bundle diameter/count: ________<br>
Any warm equipment, battery, liquid, or chemical storage: ________

No load, including the contents above, is authorized until the separate
physical qualification and installed release are complete.

## Required photo set

- [ ] wide view showing both full walls and inside corner;
- [ ] each wall with visible 68 in and 84 in tape marks;
- [ ] all four clear-length tape readings;
- [ ] outlet close-up with vertical measurement;
- [ ] outlet wide view with horizontal tape from the through far-left zero;
- [ ] through-wall stud/blocking marks at both elevations;
- [ ] return-wall stud/blocking marks at both elevations;
- [ ] inside-corner angle/template at both elevations;
- [ ] door/trim and full door-swing clearance;
- [ ] ceiling/light clearance above the proposed upper shelf; and
- [ ] labels or evidence used to identify wall construction.

## Measurement handoff checklist

- [ ] Values include units, run name, and the correct run-local zero.
- [ ] The four clear wall lengths are complete.
- [ ] Shelf-top choices at 68/84 in are confirmed or changed explicitly.
- [ ] Outlet centerline from the through far-left zero is complete.
- [ ] Corner angle and wall bow are recorded at both levels.
- [ ] Stud/blocking maps exist for both walls and both levels.
- [ ] Substrate thickness and construction are verified, not guessed.
- [ ] Door, trim, plug, cable, and driver service envelopes are documented.
- [ ] Intended contents and measured weights are listed.
- [ ] Every critical value has a matching photo ID.

Measured by: ____________________  Date: ____________________<br>
Tape/gauge used: ____________________  Units: ____________________
