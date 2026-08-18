#!/usr/bin/env python3
"""Generate the deterministic, non-authorizing R11 Gate A-left v2 package."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

try:
    from . import control_contract as control
except ImportError:  # pragma: no cover - direct execution
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import control_contract as control  # type: ignore[no-redef]


DEFAULT_OUTPUT = control.DEFAULT_STATIC_PACKAGE


def _static_readme() -> str:
    return """# R11 Gate A-left controlled qualification print v2

This deterministic package binds the immutable R11 v1 neutral bundle and the
only initially selectable article: the exact bay-0 **left** terminal integrated
half-deck, quantity one. It contains no geometry, slicer project, profile,
G-code, toolpath, credential, runtime attempt evidence, permission, or permit.

## Static state

`print_authorized` and `effective_print_authorized` are permanently false in
this package. Exact reviewed slice evidence and fresh lowercase `yes`
permission must remain outside the repository. A separately issued external
permit is effective only while fresh and unconsumed; it is atomically consumed
under the identity-bound ledger lock only when an in-process sender retains the
same verified open content-addressed G-code descriptor. A later GUI path reopen
is not authorized. Failed, cancelled, rejected, or ambiguous attempts still
consume it. Every retry needs a new attempt ID, genuinely new sliced G-code,
Preview review, live-state check, and fresh permission.

The right half, supports, keystone, cable articles, and off-plate catalog are
all blocked. No drilling, wall installation, test load, stored load,
production/full-wall printing, or nonzero rating is authorized. Rating remains
exactly 0 kg / 0 lb.
"""


def _status(v1: dict[str, Any]) -> dict[str, Any]:
    contract = control.strict_json(control.RELEASE_CONTRACT_PATH)
    return control.expected_static_status(v1, contract)


def _validate_destination(target: Path) -> None:
    resolved = Path(target).resolve()
    if resolved == DEFAULT_OUTPUT.resolve():
        return
    project = control.PROJECT_ROOT.resolve()
    if resolved == project or project in resolved.parents:
        raise control.ContractError(
            "custom static output must be a fresh path outside the repository"
        )


def _build_stage(stage: Path) -> None:
    source_before = control.v2_source_records()
    v1 = control.verify_frozen_v1()
    contract = control.strict_json(control.RELEASE_CONTRACT_PATH)
    for source, relative in (
        (control.BASELINE_LOCK_PATH, "baseline_lock.json"),
        (control.RELEASE_CONTRACT_PATH, "release_contract.json"),
        (control.ATTEMPT_SCHEMA_PATH, "schemas/attempt_evidence.schema.json"),
        (control.PERMISSION_SCHEMA_PATH, "schemas/fresh_permission.schema.json"),
        (control.PERMIT_SCHEMA_PATH, "schemas/ephemeral_permit.schema.json"),
        (control.CONSUMPTION_SCHEMA_PATH, "schemas/send_attempt_consumption.schema.json"),
    ):
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = source.read_bytes()
        destination.write_bytes(payload)
        if (
            destination.read_bytes() != payload
            or control.sha256_file(destination) != control.sha256_file(source)
        ):
            raise control.ContractError(f"staged copy does not bind live source: {relative}")
    (stage / "README.md").write_text(_static_readme(), encoding="utf-8")
    (stage / "status.json").write_bytes(control.json_bytes(_status(v1)))
    records = control.artifact_records(stage)
    source_records = control.v2_source_records()
    if source_records != source_before:
        raise control.ContractError("v2 source changed while staging static package")
    manifest = {
        "schema_version": "r11.gate-a-left-static-manifest.v2",
        "package_id": contract["package_id"],
        "exact_file_allowlist": sorted(contract["static_package_allowlist"]),
        "immutable_v1": {
            "package_id": v1["package_id"],
            "manifest_sha256": v1["manifest_sha256"],
            "tree": v1["tree"],
            "source_tree": v1["source_tree"],
            "canonical_config_sha256": v1["canonical_config_sha256"],
            "selected_article": v1["selected_article"],
        },
        "selection": contract["selection"],
        "slice_contract": contract["slice_contract"],
        "hard_boundary": control.HARD_BOUNDARY,
        "static_print_authorized": False,
        "static_effective_print_authorized": False,
        "hashed_artifacts_excluding_manifest": records,
        "source_records": source_records,
        "source_tree_evidence": control.source_tree_evidence(source_records),
    }
    (stage / "manifest.json").write_bytes(control.json_bytes(manifest))
    if control.v2_source_records() != source_before:
        raise control.ContractError("v2 source changed before static package commit")


def build_package(output: Path = DEFAULT_OUTPUT) -> Path:
    """Build once into a fresh target; existing targets are never replaced."""

    target = Path(output)
    _validate_destination(target)
    if target.exists():
        raise FileExistsError(f"refusing to replace existing static package: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.stage-", dir=target.parent))
    try:
        _build_stage(stage)
        control.validate_static_package(stage)
        if target.exists():
            raise FileExistsError(f"refusing to replace existing static package: {target}")
        os.replace(stage, target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate", action="store_true")
    group.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.validate:
        manifest = control.validate_static_package(DEFAULT_OUTPUT)
        print(
            f"PASS {manifest['package_id']} "
            f"manifest={control.sha256_file(DEFAULT_OUTPUT / 'manifest.json')} "
            "static_print_authorized=false"
        )
        return 0
    built = build_package(args.output)
    print(f"built deterministic non-authorizing package: {built}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
