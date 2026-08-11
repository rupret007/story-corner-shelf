#!/usr/bin/env python3
"""Build the deterministic, unsliced R9 PETG qualification bundle.

This generator publishes fit and form studies only.  It cannot emit slicer
profiles, G-code, wall bores, a full shelf set, an installed release, or a load
rating.  The destination must be new; publication is atomic and no-replace.
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

import trimesh


R9_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = R9_ROOT.parents[1]
if str(R9_ROOT) not in sys.path:
    sys.path.insert(0, str(R9_ROOT))

import cable_geometry as cable  # noqa: E402
import bookend_attachment as attachment  # noqa: E402
import design_math  # noqa: E402
import fixture_assembly as fixtures  # noqa: E402
import gate0_geometry as gate0  # noqa: E402
import model_io  # noqa: E402
import support_geometry as support  # noqa: E402


PACKAGE_ID = "r9_compact_bookend_petg_qualification_v5"
COMBINED_FILENAME = "MODEL_ONLY_R9_QUALIFICATION_CATALOG.3mf"
MODEL_DESCRIPTION = (
    "UNSLICED R9 QUALIFICATION-ONLY BLACK PETG MODEL; 100 PERCENT SCALE; "
    "ZERO RATED LOAD; NO WALL BORES; NO FULL SHELF SET"
)
EXPECTED_CONFIG_CANONICAL_SHA256 = (
    "37c46e68bc479a1af1fd2b075f6f54abe573cc26bf74efcc25415445d8ced079"
)
PART_GAP_MM = 10.0
CATALOG_ROW_WIDTH_MM = 520.0
RUNTIME_REQUIREMENTS = (
    ("numpy", "2.5.1"),
    ("shapely", "2.1.2"),
    ("trimesh", "5.0.0"),
    ("manifold3d", "3.5.2"),
    ("mapbox-earcut", "1.0.3"),
    ("scipy", "1.18.0"),
    ("networkx", "3.5"),
)
SOURCE_PATHS = (
    "requirements.txt",
    "development/r8/model_io.py",
    "development/r8/generated/qualification_v2/manifest.json",
    "development/r8/generated/qualification_v2/validation.json",
    "development/r8/generated/qualification_v2/stl/r8_clearance_ladder_receiver.stl",
    "development/r8/generated/qualification_v2/stl/r8_clearance_key_0p4.stl",
    "development/r9/config.json",
    "development/r9/FROZEN_BASELINES.json",
    "development/r9/design_math.py",
    "development/r9/model_io.py",
    "development/r9/support_geometry.py",
    "development/r9/cable_geometry.py",
    "development/r9/bookend_attachment.py",
    "development/r9/fixture_assembly.py",
    "development/r9/gate0_geometry.py",
    "development/r9/generate_qualification.py",
    "development/r9/README.md",
    "development/r9/docs/PRINTER_KICKOFF.md",
    "development/r9/docs/PRINT_FIRST.md",
    "development/r9/docs/ASSEMBLY.md",
    "development/r9/docs/MEASUREMENT_WORKSHEET.md",
    "development/r9/docs/TEST_PROTOCOL.md",
)
R8_GATE0_IDS = (
    "r8_clearance_ladder_receiver",
    "r8_clearance_key_0p5",
    "r8_clearance_key_0p4",
    "r8_clearance_key_0p3",
    "r8_clearance_key_0p2",
)
R8_CONTROL_ID = "r8_smooth_curved_core"
STAGE0_RECEIVER_ID = "r8_clearance_ladder_receiver"
STAGE0_KEY_ID = "r9_gate0_clearance_key_0p4_handle_down"


@dataclass(frozen=True)
class QualificationPart:
    mesh_id: str
    label: str
    category: str
    print_orientation: str
    support_required: bool
    support_evidence: str
    envelope: dict[str, Any]
    mesh: trimesh.Trimesh


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def _strict_json(path: Path) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_constant,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def _canonical_json_sha256(payload: dict[str, Any]) -> str:
    encoded = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")
    return model_io.sha256_bytes(encoded)


def _load_frozen_config() -> dict[str, Any]:
    payload = design_math.load_config()
    design_math.validate_config(payload)
    identity = _canonical_json_sha256(payload)
    if identity != EXPECTED_CONFIG_CANONICAL_SHA256:
        raise ValueError(
            "R9 artifact config identity drifted: "
            f"expected {EXPECTED_CONFIG_CANONICAL_SHA256}, observed {identity}"
        )
    design_math.validate_bound_files(payload)
    design_math.validate_frozen_baselines()
    return payload


def _source_bundle() -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for relative in SOURCE_PATHS:
        path = REPOSITORY_ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing or unsafe R9 source dependency: {relative}")
        records.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": model_io.sha256_file(path),
            }
        )
    digest_payload = b"".join(
        (
            f"{record['path']}\0{record['bytes']}\0{record['sha256']}\n"
        ).encode("utf-8")
        for record in records
    )
    return {
        "algorithm": "sha256",
        "records": records,
        "bundle_sha256": model_io.sha256_bytes(digest_payload),
    }


def runtime_provenance() -> dict[str, Any]:
    requirements = REPOSITORY_ROOT / "requirements.txt"
    declared = tuple(
        line.strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    expected = tuple(f"{name}=={version}" for name, version in RUNTIME_REQUIREMENTS)
    if declared != expected:
        raise ValueError("requirements.txt no longer matches the R9 pinned runtime")
    distributions: list[dict[str, Any]] = []
    for name, required in RUNTIME_REQUIREMENTS:
        try:
            observed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError(f"missing required distribution: {name}") from error
        if observed != required:
            raise RuntimeError(
                f"runtime drift for {name}: required {required}, observed {observed}"
            )
        distributions.append(
            {
                "distribution": name,
                "required_version": required,
                "observed_version": observed,
                "exact_match": True,
            }
        )
    if (
        model_io.sha256_file(R9_ROOT.parent / "r8" / "model_io.py")
        != model_io.EXPECTED_R8_MODEL_IO_SHA256
    ):
        raise RuntimeError("frozen R8 neutral writer changed after R9 import")
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "requirements_path": "requirements.txt",
        "requirements_sha256": model_io.sha256_file(requirements),
        "requirements_exactly_matched": True,
        "distributions": distributions,
        "mesh_serialization": "canonical float32 triangles",
        "boolean_engine": "manifold",
        "frozen_r8_model_writer_sha256": model_io.EXPECTED_R8_MODEL_IO_SHA256,
        "neutral_model_only": True,
    }


def _r8_dependency() -> dict[str, Any]:
    root = R9_ROOT.parent / "r8" / "generated" / "qualification_v2"
    manifest_path = root / "manifest.json"
    validation_path = root / "validation.json"
    cfg = design_math.load_config()
    expected_manifest = cfg["predecessor_evidence"]["r8_component_v2_manifest"][
        "sha256"
    ]
    if model_io.sha256_file(manifest_path) != expected_manifest:
        raise ValueError("R8 qualification-v2 manifest dependency changed")
    manifest = _strict_json(manifest_path)
    validation = _strict_json(validation_path)
    records = {
        record["mesh_id"]: record
        for record in manifest["hashed_artifacts_excluding_manifest"]
        if record.get("kind") == "individual_neutral_model_only_3mf"
    }
    geometry = manifest["geometry_digests_by_mesh_id"]
    if validation.get("package_id") != manifest.get("package_id"):
        raise ValueError("R8 dependency manifest/validation package IDs disagree")
    selected: list[dict[str, Any]] = []
    for mesh_id in (*R8_GATE0_IDS, R8_CONTROL_ID):
        record = records.get(mesh_id)
        if record is None:
            raise ValueError(f"R8 dependency mesh is missing: {mesh_id}")
        path = root / record["path"]
        if path.stat().st_size != record["bytes"]:
            raise ValueError(f"R8 dependency byte count changed: {mesh_id}")
        if model_io.sha256_file(path) != record["sha256"]:
            raise ValueError(f"R8 dependency file changed: {mesh_id}")
        if record["canonical_float32_triangle_digest"] != geometry[mesh_id]:
            raise ValueError(f"R8 dependency geometry digest disagrees: {mesh_id}")
        selected.append(
            {
                "mesh_id": mesh_id,
                "path_from_r9_bundle": "../../../r8/generated/qualification_v2/"
                + record["path"],
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "canonical_float32_triangle_digest": geometry[mesh_id],
            }
        )
    return {
        "package_id": manifest["package_id"],
        "manifest_path_from_r9_bundle": (
            "../../../r8/generated/qualification_v2/manifest.json"
        ),
        "manifest_sha256": expected_manifest,
        "gate0_print_order_mesh_ids": list(R8_GATE0_IDS),
        "matched_control_mesh_id": R8_CONTROL_ID,
        "records": selected,
    }


def _envelope_dict(envelope: Any) -> dict[str, Any]:
    result = asdict(envelope)
    for key in (
        "raw_part_mm",
        "required_build_volume_mm",
        "available_build_volume_mm",
    ):
        result[key] = [round(float(value), 6) for value in result[key]]
    return result


def _qualification_parts() -> list[QualificationPart]:
    labels = {
        "r9_shortened_outer_bookend_support": "Smooth shortened outer bookend core control",
        "r9_compact_support": "Smooth compact intermediate support candidate",
        "r9_concealed_corner_half_control": "Untrimmed hidden-corner half control",
        "r9_through_hidden_corner_half": "Through-wall handed hidden-corner half",
        "r9_return_hidden_corner_half": "Return-wall handed hidden-corner half",
        "r9_under_shelf_shear_key_coupon": "Non-rated under-shelf corner key coupon",
        "r9_cosmetic_corner_cover_coupon": "Cosmetic corner-cover reveal coupon",
        "r9_90_degree_tabletop_angle_fixture": "Nominal 90-degree tabletop reference",
        "r9_rear_ledger_male_coupon": "Rear-ledger male fit coupon",
        "r9_rear_ledger_female_coupon": "Rear-ledger female fit coupon",
        "r9_front_beam_lower_lap_coupon": "Front-beam lower-lap fit coupon",
        "r9_front_beam_upper_lap_coupon": "Front-beam upper-lap fit coupon",
        "r9_two_socket_outer_bookend_rail_fit_coupon": "Two-socket cable-rail interface coupon",
        "r9_flush_blank_cable_module": "Flush cable-rail blank module",
        "r9_multi_cable_comb_hook_module": "Three-position cable comb/hook module",
        "r9_through_outer_bookend_additive_two_socket_candidate": (
            "Through-run handed shortened bookend with integral two-socket receiver"
        ),
        "r9_return_outer_bookend_additive_two_socket_candidate": (
            "Return-run handed shortened bookend with integral two-socket receiver"
        ),
    }
    categories = {
        name: "support_corner_or_span_joint"
        for name in support.build_saved_qualification_parts()
    }
    categories.update(
        {name: "cable_interface" for name in cable.build_saved_cable_qualification_parts()}
    )
    categories.update(
        {
            name: "integral_bookend_receiver"
            for name in attachment.build_saved_attachment_candidates()
        }
    )
    support_meshes = support.build_saved_qualification_parts()
    support_evidence = {
        item.part_name: item for item in support.saved_print_orientation_evidence()
    }
    cable_meshes = cable.build_saved_cable_qualification_parts()
    cable_evidence = {
        item.part_name: item for item in cable.saved_cable_print_evidence()
    }
    attachment_meshes = attachment.build_saved_attachment_candidates()
    attachment_evidence = {
        item.part_name: item for item in attachment.saved_attachment_print_evidence()
    }
    parts: list[QualificationPart] = []
    for name, mesh in (
        *support_meshes.items(),
        *cable_meshes.items(),
        *attachment_meshes.items(),
    ):
        evidence = (
            support_evidence.get(name)
            or cable_evidence.get(name)
            or attachment_evidence.get(name)
        )
        if evidence is None:
            raise AssertionError(f"missing print evidence: {name}")
        if hasattr(evidence, "analytic_layer_rule"):
            support_rule = evidence.analytic_layer_rule
        elif hasattr(evidence, "support_evidence"):
            support_rule = evidence.support_evidence
        else:
            support_rule = (
                "every saved layer is connected; additive broad-face print foot "
                "provides the first-layer support field"
            )
        parts.append(
            QualificationPart(
                mesh_id=name,
                label=labels[name],
                category=categories[name],
                print_orientation=evidence.orientation_id,
                support_required=bool(evidence.support_required),
                support_evidence=str(support_rule),
                envelope=_envelope_dict(evidence.envelope),
                mesh=mesh,
            )
        )
    if len(parts) != 17 or len({part.mesh_id for part in parts}) != 17:
        raise AssertionError("R9 qualification inventory must contain 17 parts")
    return parts


def _stage0_parts() -> list[QualificationPart]:
    labels = {
        STAGE0_RECEIVER_ID: "R8 geometry-identical four-station clearance receiver",
        STAGE0_KEY_ID: "R9 corrected-pose 0.4 mm-per-face clearance key",
    }
    meshes = gate0.build_saved_gate0_parts()
    evidence = {
        item.part_name: item for item in gate0.saved_gate0_print_evidence()
    }
    parts: list[QualificationPart] = []
    for mesh_id, mesh in meshes.items():
        item = evidence[mesh_id]
        parts.append(
            QualificationPart(
                mesh_id=mesh_id,
                label=labels[mesh_id],
                category="gate0_process_and_fit_control",
                print_orientation=item.orientation_id,
                support_required=item.support_required,
                support_evidence=item.support_evidence,
                envelope=_envelope_dict(item.envelope),
                mesh=mesh,
            )
        )
    if tuple(part.mesh_id for part in parts) != (
        STAGE0_RECEIVER_ID,
        STAGE0_KEY_ID,
    ):
        raise AssertionError("R9 Gate-0 inventory changed")
    return parts


def _candidate_settings(cfg: dict[str, Any]) -> dict[str, Any]:
    printer = cfg["printer"]
    return {
        "status": "manual candidate values; neutral files contain no profile",
        "embedded_print_profile_present": False,
        "manual_support_and_brim_review_required": True,
        "scale_percent": 100.0,
        "printer": f"{printer['manufacturer']} {printer['model']}",
        "machine_preset": printer["machine_preset"],
        "plate_type": printer["plate_type"],
        "process_preset": printer["process_preset"],
        "build_volume_mm": printer["printable_volume_mm"],
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
        "drying_temperature_c": printer["drying_temperature_c"],
        "drying_duration_range_h": printer["drying_duration_range_h"],
        "received_spool_and_dryer_lower_limit_controls": printer[
            "received_spool_and_dryer_lower_limit_controls"
        ],
        "brim_mm": printer["brim_mm"],
        "brim_object_gap_mm": printer["brim_object_gap_mm"],
        "edge_reserve_each_side_mm": printer["edge_reserve_each_side_mm"],
    }


def _catalog_translations(
    meshes: list[tuple[str, model_io.SerializedMesh]],
) -> dict[str, tuple[float, float, float]]:
    x = PART_GAP_MM
    y = PART_GAP_MM
    row_depth = 0.0
    result: dict[str, tuple[float, float, float]] = {}
    for name, mesh in meshes:
        evidence = model_io.serialized_mesh_evidence(mesh)
        width, depth, _height = (float(value) for value in evidence["extents_mm"])
        if x > PART_GAP_MM and x + width > CATALOG_ROW_WIDTH_MM:
            x = PART_GAP_MM
            y += row_depth + PART_GAP_MM
            row_depth = 0.0
        result[name] = (round(x, 6), round(y, 6), 0.0)
        x += width + PART_GAP_MM
        row_depth = max(row_depth, depth)
    return result


def _fixture_evidence() -> dict[str, Any]:
    ledger, beam, corner, one_bay = fixtures.build_all_fixture_evidence()
    return {
        "rear_ledger_joint": asdict(ledger),
        "front_beam_joint": asdict(beam),
        "nominal_90_degree_corner": asdict(corner),
        "compact_one_bay": asdict(one_bay),
    }


def _bundle_readme(
    cfg: dict[str, Any],
    parts: list[QualificationPart],
    r8_dependency: dict[str, Any],
) -> str:
    settings = _candidate_settings(cfg)
    support_off = [part.mesh_id for part in parts if not part.support_required]
    support_on = [part.mesh_id for part in parts if part.support_required]
    lines = [
        "# R9 compact-bookend PETG qualification v5",
        "",
        "**QUALIFICATION ARTICLES ONLY — RATED LOAD 0 KG / 0 LB.**",
        "",
        "This directory does not contain a full shelf set, wall bores, G-code,",
        "or an installed release. The combined 3MF is an off-plate catalog, not",
        "a print plate. Open individual 3MF files one at a time at 100% scale.",
        "",
        "## Enter these settings manually in Bambu Studio",
        "",
        f"- Machine: `{settings['machine_preset']}`.",
        f"- Plate: `{settings['plate_type']}`.",
        f"- Filament: `{settings['filament_preset']}`; SUNLU black PETG, ASIN "
        f"`{settings['filament_asin']}`.",
        "  If that exact preset is absent, duplicate Generic PETG, enter every",
        "  value below, save it under the exact SUNLU preset name, and recheck it.",
        f"- Process starting point: `{settings['process_preset']}`.",
        f"- {settings['layer_height_mm']:.2f} mm layer, {settings['wall_loops']} walls, "
        f"{settings['top_shell_layers']} top / {settings['bottom_shell_layers']} bottom, "
        f"{settings['infill_percent']}% {settings['infill_pattern']} infill.",
        f"- Nozzle {settings['first_layer_nozzle_temperature_c']:.0f} C first / "
        f"{settings['other_layer_nozzle_temperature_c']:.0f} C other; Textured PEI "
        f"{settings['textured_pei_bed_temperature_c']:.0f} C.",
        f"- Flow {settings['flow_ratio']}; max volumetric speed "
        f"{settings['maximum_volumetric_speed_mm3_s']} mm3/s.",
        f"- Outer brim {settings['brim_mm']:.1f} mm, object gap "
        f"{settings['brim_object_gap_mm']:.1f} mm; keep at least "
        f"{settings['edge_reserve_each_side_mm']:.1f} mm extra plate reserve.",
        "- Dry at 50 C for 6–8 h only if the received spool and dryer permit it;",
        "  never exceed the lower stated limit. Record spool lot, drying, and flow",
        "  calibration. Do not reuse a PLA profile.",
        "- Never Auto-orient, scale, repair, or arrange. Inspect Preview before print.",
        "",
        "## Print in this order",
        "",
        "0. Use only `stage0_individual_model_only_3mf/`. Print the receiver",
        "   first, then `MODEL_ONLY_r9_gate0_clearance_key_0p4_handle_down.3mf`.",
        "   A previously printed frozen R8 v2 receiver is acceptable because its",
        "   geometry digest is identical. Do not print any legacy R8 identity-pose",
        "   key: those saved poses contain a large floating cantilever. The new key",
        "   must slice Support Off with no floating-cantilever warning, then pass the",
        "   cooled-part overhang screen and ten gentle fit cycles.",
        "1. Print `r9_rear_ledger_male_coupon` + `r9_rear_ledger_female_coupon`,",
        "   then `r9_front_beam_lower_lap_coupon` +",
        "   `r9_front_beam_upper_lap_coupon`. Dry-fit only; no load credit.",
        "2. Print `r9_compact_support`, `r9_shortened_outer_bookend_support`,",
        "   and `r9_concealed_corner_half_control`. Inspect each separately; any",
        "   detectable rocking or visible warp fails the first article. The R8",
        "   structural-control comparison is a future gated test, not this print stage.",
        "3. Print `r9_90_degree_tabletop_angle_fixture`, the through and return",
        "   hidden halves, the shear-key coupon, and cosmetic cover. This proves",
        "   nominal-square handling/reveal only; the closet angle is unverified.",
        "4. Print `r9_two_socket_outer_bookend_rail_fit_coupon` and",
        "   `r9_flush_blank_cable_module`; qualify both sockets. Then print",
        "   `r9_multi_cable_comb_hook_module`. Insert straight inward at the upper",
        "   entry, drop exactly 8 mm, and remove by the exact reverse path.",
        "5. Only after the standalone interface passes, print the distinct through",
        "   and return `outer_bookend_additive_two_socket_candidate` articles.",
        "   Their receivers are fused/additive, not removable rails. Test blank and",
        "   comb in both sockets on the table. Do not attach them to a wall.",
        "6. Stop after the required tabletop articles and service checks. Do not",
        "   print duplicates as a shelf set.",
        "",
        "## Per-part saved orientation and support rule",
        "",
    ]
    lines.extend(
        [
            "- `r8_clearance_ladder_receiver` — Support OFF; frozen R8 v2 broad",
            "  rear face on plate; reprint only if the existing receiver fails inspection.",
            "- `r9_gate0_clearance_key_0p4_handle_down` — Support OFF; exact proper",
            "  180-degree-X pose with the 20 x 16 mm handle on the plate; mandatory",
            "  slicer-warning and physical keyed-head overhang screens.",
        ]
    )
    for part in parts:
        rule = "Support ON" if part.support_required else "Support OFF"
        lines.append(
            f"- `{part.mesh_id}` — {rule}; `{part.print_orientation}`."
        )
    lines.extend(
        [
            "",
            f"Support-off inventory: {', '.join(support_off)}.",
            f"Support-required inventory: {', '.join(support_on) if support_on else 'none'}.",
            "Support classification is software evidence only; Preview remains mandatory.",
            "",
            "## Hard stop",
            "",
            "Do not drill, mount, print the full shelf, store anything on these",
            "parts, or infer a load rating. Endpoint doorway/trim/cable-loop clearance, a complete",
            "one-bay support/member interface, exact corner field geometry, framing,",
            "hardware, proof, creep, recovery, and destructive tests remain open.",
            "Start with `docs/PRINTER_KICKOFF.md`, then use this bundle's",
            "remaining `docs/` guides for records and gates.",
            "",
        ]
    )
    return "\n".join(lines)


def _artifact_record(path: Path, root: Path, **extra: Any) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": model_io.sha256_file(path),
        **extra,
    }


def _build_stage(
    stage: Path,
    cfg: dict[str, Any],
    source_bundle: dict[str, Any],
    runtime: dict[str, Any],
    r8_dependency: dict[str, Any],
) -> None:
    parts = _qualification_parts()
    stage0_parts = _stage0_parts()
    stl_root = stage / "stl"
    individual_root = stage / "individual_model_only_3mf"
    stage0_root = stage / "stage0_individual_model_only_3mf"
    catalog_root = stage / "model_only_3mf"
    serialized: list[tuple[QualificationPart, model_io.SerializedMesh]] = []
    geometry_records: list[dict[str, Any]] = []
    for part in parts:
        frozen = model_io.canonicalize_mesh(part.mesh)
        evidence = model_io.serialized_mesh_evidence(frozen)
        if not evidence["closed_one_body_positive"]:
            raise ValueError(f"serialized R9 part is invalid: {part.mesh_id}")
        if not part.envelope["fits"]:
            raise ValueError(f"R9 part does not fit A1 mini: {part.mesh_id}")
        serialized.append((part, frozen))
        stl_path = stl_root / f"{part.mesh_id}.stl"
        model_path = individual_root / f"MODEL_ONLY_{part.mesh_id}.3mf"
        model_io.write_binary_stl(stl_path, frozen)
        model_io.write_model_only_3mf(
            model_path,
            title=part.label,
            description=MODEL_DESCRIPTION,
            objects=(model_io.ModelObject(part.mesh_id, frozen),),
        )
        stl_readback = model_io.read_binary_stl(stl_path)
        inspection = model_io.inspect_model_only_3mf(model_path)
        digest = evidence["canonical_float32_triangle_digest"]
        if model_io.canonical_triangle_digest(stl_readback) != digest:
            raise ValueError(f"STL geometry changed on readback: {part.mesh_id}")
        if tuple(inspection.objects) != (part.mesh_id,):
            raise ValueError(f"individual 3MF object name changed: {part.mesh_id}")
        if inspection.translations_mm != {part.mesh_id: (0.0, 0.0, 0.0)}:
            raise ValueError(f"individual 3MF transform changed: {part.mesh_id}")
        if model_io.canonical_triangle_digest(inspection.objects[part.mesh_id]) != digest:
            raise ValueError(f"individual 3MF geometry changed: {part.mesh_id}")
        geometry_records.append(
            {
                "mesh_id": part.mesh_id,
                "label": part.label,
                "category": part.category,
                "print_orientation": part.print_orientation,
                "support_required": part.support_required,
                "support_evidence": part.support_evidence,
                "print_envelope": part.envelope,
                "serialized_mesh": evidence,
            }
        )

    stage0_geometry_records: list[dict[str, Any]] = []
    stage0_evidence = {
        item.part_name: item for item in gate0.saved_gate0_print_evidence()
    }
    for part in stage0_parts:
        frozen = model_io.canonicalize_mesh(part.mesh)
        serialized_evidence = model_io.serialized_mesh_evidence(frozen)
        if not serialized_evidence["closed_one_body_positive"]:
            raise ValueError(f"serialized Gate-0 part is invalid: {part.mesh_id}")
        if not part.envelope["fits"]:
            raise ValueError(f"Gate-0 part does not fit A1 mini: {part.mesh_id}")
        model_path = stage0_root / f"MODEL_ONLY_{part.mesh_id}.3mf"
        model_io.write_model_only_3mf(
            model_path,
            title=part.label,
            description=MODEL_DESCRIPTION + "; STAGE 0 ONLY",
            objects=(model_io.ModelObject(part.mesh_id, frozen),),
        )
        inspection = model_io.inspect_model_only_3mf(model_path)
        digest = serialized_evidence["canonical_float32_triangle_digest"]
        if tuple(inspection.objects) != (part.mesh_id,):
            raise ValueError(f"Gate-0 object name changed: {part.mesh_id}")
        if inspection.translations_mm != {part.mesh_id: (0.0, 0.0, 0.0)}:
            raise ValueError(f"Gate-0 object transform changed: {part.mesh_id}")
        if model_io.canonical_triangle_digest(inspection.objects[part.mesh_id]) != digest:
            raise ValueError(f"Gate-0 3MF geometry changed: {part.mesh_id}")
        item = stage0_evidence[part.mesh_id]
        stage0_geometry_records.append(
            {
                "mesh_id": part.mesh_id,
                "label": part.label,
                "category": part.category,
                "print_orientation": part.print_orientation,
                "support_required": part.support_required,
                "support_evidence": part.support_evidence,
                "first_layer_contact_area_mm2": round(
                    item.first_layer_contact_area_mm2, 6
                ),
                "largest_new_unsupported_area_mm2": round(
                    item.largest_new_unsupported_area_mm2, 6
                ),
                "largest_new_unsupported_layer_index": (
                    item.largest_new_unsupported_layer_index
                ),
                "slicer_preview_required": item.slicer_preview_required,
                "physical_overhang_screen_required": (
                    item.physical_overhang_screen_required
                ),
                "print_envelope": part.envelope,
                "serialized_mesh": serialized_evidence,
            }
        )

    translations = _catalog_translations(
        [(part.mesh_id, frozen) for part, frozen in serialized]
    )
    catalog_path = catalog_root / COMBINED_FILENAME
    model_io.write_model_only_3mf(
        catalog_path,
        title="R9 qualification off-plate catalog",
        description=MODEL_DESCRIPTION + "; CATALOG IS NOT A PRINT PLATE",
        objects=tuple(
            model_io.ModelObject(part.mesh_id, frozen, translations[part.mesh_id])
            for part, frozen in serialized
        ),
    )
    catalog = model_io.inspect_model_only_3mf(catalog_path)
    expected_order = tuple(part.mesh_id for part, _frozen in serialized)
    if tuple(catalog.objects) != expected_order:
        raise ValueError("combined catalog object order changed")
    if catalog.translations_mm != translations:
        raise ValueError("combined catalog translations changed")
    for part, frozen in serialized:
        if model_io.canonical_triangle_digest(catalog.objects[part.mesh_id]) != (
            model_io.canonical_triangle_digest(frozen)
        ):
            raise ValueError(f"catalog geometry changed: {part.mesh_id}")

    readme_path = stage / "README.md"
    model_io.write_bytes_exclusive(
        readme_path,
        _bundle_readme(cfg, parts, r8_dependency).encode("utf-8"),
    )
    bundled_docs = (
        "PRINTER_KICKOFF.md",
        "PRINT_FIRST.md",
        "ASSEMBLY.md",
        "MEASUREMENT_WORKSHEET.md",
        "TEST_PROTOCOL.md",
    )
    for filename in bundled_docs:
        source = R9_ROOT / "docs" / filename
        model_io.write_bytes_exclusive(stage / "docs" / filename, source.read_bytes())
    predicted_allowlist = sorted(
        [
            "README.md",
            "manifest.json",
            "validation.json",
            f"model_only_3mf/{COMBINED_FILENAME}",
            *[f"docs/{filename}" for filename in bundled_docs],
            *[f"stl/{part.mesh_id}.stl" for part in parts],
            *[
                f"individual_model_only_3mf/MODEL_ONLY_{part.mesh_id}.3mf"
                for part in parts
            ],
            *[
                f"stage0_individual_model_only_3mf/MODEL_ONLY_{part.mesh_id}.3mf"
                for part in stage0_parts
            ],
        ]
    )
    layout = design_math.calculate_layout(cfg)
    validation = {
        "package_id": PACKAGE_ID,
        "qualification_only": True,
        "unsliced": True,
        "generated_gcode_present": False,
        "embedded_toolpath_file_count": 0,
        "embedded_print_profile_present": False,
        "combined_catalog_is_single_a1_mini_plate": False,
        "manual_support_and_brim_review_required": True,
        "full_shelf_set_present": False,
        "wall_bores_present": False,
        "physical_qualification_complete": False,
        "production_ready": False,
        "installed_release_allowed": False,
        "load_rating_allowed": False,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
        "printed_material": "PETG only",
        "candidate_settings": _candidate_settings(cfg),
        "artifact_config_identity": {
            "contract_id": "r9_compact_bookend_artifact_config_v5",
            "canonical_json_sha256": EXPECTED_CONFIG_CANONICAL_SHA256,
            "exact_match": True,
        },
        "source_bundle": source_bundle,
        "runtime_provenance": runtime,
        "r8_gate0_and_control_dependency": r8_dependency,
        "effective_gate0_print_routing": {
            "receiver_mesh_id": STAGE0_RECEIVER_ID,
            "key_mesh_id": STAGE0_KEY_ID,
            "directory": "stage0_individual_model_only_3mf",
            "legacy_r8_identity_pose_keys_printable": False,
            "required_fit_clearance_per_face_mm": 0.4,
            "supersedes_package_id": "r9_compact_bookend_petg_qualification_v4",
            "supersession_scope": "Stage-0 key saved pose only",
        },
        "topology": {
            "levels": layout.levels,
            "structural_stations_per_level": layout.structural_stations_per_level,
            "visible_supports_per_level": layout.visible_supports_per_level,
            "outer_feature_columns_per_level": layout.outer_feature_columns_per_level,
            "ordinary_compact_supports_per_level": (
                layout.ordinary_compact_supports_per_level
            ),
            "hidden_corner_halves_per_level": layout.hidden_corner_halves_per_level,
            "visible_inside_corner_columns_per_level": (
                layout.visible_inside_corner_columns_per_level
            ),
            "cable_rails_per_level": layout.cable_rails_per_level,
            "cable_sockets_per_level": layout.cable_sockets_per_level,
            "run_local_datums": [
                {
                    "run_id": run.run_id,
                    "coordinate_scope": run.coordinate_scope,
                    "coordinate_datum": run.coordinate_datum,
                    "positive_direction": run.positive_direction,
                }
                for run in layout.runs
            ],
        },
        "field_measurements": {
            "through": asdict(layout.field_fits[0]),
            "return": asdict(layout.field_fits[1]),
            "return_measurement_basis": cfg["field_reference"][
                "return_wall_length_basis"
            ],
            "measurements_authorize_installed_cad": False,
            "unallocated_clear_length_is_cut_endpoint_or_drill_clearance": False,
        },
        "geometry_records_in_order": geometry_records,
        "stage0_geometry_records_in_order": stage0_geometry_records,
        "geometry_digests_by_mesh_id": {
            record["mesh_id"]: record["serialized_mesh"][
                "canonical_float32_triangle_digest"
            ]
            for record in geometry_records
        },
        "stage0_geometry_digests_by_mesh_id": {
            record["mesh_id"]: record["serialized_mesh"][
                "canonical_float32_triangle_digest"
            ]
            for record in stage0_geometry_records
        },
        "combined_catalog_path": f"model_only_3mf/{COMBINED_FILENAME}",
        "combined_object_names_in_order": list(expected_order),
        "combined_translations_mm": {
            name: list(value) for name, value in translations.items()
        },
        "combined_object_order_readback_exact": True,
        "combined_translations_readback_exact": True,
        "fixture_evidence": _fixture_evidence(),
        "integral_bookend_receiver_evidence": {
            "through_core_containment": asdict(
                attachment.core_containment_evidence("through_outer")
            ),
            "return_core_containment": asdict(
                attachment.core_containment_evidence("return_outer")
            ),
            "endpoint_semantics": asdict(attachment.endpoint_semantics_evidence()),
            "installed_clearance_qualified": False,
            "wall_attachment_authored": False,
            "rated_load_kg": 0.0,
        },
        "release_blockers": [
            "field wall lengths are recorded, but exact installed station/end/"
            "corner geometry is unauthored",
            "field corner angle, wall bow, outlet, trim, and service envelopes "
            "are unresolved",
            "framing, blocking, substrate, hardware, pilot, embedment, and driver "
            "records are unresolved",
            "compact-support ledger/front-beam one-bay interfaces are not authored",
            "endpoint doorway, trim, cable-loop, snag, and installed service "
            "clearances are not qualified",
            "full shelf and corner load paths are not authored or physically qualified",
            "target load, proof, creep, recovery, and destructive tests are unresolved",
        ],
        "exact_file_allowlist": predicted_allowlist,
    }
    validation_path = stage / "validation.json"
    model_io.write_bytes_exclusive(validation_path, _json_bytes(validation))

    non_manifest_paths = sorted(
        path for path in stage.rglob("*") if path.is_file() and path.name != "manifest.json"
    )
    records: list[dict[str, Any]] = []
    geometry_by_id = {record["mesh_id"]: record for record in geometry_records}
    stage0_geometry_by_id = {
        record["mesh_id"]: record for record in stage0_geometry_records
    }
    for path in non_manifest_paths:
        relative = path.relative_to(stage).as_posix()
        extra: dict[str, Any] = {"kind": "bundle_metadata"}
        if relative.startswith("stl/"):
            mesh_id = path.stem
            extra = {
                "kind": "binary_stl",
                "mesh_id": mesh_id,
                "canonical_float32_triangle_digest": geometry_by_id[mesh_id][
                    "serialized_mesh"
                ]["canonical_float32_triangle_digest"],
            }
        elif relative.startswith("individual_model_only_3mf/"):
            mesh_id = path.stem.removeprefix("MODEL_ONLY_")
            extra = {
                "kind": "individual_neutral_model_only_3mf",
                "mesh_id": mesh_id,
                "canonical_float32_triangle_digest": geometry_by_id[mesh_id][
                    "serialized_mesh"
                ]["canonical_float32_triangle_digest"],
            }
        elif relative.startswith("stage0_individual_model_only_3mf/"):
            mesh_id = path.stem.removeprefix("MODEL_ONLY_")
            extra = {
                "kind": "stage0_individual_neutral_model_only_3mf",
                "mesh_id": mesh_id,
                "canonical_float32_triangle_digest": stage0_geometry_by_id[mesh_id][
                    "serialized_mesh"
                ]["canonical_float32_triangle_digest"],
            }
        elif relative.startswith("model_only_3mf/"):
            extra = {"kind": "combined_neutral_model_only_3mf_catalog"}
        records.append(_artifact_record(path, stage, **extra))
    exact_allowlist = sorted([record["path"] for record in records] + ["manifest.json"])
    if exact_allowlist != predicted_allowlist:
        raise ValueError("predicted R9 artifact allowlist changed")
    manifest = {
        "schema_version": 1,
        "package_id": PACKAGE_ID,
        "qualification_only": True,
        "unsliced": True,
        "generated_gcode_present": False,
        "embedded_toolpath_file_count": 0,
        "embedded_print_profile_present": False,
        "full_shelf_set_present": False,
        "wall_bores_present": False,
        "physical_qualification_complete": False,
        "production_ready": False,
        "installed_release_allowed": False,
        "load_rating_allowed": False,
        "rated_load_kg": 0.0,
        "rated_load_lb": 0.0,
        "printed_material": "PETG only",
        "artifact_config_identity": validation["artifact_config_identity"],
        "source_bundle": source_bundle,
        "runtime_provenance": runtime,
        "r8_gate0_and_control_dependency": r8_dependency,
        "effective_gate0_print_routing": validation["effective_gate0_print_routing"],
        "field_measurements": validation["field_measurements"],
        "object_names_in_order": list(expected_order),
        "geometry_digests_by_mesh_id": validation["geometry_digests_by_mesh_id"],
        "stage0_geometry_digests_by_mesh_id": validation[
            "stage0_geometry_digests_by_mesh_id"
        ],
        "combined_catalog_path": validation["combined_catalog_path"],
        "combined_translations_mm": validation["combined_translations_mm"],
        "hashed_artifacts_excluding_manifest": records,
        "artifact_count_excluding_manifest": len(records),
        "artifact_bytes_excluding_manifest": sum(record["bytes"] for record in records),
        "exact_file_allowlist": exact_allowlist,
    }
    model_io.write_bytes_exclusive(stage / "manifest.json", _json_bytes(manifest))


def validate_bundle(root: Path) -> dict[str, Any]:
    bundle = Path(root)
    manifest = _strict_json(bundle / "manifest.json")
    validation = _strict_json(bundle / "validation.json")
    if manifest.get("package_id") != PACKAGE_ID or validation.get("package_id") != PACKAGE_ID:
        raise ValueError("R9 package ID mismatch")
    actual_paths: list[str] = []
    for path in bundle.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"R9 bundle contains a symlink: {path}")
        if path.is_file():
            actual_paths.append(path.relative_to(bundle).as_posix())
    if sorted(actual_paths) != manifest["exact_file_allowlist"]:
        raise ValueError("R9 bundle allowlist mismatch")
    records = manifest["hashed_artifacts_excluding_manifest"]
    if len(records) != manifest["artifact_count_excluding_manifest"]:
        raise ValueError("R9 artifact count mismatch")
    for record in records:
        relative = record["path"]
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError(f"unsafe R9 artifact path: {relative}")
        path = bundle / relative
        if path.stat().st_size != record["bytes"]:
            raise ValueError(f"R9 artifact byte mismatch: {relative}")
        if model_io.sha256_file(path) != record["sha256"]:
            raise ValueError(f"R9 artifact hash mismatch: {relative}")
        if path.suffix.lower() == ".3mf":
            inspection = model_io.inspect_model_only_3mf(path)
            if not inspection.passed:
                raise ValueError(f"R9 3MF inspection failed: {relative}")
    expected_digests = manifest["geometry_digests_by_mesh_id"]
    for mesh_id, digest in expected_digests.items():
        stl = model_io.read_binary_stl(bundle / "stl" / f"{mesh_id}.stl")
        individual = model_io.inspect_model_only_3mf(
            bundle / "individual_model_only_3mf" / f"MODEL_ONLY_{mesh_id}.3mf"
        )
        if model_io.canonical_triangle_digest(stl) != digest:
            raise ValueError(f"R9 STL digest mismatch: {mesh_id}")
        if model_io.canonical_triangle_digest(individual.objects[mesh_id]) != digest:
            raise ValueError(f"R9 individual 3MF digest mismatch: {mesh_id}")
    stage0_digests = manifest["stage0_geometry_digests_by_mesh_id"]
    for mesh_id, digest in stage0_digests.items():
        stage0_path = (
            bundle
            / "stage0_individual_model_only_3mf"
            / f"MODEL_ONLY_{mesh_id}.3mf"
        )
        inspection = model_io.inspect_model_only_3mf(stage0_path)
        if tuple(inspection.objects) != (mesh_id,):
            raise ValueError(f"R9 Gate-0 object mismatch: {mesh_id}")
        if inspection.translations_mm != {mesh_id: (0.0, 0.0, 0.0)}:
            raise ValueError(f"R9 Gate-0 transform mismatch: {mesh_id}")
        if model_io.canonical_triangle_digest(inspection.objects[mesh_id]) != digest:
            raise ValueError(f"R9 Gate-0 3MF digest mismatch: {mesh_id}")
    catalog = model_io.inspect_model_only_3mf(bundle / manifest["combined_catalog_path"])
    if tuple(catalog.objects) != tuple(manifest["object_names_in_order"]):
        raise ValueError("R9 combined catalog order mismatch")
    translations = {
        name: tuple(float(value) for value in values)
        for name, values in manifest["combined_translations_mm"].items()
    }
    if catalog.translations_mm != translations:
        raise ValueError("R9 combined catalog transform mismatch")
    for mesh_id, digest in expected_digests.items():
        if model_io.canonical_triangle_digest(catalog.objects[mesh_id]) != digest:
            raise ValueError(f"R9 catalog digest mismatch: {mesh_id}")
    if validation["exact_file_allowlist"] != manifest["exact_file_allowlist"]:
        raise ValueError("R9 validation/manifest allowlists disagree")
    if validation["field_measurements"] != manifest["field_measurements"]:
        raise ValueError("R9 validation/manifest field measurements disagree")
    for flag in (
        "qualification_only",
        "unsliced",
    ):
        if manifest.get(flag) is not True:
            raise ValueError(f"R9 manifest safety flag is not true: {flag}")
    for flag in (
        "generated_gcode_present",
        "embedded_print_profile_present",
        "full_shelf_set_present",
        "wall_bores_present",
        "physical_qualification_complete",
        "production_ready",
        "installed_release_allowed",
        "load_rating_allowed",
    ):
        if manifest.get(flag) is not False:
            raise ValueError(f"R9 manifest safety flag is not false: {flag}")
    return manifest


def build_bundle(destination: Path) -> Path:
    target = Path(destination).expanduser().absolute()
    resolved_target = target.resolve(strict=False)
    r6_root = (R9_ROOT.parent / "r6").resolve()
    r7_root = (R9_ROOT.parent / "r7").resolve()
    r8_root = (R9_ROOT.parent / "r8").resolve()

    def is_within(path: Path, root: Path) -> bool:
        return path == root or root in path.parents

    if any(is_within(resolved_target, root) for root in (r6_root, r7_root, r8_root)):
        raise ValueError("refusing any destination inside frozen R6/R7/R8 trees")
    if is_within(resolved_target, R9_ROOT.resolve()):
        allowed_parent = (R9_ROOT / "generated").resolve()
        if resolved_target.parent != allowed_parent:
            raise ValueError(
                "R9 repository output must be one fresh direct child of generated/"
            )
    if os.path.lexists(target):
        raise FileExistsError(f"refusing existing R9 output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    cfg = _load_frozen_config()
    source_before = _source_bundle()
    runtime = runtime_provenance()
    dependency = _r8_dependency()
    stage = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.stage-", dir=target.parent)
    )
    try:
        _build_stage(stage, cfg, source_before, runtime, dependency)
        validate_bundle(stage)
        if _source_bundle() != source_before:
            raise RuntimeError("R9 sources changed during bundle generation")
        if _canonical_json_sha256(_load_frozen_config()) != (
            EXPECTED_CONFIG_CANONICAL_SHA256
        ):
            raise RuntimeError("R9 config changed during bundle generation")
        model_io.atomic_publish_directory(stage, target)
        validate_bundle(target)
        design_math.validate_frozen_baselines()
        return target
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = build_bundle(args.output)
    manifest = validate_bundle(output)
    print(
        json.dumps(
            {
                "output": str(output),
                "package_id": manifest["package_id"],
                "artifact_count_excluding_manifest": manifest[
                    "artifact_count_excluding_manifest"
                ],
                "manifest_sha256": model_io.sha256_file(output / "manifest.json"),
                "qualification_only": True,
                "rated_load_kg": 0.0,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
