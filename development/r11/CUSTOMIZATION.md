# R11 customization and wall-layout solver contract

R11 is intended to become reusable for other measured walls and printer
envelopes. Customization means **regenerating and requalifying** an authored
system; it never means scaling an STL, stretching one bay, deleting a support,
or moving a wall screw by eye.

> **Current rating: 0 kg / 0 lb.** The R11 v1 solver may produce
> engineering-study geometry only. It hard-forces print, drilling-coordinate
> release, wall installation, test loading, and nonzero load rating to false;
> no complete input record may flip those values.

## Required inputs

Record every input in millimetres unless noted otherwise:

| Input | Required record |
|---|---|
| Wall length `L` | Three independent measurements at the intended rear, center, and front shelf depths and at the actual shelf elevation, each with instrument/resolution, uncertainty, datum, date, and observer |
| Shelf depth `d` | Desired projection plus verified door, trim, plug, cord, and circulation clearance |
| Printer envelope | Actual usable X/Y/Z, plate type, nozzle, brim, brim gap, and required edge reserve |
| Support width `w` | Candidate structural width; first-wall baseline 31.75 mm |
| Maximum pitch `p_max` | Reviewer-controlled upper bound; current candidate 254.0 mm |
| Joinery | Overlap candidate, seam clearance, minimum bearing, capture travel, and keystone service envelope |
| Wall geometry | Bow/taper at the shelf elevation, plumb/flatness, included corner angle, and endpoint/trim stand-off with uncertainty |
| End conditions | Left/right endpoint clearance, terminal/bookend identity, future corner ownership, and required assembly/disassembly sweep |
| Protected zones | Dimensioned outlet/faceplate/plug/cord envelopes, trim, doors, pipes, wiring, other utilities, and no-drill zones, all with datum and uncertainty |
| Wall structure | Every substrate layer/material/thickness; blocking location, depth, width, thickness, species/grade if known, edges/ends, and direct verification method/photo record |
| Environment | Measured minimum/maximum service temperature, humidity range, sunlight and nearby heat sources, measurement dates/duration/instrument, and intended contents/load envelope |
| Process/material | Printer serial/firmware, physical nozzle, plate identity/condition, exact profiles/overrides, filament product/lot/spool/drying, and ambient print conditions |
| Cable interface | Which endpoint is a true outer bookend; socket access, module state, and representative cable loop/bend/snag/service envelopes |

Every coordinate must identify a common wall/shelf datum and uncertainty.
Photos are supporting evidence, not dimensional inputs by themselves. Unknown
framing, utility, corner, process, or environment facts must stay explicitly
unknown and block installation-oriented output.

## Bay and support equations

For a straight wall with one support width `w` occupying both terminal faces:

```text
require L > w and p_max > 0
n_bays     = ceil((L - w) / p_max)
n_supports = n_bays + 1
pitch p    = (L - w) / n_bays
screws     = 3 * n_supports

support center c_i = w/2 + i*p,  i = 0 ... n_bays
support face interval i = [c_i - w/2, c_i + w/2]
clear distance between adjacent support faces = p - w
```

The ceiling function is mandatory: rounding down can exceed `p_max`. The
solver must recompute pitch rather than leave a short leftover bay unless a
reviewed obstacle-aware optimization deliberately creates unequal bays and
proves every bay independently.

R11 v1 additionally requires `n_bays >= 2`. It refuses a one-bay wall because
the case where both terminal end conditions belong to one bay has not been
authored or qualified. A future version must define that topology explicitly;
it may not reuse the two-or-more-bay identities by assumption.

### Measured first-wall check

```text
L = 1555.75
w = 31.75
p_max = 254.00

n_bays = ceil((1555.75 - 31.75) / 254)
       = ceil(1524 / 254)
       = 6

n_supports = 7
p = 1524 / 6 = 254.00
screws = 3 * 7 = 21
```

Centers are:

```text
15.875, 269.875, 523.875, 777.875,
1031.875, 1285.875, 1539.875 mm
```

The final support faces are exactly 0 and 1555.75 mm in this idealized layout.
Field bow, trim, endpoint clearances, and measurement uncertainty still need
to be applied by the generator; exact arithmetic does not prove fit or
blocking.

## Initial half-deck sizing worksheet

The current qualification candidates are:

```text
overlap o          = 55.00 mm
clearance g        = 0.35 mm
support width w    = 31.75 mm
minimum bearing b  = 15.70 mm
deck depth d       = 152.40 mm

regular physical span s_r = p - g
                          = 254 - 0.35
                          = 253.65 mm

terminal physical span s_t = s_r + w/2 - g/2
                            = 253.65 + 15.875 - 0.175
                            = 269.35 mm

wall closure = 2*s_t + 4*s_r + 5*g + 2*g
             = 2*269.35 + 4*253.65 + 5*0.35 + 2*0.35
             = 1555.75 mm

regular half length h_r = (s_r + o) / 2
                        = (253.65 + 55) / 2
                        = 154.325 mm

terminal half length h_t = (s_t + o) / 2
                         = (269.35 + 55) / 2
                         = 162.175 mm
```

For the first wall, bay 0 uses terminal-left and terminal-right halves and bay
5 uses terminal-left and terminal-right halves: four terminal halves at
162.175 mm. Bays 1-4 use eight regular halves at 154.325 mm. "Terminal" is an
authored identity, not a slicer mirror or a length applied to only one half.

These formulas are a candidate sizing worksheet, not finalized CAD. The
generator must derive terminal ownership from the actual support/capture
geometry, retain endpoint clearance, and measure the resulting saved mesh.
Changing pitch requires recomputing both halves and all cross-lap/capture
relationships.

## Printer-envelope equation

For an axis-aligned flat half-deck, a conservative padded footprint is:

```text
padded_x = mesh_x + 2 * (brim_width + brim_gap + edge_reserve)
padded_y = mesh_y + 2 * (brim_width + brim_gap + edge_reserve)
```

With 5.0 mm brim, 0.1 mm gap, and 2.0 mm edge reserve:

```text
terminal candidate: 162.175 + 2*(5 + 0.1 + 2) = 176.375 mm
depth:              152.400 + 2*(5 + 0.1 + 2) = 166.600 mm
```

Both are below 180 mm, but this is not nesting proof. The generator must use
the true transformed mesh, and Bambu Preview must show the complete brim
inside the printable region. Supports, wedges, and cable parts need their own
checks. Rotated packing may be accepted only from collision-free geometry and
Preview; scaling is never a fit solution.

## Obstacle-aware procedure

1. Inflate every protected wall/room envelope by measurement uncertainty,
   installation-tool clearance, plug/cord service motion, and reviewer-defined
   structural edge distance.
2. Compute the uniform layout above.
3. Intersect every support body, all three candidate screw axes, full washer
   lands, the shelf envelope, cable service path, and assembly/disassembly
   sweep with every protected zone.
4. Confirm each screw axis lands in verified blocking with accepted edge/end
   distance and embedment after substrate and intervening layers.
5. If a conflict exists, solve a constrained layout with all pitches at or
   below `p_max`, bearing and net-section floors preserved, and each bay still
   independently removable.
6. Regenerate all affected terminal and half-deck geometry. Re-run mesh,
   envelope, count, assembly-sweep, and physical qualification gates.

Never resolve a conflict by drilling a support elsewhere, omitting one of its
three fasteners, relying on a drywall anchor, trimming a load rib, scaling a
part, or accepting a pitch above the reviewed limit.

## Mandatory outputs

A reusable generator must emit at least:

- normalized inputs with units and measurement uncertainty;
- bay/support count, actual pitch, every support center and face interval;
- support identities, half-deck hands, terminal ownership, and cable-bookend
  identity;
- candidate screw count and every screw-axis coordinate;
- obstacle/blocking intersection report and explicit unresolved items;
- per-part true saved-mesh bounds, net-section/bearing measurements, volume,
  topology/manifold checks, authored orientation, and printer-envelope result;
- kit count, maximum simultaneously installed count, safe unbatched starts,
  and target batched starts as separate fields;
- a plate schedule proving that batching changes starts only, never article
  identities, kit quantity, installed-state limits, BOM, or qualification;
- deterministic hashes, source revision, neutral model-only files, manifest,
  validation, and release status;
- assembly order and exact support-capture/keystone motions for every handed
  part, including lower 2 mm clear over lug heads, slide 32 mm wallward,
  gravity-settle 2 mm into terminal pockets behind the solid 8.4 mm
  roof/shoulder, and reverse lift 2 / slide 32 outward / lift clear;
- explicit evidence that the keystone blocks half-to-half X separation only
  and receives zero support-capture, gravity, and bending credit; and
- hard-forced `print_authorized: false`,
  `drilling_coordinates_released: false`,
  `wall_installation_authorized: false`, `test_load_authorized: false`, and
  `rated_load_kg: 0.0` for all R11 v1 outputs, even if every input is present.

## Fail-closed refusal gates

The generator must refuse a printable/installation bundle, or clearly emit a
non-installable geometry study, when any of these is true:

- a required measurement, unit, uncertainty, trim/corner envelope, protected
  zone, or wall-structure record is missing;
- `L <= w`, bay count is less than two, clear span is nonpositive, or actual
  pitch exceeds the reviewed maximum;
- a support, screw/washer land, cable receiver, or assembly sweep intersects a
  protected zone;
- verified blocking or independently engineered equivalent is absent at any
  primary screw axis;
- a half-deck or support cannot fit the chosen printer at 100% scale with brim,
  gap, and reserve;
- minimum bearing, overlap, wall, true-net `I`, or true-net `Z` falls below its
  controlling requirement;
- an integral generated capture, terminal pocket/roof/shoulder, positive stop,
  or exact reverse disassembly path is missing, ambiguous, or dependent on
  snap/friction/adhesive;
- one local failure can unzip another bay;
- the cable receiver appears anywhere except a true outer bookend;
- saved mesh, source intent, manifest, validation, documentation, and plate
  schedule disagree; or
- a test, inspection, reviewer, or release-status gate is incomplete.

Geometry generation may help discover missing facts, but it is never a reason
to infer them. Record the refusal, correct the input or architecture, increment
the revision, and rerun the complete affected gate chain.
