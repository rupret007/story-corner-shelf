# Engineering design — Triadic Palatine r6

## Status and design boundary

Story Corner r6 is an **experimental, unrated candidate system**. This document
describes geometry and intended load paths; it is not a structural analysis,
code approval, or load rating. PETG is anisotropic and creep-sensitive, wall
conditions are unverified, and the target contents load is unknown.

All components inside the shelf assembly are printed black PETG: deck
cassettes, front tied frames, X-corbels with integral bearing caps, keys,
keeper strips, pins, cross-keys, facade, and ornament. The only nonprinted
installed boundary is
suitable metal structural screws with integral heads or compatible metal
washers into verified wood studs or purpose-installed blocking. Production
wall holes remain hard-blocked until the exact fastener, driver, wall finish,
framing, and utility-clearance data are entered.

The two selected L-shaped levels are complete and mechanically independent.
There is no cross-level column, rail, key, or other vertical load transfer.

## 1. Nominal plan and the 3 / 6 / 9 order

The coordinate datum is the intersection of the two finished wall planes. The
60 in wall is the through arm; the 36 in wall is the return. Reference back
clearance is 6.35 mm (0.25 in) on both walls, outer clearance is 3.175 mm
(0.125 in), and depth is 152.4 mm (6 in). The return structure clears the
through arm's complete 13.2 mm locked removable facade, its 4.4 mm axial
service stroke, and a 1.2 mm reserve. The smaller 7.2 mm integral-boss
projection is tracked separately and does not govern the return start.

| Geometry | Through / 5 ft wall | Return / 3 ft wall |
| --- | ---: | ---: |
| Run start from corner datum | 6.35 mm | 177.55 mm |
| Printed run length | 1514.475 mm | 733.675 mm |
| Visible bays | 6 | 3 |
| Pier/X-corbel stations | 7 | 4 |
| Bay span | 241.935 mm | 225.07 mm |
| Start / end pier inset | 31.4325 / 31.4325 mm | 27.0325 / 31.4325 mm |
| Half-bay cassettes | 12 | 6 |

The through cassette owns the 6 x 6 in structural corner. Its chassis front is
158.75 mm from the corner datum, its fixed zero-credit integral bosses reach
165.95 mm, and its full locked removable facade reaches 171.95 mm. The fixed
through rosette's complete axial service sweep reaches 176.35 mm. The return
structure therefore begins at 177.55 mm, retaining a 1.2 mm service-to-
structure reserve and 18.8 mm structural clearance between the chassis
envelopes. A removable,
zero-credit return-corner finish cantilevers 4.4 mm back from that structure:
its all-solid leading plane is 173.15 mm, while its relieved visible base
begins at 173.95 mm. The resulting locked all-solid gap is 1.2 mm and the
intentional visible-base relief is 2.0 mm. This finish must be removed first
before the fixed through rosette moves through its service path.
The first through crown and the structural corner front plane both lie at
158.75 mm, producing zero nominal alignment error. The complete integrated-cap
envelopes retain 30.2325 mm nominal corbel-to-corbel clearance. The structural
chassis, integral boss, locked facade, and service-swept facade retain
21.8325, 14.6325, 8.6325, and 4.2325 mm respectively to the first
perpendicular cap. Exact real-mesh final and representative
perpendicular seating sweeps show zero positive-volume overlap in the nominal
software model, but field fit remains unqualified.

Support centers, measured from the common inside-corner datum, are:

- through arm: `37.7825, 279.7175, 521.6525, 763.5875, 1005.5225,
  1247.4575, 1489.3925 mm`;
- return arm: `204.5825, 429.6525, 654.7225, 879.7925 mm`.

These stations are geometry outputs, not drilling locations. The regular
classical rhythm requires continuous verified wood blocking unless every
station is proven over framing. If framing controls, regenerate unequal
structural bay widths from real stations while preserving three and six
visible arches with independent ornamental half-piers.

## 2. Candidate load path

The intended vertical path is:

`stored object → cassette top skin, coffer ribs, and integral front/rear chords
→ broad cassette pads and integral corbel caps → tied-spandrel candidate
load sharing → X-corbel → printed wall
plate bearing → metal screw head or washer → structural screw → verified wood
stud or blocking → building structure`

No primary vertical load is intentionally assigned to a small snap, cross-key,
alignment key, cosmetic carrier, or pin. Those parts retain, preload, align, or
prevent reverse motion. The 3/6 visual rhythm results in 11 separately
wall-fastened reaction stations on every level.

### Coffer deck

Each level has 18 half-bay deck cassettes. A cassette is nominally 30 mm high,
with 3.2 mm top and bottom skins, 4.8 mm perimeter walls, 3.2 mm internal ribs,
nine depth cells, and no clear bridge greater than 14 mm in the configured
geometry. The physical intermodule seam is 0.35 mm. The largest configured
part axis including its 10 mm comb projection is 162.225 mm, below the design's
180 mm maximum part-axis design envelope.

The cassette train behaves as a segmented diaphragm, not one monolithic
five-foot polymer beam. Sixteen internal seams receive three diaphragm keys
each, for 48 keys per level. Nine crown seams are fixed locally within their
bays; each uses one left-owned removable keeper strip opposite the fixed-right
crown-pin ear. Its single rear-bayonet tongue traps all three keys after the
rearward slide, and a separate underside indexed quarter-turn pin blocks the
forward unlock slide. The visible-front fixed tie has its own separate indexed
pin. Seven inter-bay
seams sit over supported piers and use elongated floating seats with zero
longitudinal tension-splice credit; their integral corbel caps physically trap
all three keys throughout the qualified movement.

### Tied-spandrel arcade

Each visible bay has two printed structural arcade halves. The separate
candidate frame combines a compact 28 mm clevis/capital, minimum 8 mm root
web, and 14 mm curved rib with two broad cassette pads plus one spring shoulder
per half. Those three bearing interfaces seat against the 30 mm cassette and
integral-cap chassis. The full fluted column is a removable visual overlay and
receives zero structural credit.
Total facade/chassis height is 168 mm. The structural spring extrados is at
y = 46 mm and the structural crown extrados touches the cassette underside at
y = 138 mm without solid overlap; the crown intrados is y = 124 mm. The
cassette underside/top are y = 138/168 mm. A removable, zero-credit visual
facade retains the taller y = 152 mm palace crown in a separate depth lane.

The hidden structural rib begins 0.4 mm beyond the actual compact-clevis
housing, at local `u = 28.8 mm`, rather than occupying the support. Its
root-to-physical-crown half-runs are 91.9925 mm through and 83.56 mm return,
both with a 92 mm rise. Their circular radii are 91.992500306 and
83.947139130 mm. The removable visual facade retains the full 241.935 and
225.07 mm bay rhythms and visual radii of 125.527913 and 114.826773 mm. This
geometry is **not** analyzed as a masonry arch or guaranteed
pure-compression form. The closed frame is expected to see mixed compression,
bending, tension, and shear. Its curved rib remains only a candidate contributor
until matched, instrumented arch-on / arch-off full-bay tests show a repeatable
benefit without worsening failure behavior.

### 3:4:5 X-corbels

Every support uses two 12 mm brace paths over a 144 mm horizontal by 108 mm
vertical triangle with a 180 mm diagonal. One runs from `(0,154)` at the upper
wall node to `(144,46)` at the front spring; the other runs from `(0,30)` to
`(144,138)` at the cassette underside. They are unioned through a minimum 24
mm boss at `(82.666667,92)`. The candidate saved orientation places the common
wall-contact face on the build plate: installed run and elevation lie in the
bed plane while wall projection grows in build Z. That creates one connected
first layer, but it changes the layer relationship to the X paths and is not
qualified until the compact-clevis cheeks, locator-ridge onsets, lock-bore
closures, integral bearing-cap transition, every generated layer, and actual
brim/toolpath are verified together on the confirmed printer. Arcade halves
likewise need an exact same-PETG support or sacrificial strategy for their
centered pads, shoulder, and tenons in the saved broad-face orientation. No
support-free claim is made for either family.

The wall plate is intentionally solid in development geometry. Provisional y
stations 42, 84, and 126 mm are layout studies only. Actual bores, head seats,
bosses, driver tunnels, and screw locations must be regenerated after measuring
the screw shank, head or washer, embedment, driver, wall finish, framing, and
utilities. A printed surface rail is not a substitute for verified framing.

## 3. Final-X vertical-lift joinery

The active assembly has zero whole-half travel along the run. Holding a half
at its final X/run coordinate, lift it vertically so all three interfaces enter
together:

- two 18 x 8 x 22 mm top tenons enter 18.8 x 8.8 mm open-bottom cassette
  receivers and seat two 22 x 16 mm compression pads;
- one 20 x 8 x 22 mm spring tenon enters a 20.8 x 8.8 mm open-bottom pier
  receiver and seats a 28 x 16 mm shoulder.

The two top-tenon centers from the crownward physical end are
`50, 80.5925 mm` on the through arm and
`49.6, 72.16 mm` on the return. Each half receives two top positive quarter-turn
cross-keys and one spring cross-key inserted and indexed from the visible
front, with at least 75 mm of straight service access. The cross-keys resist
withdrawal only; they receive zero vertical shelf-load credit and may not pull
an unseated shoulder into position.

The tighter return interface uses a 112.535 mm nominal half-bay and 112.36 mm
physical crown half. Its `49.6 / 72.16 mm` top-key centers retain 3.76 mm of
receiver web, 3.36 mm between the adjacent boss and handle, 4.2 mm from the
receiver to the body, 4.0 mm from the handle to the body, a 7.0 mm keyway
margin, a 30.625 mm cassette-pier ligament, and a 0.4 mm root pad. The compact
19.2 mm handle contains an authored folded-U path of `17.1 + 1.6 + 7.1 =
25.8 mm`; its conservative 20.0 mm strain-screen length retains the 0.0288
proxy. These are geometry screens, not physical flexure qualification.

The two halves do not slide through one another at the crown. After they are
seated, a 72 x 48 x 6.4 mm rear bridge inserts **upward from below** into two
open-bottom keyways and stops on integral shoulders. One 5 mm PETG pin in a
5.4 mm fixed-right-half hole prevents drop or reverse slide. A second fixed pin
is prohibited because it would overconstrain the moving fit. The pin receives
zero shelf-load credit and must remain accessible without removing a cassette
or ornament. The crown bridge pin is saved with its shaft axis parallel to the
build plate, its split plane perpendicular to the plate, and its round head
and circular cross-section vertical/tangent to the plate. This orientation is
neither support-free nor production-qualified and requires the physical
same-PETG slicer/orientation coupon gate.

At the return crown, the regenerated structural parent rib is
`120.239805561..131.231041356 mm`; the through/return common guaranteed band is
`120.646226096..131.231041356 mm`. The shifted lug occupies
`120.9..127.9 mm`, its open-bottom service sweep occupies
`72.9..127.9 mm`, and the worst-case hard-stop roof remains
3.331041356 mm. The shift preserves the 7.0 mm engagement without lowering the
4.0 mm ligament threshold.

This sequence replaces the rejected 12 mm whole-half longitudinal slide, which
created a crown collision and deadlocking assembly path.

## 4. Rail-free seams and thermal movement

The release-candidate baseline deliberately has no separate stitch rails,
rail pins, or run-end ties. The geometry-current study would add 119
unqualified objects per level, lacked a defined cassette attachment, and
risked forming a second rigid
thermal loop. It is retained only as optional research and receives no
installed-object or load-path credit. Re-entry requires a named rail-on versus
rail-off full-bay comparison showing a repeatable stiffness, recovery, or
failure-mode benefit while preserving the full 1.2 mm supported-pier travel.

The active shelf instead relies on the integral front and rear chords within
each two-skin cassette, three diaphragm keys at every seam, one fixed front tie
at each crown, and direct corbel support at every pier boundary. The nine crown
seams are fixed only within their independently supported bays. At the seven
supported pier seams, the crownward cassette side is the local fixed datum;
the springward side uses an elongated pocket and lock seat over the integral
corbel cap. Cap contact is vertical bearing/sliding only and receives zero
axial credit.
No ornament, keeper, adhesive, end closure, or optional-study part may bypass
that movement and turn the five-foot run into one thermally locked PETG chord.

## 5. Corner and level independence

The corner is a visual meeting, not a rigid structural elbow. The through arm
owns the corner volume. The return remains separately corbel-supported. A
nine-petal rosette is fixed to the through-side finish and its return mate
floats; neither receives mechanical L-joint or structural credit. This avoids
forcing two bowed or non-square walls into one PETG plane.

Likewise, the provisional +12 in and +33 in shelf-top levels align visually
but remain mechanically separate. The upper level is installed first because
its cross-key, crown-pin, driver, and removal paths must be reachable before the
lower level occupies the working space.

## 6. Classical structure and isolated detail

Roman arcade, pier, and entablature geometry form the visible candidate
chassis. Greek proportion and six-flute pier overlays discipline the facade.
Egyptian influence is limited to a shallow upper cavetto. Restrained Art Deco
sunbursts, three nested chevrons, and a stepped visual keystone create a
secondary layer.

Fine archivolts, flutes, dentils, paterae, rosettes, cavetto moldings,
sunbursts, chevrons, seam keys, and the visible keystone attach to isolated
carriers. The right carrier owns the visual keystone while the left floats at
the seam. All 33 ornament objects per level are removable and receive zero
structural credit. Drawings govern geometry and access; the artist rendering
is illustrative only.

## 7. Original named-mechanism reconciliation

The governing request named several joint concepts before collision, thermal,
service-access, and inventory sweeps were complete. They are reconciled here
explicitly; none is silently claimed as an installed part when the final
release-candidate topology uses a different mechanism.

| Original requested mechanism | r6 release-candidate resolution | Reason and structural-credit boundary |
| --- | --- | --- |
| Sliding saddle plus separate saddle-retention pin | **Integrated caps replace the sliding saddles/pins.** Each X-corbel owns a full-width broad bearing cap with tight/elongated locator pockets and two removable cassette locks. Installed counts are 11 caps integral to the corbels, 22 locks, 0 sliding saddles, and 0 saddle pins per level. | The separate stack added two tolerance-sensitive interfaces, dead mass, and another pin service path without improving broad bearing. The integral cap carries candidate compression bearing; locators and locks retain/alignment only and receive no independent load rating. |
| Floating pier diaphragm/alignment keys plus a floating front entablature key | **The fixed-diaphragm/cap topology replaces floating front keys.** Each of nine crown seams has three fixed diaphragm keys, a positively pinned keeper strip, and one separately pinned visible-front tie. Each of seven supported pier seams instead has three elongated diaphragm keys trapped by the integral cap through 1.2 mm travel and has 0 front entablature keys. | The proposed floating front key's underside access collided with the cap/lock service envelope and could create an unintended axial tie. Direct cap support plus trapped elongated diaphragm keys preserves alignment and thermal travel. All keys, keepers, ties, and pins receive zero independent vertical-load credit. |
| Comb and half-lap stitch-rail joinery | The half-lap rails, rail comb/locator features, overlap pins, and run-end ties remain **noninstalled optional research geometry**. The study has 41 rail segments and 37 overlap joints represented by 74 pins, plus 4 end ties: 119 optional printed objects per level. Installed package count and structural credit are both zero. | The active cassettes already provide integral front/rear chords, three seam keys, fixed crown ties, and direct pier support. Adding the rail study would introduce an unqualified second thermal/load loop. It may return only after a named rail-on/rail-off test proves benefit while retaining the full 1.2 mm movement reserve. |

Broad shoulders, mortise/receiver seats, removable keys, pinned keeper/tie
interfaces, and asymmetric handed parts preserve the requested serviceable
"Lincoln Logs" character. The table records deliberate engineering
substitutions; it does not convert an untested joint into capacity evidence.

## 8. Physical-object reconciliation

Interfaces and integral features are not counted as separate objects. The 36
top tenons and 18 spring tenons per level are integral to arcade halves; their
receivers are integral to cassettes and corbels. The 16 cassette seams are
interfaces.

| Installed family | Per level |
| --- | ---: |
| Deck cassettes | 18 |
| Arcade halves | 18 |
| X-corbels with integral bearing caps, plus cassette locks | 33 |
| Top and spring positive quarter-turn cross-keys | 54 |
| Diaphragm keys, crown keeper strips, and fixed-crown ties | 66 |
| Indexed keeper/front-tie quarter-turn pins | 18 |
| Crown bridges and crown pins | 18 |
| **Chassis, joinery, and retention subtotal** | **225** |
| Removable ornament carriers/overlays/end/corner pieces | 33 |
| **Installed total per independent level** | **258** |
| **Selected two-level installed total** | **516** |

Coupons, sacrificial mockups, destructive specimens, and recommended spares
are outside these installed totals.

## 9. What can and cannot be claimed

Geometry tests may show watertight meshes, deterministic packages, fit
clearances, collision-free paths, and consistency between configuration,
inventory, drawings, and manifests. They cannot establish capacity, long-term
creep performance, wall adequacy, fastener pullout, or safe overhead use.

No numerical load claim may be made until the actual wall, fasteners, printer,
orientation, black PETG, service temperature, target load, written stop limits,
full-bay behavior, 90-day creep, 72-hour recovery, and teardown evidence are
qualified. Even then, any published rating needs an explicit engineering basis
and a defined scope; passing one prototype is not automatically a general
rating.

The preserved `reference/hybrid_r5/` architecture remains a fallback rather
than hidden evidence for r6. Results from one architecture may not be
transferred to the other.
