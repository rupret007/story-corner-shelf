# Contributing to Story Corner

Issue reports and evidence-backed design discussion are welcome. Code, mesh,
and asset contributions are not currently invited because the owner has not
selected a project license or contribution agreement. The technical rules
below document the review standard that will apply if that posture changes.
r6 is an experimental, unrated all-black-PETG shelf body whose only nonprinted
installation boundary is suitable metal structural screws with heads/washers
into verified wood framing.

## Rights first

This repository currently has no `LICENSE` file. Public visibility does not
grant permission to copy, modify, redistribute, or sell its contents. Do not
assume contribution or reuse rights that have not been stated. Maintainers
should select an intentional project license before inviting broad reuse.

Do not contribute copied or derivative third-party meshes without explicit,
compatible permission and provenance. The supplied MakerWorld 3MFs are
read-only functional references and must not be bundled. If permissively
licensed code is ported, preserve its required notices and identify the exact
source, version, license, and changes. Ideas are not load evidence.

## Non-negotiable safety contract

Every change must continue to state that:

- r6 is experimental and unrated; no tested load rating exists;
- production wall holes are blocked until actual fastener, driver, wall
  finish, framing, and utility data are measured and regenerated;
- primary hollow-wall and printed wall anchors are prohibited;
- all shelf-body parts are printed black PETG; only wall screws and compatible
  heads/washers are nonprinted;
- the two levels are complete and structurally independent;
- cross-keys, retention pins, floating keys, corner trim, and fine ornament receive
  zero independent vertical load credit;
- neutral 3MFs contain no G-code and no unconfirmed printer profile;
- wall, full-bay, creep, recovery, and teardown evidence is required before
  overhead use or any load claim.

Do not soften warnings because a mesh is watertight, a calculation is elegant,
or a short test appears successful.

## Source-of-truth flow

Keep the dependency direction explicit:

1. `config.json` holds authoritative dimensions, scope, status, and gates.
2. `design_math.py` derives the fitted plan and core geometry.
3. `release_plan.py` enumerates cassette and support positions.
4. `release_inventory.py` enumerates each independently printed installed
   object and reconciles 258 per level / 516 for two levels.
5. mesh and drawing generators consume those sources; they must not carry
   shadow constants or silent fallbacks.
6. generated schedules, manifests, validation, `model_3mf_report.json`, and
   `slice_report.json` are
   outputs, never hand-edited sources.

Integral features and interfaces are not physical objects. Do not inflate the
inventory with cassette/spring tenons, receivers, or cassette seams. Per level,
the active contract is 225 chassis/joinery/retention
objects plus 33 removable zero-credit ornament objects. Test coupons and spares
are outside the installed total.

## Design rules to preserve

- 6 in depth; six through bays plus three return bays equals nine.
- Seven through and four return supports on every independent level.
- The through arm owns the 6 x 6 in corner; the return remains independently
  supported and the visual corner mate floats.
- Final-X vertical lift: two cassette tenons plus one spring tenon enter
  open-bottom receivers together at zero run-axis travel.
- Two accessible top quarter-turn cross-keys plus one spring cross-key retain
  each half against withdrawal; broad shoulders carry the candidate bearing path.
- Crown bridges insert upward from below and use one fixed-right accessible
  anti-drop pin; no top-down bridge or second fixed pin.
- Nine crown seams are locally fixed; seven supported pier seams float.
- One left-owned removable keeper, opposite the fixed-right crown-pin ear,
  positively traps all three diaphragm keys with one rear-bayonet tongue; a
  separate underside indexed quarter-turn pin blocks its unlock slide, and the
  fixed front tie has its own separate indexed pin.
- Floating-pier keys remain trapped beneath the integral corbel bearing cap
  through the qualified 1.2 mm axial travel. Stitch rails are excluded from
  the baseline and receive no credit.
- At least 75 mm straight visible-front/open-underside access for every
  structural cross-key and pin.
- Upper level installs first; no cross-level structural tie.
- Roman/Greek/Egyptian/Art Deco fine detail stays isolated and zero-credit.
- Drawings govern; the artist rendering is visual intent only.

If a field condition requires a different station layout, regenerate the
parametric structure. Do not scale a mesh or move only the ornament to conceal
a missed support.

## Development workflow

1. Work on a focused branch and describe the safety/design issue being solved.
2. Update configuration first when changing an authoritative parameter.
3. Add or update deterministic tests before changing generated artifacts.
4. Regenerate through project scripts; do not manually edit STL, 3MF, SVG,
   schedules, or manifests.
5. Run all r6 regression, package, inventory, drawing, documentation, and
   determinism tests in a clean environment.
6. Regenerate twice and compare hashes when changing geometry or packaging.
7. Inspect meshes for watertightness, positive volume, one intended body,
   envelope, thin walls, collisions, trapped access paths, and correct saved
   orientation.
8. Inspect 3MF archives for neutral model content and absence of G-code,
   machine commands, or hidden slicer payloads.
9. Render and visually inspect governing drawings. Confirm warning/status text
   is legible and dimensions match the configuration.
10. Review the staged diff, including generated-file size and manifest changes,
    before opening a pull request.

Never add credentials, local absolute paths, owner Downloads, private reference
3MFs, machine caches, G-code, or unrelated generated files.

## Tests and evidence

Tests should fail closed on duplicate configuration keys, missing required
fields, stale counts, build-envelope violations, impossible assembly motion,
wall-bore generation while blocked, cross-level ties, hidden access, neutral
3MF violations, and nondeterminism.

Use exact assertions for the nominal regression fixture but label it nominal
and unverified. Geometry/software tests may claim only what they test. Physical
test records belong with a clear specimen ID and must include raw measurements,
material/profile/hardware, environment, failures, 1 h / 24 h / 7 d / 30 d /
90 d creep readings, 72 h recovery, and teardown. Never summarize a failed or
incomplete test as “passed with caveats.”

## Pull-request checklist

- [ ] Scope and motivation are clear.
- [ ] No third-party mesh or incompatible code was copied.
- [ ] Safety/status language remains explicit.
- [ ] Configuration, math, plan, inventory, generator, drawings, and docs agree.
- [ ] 258 per level = 225 + 33; 516 for two independent levels.
- [ ] No production wall hole or printed/primary hollow-wall anchor was added.
- [ ] No G-code or unconfirmed slicer profile was added.
- [ ] Final-X lift, two top plus one spring cross-key per half, upward crown bridge, positively retained
  crown keys/tie, thermal floating seams, rail-free baseline, corner
  independence, and upper-first service remain.
- [ ] Tests are deterministic and claims are limited to observed evidence.
- [ ] Generated artifacts were produced by the checked-in scripts and reconcile
  with their manifest.
- [ ] Documentation contains no local absolute paths or private file data.

The preserved `reference/hybrid_r5/` design is a separate fallback. Modify it
only in an explicitly scoped change, and never merge its assumptions or test
claims silently into active r6 documentation.
