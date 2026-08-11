# R9 first-shelf materials and hardware schedule

## Read this status first

This schedule is for the **first lower shelf only**: the 61.25 in long wall at
the 68 in shelf-top elevation. The design candidate uses six evenly spaced
supports at approximately 12 in pitch and three wall fasteners per support.

The exact screw and washer below are the selected **engineering candidates**.
Their dimensions fit the corrected R9 prototype-v3 holes. They are not yet an
installation release because the framing/blocking map, drywall thickness,
PETG-to-washer clamp test, and proof/load tests are not complete.

Do not substitute a deck screw, drywall screw, printed anchor, or unnamed wall
anchor. Do not drill the wall from a support-center drawing. The present load
rating remains **0 kg / 0 lb**.

## Simple shopping status

### Already selected and safe to have now

| Item | Exact specification | Quantity |
|---|---|---:|
| Filament | SUNLU standard black PETG, ASIN `B0D1KC72YP`, 1.75 mm, four 1 kg spools | 1 purchased 4 kg bundle |
| Printer | Bambu Lab A1 mini with installed 0.4 mm nozzle | 1 |
| Build plate | Bambu Textured PEI Plate for A1 mini | 1 |
| Cleaning supplies | Unscented dish soap, clean water, lint-free towel | 1 set |
| Measuring tools | 6 in / 150 mm digital caliper, 24 in level, tape measure, pencil, painter's tape | 1 each |
| Framing scan tool | Stud finder with live-wire/AC warning capability | 1 |

The 4 kg filament bundle is enough to continue qualification and prototype
work. A production-filament quantity will be published only after the complete
first-shelf meshes exist and their serialized mass has been calculated. Do not
assume every remaining spool is available for retries.

### Selected fastener fixture set—buy only for verification and fixture tests

| Item | Exact specification | Installed | Buy |
|---|---|---:|---:|
| Structural screw | GRK RSS Rugged Structural Screw, Climatek, **1/4 in x 3-1/2 in**, T25, part **90306** | 18 | 24 |
| Flat washer | 1/4 in USS Type A low-carbon steel flat washer, ASME B18.21.1; 0.312 in basic ID, 0.734 in basic OD, 0.051–0.080 in thick | 18 | 24 |
| Driver bit | Impact-rated T25 star-drive bit | 1 | 2 |
| Wood pilot bit | **7/64 in / 2.778 mm** sharp brad-point or twist bit | 1 | 2 |

The six spare screws and washers provide one complete spare support set plus
three additional replacements. A stripped, dropped, bent, corroded, or
overdriven fastener is discarded; it is never counted as installed hardware.

Do not stack extra washers. Do not countersink PETG. Do not use an impact
driver to establish final clamp force. The last seating step must be slow and
controlled, and the washer must remain flat without visibly crushing,
crazing, whitening, or bowing the PETG strap.

## Why the count is 18 screws

The measured first wall has this candidate structure:

- 1 far-left Palatine Moderne bookend support;
- 4 compact Palatine Moderne intermediate supports;
- 1 concealed corner-end support;
- 6 total supports x 3 screws each = **18 installed screws**; and
- 6 total supports x 3 washers each = **18 installed washers**.

The support centers are equally pitched so the geometry is regular and the
shelf spans are similar. Equal spacing does **not** prove equal load sharing;
the final proof plan must still test distributed load, point load, creep, and
recovery.

## Geometry compatibility already checked

The corrected v3 support uses three printed 7.0 mm round-envelope diamond
holes at 16, 80, and 144 mm below the shelf underside. Adjacent centers are
64.0 mm apart.

For the selected GRK 1/4 in RSS screw:

- published outside thread diameter `D` = 0.236 in / 5.994 mm;
- conservative predrilled parallel-grain spacing = `10D` = 59.944 mm;
- modeled spacing = 64.0 mm, leaving 4.056 mm geometric margin;
- published shoulder diameter = 0.244 in / 6.198 mm;
- modeled round clearance envelope = 7.0 mm;
- published head diameter = 0.533 in / 13.538 mm; and
- maximum washer OD including the cited +0.015 in tolerance is 0.749 in /
  19.025 mm, inside the modeled 20.0 mm flat washer land.

The 7/64 in pilot is a candidate for verified SPF/Douglas-fir-like sawn wood.
It falls inside the overlapping predrill ranges derived from the GRK report.
The pilot applies to wood only; the PETG hole is printed and must not be
drilled, reamed, filed, or enlarged.

With a 16.0 mm PETG strap, the maximum 2.032 mm washer thickness, and 5/8 in
drywall, the 3-1/2 in screw leaves approximately **54.99 mm / 2.17 in** of
length beyond the visible stack. That is only stack arithmetic. Actual thread
embedment must be measured from the real assembly and reviewed before use.

## Framing/blocking requirement—the current installation blocker

Six supports at approximately 12 in centers will not ordinarily align with a
typical 16 in stud layout. Therefore the primary design requires **continuous
solid wood blocking or a separately engineered equivalent behind every one of
the 18 screw axes**.

Before wall installation can be released, record all of the following:

- wall substrate material and exact thickness;
- every stud/blocking edge and center at the 68 in shelf level;
- continuous blocking species, grade, thickness, height, moisture condition,
  installation method, and reviewer;
- electrical cable, plumbing, and other concealed-service checks;
- actual screw embedment and edge/end distances;
- driver access and washer seating on a printed support; and
- framed-wall fixture, proof, creep, recovery, and destructive-test results.

If continuous blocking is absent, stop. The alternatives are to open the wall
and add blocking or to commission a separately engineered mounting-rail or
anchor schedule. A generic hollow-wall anchor is not an automatic substitute,
and buying a high advertised load rating does not qualify a grouped,
cantilevered shelf connection.

## Printed-part purchasing/printing boundary

The current `one_bay_prototype_v3` package contains five full-scale tabletop
articles: two handed supports, rear ledger, front beam, and one 160 mm shelf
cassette. Print them only in the documented staged order and only after the
software reports time/material and the operator explicitly approves that job.

The complete 61.25 in shelf set is not emitted yet. Its final part count,
segmentation, PETG mass, print hours, and spare-part count remain pending the
one-bay fit result and the framing decision. Do not multiply the one-bay files
and call the result an installed shelf.

## Authoritative fastener references

- [GRK RSS product page and part 90306](https://www.grkfasteners.com/grk-products/structural-framing-screws/rss-rugged-structural-screw)
- [GRK RSS technical drawing](https://www.grkfasteners.com/getattachment/e22b7f36-824a-482b-9181-06a3b5e0bbbc/GRK-RSS-Customer-Drawing.pdf?ext=.pdf&lang=en-US)
- [ICC-ES ESR-2442](https://www.grkfasteners.com/getmedia/5f4f72a8-8d1f-479b-8ae0-5fc043e2943d/ESR-2442.pdf?ext=.pdf)
- [Fastenal 1/4 in USS Type A washer dimensions](https://www.fastenal.com/content/product_specifications/FW.LC.USS.A.HDG.00.pdf)

Manufacturer literature does not evaluate this complete PETG-through-drywall
connection. The project must retain the physical hardware fixture and final
review gates even when every individual component matches its published data.
