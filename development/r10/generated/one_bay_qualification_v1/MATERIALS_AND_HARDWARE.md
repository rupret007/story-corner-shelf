# R10 materials, printed parts, and wall-hardware candidates

> **Procurement and installation hold. Rated load: 0 kg / 0 lb.** The exact
> printed architecture is documented so prototypes can be planned, but no wall
> hardware candidate purchase is released until the blocking/substrate stack
> and fixture plan are reviewed. No closet installation is released until all
> fixture tests and independent review are complete.

## Material contract

| Item | Exact candidate | Rule |
|---|---|---|
| Structural filament | SUNLU standard black PETG, 1.75 mm, ASIN `B0D1KC72YP` | Record label, lot, drying cycle, and spool changes |
| Printer | Bambu Lab A1 mini, physical 0.4 mm nozzle | Textured PEI plate; authored orientation only |
| Filament profile | `SUNLU PETG @BBL A1M 0.4 nozzle` | No silent generic-PETG substitution |
| Process profile | `0.20mm Strength @BBL A1M` | 6 walls, 25% grid, 5 top / 3 bottom layers, Support Off |
| Adhesive | None in the base architecture | Joints remain dry, inspectable, and replaceable |

PLA, PETG from an unrecorded spool, printed wall anchors, drywall screws, deck
screws, hidden metal beams, aluminum tubes, and metal bearing straps are not
approved substitutions. Metal in the active shelf design is limited to the
candidate wall screws and one washer per screw.

## Exact printed architecture count

| Printed article | First 61.25 in wall | Function and credit |
|---|---:|---|
| Palatine PETG support, 31.75 mm across the run | 7 | Primary support; three printed candidate wall bores each |
| Regular cassette half, 126.65 mm printed / 127 mm nominal | 10 | Five paired interior positions across six bays |
| Terminal cassette half, 142.35 mm printed / 142.875 mm nominal | 2 | Includes endpoint and half-seam clearance |
| PETG splice log, 159.1 x 20 x 24 mm | 18 | Three per bay; 79.375 mm engagement per half |
| Independent log retainer, 12 x 28 x 6 mm body; 12.4 x 28 x 10.8 mm saved envelope with integrated cap | 18 | Three per bay, one per log; flush closure and retention only, zero sustained-load credit |
| Bay-local support retainer, 8 x 136 x 6 mm | 12 | 3.8 mm shaft, 8 mm rear dog, 12 mm front handle, 2.4 mm bayonet shift, 4.0 mm proud hand grip; gravity land above stays continuous |
| Additive Roman/Art-Deco ornament | Integrated | Appearance only; zero independent structural credit |

The first wall therefore contains 37 primary bearing pieces plus 30
retention-only keys: 67 printed structural-assembly articles. The active outer bookend
also requires two flush blanks and one comb/hook, for 70 first-wall printed
articles before sacrificial coupons, spares, or destructive-test duplicates.
All 30 keys are retention-only; none receives gravity or bending credit.

Each cassette half has a 152.4 mm depth, 32.0 mm total height, 4.0 mm top
skin, 3.2 mm bottom skin, and at least 4.0 mm rear/center/front load webs. Each
splice log engages 79.375 mm into each half through a captured dovetail channel
with 0.4 mm clearance per face and a positive body shoulder.

Every midpoint and interior support line retains a centered 0.35 mm physical
seam. Each wall endpoint retains 0.35 mm clearance. The fascia is visually
continuous but physically bay-segmented; zero-gap assembly is forbidden.

The top-open midpoint notch is included in the final-mesh geometry proxy. Per
log, net area is 334.800 mm², net centroidal second moment is 8263.957 mm⁴,
and net governing elastic section modulus is 949.016 mm³—72.16%, 36.85%, and
51.35% of their respective gross values. These values describe shape only;
they do not supply a PETG allowable or capacity.

Shallow support locators, the 12 support retainers, decorative covers, and the
18 one-log retainers prevent nuisance movement only. Do not include them when
claiming a vertical load path.

Intermediate supports use a compact 76.2 mm visible corbel drop over the full
hidden 158.75 mm structural wall strap. The first-wall far-left outer bookend
may use a 120.65 mm visible emphasis. The through-side terminal is a replaceable
corner placeholder, not a final measured corner or an outer cable bookend.

## Cable bookend parts—required, not structural

The eventual L-shaped shelf level has exactly two outer cable bookends: the
far-left endpoint of this wall and the far-right endpoint of the later return
wall. The first-wall release activates only the far-left bookend.

| Printed cable article | First-wall prototype | Eventual full L per level |
|---|---:|---:|
| Outer bookend with one fused two-socket receiver | 1 | 2 |
| Inward-facing keyed socket | 2 integrated | 4 integrated |
| Flush blank | 2 | 4 |
| Multi-cable comb/hook module | 1 | 2 |

The keyed gravity fit is 0.4 mm clearance per face with 8 mm service lift/drop.
Unused sockets receive flush blanks. No cable rail, peg, receiver, or module is
allowed on an intermediate support, the through-side terminal/corner
placeholder, or at the inside corner. All cable hardware receives zero
shelf-load credit.

## Candidate wall fasteners and washers

| Item | Exact dimensional candidate | First-wall quantity |
|---|---|---:|
| Wall fastener | GRK RSS Rugged Structural Screw, Climatek, 1/4 in x 3-1/2 in, T25, part `90306` | 21 in any one full-wall assembly; controlled-lot plan below |
| Washer | L.H. Dottie `FW14`, 1/4 in USS flat washer, unhardened carbon steel, zinc plated, ASME B18.21.1; 7.7978-8.3058 mm ID, 18.4658-19.0246 mm OD, 1.2954-2.032 mm thick | Exactly one per screw; standard pack 100; controlled-lot plan below |
| Wall structure | Verified continuous solid-wood blocking or independently engineered equivalent across every screw axis | Field verified; not inferred |

One complete first-wall fixture uses 21 installed candidates of each hardware
type: three screws and three washers at each of seven supports.

There are three authored 7.0 mm candidate bores per support at 19.05 / 79.375 /
139.7 mm below the shelf underside. Each bore is surrounded by a full-solid
27.025 mm outer-diameter surface-bearing washer land. Counterbores are
forbidden. The bores are printed into the model; do not freehand drill or ream
PETG. These are prototype-fixture coordinates, not a drilling schedule or
authorization to drill the closet wall.

Use exactly one listed washer beneath each screw head. Do not stack washers,
countersink PETG, substitute a smaller washer, or crush the printed wall strap
to make a screw appear seated. Final screw suitability depends on actual wood
species/specific gravity, sound blocking thickness, embedment after every
intervening layer, edge/end distances, screw-group spacing, substrate
thickness, installation torque, and the complete shelf load case.

Generic hollow-wall or drywall anchors receive no primary structural credit.
If continuous blocking or an independently engineered equivalent does not
exist at every required screw axis, wall installation stays blocked.

The cited GRK/ICC evaluation does not cover this connection: the screw head
would bear on a loose washer over PETG rather than directly on the evaluated
wood or steel side member. The loose washer, PETG bearing land, effective
penetration, and complete screw group require their own reviewed fixture
program. This complete loose-washer/PETG stack is outside ESR-2442. GRK's
current customer drawing and current ESR also disagree about
the thread length for this nominal screw. Measure and record every controlling
dimension from the received `90306` lot and resolve the discrepancy with GRK
or the independent reviewer before a fixture calculation.

## Controlled-lot hardware allocation

The previous quantity of 30 screws and washers was insufficient. After the
field wall stack is known and a reviewer accepts the fixture plan, procure
**100 exact GRK 90306 screws and one standard 100-pack of Dottie FW14 washers**
as controlled candidate lots. Quarantine them and release only this allocation:

| Reserved use | Fresh screws | Fresh FW14 washers |
|---|---:|---:|
| Gate 5: four sacrificial three-fastener support groups | 12 | 12 |
| Gates 6 and 7: one complete mock wall and its recovered proof cases | 21 | 21 |
| Gate 8: separate fresh creep wall | 21 | 21 |
| Gate 9: separate fresh destructive wall | 21 | 21 |
| Eventual closet installation, only after full release | 21 | 21 |
| Initial unallocated spares | 4 | 4 |
| **Total controlled-lot purchase** | **100** | **100** |

Any damaged item, retry, or reviewer requirement for a fresh Gate 7 consumes
the four spares and requires replenishing the exact candidate before the
21-piece final-install reserve is touched. Passing tests never authorizes
reusing fixture screws or washers in the closet.

## Prototype quantities by gate

To fail fast, do not print the complete wall set first.

1. **Midpoint-interface gate:** one actual left cassette half, one actual right
   cassette half, one actual splice log, and its actual flush-capped retainer.
2. **One-bay gate:** reuse the passing midpoint articles, then add the remaining
   two splice logs, two log retainers, two bay-local support retainers, and two
   supports. These are actual-geometry structural articles; retain them only if
   every dimensional and cycling gate passes.
3. **Cable gate:** one far-left two-socket bookend, two blanks, and one
   comb/hook module.
4. **Tabletop wall gate:** reuse the two conforming compact supports from Gate
   2 and the conforming far-left bookend from Gate 3; then print the remaining
   **four supports** (three compact plus the terminal/corner placeholder), two
   terminal halves, eight regular halves, fifteen splice logs, fifteen one-log
   retainers, and the remaining ten bay-local support retainers. Replace any
   earlier article that was intentionally damaged in testing; a replacement
   does not increase the installed seven-support count.
5. **Wall-fixture and destructive gates:** print fresh conforming sets from the
   same recorded process; never treat a fatigued fit article as a qualification
   article.

The minimum full-size printed demand through a possible released installation
is therefore 284 articles before reviewer-defined material coupons, failed
prints, retests, destructive duplicates, or spares: the initial 70-article
tabletop set, four Gate-5 support fixtures, and three fresh 70-article walls for
Gates 6, 8, and 9. Do not print this inventory in advance; each gate exists to
avoid spending the next tranche after a failure.

Final filament mass, print time, and spool count must come from the released
100%-scale sliced set. Estimates are planning inputs only.

## Tools and records

- digital calipers, steel rule, verified square, straightedge, and feeler
  gauges;
- PETG drying equipment and a temperature/humidity logger;
- T25 driver plus a controlled seating method that cannot crush PETG;
- stud/blocking mapper followed by borescope or open-wall confirmation;
- substrate material and thickness measurement;
- freestanding framed-wall test fixture with the exact blocking and substrate;
- calibrated masses or sealed weighed containers, restraint/barricade, and
  remote observation;
- indicators or fixed rulers at **19 measurement stations**: rear and front at
  all six bay midpoints plus all seven supports; and
- serialized photos, part IDs, slice records, dimensions, load history, and
  failure observations.

## Procurement hard stops

Do not buy qualification hardware until the field wall stack and reviewed
fixture plan exist. Do not release the separate 21-piece closet-install
reserve until all of the following are documented:

1. continuous blocking or an independently engineered equivalent exists at
   every candidate screw axis;
2. the actual substrate material and thickness are known;
3. candidate screw embedment, blocking properties, edge/end distances, group
   spacing, and installation method are accepted for the complete connection;
4. exact PETG lot/process coupons, one bay, and a full tabletop set pass;
5. a fresh framed-wall mockup passes proof, sustained-creep, recovery, and
   destructive gates; and
6. an independent structural reviewer accepts the installed system and defines
   any allowable load.

## Primary product references and their limits

- [GRK RSS product page](https://www.grkfasteners.com/grk-products/structural-framing-screws/rss-rugged-structural-screw)
  identifies the 1/4 in x 3-1/2 in T25 single screw as part `90306` and describes
  its integrated washer head.
- [ICC-ES ESR-2442](https://icc-es.org/wp-content/uploads/report-directory/ESR-2442.pdf)
  evaluates the fastener in identified wood-member connections. It does **not**
  qualify a PETG side member, PETG washer-bearing land, an added loose washer,
  this screw group, or this shelf.
- [L.H. Dottie FW14 product page](https://lhdottie.com/flat-washers/fw14) and
  [manufacturer specification](https://lhdottie.com/pdf/product-specification-sheet/FW14)
  define the selected dimensional washer candidate and its standard 100-pack.
  They do not rate the loose washer over PETG as part of a GRK connection.
- [SUNLU standard PETG product data](https://store.sunlu.com/products/over-6kg-bundle-sale-petg-3d-printer-filament-1-75mm-1kg-roll)
  supplies manufacturer-typical material and process information. Typical
  molded or printed values are not long-term design allowables for this lot,
  orientation, geometry, temperature, or wall connection.

The received screw, washer, filament label, and wood/blocking record control
the fixture. If any physical item differs from this contract, stop and issue a
versioned revision rather than silently substituting it.
