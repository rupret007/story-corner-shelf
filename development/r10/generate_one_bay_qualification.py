#!/usr/bin/env python3
"""Build the deterministic, unsliced R10 one-bay qualification bundle.

The package contains the twelve actual saved Lincoln-log one-bay articles and
the four-part first-wall cable-bookend candidate set.  Every article is
written separately as neutral STL and model-only 3MF.  The combined 3MF is an
off-plate catalog for inspection only.  No profile, G-code, installation
permission, drilling schedule, production set, or load rating can be emitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

try:
    from . import (
        cable_bookend,
        capacity_study,
        lincoln_geometry,
        model_io,
        release_status,
    )
except ImportError:  # pragma: no cover - direct script execution
    # Load R10 modules before cable_bookend adds frozen R9 to sys.path.
    import model_io  # type: ignore[no-redef]
    import capacity_study  # type: ignore[no-redef]
    import lincoln_geometry  # type: ignore[no-redef]
    import cable_bookend  # type: ignore[no-redef]
    import release_status  # type: ignore[no-redef]


R10_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = R10_ROOT.parents[1]
DEFAULT_OUTPUT = R10_ROOT / "generated" / "one_bay_qualification_v1"
PACKAGE_ID = release_status.PACKAGE_ID
CATALOG_FILENAME = (
    "MODEL_ONLY_R10_ONE_BAY_QUALIFICATION_CATALOG_NOT_A_PRINT_PLATE.3mf"
)
ASSEMBLY_VISUAL_FILENAME = "R10_ONE_BAY_ASSEMBLY_AND_FIRST_WALL_REFERENCE.svg"
HANDOFF_DOCUMENTS = (
    "ASSEMBLY.md",
    "PRINT_FIRST.md",
    "MATERIALS_AND_HARDWARE.md",
    "LOAD_QUALIFICATION.md",
    "GUIDELINES.md",
    "DESIGN_REQUIREMENTS.md",
)
CORE_PART_ORDER = (
    "r10_one_bay_left_support",
    "r10_one_bay_right_support",
    "r10_one_bay_left_cassette_half",
    "r10_one_bay_right_cassette_half",
    "r10_one_bay_rear_splice_log",
    "r10_one_bay_center_splice_log",
    "r10_one_bay_front_splice_log",
    "r10_one_bay_rear_log_retainer",
    "r10_one_bay_center_log_retainer",
    "r10_one_bay_front_log_retainer",
    "r10_one_bay_left_support_retainer",
    "r10_one_bay_right_support_retainer",
)
CABLE_PART_ORDER = (
    cable_bookend.FIRST_WALL_BOOKEND_PART_NAME,
    cable_bookend.FIRST_WALL_BLANK_0_PART_NAME,
    cable_bookend.FIRST_WALL_BLANK_1_PART_NAME,
    cable_bookend.FIRST_WALL_COMB_PART_NAME,
)
PART_ORDER = CORE_PART_ORDER + CABLE_PART_ORDER
MODEL_DESCRIPTION = (
    "R10 Palatine Lincoln-log one-bay and S0 cable-bookend qualification "
    "articles; neutral unsliced geometry; 0 kg / 0 lb; no wall installation"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _strict_json(path: Path) -> Any:
    source = Path(path)

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key in {source}: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON value in {source}: {value}")

    return json.loads(
        source.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=reject_constant,
    )


def _source_paths() -> tuple[Path, ...]:
    config = capacity_study.load_config()
    capacity_study.validate_config(config)
    # Bind every top-level/visual R10 design source and controlling document,
    # while deliberately excluding tests, caches, and generated deliverables.
    r10_suffixes = {".json", ".md", ".png", ".py", ".svg"}
    r10_sources = {
        str(path.relative_to(PROJECT_ROOT))
        for path in R10_ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in r10_suffixes
        and "tests" not in path.relative_to(R10_ROOT).parts
        and "generated" not in path.relative_to(R10_ROOT).parts
        and "__pycache__" not in path.relative_to(R10_ROOT).parts
    }
    relative = {
        *r10_sources,
        "development/r8/model_io.py",
        *config["frozen_r9_inputs"].keys(),
    }
    if (PROJECT_ROOT / "requirements.txt").is_file():
        relative.add("requirements.txt")
    result = tuple(PROJECT_ROOT / path for path in sorted(relative))
    if any(not path.is_file() for path in result):
        missing = [str(path) for path in result if not path.is_file()]
        raise ValueError(f"R10 source closure is incomplete: {missing}")
    return result


def _source_records() -> list[dict[str, Any]]:
    return [
        {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in _source_paths()
    ]


def _artifact_records(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path.relative_to(root)),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(
            item
            for item in root.rglob("*")
            if item.is_file() and item.name != "manifest.json"
        )
    ]


def tree_evidence(root: Path) -> dict[str, Any]:
    """Canonical whole-tree identity used by two-build determinism tests."""

    digest = hashlib.sha256()
    count = 0
    total = 0
    for path in sorted(item for item in Path(root).rglob("*") if item.is_file()):
        payload = path.read_bytes()
        relative = str(path.relative_to(root))
        file_digest = hashlib.sha256(payload).hexdigest()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
        count += 1
        total += len(payload)
    return {"file_count": count, "total_bytes": total, "tree_sha256": digest.hexdigest()}


def _validate_destination(target: Path) -> None:
    resolved = Path(target).resolve()
    if resolved == DEFAULT_OUTPUT.resolve():
        return
    if resolved == PROJECT_ROOT or PROJECT_ROOT in resolved.parents:
        raise ValueError(
            "Custom output may not be inside the repository; use a fresh temporary path"
        )


def _all_saved_parts() -> dict[str, Any]:
    core = lincoln_geometry.build_saved_one_bay_parts()
    cable = cable_bookend.build_saved_cable_bookend_parts()
    if tuple(core) != CORE_PART_ORDER:
        raise ValueError("R10 one-bay saved-part order changed")
    if tuple(cable) != CABLE_PART_ORDER:
        raise ValueError("R10 cable-bookend saved-part order changed")
    if set(core).intersection(cable):
        raise ValueError("R10 core and cable qualification identities overlap")
    return {**core, **cable}


def _readme() -> str:
    return """# R10 one-bay qualification bundle — not a production set

This is the first **actual printed Lincoln-log shelf bay** and the separate
far-left S0 cable-bookend candidate set.  It is neutral, unsliced geometry for
tabletop qualification.  The current rating is **0 kg / 0 lb**.

## Hard boundary

- Do not drill or install this candidate on a wall.
- Do not place stored load on it.
- Do not print the combined catalog; it is deliberately off-plate.
- No slicer profile, G-code, toolpath, or printer command is present.
- `requirements.txt` is copied and its exact runtime match is recorded.
- A human must inspect every individual model in slicer Preview and give fresh
  permission before every physical print.
- Never auto-scale.  All model units are millimetres.

Read `PRINT_FIRST.md`, then select only its explicitly named files from
`individual_model_only_3mf/`.  Follow `ASSEMBLY.md` exactly and use the SVG
only as an off-plate visual reference.  The cable receiver and modules have
zero structural credit.
"""


def _build_stage(stage: Path) -> None:
    if release_status.runtime_provenance()["requirements_runtime_exact_match"] is not True:
        raise RuntimeError("R10 runtime does not match the exact requirements lock")
    source_before = _source_records()
    geometry_evidence = lincoln_geometry.build_one_bay_evidence()
    cable_evidence = cable_bookend.build_cable_bookend_evidence()
    if geometry_evidence.one_bay_part_count != len(CORE_PART_ORDER):
        raise ValueError("R10 one-bay evidence count changed")
    if {part.name for part in geometry_evidence.parts} != set(CORE_PART_ORDER):
        raise ValueError("R10 one-bay evidence inventory changed")
    if any(part.support_required for part in geometry_evidence.parts):
        raise ValueError("R10 one-bay article lost its support-free design intent")
    if cable_evidence.sockets_per_bookend != 2:
        raise ValueError("R10 cable-bookend socket count changed")
    if cable_evidence.saved_print.support_required:
        raise ValueError("R10 fused cable bookend lost its support-free design intent")

    saved = _all_saved_parts()
    serialized: dict[str, model_io.SerializedMesh] = {}
    geometry_records: list[dict[str, Any]] = []
    geometry_digests: dict[str, str] = {}
    for name in PART_ORDER:
        mesh = saved[name]
        if name in CABLE_PART_ORDER:
            cable_layers = cable_bookend.cable_geometry.saved_layer_island_report(
                mesh, layer_height_mm=1.0
            )
            if cable_layers.support_required:
                raise ValueError(f"R10 cable article has a sampled layer island: {name}")
        frozen = model_io.canonicalize_mesh(mesh)
        serialized[name] = frozen
        evidence = model_io.serialized_mesh_evidence(frozen)
        envelope = lincoln_geometry.print_envelope(mesh)
        if not evidence["closed_one_body_positive"]:
            raise ValueError(f"R10 serialized article is invalid: {name}")
        if not envelope.fits:
            raise ValueError(f"R10 article exceeds the A1 mini envelope: {name}")
        stl_path = stage / "stl" / f"{name}.stl"
        model_path = stage / "individual_model_only_3mf" / f"MODEL_ONLY_{name}.3mf"
        model_io.write_binary_stl(stl_path, frozen)
        model_io.write_model_only_3mf(
            model_path,
            title=name,
            description=MODEL_DESCRIPTION,
            objects=(model_io.ModelObject(name, frozen),),
        )
        inspection = model_io.inspect_model_only_3mf(model_path)
        if tuple(inspection.objects) != (name,):
            raise ValueError(f"R10 individual object identity changed: {name}")
        digest = str(evidence["canonical_float32_triangle_digest"])
        if model_io.canonical_triangle_digest(inspection.objects[name]) != digest:
            raise ValueError(f"R10 individual 3MF geometry changed: {name}")
        if model_io.canonical_triangle_digest(model_io.read_binary_stl(stl_path)) != digest:
            raise ValueError(f"R10 individual STL geometry changed: {name}")
        geometry_digests[name] = digest
        geometry_records.append(
            {
                "mesh_id": name,
                "inventory_family": (
                    "actual_lincoln_log_one_bay"
                    if name in CORE_PART_ORDER
                    else "first_wall_s0_cable_bookend_candidate_set"
                ),
                "support_required_by_authored_geometry": False,
                "raw_extents_mm": [round(float(value), 6) for value in mesh.extents],
                "required_build_volume_mm": [
                    round(float(value), 6)
                    for value in envelope.required_build_volume_mm
                ],
                "serialized_mesh": evidence,
            }
        )

    translations: dict[str, tuple[float, float, float]] = {}
    objects: list[model_io.ModelObject] = []
    cursor = 0.0
    for name in PART_ORDER:
        translation = (round(cursor, 6), 0.0, 0.0)
        translations[name] = translation
        objects.append(model_io.ModelObject(name, serialized[name], translation))
        cursor = round(cursor + float(saved[name].extents[0]) + 20.0, 6)
    catalog_path = stage / "model_only_3mf" / CATALOG_FILENAME
    model_io.write_model_only_3mf(
        catalog_path,
        title="R10 one-bay qualification off-plate catalog",
        description=MODEL_DESCRIPTION + "; OFF-PLATE CATALOG; DO NOT PRINT",
        objects=tuple(objects),
    )
    catalog = model_io.inspect_model_only_3mf(catalog_path)
    if tuple(catalog.objects) != PART_ORDER or catalog.translations_mm != translations:
        raise ValueError("R10 catalog order or transforms changed")

    model_io.write_bytes_exclusive(stage / "README.md", _readme().encode("utf-8"))
    for document in HANDOFF_DOCUMENTS:
        model_io.write_bytes_exclusive(
            stage / document,
            (R10_ROOT / document).read_bytes(),
        )
    model_io.write_bytes_exclusive(
        stage / ASSEMBLY_VISUAL_FILENAME,
        (
            R10_ROOT
            / "visuals"
            / "r10_one_bay_exploded_and_first_wall_topology.svg"
        ).read_bytes(),
    )
    model_io.write_bytes_exclusive(
        stage / "requirements.txt",
        (PROJECT_ROOT / "requirements.txt").read_bytes(),
    )
    validation = {
        "schema_version": "r10_one_bay_qualification_validation_v1",
        "package_id": PACKAGE_ID,
        "canonical_config_sha256": release_status.EXPECTED_R10_CONFIG_CANONICAL_SHA256,
        "qualification_only": True,
        "production_ready": False,
        "physical_qualification_complete": False,
        "wall_installation_authorized": False,
        "drilling_schedule_released": False,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
        "unsliced": True,
        "embedded_slicer_profile_present": False,
        "gcode_or_toolpath_present": False,
        "individual_article_count": len(PART_ORDER),
        "actual_lincoln_log_one_bay_article_count": len(CORE_PART_ORDER),
        "first_wall_s0_cable_candidate_article_count": len(CABLE_PART_ORDER),
        "object_names_in_order": PART_ORDER,
        "geometry_records": geometry_records,
        "catalog": {
            "path": f"model_only_3mf/{CATALOG_FILENAME}",
            "off_plate_inspection_only": True,
            "do_not_print": True,
            "object_translations_mm": translations,
        },
        "included_handoff_documents": HANDOFF_DOCUMENTS,
        "assembly_visual": {
            "path": ASSEMBLY_VISUAL_FILENAME,
            "off_plate_reference_only": True,
        },
        "assembly_order": geometry_evidence.tabletop_assembly_order,
        "cable_release_blockers": cable_evidence.release_blockers,
        "manual_preview_and_fresh_print_permission_required": True,
        "source_records": source_before,
        "runtime_provenance": release_status.runtime_provenance(),
        "requirements_lock_path": "requirements.txt",
    }
    model_io.write_bytes_exclusive(stage / "validation.json", _json_bytes(validation))

    if _source_records() != source_before:
        raise RuntimeError("R10 source changed during staged artifact generation")
    artifact_gate = release_status.complete_artifact_gate(
        individual_mesh_count=len(PART_ORDER),
        catalog_object_count=len(catalog.objects),
        neutral_3mf_audit_passed=True,
        stl_geometry_matches_3mf=True,
        source_snapshot_matches_live_tree=True,
        runtime_provenance_present=True,
    )
    status = release_status.build_release_status(artifact_gate=artifact_gate)
    model_io.write_bytes_exclusive(stage / "release_status.json", _json_bytes(status))

    records = _artifact_records(stage)
    manifest = {
        "schema_version": "r10_neutral_bundle_manifest_v1",
        "package_id": PACKAGE_ID,
        "canonical_config_sha256": release_status.EXPECTED_R10_CONFIG_CANONICAL_SHA256,
        "object_names_in_order": PART_ORDER,
        "core_one_bay_part_order": CORE_PART_ORDER,
        "cable_bookend_part_order": CABLE_PART_ORDER,
        "geometry_digests_by_mesh_id": geometry_digests,
        "catalog_translations_mm": translations,
        "combined_catalog_path": f"model_only_3mf/{CATALOG_FILENAME}",
        "source_records": source_before,
        "runtime_provenance": release_status.runtime_provenance(),
        "publication_boundary": {
            "qualification_only": True,
            "production_set": False,
            "model_only_neutral_3mf": True,
            "slicer_profile_present": False,
            "gcode_or_toolpath_present": False,
            "installation_or_drilling_authorized": False,
            "load_rating_created": False,
            "fresh_human_permission_required_before_every_print": True,
        },
        "hashed_artifacts_excluding_manifest": records,
        "artifact_count_excluding_manifest": len(records),
        "artifact_bytes_excluding_manifest": sum(item["bytes"] for item in records),
        "exact_file_allowlist": sorted(
            [item["path"] for item in records] + ["manifest.json"]
        ),
    }
    model_io.write_bytes_exclusive(stage / "manifest.json", _json_bytes(manifest))


def validate_bundle(root: Path) -> dict[str, Any]:
    bundle = Path(root)
    artifact_gate = release_status.inspect_artifact_bundle(bundle)
    if artifact_gate["passed"] is not True:
        raise ValueError("R10 neutral artifact gate did not pass")
    manifest = _strict_json(bundle / "manifest.json")
    validation = _strict_json(bundle / "validation.json")
    if manifest["package_id"] != PACKAGE_ID or validation["package_id"] != PACKAGE_ID:
        raise ValueError("R10 bundle package IDs disagree")
    if (
        manifest["canonical_config_sha256"]
        != release_status.EXPECTED_R10_CONFIG_CANONICAL_SHA256
        or validation["canonical_config_sha256"]
        != release_status.EXPECTED_R10_CONFIG_CANONICAL_SHA256
    ):
        raise ValueError("R10 bundle config identity changed")
    if tuple(manifest["object_names_in_order"]) != PART_ORDER:
        raise ValueError("R10 bundle inventory order changed")
    if validation["source_records"] != _source_records():
        raise ValueError("R10 validation source snapshot changed")
    if manifest["source_records"] != _source_records():
        raise ValueError("R10 manifest source snapshot changed")
    if manifest["runtime_provenance"] != release_status.runtime_provenance():
        raise ValueError("R10 runtime provenance changed")
    if validation["runtime_provenance"] != release_status.runtime_provenance():
        raise ValueError("R10 validation runtime provenance changed")
    live = _all_saved_parts()
    for name in PART_ORDER:
        digest = model_io.canonical_triangle_digest(model_io.canonicalize_mesh(live[name]))
        if digest != manifest["geometry_digests_by_mesh_id"][name]:
            raise ValueError(f"R10 live geometry changed after generation: {name}")
    expected_status = release_status.build_release_status(artifact_gate=artifact_gate)
    if _strict_json(bundle / "release_status.json") != expected_status:
        raise ValueError("R10 aggregate release status changed")
    if expected_status["print_authorized"] is not False:
        raise ValueError("R10 bundle may never self-authorize a physical print")
    if expected_status["wall_installation_authorized"] is not False:
        raise ValueError("R10 bundle may not authorize wall installation")
    if expected_status["rated_load_kg"] != 0.0:
        raise ValueError("R10 bundle may not create a load rating")
    return manifest


def build_bundle(destination: Path = DEFAULT_OUTPUT) -> Path:
    target = Path(destination).resolve()
    _validate_destination(target)
    source_before = _source_records()
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(target):
        raise FileExistsError(f"Refusing existing R10 bundle: {target}")
    stage = Path(tempfile.mkdtemp(prefix=".r10-one-bay-stage-", dir=target.parent))
    try:
        _build_stage(stage)
        if _source_records() != source_before:
            raise RuntimeError("R10 source changed during staged build")
        validate_bundle(stage)
        model_io.atomic_publish_directory(stage, target)
        if _source_records() != source_before:
            raise RuntimeError("R10 source changed during publication")
        validate_bundle(target)
        return target
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    published = build_bundle(args.output)
    manifest = validate_bundle(published)
    print(
        json.dumps(
            {
                "output": str(published),
                "package_id": manifest["package_id"],
                "individual_article_count": len(manifest["object_names_in_order"]),
                "manifest_sha256": _sha256(published / "manifest.json"),
                "print_started": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
