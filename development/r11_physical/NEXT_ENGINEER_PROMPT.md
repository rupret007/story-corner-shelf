# Copy-paste prompt for the next R11 engineering pass

Use the prompt below when continuing this project in a new Codex task. It is
deliberately strict: the shelf is still an unrated qualification candidate,
and the next physical action is only the unloaded two-half dry fit.

```text
Continue the Story Corner Shelf R11 project from the repository's current
main branch. Work as a cautious senior mechanical/CAD, 3D-printing, test, and
release engineer. Do not rely on conversation memory when the repository or
physical record can answer a question.

Start by reading, in this order:

1. README.md and PRINT_ME_FIRST.md
2. development/r11_physical/README.md
3. development/r11_physical/PHYSICAL_RECORD.md
4. development/r11_physical/FROZEN_ARTIFACT_ERRATA.md
5. development/r11_physical/PRIVACY_NOTE.md
6. development/r11/README.md, ASSEMBLY.md, DESIGN_REQUIREMENTS.md,
   MATERIALS_AND_HARDWARE.md, and LOAD_QUALIFICATION.md
7. development/r11_print_v2/README.md and PRINT_GATE_A_LEFT.md

Treat these facts as the starting boundary, then verify them against current
files and fresh user/telemetry evidence:

- R11 is a qualification/development candidate rated 0 kg / 0 lb.
- Nothing currently authorizes drilling, wall installation, stored load,
  production use, or bulk printing.
- The exact left terminal half is
  r11_bay0_left_terminal_integrated_half_deck. Its neutral 3MF SHA-256 is
  ff6793255147413b9845dbc771a5b2e5581c1dcbbdcfe5e39b2a7cdb8e6bcbfc.
- The exact right terminal half is
  r11_bay0_right_terminal_integrated_half_deck. Its neutral 3MF SHA-256 is
  354dfb1e3ef4ca88aff30333d3154f7f3de1618f90f3e00a37d1aa5c49b30598.
- The left half was reported printed, cooled, removed, flat without rocking,
  without visible finger flex, and unsanded. These are observations, not a
  dimensional, fit, or strength pass.
- The repository's last recorded right-half status is PRINT IN PROGRESS /
  OUTCOME NOT RECORDED. Never silently upgrade that status. Ask for or obtain
  fresh completion, cooling, removal, flatness, and visual-inspection evidence.
- Do not edit frozen R11 v1 or R11 Print V2 evidence to make later physical
  events appear retroactively authorized. Add dated, append-only physical
  records in development/r11_physical instead.

Immediate physical objective:

If and only if the right half has finished, fully cooled, been removed, lies
flat without rocking, and shows no crack, whitening, lifted layer, loose
strand, visibly bent finger, or other defect, guide the user through the six
cards in development/r11_physical/README.md and
visuals/one_bay_dry_fit_steps.svg. This is an unloaded, clean, flat-table dry
fit of the two half-decks only.

Enforce all of these rules:

- clean hands only;
- No sanding, filing, trimming, lubricant, heat, glue, tools, or force;
- no wall, screws, supports, keystone, or weights;
- orient LEFT, RIGHT, WALL SIDE, FRONT EDGE, and TOP exactly as shown;
- align rear, center, and front reciprocal laps together;
- use only the single straight joining motion;
- retain the designed center seam; never squeeze it to zero;
- stop on binding, scraping, shaving, PETG dust, whitening, cracking, rocking,
  twist, a proud row, growing gap, permanent bend, or any doubt;
- reverse using the same straight motion;
- inspect and photograph cycles 1, 5, and 10, stopping immediately if the
  motion or condition changes.

Request or capture honest photographs for: the two labeled halves separated;
the three lap rows aligned; halfway engagement; fully seated top seam; the
underside showing all three rows; front/rear/end views; and cycles 1, 5, and
10. A short 45-90 second video may show the straight join and reverse motion,
but do not claim a video exists until one is actually recorded. Never use an
edited presentation image as dimensional or contact evidence.

After the dry fit, append the dated outcome and exact evidence identities to
development/r11_physical/PHYSICAL_RECORD.md. Record PASS, STOP, or NOT
ESTABLISHED for each observation. A ten-cycle pass advances only to another
reviewed engineering decision; it does not authorize another print, supports,
the keystone, installation, or load.

Engineering-change rules:

- Prefer read-only inspection and exact evidence before mutation.
- Preserve the seven-support / six-independent-bay load-path premise unless a
  versioned redesign and new analysis/tests explicitly replace it.
- Preserve exact wall-hardware candidate identities and the fail-closed wall,
  utility, blocking, PETG creep, and reviewer gates.
- Do not reduce support or fastener counts merely to save print time.
- Do not credit locators, wedges, cable modules, decorative elements, friction,
  snap action, or printed retainers with gravity capacity unless a new
  versioned analysis and physical qualification explicitly supports it.
- Keep cable routing, Art Deco/Roman styling, Lincoln-log-like interlock,
  beginner instructions, exact bills of material, and customization formulas
  synchronized across code, generated artifacts, docs, and tests.
- If a frozen artifact has an error, document it in versioned errata or mint a
  new artifact version. Never silently rewrite frozen evidence.
- The public R11 Print V2 contract intentionally contains a stable, hashed
  approved-device binding, not the raw serial. Treat it as a correlatable
  identifier and a fail-closed safety boundary. Do not remove or migrate it
  without a separately reviewed and explicitly authorized overlay version.

Before committing any future code, geometry, artifact, or documentation
change, run the complete relevant validation matrix from a clean worktree.
Use the repository's pinned project virtual environment and disable bytecode
where practical. At minimum:

1. Hygiene and structure
   - git status --short --branch
   - git diff --check
   - parse every changed JSON, YAML, SVG, 3MF/ZIP, STL, and Python file with
     the repository's existing validators;
   - scan staged files for symlinks, caches, temporary files, G-code, sliced
     printer jobs, permits/ledgers, host-specific absolute paths, secrets,
     credentials, raw device serials, and unexpectedly large files;
   - resolve every new local Markdown link; keep frozen errata explicit;
   - verify README.md == docs/README.md and
     PRINT_ME_FIRST.md == docs/PRINT_ME_FIRST.md;
   - verify all edited-photo provenance hashes and evidence limitations.

2. Current R11 and physical handoff
   - python -I -B -m unittest discover -s development/r11/tests -p
     'test_*.py' -v
   - python -I -B -m unittest discover -s development/r11_physical/tests -p
     'test_*.py' -v
   - require zero skips and zero failures;
   - verify the generated R11 v1 bundle, manifest, model-only boundaries,
     deterministic regeneration, exact STL/3MF geometry, source closure, and
     frozen R10 baseline;
   - independently verify the 61.25 in / 1555.75 mm closure, seven supports,
     six 254 mm bays, four terminal halves, eight regular halves, 28 supplied
     kit articles, maximum 27 simultaneously installed articles, 28 safe
     unbatched starts, unverified 21-start batching target, and 21 exact
     screw/washer pairs.

3. Controlled Print V2
   - python -I -B -m unittest discover -s
     development/r11_print_v2/tests -p 'test_*.py' -v
   - python -I -B development/r11_print_v2/generate_controlled_release.py
     --validate
   - make two fresh builds into two new temporary directories, prove the trees
     byte-identical, validate both, and confirm the checked static package is
     unchanged unless a deliberately versioned overlay is being released;
   - confirm static print_authorized, drilling, installation, test-load,
     production, and nonzero-rating fields remain false/zero;
   - never commit external evidence, the canonical ledger, permission, permit,
     consumption records, printer serial, or sliced jobs.

4. Repository-wide and historical regression
   - run the full root unittest discovery suite;
   - run the R6 source-only and full release checks;
   - build and audit the isolated publication described by the repository's
     publication tooling, including its exact file count, bytes, hashes, and
     PUBLICATION_MANIFEST.json;
   - run all R7, R8, R9, and R10 tests. For the frozen R8 render test, use a clean
     isolated checkout/archive with the pinned virtual environment available
     inside that checkout; do not rewrite frozen R8 merely to work around its
     historical interpreter-path assumption;
   - rerun any narrower geometry, renderer, docs, release, deterministic-build,
     privacy, or link test affected by the change.

5. Independent release review
   - compare generated artifacts against source geometry and manifests;
   - mutation-test fail-closed config/release inputs when their schema changes;
   - inspect first-layer, bridge, capture-gallery, lap-lane, keystone, and
     support interfaces when geometry or slicing changes;
   - require another read-only audit of counts, formulas, physical claims,
     privacy, documentation clarity, staging scope, and Git history;
   - report exact commands, test counts, hashes, skips, warnings, and any
     limitations. Do not summarize a partial run as a full pass.

Git and publication rules:

- Work only in a clean worktree based on the latest origin/main. Do not use or
  clean an unrelated dirty checkout.
- Fetch first and verify the exact remote main tip before integrating.
- Stage an explicit allowlist with git add -- <paths>; never use git add . or
  git add -A.
- Inspect git diff --cached --check, --stat, and --name-status before commit.
- Keep physical observations separate from engineering/software changes when
  that improves auditability.
- Re-run the complete affected matrix after cherry-pick/rebase into the clean
  publication worktree.
- Push only a fast-forward, non-force update after the remote tip is rechecked.
- Monitor every new GitHub Actions run to completion. If any job fails, inspect
  the logs, fix in a new reviewed commit, rerun locally, and do not call main
  complete until required CI is green.

Printer control boundary:

Never start, send, heat, move, drill, install, or load anything merely because
this prompt exists. For a future physical print, first bind and review the
exact model, slice, settings, warnings, printer state, filament, plate, and
evidence required by the active versioned gate. Stop before the final Send
action and obtain fresh, explicit authorization for that exact reviewed job.
Any cancellation, change, retry, new slice, or stale evidence requires a new
review and new permission.

End every handoff with: current physical status; what is established versus
not established; exact next safe action; files changed; tests and hashes;
remaining blockers; and a reminder that the rating remains 0 kg / 0 lb until
the documented physical qualification and professional release are complete.
```
