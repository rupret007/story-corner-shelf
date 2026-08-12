#!/usr/bin/env python3
"""Build the deterministic, unsliced R11 first-outer-bay qualification bundle.

The exact inventory is eight qualification articles: the S0 fused
cable support, one ordinary adjacent support, two *terminal-length* integrated
half-decks for bay 0, one bay-local positive keystone, two flush blanks, and
one comb/hook.  The comb substitutes for a blank during cable service, so the
three cable modules are not simultaneously installed.  This is not a full-wall
set.  Each article is written
individually as neutral STL and model-only 3MF; the combined 3MF is an
off-plate inspection catalog and must not be printed.

Publication fails closed until both R11 geometry providers exist.  The script
will never rename or substitute R10 geometry, emit a slicer profile/toolpath/
G-code, authorize a print or wall operation, or create a nonzero rating.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

try:
    from . import layout, model_io, release_status
except ImportError:  # pragma: no cover - direct script execution
    import layout  # type: ignore[no-redef]
    import model_io  # type: ignore[no-redef]
    import release_status  # type: ignore[no-redef]


R11_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = R11_ROOT.parents[1]
DEFAULT_OUTPUT = R11_ROOT / "generated" / "first_outer_actual_bay_qualification_v1"
PACKAGE_ID = release_status.PACKAGE_ID
CATALOG_FILENAME = release_status.CATALOG_FILENAME
HANDOFF_DOCUMENTS = release_status.HANDOFF_DOCUMENTS
ASSEMBLY_VISUAL_RELATIVE_PATH = release_status.ASSEMBLY_VISUAL_RELATIVE_PATH
PART_ORDER = release_status.PART_ORDER
STRUCTURAL_PROVIDER_PART_ORDER = release_status.STRUCTURAL_PROVIDER_PART_ORDER
SUPPORT_CABLE_PROVIDER_PART_ORDER = release_status.SUPPORT_CABLE_PROVIDER_PART_ORDER
MODEL_DESCRIPTION = (
    "R11 first outer actual bay qualification articles; neutral unsliced "
    "geometry; not a full-wall set; 0 kg / 0 lb; no print, drilling, wall "
    "installation, or stored load authorized"
)


class QualificationGeometryIncomplete(RuntimeError):
    """Raised before staging when any exact R11 article/evidence is missing."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _artifact_records(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
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
        relative = path.relative_to(root).as_posix()
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


def _geometry_module() -> Any:
    geometry = release_status._geometry_module()  # same audited provider identity
    if geometry is None:
        raise QualificationGeometryIncomplete("R11 integrated geometry module is missing")
    return geometry


def _all_saved_parts() -> dict[str, Any]:
    geometry = _geometry_module()
    support_cable_geometry = release_status._support_cable_module()
    structural_builder = getattr(
        geometry, "build_saved_outer_terminal_bay_parts", None
    )
    support_cable_builder = (
        getattr(
            support_cable_geometry,
            "build_saved_outer_bay_support_cable_parts",
            None,
        )
        if support_cable_geometry is not None
        else None
    )
    if not callable(structural_builder) or not callable(support_cable_builder):
        missing = []
        if not callable(structural_builder):
            missing.append("build_saved_outer_terminal_bay_parts")
        if not callable(support_cable_builder):
            missing.append(
                "support_cable_geometry.build_saved_outer_bay_support_cable_parts"
            )
        raise QualificationGeometryIncomplete(
            "R11 exact saved-mesh provider(s) missing: " + ", ".join(missing)
        )
    structural = structural_builder()
    support_cable = support_cable_builder()
    if tuple(structural) != STRUCTURAL_PROVIDER_PART_ORDER:
        raise QualificationGeometryIncomplete(
            "R11 terminal-bay saved-part identity/order is incomplete"
        )
    if tuple(support_cable) != SUPPORT_CABLE_PROVIDER_PART_ORDER:
        raise QualificationGeometryIncomplete(
            "R11 support/cable saved-part identity/order is incomplete"
        )
    if set(structural).intersection(support_cable):
        raise QualificationGeometryIncomplete("R11 geometry providers overlap")
    merged = {**structural, **support_cable}
    if set(merged) != set(PART_ORDER) or len(merged) != 8:
        raise QualificationGeometryIncomplete(
            "R11 exact eight-article outer-bay inventory is incomplete"
        )
    return {name: merged[name] for name in PART_ORDER}


def preflight_geometry() -> dict[str, Any]:
    gate = release_status.geometry_gate_report()
    if gate["passed"] is not True:
        raise QualificationGeometryIncomplete(
            "R11 qualification geometry is incomplete: "
            + "; ".join(gate["analytic_blockers"])
        )
    _all_saved_parts()
    return gate


def _readme() -> str:
    return """# R11 first-outer-bay neutral qualification bundle

This package contains exactly eight R11 qualification articles: the S0 fused
cable support, one ordinary support, two terminal-length bay-0 half-decks, one
bay-local keystone, two flush blanks, and one comb/hook.  It is **not a
full-wall set**, is rated **0 kg / 0 lb**, and grants no permission to print,
drill, install, or load anything.

## Hard boundary

- No slicer profile, G-code, toolpath, printer credential, or print command is
  present.
- The combined 3MF is deliberately off-plate and must not be printed.
- Never auto-scale, auto-orient, mirror, repair, or substitute an R10 part.
- Read `PRINT_FIRST.md`; before every possible future article, inspect the
  exact individual model at 100% XYZ scale in slicer Preview and obtain fresh,
  explicit human permission.  This bundle does not provide that permission.
- Keep all wall bores empty.  Do not drill or attach this candidate to a wall.
- Cable articles and the keystone receive zero sustained-load credit.

Use only the exact individual files in `individual_model_only_3mf/` for
neutral inspection.  The checked qualification-only assembly schematic is at
`visuals/r11_first_outer_bay_exploded_and_wall_topology.svg`.
`layout_report.json`, `normalized_inputs.json`,
`validation.json`, `release_status.json`, and `manifest.json` preserve the
controlling calculation, evidence, safety boundary, and hashes.
"""


def _build_stage(stage: Path) -> None:
    geometry_gate = preflight_geometry()
    runtime = release_status.runtime_provenance()
    if runtime["requirements_runtime_exact_match"] is not True:
        raise RuntimeError("R11 runtime does not match the exact requirements lock")
    config = release_status.strict_json(R11_ROOT / "config.json")
    layout.validate_config(config)
    layout_report = layout.build_plan(config)
    if (
        layout_report["release"].get(
            "checked_neutral_qualification_artifact_generation_allowed"
        )
        is not True
    ):
        raise RuntimeError("R11 layout policy does not allow checked neutral generation")
    source_before = release_status.source_records()
    source_identity = release_status.source_tree_evidence(source_before)
    saved = _all_saved_parts()

    report_by_name = {
        item["mesh_id"]: item for item in geometry_gate["saved_mesh_reports"]
    }
    if tuple(report_by_name) != PART_ORDER:
        raise QualificationGeometryIncomplete("R11 mesh-evidence order changed")

    serialized: dict[str, model_io.SerializedMesh] = {}
    geometry_records: list[dict[str, Any]] = []
    geometry_digests: dict[str, str] = {}
    for name in PART_ORDER:
        mesh = saved[name]
        frozen = model_io.canonicalize_mesh(mesh)
        serialized[name] = frozen
        evidence = model_io.serialized_mesh_evidence(frozen)
        report = report_by_name[name]
        if evidence["closed_one_body_positive"] is not True or report["valid"] is not True:
            raise ValueError(f"R11 serialized article is invalid: {name}")
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
        if not inspection.passed or tuple(inspection.objects) != (name,):
            raise ValueError(f"R11 individual neutral 3MF audit failed: {name}")
        digest = str(evidence["canonical_float32_triangle_digest"])
        if model_io.canonical_triangle_digest(inspection.objects[name]) != digest:
            raise ValueError(f"R11 individual 3MF geometry changed: {name}")
        if model_io.canonical_triangle_digest(model_io.read_binary_stl(stl_path)) != digest:
            raise ValueError(f"R11 individual STL geometry changed: {name}")
        geometry_digests[name] = digest
        geometry_records.append(
            {
                "mesh_id": name,
                "qualification_role": (
                    "first_outer_bay_structural_or_retention_article"
                    if name in {
                        release_status.S0_SUPPORT_PART,
                        release_status.S1_SUPPORT_PART,
                        release_status.LEFT_TERMINAL_HALF_PART,
                        release_status.RIGHT_TERMINAL_HALF_PART,
                        release_status.KEYSTONE_PART,
                    }
                    else "first_wall_s0_zero_structural_credit_cable_article"
                ),
                "support_required_by_authored_geometry": False,
                "raw_extents_mm": report["raw_extents_mm"],
                "required_build_volume_mm": report["required_build_volume_mm"],
                "serialized_mesh": evidence,
            }
        )

    translations: dict[str, tuple[float, float, float]] = {}
    objects: list[model_io.ModelObject] = []
    cursor = 0.0
    for name in PART_ORDER:
        # Place the exact float32 geometry that is written, rather than the
        # pre-serialization CAD bounds.  Round the next left edge upward so a
        # float32 extent can never erode the promised 20 mm inspection gap by
        # a few nanometres.
        vertices_x = serialized[name].vertices[:, 0]
        source_left = float(vertices_x.min())
        source_right = float(vertices_x.max())
        translate_x = math.ceil((cursor - source_left) * 1_000_000.0) / 1_000_000.0
        translation = (translate_x, 0.0, 0.0)
        translations[name] = translation
        objects.append(model_io.ModelObject(name, serialized[name], translation))
        cursor = source_right + translate_x + 20.0
    catalog_path = stage / "model_only_3mf" / CATALOG_FILENAME
    model_io.write_model_only_3mf(
        catalog_path,
        title="R11 first outer actual bay off-plate qualification catalog",
        description=MODEL_DESCRIPTION + "; OFF-PLATE CATALOG; DO NOT PRINT",
        objects=tuple(objects),
    )
    catalog = model_io.inspect_model_only_3mf(catalog_path)
    if tuple(catalog.objects) != PART_ORDER or catalog.translations_mm != translations:
        raise ValueError("R11 catalog order or transforms changed")

    model_io.write_bytes_exclusive(stage / "README.md", _readme().encode("utf-8"))
    for document in HANDOFF_DOCUMENTS:
        model_io.write_bytes_exclusive(stage / document, (R11_ROOT / document).read_bytes())
    source_visual = R11_ROOT / ASSEMBLY_VISUAL_RELATIVE_PATH
    assembly_visual = release_status.inspect_assembly_visual(source_visual)
    model_io.write_bytes_exclusive(
        stage / ASSEMBLY_VISUAL_RELATIVE_PATH, source_visual.read_bytes()
    )
    if release_status.inspect_assembly_visual(
        stage / ASSEMBLY_VISUAL_RELATIVE_PATH
    ) != assembly_visual:
        raise ValueError("R11 staged assembly visual changed")
    model_io.write_bytes_exclusive(
        stage / "normalized_inputs.json", _json_bytes(config)
    )
    model_io.write_bytes_exclusive(
        stage / "layout_report.json", _json_bytes(layout_report)
    )
    model_io.write_bytes_exclusive(
        stage / "requirements.txt", (PROJECT_ROOT / "requirements.txt").read_bytes()
    )

    validation = {
        "schema_version": "r11_first_outer_bay_validation_v1",
        "package_id": PACKAGE_ID,
        "canonical_config_sha256": release_status.canonical_json_sha256(config),
        "qualification_only": True,
        "full_wall_set": False,
        "production_ready": False,
        "physical_qualification_complete": False,
        "wall_installation_authorized": False,
        "drilling_coordinates_released": False,
        "drilling_schedule_released": False,
        "print_authorized": False,
        "test_load_authorized": False,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
        "unsliced": True,
        "embedded_slicer_profile_present": False,
        "gcode_or_toolpath_present": False,
        "individual_article_count": 8,
        "object_names_in_order": PART_ORDER,
        "terminal_bay_part_order": STRUCTURAL_PROVIDER_PART_ORDER,
        "support_cable_part_order": SUPPORT_CABLE_PROVIDER_PART_ORDER,
        "both_bay0_half_decks_are_terminal_length": True,
        "terminal_half_deck_length_mm": 162.175,
        "geometry_records": geometry_records,
        "catalog": {
            "path": f"model_only_3mf/{CATALOG_FILENAME}",
            "off_plate_inspection_only": True,
            "do_not_print": True,
            "object_translations_mm": translations,
        },
        "included_handoff_documents": HANDOFF_DOCUMENTS,
        "assembly_visual": assembly_visual,
        "manual_preview_and_fresh_print_permission_required": True,
        "source_records": source_before,
        "source_tree_evidence": source_identity,
        "runtime_provenance": runtime,
        "requirements_lock_path": "requirements.txt",
        "geometry_gate": geometry_gate,
    }
    model_io.write_bytes_exclusive(stage / "validation.json", _json_bytes(validation))

    if release_status.source_records() != source_before:
        raise RuntimeError("R11 source changed during staged artifact generation")
    artifact_gate = release_status.complete_artifact_gate(
        individual_mesh_count=8,
        catalog_object_count=len(catalog.objects),
        neutral_3mf_audit_passed=True,
        stl_geometry_matches_3mf=True,
        source_snapshot_matches_live_tree=True,
        runtime_provenance_present=True,
    )
    status = release_status.build_release_status(artifact_gate=artifact_gate)
    for field in (
        "production_ready",
        "wall_installation_authorized",
        "drilling_coordinates_released",
        "drilling_schedule_released",
        "print_authorized",
        "test_load_authorized",
        "full_wall_set_complete",
    ):
        if status[field] is not False:
            raise RuntimeError(f"R11 release status may not self-authorize: {field}")
    if (status["rated_load_kg"], status["rated_load_lb"]) != (0.0, 0.0):
        raise RuntimeError("R11 release status may not create a load rating")
    model_io.write_bytes_exclusive(stage / "release_status.json", _json_bytes(status))

    records = _artifact_records(stage)
    manifest = {
        "schema_version": "r11_neutral_bundle_manifest_v1",
        "package_id": PACKAGE_ID,
        "canonical_config_sha256": release_status.canonical_json_sha256(config),
        "object_names_in_order": PART_ORDER,
        "terminal_bay_part_order": STRUCTURAL_PROVIDER_PART_ORDER,
        "support_cable_part_order": SUPPORT_CABLE_PROVIDER_PART_ORDER,
        "geometry_digests_by_mesh_id": geometry_digests,
        "catalog_translations_mm": translations,
        "combined_catalog_path": f"model_only_3mf/{CATALOG_FILENAME}",
        "assembly_visual": assembly_visual,
        "source_records": source_before,
        "source_tree_evidence": source_identity,
        "runtime_provenance": runtime,
        "publication_boundary": release_status.PUBLICATION_BOUNDARY,
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
        raise ValueError("R11 neutral artifact gate did not pass")
    manifest = release_status.strict_json(bundle / "manifest.json")
    validation = release_status.strict_json(bundle / "validation.json")
    if manifest["package_id"] != PACKAGE_ID or validation["package_id"] != PACKAGE_ID:
        raise ValueError("R11 bundle package IDs disagree")
    if tuple(manifest["object_names_in_order"]) != PART_ORDER:
        raise ValueError("R11 bundle inventory order changed")
    if validation["source_records"] != release_status.source_records():
        raise ValueError("R11 validation source snapshot changed")
    if validation["source_tree_evidence"] != release_status.source_tree_evidence():
        raise ValueError("R11 validation source-tree identity changed")
    if validation["runtime_provenance"] != release_status.runtime_provenance():
        raise ValueError("R11 validation runtime provenance changed")
    live = _all_saved_parts()
    for name in PART_ORDER:
        digest = model_io.canonical_triangle_digest(model_io.canonicalize_mesh(live[name]))
        if digest != manifest["geometry_digests_by_mesh_id"][name]:
            raise ValueError(f"R11 live geometry changed after generation: {name}")
    expected_status = release_status.build_release_status(artifact_gate=artifact_gate)
    stored_status = release_status.strict_json(bundle / "release_status.json")
    # Evidence providers intentionally use immutable tuples in memory; JSON
    # represents those sequences as arrays.  Compare the canonical strict-JSON
    # encodings so this audit checks content rather than Python container type.
    if _json_bytes(stored_status) != _json_bytes(expected_status):
        raise ValueError("R11 aggregate release status changed")
    if expected_status["print_authorized"] is not False:
        raise ValueError("R11 bundle may never self-authorize a physical print")
    if expected_status["wall_installation_authorized"] is not False:
        raise ValueError("R11 bundle may never authorize wall installation")
    if expected_status["drilling_schedule_released"] is not False:
        raise ValueError("R11 bundle may never release drilling")
    if expected_status["drilling_coordinates_released"] is not False:
        raise ValueError("R11 bundle may never release drilling coordinates")
    if expected_status["test_load_authorized"] is not False:
        raise ValueError("R11 bundle may never authorize test loading")
    if expected_status["production_ready"] is not False:
        raise ValueError("R11 bundle may never claim production readiness")
    if (expected_status["rated_load_kg"], expected_status["rated_load_lb"]) != (0.0, 0.0):
        raise ValueError("R11 bundle may never create a load rating")
    return manifest


def build_bundle(destination: Path = DEFAULT_OUTPUT) -> Path:
    target = Path(destination).resolve()
    _validate_destination(target)
    # Preflight before creating a target parent or staging directory.  Missing
    # geometry must leave no misleading partial artifact tree behind.
    preflight_geometry()
    source_before = release_status.source_records()
    target.parent.mkdir(parents=True, exist_ok=True)
    if os.path.lexists(target):
        raise FileExistsError(f"Refusing existing R11 bundle: {target}")
    stage = Path(tempfile.mkdtemp(prefix=".r11-outer-bay-stage-", dir=target.parent))
    try:
        _build_stage(stage)
        if release_status.source_records() != source_before:
            raise RuntimeError("R11 source changed during staged build")
        validate_bundle(stage)
        model_io.atomic_publish_directory(stage, target)
        if release_status.source_records() != source_before:
            raise RuntimeError("R11 source changed during publication")
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
                "full_wall_set": False,
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
