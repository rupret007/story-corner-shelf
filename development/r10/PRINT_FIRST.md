# R10 print-first handoff — fail fast

> **Stop before every physical print.** Slicing and Preview inspection do not
> authorize printer motion. A fresh, explicit human “yes, print this job” is
> required after the exact plate, material mapping, settings, Preview, and
> printer state are confirmed. Permission from an earlier job does not carry
> forward. This rule applies even when a retry appears unchanged.

This sequence produces one actual 254 mm Lincoln-log shelf cell and the
separate first-wall S0 cable candidate as quickly as responsible qualification
allows. It is not a miniature or a cosmetic mockup. It is also not a complete
six-bay production set, a wall-installable release, a drilling schedule, or a
load-rated shelf. Current rating: **0 kg / 0 lb**.

Inventory context: this qualification bundle contains 16 articles—12 for one
actual bay and four for the separate S0 cable gate. A future complete first
wall contains exactly 70 printed articles: seven supports (including S0 as one
of the seven), 12 cassette halves, 18 splice logs, 18 integrated-flush-cap log
retainers, 12 bay-local support retainers, two flush blanks, and one comb/hook.
Do not mistake the qualification bundle for authorization to print that set.

## 1. Build and verify the neutral bundle

From the repository root, generate the deterministic qualification bundle:

```sh
.venv/bin/python development/r10/generate_one_bay_qualification.py
```

The expected output directory is
`development/r10/generated/one_bay_qualification_v1/`. Generation creates
neutral STL and model-only 3MF geometry; it does not slice, send, or print.
The command refuses to replace an existing bundle.

Before opening a model, verify:

- `manifest.json`, `validation.json`, and `release_status.json` exist;
- `release_status.json` still says `print_authorized: false`,
  `wall_installation_authorized: false`, and `rated_load_kg: 0.0`;
- `individual_model_only_3mf/` contains the 16 files listed below; and
- no G-code, BG-code, toolpath, or embedded slicer profile is present.

Never print
`MODEL_ONLY_R10_ONE_BAY_QUALIFICATION_CATALOG_NOT_A_PRINT_PLATE.3mf`. It is an
off-plate inspection catalog, not an A1 mini plate.

## 2. Lock the printer, material, and process before each slice

For every individual job, confirm all of these fields rather than relying on a
previous plate:

| Field | Required value |
|---|---|
| Printer | Bambu Lab A1 mini |
| Physical nozzle | 0.4 mm |
| Plate | Textured PEI plate, clean and clear |
| Material | SUNLU standard black PETG, 1.75 mm, ASIN `B0D1KC72YP` |
| Project filament mapping | `SUNLU PETG @BBL A1M 0.4 nozzle` mapped to the physically loaded PETG |
| Process | `0.20mm Strength @BBL A1M` |
| Layer height | 0.20 mm |
| Walls | 6 |
| Infill | 25% grid |
| Top / bottom | 5 top layers / 3 bottom layers |
| Supports | Off |
| Brim | 5 mm outer brim, 0.1 mm brim-object gap |
| Scale | 100% in X, Y, and Z; millimetres; never auto-scale |
| Plate population | One named article per plate for this qualification |

Do not silently substitute Generic PETG, another spool, another nozzle,
another plate, another process, or a repaired/scaled mesh. Record the PETG lot,
drying cycle, ambient conditions, printer, plate, nozzle, profile revisions,
and every override.

For each file: import only that individual model-only 3MF, preserve its saved
orientation, slice, and inspect Preview layer by layer. Confirm the first layer
is continuous, every intended opening remains open, there is no floating
island, the slicer did not repair or resize the mesh, Support remains Off, and
the estimated material/time are recorded. Then stop at the final Send/Print
control and obtain fresh permission.

Let PETG and the plate cool before removal. Inspect the removed article and
clear the plate before preparing the next job. A print cancellation or failure
requires a new inspection, a newly sliced/reviewed job when anything changed,
and fresh permission before retrying.

## 3. Exact individual files and saved orientations

All paths below are inside `individual_model_only_3mf/`. Support is Off for
every article.

| Exact file | Authored orientation |
|---|---|
| `MODEL_ONLY_r10_one_bay_left_support.3mf` | `wall_face_down_rotated_45_degrees` |
| `MODEL_ONLY_r10_one_bay_right_support.3mf` | `wall_face_down_rotated_45_degrees` |
| `MODEL_ONLY_r10_one_bay_left_cassette_half.3mf` | `solid_support_end_diaphragm_on_plate` |
| `MODEL_ONLY_r10_one_bay_right_cassette_half.3mf` | `solid_support_end_diaphragm_on_plate` |
| `MODEL_ONLY_r10_one_bay_rear_splice_log.3mf` | `flat_dovetail_side_on_plate` |
| `MODEL_ONLY_r10_one_bay_center_splice_log.3mf` | `flat_dovetail_side_on_plate` |
| `MODEL_ONLY_r10_one_bay_front_splice_log.3mf` | `flat_dovetail_side_on_plate` |
| `MODEL_ONLY_r10_one_bay_rear_log_retainer.3mf` | `largest_flat_face_on_plate` |
| `MODEL_ONLY_r10_one_bay_center_log_retainer.3mf` | `largest_flat_face_on_plate` |
| `MODEL_ONLY_r10_one_bay_front_log_retainer.3mf` | `largest_flat_face_on_plate` |
| `MODEL_ONLY_r10_one_bay_left_support_retainer.3mf` | `largest_flat_face_on_plate` |
| `MODEL_ONLY_r10_one_bay_right_support_retainer.3mf` | `largest_flat_face_on_plate` |
| `MODEL_ONLY_r10_first_wall_s0_inward_two_socket_additive_bookend_candidate.3mf` | wall face down, rotated 45 degrees, additive receiver ramp upward |
| `MODEL_ONLY_r10_first_wall_socket_0_flush_blank.3mf` | local minimum-Z broad side on plate |
| `MODEL_ONLY_r10_first_wall_socket_1_flush_blank.3mf` | local minimum-Z broad side on plate |
| `MODEL_ONLY_r10_first_wall_multi_cable_comb_hook.3mf` | local minimum-Z broad side on plate |

Do not rotate a part merely to make the slicer warning disappear. Stop and
resolve the warning against the authored mesh and orientation.

## 4. Fastest responsible print order

The rule is simple: print only enough to expose the next expensive failure.
Each line is a separate plate and needs fresh permission.

### Gate A — midpoint Lincoln-log interface

1. `MODEL_ONLY_r10_one_bay_left_cassette_half.3mf`
2. `MODEL_ONLY_r10_one_bay_right_cassette_half.3mf`
3. `MODEL_ONLY_r10_one_bay_rear_splice_log.3mf`
4. `MODEL_ONLY_r10_one_bay_rear_log_retainer.3mf`

Assemble those four parts off the supports using Steps 1–3 of `ASSEMBLY.md`.
The log must reach its positive shoulder; the retainer must lower through the
left-half top access; its integrated cap must finish flush; and the right half
must slide on without force and capture the key. Perform ten gentle dry cycles.
Stop before printing duplicates if this gate fails.

### Gate B — one support-capture interface

5. `MODEL_ONLY_r10_one_bay_left_support_retainer.3mf`
6. `MODEL_ONLY_r10_one_bay_left_support.3mf`

Reuse the assembled cassette. Confirm broad, direct bearing on the support
capital. Insert the retainer straight from the front, rear-dog first, and shift
it exactly 2.4 mm toward the bay. Confirm the positive walk-out stop. To remove,
shift it 2.4 mm away from the bay and pull straight forward. Perform ten gentle
unloaded cycles. The retainer receives no gravity or bending credit.

### Gate C — complete one actual shelf cell

7. `MODEL_ONLY_r10_one_bay_right_support.3mf`
8. `MODEL_ONLY_r10_one_bay_center_splice_log.3mf`
9. `MODEL_ONLY_r10_one_bay_front_splice_log.3mf`
10. `MODEL_ONLY_r10_one_bay_center_log_retainer.3mf`
11. `MODEL_ONLY_r10_one_bay_front_log_retainer.3mf`
12. `MODEL_ONLY_r10_one_bay_right_support_retainer.3mf`

Now assemble all 12 core articles exactly as `ASSEMBLY.md` specifies. Verify
all three flush caps, both 2.4 mm bayonet captures, the 0.35 mm physical
midpoint seam, full bearing at both 15.70 mm contacts, flatness, squareness,
and ten complete unloaded assembly/disassembly cycles.

This is the first actual shelf cell. Passing it does not authorize a second
bay, the full first wall, wall hardware, drilling, installation, proof load,
creep load, stored load, or a load rating.

### Gate D — separate far-left S0 cable candidate

13. `MODEL_ONLY_r10_first_wall_socket_0_flush_blank.3mf`
14. `MODEL_ONLY_r10_first_wall_s0_inward_two_socket_additive_bookend_candidate.3mf`

Use the first blank to expose socket-fit failure before printing the remaining
modules. Test it in socket 0 and socket 1, one at a time: move straight inward
at the upper entry, lower exactly 8 mm, lift 8 mm, and move straight outward.
Complete ten cycles in each socket.

Only if both sockets pass:

15. `MODEL_ONLY_r10_first_wall_multi_cable_comb_hook.3mf`
16. `MODEL_ONLY_r10_first_wall_socket_1_flush_blank.3mf`

Cycle the comb/hook ten times in each socket, one socket at a time. Then verify
the two furniture states: both sockets flush-blanked, and one comb/hook plus one
blank. Cable parts receive zero shelf-load credit. Do not attach the bookend to
a wall and do not treat this test as room-clearance qualification.

## 5. First-article inspection record

Copy one row per physical article. “Pass” requires every cell to be complete.

| Job / file | Photo ID | Spool lot + dry record | 100% scale | Saved orientation | Support Off | Slice time / mass | Cooled before removal | Dimensional check | Defects / slicer warnings | Pass / fail |
|---|---|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |

At minimum, inspect for warp, cracks, layer separation, under-extrusion,
contamination, whitening, missing features, first-layer damage, dimensional
drift, proud flush caps, blocked channels/keyways, bore damage, and loose
fragments. Record measurements before any fit cycle.

## 6. One-bay unloaded cycling record

Use one row for each complete assemble/disassemble cycle. Do not add load.

| Cycle | Three shoulders fully seated | Three integrated caps flush | Right-half slide by hand | Left support key inserted + 2.4 mm toward bay | Right support key inserted + 2.4 mm toward bay | Both reverse paths clean | Dust / whitening / cracks / looseness | Pass / fail | Photo ID |
|---:|---|---|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |  |  |  |
| 8 |  |  |  |  |  |  |  |  |  |
| 9 |  |  |  |  |  |  |  |  |  |
| 10 |  |  |  |  |  |  |  |  |  |

## 7. Cable-module cycling record

Each module must complete ten cycles in each socket. Keep the other socket
empty during its first qualification. One cycle is straight inward at the
upper entry, 8 mm down, 8 mm up, and straight outward.

| Article | Socket | Cycles completed | Gravity seat complete | Reverse path clean | Bind / wear / damage | Pass / fail | Photo ID |
|---|---:|---:|---|---|---|---|---|
| Socket 0 flush blank | 0 |  |  |  |  |  |  |
| Socket 0 flush blank | 1 |  |  |  |  |  |  |
| Multi-cable comb/hook | 0 |  |  |  |  |  |  |
| Multi-cable comb/hook | 1 |  |  |  |  |  |  |
| Socket 1 flush blank | 0 |  |  |  |  |  |  |
| Socket 1 flush blank | 1 |  |  |  |  |  |  |

## 8. Stop conditions and next boundary

Stop immediately for auto-scaling, the wrong filament mapping, a changed
orientation, Support enabled, a slicer repair, a floating island, print
cancellation, force, crack, whitening, shaving, progressive dust, looseness,
rocking, a proud cap, incomplete shoulder seating, blocked reverse motion, a
support retainer that bypasses its positive stop, or cable socket/root damage.

After all records pass, preserve the parts, project files, Preview screenshots,
slice reports, photos, and spool/process record. The next decision is a reviewed
qualification step under `LOAD_QUALIFICATION.md`, not automatic production.
No wall drilling, wall installation, hardware purchase, or load application is
authorized here. Exact future material and wall-hardware candidates remain in
`MATERIALS_AND_HARDWARE.md`.
