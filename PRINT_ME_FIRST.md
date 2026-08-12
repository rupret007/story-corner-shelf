# Print me first — r6 gate card

> **CURRENT DEVELOPMENT IS R11, NOT R6.** Before doing anything, read
> [development/r11/README.md](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11/README.md), its
> [v1 print hold](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11/PRINT_FIRST.md), and the separate
> [Gate A-left v2 control overlay](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11_print_v2/PRINT_GATE_A_LEFT.md).
> The current first-wall design uses the measured **1555.75 mm** wall.
> The immutable R11 v1 neutral bundle is model-only and never
> print-authorized. The checked-in v2 package is also non-authorizing; it can
> support only one external, exact-job, fresh, single-use permit for the exact
> bay-0 **left** terminal half-deck, quantity one. That permit must be consumed
> before one Send attempt. **No print is authorized by the checked-in files
> themselves.** The permit is consumed even when the attempt fails or is
> cancelled, rejected, or ambiguous, and cannot be reused. Every retry needs a
> new slice, review, live-state check, and fresh permission.
>
> Real-world observations now live in the separate
> [beginner physical guide](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11_physical/README.md) and
> [append-only physical record](https://github.com/rupret007/story-corner-shelf/blob/main/development/r11_physical/PHYSICAL_RECORD.md).
> The left terminal half-deck was printed, cooled, and removed; the user reports
> no rocking, no visible finger flex, and no sanding. A later right-half job was
> initiated outside the frozen left-only v2 overlay, but its completed-part
> outcome has not yet been recorded. That does not retroactively authorize it
> or change v1/v2. Once both halves are cool and inspected, the next reviewed
> action is an **unloaded flat-table dry-fit**, never wall work or a load test.
>
> Full-wall planning remains **28 kit articles**, at most **27 simultaneously
> installed**, **28 safe unbatched starts**, and an
> **unverified 21-start batched target**. Neither v1 nor v2 authorizes drilling, wall installation,
> test or stored load, production/full-wall printing, or a nonzero rating
> (**0 kg / 0 lb**).
>
> This R6 gate card is retained as historical/frozen evidence, along with the
> R7-R10 trees under `development/`. It cannot authorize or define an R11 job.
> A standalone historical R6 publication may omit the `development/` tree; use
> the full source repository for current R11 work.

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

## 1. Confirm before slicing anything

Record these in [MEASUREMENT_WORKSHEET.md](MEASUREMENT_WORKSHEET.md):

- exact printer model;
- nozzle diameter and nozzle condition;
- build-plate type and usable build area;
- black-PETG manufacturer, product line, color, lot/batch if available, age,
  storage, and drying procedure;
- measured 3 ft and 5 ft wall geometry at both proposed shelf heights;
- corner angle, wall bow, ceiling bow, outlet/plug service envelope, and all
  trim or obstructions;
- verified stud or purpose-installed blocking centers, widths, material,
  thickness, and utility-clearance method;
- actual structural screw shank diameter, head/washer outside diameter, length,
  thread embedment, driver bit, and driver-access envelope;
- largest stored-item width, depth, loaded height, loaded weight, quantity, and
  total target contents load per level.

An earlier reference 3MF mentions an A1 mini, 0.4 mm nozzle, and PLA settings.
Those settings do not confirm this project. Do not use embedded or inherited
profiles as evidence. r6 contains no G-code and must remain model-only until
the actual printer, nozzle, plate, and PETG are confirmed.

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

Do not infer fit from nominal clearances. Print, label, measure, and retain:

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

There is no authoritative print-time estimate while those inputs remain
unconfirmed. CAD volume and model-only 3MF object counts are not print-time
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
