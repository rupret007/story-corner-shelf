# R11 materials, printed articles, and hardware candidates

> **Procurement and installation hold. Rated load: 0 kg / 0 lb.** This is a
> candidate bill of materials for design and qualification planning. Do not buy
> wall hardware, drill the closet wall, install a support, or place load based
> on this list. The field wall stack and independent fixture plan must be
> reviewed first. R11 v1 still hard-forces print, drilling-coordinate release,
> installation, and test-load authorization to false after that review.

## Exact printer and material baseline

| Item | Exact candidate | Required record / rule |
|---|---|---|
| Structural filament | SUNLU standard black PETG, 1.75 mm, ASIN `B0D1KC72YP` | Photograph received label; record lot, drying cycle, ambient conditions, spool changes, and remaining mass |
| Printer | Bambu Lab A1 mini | Record machine, firmware, plate, and physical nozzle |
| Nozzle | Physical 0.4 mm standard-flow nozzle | Do not substitute 0.2, 0.6, 0.8, or hardened/high-flow behavior without a new process qualification |
| Plate | Textured PEI | Clean, empty, cool, correctly seated, and selected in the slicer before every job |
| Filament profile | `SUNLU PETG @BBL A1M 0.4 nozzle` | Map project filament to the physically loaded external PETG; do not silently use Generic PETG |
| Process profile | `0.20mm Strength @BBL A1M` | 0.20 mm layers, 6 walls, 25% grid, 5 top / 3 bottom, Support Off |
| Bed adhesion | 5 mm outer brim, 0.1 mm brim-object gap | Inspect complete brim in Preview; remove only after cooling |
| Adhesive / lubricant | None | Base joinery remains dry, inspectable, reversible, and replaceable |

PLA, an unrecorded PETG spool, resin, wood-filled filament, printed wall
anchors, drywall screws, deck screws, hidden metal beams, aluminum tubes, steel
bearing straps, glue, solvent welding, and friction-only retainers are not
approved substitutions.

Final filament mass, print time, and spool quantity are **unknown until the R11
generator is integrated and every 100%-scale saved model is sliced with the
contract above**. Do not use an R10 slicer estimate or the earlier 5.6 kg
planning estimate as an R11 purchase quantity.

## First-wall kit and installed-state targets

The 28-article count is the reduced-part **supplied-kit design target**, not a
generated inventory claim. The future manifest must enumerate every handed
identity and prove the count. S0 has only two sockets, so only two of the three
supplied cable modules can be installed at once.

| Printed family | Candidate first-wall quantity | Function / credit |
|---|---:|---|
| S0 far-left support/bookend with fused inward two-socket receiver | 1 | Structural support; receiver is additive and nonstructural |
| Ordinary or terminal supports S1-S6 | 6 | Structural supports; S6 remains a first-wall terminal/corner placeholder, not a final inside corner |
| Authored three-rib half-decks | 12 | Bay 0 and bay 5 each use terminal left/right halves: four terminal halves at 162.175 mm; bays 1-4 use eight regular halves at 154.325 mm; never create identities by casual mirroring |
| Positive Palatine/Art-Deco bay keystones | 6 | One per bay; blocks half-to-half X separation only; zero support-capture and sustained vertical-load credit |
| Flush cable blanks | 2 | One normal installed state blanks both S0 sockets; zero shelf-load credit |
| Multi-cable comb/hook | 1 | Alternate module for one S0 socket; representative cables only |
| **Supplied-kit target** | **28** | Qualification duplicates, failures, spares, and test articles excluded |
| **Maximum simultaneously installed** | **27** | 25 structural/retention articles plus exactly 2 of the 3 cable modules |

The two permitted normal module states are two blanks, or one blank plus one
comb/hook. The unused third module is stored off the shelf. It is never placed
in a nonexistent third socket or counted as simultaneously installed.

R11 integrates the three shelf ribs and cross-laps into the 12 half-decks. It
therefore has no separate R10 splice logs, no one-log retainers, and no
support-retainer bars. If physical testing shows an additional printed
structural or retention article is necessary, revise the architecture, count,
start plan, documentation, and qualification program together.

## Safe and target production-start plans

| Plate family | Safe unbatched starts | Target batched starts | Plate population rule |
|---|---:|---:|---|
| Supports | 7 | 7 | One support per plate in authored orientation |
| Half-decks | 12 | 12 | One half-deck per plate in authored flat high-load orientation |
| Keystones | 6 | 1 | Batch all six only after collision-free packing and first-layer separation are proven |
| Cable modules | 3 | 1 | Batch two blanks plus one comb/hook only after packing is proven |
| **Total** | **28** | **21** | Qualification and retries add starts |

Do not batch structural supports or half-decks merely to reduce starts. The
six-keystone and three-module plates remain targets until the generated saved
orientations, brims, and Bambu Preview prove them. Until then, use 28 as the
safe one-article-per-start plan. Batch nesting changes starts only; it does not
alter kit quantity, the 27-installed limit, manifest identities, BOM, or any
qualification article or gate.

## Exact first-wall fastener candidates

| Item | Exact candidate | Installed first-wall quantity if eventually released |
|---|---|---:|
| Wall screw | GRK RSS Rugged Structural Screw, Climatek, 1/4 in x 3-1/2 in, T25, part `90306` | 21 |
| Washer | L.H. Dottie `FW14`, 1/4 in USS flat washer, unhardened zinc-plated carbon steel, ASME B18.21.1; 7.7978-8.3058 mm ID, 18.4658-19.0246 mm OD, 1.2954-2.032 mm thick | Exactly 21; one per screw |
| Wall structure | Verified continuous solid-wood blocking or independently engineered equivalent at every screw axis | Field verified, never inferred |

Each of seven supports has three authored 7.0 mm candidate bores at 19.05,
79.375, and 139.7 mm below the shelf underside. Every bore is surrounded by a
full-solid 27.025 mm outer-diameter surface-bearing land. These are fixture
candidates, not a drilling schedule.

Use one listed washer immediately beneath each screw head. Do not stack
washers, countersink or counterbore PETG, substitute a smaller washer, ream a
printed bore, or crush a strap to make the head appear seated.

Generic drywall/hollow-wall anchors receive no primary structural credit. If
continuous blocking or an independently engineered equivalent is not verified
at all 21 first-wall axes, installation remains blocked. The loose FW14 washer
over PETG connection is outside ESR-2442; catalog screw capacity is not shelf
capacity. Current GRK documents also conflict on thread length, so the received
90306 lot must be measured before any connection calculation.

## Controlled-lot qualification plan

Only after the field wall stack and fixture protocol are independently
reviewed, procure 100 exact GRK 90306 screws and one 100-pack of exact FW14
washers as controlled candidate lots:

| Reserved use | Fresh screws | Fresh FW14 washers |
|---|---:|---:|
| Four sacrificial three-fastener support fixtures | 12 | 12 |
| Complete mock-wall service/proof program | 21 | 21 |
| Separate fresh 1000-hour creep wall | 21 | 21 |
| Separate fresh destructive wall | 21 | 21 |
| Quarantined possible final installation, only after release | 21 | 21 |
| Unallocated spares | 4 | 4 |
| **Total** | **100** | **100** |

Fixture hardware is never reused in the closet. A failed or damaged item uses
the four spares and, if necessary, requires replenishing the exact lot before
the 21-piece final-install reserve is touched.

## Novice tools and records checklist

For neutral generation, printing, and unloaded tabletop fit work only:

- computer with the pinned R11 source revision and Bambu Studio;
- Bambu Lab A1 mini with the physical 0.4 mm nozzle and Textured PEI plate;
- exact, dried, recorded SUNLU PETG above;
- filament scale or recorded spool weights;
- digital calipers, steel rule, verified square, straightedge, and feeler
  gauges;
- soft brush and deburring tool used **only on the sacrificial brim**, never on
  a structural fit;
- clean padded flat table, labels, permanent record sheet, and camera; and
- part IDs, source hash, generated manifest, saved-mesh hash, slice time/mass,
  Preview screenshots, spool/process record, dimensions, and defect photos.

For later reviewed fixtures—not the real wall:

- purpose-built freestanding framed-wall mockup reproducing verified blocking,
  substrate, trim stand-off, and accepted screw installation;
- T25 driver plus a controlled seating method that prevents PETG crushing;
- borescope/open-wall evidence and blocking/substrate measurement tools;
- calibrated masses or sealed weighed containers, restraints, barricades, and
  remote observation;
- temperature/humidity logger and controlled elevated-temperature enclosure;
- displacement indicators or fixed rulers at the 19 specified stations; and
- reviewer-approved measurement, stop, recovery, and destructive-test plans.

## Procurement hard stops

Do not procure qualification hardware until wall structure and the complete
fixture plan are reviewed. Do not release the possible final-install reserve
until every gate in [LOAD_QUALIFICATION.md](LOAD_QUALIFICATION.md) passes and an
independent structural reviewer issues written installation conditions and an
allowable load. Until then: **0 kg / 0 lb, no drilling, no installation**.
R11 v1 additionally holds `print_authorized`,
`drilling_coordinates_released`, `wall_installation_authorized`, and
`test_load_authorized` false in every output; procurement or review does not
change that version boundary.

## Candidate source references and limits

- [GRK RSS product page](https://www.grkfasteners.com/grk-products/structural-framing-screws/rss-rugged-structural-screw)
  identifies the nominal candidate. It does not rate this shelf or PETG stack.
- [ICC-ES ESR-2442](https://icc-es.org/wp-content/uploads/report-directory/ESR-2442.pdf)
  covers identified fastener/wood connections, not the loose-washer/PETG side
  member used here.
- [L.H. Dottie FW14 product page](https://lhdottie.com/flat-washers/fw14) and
  [manufacturer specification](https://lhdottie.com/pdf/product-specification-sheet/FW14)
  define the washer candidate, not its capacity over PETG.
- [SUNLU PETG product data](https://store.sunlu.com/products/over-6kg-bundle-sale-petg-3d-printer-filament-1-75mm-1kg-roll)
  provides typical material information, not a long-term allowable for this
  lot, process, orientation, temperature, or geometry.

Physical received items and reviewer-approved records control. Any difference
requires a versioned revision, not a silent substitution.
