#!/usr/bin/env python3
"""Fail-closed R11 neutral-bundle and release-state aggregation.

R11's current deliverable is an eight-article, first-outer-bay *qualification*
set.  It is not a full-wall set and it can never authorize a print, drilling,
installation, production use, or load.  Even a fully deterministic neutral
bundle keeps those transitions hard-false and the rating at 0 kg / 0 lb.

The geometry contract deliberately has two modules: ``integrated_geometry``
provides the terminal bay (two terminal half-decks plus its bay-local
keystone), while ``support_cable_geometry`` provides the S0 fused cable
support, one ordinary support, two blanks, and one comb/hook.  Publication
fails closed until both providers exist and pass.
R10 geometry is never renamed or substituted for a missing R11 article.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
from importlib import metadata
import json
import math
from pathlib import Path, PurePosixPath
import platform
import sys
from typing import Any, Mapping
import warnings
from xml.etree import ElementTree as ET
import zlib

try:
    from . import layout, model_io
except ImportError:  # pragma: no cover - direct script execution
    import layout  # type: ignore[no-redef]
    import model_io  # type: ignore[no-redef]


R11_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = R11_ROOT.parents[1]
PACKAGE_ID = "r11_first_outer_actual_bay_neutral_qualification_v1"
CATALOG_FILENAME = (
    "MODEL_ONLY_R11_FIRST_OUTER_ACTUAL_BAY_CATALOG_NOT_A_PRINT_PLATE.3mf"
)
HANDOFF_DOCUMENTS = (
    "ASSEMBLY.md",
    "CUSTOMIZATION.md",
    "DESIGN_REQUIREMENTS.md",
    "GUIDELINES.md",
    "LOAD_QUALIFICATION.md",
    "MATERIALS_AND_HARDWARE.md",
    "PLAN.md",
    "PRINT_FIRST.md",
)
ASSEMBLY_VISUAL_RELATIVE_PATH = (
    "visuals/r11_first_outer_bay_exploded_and_wall_topology.svg"
)
EXPECTED_ASSEMBLY_VISUAL_SHA256 = (
    "8d00061476ac89d026a6f8cc560ff255b2c5e0ffa377b49f114e53e8052a3ea5"
)
ASSEMBLY_VISUAL_REQUIRED_LABELS = (
    "QUALIFICATION-ONLY ENGINEERING SCHEMATIC · R11 v1",
    "NO PRINT · NO DRILL · NO INSTALL · NO LOAD · RATED LOAD 0 kg / 0 lb",
    "LEFT TERMINAL HALF-DECK · 162.175 mm",
    "RIGHT TERMINAL HALF-DECK · 162.175 mm",
    "1 removable keystone 0 VERTICAL-LOAD CREDIT",
    "S0 · fused two-socket outer support",
    "S1 · ordinary support",
    "No drilling map: bore positions intentionally omitted; drilling coordinates are not released.",
    "1 · lower with 2 mm clearance",
    "2 · slide 32 mm wallward",
    "3 · settle 2 mm",
    "two flush blanks or blank + comb/hook",
    "4 terminal halves × 162.175 mm (both halves of bays 0 and 5)",
    "8 regular halves × 154.325 mm",
    "28-kit · 27 active max · 28 safe starts · 21 unverified batched target",
)

S0_SUPPORT_PART = "r11_first_wall_s0_fused_two_socket_support"
S1_SUPPORT_PART = "r11_first_wall_s1_ordinary_support"
LEFT_TERMINAL_HALF_PART = "r11_bay0_left_terminal_integrated_half_deck"
RIGHT_TERMINAL_HALF_PART = "r11_bay0_right_terminal_integrated_half_deck"
KEYSTONE_PART = "r11_bay0_positive_keystone"
BLANK_0_PART = "r11_first_wall_socket_0_flush_blank"
BLANK_1_PART = "r11_first_wall_socket_1_flush_blank"
COMB_PART = "r11_first_wall_multi_cable_comb_hook"

STRUCTURAL_PROVIDER_PART_ORDER = (
    LEFT_TERMINAL_HALF_PART,
    RIGHT_TERMINAL_HALF_PART,
    KEYSTONE_PART,
)
SUPPORT_CABLE_PROVIDER_PART_ORDER = (
    S0_SUPPORT_PART,
    S1_SUPPORT_PART,
    BLANK_0_PART,
    BLANK_1_PART,
    COMB_PART,
)
PART_ORDER = (
    S0_SUPPORT_PART,
    S1_SUPPORT_PART,
    LEFT_TERMINAL_HALF_PART,
    RIGHT_TERMINAL_HALF_PART,
    KEYSTONE_PART,
    BLANK_0_PART,
    BLANK_1_PART,
    COMB_PART,
)

PUBLICATION_BOUNDARY = {
    "drilling_coordinates_released": False,
    "drilling_schedule_released": False,
    "fresh_human_permission_required_before_every_print": True,
    "full_wall_set": False,
    "gcode_or_toolpath_present": False,
    "installation_authorized": False,
    "load_rating_created": False,
    "model_only_neutral_3mf": True,
    "print_authorized": False,
    "production_set": False,
    "qualification_only": True,
    "slicer_profile_present": False,
    "test_load_authorized": False,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_assembly_visual(path: Path) -> dict[str, Any]:
    """Parse and bind the exact safe, qualification-only R11 SVG handoff."""

    source = Path(path)
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ValueError("R11 assembly visual is not well-formed XML") from error
    svg_namespace = "http://www.w3.org/2000/svg"
    forbidden_tags = {
        f"{{{svg_namespace}}}script",
        f"{{{svg_namespace}}}foreignObject",
        f"{{{svg_namespace}}}image",
    }
    nodes = tuple(root.iter())
    external_reference_free = True
    for node in nodes:
        for key, value in node.attrib.items():
            if key == "href" or key.endswith("}href"):
                external_reference_free &= value.startswith("#")
            if "url(" in value:
                external_reference_free &= "url(#" in value
    normalized_text = " ".join(" ".join(root.itertext()).split())
    label_checks = {
        label: label in normalized_text for label in ASSEMBLY_VISUAL_REQUIRED_LABELS
    }
    checks = {
        "sha256_exact": digest == EXPECTED_ASSEMBLY_VISUAL_SHA256,
        "svg_root_exact": root.tag == f"{{{svg_namespace}}}svg",
        "canvas_exact": (
            root.attrib.get("width") == "1600"
            and root.attrib.get("height") == "1100"
            and root.attrib.get("viewBox") == "0 0 1600 1100"
        ),
        "accessible_title_and_description_present": bool(
            root.find(f"{{{svg_namespace}}}title") is not None
            and root.find(f"{{{svg_namespace}}}desc") is not None
            and root.attrib.get("role") == "img"
            and root.attrib.get("aria-labelledby") == "r11-title r11-desc"
        ),
        "no_script_foreign_object_or_embedded_image": not any(
            node.tag in forbidden_tags for node in nodes
        ),
        "no_external_references": external_reference_free,
        "all_required_labels_present": all(label_checks.values()),
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        missing = sorted(label for label, passed in label_checks.items() if not passed)
        raise ValueError(
            f"R11 assembly visual audit failed: checks={failed}, missing_labels={missing}"
        )
    return {
        "path": ASSEMBLY_VISUAL_RELATIVE_PATH,
        "bytes": len(payload),
        "sha256": digest,
        "required_labels": list(ASSEMBLY_VISUAL_REQUIRED_LABELS),
        "checks": checks,
    }


def strict_json(path: Path) -> Any:
    """Read strict JSON, rejecting duplicate keys and non-finite numbers."""

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


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def runtime_provenance() -> dict[str, Any]:
    """Return the exact neutral-writer runtime identity recorded in bundles."""

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
                raise ValueError("R11 requirements must use exact name==version pins")
            name, version = content.split("==")
            if not name or not version or name in locked:
                raise ValueError("R11 requirements contain an invalid or duplicate pin")
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
        "r10_model_io_sha256_verified_before_execution": (
            model_io.EXPECTED_R10_MODEL_IO_SHA256
        ),
        "scipy_version": packages["scipy"],
        "shapely_version": packages["shapely"],
        "trimesh_version": packages["trimesh"],
        "zlib_compile_version": zlib.ZLIB_VERSION,
        "zlib_runtime_version": zlib.ZLIB_RUNTIME_VERSION,
    }


def source_paths() -> tuple[Path, ...]:
    """Return the exact live source closure guarded during publication."""

    suffixes = {".json", ".md", ".png", ".py", ".svg"}
    r11_sources = {
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in R11_ROOT.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffixes
        and "tests" not in path.relative_to(R11_ROOT).parts
        and "generated" not in path.relative_to(R11_ROOT).parts
        and "__pycache__" not in path.relative_to(R11_ROOT).parts
    }
    relative = {
        *r11_sources,
        "development/r8/model_io.py",
        "development/r9/model_io.py",
        "development/r10/model_io.py",
    }
    if (PROJECT_ROOT / "requirements.txt").is_file():
        relative.add("requirements.txt")
    required = {
        "development/r11/ASSEMBLY.md",
        "development/r11/CUSTOMIZATION.md",
        "development/r11/DESIGN_REQUIREMENTS.md",
        "development/r11/FROZEN_BASELINES.json",
        "development/r11/GUIDELINES.md",
        "development/r11/LOAD_QUALIFICATION.md",
        "development/r11/MATERIALS_AND_HARDWARE.md",
        "development/r11/PLAN.md",
        "development/r11/PRINT_FIRST.md",
        "development/r11/README.md",
        "development/r11/config.json",
        "development/r11/generate_qualification.py",
        "development/r11/integrated_geometry.py",
        "development/r11/layout.py",
        "development/r11/model_io.py",
        "development/r11/release_status.py",
        "development/r11/support_cable_geometry.py",
        f"development/r11/{ASSEMBLY_VISUAL_RELATIVE_PATH}",
    }
    missing_names = sorted(required - relative)
    if missing_names:
        raise ValueError(f"R11 source closure is incomplete: {missing_names}")
    result = tuple(PROJECT_ROOT / name for name in sorted(relative))
    bad = [
        str(path)
        for path in result
        if not path.is_file() or path.is_symlink()
    ]
    if bad:
        raise ValueError(f"R11 source closure contains a missing/symlink source: {bad}")
    return result


def source_records() -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(PROJECT_ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in source_paths()
    ]


def source_tree_evidence(records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    current = source_records() if records is None else records
    digest = hashlib.sha256()
    total = 0
    for record in current:
        digest.update(record["path"].encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(record["sha256"].encode("ascii"))
        digest.update(b"\n")
        total += int(record["bytes"])
    return {
        "source_file_count": len(current),
        "source_bytes": total,
        "source_tree_sha256": digest.hexdigest(),
    }


def config_gate_report() -> dict[str, Any]:
    config = strict_json(R11_ROOT / "config.json")
    layout.validate_config(config)
    plan = layout.build_plan(config)
    predecessor_live = layout.verify_frozen_r10()
    predecessor = {
        **predecessor_live,
        "path": "development/r10",
    }
    project = config["project"]
    counts = plan["printed_piece_counts"]
    hardware = plan["hardware_candidate_counts"]
    joinery = plan["joinery_candidate"]
    bays = plan["layout"]["bay_stations"]
    starts = plan["print_start_estimate"]
    checks = {
        "strict_checked_in_config_validates": True,
        "frozen_r10_tree_verified": predecessor_live["verified"] is True,
        "qualification_only": project["qualification_only"] is True,
        "project_release_flags_remain_false": all(
            project[name] is False
            for name in (
                "print_authorized",
                "production_ready",
                "wall_installation_authorized",
                "drilling_coordinates_released",
                "test_load_authorized",
                "geometry_release_complete",
                "independent_engineering_review_approved",
                "physical_load_qualification_passed",
                "tested_load_rating_exists",
            )
        ),
        "zero_rated": (
            float(project["rated_load_kg"]) == 0.0
            and float(project["rated_load_lb"]) == 0.0
        ),
        "exact_six_bay_seven_support_layout": (
            plan["layout"]["bay_count"] == 6
            and plan["layout"]["support_count"] == 7
            and plan["layout"]["actual_pitch_mm"] == 254.0
            and plan["layout"]["exact_wall_closure"]["closure_residual_mm"] == 0.0
        ),
        "exact_outer_terminal_and_interior_regular_identity": (
            joinery["terminal_half_deck_length_mm"] == 162.175
            and len(bays) == 6
            and all(
                (bay["left_half_kind"], bay["right_half_kind"])
                == (
                    ("terminal", "terminal")
                    if index in (0, 5)
                    else ("regular", "regular")
                )
                for index, bay in enumerate(bays)
            )
        ),
        "exact_target_counts": (
            counts["supports"] == 7
            and counts["integrated_half_decks"] == 12
            and counts["positive_bay_wedges"] == 6
            and counts["cable_modules"] == 3
            and counts["kit_articles"] == 28
            and counts["simultaneously_installed_articles"] == 27
            and counts["terminal_integrated_half_decks"] == 4
            and counts["regular_integrated_half_decks"] == 8
        ),
        "safe_and_target_start_counts_are_distinct": (
            starts["safe_unbatched_starts"] == 28
            and starts["target_batched_starts"] == 21
            and starts["plate_nesting_verified"] is False
            and starts["verified_production_starts"] is None
        ),
        "exact_candidate_hardware_counts": (
            hardware["wall_fasteners"] == 21 and hardware["washers"] == 21
        ),
        "solver_does_not_release_installation": (
            plan["release"]["installation_ready"] is False
            and plan["release"]["print_authorized"] is False
            and plan["release"]["wall_installation_authorized"] is False
            and plan["release"]["drilling_coordinates_released"] is False
            and plan["release"]["test_load_authorized"] is False
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "canonical_config_sha256": canonical_json_sha256(config),
        "frozen_r10_tree": predecessor,
        "layout_report": plan,
        "open_physical_and_field_gates": list(plan["release"]["blockers"]),
    }


def _geometry_module() -> Any | None:
    module_name = (
        f"{__package__}.integrated_geometry" if __package__ else "integrated_geometry"
    )
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            return None
        raise


def _support_cable_module() -> Any | None:
    module_name = (
        f"{__package__}.support_cable_geometry"
        if __package__
        else "support_cable_geometry"
    )
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name == module_name:
            return None
        raise


def _saved_mesh_report(name: str, mesh: Any) -> dict[str, Any]:
    try:
        extents = tuple(float(value) for value in mesh.extents)
        if len(extents) != 3 or not all(math.isfinite(value) and value > 0 for value in extents):
            raise ValueError("non-positive or non-finite extents")
        frozen = model_io.canonicalize_mesh(mesh)
        serialized = model_io.serialized_mesh_evidence(frozen)
    except Exception as error:  # report the blocker; never publish through it
        return {"mesh_id": name, "valid": False, "error": str(error)}
    allowance = 14.2
    required = (extents[0] + allowance, extents[1] + allowance, extents[2])
    fits = required[2] <= 180.0 and (
        (required[0] <= 180.0 and required[1] <= 180.0)
        or (required[1] <= 180.0 and required[0] <= 180.0)
    )
    return {
        "mesh_id": name,
        "valid": bool(serialized["closed_one_body_positive"] and fits),
        "raw_extents_mm": [round(value, 6) for value in extents],
        "required_build_volume_mm": [round(value, 6) for value in required],
        "fits_a1_mini_with_14p2_mm_xy_allowance": fits,
        "serialized_mesh": serialized,
    }


def geometry_gate_report() -> dict[str, Any]:
    """Audit both exact R11 providers without substituting predecessor parts."""

    geometry = _geometry_module()
    support_cable_geometry = _support_cable_module()
    blockers: list[str] = []
    if geometry is None:
        return {
            "passed": False,
            "checks": {"integrated_geometry_module_present": False},
            "expected_part_order": list(PART_ORDER),
            "available_part_order": [],
            "saved_mesh_reports": [],
            "analytic_blockers": ["R11 integrated_geometry.py is missing"],
            "physical_and_field_blockers": [],
        }

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
    structural_evidence_builder = getattr(
        geometry, "build_outer_terminal_bay_evidence", None
    )
    support_cable_evidence_builder = (
        getattr(
            support_cable_geometry,
            "build_outer_bay_support_cable_evidence",
            None,
        )
        if support_cable_geometry is not None
        else None
    )

    structural: Mapping[str, Any] = {}
    support_cable: Mapping[str, Any] = {}
    structural_evidence: Mapping[str, Any] = {}
    support_cable_evidence: Mapping[str, Any] = {}
    if not callable(structural_builder):
        blockers.append("terminal-bay saved-mesh provider is missing")
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            structural = structural_builder()
    if not callable(support_cable_builder):
        blockers.append(
            "R11 support_cable_geometry saved-mesh provider is missing"
        )
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            support_cable = support_cable_builder()
    if not callable(structural_evidence_builder):
        blockers.append("terminal-bay analytic evidence provider is missing")
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            structural_evidence = structural_evidence_builder()
    if not callable(support_cable_evidence_builder):
        blockers.append(
            "R11 support_cable_geometry analytic evidence provider is missing"
        )
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            support_cable_evidence = support_cable_evidence_builder()

    structural_order = tuple(structural)
    support_cable_order = tuple(support_cable)
    if structural and structural_order != STRUCTURAL_PROVIDER_PART_ORDER:
        blockers.append("terminal-bay saved-part identity/order changed")
    if support_cable and support_cable_order != SUPPORT_CABLE_PROVIDER_PART_ORDER:
        blockers.append("support/cable saved-part identity/order changed")
    overlap = set(structural).intersection(support_cable)
    if overlap:
        blockers.append(f"R11 geometry providers overlap: {sorted(overlap)}")
    combined = {**dict(structural), **dict(support_cable)}
    available_order = tuple(name for name in PART_ORDER if name in combined)
    missing = [name for name in PART_ORDER if name not in combined]
    if missing:
        blockers.append(f"exact R11 qualification meshes are missing: {missing}")
    extra = sorted(set(combined) - set(PART_ORDER))
    if extra:
        blockers.append(f"unexpected R11 qualification meshes exist: {extra}")

    mesh_reports = [
        _saved_mesh_report(name, combined[name])
        for name in available_order
    ]
    if any(report["valid"] is not True for report in mesh_reports):
        blockers.append("one or more R11 saved meshes failed neutral/envelope checks")

    structural_evidence_passed = bool(
        structural_evidence.get("geometry_subset_passed") is True
    )
    support_cable_evidence_passed = bool(
        support_cable_evidence.get("geometry_subset_passed") is True
    )
    structural_support_map = structural_evidence.get("support_required_by_part")
    support_cable_support_map = support_cable_evidence.get(
        "support_required_by_part"
    )
    support_free_contract_passed = bool(
        structural_support_map
        == {name: False for name in STRUCTURAL_PROVIDER_PART_ORDER}
        and support_cable_support_map
        == {name: False for name in SUPPORT_CABLE_PROVIDER_PART_ORDER}
    )
    layer_connectivity_passed = bool(
        structural_evidence.get("all_saved_layer_islands_clear") is True
        and support_cable_evidence.get("all_saved_layer_islands_clear") is True
    )
    if not structural_evidence_passed:
        blockers.append("terminal-bay analytic evidence is incomplete")
    if not support_cable_evidence_passed:
        blockers.append("support/cable analytic evidence is incomplete")
    if not support_free_contract_passed:
        blockers.append("authored support-free intent evidence is incomplete")
    if not layer_connectivity_passed:
        blockers.append("saved-layer connectivity evidence is incomplete")

    checks = {
        "integrated_geometry_module_present": True,
        "support_cable_geometry_module_present": support_cable_geometry is not None,
        "terminal_bay_provider_complete": (
            structural_order == STRUCTURAL_PROVIDER_PART_ORDER
        ),
        "support_cable_provider_complete": (
            support_cable_order == SUPPORT_CABLE_PROVIDER_PART_ORDER
        ),
        "exact_eight_unique_articles": (
            set(combined) == set(PART_ORDER) and len(combined) == 8
        ),
        "bay0_uses_two_terminal_halves": (
            LEFT_TERMINAL_HALF_PART in combined
            and RIGHT_TERMINAL_HALF_PART in combined
            and not any("regular" in name for name in combined)
        ),
        "all_saved_meshes_are_one_body_closed_positive_and_fit": bool(
            len(mesh_reports) == 8
            and all(report["valid"] is True for report in mesh_reports)
        ),
        "terminal_bay_analytic_evidence_passed": structural_evidence_passed,
        "support_cable_analytic_evidence_passed": support_cable_evidence_passed,
        "authored_support_free_intent_passed": support_free_contract_passed,
        "saved_layer_connectivity_passed": layer_connectivity_passed,
        "no_predecessor_substitution": all(name.startswith("r11_") for name in combined),
    }
    evidence_blockers: list[str] = []
    for evidence in (structural_evidence, support_cable_evidence):
        for item in evidence.get("subset_analytic_blockers", ()):
            evidence_blockers.append(str(item))
    blockers.extend(evidence_blockers)
    physical: list[str] = []
    for evidence in (structural_evidence, support_cable_evidence):
        for item in evidence.get("subset_physical_and_field_blockers", ()):
            physical.append(str(item))
    return {
        "passed": all(checks.values()) and not blockers,
        "checks": checks,
        "expected_part_order": list(PART_ORDER),
        "available_part_order": list(available_order),
        "saved_mesh_reports": mesh_reports,
        "terminal_bay_evidence": dict(structural_evidence),
        "support_cable_evidence": dict(support_cable_evidence),
        "analytic_blockers": sorted(set(blockers)),
        "physical_and_field_blockers": sorted(set(physical)),
    }


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
        "blockers": ["no deterministic R11 outer-bay qualification bundle was supplied"],
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
        individual_mesh_count == 8,
        catalog_object_count == 8,
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
        "blockers": [] if all(checks) else ["neutral R11 artifact contract is incomplete"],
    }


def _expected_bundle_paths() -> list[str]:
    return sorted(
        [
            *HANDOFF_DOCUMENTS,
            "README.md",
            "layout_report.json",
            "manifest.json",
            "normalized_inputs.json",
            "release_status.json",
            "requirements.txt",
            "validation.json",
            ASSEMBLY_VISUAL_RELATIVE_PATH,
            f"model_only_3mf/{CATALOG_FILENAME}",
            *[f"stl/{name}.stl" for name in PART_ORDER],
            *[
                f"individual_model_only_3mf/MODEL_ONLY_{name}.3mf"
                for name in PART_ORDER
            ],
        ]
    )


def inspect_artifact_bundle(bundle: Path) -> dict[str, Any]:
    """Independently audit an R11 neutral bundle without importing its builder."""

    root = Path(bundle)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("R11 bundle must be a real directory")
    if any(path.is_symlink() for path in root.rglob("*")):
        raise ValueError("R11 bundle may not contain symlinks")
    manifest = strict_json(root / "manifest.json")
    if manifest.get("package_id") != PACKAGE_ID:
        raise ValueError("R11 package identity changed")
    actual_paths = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )
    actual_directories = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_dir()
    )
    if actual_directories != [
        "individual_model_only_3mf",
        "model_only_3mf",
        "stl",
        "visuals",
    ]:
        raise ValueError("R11 bundle directory allowlist changed")
    if actual_paths != manifest.get("exact_file_allowlist"):
        raise ValueError("R11 bundle file allowlist changed")
    if actual_paths != _expected_bundle_paths():
        raise ValueError("R11 bundle contains a forbidden or missing artifact type")
    forbidden_suffixes = {".gcode", ".bgcode", ".gco", ".3mf~"}
    if any(path.suffix.lower() in forbidden_suffixes for path in root.rglob("*")):
        raise ValueError("R11 bundle contains G-code or a toolpath artifact")
    forbidden_name_tokens = ("slicer_profile", "process_profile", "filament_profile")
    if any(
        any(token in path.name.lower() for token in forbidden_name_tokens)
        for path in root.rglob("*")
        if path.is_file()
    ):
        raise ValueError("R11 bundle contains a slicer/profile artifact")
    records = _artifact_records(root)
    if records != manifest.get("hashed_artifacts_excluding_manifest"):
        raise ValueError("R11 bundle artifact hashes changed")
    if (
        manifest.get("artifact_count_excluding_manifest") != len(records)
        or manifest.get("artifact_bytes_excluding_manifest")
        != sum(record["bytes"] for record in records)
    ):
        raise ValueError("R11 artifact count or byte total changed")
    if manifest.get("publication_boundary") != PUBLICATION_BOUNDARY:
        raise ValueError("R11 publication safety boundary changed")
    order = tuple(manifest.get("object_names_in_order", ()))
    if order != PART_ORDER or len(set(order)) != 8:
        raise ValueError("R11 outer-bay inventory identity/order changed")
    if tuple(manifest.get("terminal_bay_part_order", ())) != STRUCTURAL_PROVIDER_PART_ORDER:
        raise ValueError("R11 terminal-bay inventory changed")
    if tuple(manifest.get("support_cable_part_order", ())) != SUPPORT_CABLE_PROVIDER_PART_ORDER:
        raise ValueError("R11 support/cable inventory changed")

    digests = manifest.get("geometry_digests_by_mesh_id", {})
    if set(digests) != set(order):
        raise ValueError("R11 geometry digest inventory changed")
    for name in order:
        inspection = model_io.inspect_model_only_3mf(
            root / "individual_model_only_3mf" / f"MODEL_ONLY_{name}.3mf"
        )
        if tuple(inspection.objects) != (name,):
            raise ValueError(f"R11 individual object identity changed: {name}")
        model_digest = model_io.canonical_triangle_digest(inspection.objects[name])
        stl_digest = model_io.canonical_triangle_digest(
            model_io.read_binary_stl(root / "stl" / f"{name}.stl")
        )
        if model_digest != digests[name] or stl_digest != digests[name]:
            raise ValueError(f"R11 STL/3MF geometry mismatch: {name}")
    catalog = model_io.inspect_model_only_3mf(
        root / "model_only_3mf" / CATALOG_FILENAME
    )
    if tuple(catalog.objects) != order:
        raise ValueError("R11 catalog object order changed")
    catalog_translations_json = {
        name: list(translation)
        for name, translation in catalog.translations_mm.items()
    }
    if catalog_translations_json != manifest.get("catalog_translations_mm"):
        raise ValueError("R11 catalog transforms changed")
    for name in order:
        if model_io.canonical_triangle_digest(catalog.objects[name]) != digests[name]:
            raise ValueError(f"R11 catalog geometry mismatch: {name}")
    prior_right: float | None = None
    catalog_left = math.inf
    catalog_right = -math.inf
    for name in order:
        translation = catalog.translations_mm[name]
        if translation[1:] != (0.0, 0.0):
            raise ValueError("R11 catalog may use only deterministic X translations")
        vertices = catalog.objects[name].vertices
        left = float(vertices[:, 0].min()) + translation[0]
        right = float(vertices[:, 0].max()) + translation[0]
        if prior_right is not None and left < prior_right + 19.999999:
            raise ValueError("R11 catalog articles lost their 20 mm inspection gap")
        prior_right = right
        catalog_left = min(catalog_left, left)
        catalog_right = max(catalog_right, right)
    if catalog_right - catalog_left <= 180.0:
        raise ValueError("R11 combined catalog is not demonstrably off-plate")

    live_sources = source_records()
    if manifest.get("source_records") != live_sources:
        raise ValueError("R11 manifest source snapshot changed")
    if manifest.get("source_tree_evidence") != source_tree_evidence(live_sources):
        raise ValueError("R11 manifest source-tree identity changed")
    runtime = runtime_provenance()
    runtime_matches = bool(
        manifest.get("runtime_provenance") == runtime
        and runtime["requirements_runtime_exact_match"] is True
    )
    normalized = strict_json(root / "normalized_inputs.json")
    live_config = strict_json(R11_ROOT / "config.json")
    if normalized != live_config:
        raise ValueError("R11 normalized inputs changed")
    live_config_digest = canonical_json_sha256(live_config)
    if manifest.get("canonical_config_sha256") != live_config_digest:
        raise ValueError("R11 manifest config identity changed")
    report = strict_json(root / "layout_report.json")
    if report != layout.build_plan(live_config):
        raise ValueError("R11 layout report changed")
    for document in HANDOFF_DOCUMENTS:
        if (root / document).read_bytes() != (R11_ROOT / document).read_bytes():
            raise ValueError(f"R11 handoff document changed: {document}")
    bundled_visual = inspect_assembly_visual(root / ASSEMBLY_VISUAL_RELATIVE_PATH)
    source_visual = inspect_assembly_visual(R11_ROOT / ASSEMBLY_VISUAL_RELATIVE_PATH)
    if bundled_visual != source_visual or (
        root / ASSEMBLY_VISUAL_RELATIVE_PATH
    ).read_bytes() != (R11_ROOT / ASSEMBLY_VISUAL_RELATIVE_PATH).read_bytes():
        raise ValueError("R11 bundled assembly visual changed")
    if manifest.get("assembly_visual") != source_visual:
        raise ValueError("R11 manifest assembly-visual identity changed")
    if (root / "requirements.txt").read_bytes() != (
        PROJECT_ROOT / "requirements.txt"
    ).read_bytes():
        raise ValueError("R11 bundled requirements lock changed")
    validation = strict_json(root / "validation.json")
    if validation.get("canonical_config_sha256") != live_config_digest:
        raise ValueError("R11 validation config identity changed")
    if validation.get("source_records") != live_sources:
        raise ValueError("R11 validation source snapshot changed")
    if validation.get("source_tree_evidence") != source_tree_evidence(live_sources):
        raise ValueError("R11 validation source-tree identity changed")
    if validation.get("runtime_provenance") != runtime:
        raise ValueError("R11 validation runtime provenance changed")
    for name, expected in {
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
    }.items():
        if validation.get(name) != expected:
            raise ValueError(f"R11 validation safety field changed: {name}")
    if tuple(validation.get("object_names_in_order", ())) != PART_ORDER:
        raise ValueError("R11 validation inventory changed")
    if validation.get("assembly_visual") != source_visual:
        raise ValueError("R11 validation assembly-visual identity changed")
    stored_status = strict_json(root / "release_status.json")
    if stored_status.get("package_id") != PACKAGE_ID:
        raise ValueError("R11 stored release-status package identity changed")
    for name, expected in {
        "full_wall_set_complete": False,
        "all_physical_gates_complete": False,
        "production_ready": False,
        "wall_installation_authorized": False,
        "drilling_coordinates_released": False,
        "drilling_schedule_released": False,
        "print_authorized": False,
        "test_load_authorized": False,
        "fresh_human_permission_required_before_every_print": True,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
    }.items():
        if stored_status.get(name) != expected:
            raise ValueError(f"R11 stored release-status safety field changed: {name}")
    return complete_artifact_gate(
        individual_mesh_count=len(order),
        catalog_object_count=len(catalog.objects),
        neutral_3mf_audit_passed=True,
        stl_geometry_matches_3mf=True,
        source_snapshot_matches_live_tree=True,
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
    neutral_complete = bool(
        config["passed"] and geometry["passed"] and artifact.get("passed")
    )
    blockers = [
        *config["open_physical_and_field_gates"],
        *geometry["analytic_blockers"],
        *geometry["physical_and_field_blockers"],
        *artifact.get("blockers", ()),
    ]
    return {
        "schema_version": "r11_release_status_v1",
        "package_id": PACKAGE_ID,
        "first_outer_actual_bay_neutral_bundle_complete": neutral_complete,
        "full_wall_set_complete": False,
        "all_physical_gates_complete": False,
        "production_ready": False,
        "wall_installation_authorized": False,
        "drilling_coordinates_released": False,
        "drilling_schedule_released": False,
        "print_authorized": False,
        "test_load_authorized": False,
        "fresh_human_permission_required_before_every_print": True,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
        "config_gate": config,
        "geometry_gate": geometry,
        "artifact_gate": artifact,
        "open_release_blockers": sorted(set(str(item) for item in blockers)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_release_status(bundle=args.bundle), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
