# Frozen R11 v1 artifact errata

> **Errata only.** This file does not modify, authorize, or supersede the
> frozen R11 v1 neutral bundle. The rating remains 0 kg / 0 lb.

The generated v1 bundle is byte-pinned evidence. Two copied Markdown files in
that bundle preserve a source-relative historical R10 link. The link works in
the source tree but not from the copied bundle directory:

| Frozen copied file | Broken copied link | Correct canonical target |
| --- | --- | --- |
| `GUIDELINES.md` | `../r10/README.md` | [development/r10/README.md](https://github.com/rupret007/story-corner-shelf/blob/main/development/r10/README.md) |
| `DESIGN_REQUIREMENTS.md` | `../r10/README.md` | [development/r10/README.md](https://github.com/rupret007/story-corner-shelf/blob/main/development/r10/README.md) |

Why this is recorded instead of silently rewritten: the bundle manifest,
source closure, deterministic tree, and the separate v2 baseline all bind the
existing bytes. Rewriting the copied files in place would falsify those
identities. A future artifact version may correct the copied links and must
receive a new package ID, manifest, source closure, and dependent baseline.

No model, geometry, process setting, permission, installation rule, or load
claim is changed by this erratum.
