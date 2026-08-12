# Gate A-left operator contract

1. Verify the frozen v1 bundle and the checked-in v2 static package.
2. Slice only `r11_bay0_left_terminal_integrated_half_deck`, quantity one.
   Use only Bambu Studio `02.07.01.62` with executable SHA-256
   `b022be6750898454803e9e07178b7c7446c0e5b4d148c593b4b56efde09ba281`.
   Trusted preparation and permit issuance rehash the installed 253,787,536-byte
   executable; the attempt field cannot self-attest this process identity.
3. Record every field required by `schemas/attempt_evidence.schema.json` in a
   JSON file outside the repository. Do not save project/profile/G-code data
   in Git. Export the final sliced plate externally and record its SHA-256 and
   byte count. Trusted code extracts the sole G-code member from that exact ZIP
   archive, derives its sole embedded config block, and requires the separately
   supplied G-code/config evidence to be byte-identical. Claimed unrelated
   payloads never establish a job. A re-slice is a different job even when only
   the estimate changes.
   The complete emitted config block is pinned by approved byte count and
   SHA-256, so any uncontrolled, custom-G-code, or inherited-setting drift also
   blocks the attempt even when the listed controlled values still look right.
   Run the trusted `prepare-evidence` command documented in `README.md` against
   the exact exported sliced plate. It creates a fresh external directory with
   the archive-derived G-code/config and all six approved profile proof files;
   never hand-author or edit those files.
   The external evidence manifest must list a canonical relative path, byte
   count, and SHA-256 for the project, sliced plate, G-code, G-code config,
   three native full-effective Bambu profile exports, their three deterministic
   canonical snapshots, and all eight screenshot evidence classes. Every
   component of every external path is opened with `openat`/`O_NOFOLLOW`; each
   regular file is read once and its exact bytes are used for both parsing and
   hashing. The strict profile parser rejects missing, unknown, duplicate, or
   changed controlled fields and cross-checks the emitted G-code config.
4. Pin the complete process: 250°C first/245°C other nozzle, 60°C bed,
   flow ratio 0.94, maximum volumetric speed 9 mm³/s, part fan 10–30%, and
   overhang fan 90%. Record the physical A1 mini's serial as SHA-256 only and
   bind its exact reviewed firmware/module map and 0.4 mm stainless nozzle.
   Any device, firmware, module, or nozzle-material change creates a new
   process candidate.
5. Review the exact plate, transform, effective settings, warning list, first
   layer, capture and cross-lap layers, final layers, and current printer and
   filament state. A screenshot field may bind a deterministic contact sheet
   or manifest when that evidence class needs multiple native captures. All
   eight evidence-class hashes must be pairwise distinct. Any unresolved
   warning blocks the attempt.
   Flat live-state fields cannot self-attest: bind the exact read-only printer
   telemetry snapshot, fresh human plate and nozzle observations, photographed
   physical spool-label evidence (including lot), and the dryer log/display to separate
   external files with SHA-256 and timestamps. Printer telemetry does not prove
   plate cleanliness/type, nozzle flow, spool lot, or drying; those remain
   blocked until their named physical/human evidence exists.
6. Require a structured drying record with `dried: true`, method, exactly
   50.0°C, 6.0–8.0 hours, and completion time. Confirm the spool/dryer accepts
   that lower-limit cycle. No exploratory/undried bypass may claim this gate.
7. Show the user the part identity/hash, settings, time, mass, layers, and
   warning dispositions. Ask exactly: **Start this exact one-piece Gate A-left
   qualification print now?**
8. Record only the exact lowercase response `yes` in an external
   fresh-permission JSON. Explicitly initialize the identity-bound ledger once,
   then issue the external permit. Only an in-process sender may atomically
   consume and use the same verified open content-addressed G-code descriptor.
   A later GUI path reopen is not authorized by this overlay.
9. A failed, cancelled, rejected, or ambiguous Send consumes the permit. For
   every retry: create a new attempt ID, re-slice to genuinely new G-code,
   re-review Preview, re-check live state, and ask again. A wrapper change around
   identical G-code remains permanently spent and is rejected.
10. Cool fully; remove without force; photograph, measure, and inspect. Hold the
   right half for a separate release.

This pathway never permits drilling, wall installation, load testing, stored
load, production, or the full wall. Rated load is 0 kg / 0 lb.
