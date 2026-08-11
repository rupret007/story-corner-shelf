# R9 printer kickoff — controlled Stage 0

This is the operator handoff for the **first physical print only**. It turns the
frozen R9 PETG settings into a deliberate Bambu Studio preflight while keeping
the person at the printer in control of every physical action.

> **QUALIFICATION-ONLY HARD STOP:** Stage 0 produces small clearance-test
> articles. It does not authorize a full shelf, duplicate/production parts,
> wall drilling, installation, hanging, or stored load. R9 remains unrated at
> **0 kg / 0 lb**. Passing Stage 0 is only permission to consider the next
> documented qualification stage.

## What the user does before kickoff

Do not open a print job until every item below is true.

- [ ] The printer is a **Bambu Lab A1 mini** with the **0.4 mm nozzle**
      installed and is idle, connected, and free of another job.
- [ ] The installed build plate is the **Textured PEI Plate**, is empty, and
      has been cleaned using the plate maker's instructions.
- [ ] PLA has been unloaded. The loaded spool's physical label says **SUNLU
      PETG**, **black**, not PLA, PETG+, high-speed PETG, matte PETG, or another
      formulation.
- [ ] The spool matches Amazon ASIN `B0D1KC72YP`, selected variant
      **4 kg / 2 Black + 2 Black**: four black 1 kg spools, 1.75 mm
      +/-0.02 mm. The bound listing is
      `https://www.amazon.com/dp/B0D1KC72YP?th=1`.
- [ ] The spool lot or other unique spool identifier has been written in the
      print record. A web listing is not a substitute for checking the label;
      listing variants can change.
- [ ] The drying cycle has been recorded. The R9 baseline is **50 C for 6–8
      hours**, but only when both the received spool label and dryer manual
      permit it. Never exceed the lower stated temperature limit. Stop on any
      conflict instead of guessing.
- [ ] After drying, the PETG has stayed sealed or in a dry box until loading.
- [ ] The user has physically loaded the PETG through the intended feed path,
      completed the printer's normal load/purge routine, and confirmed that
      the extruded material is black PETG.
- [ ] The user can remain near the printer for the first layer, can reach the
      printer's Stop control, and will keep hands away from the hot end and
      moving axes.

If any box is false or uncertain, stop. Codex cannot identify a spool, clean a
plate, install a nozzle, load filament, inspect a purge, or make the printer's
physical area safe.

## The exact phrase that begins software preparation

Only after the physical checklist is complete, tell Codex exactly:

```text
PETG loaded—start Stage 0
```

That phrase authorizes Codex to perform **software preparation only**: open the
exact neutral 3MF, select the A1 mini, enter/verify the PETG and process
settings, slice, and inspect Preview. Codex will directly operate the visible
Bambu Studio controls when macOS Accessibility access is available. If that
access is unavailable or a control cannot be verified reliably, Codex will
stop at that control, give the exact visible selection, and verify the user's
screen rather than pretending the change was made. The phrase is **not**
authorization to send a job to the printer or start a physical print.

Codex must stop after Preview, report the selected printer/plate/filament,
settings, warnings, estimated time, and material estimate, and ask for explicit
authorization before Send/Print. A clear user response authorizing that exact
Stage 0 file is required. Silence, the kickoff phrase above, a general “looks
good,” or authorization for a previous plate is not sufficient. The corrected
Stage 0 key is a separate physical job and requires a separate authorization.

## Exact first file — do not substitute the catalog or an STL

Start a new project and import exactly one object from this repository-relative
path:

```text
development/r9/generated/qualification_v5/stage0_individual_model_only_3mf/MODEL_ONLY_r8_clearance_ladder_receiver.3mf
```

Verify the file's byte count, SHA-256, object name, and geometry digest against
the **live v5 `manifest.json`** in the parent bundle before opening it. Do not
copy a digest from a message or an older package.

Use the individual neutral 3MF only. Do not open the combined R9 catalog, use
the STL, copy an old arranged plate, or use G-code from another machine or
person. The receiver's saved print pose is **broad rear face down; source X/Z
relabelled to bed X/Y**. Preserve that pose at 100% scale.

## Frozen Bambu Studio setup

The neutral 3MF carries geometry, not a trusted machine or material profile.
Start with a new project and verify every value below; never inherit a PLA
project.

| Bambu Studio control | Required Stage 0 value |
|---|---|
| Printer | `Bambu Lab A1 mini 0.4 nozzle` |
| Nozzle diameter | 0.4 mm |
| Plate type | `Textured PEI Plate` |
| Filament | `SUNLU PETG @BBL A1M 0.4 nozzle` |
| Process starting point | `0.20mm Strength @BBL A1M` |
| Object scale | 100% on X, Y, and Z; never auto-scale |
| Saved orientation | Preserve the imported pose; never auto-orient |
| Layer height | 0.20 mm |
| First-layer nozzle temperature | 250 C |
| Other-layer nozzle temperature | 245 C |
| Textured-PEI bed temperature | 60 C |
| Flow ratio | 0.94 |
| Maximum volumetric speed | 9 mm^3/s |
| Normal fan | 10% minimum / 30% maximum |
| Overhang fan | 90% |
| Wall loops | 6 |
| Top shell layers | 5 |
| Bottom shell layers | 3 |
| Sparse infill | 25% grid |
| Support | Off for the receiver and corrected 0.4 key |
| Brim type | Outer brim only |
| Brim width / object gap | 5.0 mm / 0.1 mm |
| Plate-edge reserve | At least 2.0 mm beyond the brim on every edge |
| First-article arrangement | One exact Stage 0 part on the plate |

Leave unlisted controls at the selected `0.20mm Strength @BBL A1M` starting
point. Do not improvise a speed, seam, support, scale, orientation, repair, or
flow change to clear a warning. A changed process must be documented and must
restart the applicable qualification record.

The installed Bambu Studio 02.07.01.62 system catalog contains the exact SUNLU
profile, but it may not yet be enabled in the Prepare dropdown. Open filament
selection/Manage Presets, enable `SUNLU` →
`SUNLU PETG @BBL A1M 0.4 nozzle`, and then select it. Reopen its settings and
verify the full table above; the profile name alone is not evidence.

### If the SUNLU preset cannot be enabled

Do not choose PLA and do not select a similarly named PETG formulation. In
Bambu Studio, duplicate `Generic PETG`, name the duplicate
`SUNLU PETG @BBL A1M 0.4 nozzle`, enter every filament-related value in the
table above, save it, then reopen the saved preset and verify the values again.
Apply the process values separately from `0.20mm Strength @BBL A1M`.

If Studio prevents an exact required entry or a setting name cannot be mapped
unambiguously, stop and report the discrepancy. Do not choose the nearest
value without approval and a revised qualification record.

## Prepare-mode gates before slicing

Codex must verify all of these in Prepare before selecting Slice Plate:

- [ ] The active machine says A1 mini / 0.4 mm and the active plate says
      Textured PEI.
- [ ] Exactly one object is present and its name traces to
      `r8_clearance_ladder_receiver`.
- [ ] X/Y/Z scale is exactly 100%, the imported saved pose is unchanged, and
      the receiver's broad rear face is on the plate.
- [ ] Studio did not auto-arrange, auto-orient, auto-scale, mirror, merge,
      auto-repair, or replace the model.
- [ ] The active filament is the verified SUNLU standard PETG preset and no
      PLA filament remains assigned to the object or plate.
- [ ] The complete temperature, flow, speed-limit, cooling, strength, infill,
      support, and brim table above has been checked.
- [ ] The outer brim and the required 2.0 mm additional edge reserve fit
      entirely inside the usable plate and avoid exclusion zones.
- [ ] There are no unresolved model, manifold, floating-object, plate-fit, or
      exclusion-zone warnings.

Failure of any item is a stop, not permission to use a one-click repair.

## Preview gates after slicing

Inspect Preview layer by layer. The job is eligible to ask for physical-print
authorization only when every gate passes.

1. Preview contains one receiver and one outer brim, with no second object,
   purge artifact represented as a part, or remnant from an old project.
2. The first layer is a continuous footprint in the saved orientation; the
   part does not begin with a disconnected island.
3. No later layer begins as an unexplained disconnected island, and no required
   feature is omitted from the toolpath.
4. Support remains Off. If Preview appears to require support in the frozen
   receiver pose, stop and report the mismatch rather than enabling support.
5. The brim stays on the printable surface, avoids exclusion zones, and leaves
   at least 2.0 mm of additional reserve to every bed edge.
6. There is no collision, outside-plate, empty-layer, toolpath, slicing, or
   model-repair warning.
7. The Preview summary still reports the exact PETG filament assignment. The
   estimated time and material quantity are recorded for the authorization
   prompt.

Codex should capture or retain a Preview screenshot and the verified settings
summary with the print record. A successful slice is software evidence only;
it does not prove the first layer, dimensions, fit, or strength.

## Physical-print authorization and operator handoff

After all Preview gates pass, Codex must ask a narrow question naming the exact
file, printer, and material, for example:

> Preview passed for
> `MODEL_ONLY_r8_clearance_ladder_receiver.3mf` on the A1 mini using black
> SUNLU standard PETG. Do you explicitly authorize me to send and start this
> Stage 0 receiver print now?

Codex may select Send/Print only after an unambiguous affirmative response to
that question. Before the final Start/Print action, verify the physical
filament-slot mapping still points to the loaded SUNLU PETG and the destination
device is the intended A1 mini. Any printer warning or unexpected mapping is a
new stop.

Map the feed path explicitly: when using the external spool holder, select the
external spool and do not map the job to AMS Lite; when using AMS Lite, select
the exact slot containing the verified black SUNLU PETG. The user must confirm
the physical path and slot in person before the print starts.

In the print dialog, set **Bed Leveling On** and **Timelapse Off**. Leave
**Flow Dynamics Calibration On** for the first Stage 0 print and record that
choice. Flow Dynamics changes pressure advance; it does not replace or silently
rewrite the frozen 0.94 flow ratio. If any later plate changes that calibration
policy or adopts a different calibrated process, treat it as a process change,
record it, and repeat the applicable clearance gate before qualifying parts.

Once the printer starts, control passes to the human operator:

1. Stay with the machine through the complete first layer. Watch for poor
   adhesion, nozzle dragging, blobs, lifted edges, wrong-color material, or an
   unexpected purge/print location.
2. Use the printer's Stop control immediately if the first layer is unsafe or
   clearly defective. Do not reach into a moving or hot printer.
3. Report the stop/failure and preserve a photo; do not quietly change scale,
   temperature, flow, support, or orientation and retry.
4. At completion, let the plate and PETG part cool fully before removal. Do
   not flex, fit, or measure a hot part.
5. Photograph the cooled receiver, record the Studio version, spool lot, dry
   cycle, settings confirmation, result, and photo identifier, then inspect it
   using `PRINT_FIRST.md` and `TEST_PROTOCOL.md`.

Codex cannot watch the physical first layer, smell overheating, hear a
mechanical problem, remove the cooled part, or judge hidden damage. The user is
the on-site safety operator and may stop the printer at any time.

## Remaining Stage 0 sequence

Only after the receiver is cool, identified, photographed, and passes the
cooled-part inspection may the corrected 0.4 key be prepared. Use one
individual neutral 3MF on the first-article plate:

1. `MODEL_ONLY_r9_gate0_clearance_key_0p4_handle_down.3mf`

It is in the same v5 Stage-0 directory as the receiver. Preserve the imported
handle-down pose at 100% scale with Support Off and repeat the complete Prepare,
Preview, authorization, first-layer, cooling, record, and inspection gates.

Before fit, inspect Preview layers 28–30 and the cooled keyed-head wings. Stop
on a floating-cantilever warning, loose strand, curl, torn perimeter, layer
separation, or visible droop. The authored interface is 0.4 mm per face; the
key must fully seat and release
by hand for ten gentle cycles without tools, cracking, whitening, permanent
set, lost engagement, or increasing bind. Do not print the legacy frozen R8 v2
key files; their identity saved pose has a large handle cantilever. If 0.4
fails, stop Stage 0, preserve the failed record, and correct the
printing process. Never sand a key, enlarge the receiver, rescale a model, or
compensate in CAD to manufacture a pass.

## Stop after Stage 0

Even a clean 0.4 mm fit is not permission to print a complete shelf or work on
the wall. The current R9 release contains qualification coupons and tabletop
studies only; a complete shelf set, wall-bore template, installed hardware
schedule, verified framing/blocking map, target contents load, and physical
proof/creep/destructive evidence do not exist. Continue only under the next
exact versioned qualification instructions.
