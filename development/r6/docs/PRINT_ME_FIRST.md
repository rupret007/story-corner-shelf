# Print me first — r6 gate card

> **STOP: Story Corner r6 is experimental, unrated, and not released for
> overhead use. There is no tested load rating. Production wall holes are
> blocked. Do not print the complete set, drill the wall, install the shelf, or
> place stored objects on it until every gate below is closed.**

Every shelf-body component is intended to be printed in the same qualified
black PETG system. The only nonprinted installed items are suitable metal
structural screws with integral heads or compatible metal washers into verified
wood studs or purpose-installed blocking. No printed wall anchor, primary
hollow-wall anchor, structural adhesive, or metal member hidden inside the
shelf body is part of r6.

## 1. Record the right gate before slicing

Isolated, non-wall fit/material coupons may be sliced before the wall survey is
complete. That narrow permission does not transfer to a wall-interface coupon,
X-corbel, full bay, one-level package, two-level package, drilling, installation,
or loading.

### Before any isolated non-wall coupon slice

Record these in [MEASUREMENT_WORKSHEET.md](MEASUREMENT_WORKSHEET.md) or the
retained local qualification record:

- r6 artifact/manifest identity and the exact non-wall print-first object and
  plate selected;
- exact printer model, firmware, nozzle diameter, and nozzle condition;
- build-plate type, usable build area, cleaning state, and condition;
- black-PETG manufacturer, product line, ASIN, color, lot/batch if available,
  exact spool, age, storage, and recorded drying procedure;
- Bambu Studio version, installed system-filament profile name, process name,
  and every candidate or per-plate override used;
- the local project/output path and the retained slice/settings-report path;
- who will supervise the print and the tested emergency-stop procedure: where
  to press Stop/Cancel and where the accessible power switch or disconnect is,
  without reaching into a moving or hot printer.

Mark wall geometry, framing, hardware, driver access, storage, target load, and
all structural/installation tests **OPEN / NOT MEASURED**. Do not leave them
blank in a way that could be mistaken for complete.

### Before a wall-interface, X-corbel, full-bay, or installation-set slice

Complete every preliminary record above, then also record:

- measured 3 ft and 5 ft wall geometry at both proposed shelf heights;
- corner angle, wall bow, ceiling bow, outlet/plug service envelope, and all
  trim or obstructions;
- verified stud or purpose-installed blocking centers, widths, material,
  thickness, and utility-clearance method;
- actual structural screw shank diameter, head/washer outside diameter, length,
  thread embedment, driver bit, and driver-access envelope;
- largest stored-item width, depth, loaded height, loaded weight, quantity, and
  total target contents load per level.

The intended local qualification setup is now confirmed as a **Bambu Lab A1
mini**, **0.4 mm nozzle**, **Bambu Textured PEI Plate**, and **SUNLU standard
black PETG 1.75 mm**, ASIN
[`B0D1KC72YP`](https://www.amazon.com/dp/B0D1KC72YP). Record the actual spool
lot/batch even if the retail listing does not show one. The listing says the
product is GRS-certified with at least 50% recycled content; do not disqualify
it for that reason, but do make every result specific to this ASIN, black
color, lot, spool, drying record, and saved profile.

An earlier reference 3MF and the current Bambu Studio workspace contain PLA
settings. **The current Studio PLA profile must not be reused, copied, or
edited into the PETG profile.** Select the installed Bambu Studio **system**
filament profile named exactly `SUNLU PETG @BBL A1M 0.4 nozzle` and verify
PETG—not PLA—before every slice. This starting profile is a system profile,
not a local user preset. This setup identifies the qualification hardware and
material; it does not prove that the profile, a part, or an installation is
physically qualified. r6 release files contain no G-code and remain
model-only.

## 2. Verify the artifact is what it claims to be

The canonical package IDs and model-only filenames are frozen in source, and
the current deterministic build emits and validates all five. A filename by
itself does not mean that a copied or rebuilt package matches the checked
manifest, and software validation does not establish physical qualification.
These files are software-model packages only. A passing package must
state `software_model_package_eligible: true`,
`physical_installation_qualified: false`, and
`production_release_eligible: false`. The qualification package is a specimen
model, not a successful qualification result. Accept only a generated manifest
whose ID and filename match this table exactly:

| Canonical package ID | Frozen model-only filename |
| --- | --- |
| `print_first_prototypes` | `MODEL_ONLY_R6_PRINT_FIRST_PROTOTYPES.3mf` |
| `unique_parts_catalog` | `MODEL_ONLY_R6_UNIQUE_PARTS_CATALOG.3mf` |
| `worst_case_one_bay_qualification` | `MODEL_ONLY_R6_WORST_CASE_ONE_BAY_QUALIFICATION.3mf` |
| `one_level_l` | `MODEL_ONLY_R6_ONE_LEVEL_L.3mf` |
| `two_level_full_project` | `MODEL_ONLY_R6_TWO_LEVEL_FULL_PROJECT.3mf` |

Never treat a development specimen, artist rendering, renamed file, or a
canonical filename without its matching validation evidence as a production
part or physically installable shelf.

The five files above are aggregate packages. The same checked artifact set
also contains exactly 49 individual one-part model-only 3MFs in
`generated/individual_model_only_3mf/`, paired one-for-one with the 49 STL
sources in `generated/stl/`. Each pair must retain the same basename, geometry
digest, bounds, triangle count, closed-solid audit, and manifest record.

Before printing any release candidate, verify that:

- the manifest identifies r6 and says `production_release_eligible: false`;
- every 3MF is model-only and contains no G-code or slicer command payload;
- all 49 STL / individual-3MF pairs are present in their documented generated
  directories and pass the exact pair audit;
- the validation report is for the same manifest and configuration digest;
- the parts schedule says 258 installed objects per level: 225 chassis,
  joinery, and retention objects plus 33 zero-credit ornament objects;
- the selected two-level schedule says 516 installed objects; coupons and
  spares are additional;
- no production X-corbel contains a wall-fastener bore until the real hardware
  and wall build-up have been measured and regenerated;
- every required part fits the confirmed build volume in its saved
  orientation;
- drawings and schedule agree with `3 + 6 = 9` bays, 7 + 4 supports, 18
  cassettes, and two independent levels.

## 3. Print qualification pieces first

Do not infer fit from nominal clearances.

The canonical print-first package contains eight development objects, but it
is still qualification-only and unsliced. For the first local campaign, print
only its **non-wall** coupon plates, one plate at a time. Keep
`R6_DEV_BLOCKED_WALL_SCREW_BEARING_COUPON_SOLID_NO_HOLE` disabled: it is a
solid no-hole boundary placeholder, not a coupon for the eventual screw. Do
not print a wall-screw bearing coupon, any X-corbel, or either full
installation package until the actual screw/head/washer, driver envelope,
finished-wall build-up, and verified framing have been recorded and the wall
interface has been regenerated.

The full eventual qualification sequence is to print, label, measure, and
retain:

1. the 0.2 / 0.3 / 0.4 / 0.5 mm clearance matrix and pin coupons;
2. the crown-bridge insertion and accessible-pin coupon;
3. the wall-screw bearing coupon regenerated around the actual screw and metal
   head/washer;
4. one two-skin cassette with its fixed/floating seam, integral-cap locator,
   key keeper, and visible-front crown-tie interfaces;
5. one complete X-corbel with its integral full-width bearing cap, cassette
   locks, and driver-access mockup;
6. the ornament connector coupons, which remain outside the 33 installed
   ornament pieces;
7. one complete worst-case 241.935 mm through-arm bay on a sacrificial wall
   mockup reproducing the real finish, verified framing, and fastener.

Reject any coupon with split layers, poor fusion, severe stringing inside a
receiver, distorted pins, whitening, cracks, nonrepeatable engagement, hidden
tool access, or a fit that requires hammering. Tune one centralized clearance
parameter and regenerate; do not scale a structural part in the slicer.

## 4. Slicing rules until a tested profile exists

No universal production profile is supplied. PETG brand, drying, nozzle,
machine, plate, temperature, cooling, line width, layer height, perimeter
count, seam placement, and speed materially affect the result. Start from the
confirmed PETG manufacturer's guidance and the printer manufacturer's profile,
then qualify the coupons and full bay with the exact settings you intend to
use. Record the slicer version and export a settings report.

### Candidate A1 mini / SUNLU PETG qualification profile

Use the installed Bambu Studio system profile `SUNLU PETG @BBL A1M 0.4
nozzle`. SUNLU does not currently publish an official standard-PETG A1 mini
download in its own preset selector, so the installed Bambu system profile and
these values are a project-specific starting point to calibrate, not a
SUNLU-certified A1 mini download:

| Bambu Studio field | Candidate value |
| --- | --- |
| Printer | `Bambu Lab A1 mini 0.4 nozzle` |
| Build plate | `Textured PEI Plate` |
| Filament | Bambu system profile `SUNLU PETG @BBL A1M 0.4 nozzle`; SUNLU standard black PETG 1.75 mm, ASIN `B0D1KC72YP` |
| Nozzle | 250 °C first layer; 245 °C other layers |
| Textured bed | 60 °C first and other layers |
| Flow ratio | 0.94 |
| Maximum volumetric speed | 9 mm³/s |
| Process preset | `0.20 mm Strength`; 0.20 mm layer height |
| Wall loops | 6 |
| Top / bottom shell layers | 5 / 3 |
| Sparse infill | 25%, grid |
| Brim | 5 mm baseline; a qualification-project plate may require an explicit override |
| Supports | Off by system default; inspect each plate and retain any project-specific override |
| Part cooling | 10% minimum, 30% maximum, 90% for overhangs |

Leave those embedded system/process values unchanged for the first baseline;
do not improvise cooling, shell, infill, support, or brim values. The local
qualification builder may deliberately override support or brim per plate.
When it does, the project-specific value governs that plate and must appear in
the retained settings report.

SUNLU's current standard-PETG sources differ in some details. For this first
controlled baseline, dry the exact spool at **60–65 °C for 6 hours**. Record
the dryer, indicated/verified temperature, start/end time, ASIN, color,
lot/batch, spool, and date. Do not carry a passing result to another PETG
product, color, lot, spool, drying history, profile, or changed temperature or
flow setting.

### Beginner-safe Bambu Studio sequence

1. With the plate removed and cool, wash the Textured PEI surface with
   detergent and water, rinse it, and dry it completely. Do not touch the
   cleaned print area and do not use acetone. Dry the PETG as specified above.
2. Reinstall the clean plate correctly, load the dried PETG, and confirm the
   printer shows the intended PETG spool. Do not leave PLA selected anywhere.
3. Open the **local qualification project**. Select `Bambu Lab A1 mini 0.4
   nozzle`, `Textured PEI Plate`, and the installed system profile `SUNLU PETG
   @BBL A1M 0.4 nozzle`. Never open a canonical aggregate 3MF and press Print
   without this local setup review.
4. Check that every object is at **100% scale on X, Y, and Z**. Do not use
   auto-scale, fit-to-bed scaling, unit conversion, cutting, or repair that
   changes geometry.
5. Select one non-wall qualification plate and slice it locally. In Preview,
   inspect the first layer, brim, supports, every layer/toolpath, unsupported
   regions, collisions, plate boundaries, and all warnings. Confirm no path is
   missing and no object crosses a keep-out or printable boundary.
6. Before relying on the candidate values, use supported A1-series **Flow
   Dynamics** calibration if the installed firmware offers it. For **Flow
   Rate**, the A1 mini requires Bambu Studio's manual coarse and fine workflow;
   inspect the calibration pieces and save the result as a new filament user
   preset. Do not call either result a structural qualification.
7. Print **one plate at a time** and watch the first layer. Stop immediately
   for lifting, nozzle contact, scraping, missing extrusion, severe stringing,
   layer separation, or a toolpath different from Preview.
8. When the print finishes, wait for the Textured PEI Plate to cool to **35 °C
   or below** before removal. Label the specimen with spool/lot, profile,
   settings, plate, date, and plate number; record and retain the local slice
   report.

The development-only helper is named
`build_bambu_qualification_projects.py`. Use the command that matches the tree
you actually have, with the same exact fresh sibling output path.

From the source-workspace repository root:

```text
.venv/bin/python development/r6/build_bambu_qualification_projects.py --output ../story-corner-r6-bambu-a1mini-sunlu-petg-qualification-v1
```

From the flattened published-project root:

```text
.venv/bin/python build_bambu_qualification_projects.py --output ../story-corner-r6-bambu-a1mini-sunlu-petg-qualification-v1
```

The helper atomically creates that fresh workspace sibling and must refuse to
replace an existing destination or write anywhere else. Never point it at
`development/r6/generated/` or another existing release directory. Its
`../story-corner-r6-bambu-a1mini-sunlu-petg-qualification-v1/` output is a local,
unsliced qualification workspace with no G-code; it is not a sixth canonical
package, is not covered by the release manifest, and must not be published as
a production artifact.

### A1 mini build-volume warning

Bambu specifies the A1 mini build volume as 180 x 180 x 180 mm. The saved
X-corbel geometry reaches 168 mm on its bed axis and its required 6 mm brim on
both sides reaches **exactly 180 mm**. That leaves zero nominal bed-axis margin
before plate keep-outs, placement tolerance, extrusion width, or slicer/toolhead
constraints. Do not scale, crop, split, rotate, or remove the required brim to
force it to fit. The corbel stays blocked until its exact saved orientation,
brim, supports, and entire Preview toolpath fit the confirmed usable plate and
its actual-parent coupon gates pass. The corbel is not part of the initial
campaign; its 6 mm brim is a deliberate project-specific override to the
general 5 mm candidate baseline.

Official references: [Bambu Lab A1 mini specifications](https://us.store.bambulab.com/products/a1-mini),
[Bambu Textured PEI Plate cleaning, PETG, and cool-removal guidance](https://us.store.bambulab.com/products/bambu-textured-pei-plate),
[Bambu Flow Dynamics calibration](https://wiki.bambulab.com/en/software/bambu-studio/calibration_pa),
[Bambu Flow Rate calibration](https://wiki.bambulab.com/en/software/bambu-studio/calibration_flow_rate),
[SUNLU standard PETG product guidance](https://www.sunlu.com/products/petg-3d-printing-filament),
[SUNLU PETG TDS](https://media.sunlu.com/prod/20260330/f27808f0-3a19-49e3-bd79-6e846d6f4c15.pdf?filename=TDS),
[SUNLU filament drying guide](https://www.sunlu.com/wiki/filament-usage-guide),
and [SUNLU printer-preset selector](https://www.sunlu.com/materials-lab/printer-presets).

There is no authoritative print-time estimate while those inputs remain
unqualified. CAD volume and model-only 3MF object counts are not print-time
proxies; retain the exact qualified slicer's time estimate with its settings
report before planning a complete print campaign.

Preserve the saved structural orientations:

| Part family | Qualification orientation |
| --- | --- |
| Deck cassette | Continuous top skin on the plate; coffer lands upward, then flip for installation |
| Arcade half | Broad elevation face on the plate; qualify same-PETG support/sacrificial mapping for the centered pads, shoulder, and tenons |
| X-corbel | Common wall-contact face on the plate; qualify every-layer connectivity, clevis cheeks, ridge/lock closures, exact same-PETG supports, and the full brim/toolpath |
| Crown diaphragm keeper | Broad strip face on the plate with its one rear-bayonet tongue upward; qualify it with the separate keeper-reach indexed quarter-turn pin in the exact actual-parent receiver orientation |
| Crown bridge | Broad ladder face on the plate |
| Wedges and flat keys | Largest broad face on the plate |
| Ornament | Decorated `d=0` face on the plate with receiver housings upward; this is not a flat-back print and requires the actual-parent orientation coupon |
| Crown-bridge pin | Shaft axis parallel to the plate; split plane perpendicular to the plate; round head and circular cross-section vertical/tangent to the plate. No support-free or production claim; qualify slicer mapping, brim, cooling, flexure, and actual-parent service on the confirmed profile |
| Indexed keeper/front-tie pins | Shaft axis parallel to the plate with the 8 mm handle edge and one T-tail edge on the plate; qualify both service-axis variants in their actual-parent receivers |

Do not rotate a structural part merely to reduce supports without repeating
qualification. Do not substitute PLA, PETG-CF, another polymer, another black
PETG product, or a different lot mid-test and carry results forward.

## 5. Test before any overhead installation

Follow [TEST_PROTOCOL.md](TEST_PROTOCOL.md) on a guarded bench or low
sacrificial wall mockup where failure cannot strike a person, pet, vehicle, or
valuable object. Required evidence includes:

- coupon and wall-bearing results using the final profile and actual fastener;
- a complete worst-case bay and corner dry-fit;
- matched low-load arch-on / arch-off deflection comparison;
- separate distributed, front-edge, crown-point, and asymmetric/torsional load
  cases only after a target load and written stop limits are set;
- whole-article thermal cycling of a complete independent L level; coupon-only
  cycling does not close this gate;
- sustained-load readings at 1 hour, 24 hours, 7 days, 30 days, and 90 days;
- 72 hours unloaded recovery after the 90-day reading;
- teardown inspection of every bearing face, pin, cross-key, receiver, keeper,
  floating integral-cap seat, screw seat, and printed layer path.
- a separately printed matched specimen loaded destructively to failure and
  never reused for creep evidence or installation.

Thirty days is only an initial creep screen. No load claim may be considered
before 90 days plus recovery and teardown, and completion does not create an
automatic rating.

## 6. Installation gate

Proceed to [ASSEMBLY.md](ASSEMBLY.md) only after all measurements are entered,
production wall geometry is regenerated, test acceptance criteria are written,
all tests pass for the exact material/profile/hardware combination, and a
competent person has reviewed the intended wall and use. Install the upper
level first so its 75 mm minimum front/underside cross-key-and-pin service paths
remain accessible; install the lower level only after the upper level is fully
service-checked.

If any gate is uncertain, stop. The preserved `reference/hybrid_r5/` design is
the documented fallback, but it is a separate architecture and its evidence
must not be transferred to r6.
