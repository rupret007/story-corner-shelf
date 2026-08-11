#!/usr/bin/env python3
"""Fail-closed R10 qualification and release-state aggregation.

Four independent evidence families are merged: the canonical configuration,
Lincoln-log geometry, cable-bookend geometry, and neutral bundle artifacts.
An analytically complete neutral bundle is still *not* permission to print,
drill, install, or load the shelf.  Those transitions require their explicit
physical gates and fresh human approval.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import sys
from typing import Any, Mapping
import zlib

try:
    from . import cable_bookend, capacity_study, lincoln_geometry, model_io
except ImportError:  # pragma: no cover - direct script execution
    # Load the R10 writer before cable_bookend adds frozen R9 to sys.path.
    import model_io  # type: ignore[no-redef]
    import capacity_study  # type: ignore[no-redef]
    import lincoln_geometry  # type: ignore[no-redef]
    import cable_bookend  # type: ignore[no-redef]


R10_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = R10_ROOT.parents[1]
PACKAGE_ID = "r10_palatine_lincoln_arcade_one_bay_qualification_v1"
EXPECTED_LINCOLN_GEOMETRY_SHA256 = (
    "9914cce9b8057bbb1ecd988475b97eb7fa36ab504d5fd84fc4e8f4070edb8ee5"
)
EXPECTED_CABLE_BOOKEND_SHA256 = (
    "69bfdd3a3fa3ebef0df11edb21b30e881c8c6b24563516a2ee6f90f66d2d1f6b"
)
EXPECTED_R10_CONFIG_CANONICAL_SHA256 = (
    "f800b4ef27a6fbdca02594b5fab37e31861199789b196ef34017f3e8f19d9cef"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def runtime_provenance() -> dict[str, Any]:
    """Return deterministic serializer/runtime identity for the manifest."""

    distributions = (
        "manifold3d",
        "mapbox-earcut",
        "networkx",
        "numpy",
        "scipy",
        "shapely",
        "trimesh",
    )
    packages: dict[str, str] = {}
    for distribution in distributions:
        try:
            packages[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            packages[distribution] = "not-installed"
    requirements = PROJECT_ROOT / "requirements.txt"
    locked: dict[str, str] = {}
    if requirements.is_file():
        for line in requirements.read_text(encoding="utf-8").splitlines():
            content = line.strip()
            if not content or content.startswith("#"):
                continue
            if content.count("==") != 1:
                raise ValueError("R10 requirements must use exact name==version pins")
            name, version = content.split("==")
            if not name or not version or name in locked:
                raise ValueError("R10 requirements contain an invalid or duplicate pin")
            locked[name] = version
    requirements_match = bool(
        locked and all(packages.get(name) == version for name, version in locked.items())
    )
    return {
        "byteorder": sys.byteorder,
        "manifold3d_version": packages["manifold3d"],
        "mapbox_earcut_version": packages["mapbox-earcut"],
        "networkx_version": packages["networkx"],
        "numpy_version": packages["numpy"],
        "python_cache_tag": str(sys.implementation.cache_tag),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "requirements_txt_sha256": (
            _sha256(requirements) if requirements.is_file() else "absent"
        ),
        "requirements_runtime_exact_match": requirements_match,
        "requirements_versions": locked,
        "scipy_version": packages["scipy"],
        "r9_model_io_sha256_verified_before_execution": (
            model_io.EXPECTED_R9_MODEL_IO_SHA256
        ),
        "shapely_version": packages["shapely"],
        "trimesh_version": packages["trimesh"],
        "zlib_compile_version": zlib.ZLIB_VERSION,
        "zlib_runtime_version": zlib.ZLIB_RUNTIME_VERSION,
    }


def config_gate_report(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    cfg = capacity_study.load_config() if config is None else dict(config)
    capacity_study.validate_config(cfg)
    project = cfg["project"]
    cable = cfg["printed_arcade"]["cable_system"]
    physical = cfg["physical_gates"]
    physical_values_are_boolean = all(type(value) is bool for value in physical.values())
    physical_passed = bool(physical and physical_values_are_boolean and all(physical.values()))
    config_sha256 = capacity_study.canonical_config_sha256(cfg)
    contract_checks = {
        "capacity_study_validation_passed": True,
        "frozen_config_canonical_hash_matches": (
            config_sha256 == EXPECTED_R10_CONFIG_CANONICAL_SHA256
            and capacity_study.EXPECTED_CONFIG_CANONICAL_SHA256
            == EXPECTED_R10_CONFIG_CANONICAL_SHA256
        ),
        "qualification_only": project["qualification_only"] is True,
        "zero_rated": (
            float(project["rated_load_kg"]) == 0.0
            and float(project["rated_load_lb"]) == 0.0
        ),
        "first_wall_has_one_active_cable_bookend": (
            cable["first_wall_active_bookends"] == 1
            and cable["active_first_wall_support_indices"] == [0]
        ),
        "two_inward_sockets_with_frozen_interface": (
            cable["sockets_per_bookend"] == 2
            and cable["socket_clearance_per_face_mm"] == 0.4
            and cable["service_lift_mm"] == 8.0
            and cable["inward_facing"] is True
        ),
        "two_blanks_and_one_comb_required": (
            cable["first_wall_flush_blank_quantity"] == 2
            and cable["first_wall_comb_hook_quantity"] == 1
        ),
        "no_intermediate_or_corner_cable_hardware": (
            cable["allowed_on_intermediate_supports"] is False
            and cable["allowed_at_inside_corner"] is False
        ),
        "physical_gate_values_are_boolean": physical_values_are_boolean,
    }
    return {
        "passed": all(contract_checks.values()),
        "canonical_config_sha256": config_sha256,
        "checks": contract_checks,
        "physical_gate_count": len(physical),
        "physical_gates_passed_count": sum(value is True for value in physical.values()),
        "all_physical_gates_passed": physical_passed,
        "open_physical_gates": sorted(
            name for name, value in physical.items() if value is not True
        ),
        "project_wall_installation_authorized": (
            project["wall_installation_authorized"] is True
        ),
        "project_production_ready": project["production_ready"] is True,
        "project_physical_qualification_complete": (
            project["physical_qualification_complete"] is True
        ),
    }


def geometry_gate_report() -> dict[str, Any]:
    evidence = lincoln_geometry.build_one_bay_evidence()
    envelopes = lincoln_geometry.print_envelopes()
    checks = {
        "frozen_geometry_source_hash_matches": (
            _sha256(Path(lincoln_geometry.__file__).resolve())
            == EXPECTED_LINCOLN_GEOMETRY_SHA256
        ),
        "exact_twelve_article_one_bay": evidence.one_bay_part_count == 12,
        "installed_target_collision_free": evidence.target_pose_collision_free is True,
        "right_half_capture_path_collision_free": (
            evidence.right_half_capture_path_collision_free is True
        ),
        "positive_log_body_shoulders_authored": (
            evidence.positive_log_body_shoulders_authored is True
        ),
        "log_retainer_preassembly_path_authored": (
            evidence.log_retainer_preassembly_path_authored is True
        ),
        "flush_log_key_access_closures_authored": (
            evidence.flush_log_key_access_closures_authored is True
        ),
        "support_retainer_positive_capture_authored": (
            evidence.support_retainer_positive_capture_authored is True
        ),
        "support_retainer_service_path_collision_free": (
            evidence.support_retainer_service_path_collision_free is True
        ),
        "support_retainer_has_positive_stop_and_hand_grip": (
            evidence.support_retainer_walkout_stop_intersection_mm3 > 1.0e-5
            and evidence.support_retainer_hand_grip_protrusion_mm == 4.0
        ),
        "midpoint_net_section_geometry_proxy_authored": (
            evidence.midpoint_net_section_geometry_authored is True
            and evidence.midpoint_notched_log_section_qualified is False
            and 0.0 < evidence.log_section.net_to_gross_area_ratio < 1.0
            and 0.0
            < evidence.log_section.net_to_gross_second_moment_ratio
            < 1.0
            and 0.0
            < evidence.log_section.net_to_gross_section_modulus_ratio
            < 1.0
        ),
        "three_full_solid_surface_washer_lands_authored": (
            len(evidence.washer_lands) == 3
            and all(item.full_solid for item in evidence.washer_lands)
            and all(item.bore_diameter_mm == 7.0 for item in evidence.washer_lands)
            and all(item.outer_diameter_mm == 27.025 for item in evidence.washer_lands)
        ),
        "all_saved_geometry_fits_a1_mini_with_authored_margin": all(
            item.fits for item in envelopes.values()
        ),
        "no_material_capacity_claim_in_section_proxy": (
            evidence.log_section.material_capacity_claimed is False
        ),
        "zero_rated_and_no_install": (
            lincoln_geometry.RATED_LOAD_KG == 0.0
            and lincoln_geometry.RATED_LOAD_LB == 0.0
            and lincoln_geometry.WALL_INSTALLATION_AUTHORIZED is False
        ),
        "no_open_analytic_geometry_blockers": not evidence.release_blockers,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "one_bay_part_names": [part.name for part in evidence.parts],
        "analytic_release_blockers": list(evidence.release_blockers),
        "no_load_boundary": evidence.no_load_boundary,
    }


def cable_gate_report() -> dict[str, Any]:
    evidence = cable_bookend.build_cable_bookend_evidence()
    saved = cable_bookend.build_saved_cable_bookend_parts()
    checks = {
        "frozen_cable_source_hash_matches": (
            _sha256(Path(cable_bookend.__file__).resolve())
            == EXPECTED_CABLE_BOOKEND_SHA256
        ),
        "exact_four_article_first_wall_cable_set": len(saved) == 4,
        "support_core_preserved_additive_only": (
            evidence.core.source_core_preserved is True
            and evidence.core.additive_only is True
        ),
        "wall_bores_clear": evidence.clearance.wall_bores_clear is True,
        "support_retainer_service_lanes_clear": (
            evidence.clearance.both_support_retainer_service_lanes_clear is True
        ),
        "four_module_socket_paths_collision_free": (
            len(evidence.module_service) == 4
            and all(item.collision_free for item in evidence.module_service)
            and all(item.removal_is_exact_reverse for item in evidence.module_service)
        ),
        "saved_bookend_is_support_free_one_body_a1_fit": (
            evidence.saved_print.support_required is False
            and evidence.saved_print.body_count == 1
            and evidence.saved_print.watertight is True
            and evidence.saved_print.winding_consistent is True
            and evidence.saved_print.envelope.fits is True
        ),
        "s0_only_two_socket_inward_semantics": (
            evidence.active_first_wall_support_indices == (0,)
            and evidence.sockets_per_bookend == 2
            and evidence.inward_facing is True
            and evidence.intermediate_support_hardware_allowed is False
            and evidence.corner_hardware_allowed is False
        ),
        "field_clearance_remains_unqualified": (
            evidence.field_clearance_qualified is False
        ),
        "zero_rated_and_no_install": (
            evidence.rated_load_kg == 0.0
            and evidence.rated_load_lb == 0.0
            and evidence.wall_installation_authorized is False
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "saved_part_names": list(saved),
        "physical_and_field_release_blockers": list(evidence.release_blockers),
    }


def _artifact_records(root: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted(
        item for item in root.rglob("*") if item.is_file() and item.name != "manifest.json"
    ):
        result.append(
            {
                "path": str(path.relative_to(root)),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return result


def pending_artifact_gate() -> dict[str, Any]:
    return {
        "passed": False,
        "package_id": PACKAGE_ID,
        "individual_mesh_count": 0,
        "catalog_object_count": 0,
        "neutral_3mf_audit_passed": False,
        "stl_geometry_matches_3mf": False,
        "source_snapshot_matches_live_tree": False,
        "runtime_provenance_present": False,
        "blockers": ["no deterministic R10 qualification bundle was supplied"],
    }


def complete_artifact_gate(
    *,
    individual_mesh_count: int,
    catalog_object_count: int,
    neutral_3mf_audit_passed: bool,
    stl_geometry_matches_3mf: bool,
    source_snapshot_matches_live_tree: bool,
    runtime_provenance_present: bool,
) -> dict[str, Any]:
    checks = (
        individual_mesh_count == 16,
        catalog_object_count == 16,
        neutral_3mf_audit_passed is True,
        stl_geometry_matches_3mf is True,
        source_snapshot_matches_live_tree is True,
        runtime_provenance_present is True,
    )
    return {
        "passed": all(checks),
        "package_id": PACKAGE_ID,
        "individual_mesh_count": individual_mesh_count,
        "catalog_object_count": catalog_object_count,
        "neutral_3mf_audit_passed": neutral_3mf_audit_passed,
        "stl_geometry_matches_3mf": stl_geometry_matches_3mf,
        "source_snapshot_matches_live_tree": source_snapshot_matches_live_tree,
        "runtime_provenance_present": runtime_provenance_present,
        "blockers": [] if all(checks) else ["neutral artifact contract is incomplete"],
    }


def inspect_artifact_bundle(bundle: Path) -> dict[str, Any]:
    """Independently audit a published neutral bundle without importing its builder."""

    root = Path(bundle)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("R10 bundle must be a real directory")
    if any(path.is_symlink() for path in root.rglob("*")):
        raise ValueError("R10 bundle may not contain symlinks")
    manifest = _strict_json(root / "manifest.json")
    if manifest.get("package_id") != PACKAGE_ID:
        raise ValueError("R10 package identity changed")
    actual_paths = sorted(
        str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()
    )
    if actual_paths != manifest.get("exact_file_allowlist"):
        raise ValueError("R10 bundle file allowlist changed")
    artifact_records = _artifact_records(root)
    if artifact_records != manifest.get("hashed_artifacts_excluding_manifest"):
        raise ValueError("R10 bundle artifact hashes changed")
    if (
        manifest.get("artifact_count_excluding_manifest") != len(artifact_records)
        or manifest.get("artifact_bytes_excluding_manifest")
        != sum(record["bytes"] for record in artifact_records)
    ):
        raise ValueError("R10 artifact count or byte total changed")
    boundary = manifest.get("publication_boundary", {})
    if boundary != {
        "fresh_human_permission_required_before_every_print": True,
        "gcode_or_toolpath_present": False,
        "installation_or_drilling_authorized": False,
        "load_rating_created": False,
        "model_only_neutral_3mf": True,
        "production_set": False,
        "qualification_only": True,
        "slicer_profile_present": False,
    }:
        raise ValueError("R10 publication safety boundary changed")
    order = tuple(manifest.get("object_names_in_order", ()))
    if len(order) != 16 or len(set(order)) != 16:
        raise ValueError("R10 individual inventory must contain 16 unique articles")
    expected_paths = sorted(
        [
            "PRINT_FIRST.md",
            "README.md",
            "ASSEMBLY.md",
            "DESIGN_REQUIREMENTS.md",
            "GUIDELINES.md",
            "LOAD_QUALIFICATION.md",
            "MATERIALS_AND_HARDWARE.md",
            "R10_ONE_BAY_ASSEMBLY_AND_FIRST_WALL_REFERENCE.svg",
            "manifest.json",
            "release_status.json",
            "requirements.txt",
            "validation.json",
            "model_only_3mf/"
            "MODEL_ONLY_R10_ONE_BAY_QUALIFICATION_CATALOG_NOT_A_PRINT_PLATE.3mf",
            *[f"stl/{name}.stl" for name in order],
            *[
                f"individual_model_only_3mf/MODEL_ONLY_{name}.3mf"
                for name in order
            ],
        ]
    )
    if actual_paths != expected_paths:
        raise ValueError("R10 bundle contains a forbidden or missing artifact type")
    digests = manifest.get("geometry_digests_by_mesh_id", {})
    if set(digests) != set(order):
        raise ValueError("R10 geometry digest inventory changed")
    for name in order:
        model_path = root / "individual_model_only_3mf" / f"MODEL_ONLY_{name}.3mf"
        inspection = model_io.inspect_model_only_3mf(model_path)
        if tuple(inspection.objects) != (name,):
            raise ValueError(f"R10 individual object identity changed: {name}")
        model_digest = model_io.canonical_triangle_digest(inspection.objects[name])
        stl_digest = model_io.canonical_triangle_digest(
            model_io.read_binary_stl(root / "stl" / f"{name}.stl")
        )
        if model_digest != digests[name] or stl_digest != digests[name]:
            raise ValueError(f"R10 STL/3MF geometry mismatch: {name}")
    catalog = model_io.inspect_model_only_3mf(
        root
        / "model_only_3mf"
        / "MODEL_ONLY_R10_ONE_BAY_QUALIFICATION_CATALOG_NOT_A_PRINT_PLATE.3mf"
    )
    if tuple(catalog.objects) != order:
        raise ValueError("R10 catalog object order changed")
    for name in order:
        if model_io.canonical_triangle_digest(catalog.objects[name]) != digests[name]:
            raise ValueError(f"R10 catalog geometry mismatch: {name}")
    source_matches = True
    source_records = manifest.get("source_records", ())
    source_names = [record.get("path") for record in source_records]
    if not source_records or len(source_names) != len(set(source_names)):
        source_matches = False
    for record in source_records:
        source = (PROJECT_ROOT / record["path"]).resolve()
        if PROJECT_ROOT.resolve() not in source.parents:
            source_matches = False
            break
        if (
            not source.is_file()
            or source.stat().st_size != record["bytes"]
            or _sha256(source) != record["sha256"]
        ):
            source_matches = False
            break
    live_runtime = runtime_provenance()
    runtime_matches = bool(
        manifest.get("runtime_provenance") == live_runtime
        and live_runtime["requirements_runtime_exact_match"] is True
    )
    return complete_artifact_gate(
        individual_mesh_count=len(order),
        catalog_object_count=len(catalog.objects),
        neutral_3mf_audit_passed=True,
        stl_geometry_matches_3mf=True,
        source_snapshot_matches_live_tree=source_matches,
        runtime_provenance_present=runtime_matches,
    )


def build_release_status(
    *,
    artifact_gate: Mapping[str, Any] | None = None,
    bundle: Path | None = None,
) -> dict[str, Any]:
    if artifact_gate is not None and bundle is not None:
        raise ValueError("Supply artifact_gate or bundle, not both")
    artifact = (
        inspect_artifact_bundle(bundle)
        if bundle is not None
        else dict(artifact_gate) if artifact_gate is not None else pending_artifact_gate()
    )
    config = config_gate_report()
    geometry = geometry_gate_report()
    cable = cable_gate_report()
    neutral_complete = bool(
        config["passed"] and geometry["passed"] and cable["passed"] and artifact.get("passed")
    )
    physical_complete = bool(config["all_physical_gates_passed"])
    installation_authorized = bool(
        neutral_complete
        and physical_complete
        and config["project_wall_installation_authorized"]
        and config["project_production_ready"]
        and config["project_physical_qualification_complete"]
    )
    blockers = [
        *config["open_physical_gates"],
        *geometry["analytic_release_blockers"],
        *cable["physical_and_field_release_blockers"],
        *artifact.get("blockers", ()),
    ]
    return {
        "schema_version": "r10_release_status_v1",
        "package_id": PACKAGE_ID,
        "qualification_bundle_analytically_complete": neutral_complete,
        "all_physical_gates_complete": physical_complete,
        "production_ready": False,
        "wall_installation_authorized": installation_authorized,
        "drilling_schedule_released": False,
        "print_authorized": False,
        "fresh_human_permission_required_before_every_print": True,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
        "config_gate": config,
        "geometry_gate": geometry,
        "cable_gate": cable,
        "artifact_gate": artifact,
        "open_release_blockers": sorted(set(blockers)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_release_status(bundle=args.bundle), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
