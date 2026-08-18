# R11 reduced-part product plan

This plan turns the R10 Palatine Lincoln-log study into a simpler, reusable
R11 architecture without weakening the seven-support first-wall topology.
It is a versioned redesign; it does not silently alter the immutable R10
qualification package.

> **Current status: engineering study only; 0 kg / 0 lb.** R11 v1 hard-forces
> printing, drilling-coordinate release, installation, test loading, and
> stored load to false regardless of printer state or input completeness.

The [qualification-only exploded bay and first-wall topology diagram](visuals/r11_first_outer_bay_exploded_and_wall_topology.svg)
summarizes the candidate geometry, exact motion, structural-credit boundary,
and count arithmetic without serving as a fabrication or drilling drawing.

## Product objective

For the measured 1555.75 mm first wall, reduce R10's 70-article inventory to a
28-article supplied kit, with at most 27 articles installed simultaneously,
while preserving:

- seven wall supports and six independently removable bays;
- 254.0 mm maximum support-center pitch;
- three candidate wall screws and one washer per support;
- three structural load lanes at the rear, center, and front of each bay;
- broad support-capital bearing and local failure containment;
- a black-PETG Roman / Art-Deco visual language; and
- the far-left two-socket cable receiver, two blanks, and one comb/hook.

The A1 mini cannot fit a complete 254 mm by 152.4 mm structural bay as one
flat, margin-compliant print. Two structural half-decks per bay are therefore
the hard minimum for this printer and shelf depth. R11 reduces the remaining
parts by integrating the R10 splice-log and support-retention functions into
those two half-decks and their supports.

## Frozen candidate architecture

The target first-wall kit is:

| Family | Kit count | Function |
|---|---:|---|
| Supports | 7 | Broad gravity bearing and candidate wall connection; S0 includes the fused cable receiver |
| Integrated half-decks | 12 | Two per bay, each with rear/center/front reciprocal load ribs |
| Bay-local keystones | 6 | One per bay; blocks half-to-half X separation and receives no support-capture or sustained-load credit |
| Cable modules | 3 | Two flush blanks and one comb/hook; zero shelf-load credit |
| **Supplied kit** | **28** | Qualification target, not a released production count |
| **Maximum simultaneously installed** | **27** | 25 structural/retention articles plus 2 modules in 2 sockets |

The safe unbatched plan is 28 one-article starts. The batched target is 21:
seven individual support plates, twelve individual half-deck plates, one
verified six-keystone plate, and one verified three-cable-module plate. Until
those optional batch plates are nested, sliced, and qualified, 21 remains a
planning target rather than a slicer fact. Batching changes starts only; it
does not alter kit quantity, installed-state limits, identities, BOM, or
qualification scope.

## Exact first-wall closure

The controlling first-wall inputs are:

```text
L = 1555.75 mm   measured clear wall length
w =   31.75 mm   support run width
p_max = 254 mm   maximum candidate support-center pitch
g =    0.35 mm   candidate endpoint/support-line/midpoint clearance
o =   55.00 mm   initial reciprocal-rib overlap candidate
```

The uniform layout is:

```text
bays = ceil((L - w) / p_max) = ceil(1524 / 254) = 6
supports = bays + 1 = 7
pitch = (L - w) / bays = 254 mm
candidate wall fasteners = 3 * supports = 21
```

The six idealized bay bodies comprise two terminal physical spans and four
regular physical spans:

```text
regular physical span  = pitch - g = 253.65 mm
terminal physical span = regular span + w/2 - g/2 = 269.35 mm

wall closure = 2*269.35 + 4*253.65 + 5*0.35 + 2*0.35
             = 1555.75 mm
```

For two equal reciprocal halves with 55 mm overlap:

```text
regular half run  = (253.65 + 55) / 2 = 154.325 mm
terminal half run = (269.35 + 55) / 2 = 162.175 mm
```

Both halves of bay 0 and both halves of bay 5 are terminal: four terminal
halves at 162.175 mm. Both halves of bays 1-4 are regular: eight regular halves
at 154.325 mm. R11 v1 refuses a one-bay wall because a single bay owning both
terminal end conditions is not authored or qualified.

With the project's 14.2 mm total X/Y allowance for 5 mm brim, 0.1 mm
brim-object gap, and 2 mm reserve at each edge, the terminal planning envelope
is 176.375 by 166.600 by 32.000 mm. Its minimum nominal bed-axis spare is only
3.625 mm, so the saved mesh and live Preview—not this worksheet—control fit.

## Work packages and gates

### A. Source and solver freeze

1. Freeze the complete R10 source tree by file count, byte count, tree hash,
   and canonical configuration identity.
2. Encode every product constant in strict JSON and reject duplicate keys,
   non-finite values, unknown fields, and unsafe mutations.
3. Implement a unit-aware layout solver that derives bay count, support
   centers, module lengths, counts, candidate screw axes, and refusal reasons.
4. Require exact, datum-bound records for wall measurements/uncertainty,
   bow/taper/corner angle, endpoints/trim, protected services/no-drill zones,
   every substrate layer, verified blocking geometry, printer/nozzle/plate,
   profiles/overrides, filament lot/drying, temperature/humidity/heat sources,
   contents/load envelope, and cable service sweeps.

**Gate:** two independent calculations close the measured wall exactly and
the solver refuses every missing or contradictory safety-critical input.

### B. Integrated one-bay geometry

1. Author left/right flat-printed half-decks with three reciprocal load ribs.
2. Preserve broad shoulders, at least 15.70 mm physical support bearing, and
   true-net rib-section comparison floors at the governing cuts.
3. Author the bay-local fixed-lug capture at both support contacts: lower with
   2 mm clearance, slide 32 mm wallward, then gravity-settle 2 mm into terminal
   pockets behind a solid 8.4 mm roof/shoulder; reverse lift 2, slide 32
   outward, lift clear.
4. Author one positive removable keystone that prevents half-to-half X
   separation without receiving support-capture, sustained gravity, or bending
   credit.
5. Prove collision-free assembly/reverse paths, one-body watertight meshes,
   layer connectivity, and A1-mini envelopes at 100% scale.

**Gate:** no shared loose key can release adjacent bays, no fit depends on
friction/snap/glue, and all saved geometry passes analytic mesh checks.

### C. Cable bookend and appearance

1. Port the existing inward-facing two-socket receiver onto the R11 S0
   support without subtracting from the structural support core.
2. Preserve two flush blanks and one comb/hook with the qualified keyed
   interface and service motion.
3. Keep intermediate supports and the future inside corner free of cable
   hardware.
4. Apply Palatine / Art-Deco ornament additively and outside every load path,
   bore land, capture, and service envelope.

**Gate:** the source support is byte/geometry-preserved inside the fused
bookend, all module service paths are collision-free, and cable parts retain
zero structural credit.

### D. Immutable neutral qualification bundle

1. Emit only exact individual STL and neutral model-only 3MF articles plus an
   explicitly off-plate inspection catalog.
2. Include normalized inputs, layout report, saved-mesh evidence, validation,
   release status, assembly diagram, BOM, and all controlling guides.
3. Bind every source and predecessor dependency by hash before execution.
4. Stage, validate, and publish atomically; refuse replacement; prove two
   fresh builds byte-for-byte identical.

**Gate:** exact file allowlist, source closure, geometry bijection, object
order, transforms, hashes, neutral archives, and zero G-code/profile/toolpath
all pass independently. Print/drilling-coordinate/install/test-load flags
remain hard-forced false and rated load remains 0 kg / 0 lb.

### E. Fail-fast physical qualification

A later reviewed print-capable revision may print only after the bundle and
exact live Preview pass; R11 v1 itself remains print-blocked:

1. one reciprocal-rib fit pair and its keystone;
2. one support-contact/capture fixture;
3. one complete actual bay on two supports;
4. the S0 cable bookend and modules;
5. only then the remaining tabletop first-wall set.

Every article is inspected cooled, measured, cycled through the exact
assembly/reverse motion, and quarantined on warp, crack, whitening, increasing
bind, loose capture, filled channel, dimensional drift, or permanent set. No
sanding, reaming, heat, lubricant, force, or hidden repair is allowed.

**Gate:** a failure stops the next print tranche and returns the design to the
smallest affected source/fixture gate.

### F. Connection and load qualification

The complete exact screw/FW14/PETG/substrate/blocking stack, one-bay rig,
framed-wall fixture, proof cases, cyclic cases, 1000-hour elevated-temperature
creep, recovery, and destructive twins must pass the requirements in
[LOAD_QUALIFICATION.md](LOAD_QUALIFICATION.md). Test objectives do not become
ratings. Only an independent structural reviewer may release a nonzero
allowable and installation conditions.

## Explicitly rejected shortcuts

- Six supports: this creates 304.8 mm / 12 in pitch, exceeding the current
  254 mm candidate maximum and materially increasing bending/deflection.
- One complete bay print: it does not fit the A1 mini at the required depth,
  brim, gap, and edge reserve.
- Fusing R10's upright half-cassette to its flat splice logs: it rotates the
  primary log load path across the intended layer orientation.
- A single capital key shared by adjacent bays: one loose part could release
  two bays and violate local failure containment.
- Fewer wall screws, generic drywall anchors, or moved freehand bores: they
  invalidate the candidate connection and do not solve missing blocking.
- Scaling, auto-orienting, support-enabled rescue, sanding, glue, or snap
  preload: each changes the qualified system or hides a failed fit.
- Calling geometric floors, target loads, attractive prints, or short tests a
  load rating.

## Public customization milestone

The reusable product release is complete only when a user can provide a
measured wall record and receive:

- deterministic support/bay/module quantities and coordinates;
- exact terminal and regular handed model identities;
- protected-zone and blocking conflicts with refusal reasons;
- true saved-mesh and printer-envelope evidence;
- a derived BOM and plate schedule;
- assembly and inspection records specific to that layout; and
- an explicit statement of every unresolved print, connection, installation,
  environment, and load gate.

See [CUSTOMIZATION.md](CUSTOMIZATION.md) for the solver contract and
[GUIDELINES.md](GUIDELINES.md) for the non-negotiable design memory.
