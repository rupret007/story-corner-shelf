#!/usr/bin/env python3
"""Emit a deterministic, unsliced five-part R8 one-bay qualification bundle.

The caller must provide a fresh destination.  Artifacts are first written and
validated in a hidden sibling directory, then published with the atomic
no-replace primitive in :mod:`model_io`.  This generator has no default output
inside the repository and refuses R6, R7, and the existing R8 qualification-v1
trees.

The printable catalog is qualification-only PETG geometry.  It contains no
G-code, toolpath, printer profile, wall-fastener bore, load rating, or release
authorization.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Sequence

import numpy as np
import trimesh


R8_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = R8_ROOT.parents[1]
DEVELOPMENT_ROOT = R8_ROOT.parent
if str(R8_ROOT) not in sys.path:
    sys.path.insert(0, str(R8_ROOT))

import accessory_geometry as accessory  # noqa: E402
import assembly_geometry as assembly  # noqa: E402
import design_math  # noqa: E402
import generate_qualification as general_qualification  # noqa: E402
import interface_geometry as interface  # noqa: E402
import model_io  # noqa: E402
import production_plan  # noqa: E402
import shelf_geometry as shelf  # noqa: E402


PACKAGE_ID = "r8_16b_petg_one_bay_qualification_v2"
PACKAGE_FILENAME = "MODEL_ONLY_R8_ONE_BAY_QUALIFICATION_CATALOG.3mf"
MODEL_DESCRIPTION = (
    "UNSLICED R8 ONE-BAY QUALIFICATION-ONLY PETG MODELS; 100 PERCENT SCALE; "
    "ZERO RATED LOAD; NO PRINT PROFILE; PHYSICAL TESTING REQUIRED"
)
PART_GAP_MM = 10.0
COMBINED_CATALOG_ROW_WIDTH_MM = 520.0
EXPECTED_PART_IDS = (
    "r8_one_bay_registered_cassette",
    "r8_one_bay_left_rail_ready_locator_d_frame",
    "r8_one_bay_right_smooth_locator_seated_keeper_d_frame",
    "r8_one_bay_mounted_rail",
    "r8_one_bay_retained_blank",
)
SOURCE_PATHS = (
    "requirements.txt",
    "development/r8/config.json",
    "development/r8/FROZEN_BASELINES.json",
    "development/r8/design_math.py",
    "development/r8/shelf_geometry.py",
    "development/r8/accessory_geometry.py",
    "development/r8/interface_geometry.py",
    "development/r8/assembly_geometry.py",
    "development/r8/model_io.py",
    "development/r8/production_plan.py",
    "development/r8/generate_qualification.py",
    "development/r8/generate_one_bay_qualification.py",
)


@dataclass(frozen=True)
class QualificationPart:
    """One exact printable body in its saved print orientation."""

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
    """Reject material, anchor, and release drift before staging output."""

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
    if assembly.NOMINAL_PRINTED_PART_COUNT != len(EXPECTED_PART_IDS):
        raise ValueError("Assembly source no longer defines exactly five parts")
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
        f"{record['path']}\0{record['bytes']}\0{record['sha256']}\n".encode(
            "utf-8"
        )
        for record in records
    )
    return {
        "algorithm": "sha256",
        "records": records,
        "bundle_sha256": model_io.sha256_bytes(digest_payload),
    }


def _relabel_axes(
    mesh: trimesh.Trimesh, axes: tuple[int, int, int]
) -> trimesh.Trimesh:
    """Relabel axes, preserve outward winding, and normalize to positive XYZ."""

    if tuple(sorted(axes)) != (0, 1, 2):
        raise ValueError("Print-axis relabel must be an XYZ permutation")
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


def _qualification_parts(
    cfg: dict[str, Any],
) -> tuple[list[QualificationPart], assembly.OneBayAssembly]:
    seated = assembly.build_one_bay(keeper_state="seated")
    yaw = float(cfg["shelf"]["cassette_saved_orientation_candidate"]["bed_yaw_deg"])
    cassette_reserve = float(
        cfg["shelf"]["cassette_saved_orientation_candidate"][
            "edge_reserve_each_side_mm"
        ]
    )
    support_reserve = float(cfg["d_frame"]["saved_edge_reserve_each_side_mm"])
    parts = [
        QualificationPart(
            EXPECTED_PART_IDS[0],
            "Registered one-bay front-first U-box cassette",
            "visible front face down with frozen 45 degree bed yaw",
            shelf.orient_cassette_on_long_edge(
                seated.cassette.source_registered,
                yaw_degrees=yaw,
            ),
            cassette_reserve,
            expected_support_required=False,
        ),
        QualificationPart(
            EXPECTED_PART_IDS[1],
            "Left rail-ready locator D-frame",
            "broad run-side face down; installed Y/Z mapped to bed X/Y",
            assembly.orient_installed_support_for_print(seated.left_support.body),
            support_reserve,
            expected_support_required=False,
        ),
        QualificationPart(
            EXPECTED_PART_IDS[2],
            "Right smooth locator plus seated keeper D-frame",
            "broad run-side face down; installed Y/Z mapped to bed X/Y",
            assembly.orient_installed_support_for_print(seated.right_support.body),
            support_reserve,
            expected_support_required=False,
        ),
        QualificationPart(
            EXPECTED_PART_IDS[3],
            "Mounted three-station retention rail",
            "broad rear face down; installed X/Z mapped to bed X/Y",
            _relabel_axes(seated.mounted_rail, (0, 2, 1)),
            expected_support_required=False,
        ),
        QualificationPart(
            EXPECTED_PART_IDS[4],
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
    ]
    ids = tuple(part.mesh_id for part in parts)
    if ids != EXPECTED_PART_IDS or len(set(ids)) != 5:
        raise AssertionError("One-bay inventory must be exactly five ordered bodies")
    return parts, seated


def _candidate_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    settings = dict(general_qualification._candidate_settings(cfg))
    settings["status"] = "candidate values for manual Bambu Studio entry and review"
    return settings


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
) -> tuple[dict[str, tuple[float, float, float]], tuple[float, float, float]]:
    x = PART_GAP_MM
    y = PART_GAP_MM
    row_height = 0.0
    translations: dict[str, tuple[float, float, float]] = {}
    placed: list[tuple[str, float, float, float, float, float]] = []
    for name, mesh in meshes:
        evidence = model_io.serialized_mesh_evidence(mesh)
        width, depth, height = (float(value) for value in evidence["extents_mm"])
        if x > PART_GAP_MM and x + width > COMBINED_CATALOG_ROW_WIDTH_MM:
            x = PART_GAP_MM
            y += row_height + PART_GAP_MM
            row_height = 0.0
        translations[name] = (round(x, 6), round(y, 6), 0.0)
        placed.append((name, x, x + width, y, y + depth, height))
        x += width + PART_GAP_MM
        row_height = max(row_height, depth)
    for index, left in enumerate(placed):
        for right in placed[index + 1 :]:
            overlap_x = min(left[2], right[2]) - max(left[1], right[1])
            overlap_y = min(left[4], right[4]) - max(left[3], right[3])
            if (
                overlap_x > -PART_GAP_MM + 1.0e-6
                and overlap_y > -PART_GAP_MM + 1.0e-6
            ):
                raise ValueError(
                    f"Combined catalog spacing drifted: {left[0]} / {right[0]}"
                )
    maximum_x = max(record[2] for record in placed)
    maximum_y = max(record[4] for record in placed)
    maximum_z = max(record[5] for record in placed)
    extent = (
        round(maximum_x + PART_GAP_MM, 6),
        round(maximum_y + PART_GAP_MM, 6),
        round(maximum_z, 6),
    )
    return translations, extent


def _overlap_mm3(first: trimesh.Trimesh, second: trimesh.Trimesh) -> float:
    return round(assembly.positive_overlap_volume(first, second), 9)


def _service_sweep(
    moving: trimesh.Trimesh,
    phases: Sequence[tuple[str, tuple[np.ndarray, ...]]],
    fixed: Sequence[tuple[str, trimesh.Trimesh]],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    all_clear = True
    for phase_name, matrices in phases:
        maximum = 0.0
        maximum_at: dict[str, Any] | None = None
        for station_index, matrix in enumerate(matrices):
            positioned = assembly.transformed(moving, matrix)
            for target_name, target in fixed:
                overlap = _overlap_mm3(positioned, target)
                if overlap > maximum:
                    maximum = overlap
                    maximum_at = {
                        "station_index": station_index,
                        "target": target_name,
                    }
        clear = maximum <= assembly.COLLISION_TOLERANCE_MM3
        all_clear &= clear
        records.append(
            {
                "phase": phase_name,
                "station_count": len(matrices),
                "maximum_positive_overlap_mm3": maximum,
                "maximum_at": maximum_at,
                "clear_within_numeric_tolerance": clear,
            }
        )
    return {"phases": records, "all_phases_clear": all_clear}


def _installed_scene_evidence(
    seated: assembly.OneBayAssembly,
) -> dict[str, Any]:
    """Recompute Boolean, contact, and service evidence from assembly source."""

    released = assembly.build_one_bay(keeper_state="deflected")
    nominal_parts = (
        ("registered_cassette", seated.cassette.installed),
        ("left_rail_ready_support", seated.left_support.body),
        ("right_keeper_support", seated.right_support.body),
        ("mounted_rail", seated.mounted_rail),
        ("retained_blank", seated.seated_retained_blank),
    )
    pairwise: list[dict[str, Any]] = []
    nominal_clear = True
    for index, (left_name, left_mesh) in enumerate(nominal_parts):
        for right_name, right_mesh in nominal_parts[index + 1 :]:
            overlap = _overlap_mm3(left_mesh, right_mesh)
            clear = overlap <= assembly.COLLISION_TOLERANCE_MM3
            nominal_clear &= clear
            pairwise.append(
                {
                    "first": left_name,
                    "second": right_name,
                    "positive_overlap_mm3": overlap,
                    "clear_within_numeric_tolerance": clear,
                }
            )

    frozen_core_digest = accessory.mesh_geometry_digest(
        shelf.build_d_frame_corbel()
    )
    core_records: list[dict[str, Any]] = []
    cores_preserved = True
    for support in (seated.left_support, seated.right_support):
        restored = assembly.transformed(
            support.installed_core,
            np.linalg.inv(support.source_to_installed),
        )
        source_digest = accessory.mesh_geometry_digest(support.source_core)
        restored_digest = accessory.mesh_geometry_digest(restored)
        retained = _overlap_mm3(support.installed_core, support.body)
        preserved = bool(
            source_digest == frozen_core_digest
            and restored_digest == frozen_core_digest
            and abs(retained - float(support.installed_core.volume)) <= 0.05
            and float(support.body.volume) > float(support.installed_core.volume)
        )
        cores_preserved &= preserved
        core_records.append(
            {
                "side": support.side,
                "source_core_digest": source_digest,
                "restored_core_digest": restored_digest,
                "frozen_core_digest": frozen_core_digest,
                "installed_core_volume_mm3": round(
                    float(support.installed_core.volume), 6
                ),
                "body_volume_mm3": round(float(support.body.volume), 6),
                "core_retained_overlap_mm3": retained,
                "rail_mount_boss_count": len(support.rail_mount_bosses),
                "core_preserved_additions_only": preserved,
            }
        )

    registration_axes: list[dict[str, Any]] = []
    registration_passed = True
    supports = (seated.left_support.body, seated.right_support.body)
    for axis in ("x", "y"):
        at_clearance = assembly.transformed(
            seated.cassette.installed,
            assembly.translation(**{axis: assembly.REGISTRATION_CLEARANCE_PER_FACE_MM}),
        )
        blocked = assembly.transformed(
            seated.cassette.installed,
            assembly.translation(
                **{axis: 2.0 * assembly.REGISTRATION_CLEARANCE_PER_FACE_MM}
            ),
        )
        clearance_overlap = round(
            sum(_overlap_mm3(at_clearance, support) for support in supports),
            9,
        )
        blocked_overlap = round(
            sum(_overlap_mm3(blocked, support) for support in supports),
            9,
        )
        passed = bool(
            clearance_overlap <= assembly.COLLISION_TOLERANCE_MM3
            and blocked_overlap > 1.0
        )
        registration_passed &= passed
        registration_axes.append(
            {
                "axis": axis,
                "accepted_offset_mm": assembly.REGISTRATION_CLEARANCE_PER_FACE_MM,
                "accepted_positive_overlap_mm3": clearance_overlap,
                "rejected_offset_mm": (
                    2.0 * assembly.REGISTRATION_CLEARANCE_PER_FACE_MM
                ),
                "rejected_positive_overlap_mm3": blocked_overlap,
                "fail_closed": passed,
            }
        )

    contact_lifted = assembly.transformed(
        seated.cassette.installed,
        assembly.translation(z=assembly.KEEPER_CONTACT_LIFT_MM),
    )
    blocked_lifted = assembly.transformed(
        seated.cassette.installed,
        assembly.translation(z=assembly.KEEPER_BLOCKING_LIFT_MM),
    )
    keeper_contact_overlap = _overlap_mm3(
        contact_lifted, seated.right_support.body
    )
    keeper_blocked_overlap = _overlap_mm3(
        blocked_lifted, seated.right_support.body
    )
    keeper_passed = bool(
        keeper_contact_overlap <= assembly.COLLISION_TOLERANCE_MM3
        and keeper_blocked_overlap > 1.0
    )

    cassette_service = assembly.service_transforms()
    cassette_sweep = _service_sweep(
        released.cassette.installed,
        (
            ("installation_with_keeper_deflected", cassette_service.installation),
            ("removal_with_keeper_deflected", cassette_service.removal),
        ),
        (
            ("left_support", released.left_support.body),
            ("right_deflected_keeper_support", released.right_support.body),
            ("mounted_rail", released.mounted_rail),
            ("retained_blank", released.seated_retained_blank),
        ),
    )
    cassette_sweep.update(
        {
            "increment_mm": cassette_service.increment_mm,
            "lift_mm": cassette_service.lift_mm,
        }
    )

    rail_service = assembly.rail_mount_service_transforms()
    rail_sweep = _service_sweep(
        interface.build_mounted_retention_rail(),
        (
            ("approach", rail_service.approach),
            ("drop", rail_service.drop),
            ("reverse_lift", rail_service.removal_lift),
            ("reverse_outward", rail_service.removal_outward),
        ),
        (
            ("registered_cassette", seated.cassette.installed),
            ("left_support", seated.left_support.body),
            ("right_support", seated.right_support.body),
        ),
    )
    unauthorized_rail = assembly.transformed(
        interface.build_mounted_retention_rail(),
        assembly.translation(y=0.8) @ rail_service.seated,
    )
    unauthorized_rail_overlap = _overlap_mm3(
        unauthorized_rail, seated.left_support.body
    )
    rail_sweep.update(
        {
            "increment_mm": rail_service.increment_mm,
            "module_removal_required_first": (
                assembly.RAIL_SERVICE_REQUIRES_MODULE_REMOVAL
            ),
            "unauthorized_pull_without_lift_overlap_mm3": (
                unauthorized_rail_overlap
            ),
            "unauthorized_pull_fail_closed": unauthorized_rail_overlap > 1.0,
        }
    )

    blank_service = assembly.blank_module_service_transforms()
    blank_sweep = _service_sweep(
        interface.build_retained_accessory("blank", latch_state="deflected"),
        (
            ("approach", blank_service.approach),
            ("drop", blank_service.drop),
            ("reverse_lift", blank_service.removal_lift),
            ("reverse_outward", blank_service.removal_outward),
        ),
        (
            ("mounted_rail", seated.mounted_rail),
            ("left_support", seated.left_support.body),
            ("right_support", seated.right_support.body),
            ("registered_cassette", seated.cassette.installed),
        ),
    )
    blank_sweep.update({"increment_mm": blank_service.increment_mm})

    contacts = [asdict(contact) for contact in seated.bearing_contacts]
    contacts_passed = bool(
        len(contacts) == 2
        and all(
            contact["cap_overlap_width_mm"] == assembly.CAP_BEARING_WIDTH_MM
            and contact["net_cap_contact_area_mm2"] > 0.0
            and contact["net_selected_land_contact_area_mm2"] > 0.0
            for contact in contacts
        )
    )
    strain = asdict(assembly.keeper_strain_proxy())
    all_passed = bool(
        nominal_clear
        and cores_preserved
        and registration_passed
        and keeper_passed
        and cassette_sweep["all_phases_clear"]
        and rail_sweep["all_phases_clear"]
        and rail_sweep["unauthorized_pull_fail_closed"]
        and blank_sweep["all_phases_clear"]
        and contacts_passed
        and strain["below_three_percent"]
    )
    evidence = {
        "evidence_source": "development/r8/assembly_geometry.py",
        "boolean_engine": "manifold",
        "collision_numeric_tolerance_mm3": assembly.COLLISION_TOLERANCE_MM3,
        "nominal_five_part_pairwise_boolean": {
            "pair_count": len(pairwise),
            "records": pairwise,
            "all_pairs_clear_within_numeric_tolerance": nominal_clear,
        },
        "bearing_contact_datums": contacts,
        "bearing_contacts_passed": contacts_passed,
        "structural_core_preservation": {
            "records": core_records,
            "all_cores_preserved_additions_only": cores_preserved,
            "registration_structural_credit": assembly.REGISTRATION_STRUCTURAL_CREDIT,
            "keeper_structural_credit": assembly.KEEPER_STRUCTURAL_CREDIT,
        },
        "registration_clearance_fail_closed": {
            "clearance_per_face_mm": assembly.REGISTRATION_CLEARANCE_PER_FACE_MM,
            "remaining_bottom_skin_mm": (
                assembly.REGISTRATION_REMAINING_BOTTOM_SKIN_MM
            ),
            "axes": registration_axes,
            "passed": registration_passed,
        },
        "keeper_retention": {
            "contact_lift_mm": assembly.KEEPER_CONTACT_LIFT_MM,
            "contact_positive_overlap_mm3": keeper_contact_overlap,
            "blocking_lift_mm": assembly.KEEPER_BLOCKING_LIFT_MM,
            "blocking_positive_overlap_mm3": keeper_blocked_overlap,
            "seated_blocks_and_deflected_service_clears": keeper_passed,
            "strain_proxy": strain,
        },
        "service_evidence": {
            "safe_order": {
                "installation": [
                    "hold right keeper deflected",
                    "lower registered cassette through full 2.0 mm clear approach",
                    "release keeper to seated state",
                    "mount empty rail through approach and 4.0 mm drop",
                    "install retained blank through entry, 8.0 mm drop, and latch",
                ],
                "removal": [
                    "release and remove retained blank",
                    "lift and remove empty rail",
                    "hold right keeper deflected",
                    "lift cassette 2.0 mm and remove",
                ],
            },
            "cassette": cassette_sweep,
            "rail": rail_sweep,
            "retained_blank": blank_sweep,
        },
        "all_installed_scene_evidence_passed": all_passed,
    }
    if not all_passed:
        raise ValueError("One-bay installed-scene qualification evidence failed")
    return evidence


def _physical_test_requirements() -> list[str]:
    return [
        "Prior 0.4 mm per-face receiver/key clearance coupon must pass.",
        "Record PETG lot, drying cycle, flow calibration, dimensions, and warp.",
        "Dry-fit both locator keys and verify full bearing without rocking.",
        "Cycle cassette installation/removal with the keeper deflected.",
        "Cycle seated keeper retention and inspect for whitening, cracks, or set.",
        "Cycle blank latch and empty-rail install/removal in the safe order.",
        "Run approved thermal, creep, proof-load, and destructive protocols later.",
        "Do not infer a shelf load rating from this one-bay fit qualification.",
    ]


def _bundle_readme(cfg: dict[str, Any]) -> bytes:
    settings = _candidate_settings(cfg)
    drying_low, drying_high = settings["drying_temperature_range_c"]
    drying_hours_low, drying_hours_high = settings["drying_duration_range_h"]
    fan_low, fan_high = settings["fan_percent_range"]
    return f"""# R8 one-bay PETG qualification bundle

This is an **unsliced, zero-rated, five-part fit qualification**, not an
installed shelf release. It contains exactly one registered cassette, one
left rail-ready locator D-frame, one right smooth locator/keeper D-frame, one
mounted rail, and one retained blank. It contains no G-code, toolpath, printer
profile, wall-fastener bores, or load rating.

The frozen filament identity is **{settings['filament_manufacturer']}
{settings['filament_product']} {settings['filament_color']}**, ASIN
`{settings['filament_asin']}`: [selected listing]({settings['filament_product_url']}).
Selected variant: `{settings['filament_selected_variant']}`. Confirm the received
spool label; the label and dryer limit control, and the lower stated temperature
limit must never be exceeded.

## Gate 0: qualify 0.4 mm first

Before printing this bundle, use the clearance ladder in the exact
`r8_16b_petg_qualification_v2` bundle and verify its receiver plus four key
digests against this package's `prior_clearance_qualification` record. Test
0.5, then **0.4 mm per face**. The one-bay
locator, rail, and blank interfaces are authored around 0.4 mm. If 0.4 mm
does not pass cleanly after cooling, stop and correct drying/flow/process;
never scale these parts to force a fit.

## Bambu Studio and PETG settings

1. Open a new `{settings['printer']} {settings['nozzle_mm']:g} nozzle` Textured
   PEI project. Import one
   individual neutral 3MF at **100% scale**. Do not auto-scale, auto-orient,
   repair, or merge it. The combined 3MF is a catalog, **not one build plate**;
   do not slice its layout as-is.
2. Select `{settings['filament_preset']}` and manually verify PETG only:
   {settings['layer_height_mm']:.2f} mm layers, {settings['wall_loops']} wall
   loops, {settings['top_shell_layers']} top and
   {settings['bottom_shell_layers']} bottom shell layers,
   {settings['infill_percent']}% {settings['infill_pattern']} infill,
   {settings['first_layer_nozzle_temperature_c']:g} C first layer,
   {settings['other_layer_nozzle_temperature_c']:g} C later layers,
   {settings['textured_pei_bed_temperature_c']:g} C bed,
   {settings['flow_ratio']:g} flow,
   {settings['maximum_volumetric_speed_mm3_s']:g} mm^3/s maximum volumetric
   speed, {fan_low:g}-{fan_high:g}% normal fan, and
   {settings['overhang_fan_percent']:g}% overhang fan.
   Never use a PLA preset.
3. The SUNLU standard-PETG baseline is {drying_low:g} C (validated lower/upper
   values: {drying_low:g} C / {drying_high:g} C) for
   {drying_hours_low:g}-{drying_hours_high:g} hours, conditional on the
   received spool label and dryer limit. Record spool lot, exact drying cycle,
   flow calibration, Studio version, plate, and every manual setting. Source:
   {settings['drying_guidance_source_url']}
4. Preserve the saved orientations: cassette visible front down at 45 degrees;
   both D-frames broad face down; rail broad rear down; blank local XY on the
   bed with its common body down and local negative Z building upward.
5. All five exact saved meshes pass the deposited-layer support gate; the blank
   begins on at least 64 mm^2 of common-body contact. Start with Support OFF and
   inspect Preview. If Studio shows a new island, changes orientation, or wants
   support on cap-bearing, locator, keeper, rail, or latch contact geometry,
   stop and record the mismatch instead of accepting an automatic repair.
6. Start with a {settings['brim_mm']:.1f} mm outer brim and
   {settings['brim_object_gap_mm']:.1f} mm brim-object gap, then inspect the
   preview for plate-edge, exclusion-zone, support, and brim conflicts. The
   cassette and D-frames reserve an additional
   {cfg['d_frame']['saved_edge_reserve_each_side_mm']:g} mm per bed edge. Do not reduce
   the reserve or scale a part to make a warning disappear.

## Safe service order

Install: hold the right keeper deflected; lower the cassette through its full
2.0 mm clear approach; seat it; release the keeper; mount the **empty** rail
through its approach and 4.0 mm drop; then install the blank through its entry,
8.0 mm drop, and front-release latch.

Remove in reverse: release/lift/remove the blank first; lift/remove the empty
rail second; hold the keeper deflected; then lift the cassette 2.0 mm and
remove it. Never pull the rail outward while it is loaded or before its service
lift. Never force the cassette past a seated keeper.

## Required one-bay physical tests

- Inspect all five cooled PETG parts for warp, layer separation, poor support
  interfaces, cracks, whitening, and dimension drift.
- Verify both locator fits, full end-land/cap bearing, no rocking, 0.35 mm seam
  intent, keeper contact, and non-destructive release.
- Cycle cassette installation/removal, keeper release/retention, blank latch,
  and empty-rail service in the safe order; record cycle count and damage.
- Stop on binding, permanent set, cracking, whitening, lost latch engagement,
  or bearing gaps. Do not sand load/contact features into an unrecorded fit.
- Thermal, creep, proof-load, and destructive protocols remain separate future
  gates. This coupon cannot establish an installed shelf load rating.

All printed parts are PETG. Any later wall installation still requires verified
framing/blocking and an approved metal structural screw/washer schedule. Printed
or hollow-wall anchors are not authorized in the primary load path.
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
    raise ValueError(f"Unclassified one-bay artifact: {relative}")


def _build_stage(stage: Path) -> dict[str, Any]:
    cfg = _load_config()
    config_identity = production_plan.validate_artifact_coupled_config_identity(cfg)
    runtime = general_qualification.runtime_provenance()
    clearance_contract = general_qualification.clearance_v2_geometry_contract()
    sources_before = _source_bundle()
    parts, seated = _qualification_parts(cfg)
    installed_scene = _installed_scene_evidence(seated)
    settings = _candidate_settings(cfg)
    blockers = list(design_math.production_blockers(cfg))
    if not blockers:
        raise ValueError("One-bay bundle unexpectedly has no release blockers")

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
            raise ValueError(f"{part.mesh_id}: failed body or A1-mini envelope audit")

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
            raise ValueError(f"{part.mesh_id}: STL/individual 3MF bijection failed")
        if individual.translations_mm != {part.mesh_id: (0.0, 0.0, 0.0)}:
            raise ValueError(f"{part.mesh_id}: individual 3MF changed placement")
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

    retained_blank_digest = general_qualification.retained_blank_v2_geometry_digest()
    one_bay_blank_digest = model_io.canonical_triangle_digest(
        serialized_by_name[EXPECTED_PART_IDS[4]]
    )
    if one_bay_blank_digest != retained_blank_digest:
        raise ValueError("One-bay printable blank differs from the general v2 blank")
    installed_blank = model_io.canonicalize_mesh(seated.seated_retained_blank)
    installed_blank_digest = model_io.canonical_triangle_digest(installed_blank)

    ordered_meshes = [
        (part.mesh_id, serialized_by_name[part.mesh_id]) for part in parts
    ]
    translations, catalog_extent = _combined_translations(ordered_meshes)
    combined_relative = f"model_only_3mf/{PACKAGE_FILENAME}"
    combined_path = stage / combined_relative
    model_io.write_model_only_3mf(
        combined_path,
        "Story Corner R8 one-bay five-part qualification catalog",
        MODEL_DESCRIPTION,
        [
            model_io.ModelObject(name, mesh, translations[name])
            for name, mesh in ordered_meshes
        ],
    )
    combined = model_io.inspect_model_only_3mf(combined_path)
    if tuple(combined.objects) != EXPECTED_PART_IDS:
        raise ValueError("Combined one-bay object order or set drifted")
    if combined.translations_mm != translations:
        raise ValueError("Combined one-bay translations changed on readback")
    for record in part_validation:
        name = record["mesh_id"]
        digest = model_io.canonical_triangle_digest(combined.objects[name])
        record["serialized_geometry_digests"]["combined_3mf"] = digest
        if len(set(record["serialized_geometry_digests"].values())) != 1:
            raise ValueError(f"{name}: combined catalog geometry is not bijective")

    model_io.write_bytes_exclusive(stage / "README.md", _bundle_readme(cfg))
    sources_after = _source_bundle()
    if sources_before != sources_after:
        raise RuntimeError("R8 source SHA bundle changed during one-bay generation")

    validation = {
        "schema_version": 1,
        "package_id": PACKAGE_ID,
        "validation_passed": True,
        "qualification_only": True,
        "unsliced": True,
        "generated_gcode_present": False,
        "embedded_toolpath_file_count": 0,
        "embedded_print_profile_present": False,
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
        "support_required_part_ids": [],
        "combined_catalog_is_single_a1_mini_plate": False,
        "combined_package": {
            "path": combined_relative,
            "object_names_in_order": list(EXPECTED_PART_IDS),
            "readback_object_names_in_order": list(combined.objects),
            "object_order_readback_exact": True,
            "translations_mm": {
                name: list(translations[name]) for name, _mesh in ordered_meshes
            },
            "readback_translations_mm": {
                name: list(combined.translations_mm[name])
                for name in EXPECTED_PART_IDS
            },
            "translations_readback_exact": True,
            "catalog_extent_mm": list(catalog_extent),
            "single_plate_claim": False,
            "neutral_model_checks": combined.checks,
        },
        "parts": part_validation,
        "installed_scene_evidence": installed_scene,
        "prior_clearance_qualification": {
            "required": True,
            "required_clearance_per_face_mm": 0.4,
            "coupon_included_in_this_bundle": False,
            "source_package_id": general_qualification.PACKAGE_ID,
            "source_contract_without_checked_output_dependency": True,
            "clearance_v2_geometry_contract": clearance_contract,
        },
        "retained_blank_cross_bundle_contract": {
            "general_v2_package_id": general_qualification.PACKAGE_ID,
            "general_v2_canonical_float32_triangle_digest": retained_blank_digest,
            "one_bay_printable_canonical_float32_triangle_digest": one_bay_blank_digest,
            "exact_match": True,
            "installed_scene_copy_canonical_float32_triangle_digest": (
                installed_blank_digest
            ),
            "installed_scene_copy_used_only_for_scene_evidence": True,
        },
        "petg_a1_mini_candidate_settings": settings,
        "manual_support_and_brim_review_required": True,
        "physical_test_requirements": _physical_test_requirements(),
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
    model_io.write_bytes_exclusive(
        stage / "validation.json", _json_bytes(validation)
    )

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
            "Staged one-bay artifact set drifted: "
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
        "combined_catalog_is_single_a1_mini_plate": False,
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
        "prior_clearance_qualification_required_mm_per_face": 0.4,
        "prior_clearance_v2_geometry_contract": clearance_contract,
        "retained_blank_cross_bundle_contract": validation[
            "retained_blank_cross_bundle_contract"
        ],
        "manual_support_and_brim_review_required": True,
        "saved_orientation_support_contracts_passed": True,
        "support_required_part_ids": [],
        "combined_object_order_readback_exact": True,
        "combined_translations_readback_exact": True,
        "unresolved_blockers": blockers,
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
        raise ValueError("Final one-bay bundle differs from its exact allowlist")
    for record in manifest["hashed_artifacts_excluding_manifest"]:
        artifact = stage / record["path"]
        if (
            artifact.stat().st_size != record["bytes"]
            or model_io.sha256_file(artifact) != record["sha256"]
        ):
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
        tempfile.mkdtemp(
            prefix=f".{destination.name}.r8-one-bay-stage-",
            dir=destination.parent,
        )
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
        description="Emit the unsliced R8 five-part one-bay PETG qualification bundle."
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Fresh caller-supplied destination; existing and protected paths refused.",
    )
    args = parser.parse_args()
    manifest = build(args.output)
    print(
        "PASS: "
        f"{manifest['qualification_object_count']} exact one-bay PETG bodies, "
        f"{manifest['artifact_count_excluding_manifest']} hashed artifacts, "
        "unsliced, profile-free, and zero-rated"
    )


if __name__ == "__main__":
    main()
