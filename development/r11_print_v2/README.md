# R11 Gate A-left controlled print overlay

This sibling overlay preserves the immutable R11 v1 neutral bundle while
providing a fail-closed path to **one** tabletop qualification print of the
exact bay-0 left terminal half-deck. It does not contain geometry, a slicer
project, a profile, G-code, toolpaths, credentials, or reusable permission.

The checked-in generated package is deliberately non-authorizing. A print can
become eligible only after an exact Bambu slice is reviewed, its complete
evidence is stored outside this repository, and the user answers the exact
fresh-permission question. The resulting external permit is single-use. The
only authoritative consumption API atomically consumes under the ledger lock
and returns the same still-open, content-addressed G-code file descriptor to
an in-process sender. Failed, cancelled, rejected, and ambiguous attempts
still consume it.

## Commands

Validate or deterministically rebuild the static package into a fresh external
directory:

```sh
python -I -B development/r11_print_v2/generate_controlled_release.py --validate
python -I -B development/r11_print_v2/generate_controlled_release.py --output /tmp/r11-v2-check
```

After completing external evidence that conforms to the supplied schema:

```sh
python -I -B development/r11_print_v2/evaluate_attempt.py prepare-evidence --sliced-plate /private/tmp/r11-gate-a-evidence-20260811/r11_gate_a_left_20260811.gcode.3mf --output-directory /private/tmp/r11-gate-a-evidence-20260811/prepared-v2
python -I -B development/r11_print_v2/evaluate_attempt.py review --attempt /outside/repo/attempt.json
python -I -B development/r11_print_v2/evaluate_attempt.py init-ledger
python -I -B development/r11_print_v2/evaluate_attempt.py issue --attempt /outside/repo/attempt.json --permission /outside/repo/permission.json
```

The attempt also requires five independent live provenance files: read-only
printer telemetry, fresh human plate and nozzle observations, a physical
spool-label capture including the lot, and the completed dryer log/display. Hashes and
timestamps for those files are part of the reviewed-job digest. Telemetry alone
cannot attest plate cleanliness/type, physical nozzle flow/material, filament
lot, or drying.

`prepare-evidence` requires a fresh, nonexistent destination. It verifies the
three pinned native Bambu application profile sources, emits all three exact
approved effective profile exports plus their three deterministic snapshots,
and derives the sole G-code payload and exact config block directly from the
supplied sliced archive. It prints every output filename, byte count, and
SHA-256. It does not create an attempt or permission and never authorizes a
print. Use those reported files as relative evidence paths; do not hand-author
or rewrite any of the six profile JSON files. The complete emitted config
block must also match its frozen approved byte count and SHA-256; checking only
a small list of visible settings is insufficient.

The CLI deliberately has no path-only `consume` command: exiting and later
reopening a mutable GUI path would recreate a TOCTOU window. A sender must call
`consume_and_open_send_payload(...)` and send from its returned open descriptor
in that same process. No such printer sender is included here, so this overlay
does not itself contact or start the printer. Never reuse an attempt,
permission, sliced archive, extracted G-code, reviewed-job identity, or permit
for a retry. The ledger derives from the OS account database (never `HOME`), is
bound to uid/host/project by a strict identity record, requires explicit
one-time initialization, and cannot be redirected by any production API or CLI.

## Permanent boundary

No drilling, wall installation, test load, stored load, production/full-wall
printing, or nonzero load rating is authorized. The rating remains exactly
**0 kg / 0 lb**. The right half stays blocked until this left article cools,
is removed without force, and passes documented inspection under a separate
future gate.
