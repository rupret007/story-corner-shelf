#!/usr/bin/env python3
"""Build the deterministic, unsliced R8 PETG qualification bundle.

The caller must provide a fresh destination.  All files are built in a hidden
sibling stage, validated there, and published with a kernel-level atomic
no-replace rename.  This module never defaults to ``development/r8/generated``.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
from typing import Any

import numpy as np
import trimesh


R8_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = R8_ROOT.parents[1]
DEVELOPMENT_ROOT = R8_ROOT.parent
if str(R8_ROOT) not in sys.path:
    sys.path.insert(0, str(R8_ROOT))

import accessory_geometry as accessory  # noqa: E402
import design_math  # noqa: E402
import interface_geometry as interface  # noqa: E402
import model_io  # noqa: E402
import production_plan  # noqa: E402
import shelf_geometry as shelf  # noqa: E402


PACKAGE_ID = "r8_16b_petg_qualification_v2"
PACKAGE_FILENAME = "MODEL_ONLY_R8_QUALIFICATION_ALL_PARTS.3mf"
MODEL_DESCRIPTION = (
    "UNSLICED R8 QUALIFICATION-ONLY PETG MODEL; 100 PERCENT SCALE; "
    "ZERO RATED LOAD; PHYSICAL TESTING AND VERIFIED WALL FRAMING REQUIRED"
)
PART_GAP_MM = 10.0
COMBINED_CATALOG_WIDTH_MM = 520.0
SOURCE_PATHS = (
    "requirements.txt",
    "development/r8/config.json",
    "development/r8/FROZEN_BASELINES.json",
    "development/r8/design_math.py",
    "development/r8/shelf_geometry.py",
    "development/r8/accessory_geometry.py",
    "development/r8/interface_geometry.py",
    "development/r8/model_io.py",
    "development/r8/production_plan.py",
    "development/r8/generate_qualification.py",
)
RUNTIME_REQUIREMENTS = (
    ("numpy", "2.5.1"),
    ("shapely", "2.1.2"),
    ("trimesh", "5.0.0"),
    ("manifold3d", "3.5.2"),
    ("mapbox-earcut", "1.0.3"),
    ("scipy", "1.18.0"),
    ("networkx", "3.5"),
)
CLEARANCE_V2_PART_IDS = (
    "r8_clearance_ladder_receiver",
    "r8_clearance_key_0p2",
    "r8_clearance_key_0p3",
    "r8_clearance_key_0p4",
    "r8_clearance_key_0p5",
)
RETAINED_BLANK_PART_ID = "r8_retained_blank"


@dataclass(frozen=True)
class QualificationPart:
    mesh_id: str
    label: str
    print_orientation: str
    mesh: trimesh.Trimesh
    edge_reserve_each_side_mm: float = 0.0
    expected_support_required: bool | None = None
    minimum_first_layer_body_contact_mm2: float = 0.0


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _exact_numeric_zero(value: object) -> bool:
    return bool(
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) == 0.0
    )


def _validate_frozen_scope(payload: dict[str, Any]) -> None:
    """Reject any material, anchor, or release drift before writing files."""

    project = payload["project"]
    material = payload["material"]
    printer = payload["printer"]
    wall = payload["wall_attachment"]
    accessory_cfg = payload["accessory_system"]
    issues: list[str] = []
    if project.get("qualification_only") is not True:
        issues.append("project.qualification_only")
    for key in (
        "installed_release_allowed",
        "physical_qualification_complete",
        "production_ready",
        "load_rating_allowed",
        "tested_load_rating_exists",
        "wall_bores_emitted",
        "embedded_gcode_allowed",
    ):
        if project.get(key) is not False:
            issues.append(f"project.{key}")
    for key in ("rated_load_kg", "rated_load_lb"):
        if not _exact_numeric_zero(project.get(key)):
            issues.append(f"project.{key}")
    if material.get("printed_material") != "PETG only":
        issues.append("material.printed_material")
    if material.get("primary_part_material") != "PETG":
        issues.append("material.primary_part_material")
    for key in (
        "pla_allowed_in_primary_or_load_path_parts",
        "structural_credit_from_accessories_allowed",
        "printed_wall_anchors_allowed",
        "hollow_wall_anchors_allowed_in_primary_load_path",
    ):
        if material.get(key) is not False:
            issues.append(f"material.{key}")
    if printer.get("filament_product") != "PETG":
        issues.append("printer.filament_product")
    preset = printer.get("filament_preset")
    if (
        not isinstance(preset, str)
        or "PETG" not in preset.upper()
        or "PLA" in preset.upper()
    ):
        issues.append("printer.filament_preset")
    if wall.get("continuous_blocking_or_verified_equivalent_required") is not True:
        issues.append("wall_attachment.continuous_blocking_required")
    if wall.get("printed_fastener_or_anchor_substitution_allowed") is not False:
        issues.append("wall_attachment.printed_fastener_substitution")
    if accessory_cfg.get("structural_or_shelf_load_credit") is not False:
        issues.append("accessory_system.structural_or_shelf_load_credit")
    for key in ("rated_load_kg", "rated_load_lb"):
        if not _exact_numeric_zero(accessory_cfg.get(key)):
            issues.append(f"accessory_system.{key}")
    if issues:
        raise ValueError("R8 frozen PETG/safety scope drifted: " + ", ".join(issues))
    try:
        production_plan.validate_project_scope(payload)
    except production_plan.PlanningBlocked as error:
        raise ValueError(
            "R8 canonical planner scope drifted: " + ", ".join(error.blockers)
        ) from error


def _load_config() -> dict[str, Any]:
    payload = json.loads(
        (R8_ROOT / "config.json").read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    if not isinstance(payload, dict):
        raise ValueError("R8 config must be a JSON object")
    _validate_frozen_scope(payload)
    return payload


def _source_bundle() -> dict[str, Any]:
    records = [
        {
            "path": relative,
            "bytes": (REPOSITORY_ROOT / relative).stat().st_size,
            "sha256": model_io.sha256_file(REPOSITORY_ROOT / relative),
        }
        for relative in SOURCE_PATHS
    ]
    digest_payload = b"".join(
        f"{record['path']}\0{record['bytes']}\0{record['sha256']}\n".encode("utf-8")
        for record in records
    )
    return {
        "algorithm": "sha256",
        "records": records,
        "bundle_sha256": model_io.sha256_bytes(digest_payload),
    }


def runtime_provenance() -> dict[str, Any]:
    """Record and enforce the exact pinned geometry runtime."""

    requirements_path = REPOSITORY_ROOT / "requirements.txt"
    declared = tuple(
        line.strip()
        for line in requirements_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    expected = tuple(f"{name}=={version}" for name, version in RUNTIME_REQUIREMENTS)
    if declared != expected:
        raise ValueError("Root requirements.txt no longer matches the frozen R8 runtime")
    distributions: list[dict[str, Any]] = []
    for name, required in RUNTIME_REQUIREMENTS:
        try:
            observed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError(f"Required R8 runtime distribution is missing: {name}") from error
        if observed != required:
            raise RuntimeError(
                f"R8 runtime drift for {name}: required {required}, observed {observed}"
            )
        distributions.append(
            {
                "distribution": name,
                "required_version": required,
                "observed_version": observed,
                "exact_match": True,
            }
        )
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "requirements_path": "requirements.txt",
        "requirements_sha256": model_io.sha256_file(requirements_path),
        "requirements_exactly_matched": True,
        "distributions": distributions,
        "mesh_serialization": "canonical float32 triangles",
        "boolean_engine": "manifold",
    }


def _relabel_axes(mesh: trimesh.Trimesh, axes: tuple[int, int, int]) -> trimesh.Trimesh:
    """Relabel XYZ into a print orientation, preserve outward winding, normalize."""

    if tuple(sorted(axes)) != (0, 1, 2):
        raise ValueError("Print-axis relabel must be a permutation of XYZ")
    result = trimesh.Trimesh(
        vertices=np.asarray(mesh.vertices, dtype=float)[:, axes],
        faces=np.asarray(mesh.faces, dtype=np.int64).copy(),
        process=False,
    )
    if float(result.volume) < 0.0:
        result.invert()
    result.apply_translation(-np.asarray(result.bounds[0], dtype=float))
    result.remove_unreferenced_vertices()
    result.merge_vertices()
    result.fix_normals(multibody=True)
    return result


def clearance_v2_geometry_contract() -> dict[str, Any]:
    """Return exact receiver/key digests for the general v2 clearance gate."""

    ladder = accessory.build_clearance_ladder()
    meshes = [
        (CLEARANCE_V2_PART_IDS[0], _relabel_axes(ladder.receiver, (0, 2, 1))),
        *(
            (mesh_id, _relabel_axes(key, (0, 2, 1)))
            for mesh_id, key in zip(CLEARANCE_V2_PART_IDS[1:], ladder.keys)
        ),
    ]
    digests = {
        mesh_id: model_io.canonical_triangle_digest(
            model_io.canonicalize_mesh(mesh)
        )
        for mesh_id, mesh in meshes
    }
    if tuple(digests) != CLEARANCE_V2_PART_IDS or len(set(digests.values())) != 5:
        raise ValueError("R8 v2 clearance receiver/key digest contract drifted")
    return {
        "source_package_id": PACKAGE_ID,
        "contract_version": 1,
        "clearance_per_face_mm_in_order": list(ladder.clearances_mm),
        "mesh_ids_in_order": list(CLEARANCE_V2_PART_IDS),
        "canonical_float32_triangle_digests": digests,
    }


def retained_blank_v2_geometry_digest() -> str:
    """Return the canonical local-print blank digest shared by both v2 bundles."""

    mesh = interface.orient_retained_module_for_print(
        interface.build_retained_accessory("blank")
    )
    return model_io.canonical_triangle_digest(model_io.canonicalize_mesh(mesh))


def _longest_cassettes(
    cfg: dict[str, Any],
) -> tuple[trimesh.Trimesh, trimesh.Trimesh, dict[str, Any]]:
    plan = design_math.calculate_plan(cfg)
    candidates: list[tuple[float, str, int]] = []
    for run in (plan.through, plan.return_run):
        for index, width in enumerate(run.physical_module_widths_mm):
            candidates.append((round(float(width), 9), run.run_id, index))
    longest_width = max(width for width, _run, _index in candidates)
    selected = min(
        (item for item in candidates if item[0] == longest_width),
        key=lambda item: (item[1], item[2]),
    )
    selected_dimensions = cfg["shelf"]["selected_cassette_geometry_mm"]
    u_box, u_box_metrics = shelf.build_front_first_u_box_cassette(
        longest_width,
        top_skin_mm=float(selected_dimensions["top_skin"]),
        bottom_skin_mm=float(selected_dimensions["bottom_skin"]),
        visible_front_wall_mm=float(selected_dimensions["visible_front_wall"]),
        full_depth_end_land_mm=float(selected_dimensions["full_depth_end_land"]),
        internal_web_mm=float(selected_dimensions["internal_web"]),
        internal_web_count=int(selected_dimensions["internal_web_count"]),
    )
    coffer, coffer_metrics = shelf.build_coffered_cassette_seed(longest_width)
    yaw = float(cfg["shelf"]["cassette_saved_orientation_candidate"]["bed_yaw_deg"])
    oriented_u_box = shelf.orient_cassette_on_long_edge(u_box, yaw_degrees=yaw)
    oriented_coffer = shelf.orient_cassette_on_long_edge(coffer, yaw_degrees=yaw)
    return oriented_u_box, oriented_coffer, {
        "selected_candidate": cfg["shelf"]["selected_cassette_candidate"],
        "selected_run": selected[1],
        "selected_module_index_zero_based": selected[2],
        "selected_physical_length_mm": selected[0],
        "selected_u_box_metrics": asdict(u_box_metrics),
        "matched_heavy_coffer_control_metrics": asdict(coffer_metrics),
        "selected_u_box_volume_mm3": round(float(u_box.volume), 6),
        "matched_heavy_coffer_control_volume_mm3": round(float(coffer.volume), 6),
        "selected_to_control_volume_ratio": round(
            float(u_box.volume) / float(coffer.volume), 9
        ),
    }


def _qualification_parts(
    cfg: dict[str, Any],
) -> tuple[list[QualificationPart], dict[str, Any]]:
    wrapper = interface.build_eligible_d_frame_wrapper("through", 4, 9)
    preservation = interface.core_preservation_report(wrapper)
    if not preservation.additive_only:
        raise ValueError("Eligible D-frame wrapper no longer preserves its structural core")
    curved, straight = shelf.build_matched_corbel_pair()
    # The profiles are analytically equal-area. Manifold's faceted volume
    # integration differs by about 0.013 mm3 across ~279,000 mm3, so retain a
    # far tighter than process-scale 0.05 mm3 serialization tolerance.
    if abs(float(curved.volume) - float(straight.volume)) > 0.05:
        raise ValueError("Straight D-frame control is no longer equal-volume")
    selected_cassette, coffer_control, cassette_record = _longest_cassettes(cfg)
    ladder = accessory.build_clearance_ladder()
    reserve = float(
        cfg["shelf"]["cassette_saved_orientation_candidate"][
            "edge_reserve_each_side_mm"
        ]
    )
    d_frame_reserve = float(cfg["d_frame"]["saved_edge_reserve_each_side_mm"])
    parts = [
        QualificationPart(
            "r8_curved_eligible_d_frame_mount",
            "Curved eligible D-frame with additive rail bosses",
            "broad run-side face down; installed Y/Z relabelled to bed X/Y",
            _relabel_axes(wrapper.body, (1, 2, 0)),
            edge_reserve_each_side_mm=d_frame_reserve,
            expected_support_required=False,
        ),
        QualificationPart(
            "r8_smooth_curved_core",
            "Unmodified curved D-frame structural core",
            "broad run-side face down in native source orientation",
            _relabel_axes(curved, (0, 1, 2)),
            edge_reserve_each_side_mm=d_frame_reserve,
            expected_support_required=False,
        ),
        QualificationPart(
            "r8_equal_volume_straight_control",
            "Equal-envelope equal-volume straight control",
            "broad run-side face down in native source orientation",
            _relabel_axes(straight, (0, 1, 2)),
            edge_reserve_each_side_mm=d_frame_reserve,
            expected_support_required=False,
        ),
        QualificationPart(
            "r8_selected_front_first_u_box_cassette",
            "Selected longest front-first open-back U-box cassette qualification candidate",
            "visible front long edge down with frozen 45 degree bed yaw",
            selected_cassette,
            edge_reserve_each_side_mm=reserve,
            expected_support_required=False,
        ),
        QualificationPart(
            "r8_matched_heavy_coffer_control",
            "Matched-length heavy coffer cassette control",
            "visible front long edge down with frozen 45 degree bed yaw",
            coffer_control,
            edge_reserve_each_side_mm=reserve,
            expected_support_required=False,
        ),
        QualificationPart(
            "r8_mounted_retention_rail",
            "Mounted three-station retention rail",
            "broad rear face down; installed X/Z relabelled to bed X/Y",
            _relabel_axes(interface.build_mounted_retention_rail(), (0, 2, 1)),
            expected_support_required=False,
        ),
        QualificationPart(
            "r8_retained_blank",
            "Retained blank module",
            "local XY on bed; 180 degree X flip; local negative Z builds upward",
            interface.orient_retained_module_for_print(
                interface.build_retained_accessory("blank")
            ),
            minimum_first_layer_body_contact_mm2=(
                interface.BLANK_MINIMUM_FIRST_LAYER_BODY_CONTACT_MM2
            ),
            expected_support_required=False,
        ),
        QualificationPart(
            "r8_retained_single_peg",
            "Retained lightweight single-cable peg",
            "local XY on bed; 180 degree X flip; painted support required",
            interface.orient_retained_module_for_print(
                interface.build_retained_accessory("single_peg")
            ),
            expected_support_required=True,
        ),
        QualificationPart(
            "r8_retained_three_cable_comb",
            "Retained three-position cable comb",
            "local XY on bed; 180 degree X flip; painted support required",
            interface.orient_retained_module_for_print(
                interface.build_retained_accessory("three_cable_comb")
            ),
            expected_support_required=True,
        ),
        QualificationPart(
            "r8_retained_shortened_coil_j_hook",
            "Retained shortened lightweight cable-coil J-hook",
            "local XY on bed; 180 degree X flip; painted support required",
            interface.orient_retained_module_for_print(
                interface.build_retained_accessory("coil_j_hook")
            ),
            expected_support_required=True,
        ),
        QualificationPart(
            "r8_clearance_ladder_receiver",
            "Four-station 0.2/0.3/0.4/0.5 mm receiver ladder",
            "broad rear face down; source X/Z relabelled to bed X/Y",
            _relabel_axes(ladder.receiver, (0, 2, 1)),
            expected_support_required=False,
        ),
    ]
    for clearance, key in zip(ladder.clearances_mm, ladder.keys):
        slug = f"{clearance:.1f}".replace(".", "p")
        parts.append(
            QualificationPart(
                f"r8_clearance_key_{slug}",
                f"Common qualification key for {clearance:.1f} mm per-face clearance",
                "broad side face down; local X/Z relabelled to bed X/Y",
                _relabel_axes(key, (0, 2, 1)),
                expected_support_required=False,
            )
        )
    if len(parts) != 15 or len({part.mesh_id for part in parts}) != 15:
        raise AssertionError("R8 qualification inventory must contain 15 unique bodies")
    supplemental = {
        "d_frame_core_preservation": asdict(preservation),
        "curved_core_volume_mm3": round(float(curved.volume), 6),
        "straight_control_volume_mm3": round(float(straight.volume), 6),
        "equal_volume_absolute_delta_mm3": round(
            abs(float(curved.volume) - float(straight.volume)), 9
        ),
        "cassette": cassette_record,
        "clearance_ladder_per_face_mm": list(ladder.clearances_mm),
    }
    return parts, supplemental


def _candidate_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    printer = cfg["printer"]
    return {
        "status": "candidate values to enter and verify manually in Bambu Studio; not embedded",
        "profile_embedded": False,
        "support_and_brim_review_required": True,
        "scale_percent": 100.0,
        "printer": f"{printer['manufacturer']} {printer['model']}",
        "build_volume_mm": printer["printable_volume_mm"],
        "material": cfg["material"]["printed_material"],
        "filament": f"{printer['filament_manufacturer']} {printer['filament_product']} {printer['filament_color']}",
        "filament_manufacturer": printer["filament_manufacturer"],
        "filament_product": printer["filament_product"],
        "filament_color": printer["filament_color"],
        "filament_asin": printer["filament_asin"],
        "filament_product_url": printer["filament_product_url"],
        "filament_selected_variant": printer["filament_selected_variant"],
        "filament_preset": printer["filament_preset"],
        "nozzle_mm": printer["nozzle_mm"],
        "layer_height_mm": printer["layer_height_mm"],
        "wall_loops": printer["wall_loops"],
        "top_shell_layers": printer["top_shell_layers"],
        "bottom_shell_layers": printer["bottom_shell_layers"],
        "infill_percent": printer["infill_percent"],
        "infill_pattern": printer["infill_pattern"],
        "first_layer_nozzle_temperature_c": printer[
            "first_layer_nozzle_temperature_c"
        ],
        "other_layer_nozzle_temperature_c": printer[
            "other_layer_nozzle_temperature_c"
        ],
        "textured_pei_bed_temperature_c": printer[
            "textured_pei_bed_temperature_c"
        ],
        "flow_ratio": printer["flow_ratio"],
        "maximum_volumetric_speed_mm3_s": printer[
            "maximum_volumetric_speed_mm3_s"
        ],
        "fan_percent_range": [printer["fan_min_percent"], printer["fan_max_percent"]],
        "overhang_fan_percent": printer["overhang_fan_percent"],
        "brim_mm": printer["brim_mm"],
        "brim_object_gap_mm": printer["brim_object_gap_mm"],
        "drying_temperature_range_c": printer["drying_temperature_range_c"],
        "drying_duration_range_h": printer["drying_duration_range_h"],
        "drying_guidance_source_url": printer["drying_guidance_source_url"],
        "drying_received_spool_label_controls": printer[
            "drying_received_spool_label_controls"
        ],
        "drying_dryer_limit_controls": printer["drying_dryer_limit_controls"],
        "drying_never_exceed_lower_stated_limit": printer[
            "drying_never_exceed_lower_stated_limit"
        ],
        "drying_record_required": printer["drying_record_required"],
    }


def _accessory_layout(cfg: dict[str, Any]) -> dict[str, Any]:
    plan = design_math.calculate_plan(cfg)
    defaults = cfg["accessory_system"]["default_equipped_station_indices"]
    return {
        "geometrically_eligible_corbel_indices": {
            "through": list(plan.through.accessory_eligible_corbel_indices),
            "return": list(plan.return_run.accessory_eligible_corbel_indices),
        },
        "geometrically_eligible_rails_per_level": plan.accessory_eligible_corbels_per_level,
        "geometrically_eligible_rails_selected_two_levels": plan.accessory_eligible_corbels_selected_levels,
        "geometrically_eligible_sockets_per_level": plan.accessory_socket_count_per_level,
        "geometrically_eligible_sockets_selected_two_levels": plan.accessory_socket_count_selected_levels,
        "clean_default_equipped_corbel_indices": {
            "through": list(defaults["through"]),
            "return": list(defaults["return"]),
        },
        "clean_default_rails_per_level": plan.accessory_default_rails_per_level,
        "clean_default_rails_selected_two_levels": plan.accessory_default_rails_selected_levels,
        "clean_default_sockets_per_level": plan.accessory_default_socket_count_per_level,
        "clean_default_sockets_selected_two_levels": plan.accessory_default_socket_count_selected_levels,
        "sockets_per_rail": plan.accessory_sockets_per_eligible_corbel,
    }


def _print_envelope(
    serialized: model_io.SerializedMesh,
    *,
    cfg: dict[str, Any],
    edge_reserve_each_side_mm: float,
) -> dict[str, Any]:
    evidence = model_io.serialized_mesh_evidence(serialized)
    extents = [float(value) for value in evidence["extents_mm"]]
    brim = float(cfg["printer"]["brim_mm"])
    brim_gap = float(cfg["printer"]["brim_object_gap_mm"])
    required = [
        extents[0] + 2.0 * (brim + brim_gap + edge_reserve_each_side_mm),
        extents[1] + 2.0 * (brim + brim_gap + edge_reserve_each_side_mm),
        extents[2],
    ]
    available = [float(value) for value in cfg["printer"]["printable_volume_mm"]]
    return {
        "part_mm": [round(value, 6) for value in extents],
        "required_with_brim_and_reserved_edges_mm": [
            round(value, 6) for value in required
        ],
        "available_mm": available,
        "brim_mm": brim,
        "brim_object_gap_mm": brim_gap,
        "additional_edge_reserve_each_side_mm": edge_reserve_each_side_mm,
        "fits": all(
            needed <= allowed + 1.0e-6
            for needed, allowed in zip(required, available)
        ),
    }


def _combined_translations(
    meshes: list[tuple[str, model_io.SerializedMesh]],
) -> dict[str, tuple[float, float, float]]:
    x = PART_GAP_MM
    y = PART_GAP_MM
    row_height = 0.0
    translations: dict[str, tuple[float, float, float]] = {}
    placed: list[tuple[str, float, float, float, float]] = []
    for name, mesh in meshes:
        evidence = model_io.serialized_mesh_evidence(mesh)
        width, depth, _height = (float(value) for value in evidence["extents_mm"])
        if x > PART_GAP_MM and x + width > COMBINED_CATALOG_WIDTH_MM:
            x = PART_GAP_MM
            y += row_height + PART_GAP_MM
            row_height = 0.0
        translations[name] = (round(x, 6), round(y, 6), 0.0)
        placed.append((name, x, x + width, y, y + depth))
        x += width + PART_GAP_MM
        row_height = max(row_height, depth)
    for index, left in enumerate(placed):
        for right in placed[index + 1 :]:
            overlap_x = min(left[2], right[2]) - max(left[1], right[1])
            overlap_y = min(left[4], right[4]) - max(left[3], right[3])
            if overlap_x > -PART_GAP_MM + 1.0e-6 and overlap_y > -PART_GAP_MM + 1.0e-6:
                raise ValueError(f"Combined catalog spacing drifted: {left[0]} / {right[0]}")
    return translations


def _bundle_readme(
    cfg: dict[str, Any], object_count: int, parts: list[dict[str, Any]]
) -> bytes:
    settings = _candidate_settings(cfg)
    cassette = next(
        record
        for record in parts
        if record["mesh_id"] == "r8_selected_front_first_u_box_cassette"
    )["a1_mini_candidate_envelope"]
    part_x, part_y, part_z = cassette["part_mm"]
    required_x, required_y, _required_z = cassette[
        "required_with_brim_and_reserved_edges_mm"
    ]
    drying_low, drying_high = settings["drying_temperature_range_c"]
    drying_hours_low, drying_hours_high = settings["drying_duration_range_h"]
    fan_low, fan_high = settings["fan_percent_range"]
    return f"""# R8 PETG qualification bundle

This is an **unsliced, zero-rated qualification set**, not an installed shelf
release. It contains {object_count} one-body test models, no wall-fastener
bores, no G-code, no toolpaths, and no embedded Bambu Studio process profile.

The frozen filament identity is **{settings['filament_manufacturer']}
{settings['filament_product']} {settings['filament_color']}**, ASIN
`{settings['filament_asin']}`: [selected listing]({settings['filament_product_url']}).
Selected variant: `{settings['filament_selected_variant']}`. Confirm the received
spool label before use; the label and dryer limit control, and the lower stated
temperature limit must never be exceeded.

## Open in Bambu Studio

1. Start a new `{settings['printer']} {settings['nozzle_mm']:g} nozzle` project
   with the Textured PEI
   plate. These neutral 3MFs do **not** select a printer, filament, or process
   preset. Never reuse a PLA preset for these PETG qualification parts.
2. Import one file from `individual_model_only_3mf/` at **100% scale**. Do not
   auto-scale, auto-orient, or repair it. The combined 3MF is an all-parts catalog;
   it is not one A1 mini plate, so do not slice the combined layout as-is.
3. Select `{settings['filament_preset']}` and `0.20mm Strength @BBL A1M`.
   Explicitly verify: {settings['layer_height_mm']:.2f} mm layers,
   {settings['wall_loops']} wall loops,
   {settings['top_shell_layers']} top / {settings['bottom_shell_layers']} bottom
   shell layers, {settings['infill_percent']}% **{settings['infill_pattern']}**
   infill, Brim type `Outer brim only`, {settings['brim_mm']:.1f} mm brim width,
   and {settings['brim_object_gap_mm']:.1f} mm brim-object gap.
4. Verify {settings['first_layer_nozzle_temperature_c']:g} C first layer /
   {settings['other_layer_nozzle_temperature_c']:g} C later layers,
   {settings['textured_pei_bed_temperature_c']:g} C bed,
   {settings['flow_ratio']:g} flow ratio,
   {settings['maximum_volumetric_speed_mm3_s']:g} mm^3/s maximum volumetric
   speed, {fan_low:g}-{fan_high:g}% normal fan, and
   {settings['overhang_fan_percent']:g}% overhang fan. The SUNLU standard-PETG
   baseline is {drying_low:g} C (validated lower/upper values:
   {drying_low:g} C / {drying_high:g} C)
   for {drying_hours_low:g}-{drying_hours_high:g} hours, conditional on the
   received spool label and dryer limit. Record the spool lot, exact drying
   cycle, and flow calibration before printing. Source:
   {settings['drying_guidance_source_url']}
5. Print the clearance receiver and keys first, testing **loosest to tightest**:
   0.5, 0.4, 0.3, then 0.2 mm per face. The authored interface is 0.4 mm; if
   0.4 does not qualify, stop and correct the process rather than scaling parts.
6. Continue only in this order: mounted rail + blank; one D-frame + rail fit;
   the remaining cable modules; then one selected U-box cassette. Curved,
   straight, and heavy-coffer controls are comparison articles, not shelf-set
   production parts.

## Support rules are part-specific

- The saved blank, rail, D-frames, clearance articles, and cassette candidates
  pass the deposited-layer connectivity gate. Start with Support OFF for those
  exact saved orientations, inspect Preview, and stop if Studio reports a new
  island or changes the orientation.
- The single peg, three-cable comb, and coil J-hook have intentional cable
  features that begin as unsupported islands in the saved orientation. Use
  manually reviewed/painted support for those three parts only, while keeping
  support out of the keyed head, latch, receiver, and rail-contact surfaces.
- Install combs from the bottom socket upward. Remove combs from the top socket
  downward; a moving comb is not independently serviceable beneath an occupied
  neighboring socket.

The selected U-box is already oriented with its **visible front long edge on
the plate** and a {cfg['shelf']['cassette_saved_orientation_candidate']['bed_yaw_deg']:g}
degree bed yaw. Its validated part envelope is {part_x:.4f} x {part_y:.4f} mm
by {part_z:g} mm high; {settings['brim_mm']:.1f} mm brim,
{settings['brim_object_gap_mm']:.1f} mm brim-object gap, and the independent
{cfg['shelf']['cassette_saved_orientation_candidate']['edge_reserve_each_side_mm']:g}
mm-per-edge reserve require {required_x:.4f} x {required_y:.4f} mm. Center it
on the plate. If
Studio reports an exclusion-zone
conflict, stop—never auto-scale it to force a fit.

The clean default layout equips alternating supports: through-run indices
1/3/5/7 and return-run indices 1/3. That is 6 rails / 18 sockets per level
(12 / 36 across two levels). All 10 interior supports per level remain
geometrically eligible, but are not all equipped by default.

Do not install or load these parts yet. Target shelf load, wall/framing survey,
metal structural screw schedule, cassette print proof, dimensional fit, cyclic
retention, thermal cycling, creep, proof-load, and destructive testing remain
unresolved. Printed wall anchors and hollow-wall anchors are not authorized in
the primary load path.
""".encode("utf-8")


def _artifact_kind(relative: str) -> str:
    if relative.startswith("stl/"):
        return "individual_stl"
    if relative.startswith("individual_model_only_3mf/"):
        return "individual_neutral_model_only_3mf"
    if relative.startswith("model_only_3mf/"):
        return "combined_neutral_model_only_3mf"
    if relative == "validation.json":
        return "validation_report"
    if relative == "README.md":
        return "bundle_readme"
    raise ValueError(f"Unclassified R8 artifact: {relative}")


def _build_stage(stage: Path) -> dict[str, Any]:
    cfg = _load_config()
    config_identity = production_plan.validate_artifact_coupled_config_identity(cfg)
    runtime = runtime_provenance()
    clearance_contract = clearance_v2_geometry_contract()
    sources_before = _source_bundle()
    parts, geometry_context = _qualification_parts(cfg)
    settings = _candidate_settings(cfg)
    accessory_layout = _accessory_layout(cfg)
    blockers = list(design_math.production_blockers(cfg))
    if not blockers:
        raise ValueError("Qualification bundle unexpectedly has no release blockers")

    serialized_by_name: dict[str, model_io.SerializedMesh] = {}
    part_validation: list[dict[str, Any]] = []
    for part in parts:
        serialized = model_io.canonicalize_mesh(part.mesh)
        serialized_by_name[part.mesh_id] = serialized
        source_evidence = model_io.serialized_mesh_evidence(serialized)
        layer_evidence: dict[str, Any] | None = None
        if part.expected_support_required is not None:
            serialized_mesh = trimesh.Trimesh(
                vertices=np.asarray(serialized.vertices, dtype=float),
                faces=np.asarray(serialized.faces, dtype=np.int64),
                process=False,
            )
            layer_report = interface.saved_oriented_layer_island_report(
                serialized_mesh,
                layer_height_mm=float(cfg["printer"]["layer_height_mm"]),
            )
            if layer_report.support_required is not part.expected_support_required:
                raise ValueError(
                    f"{part.mesh_id}: saved-layer support classification drifted"
                )
            if (
                layer_report.first_layer_body_contact_area_mm2 + 1.0e-6
                < part.minimum_first_layer_body_contact_mm2
            ):
                raise ValueError(
                    f"{part.mesh_id}: first-layer body contact is below its gate"
                )
            layer_evidence = asdict(layer_report)
        envelope = _print_envelope(
            serialized,
            cfg=cfg,
            edge_reserve_each_side_mm=part.edge_reserve_each_side_mm,
        )
        if not source_evidence["closed_one_body_positive"] or not envelope["fits"]:
            raise ValueError(f"{part.mesh_id}: failed body or A1 mini envelope audit")

        stl_path = stage / "stl" / f"{part.mesh_id}.stl"
        model_io.write_binary_stl(stl_path, serialized)
        stl_mesh = model_io.read_binary_stl(stl_path)
        stl_evidence = model_io.serialized_mesh_evidence(stl_mesh)

        individual_relative = (
            f"individual_model_only_3mf/MODEL_ONLY_{part.mesh_id}.3mf"
        )
        individual_path = stage / individual_relative
        model_io.write_model_only_3mf(
            individual_path,
            f"Story Corner {part.label}",
            MODEL_DESCRIPTION,
            [model_io.ModelObject(part.mesh_id, serialized)],
        )
        individual = model_io.inspect_model_only_3mf(individual_path)
        individual_mesh = individual.objects[part.mesh_id]
        digests = {
            "source_float32": model_io.canonical_triangle_digest(serialized),
            "stl": model_io.canonical_triangle_digest(stl_mesh),
            "individual_3mf": model_io.canonical_triangle_digest(individual_mesh),
        }
        if len(set(digests.values())) != 1:
            raise ValueError(f"{part.mesh_id}: STL/individual-3MF geometry is not bijective")
        if individual.translations_mm != {part.mesh_id: (0.0, 0.0, 0.0)}:
            raise ValueError(f"{part.mesh_id}: individual 3MF changed scale or placement")
        part_validation.append(
            {
                "mesh_id": part.mesh_id,
                "label": part.label,
                "print_orientation": part.print_orientation,
                "scale_percent": 100.0,
                "stl_path": stl_path.relative_to(stage).as_posix(),
                "individual_3mf_path": individual_relative,
                "serialized_geometry_digests": digests,
                "serialized_geometry_evidence": stl_evidence,
                "a1_mini_candidate_envelope": envelope,
                "saved_layer_support_evidence": layer_evidence,
                "individual_3mf_neutral_checks": individual.checks,
            }
        )

    actual_clearance_digests = {
        mesh_id: model_io.canonical_triangle_digest(serialized_by_name[mesh_id])
        for mesh_id in CLEARANCE_V2_PART_IDS
    }
    if actual_clearance_digests != clearance_contract[
        "canonical_float32_triangle_digests"
    ]:
        raise ValueError("General v2 clearance parts no longer match their source contract")
    retained_blank_digest = retained_blank_v2_geometry_digest()
    if (
        model_io.canonical_triangle_digest(
            serialized_by_name[RETAINED_BLANK_PART_ID]
        )
        != retained_blank_digest
    ):
        raise ValueError("General v2 blank no longer matches its local mesh contract")

    ordered_meshes = [(part.mesh_id, serialized_by_name[part.mesh_id]) for part in parts]
    translations = _combined_translations(ordered_meshes)
    combined_relative = f"model_only_3mf/{PACKAGE_FILENAME}"
    combined_path = stage / combined_relative
    model_io.write_model_only_3mf(
        combined_path,
        "Story Corner R8 all-parts qualification catalog",
        MODEL_DESCRIPTION,
        [
            model_io.ModelObject(name, mesh, translations[name])
            for name, mesh in ordered_meshes
        ],
    )
    combined = model_io.inspect_model_only_3mf(combined_path)
    expected_object_order = tuple(part.mesh_id for part in parts)
    if tuple(combined.objects) != expected_object_order:
        raise ValueError("Combined qualification 3MF object order or set drifted")
    if combined.translations_mm != translations:
        raise ValueError("Combined qualification 3MF translations changed on readback")
    for record in part_validation:
        name = record["mesh_id"]
        digest = model_io.canonical_triangle_digest(combined.objects[name])
        record["serialized_geometry_digests"]["combined_3mf"] = digest
        if len(set(record["serialized_geometry_digests"].values())) != 1:
            raise ValueError(f"{name}: STL/individual/combined geometry bijection failed")

    model_io.write_bytes_exclusive(
        stage / "README.md", _bundle_readme(cfg, len(parts), part_validation)
    )
    sources_after = _source_bundle()
    if sources_before != sources_after:
        raise RuntimeError("R8 source SHA bundle changed while geometry was generated")

    validation = {
        "schema_version": 1,
        "package_id": PACKAGE_ID,
        "validation_passed": True,
        "qualification_only": True,
        "unsliced": True,
        "generated_gcode_present": False,
        "embedded_toolpath_file_count": 0,
        "embedded_print_profile_present": False,
        "manual_support_and_brim_review_required": True,
        "scale_percent": 100.0,
        "material": "PETG only",
        "printer_candidate": "Bambu Lab A1 mini",
        "qualification_object_count": len(parts),
        "individual_stl_count": len(parts),
        "individual_neutral_3mf_count": len(parts),
        "combined_neutral_3mf_count": 1,
        "serialized_stl_individual_3mf_combined_bijection": True,
        "all_serialized_parts_watertight_one_body_positive": True,
        "all_candidate_orientations_fit_a1_mini": True,
        "saved_orientation_support_contracts_passed": True,
        "support_required_part_ids": [
            record["mesh_id"]
            for record in part_validation
            if record["saved_layer_support_evidence"] is not None
            and record["saved_layer_support_evidence"]["support_required"]
        ],
        "combined_catalog_is_single_a1_mini_plate": False,
        "combined_package": {
            "path": combined_relative,
            "object_names_in_order": list(expected_object_order),
            "readback_object_names_in_order": list(combined.objects),
            "object_order_readback_exact": True,
            "translations_mm": {
                name: list(translations[name]) for name, _mesh in ordered_meshes
            },
            "readback_translations_mm": {
                name: list(combined.translations_mm[name])
                for name in expected_object_order
            },
            "translations_readback_exact": True,
            "neutral_model_checks": combined.checks,
        },
        "parts": part_validation,
        "geometry_context": geometry_context,
        "clearance_v2_geometry_contract": clearance_contract,
        "retained_blank_v2_canonical_float32_triangle_digest": (
            retained_blank_digest
        ),
        "petg_a1_mini_candidate_settings": settings,
        "accessory_rail_layout": accessory_layout,
        "accessory_service_constraints": {
            "three_cable_comb_install_order": "bottom socket upward",
            "three_cable_comb_removal_order": "top socket downward",
            "reason": (
                "a moving comb conflicts with an occupied immediately-above "
                "socket; other retained module neighbor combinations clear"
            ),
        },
        "release_state": {
            "rated_load_kg": 0.0,
            "rated_load_lb": 0.0,
            "physical_qualification_complete": False,
            "installed_release_allowed": False,
            "production_ready": False,
            "load_rating_allowed": False,
            "wall_bores_emitted": False,
            "print_profile_released": False,
        },
        "unresolved_blockers": blockers,
        "artifact_config_identity": {
            "contract_id": production_plan.FROZEN_ARTIFACT_CONFIG_CONTRACT_ID,
            "algorithm": "sha256",
            "canonical_json_sha256": config_identity,
            "exact_match": True,
        },
        "runtime_provenance": runtime,
        "source_sha_bundle": sources_before,
    }
    model_io.write_bytes_exclusive(stage / "validation.json", _json_bytes(validation))

    expected_nonmanifest = {
        "README.md",
        "validation.json",
        combined_relative,
        *{record["stl_path"] for record in part_validation},
        *{record["individual_3mf_path"] for record in part_validation},
    }
    actual_nonmanifest = {
        path.relative_to(stage).as_posix()
        for path in stage.rglob("*")
        if path.is_file()
    }
    if actual_nonmanifest != expected_nonmanifest:
        raise ValueError(
            "Staged artifact set drifted: "
            f"missing={sorted(expected_nonmanifest - actual_nonmanifest)}, "
            f"extra={sorted(actual_nonmanifest - expected_nonmanifest)}"
        )
    artifact_records = [
        {
            "path": relative,
            "kind": _artifact_kind(relative),
            "bytes": (stage / relative).stat().st_size,
            "sha256": model_io.sha256_file(stage / relative),
        }
        for relative in sorted(expected_nonmanifest)
    ]
    digest_by_mesh = {
        record["mesh_id"]: record["serialized_geometry_digests"]["stl"]
        for record in part_validation
    }
    for artifact in artifact_records:
        relative = artifact["path"]
        for mesh_id, digest in digest_by_mesh.items():
            if relative.endswith(f"/{mesh_id}.stl") or relative.endswith(
                f"/MODEL_ONLY_{mesh_id}.3mf"
            ):
                artifact["mesh_id"] = mesh_id
                artifact["canonical_float32_triangle_digest"] = digest
                break

    manifest = {
        "schema_version": 1,
        "package_id": PACKAGE_ID,
        "manifest_filename": "manifest.json",
        "exact_file_allowlist": sorted({*expected_nonmanifest, "manifest.json"}),
        "hashed_artifacts_excluding_manifest": artifact_records,
        "artifact_count_excluding_manifest": len(artifact_records),
        "artifact_bytes_excluding_manifest": sum(
            int(record["bytes"]) for record in artifact_records
        ),
        "qualification_object_count": len(parts),
        "qualification_only": True,
        "unsliced": True,
        "generated_gcode_present": False,
        "embedded_toolpath_file_count": 0,
        "embedded_print_profile_present": False,
        "manual_support_and_brim_review_required": True,
        "scale_percent": 100.0,
        "material": "PETG only",
        "physical_qualification_complete": False,
        "installed_release_allowed": False,
        "production_ready": False,
        "load_rating_allowed": False,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
        "artifact_config_identity": validation["artifact_config_identity"],
        "runtime_provenance": runtime,
        "source_sha_bundle": sources_before,
        "petg_a1_mini_candidate_settings": settings,
        "accessory_rail_layout": accessory_layout,
        "accessory_service_constraints": {
            "three_cable_comb_install_order": "bottom socket upward",
            "three_cable_comb_removal_order": "top socket downward",
        },
        "unresolved_blockers": blockers,
        "saved_orientation_support_contracts_passed": True,
        "support_required_part_ids": [
            record["mesh_id"]
            for record in part_validation
            if record["saved_layer_support_evidence"] is not None
            and record["saved_layer_support_evidence"]["support_required"]
        ],
        "clearance_v2_geometry_contract": clearance_contract,
        "retained_blank_v2_canonical_float32_triangle_digest": (
            retained_blank_digest
        ),
        "combined_object_order_readback_exact": True,
        "combined_translations_readback_exact": True,
        "geometry_digests_by_mesh_id": digest_by_mesh,
        "validation_path": "validation.json",
        "combined_package_path": combined_relative,
    }
    model_io.write_bytes_exclusive(stage / "manifest.json", _json_bytes(manifest))
    actual_final = {
        path.relative_to(stage).as_posix()
        for path in stage.rglob("*")
        if path.is_file()
    }
    if actual_final != set(manifest["exact_file_allowlist"]):
        raise ValueError("Final bundle differs from the manifest exact allowlist")
    for record in manifest["hashed_artifacts_excluding_manifest"]:
        artifact = stage / record["path"]
        if artifact.stat().st_size != record["bytes"] or model_io.sha256_file(artifact) != record["sha256"]:
            raise ValueError(f"Manifest hash audit failed: {record['path']}")
    return manifest


def _is_within(candidate: Path, protected_root: Path) -> bool:
    try:
        candidate.relative_to(protected_root)
        return True
    except ValueError:
        return False


def _protected_roots() -> tuple[Path, ...]:
    return (
        (DEVELOPMENT_ROOT / "r6").resolve(strict=False),
        (DEVELOPMENT_ROOT / "r7").resolve(strict=False),
        (R8_ROOT / "generated" / "qualification_v1").resolve(strict=False),
    )


def _assert_output_allowed(destination: Path) -> None:
    for protected in _protected_roots():
        if _is_within(destination, protected):
            raise PermissionError(
                f"Refusing output inside protected baseline: {protected}"
            )


def build(output: Path) -> dict[str, Any]:
    """Generate, validate, and atomically publish into a fresh directory."""

    destination = Path(output).expanduser().resolve(strict=False)
    _assert_output_allowed(destination)
    if os.path.lexists(destination):
        raise FileExistsError(f"Refusing existing output directory: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.r8-stage-", dir=destination.parent)
    )
    try:
        manifest = _build_stage(stage)
        model_io.atomic_publish_directory(stage, destination)
        return manifest
    except BaseException:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Emit the unsliced R8 PETG qualification bundle."
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Fresh caller-supplied destination; existing paths are refused.",
    )
    args = parser.parse_args()
    manifest = build(args.output)
    print(
        "PASS: "
        f"{manifest['qualification_object_count']} exact R8 bodies, "
        f"{manifest['artifact_count_excluding_manifest']} hashed artifacts, "
        "unsliced and zero-rated"
    )


if __name__ == "__main__":
    main()
