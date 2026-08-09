#!/usr/bin/env python3
"""Generate safe, model-only Story Corner r6 development prototypes.

This file is deliberately isolated under ``development/r6``.  It does not
touch the verified r5 output tree and it cannot emit production geometry or
embedded G-code.  The generated meshes are fit and load-path development
specimens only; they are not a shelf bill of materials and carry no load
rating.

The wall-fastener boundary is intentionally fail-closed:

* the X-corbel prototype never receives a production screw bore;
* when actual screw dimensions are absent, the bearing coupon is a visibly
  crossed, solid ``NO HOLE`` placeholder; and
* ``--production`` always exits before writing anything.

Run with the project environment, for example::

    .venv/bin/python development/r6/generate_all_petg_r6.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


R6_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = R6_DIR.parents[1]
CONFIG_PATH = R6_DIR / "config.json"
OUT = R6_DIR / "generated"
STL_OUT = OUT / "stl"
MODEL_3MF_OUT = OUT / "model_only_3mf"
INDIVIDUAL_MODEL_3MF_OUT = OUT / "individual_model_only_3mf"
GENERATOR_LABEL = "generate_all_petg_r6.py"
GENERATION_SOURCE_BUNDLE_FILENAMES: tuple[str, ...] = tuple(
    sorted(
        {
            "crown_retention_pin.py",
            "design_math.py",
            "generate_all_petg_r6.py",
            "generate_drawings.py",
            "interface_geometry.py",
            "model_io.py",
            "ornament_access.py",
            "ornament_geometry.py",
            "package_layout.py",
            "package_validation.py",
            "rail_geometry.py",
            "release_inventory.py",
            "release_plan.py",
            "retention_cross_key.py",
        }
    )
)

# Direct execution places development/r6, rather than the repository root, at
# sys.path[0].  Add both local sources explicitly before importing shared r6
# math and the already-tested neutral mesh/3MF primitives.
for source_root in (PROJECT_ROOT, R6_DIR):
    source = str(source_root)
    if source not in sys.path:
        sys.path.insert(0, source)

try:
    import numpy as np
    import trimesh
    from shapely.geometry import LineString, Polygon
    from shapely.geometry import box as shapely_box
    from shapely.ops import unary_union

    from design_math import (
        calculate_plan,
        grand_arc,
        production_blockers,
        x_corbel_geometry,
    )
    from generate_drawings import generate_drawings
    from model_io import (
        boolean_difference,
        boolean_union,
        cuboid,
        normalize_mesh,
        rounded_prism,
        write_instanced_model_3mf as _write_instanced_model_3mf,
        write_model_3mf as _write_model_3mf,
    )
    from package_layout import (
        ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS,
        EXPECTED_EMITTED_SOURCE_PART_COUNT,
        SAFETY_DESCRIPTION,
        PackageMeshSourceAudit,
        PrototypeSpec,
        arrange_package_plan,
        build_release_package_plans,
    )
    from package_validation import (
        inspect_model_only_3mf,
        inspect_serialized_stl_geometry,
        serialized_mesh_geometry_evidence,
        validate_package_3mf,
    )
    from interface_geometry import (
        arch_saved_to_run_matrix,
        cassette_saved_to_run_matrix,
        crown_bridge_contract,
        diaphragm_retention_contract,
        integrated_cap_lock_contract,
        ornament_interface_contract,
        physical_crown_face_shift_mm,
        rail_baseline_contract,
        saddle_thermal_contract,
        spring_socket_contract,
        structural_elevation_contract,
        top_feature_x_from_spring_mm,
    )
    from ornament_geometry import (
        build_ornament_families,
        compact_pier_gravity_keyhole_boss_mesh,
        gravity_keyhole_boss_mesh,
        noncapturing_loose_locator_post_mesh,
        ornament_instances_per_level,
        ornament_topology,
    )
    from ornament_access import (
        carrier_coordinate_contract,
        connector_types_for_family,
        ornament_access_contract,
        swept_oculi_for_family,
    )
    from rail_geometry import (
        run_end_tie_block_mesh,
        stitch_rail_pin_mesh,
        stitch_rail_segment_mesh,
    )
    from release_inventory import (
        count_by,
        enumerate_level_inventory,
        enumerate_selected_inventory,
        inventory_reconciliation,
        records_to_csv,
        records_to_json,
    )
    from release_plan import (
        enumerate_cassette_instances,
        group_cassette_variants,
        plan_all_stitch_rails,
    )
    from retention_cross_key import (
        key_transform_q,
        positive_retention_cross_key_contract,
    )
    from crown_retention_pin import crown_retention_pin_contract
except ModuleNotFoundError as exc:  # pragma: no cover - environment guidance
    raise SystemExit(
        "Story Corner r6 needs the project Python environment. Run "
        "`.venv/bin/python development/r6/generate_all_petg_r6.py`. "
        f"Missing dependency: {exc.name}"
    ) from exc


@dataclass
class PrototypePart:
    """One unique development mesh and its safety-facing metadata."""

    name: str
    mesh: trimesh.Trimesh
    purpose: str
    saved_orientation: str
    status: str = "DEVELOPMENT PROTOTYPE; NO LOAD RATING"
    notes: list[str] = field(default_factory=list)
    design_metrics: dict[str, Any] = field(default_factory=dict)


# No named/static software exception is accepted.  The current config and
# meshes must still pass every runtime Boolean/kinematic validator—including
# the full-facade cross-arm corner gate—before package planning can complete.
# Physical PETG, printer, wall-fastener, fit/cycle/migration, and load gates
# are reported separately and never masquerade as missing CAD.
UNRESOLVED_INTERFACE_BLOCKERS: tuple[dict[str, str], ...] = ()

CASSETTE_COMPLETION_BLOCKER: dict[str, Any] = {
    "id": "R6_CHASSIS_SOFTWARE_GEOMETRY_CLOSED_PHYSICAL_QUALIFICATION_PENDING",
    "state": (
        "TWO-SKIN/CLEVIS/CRADLE/LOCK/KEEPER/TIE/CROWN SOFTWARE GEOMETRY AND "
        "KINEMATICS CLOSED; PHYSICAL INSTALLATION/PRODUCTION QUALIFICATION PENDING"
    ),
    "software_model_package_eligible": True,
    "physical_installation_qualified": False,
    "production_release_eligible": False,
    "configured_bottom_skin_mm": 3.2,
    "configured_bottom_skin_present_in_current_position_specific_meshes": True,
    "current_saved_orientation_verified_top_skin_on_build_plate": True,
    "authoritative_installed_solid_collision_gate_passed": True,
    "authoritative_full_vertical_lift_collision_gate_passed": True,
    "all_22_static_lock_mates_collision_free": True,
    "straight_lock_service_corridor_collision_free": True,
    "compressed_lock_service_sweep_step_mm": 0.4,
    "compressed_lock_service_sweep_mm": 75.0,
    "compressed_lock_service_sweep_boolean_pair_count": 8316,
    "expanded_tail_flex_coupon_required": True,
    "required_next_pass": (
        "Print the exact same-PETG parent/flex/orientation coupons, confirm printer/"
        "nozzle/material and wall hardware, then complete fit/cycle/thermal/creep/"
        "destructive qualification; no tested load rating exists."
    ),
}


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_config(path: Path = CONFIG_PATH) -> tuple[dict[str, Any], bytes]:
    payload = path.read_bytes()
    cfg = json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )
    if not isinstance(cfg, dict):
        raise ValueError("r6 config root must be a JSON object")
    return cfg, payload


def deep_get(mapping: dict[str, Any], path: str, default: Any = None) -> Any:
    """Schema-tolerant dotted lookup used only for optional/defaulted fields."""

    current: Any = mapping
    for component in path.split("."):
        if not isinstance(current, dict) or component not in current:
            return default
        current = current[component]
    return current


def number(cfg: dict[str, Any], path: str, default: float) -> float:
    value = deep_get(cfg, path, default)
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be numeric; got {value!r}") from exc


def positive(value: float, label: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be finite and positive; got {value!r}")
    return value


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def generation_source_bundle(source_root: Path = R6_DIR) -> dict[str, Any]:
    """Hash the exact active Python source set which authored the artifacts.

    Record paths are basenames relative to the staged r6/publication root, so
    the same evidence remains verifiable after ``publish_root`` relocates the
    self-contained source set.  ``config.json`` remains outside this bundle
    because both reports already enforce its independent ``config_sha256``.
    """

    if len(GENERATION_SOURCE_BUNDLE_FILENAMES) != 14:
        raise ValueError("The generation source allowlist must contain exactly 14 files")
    records: list[dict[str, Any]] = []
    for filename in GENERATION_SOURCE_BUNDLE_FILENAMES:
        path = source_root / filename
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Generation source is missing or unsafe: {path}")
        payload = path.read_bytes()
        records.append(
            {
                "path": filename,
                "size_bytes": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )
    records.sort(key=lambda item: str(item["path"]))
    aggregate = hashlib.sha256()
    for record in records:
        aggregate.update(str(record["path"]).encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(record["size_bytes"]).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(str(record["sha256"]).encode("ascii"))
        aggregate.update(b"\n")
    return {
        "schema_version": 1,
        "hash_algorithm": "sha256",
        "aggregate_serialization": (
            "UTF-8 path + NUL + decimal size_bytes + NUL + lowercase hex "
            "sha256 + LF; records sorted by path"
        ),
        "config_sha256_enforced_separately": True,
        "source_file_count": len(records),
        "aggregate_sha256": aggregate.hexdigest(),
        "records": records,
    }


def finish_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Normalize and deterministically clean a generated solid."""

    mesh = mesh.copy()
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    if float(mesh.volume) < 0.0:
        mesh.invert()
    normalize_mesh(mesh)
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    return mesh


SERIALIZED_REPAIR_GRID_DECIMALS = 4
SERIALIZED_MAXIMUM_BOUNDS_DRIFT_MM = 1.0e-4
SERIALIZED_MAXIMUM_VOLUME_DRIFT_MM3 = 0.5


def _serialized_coordinate_vertices(
    vertices: np.ndarray, *, encoding: str
) -> np.ndarray:
    """Return the coordinates an STL or neutral 3MF can actually preserve."""

    source = np.asarray(vertices, dtype=np.float64)
    if encoding == "binary_stl_float32":
        return source.astype(np.float32).astype(np.float64)
    if encoding == "neutral_3mf_round_trip_decimal_17":
        # model_io uses the shortest deterministic 17-significant-digit form,
        # which round-trips every input float64 coordinate exactly.
        return source.copy()
    if encoding == "repair_grid_decimal_4":
        return np.round(source, SERIALIZED_REPAIR_GRID_DECIMALS)
    raise ValueError(f"Unknown serialized-coordinate encoding: {encoding!r}")


def _exact_coordinate_weld(
    vertices: np.ndarray, faces: np.ndarray
) -> trimesh.Trimesh:
    """Weld only coordinates which are exactly equal after serialization."""

    unique_vertices, inverse = np.unique(
        np.asarray(vertices, dtype=np.float64), axis=0, return_inverse=True
    )
    remapped_faces = inverse[np.asarray(faces, dtype=np.int64)]
    return trimesh.Trimesh(
        vertices=unique_vertices,
        faces=remapped_faces,
        process=False,
    )


def _remove_serialized_debris(
    mesh: trimesh.Trimesh,
) -> tuple[trimesh.Trimesh, int]:
    """Remove faces which collapse only after an output coordinate encoding.

    Boolean output can contain a triangle whose vertices are distinct in the
    in-memory double-precision mesh but collinear after STL float32 or 3MF
    round-trip-decimal serialization.  Such a face is not printable geometry.  This
    cleanup operates only on an output copy and never relaxes an installed
    interface or collision threshold.
    """

    cleaned = mesh.copy()
    vertices = np.asarray(cleaned.vertices, dtype=np.float64)
    faces = np.asarray(cleaned.faces, dtype=np.int64)
    triangles = vertices[faces]
    cross = np.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    nondegenerate = np.einsum("ij,ij->i", cross, cross) > 0.0
    removed = int(np.count_nonzero(~nondegenerate))
    cleaned.update_faces(nondegenerate)

    unique_faces = cleaned.unique_faces()
    removed += int(np.count_nonzero(~unique_faces))
    cleaned.update_faces(unique_faces)
    cleaned.remove_unreferenced_vertices()
    cleaned.fix_normals()
    if float(cleaned.volume) < 0.0:
        cleaned.invert()
    return cleaned, removed


def _serialized_mesh_is_closed(mesh: trimesh.Trimesh) -> bool:
    if len(mesh.faces) == 0:
        return False
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    triangles = vertices[np.asarray(mesh.faces, dtype=np.int64)]
    cross = np.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    if np.any(np.einsum("ij,ij->i", cross, cross) <= 0.0):
        return False
    return bool(
        mesh.is_watertight
        and mesh.is_winding_consistent
        and mesh.is_volume
        and len(mesh.split(only_watertight=False)) == 1
    )


def serialization_ready_mesh(
    source_mesh: trimesh.Trimesh,
    *,
    target: str,
    source_name: str = "unnamed mesh",
) -> trimesh.Trimesh:
    """Build a deterministic, round-trip-safe output copy of one solid.

    Native STL/3MF quantization is retained whenever it stays a closed solid.
    If quantization collapses any face, the output copy is snapped to a
    0.0001 mm grid before exact welding and debris removal.  The repair grid is
    four thousand times finer than the project's smallest 0.4 mm qualified-fit
    step, while explicit bounds and volume drift gates prevent it from hiding
    a substantive geometry change.
    """

    encoding = {
        "stl": "binary_stl_float32",
        "3mf": "neutral_3mf_round_trip_decimal_17",
    }.get(target)
    if encoding is None:
        raise ValueError(f"Unknown serialized mesh target: {target!r}")
    source = source_mesh.copy()
    source.remove_unreferenced_vertices()
    source.fix_normals()
    # The double-precision Boolean source may still carry a zero-area helper
    # facet while Trimesh correctly recognizes its indexed shell as a closed
    # volume.  Removing that serialization debris is this function's job, so
    # the source gate checks topology here and the stricter positive-triangle
    # gate is applied to the returned output copy below.
    if not (
        source.is_watertight
        and source.is_winding_consistent
        and source.is_volume
        and len(source.split(only_watertight=False)) == 1
    ):
        raise ValueError(
            f"{source_name} ({target}): source mesh is not one closed positive volume"
        )

    native = _exact_coordinate_weld(
        _serialized_coordinate_vertices(source.vertices, encoding=encoding),
        source.faces,
    )
    native, native_removed = _remove_serialized_debris(native)
    if native_removed == 0 and _serialized_mesh_is_closed(native):
        result = native
    else:
        repaired = _exact_coordinate_weld(
            _serialized_coordinate_vertices(
                source.vertices, encoding="repair_grid_decimal_4"
            ),
            source.faces,
        )
        repaired, _removed = _remove_serialized_debris(repaired)
        if not _serialized_mesh_is_closed(repaired):
            raise ValueError(
                f"{source_name} ({target}): 0.0001 mm serialization repair did not preserve a "
                "watertight one-body positive volume"
            )
        # The repair grid is an intermediate cleanup, not the output encoding.
        # Re-apply the requested target encoding so the returned coordinates
        # are exactly the ones a consumer will decode.  In particular, binary
        # STL still stores the repaired decimal coordinates as float32; using
        # the pre-float32 repair mesh for a paired 3MF would straddle common
        # audit-grid ties despite representing the same intended surface.
        encoded_repair = _exact_coordinate_weld(
            _serialized_coordinate_vertices(repaired.vertices, encoding=encoding),
            repaired.faces,
        )
        encoded_repair, encoded_removed = _remove_serialized_debris(encoded_repair)
        if encoded_removed or not _serialized_mesh_is_closed(encoded_repair):
            raise ValueError(
                f"{source_name} ({target}): target encoding did not preserve the "
                "0.0001 mm repaired watertight one-body volume"
            )
        result = encoded_repair

    bounds_drift = float(
        np.max(
            np.abs(
                np.asarray(result.bounds, dtype=float)
                - np.asarray(source.bounds, dtype=float)
            )
        )
    )
    volume_drift = abs(abs(float(result.volume)) - abs(float(source.volume)))
    volume_limit = max(
        SERIALIZED_MAXIMUM_VOLUME_DRIFT_MM3,
        abs(float(source.volume)) * 1.0e-6,
    )
    if bounds_drift > SERIALIZED_MAXIMUM_BOUNDS_DRIFT_MM + 1.0e-12:
        raise ValueError(
            f"{source_name} ({target}): serialized bounds drift {bounds_drift:.9f} mm exceeds "
            f"{SERIALIZED_MAXIMUM_BOUNDS_DRIFT_MM:.7f} mm"
        )
    if volume_drift > volume_limit + 1.0e-9:
        raise ValueError(
            f"{source_name} ({target}): serialized solid-volume drift {volume_drift:.9f} mm3 "
            f"exceeds {volume_limit:.9f} mm3"
        )
    return result


def write_model_3mf(
    path: Path,
    title: str,
    description: str,
    objects: list[tuple[str, trimesh.Trimesh, tuple[float, float, float]]],
) -> None:
    """Write a neutral 3MF after common serialized-coordinate cleanup."""

    _write_model_3mf(
        path,
        title,
        description,
        [
            (
                name,
                serialization_ready_mesh(mesh, target="3mf", source_name=name),
                translation,
            )
            for name, mesh, translation in objects
        ],
    )


def write_instanced_model_3mf(
    path: Path,
    title: str,
    description: str,
    mesh_families: list[tuple[str, trimesh.Trimesh]],
    instances: list[tuple[str, str, tuple[float, float, float]]],
) -> None:
    """Write an instanced neutral 3MF using the same mesh cleanup as STL."""

    _write_instanced_model_3mf(
        path,
        title,
        description,
        [
            (
                name,
                serialization_ready_mesh(mesh, target="3mf", source_name=name),
            )
            for name, mesh in mesh_families
        ],
        instances,
    )


def clean_mesh_preserve_coordinates(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Clean a boolean result without translating its installed-coordinate datum."""

    mesh = mesh.copy()
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    if float(mesh.volume) < 0.0:
        mesh.invert()
    components = [
        component
        for component in mesh.split(only_watertight=False)
        if len(component.faces) >= 4 and abs(float(component.volume)) > 1.0e-6
    ]
    if len(components) == 1:
        mesh = components[0]
        mesh.remove_unreferenced_vertices()
        mesh.merge_vertices()
        mesh.fix_normals()
    return mesh


def safe_union_installed(
    meshes: Iterable[trimesh.Trimesh], label: str
) -> trimesh.Trimesh:
    """Boolean-union installed-coordinate solids without normalizing mid-build."""

    source = list(meshes)
    if not source:
        raise ValueError(f"{label}: cannot union an empty mesh list")
    try:
        result = boolean_union(source)
    except Exception as exc:  # pragma: no cover - backend-specific error path
        raise RuntimeError(f"{label}: manifold union failed: {exc}") from exc
    if result is None or len(result.faces) == 0:
        raise RuntimeError(f"{label}: manifold union returned no solid")
    return clean_mesh_preserve_coordinates(result)


def safe_difference_installed(
    body: trimesh.Trimesh,
    cutters: Iterable[trimesh.Trimesh],
    label: str,
) -> trimesh.Trimesh:
    """Boolean-cut installed-coordinate solids without normalizing mid-build."""

    cutter_list = list(cutters)
    if not cutter_list:
        return clean_mesh_preserve_coordinates(body)
    try:
        result = boolean_difference(body, cutter_list)
    except Exception as exc:  # pragma: no cover - backend-specific error path
        raise RuntimeError(f"{label}: manifold difference failed: {exc}") from exc
    if result is None or len(result.faces) == 0:
        raise RuntimeError(f"{label}: manifold difference returned no solid")
    return clean_mesh_preserve_coordinates(result)


def union_integral_ornament_bosses(
    parent: trimesh.Trimesh,
    bosses: Iterable[trimesh.Trimesh],
    *,
    minimum_overlap_mm3: float,
    label: str,
    overlap_reference: trimesh.Trimesh | None = None,
) -> tuple[trimesh.Trimesh, list[float]]:
    """Fuse exact sacrificial bosses and prove each +0.02 mm parent union."""

    current = clean_mesh_preserve_coordinates(parent)
    overlaps: list[float] = []
    for index, boss in enumerate(bosses, start=1):
        reference = current if overlap_reference is None else overlap_reference
        intersection = trimesh.boolean.intersection(
            [reference, boss], engine="manifold", check_volume=True
        )
        if (
            intersection is None
            or len(intersection.faces) < 4
            or not intersection.is_watertight
        ):
            overlap = 0.0
        else:
            overlap = abs(float(intersection.volume))
        combined = safe_union_installed(
            [current, boss], f"{label} ornament boss {index}"
        )
        mesh_boolean_tolerance_mm3 = 1.0e-3
        if overlap < minimum_overlap_mm3 - mesh_boolean_tolerance_mm3:
            raise ValueError(
                f"{label}: ornament boss {index} parent union is only "
                f"{overlap:.9f} mm3"
            )
        # Any materially larger overlap means the boss entered structural
        # material beyond the frozen 0.02 mm sacrificial neck union.
        if overlap > minimum_overlap_mm3 + mesh_boolean_tolerance_mm3:
            raise ValueError(
                f"{label}: ornament boss {index} over-embeds its parent by "
                f"{overlap - minimum_overlap_mm3:.9f} mm3"
            )
        current = combined
        overlaps.append(overlap)
    return current, overlaps


def positive_solid_intersection_volume_mm3(
    left: trimesh.Trimesh, right: trimesh.Trimesh
) -> float:
    """Measure only real positive-volume overlap between two closed solids."""

    if not np.all(
        np.asarray(left.bounds[1], dtype=float)
        > np.asarray(right.bounds[0], dtype=float) + 1.0e-9
    ) or not np.all(
        np.asarray(right.bounds[1], dtype=float)
        > np.asarray(left.bounds[0], dtype=float) + 1.0e-9
    ):
        return 0.0
    overlap = trimesh.boolean.intersection(
        [left, right], engine="manifold", check_volume=True
    )
    if overlap is None or len(overlap.faces) < 4 or not overlap.is_watertight:
        return 0.0
    if np.any(np.asarray(overlap.extents, dtype=float) <= 1.0e-8):
        return 0.0
    return abs(float(overlap.volume))


def safe_union(meshes: Iterable[trimesh.Trimesh], label: str) -> trimesh.Trimesh:
    source = list(meshes)
    if not source:
        raise ValueError(f"{label}: cannot union an empty mesh list")
    try:
        result = boolean_union(source)
    except Exception as exc:  # pragma: no cover - backend-specific error path
        raise RuntimeError(f"{label}: manifold union failed: {exc}") from exc
    if result is None or len(result.faces) == 0:
        raise RuntimeError(f"{label}: manifold union returned no solid")
    return finish_mesh(result)


def safe_difference(
    body: trimesh.Trimesh,
    cutters: Iterable[trimesh.Trimesh],
    label: str,
) -> trimesh.Trimesh:
    cutter_list = list(cutters)
    if not cutter_list:
        return finish_mesh(body)
    try:
        result = boolean_difference(body, cutter_list)
    except Exception as exc:  # pragma: no cover - backend-specific error path
        raise RuntimeError(f"{label}: manifold difference failed: {exc}") from exc
    if result is None or len(result.faces) == 0:
        raise RuntimeError(f"{label}: manifold difference returned no solid")
    return finish_mesh(result)


def extrude_polygon(shape: Polygon, height: float, *, z0: float = 0.0) -> trimesh.Trimesh:
    if shape.is_empty or not shape.is_valid:
        raise ValueError("Cannot extrude an empty or invalid polygon")
    mesh = trimesh.creation.extrude_polygon(shape, height=height, engine="earcut")
    if z0:
        mesh.apply_translation([0.0, 0.0, z0])
    return mesh


def cylinder_z(
    diameter: float,
    height: float,
    *,
    center_xy: tuple[float, float],
    z0: float = 0.0,
    sections: int = 48,
) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(
        radius=positive(diameter, "cylinder diameter") / 2.0,
        height=positive(height, "cylinder height"),
        sections=sections,
    )
    mesh.apply_translation([center_xy[0], center_xy[1], z0 + height / 2.0])
    return mesh


def cylinder_y(
    diameter: float,
    length: float,
    *,
    center_xz: tuple[float, float],
    y0: float = 0.0,
    sections: int = 48,
) -> trimesh.Trimesh:
    """Create a cylinder whose axis follows installed rear-to-front ``q``/Y.

    Keeping this as a coordinate-preserving primitive avoids the old failure
    mode where an intermediate normalized mesh made a later installed-datum
    cutter miss its intended parent.
    """

    mesh = trimesh.creation.cylinder(
        radius=positive(diameter, "cylinder diameter") / 2.0,
        height=positive(length, "cylinder length"),
        sections=sections,
    )
    mesh.apply_transform(
        trimesh.geometry.align_vectors(
            np.asarray([0.0, 0.0, 1.0]),
            np.asarray([0.0, 1.0, 0.0]),
        )
    )
    mesh.apply_translation(
        [center_xz[0], y0 + length / 2.0, center_xz[1]]
    )
    return mesh


def positive_cross_key_receiver_local_geometry(
    cfg: dict[str, Any],
) -> tuple[trimesh.Trimesh, list[trimesh.Trimesh], dict[str, Any]]:
    """Return the integral receiver-boss blank and all exact local cutters.

    Local axes are the frozen cross-key axes ``(u, y, q)`` with the parent
    visible face at q=0 and wall/rear in +q.  The caller transforms both the
    boss and cutters into its parent coordinates before the final Boolean.
    """

    key = cfg["tied_arcade"]["retention_wedge"]
    contract = positive_retention_cross_key_contract(cfg)
    boss = key["front_bayonet_boss"]
    outer_u, outer_y = (float(value) for value in boss["outer_run_y_mm"])
    outer_q = tuple(float(value) for value in boss["outer_q_envelope_mm"])
    gate_q = tuple(float(value) for value in boss["front_gate_q_envelope_mm"])
    slot_u, slot_y = (
        float(value) for value in boss["vertical_entry_slot_run_y_mm"]
    )
    chamber_q = tuple(
        float(value) for value in boss["rotation_chamber_q_envelope_mm"]
    )
    primary_q = tuple(
        float(value) for value in key["receiver_primary_q_envelope_mm"]
    )
    dog_depth = float(
        key["visible_handle_and_positive_index"][
            "latch_dog_nominal_positive_engagement_mm"
        ]
    )
    outer = cuboid(
        (outer_u, outer_y, outer_q[1] - outer_q[0]),
        origin=(-outer_u / 2.0, -outer_y / 2.0, outer_q[0]),
    )
    cutters = [
        cuboid(
            (slot_u, slot_y, gate_q[1] - gate_q[0] + 0.4),
            origin=(-slot_u / 2.0, -slot_y / 2.0, gate_q[0] - 0.2),
        ),
        cylinder_z(
            float(boss["rotation_chamber_diameter_mm"]),
            chamber_q[1] - chamber_q[0] + 0.4,
            center_xy=(0.0, 0.0),
            z0=chamber_q[0] - 0.2,
        ),
        cylinder_z(
            float(key["tenon_through_bore_diameter_mm"]),
            primary_q[1] - chamber_q[1] + 0.6,
            center_xy=(0.0, 0.0),
            z0=chamber_q[1] - 0.2,
        ),
        # One hard-sided dog seat at the locked +u index.  It is open at the
        # outer +u wall and has exactly the configured 1.2 mm q engagement.
        cuboid(
            (1.8, 3.6, dog_depth + 0.2),
            origin=(outer_u / 2.0 - 1.8, -1.8, outer_q[0] - 0.1),
        ),
    ]
    return outer, cutters, {
        "family_id": contract.family_id,
        "outer_u_y_q_envelope_mm": [outer_u, outer_y, list(outer_q)],
        "entry_slot_u_y_mm": [slot_u, slot_y],
        "rotation_chamber_diameter_mm": float(
            boss["rotation_chamber_diameter_mm"]
        ),
        "shaft_bore_diameter_mm": contract.bore_diameter_mm,
        "unique_locked_index_notch_count": 1,
        "latch_dog_nominal_engagement_mm": dog_depth,
        "parent_positive_union_overlap_q_mm": list(
            boss["parent_positive_union_overlap_q_mm"]
        ),
    }


def structural_cross_key_service_access_mm(cfg: dict[str, Any]) -> float:
    """Return the single authoritative structural cross-key service clearance.

    The top cassette receivers, spring receiver, crown bridge, and two-level
    placement rule describe the same visible-front service corridor. Missing
    or contradictory source fields fail closed; this function never supplies
    a numeric fallback.
    """

    cross_key = positive_retention_cross_key_contract(cfg)
    access = float(cross_key.minimum_external_service_access_mm)
    peers = {
        "spring_joint": float(
            cfg["tied_arcade"]["spring_final_x_vertical_joint"]
            ["minimum_straight_service_access_mm"]
        ),
        "crown_bridge": float(
            cfg["tied_arcade"]["rear_crown_bridge"]
            ["minimum_straight_service_access_mm"]
        ),
        "two_level_vertical_layout": float(
            cfg["closet"]["vertical_layout"]
            ["minimum_straight_wedge_and_pin_service_access_mm"]
        ),
    }
    mismatches = {
        name: value for name, value in peers.items() if abs(value - access) > 1.0e-7
    }
    if mismatches:
        raise ValueError(
            "Structural cross-key service-access contracts disagree: "
            f"cross_key={access}, peers={mismatches}"
        )
    return access


def bowtie_key_mesh(
    *,
    total_span: float,
    head_width: float,
    neck_width: float,
    insertion_depth: float,
) -> trimesh.Trimesh:
    """Bottom-inserted Dutchman key with a flat access edge.

    The tapered profile lies in run/elevation (X/Z), while ``insertion_depth``
    occupies shelf depth (Y).  A flat lower profile makes the key compatible
    with the cassette family's bottom-access receiver path; the tapered upper
    shoulders provide the broad longitudinal bearing faces.
    """

    total_span = positive(total_span, "bowtie total span")
    head_width = positive(head_width, "bowtie head width")
    neck_width = positive(neck_width, "bowtie neck width")
    insertion_depth = positive(insertion_depth, "bowtie insertion depth")
    if neck_width >= head_width:
        raise ValueError("A bowtie key neck must be narrower than its heads")
    shoulder = total_span * 0.36
    outline = Polygon(
        [
            (0.0, 0.0),
            (total_span, 0.0),
            (total_span, head_width),
            (total_span - shoulder, neck_width),
            (shoulder, neck_width),
            (0.0, head_width),
        ]
    )
    # extrude_polygon creates X/profile-Y/extrusion-Z. Rotate +90 degrees
    # around X and translate so the final axes are X/run, Y/shelf depth,
    # Z/elevation.
    mesh = extrude_polygon(outline, insertion_depth)
    mesh.apply_transform(
        trimesh.transformations.rotation_matrix(
            math.pi / 2.0,
            [1.0, 0.0, 0.0],
            point=[0.0, 0.0, 0.0],
        )
    )
    mesh.apply_translation([0.0, insertion_depth, 0.0])
    return finish_mesh(mesh)


def clearance_ladder_parts(cfg: dict[str, Any]) -> list[PrototypePart]:
    clearances = [
        float(value)
        for value in deep_get(cfg, "joinery.coupon_clearance_matrix_mm", [0.2, 0.3, 0.4, 0.5])
    ]
    if len(clearances) < 2 or any(value <= 0.0 for value in clearances):
        raise ValueError("joinery.coupon_clearance_matrix_mm needs at least two positive values")

    nominal_tongue = 10.0
    plate_thickness = 6.0
    slot_pitch = 21.0
    margin = 10.0
    receiver_width = 2.0 * margin + slot_pitch * (len(clearances) - 1) + 12.0
    receiver_depth = 70.0
    body = cuboid((receiver_width, receiver_depth, plate_thickness))
    cutters: list[trimesh.Trimesh] = []
    slot_centers: list[float] = []
    pin_diameter = number(cfg, "tied_arcade.rear_crown_bridge.retention_pin_diameter_mm", 5.0)
    for index, clearance in enumerate(clearances):
        center_x = margin + 6.0 + index * slot_pitch
        slot_centers.append(center_x)
        slot_width = nominal_tongue + 2.0 * clearance
        # Open-edge U slots allow one nominal tongue to be tried in every fit.
        cutters.append(
            cuboid(
                (slot_width, 34.0, plate_thickness + 0.4),
                origin=(center_x - slot_width / 2.0, -0.2, -0.2),
            )
        )
        # The matching rear row lets the same anti-drop pin sample four bores.
        cutters.append(
            cylinder_z(
                pin_diameter + 2.0 * clearance,
                plate_thickness + 0.4,
                center_xy=(center_x, 54.0),
                z0=-0.2,
                sections=48,
            )
        )
    receiver = safe_difference(body, cutters, "clearance ladder receiver")

    tongue_shaft = cuboid((nominal_tongue, 35.0, plate_thickness), origin=(6.0, 18.0, 0.0))
    tongue_handle = rounded_prism(22.0, 20.0, plate_thickness, 3.0)
    top_joint = deep_get(
        cfg,
        "tied_arcade.cassette_final_x_vertical_tenon_joint",
        {},
    )
    positive_key = deep_get(cfg, "tied_arcade.retention_wedge", {})
    if not isinstance(top_joint, dict) or not isinstance(positive_key, dict):
        raise ValueError("Clearance-ladder dual coupon needs the top-tenon/key contract")
    tenon_run = float(top_joint["tenon_run_width_mm"])
    tenon_depth = float(top_joint["tenon_depth_mm"])
    tenon_height = float(top_joint["tenon_engagement_height_mm"])
    tenon_bore = float(positive_key["tenon_through_bore_diameter_mm"])
    if (tenon_run, tenon_depth, tenon_height, tenon_bore) != (
        18.0,
        8.0,
        22.0,
        4.0,
    ):
        raise ValueError("Clearance-ladder dual coupon dimensions drifted")
    tenon_origin = (28.0, 6.0, 0.0)
    tenon_stub = cuboid(
        (tenon_run, tenon_depth, tenon_height),
        origin=tenon_origin,
    )
    # The 9 x 4 x 6 bridge overlaps the 22 mm handle by 2 mm and the exact
    # tenon stub by 1 mm.  This produces one deliberate printable body while
    # leaving the fit-ladder tongue and actual top-tenon test ends separated.
    dual_coupon_bridge = cuboid((9.0, 4.0, plate_thickness), origin=(20.0, 8.0, 0.0))
    tongue_blank = safe_union(
        [tongue_shaft, tongue_handle, dual_coupon_bridge, tenon_stub],
        "clearance ladder dual tongue and top-tenon coupon",
    )
    tenon_bore_cutter = cylinder_y(
        tenon_bore,
        tenon_depth + 0.4,
        center_xz=(tenon_origin[0] + tenon_run / 2.0, tenon_height / 2.0),
        y0=tenon_origin[1] - 0.2,
        sections=48,
    )
    tongue = safe_difference(
        tongue_blank,
        [tenon_bore_cutter],
        "clearance ladder dual coupon real top-tenon bore",
    )

    mapping = [
        {
            "left_to_right_index": index + 1,
            "clearance_per_face_mm": clearance,
            "slot_width_mm": nominal_tongue + 2.0 * clearance,
            "pin_bore_diameter_mm": pin_diameter + 2.0 * clearance,
            "slot_center_x_mm": slot_centers[index],
        }
        for index, clearance in enumerate(clearances)
    ]
    return [
        PrototypePart(
            name="R6_DEV_JOINERY_CLEARANCE_LADDER_RECEIVER",
            mesh=receiver,
            purpose="Left-to-right PETG fit ladder for sliding tongues and the 5 mm retention pin.",
            saved_orientation="flat plate face on build plate",
            notes=[
                "Use only with the companion nominal tongue and crown anti-drop pin.",
                "The left-to-right mapping is recorded in validation.json; no text is embossed into a structural coupon.",
            ],
            design_metrics={"nominal_tongue_width_mm": nominal_tongue, "stations": mapping},
        ),
        PrototypePart(
            name="R6_DEV_JOINERY_CLEARANCE_LADDER_TONGUE",
            mesh=tongue,
            purpose=(
                "One-body dual coupon: nominal fit-ladder tongue plus the exact "
                "18 x 8 x 22 mm cassette-top tenon and real 4 mm cross-key bore."
            ),
            saved_orientation=(
                "broad handle/tongue face and top-tenon base on build plate; "
                "the transverse 4 mm bore requires actual-orientation support review"
            ),
            notes=[
                "Do not force a binding fit; record insertion force and surface damage.",
                "Use the exact tenon end only with the selected through-start cassette and actual top positive cross-key.",
                "This coupon proves no complete capture, load capacity, production print mapping, or installation qualification by itself.",
            ],
            design_metrics={
                "tongue_width_mm": nominal_tongue,
                "tongue_engagement_length_mm": 35.0,
                "thickness_mm": plate_thickness,
                "dual_coupon_one_connected_body": True,
                "top_tenon_stub_run_depth_engagement_mm": [
                    tenon_run,
                    tenon_depth,
                    tenon_height,
                ],
                "top_tenon_through_bore_diameter_mm": tenon_bore,
                "top_tenon_receiver_clearance_per_side_mm": float(
                    top_joint["receiver_clearance_per_side_mm"]
                ),
                "positive_cross_key_fit_mating_context": {
                    "tenon_coupon": "R6_DEV_JOINERY_CLEARANCE_LADDER_TONGUE",
                    "actual_parent": "R6_DEV_CASSETTE_THROUGH_01_OF_12",
                    "actual_key": "R6_DEV_FINAL_X_TOP_CAPTURE_WEDGE_UNIVERSAL",
                    "scope": "dimensional insertion/index/cycle coupon only",
                },
                "structural_credit": False,
                "complete_capture_claim": False,
                "physical_installation_qualified": False,
                "production_release_eligible": False,
            },
        ),
    ]


def wall_screw_bearing_coupon(cfg: dict[str, Any]) -> tuple[PrototypePart, dict[str, Any]]:
    support = deep_get(cfg, "support", {})
    if not isinstance(support, dict):
        support = {}
    shank = support.get("field_verified_screw_shank_diameter_mm")
    head = support.get("field_verified_screw_head_or_washer_od_mm")
    dimensions_known = all(value is not None for value in (shank, head))

    base_width = 60.0
    base_depth = 60.0
    seat_thickness = number(cfg, "corbel.minimum_petg_head_seat_thickness_mm", 8.0)
    total_height = max(16.0, seat_thickness + 8.0)
    base = rounded_prism(base_width, base_depth, total_height, 4.0)

    if not dimensions_known:
        # A raised X makes it visually and geometrically impossible to mistake
        # this solid placeholder for a drill guide or qualified bearing coupon.
        bars: list[trimesh.Trimesh] = [base]
        for angle in (-45.0, 45.0):
            bar = cuboid((50.0, 5.0, 4.0), origin=(5.0, 27.5, total_height - 0.05))
            bar.apply_transform(
                trimesh.transformations.rotation_matrix(
                    math.radians(angle),
                    [0.0, 0.0, 1.0],
                    point=[30.0, 30.0, total_height],
                )
            )
            bars.append(bar)
        mesh = safe_union(bars, "blocked wall-screw coupon")
        gate = {
            "state": "HARD_BLOCKED_SOLID_PLACEHOLDER_NO_HOLE",
            "actual_screw_dimensions_known": False,
            "production_holes_generated": False,
            "missing": [
                key
                for key in (
                    "field_verified_screw_shank_diameter_mm",
                    "field_verified_screw_head_or_washer_od_mm",
                )
                if support.get(key) is None
            ],
        }
        return (
            PrototypePart(
                name="R6_DEV_BLOCKED_WALL_SCREW_BEARING_COUPON_SOLID_NO_HOLE",
                mesh=mesh,
                purpose="Fail-closed placeholder proving that unknown wall-fastener dimensions cannot leak into production bores.",
                saved_orientation="flat bearing face on build plate; raised X upward",
                status="HARD BLOCKED; SOLID PLACEHOLDER; NOT A DRILL GUIDE",
                notes=[
                    "There is intentionally no through-hole, head pocket, driver tunnel, or screw-station geometry.",
                    "Measure the actual structural screw, washer/head, driver, wall finish, and blocking before regenerating a test coupon.",
                ],
            ),
            gate,
        )

    shank = positive(float(shank), "verified screw shank diameter")
    head = positive(float(head), "verified screw head/washer diameter")
    clearance_bore = shank + 0.4
    head_pocket = head + 0.6
    boss_od = max(22.0, head + 8.0)
    if head_pocket / 2.0 + 4.0 > boss_od / 2.0 + 1e-9:
        raise ValueError("Verified head/washer leaves less than 4 mm radial PETG ligament")

    boss = cylinder_z(boss_od, total_height, center_xy=(30.0, 30.0))
    blank = safe_union([base, boss], "measured wall-screw test blank")
    shank_cut = cylinder_z(
        clearance_bore,
        total_height + 0.4,
        center_xy=(30.0, 30.0),
        z0=-0.2,
    )
    pocket_depth = total_height - seat_thickness
    head_cut = cylinder_z(
        head_pocket,
        pocket_depth + 0.2,
        center_xy=(30.0, 30.0),
        z0=seat_thickness,
    )
    mesh = safe_difference(blank, [shank_cut, head_cut], "measured wall-screw bearing coupon")
    gate = {
        "state": "MEASURED_DIMENSION_TEST_COUPON_ONLY",
        "actual_screw_dimensions_known": True,
        "production_holes_generated": False,
        "verified_shank_mm": shank,
        "verified_head_or_washer_od_mm": head,
        "coupon_clearance_bore_mm": clearance_bore,
        "coupon_head_pocket_mm": head_pocket,
        "coupon_boss_od_mm": boss_od,
    }
    return (
        PrototypePart(
            name="R6_DEV_MEASURED_WALL_SCREW_BEARING_COUPON_TEST_ONLY",
            mesh=mesh,
            purpose="Sacrificial PETG bearing-seat coupon generated from measured fastener dimensions.",
            saved_orientation="flat wall-contact face on build plate",
            status="TEST COUPON ONLY; CORBEL PRODUCTION BORES REMAIN BLOCKED",
            notes=[
                "This coupon does not authorize a corbel screw station or an overhead installation.",
                "Test against the actual wall finish and verified wood blocking fixture.",
            ],
            design_metrics=gate,
        ),
        gate,
    )


def cassette_half(
    cfg: dict[str, Any],
    *,
    width: float,
    depth: float,
) -> PrototypePart:
    total_height = number(cfg, "structure.cassette_total_height_mm", 30.0)
    skin = number(cfg, "structure.cassette_top_skin_mm", 3.2)
    perimeter = number(cfg, "structure.cassette_perimeter_wall_mm", 4.8)
    rib = max(
        number(cfg, "structure.cassette_internal_rib_mm", 3.2),
        number(cfg, "joinery.minimum_wall_mm", 3.2),
    )
    depth_cells = int(number(cfg, "structure.cassette_depth_cell_count", 9.0))
    maximum_clear = number(cfg, "structure.cassette_maximum_clear_bridge_mm", 14.0)
    tie_zone = deep_get(cfg, "structure.front_entablature_tie_zone_from_rear_mm", [depth - 18.0, depth])
    tie_start = float(tie_zone[0]) if isinstance(tie_zone, list) and tie_zone else depth - 18.0
    tie_start = min(max(tie_start, perimeter * 2.0), depth - perimeter)
    if not (0.0 < skin < total_height and width > 2.0 * perimeter and depth > 2.0 * perimeter):
        raise ValueError("Cassette dimensions do not leave a positive coffer grid")
    if depth_cells < 1:
        raise ValueError("Cassette needs at least one depth cell")

    inner_width = width - 2.0 * perimeter
    x_cells = max(1, math.ceil((inner_width + rib) / (maximum_clear + rib)))
    clear_x = (inner_width - (x_cells - 1) * rib) / x_cells
    grid_depth = tie_start - perimeter
    clear_y = (grid_depth - (depth_cells - 1) * rib) / depth_cells
    if min(clear_x, clear_y) <= 0.0:
        raise ValueError("Cassette rib grid consumes its coffer openings")
    if clear_x > maximum_clear + 1e-6 or clear_y > maximum_clear + 1e-6:
        raise ValueError(
            f"Cassette coffer clear span exceeds {maximum_clear:g} mm: {clear_x:.3f}, {clear_y:.3f}"
        )

    # One continuous skin is printed on the bed.  The coffer grid grows from
    # it, leaving every cell visibly open on the prototype's opposite face.
    # This avoids hidden sealed cavities and keeps the development mesh a
    # verifiably single connected shell.  The configured second skin is not
    # claimed by this prototype and remains a later test decision.
    skin_mesh = cuboid((width, depth, skin))
    outer = shapely_box(0.0, 0.0, width, depth)
    inner = shapely_box(perimeter, perimeter, width - perimeter, depth - perimeter)
    footprint_components = [outer.difference(inner)]
    footprint_components.append(shapely_box(perimeter, tie_start, width - perimeter, depth))

    cursor = perimeter
    for _index in range(x_cells - 1):
        cursor += clear_x
        footprint_components.append(shapely_box(cursor, perimeter, cursor + rib, tie_start))
        cursor += rib

    cursor = perimeter
    for _index in range(depth_cells - 1):
        cursor += clear_y
        footprint_components.append(shapely_box(perimeter, cursor, width - perimeter, cursor + rib))
        cursor += rib

    grid_footprint = unary_union(footprint_components)
    grid_mesh = extrude_polygon(
        grid_footprint,
        total_height - skin + 0.02,
        z0=skin - 0.02,
    )
    mesh = safe_union([skin_mesh, grid_mesh], "coffered cassette half")
    return PrototypePart(
        name="R6_DEV_COFFERED_CASSETTE_HALF_MAX_WIDTH_COUPON",
        mesh=mesh,
        purpose="Worst-width half-bay cassette for bridge-span, rib, surface, and print-behavior development.",
        saved_orientation="continuous skin flat on build plate; coffer grid upward",
        status="COUPON ONLY; NOT A POSITION-SPECIFIC CHASSIS",
        notes=[
            "This first prototype has one continuous skin and an open coffer face so every cell is inspectable.",
            "It intentionally does not claim the config's final two-skin topology, saddle receiver, T-lug tracks, or production seam pockets.",
            "Do not use this isolated cassette as an overhead shelf.",
        ],
        design_metrics={
            "width_mm": width,
            "depth_mm": depth,
            "height_mm": total_height,
            "continuous_skin_mm": skin,
            "effective_structural_rib_mm": rib,
            "coffer_cells_across_width": x_cells,
            "coffer_cells_across_depth": depth_cells,
            "maximum_actual_clear_span_mm": max(clear_x, clear_y),
            "front_solid_tie_zone_start_mm": tie_start,
        },
    )


def extrude_xz_profile_along_y(
    profile_xz: Polygon,
    *,
    y0: float,
    depth: float,
) -> trimesh.Trimesh:
    """Extrude an X/Z profile through a shelf-depth Y band."""

    depth = positive(depth, "profile extrusion depth")
    mesh = extrude_polygon(profile_xz, depth)
    mesh.apply_transform(
        trimesh.transformations.rotation_matrix(
            math.pi / 2.0,
            [1.0, 0.0, 0.0],
            point=[0.0, 0.0, 0.0],
        )
    )
    # +90 degrees maps the original extrusion 0..depth to Y=-depth..0.
    mesh.apply_translation([0.0, y0 + depth, 0.0])
    return mesh


def extrude_yz_profile_along_x(
    profile_yz: Polygon,
    *,
    x0: float,
    width: float,
) -> trimesh.Trimesh:
    """Extrude a rear/front--elevation profile through a run-axis interval."""

    width = positive(width, "profile extrusion width")
    mesh = extrude_polygon(profile_yz, width)
    # extrude_polygon authors (profile-X, profile-Y, extrusion-Z).  Here the
    # profile axes are installed (q, e), so permute to installed (s, q, e).
    mesh.apply_transform(
        np.asarray(
            [
                [0.0, 0.0, 1.0, x0],
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
    )
    return mesh


def cassette_seam_class(run_plan: Any, station_mm: float) -> str:
    """Classify one nominal cassette boundary from shared plan stations."""

    tolerance = 1.0e-6
    if abs(station_mm) <= tolerance or abs(station_mm - float(run_plan.length_mm)) <= tolerance:
        return "outer_end"
    if any(
        abs(station_mm - float(crown)) <= tolerance
        for crown in run_plan.crown_seam_stations_local_mm
    ):
        return "fixed_crown"
    if any(
        abs(station_mm - float(pier)) <= tolerance
        for pier in run_plan.pier_seam_stations_local_mm
    ):
        return "floating_supported_pier"
    raise ValueError(
        f"{run_plan.run_id}: boundary {station_mm:.6f} mm is not an outer, crown, or pier station"
    )


def bottom_access_half_receiver_cutter(
    *,
    side: str,
    face_x_mm: float,
    engagement_mm: float,
    movement_extension_mm: float,
    axial_fit_clearance_mm: float,
    head_height_mm: float,
    neck_height_mm: float,
    band_center_y_mm: float,
    band_depth_mm: float,
    transverse_clearance_mm: float,
    vertical_clearance_mm: float,
) -> tuple[trimesh.Trimesh, dict[str, float]]:
    """Create one cassette-side, bottom-access Dutchman receiver cutter.

    The key enters from the open bottom.  Its flat lower edge and tapered upper
    shoulder carry longitudinal separation into a broad PETG bearing face.
    ``movement_extension_mm`` is zero at fixed crowns and half of the total
    qualified travel reserve at each side of a floating pier seam.
    """

    if side not in {"left", "right"}:
        raise ValueError(f"Receiver side must be left or right; got {side!r}")
    direction = 1.0 if side == "left" else -1.0
    length = (
        positive(engagement_mm, "receiver engagement")
        + max(0.0, float(movement_extension_mm))
        + max(0.0, float(axial_fit_clearance_mm))
    )
    head = positive(head_height_mm, "receiver head height") + max(
        0.0, float(vertical_clearance_mm)
    )
    neck = positive(neck_height_mm, "receiver neck height") + max(
        0.0, float(vertical_clearance_mm)
    )
    if neck >= head:
        raise ValueError("Receiver neck must remain lower than its head shoulder")
    outside = 0.3
    # The authored key is a symmetric full bowtie: each half receiver starts
    # at the center neck, and its taper begins at 28% of the half-span
    # (1 - 2 * the source profile's 0.36 shoulder fraction).  Using 64%
    # leaves a real wedge of parent material in the insertion path even
    # though the nominal head/neck dimensions match.
    shoulder_u = length * 0.28

    def point(u: float, z: float) -> tuple[float, float]:
        return (face_x_mm + direction * u, z)

    profile = Polygon(
        [
            point(-outside, -0.2),
            point(length, -0.2),
            point(length, head),
            point(shoulder_u, neck),
            point(0.0, neck),
        ]
    )
    cutter_depth = positive(band_depth_mm, "receiver band depth") + 2.0 * max(
        0.0, float(transverse_clearance_mm)
    )
    y0 = float(band_center_y_mm) - cutter_depth / 2.0
    cutter = extrude_xz_profile_along_y(profile, y0=y0, depth=cutter_depth)
    return cutter, {
        "engagement_mm": engagement_mm,
        "movement_extension_this_half_mm": movement_extension_mm,
        "axial_fit_clearance_this_half_mm": axial_fit_clearance_mm,
        "receiver_length_from_seam_face_mm": length,
        "head_height_with_vertical_clearance_mm": head,
        "neck_height_with_vertical_clearance_mm": neck,
        "band_center_from_rear_mm": band_center_y_mm,
        "band_depth_with_transverse_clearance_mm": cutter_depth,
    }


def front_insert_half_receiver_cutter(
    *,
    side: str,
    face_x_mm: float,
    engagement_mm: float,
    axial_fit_clearance_mm: float,
    head_height_mm: float,
    neck_height_mm: float,
    q_envelope_mm: tuple[float, float],
    vertical_clearance_per_face_mm: float,
) -> tuple[trimesh.Trimesh, dict[str, float]]:
    """Create one front-open half of the fixed crown entablature tie seat."""

    if side not in {"left", "right"}:
        raise ValueError("Front-inserted receiver side must be left or right")
    direction = 1.0 if side == "left" else -1.0
    length = positive(engagement_mm, "front-tie engagement") + max(
        0.0, axial_fit_clearance_mm
    )
    vertical_clearance = max(0.0, vertical_clearance_per_face_mm)
    head = positive(head_height_mm, "front-tie head") + 2.0 * vertical_clearance
    neck = positive(neck_height_mm, "front-tie neck") + 2.0 * vertical_clearance
    if neck >= head:
        raise ValueError("Front-tie neck must remain below its broad head")
    # Match the same centered full-bowtie profile used by the removable key.
    # Its 0.36 full-span shoulder becomes 0.28 of each half receiver.
    shoulder_u = length * 0.28

    def point(u: float, z: float) -> tuple[float, float]:
        return face_x_mm + direction * u, z

    profile = Polygon(
        [
            point(-0.2, 0.0),
            point(length, 0.0),
            point(length, head),
            point(shoulder_u, neck),
            point(0.0, neck),
        ]
    )
    q0, q1 = q_envelope_mm
    if q1 <= q0:
        raise ValueError("Front-tie receiver q envelope is empty")
    cutter = extrude_xz_profile_along_y(
        profile,
        y0=q0,
        depth=q1 - q0 + 0.2,
    )
    return cutter, {
        "engagement_mm": engagement_mm,
        "axial_fit_clearance_this_half_mm": axial_fit_clearance_mm,
        "receiver_length_from_seam_face_mm": length,
        "head_height_with_vertical_clearance_mm": head,
        "neck_height_with_vertical_clearance_mm": neck,
        "front_open_q_min_mm": q0,
        "front_open_q_max_mm": q1,
        "front_overcut_mm": 0.2,
    }


def clipped_landing_block(
    *,
    part_width_mm: float,
    part_depth_mm: float,
    center_x_mm: float,
    width_x_mm: float,
    center_y_mm: float,
    depth_y_mm: float,
    height_mm: float,
) -> trimesh.Trimesh | None:
    """Full-height receiver/locator land clipped to exact cassette width."""

    x0 = max(0.0, center_x_mm - width_x_mm / 2.0)
    x1 = min(part_width_mm, center_x_mm + width_x_mm / 2.0)
    y0 = max(0.0, center_y_mm - depth_y_mm / 2.0)
    y1 = min(part_depth_mm, center_y_mm + depth_y_mm / 2.0)
    if x1 - x0 <= 1.0e-6 or y1 - y0 <= 1.0e-6:
        return None
    return cuboid((x1 - x0, y1 - y0, height_mm), origin=(x0, y0, 0.0))


def saddle_locator_spec(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return one config-derived saddle-ridge and cassette-pocket interface.

    The r6 schema deliberately avoids an independently invented saddle pitch.
    The two ridge centers therefore bisect the two clear gaps between the three
    configured diaphragm bands.  Width, height, and clearance all come from
    existing structural fields.
    """

    diaphragm = deep_get(cfg, "joinery.diaphragm_bowtie", {})
    if not isinstance(diaphragm, dict):
        raise ValueError("joinery.diaphragm_bowtie is required for saddle locators")
    centers = tuple(float(value) for value in diaphragm.get("centers_from_rear_mm", []))
    band_depth = float(diaphragm.get("depth_mm", 0.0))
    if len(centers) != 3 or band_depth <= 0.0:
        raise ValueError("Three positive-depth diaphragm bands are required")
    ridge_centers = tuple(
        (centers[index] + centers[index + 1]) / 2.0 for index in range(2)
    )
    thermal = saddle_thermal_contract(cfg)
    ridge_width = float(thermal.ridge_width_mm)
    configured_ridge_width = number(
        cfg, "structure.stitch_rail_locator_ridge_width_mm", ridge_width
    )
    if abs(configured_ridge_width - ridge_width) > 1.0e-7:
        raise ValueError("Saddle locator ridge width drifts across config contracts")
    # The locator is a dedicated 10.0 mm q-depth feature.  It must not inherit
    # the unrelated 14 mm structural-arch radial thickness: doing so enlarges
    # the cassette access pocket to 14.4 mm and destroys the frozen 3.2 mm
    # minimum ligament beside the first diaphragm receiver.
    ridge_depth = float(thermal.ridge_depth_mm)
    ridge_height = number(cfg, "structure.cassette_rail_saddle_depth_mm", 7.0)
    clearance = number(cfg, "structure.cassette_rail_saddle_clearance_mm", 0.4)
    return {
        "ridge_width_along_run_mm": ridge_width,
        "ridge_depth_along_shelf_mm": ridge_depth,
        "ridge_height_mm": ridge_height,
        "clearance_total_mm": clearance,
        "pocket_width_along_run_mm": float(thermal.terminal_pocket_width_mm),
        "terminal_or_fixed_pocket_width_along_run_mm": float(
            thermal.terminal_pocket_width_mm
        ),
        "floating_pocket_width_along_run_mm": float(
            thermal.floating_pocket_width_mm
        ),
        "floating_total_axial_travel_mm": float(thermal.total_axial_travel_mm),
        "internal_pier_fixed_side": str(thermal.fixed_side),
        "internal_pier_floating_side": str(thermal.floating_side),
        "pocket_depth_along_shelf_mm": float(thermal.pocket_depth_mm),
        "pocket_vertical_depth_mm": ridge_height + clearance,
        "centers_from_rear_mm": ridge_centers,
        "coordinate_derivation": "midpoints of the two clear gaps between the three configured diaphragm bands",
    }


def cassette_final_x_receiver_cutters(
    cfg: dict[str, Any],
    *,
    instance_plan: Any,
    part_width_mm: float,
    part_depth_mm: float,
) -> tuple[list[trimesh.Trimesh], list[trimesh.Trimesh], dict[str, Any]]:
    """Two final-coordinate receivers, bayonet bosses, and service paths."""

    joint = deep_get(cfg, "tied_arcade.cassette_final_x_vertical_tenon_joint", {})
    bridge = deep_get(cfg, "tied_arcade.rear_crown_bridge", {})
    front_joint = deep_get(cfg, "joinery.front_entablature_joint", {})
    wedge_cfg = deep_get(cfg, "tied_arcade.retention_wedge", {})
    if not all(isinstance(value, dict) for value in (joint, bridge, front_joint, wedge_cfg)):
        raise ValueError("Final-X cassette receiver configuration is incomplete")
    run_centers = deep_get(
        cfg,
        f"tied_arcade.cassette_final_x_vertical_tenon_joint.run_centers_mm.{instance_plan.run_id}",
        None,
    )
    if not isinstance(run_centers, dict):
        raise ValueError(f"No final-X tenon centers for {instance_plan.run_id}")
    centers_u = tuple(float(value) for value in run_centers["final_u_centers_mm"])
    entry_u = tuple(float(value) for value in run_centers["entry_u_centers_mm"])
    if len(centers_u) < 2 or centers_u != entry_u:
        raise ValueError(
            "Final-X requires at least two tenons with identical entry/final U centers"
        )

    tenon_width = float(joint["tenon_run_width_mm"])
    receiver_width = float(joint["receiver_run_width_mm"])
    receiver_depth = float(joint["receiver_depth_mm"])
    tenon_height = float(joint["tenon_engagement_height_mm"])
    roof = float(joint["receiver_roof_above_tenon_mm"])
    wedge_run, wedge_vertical = (
        float(value) for value in wedge_cfg["through_hole_run_y_mm"]
    )
    cassette_height = number(cfg, "structure.cassette_total_height_mm", 30.0)
    cassette_global_bottom = number(cfg, "tied_arcade.cassette_entablature_bottom_y_mm", 138.0)
    wedge_center_local_z = float(joint["retention_wedge_center_y_mm"]) - cassette_global_bottom
    minimum_run_ligament = float(joint["minimum_tenon_clear_ligament_run_mm"])
    minimum_vertical_ligament = float(joint["minimum_tenon_clear_ligament_y_mm"])
    access = structural_cross_key_service_access_mm(cfg)
    bridge_half = max(abs(float(value)) for value in bridge["final_u_envelope_from_crown_mm"])
    bridge_body_q = tuple(
        float(value) for value in bridge["bridge_body_q_envelope_mm"]
    )
    bridge_rails = bridge["dovetail_rails"]
    if not isinstance(bridge_rails, dict):
        raise ValueError("Rear crown bridge dovetail contract is incomplete")
    front_center_q = float(front_joint.get("center_from_rear_mm", part_depth_mm - 9.0))
    front_zone = deep_get(
        cfg,
        "structure.front_entablature_tie_zone_from_rear_mm",
        [part_depth_mm - 18.0, part_depth_mm],
    )
    if not isinstance(front_zone, list) or len(front_zone) != 2:
        raise ValueError("Front chord zone is required for final-X wedge access")

    if abs((tenon_width - wedge_run) / 2.0 - minimum_run_ligament) > 1.0e-7:
        raise ValueError("Configured top-tenon wedge does not preserve the exact 7 mm run ligament")
    if abs((tenon_height - wedge_vertical) / 2.0 - minimum_vertical_ligament) > 1.0e-7:
        raise ValueError("Configured top-tenon wedge does not preserve the exact 9 mm vertical ligament")
    if abs(tenon_height + roof - cassette_height) > 1.0e-7:
        raise ValueError("Top-tenon engagement plus receiver roof must equal cassette height")
    configured_receiver_web = float(run_centers["minimum_receiver_web_between_mm"])
    actual_receiver_web = min(
        right - left - receiver_width
        for left, right in zip(centers_u, centers_u[1:])
    )
    if abs(actual_receiver_web - configured_receiver_web) > 1.0e-7:
        raise ValueError("Top-receiver center spacing drifts from its exact web")
    if actual_receiver_web < number(cfg, "joinery.minimum_wall_mm", 3.2) - 1.0e-7:
        raise ValueError("Adjacent top receivers violate the minimum structural web")
    crown_clearance = centers_u[0] - receiver_width / 2.0 - bridge_half
    if crown_clearance < -1.0e-7:
        raise ValueError("First top receiver enters the crown-bridge U envelope")
    top_receiver_depth = (
        front_center_q - receiver_depth / 2.0,
        front_center_q + receiver_depth / 2.0,
    )
    body_q_clearance = top_receiver_depth[0] - bridge_body_q[1]
    keyway_centers = tuple(
        float(value) for value in bridge_rails["u_centers_from_crown_mm"]
    )
    keyway_outer_u = max(keyway_centers) + float(
        bridge_rails["keyway_head_width_along_u_mm"]
    ) / 2.0
    keyway_u_clearance = centers_u[0] - receiver_width / 2.0 - keyway_outer_u
    if body_q_clearance < -1.0e-7 or keyway_u_clearance < -1.0e-7:
        raise ValueError("Top receiver does not clear the crown body/keyway in 3D")

    spring_side = str(instance_plan.spring_side)
    if spring_side not in {"left", "right"}:
        raise ValueError(f"Unexpected spring side {spring_side!r}")
    cutters: list[trimesh.Trimesh] = []
    receiver_bosses: list[trimesh.Trimesh] = []
    records: list[dict[str, Any]] = []
    local_boss, local_boss_cutters, cross_key_metrics = (
        positive_cross_key_receiver_local_geometry(cfg)
    )
    for index, center_u in enumerate(centers_u, start=1):
        center_x = (
            part_width_mm - center_u if spring_side == "left" else center_u
        )
        if center_x - receiver_width / 2.0 < -1.0e-7 or center_x + receiver_width / 2.0 > part_width_mm + 1.0e-7:
            raise ValueError(f"{instance_plan.logical_id}: top receiver {index} leaves cassette")
        cutters.append(
            cuboid(
                (receiver_width, receiver_depth, tenon_height + 0.2),
                origin=(
                    center_x - receiver_width / 2.0,
                    front_center_q - receiver_depth / 2.0,
                    -0.2,
                ),
            )
        )
        receiver_from_key_local = np.asarray(
            [
                [1.0, 0.0, 0.0, center_x],
                [0.0, 0.0, -1.0, part_depth_mm],
                [0.0, 1.0, 0.0, wedge_center_local_z],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        boss_parent = local_boss.copy()
        boss_parent.apply_transform(receiver_from_key_local)
        receiver_bosses.append(clean_mesh_preserve_coordinates(boss_parent))
        for local_cutter in local_boss_cutters:
            cutter_parent = local_cutter.copy()
            cutter_parent.apply_transform(receiver_from_key_local)
            cutters.append(clean_mesh_preserve_coordinates(cutter_parent))
        records.append(
            {
                "index": index,
                "u_from_crownward_physical_face_mm": center_u,
                "entry_u_from_crownward_physical_face_mm": entry_u[index - 1],
                "x_relative_to_saved_handed_cassette_mm": round(center_x, 6),
                "receiver_run_width_mm": receiver_width,
                "receiver_depth_mm": receiver_depth,
                "open_bottom_engagement_height_mm": tenon_height,
                "roof_above_receiver_mm": roof,
                "wedge_mortise_run_vertical_mm": [wedge_run, wedge_vertical],
                "wedge_axis": str(joint["retention_wedge_axis"]),
                "positive_cross_key_receiver": dict(cross_key_metrics),
                "positive_cross_key_parent_transform_row_major": (
                    receiver_from_key_local.tolist()
                ),
                "minimum_straight_service_access_mm": access,
            }
        )

    return cutters, receiver_bosses, {
        "installation_motion": str(joint["installation_motion"]),
        "whole_half_longitudinal_travel_mm": float(joint["whole_half_longitudinal_travel_mm"]),
        "receiver_count": len(records),
        "wedge_access_path_count": len(records),
        "positive_cross_key_receiver_boss_count": len(receiver_bosses),
        "positive_cross_key_receiver_bosses_integral": True,
        "receivers": records,
        "tenon_run_ligament_each_side_of_4mm_wedge_mm": minimum_run_ligament,
        "tenon_vertical_ligament_above_below_4mm_wedge_mm": minimum_vertical_ligament,
        "minimum_crown_bridge_u_clearance_mm": round(crown_clearance, 6),
        "top_receiver_global_depth_envelope_mm": list(top_receiver_depth),
        "crown_bridge_body_q_envelope_mm": list(bridge_body_q),
        "minimum_crown_bridge_body_q_clearance_mm": round(body_q_clearance, 6),
        "minimum_crown_keyway_u_clearance_mm": round(keyway_u_clearance, 6),
        "crown_keyway_q_overlaps_top_receiver_q": True,
        "crown_keyway_and_top_receiver_are_separated_in_u": True,
        "crown_bridge_depth_collision": False,
        "minimum_straight_service_access_mm": access,
    }


def cassette_upper_x_cradle_cutter(
    cfg: dict[str, Any],
    *,
    support_local_x_mm: float,
    part_width_mm: float,
    cassette_height_mm: float,
    top_skin_mm: float,
) -> tuple[trimesh.Trimesh, dict[str, Any], Polygon]:
    """Return the exact open-bottom cradle for the buffered upper X chord.

    The source X is a 12 mm Euclidean buffer around the audited descending
    3:4:5 centerline.  At a fixed rear/front coordinate that buffer has a
    7.5 mm vertical half-height.  The configured 0.4 mm cradle allowance is a
    horizontal q clearance, so translating the upper boundary toward the
    shelf front by 0.4 mm produces the frozen q=25.383333 underside exit.
    Filling vertically down from that boundary creates a genuinely
    open-bottom receiver rather than a trapped diagonal tunnel.
    """

    corbel = deep_get(cfg, "corbel", {})
    cradle = deep_get(cfg, "corbel.upper_diagonal_cassette_union_segment_mm", {})
    nodes = deep_get(cfg, "corbel.x_brace_nodes_mm", {})
    if not all(isinstance(value, dict) for value in (corbel, cradle, nodes)):
        raise ValueError("Upper-X cradle configuration is incomplete")
    wall_upper = tuple(float(value) for value in nodes["wall_upper"])
    front_spring = tuple(float(value) for value in nodes["front_spring"])
    dx = front_spring[0] - wall_upper[0]
    de = front_spring[1] - wall_upper[1]
    centerline_length = math.hypot(dx, de)
    if min(dx, centerline_length) <= 0.0:
        raise ValueError("Upper-X centerline must advance toward the shelf front")
    slope = de / dx
    brace_radius = float(cradle["brace_radius_mm"])
    fit_q = float(cradle["cradle_fit_clearance_mm"])
    q_max = float(cradle["maximum_local_q_from_rear_mm"])
    cassette_underside = number(
        cfg, "tied_arcade.cassette_entablature_bottom_y_mm", 138.0
    )
    back_clearance = float(cfg["closet"]["runs"][0]["reference_shelf_back_clearance_in"]) * 25.4
    center_e_at_rear = wall_upper[1] + slope * back_clearance
    vertical_half_at_fixed_q = brace_radius / (dx / centerline_length)
    actual_upper_local_e_at_rear = (
        center_e_at_rear + vertical_half_at_fixed_q - cassette_underside
    )
    cutter_upper_local_e_at_rear = actual_upper_local_e_at_rear - slope * fit_q
    derived_q_max = cutter_upper_local_e_at_rear / -slope
    if abs(derived_q_max - q_max) > 1.0e-6:
        raise ValueError(
            "Configured upper-X cradle q maximum does not match the buffered "
            f"3:4:5 chord ({derived_q_max:.9f} != {q_max:.9f})"
        )

    clear_run_width = float(corbel["body_thickness_mm"]) + 2.0 * fit_q
    x0 = max(0.0, support_local_x_mm - clear_run_width / 2.0)
    x1 = min(part_width_mm, support_local_x_mm + clear_run_width / 2.0)
    if x1 - x0 <= 1.0e-7:
        raise ValueError("Upper-X cradle misses its position-specific cassette")
    cutter_floor = -0.2
    rear_overcut = 0.2
    profile = Polygon(
        [
            (-rear_overcut, cutter_floor),
            (-rear_overcut, cutter_upper_local_e_at_rear - slope * rear_overcut),
            (0.0, cutter_upper_local_e_at_rear),
            (q_max, 0.0),
            (q_max, cutter_floor),
        ]
    )
    cutter = extrude_yz_profile_along_x(profile, x0=x0, width=x1 - x0)
    minimum_top_solid = cassette_height_mm - cutter_upper_local_e_at_rear
    required_top_clearance = float(cradle["minimum_top_skin_clearance_mm"])
    if minimum_top_solid < required_top_clearance - 1.0e-7:
        raise ValueError("Upper-X cradle violates its configured top-skin clearance")
    if cutter_upper_local_e_at_rear >= cassette_height_mm - top_skin_mm - 1.0e-7:
        raise ValueError("Upper-X cradle cuts the continuous cassette top skin")

    minimum_wall = number(cfg, "joinery.minimum_wall_mm", 3.2)
    protected_land = shapely_box(
        max(0.0, x0 - minimum_wall),
        0.0,
        min(part_width_mm, x1 + minimum_wall),
        q_max + minimum_wall,
    )
    metrics = {
        "generated": True,
        "open_bottom": True,
        "support_center_relative_to_physical_part_mm": support_local_x_mm,
        "run_interval_relative_to_physical_part_mm": [x0, x1],
        "clear_run_width_before_part_clipping_mm": clear_run_width,
        "maximum_q_from_rear_mm": q_max,
        "buffered_chord_actual_q_at_underside_mm": float(
            cradle["outer_solid_maximum_local_q_at_cassette_underside_mm"]
        ),
        "fit_clearance_in_q_mm": fit_q,
        "maximum_local_e_at_rear_mm": cutter_upper_local_e_at_rear,
        "minimum_solid_to_top_surface_mm": minimum_top_solid,
        "configured_minimum_top_skin_clearance_mm": required_top_clearance,
        "continuous_top_skin_cut": False,
        "coordinate_derivation": (
            "exact 12 mm buffered 3:4:5 upper diagonal, translated +0.4 mm "
            "in q and vertically opened to the cassette underside"
        ),
    }
    return cutter, metrics, protected_land


def cassette_integrated_cap_lock_cutters(
    cfg: dict[str, Any],
    *,
    support_local_x_mm: float,
    support_side: str,
    position_index: int,
    position_count: int,
    part_width_mm: float,
    part_depth_mm: float,
) -> tuple[list[trimesh.Trimesh], list[dict[str, Any]], list[Polygon]]:
    """Cut the exact terminal/fixed/floating integral-cap lock receivers."""

    contract = integrated_cap_lock_contract(cfg)
    corbel = cfg["corbel"]
    lock = corbel["integrated_cap_cassette_lock"]
    if not isinstance(lock, dict):
        raise ValueError("Integral-cap lock configuration is incomplete")
    thermal_travel = float(corbel["floating_pier_total_axial_travel_mm"])
    lock_travel = float(corbel["floating_pier_lock_slot_total_axial_travel_mm"])
    if abs(lock_travel - thermal_travel) > 1.0e-7:
        raise ValueError(
            "Cassette lock travel must equal the authoritative floating-pier travel"
        )
    receiver_e = tuple(float(value) for value in lock["cassette_receiver_y_envelope_mm"])
    shoulder_e = tuple(float(value) for value in lock["tail_capture_shoulder_y_envelope_mm"])
    cassette_bottom_e = number(
        cfg, "tied_arcade.cassette_entablature_bottom_y_mm", 138.0
    )
    receiver_z = (receiver_e[0] - cassette_bottom_e, receiver_e[1] - cassette_bottom_e)
    shoulder_z = (shoulder_e[0] - cassette_bottom_e, shoulder_e[1] - cassette_bottom_e)
    if receiver_z[0] != 0.0 or abs(shoulder_z[1] - receiver_z[1]) > 1.0e-7:
        raise ValueError("Cassette-lock receiver/shoulder stack is not bottom-referenced")

    cornerward_center = tuple(
        float(value) for value in contract["cornerward_center_s_q_mm"]
    )
    outboard_center = tuple(
        float(value) for value in contract["outboard_center_s_q_mm"]
    )
    tight_dims = tuple(float(value) for value in contract["tight_receiver_run_q_mm"])
    floating_dims = tuple(
        float(value) for value in contract["floating_receiver_run_q_mm"]
    )
    if position_index == 0:
        owned = (
            ("run_start_cornerward_tight", cornerward_center, tight_dims, False),
            ("run_start_outboard_tight", outboard_center, tight_dims, False),
        )
    elif position_index == position_count - 1:
        owned = (
            ("run_end_cornerward_floating", cornerward_center, floating_dims, True),
            ("run_end_outboard_floating", outboard_center, floating_dims, True),
        )
    elif support_side == "right":
        owned = (
            (
                "internal_previous_cornerward_floating",
                cornerward_center,
                floating_dims,
                True,
            ),
        )
    elif support_side == "left":
        owned = (
            (
                "internal_next_outboard_tight",
                outboard_center,
                tight_dims,
                False,
            ),
        )
    else:
        raise ValueError(f"Unknown support side {support_side!r} for cap locks")

    shank_run, shank_q = (float(value) for value in lock["square_shank_run_q_mm"])
    # The split tail flexes in q, never in the thermally elongated run axis.
    # Its 0.8 mm catch projection per q face and 0.2 mm chamber clearance per
    # face are derived from the frozen 0.4 mm fit increment.  These are
    # retention-only prototype features and remain coupon-gated.
    tail_expanded_q = shank_q + 4.0 * 0.4
    chamber_q = tail_expanded_q + 0.4
    chamber_height = number(cfg, "joinery.minimum_wall_mm", 3.2)
    chamber_z = (receiver_z[1], receiver_z[1] + chamber_height)
    minimum_wall = number(cfg, "joinery.minimum_wall_mm", 3.2)
    cutters: list[trimesh.Trimesh] = []
    records: list[dict[str, Any]] = []
    protected_lands: list[Polygon] = []
    for role, center, receiver_dims, floating in owned:
        center_x = support_local_x_mm + center[0]
        center_q = center[1]
        receiver_run, receiver_q = receiver_dims
        if (
            center_x - receiver_run / 2.0 < -1.0e-7
            or center_x + receiver_run / 2.0 > part_width_mm + 1.0e-7
            or center_q - chamber_q / 2.0 < -1.0e-7
            or center_q + chamber_q / 2.0 > part_depth_mm + 1.0e-7
        ):
            raise ValueError("Position-specific cassette lock receiver leaves its part")
        cutters.extend(
            [
                cuboid(
                    (receiver_run, receiver_q, receiver_z[1] + 0.2),
                    origin=(
                        center_x - receiver_run / 2.0,
                        center_q - receiver_q / 2.0,
                        -0.2,
                    ),
                ),
                cuboid(
                    (receiver_run, chamber_q, chamber_z[1] - chamber_z[0]),
                    origin=(
                        center_x - receiver_run / 2.0,
                        center_q - chamber_q / 2.0,
                        chamber_z[0],
                    ),
                ),
            ]
        )
        protected_lands.append(
            shapely_box(
                center_x - receiver_run / 2.0 - minimum_wall,
                center_q - chamber_q / 2.0 - minimum_wall,
                center_x + receiver_run / 2.0 + minimum_wall,
                center_q + chamber_q / 2.0 + minimum_wall,
            ).intersection(
                shapely_box(0.0, 0.0, part_width_mm, part_depth_mm)
            )
        )
        records.append(
            {
                "ownership": role,
                "center_x_relative_to_physical_part_mm": center_x,
                "center_s_from_support_mm": center[0],
                "center_q_from_rear_mm": center_q,
                "receiver_run_q_mm": [receiver_run, receiver_q],
                "receiver_local_z_envelope_mm": [round(value, 6) for value in receiver_z],
                "tail_capture_shoulder_local_z_envelope_mm": [
                    round(value, 6) for value in shoulder_z
                ],
                "tail_expansion_chamber_run_q_mm": [receiver_run, chamber_q],
                "tail_expansion_chamber_local_z_envelope_mm": [
                    round(value, 6) for value in chamber_z
                ],
                "floating_total_axial_travel_mm": (
                    lock_travel if floating else 0.0
                ),
                "open_bottom_insertion": True,
                "positive_tail_capture_modeled": True,
                "retention_credit": "zero",
            }
        )
    return cutters, records, protected_lands


def cassette_chassis_for_position(
    cfg: dict[str, Any],
    *,
    run_plan: Any,
    instance_plan: Any,
) -> PrototypePart:
    """Build one exact position-specific half-bay chassis."""

    physical_widths = tuple(float(value) for value in run_plan.cassette_physical_widths_mm)
    count = len(physical_widths)
    position_index = int(instance_plan.index)
    if not 0 <= position_index < count:
        raise ValueError(f"{run_plan.run_id}: invalid cassette position {position_index}")

    nominal_left = float(instance_plan.nominal_start_local_mm)
    nominal_right = float(instance_plan.nominal_end_local_mm)
    physical_left = float(instance_plan.physical_start_local_mm)
    physical_right = float(instance_plan.physical_end_local_mm)
    width = float(instance_plan.physical_width_mm)
    expected_width = physical_widths[position_index]
    if abs(width - expected_width) > 1.0e-7:
        raise ValueError(
            f"{run_plan.run_id} cassette {position_index + 1}: physical width "
            f"{width:.7f} != plan {expected_width:.7f}"
        )

    release_to_generator_class = {
        "free_run_start": "outer_end",
        "free_run_end": "outer_end",
        "fixed_crown": "fixed_crown",
        "floating_supported_pier": "floating_supported_pier",
    }
    left_class = release_to_generator_class[str(instance_plan.left_joint_class)]
    right_class = release_to_generator_class[str(instance_plan.right_joint_class)]
    if left_class != cassette_seam_class(run_plan, nominal_left):
        raise ValueError(f"{instance_plan.logical_id}: left seam-class mismatch")
    if right_class != cassette_seam_class(run_plan, nominal_right):
        raise ValueError(f"{instance_plan.logical_id}: right seam-class mismatch")

    support_station = float(instance_plan.support_center_local_mm)
    support_matches = [
        (index, float(station))
        for index, station in enumerate(run_plan.support_centers_local_mm)
        if abs(float(station) - support_station) <= 1.0e-7
    ]
    if len(support_matches) != 1:
        raise ValueError(f"{instance_plan.logical_id}: release support does not match one plan support")
    support_index, _support_station_check = support_matches[0]
    support_local = float(instance_plan.support_offset_from_physical_left_mm)
    if abs(support_local - (support_station - physical_left)) > 1.0e-7:
        raise ValueError(f"{instance_plan.logical_id}: physical support offset drift")
    if abs(support_station - nominal_left) <= 1.0e-7:
        support_relation = "left_supported_pier_seam"
        support_side = "left"
    elif abs(support_station - nominal_right) <= 1.0e-7:
        support_relation = "right_supported_pier_seam"
        support_side = "right"
    else:
        support_relation = "interior_end_pier_station"
        support_side = "interior"

    height = number(cfg, "structure.cassette_total_height_mm", 30.0)
    cassette_bottom_e = number(
        cfg, "tied_arcade.cassette_entablature_bottom_y_mm", 138.0
    )
    top_skin = number(cfg, "structure.cassette_top_skin_mm", 3.2)
    bottom_skin = number(cfg, "structure.cassette_bottom_skin_mm", 3.2)
    bottom_land = max(
        number(cfg, "structure.cassette_internal_rib_mm", 3.2),
        number(cfg, "joinery.minimum_wall_mm", 3.2),
    )
    perimeter = number(cfg, "structure.cassette_perimeter_wall_mm", 4.8)
    maximum_clear = number(cfg, "structure.cassette_maximum_clear_bridge_mm", 14.0)
    depth_cells = int(number(cfg, "structure.cassette_depth_cell_count", 9.0))
    depth = number(cfg, "closet.shelf_depth_in", 6.0) * 25.4
    rear_chord_depth = number(cfg, "structure.stitch_rail_depth_mm", 18.0)
    tie_zone = deep_get(
        cfg,
        "structure.front_entablature_tie_zone_from_rear_mm",
        [depth - 18.0, depth],
    )
    if not isinstance(tie_zone, list) or len(tie_zone) != 2:
        raise ValueError("structure.front_entablature_tie_zone_from_rear_mm must have two values")
    front_chord_start = float(tie_zone[0])
    front_chord_end = float(tie_zone[1])
    if abs(front_chord_end - depth) > 1.0e-6:
        raise ValueError("Front entablature chord must terminate at the cassette front edge")
    if not (
        0.0 < top_skin < height
        and 0.0 < bottom_skin < height
        and top_skin + bottom_skin < height
        and 0.0 < rear_chord_depth < front_chord_start < front_chord_end
        and width > 2.0 * perimeter
    ):
        raise ValueError("Cassette chassis dimensions leave no valid coffer field")
    inner_width = width - 2.0 * perimeter
    x_cells = max(1, math.ceil((inner_width + bottom_land) / (maximum_clear + bottom_land)))
    clear_x = (inner_width - (x_cells - 1) * bottom_land) / x_cells
    central_depth = front_chord_start - rear_chord_depth
    clear_y = (central_depth - (depth_cells - 1) * bottom_land) / depth_cells
    if min(clear_x, clear_y) <= 0.0 or max(clear_x, clear_y) > maximum_clear + 1.0e-6:
        raise ValueError(
            f"{run_plan.run_id} cassette {position_index + 1}: invalid coffer clear spans "
            f"{clear_x:.4f}/{clear_y:.4f} mm"
        )

    # Author the coffer as voids cut from one exact outer solid.  This avoids
    # overlapping-shell artifacts from attempting to union two skins and many
    # intersecting ribs.  The uncut material is exactly the two skins, full
    # front/rear chords, perimeter, transverse ribs, and receiver lands.
    blank_body = cuboid((width, depth, height), origin=(0.0, 0.0, 0.0))
    x_clear_intervals: list[tuple[float, float]] = []
    cursor = perimeter
    for cell_index in range(x_cells):
        x_clear_intervals.append((cursor, cursor + clear_x))
        cursor += clear_x
        if cell_index + 1 < x_cells:
            cursor += bottom_land
    y_clear_intervals: list[tuple[float, float]] = []
    cursor = rear_chord_depth
    for cell_index in range(depth_cells):
        y_clear_intervals.append((cursor, cursor + clear_y))
        cursor += clear_y
        if cell_index + 1 < depth_cells:
            cursor += bottom_land
    if abs(x_clear_intervals[-1][1] - (width - perimeter)) > 1.0e-6:
        raise ValueError("Cassette X coffer intervals do not terminate at the perimeter")
    if abs(y_clear_intervals[-1][1] - front_chord_start) > 1.0e-6:
        raise ValueError("Cassette Y coffer intervals do not terminate at the front chord")
    coffer_cell_plans = [
        shapely_box(x0, y0, x1, y1)
        for x0, x1 in x_clear_intervals
        for y0, y1 in y_clear_intervals
    ]
    landing_plan_shapes: list[Any] = []

    fit_clearance = number(cfg, "joinery.nominal_fit_clearance_mm", 0.35)
    axial_fit_half = fit_clearance / 2.0
    # The deleted floating front-key family is not a thermal datum.  Every
    # active cassette seam receiver consumes the same required, config-owned
    # corbel movement contract used by the cap locators and lock slots.
    travel_total = float(saddle_thermal_contract(cfg).total_axial_travel_mm)
    minimum_wall = number(cfg, "joinery.minimum_wall_mm", 3.2)
    diaphragm = deep_get(cfg, "joinery.diaphragm_bowtie", {})
    front_joint = deep_get(cfg, "joinery.front_entablature_joint", {})
    if not isinstance(diaphragm, dict) or not isinstance(front_joint, dict):
        raise ValueError("Cassette receiver geometry requires both joinery objects")
    diaphragm_centers = [float(value) for value in diaphragm.get("centers_from_rear_mm", [])]
    if len(diaphragm_centers) != 3:
        raise ValueError("Each structural cassette seam requires exactly three diaphragm receivers")
    front_center = float(front_joint.get("center_from_rear_mm", 143.4))
    cutters: list[trimesh.Trimesh] = []
    receiver_records: list[dict[str, Any]] = []
    underside_access_records: list[dict[str, Any]] = []
    front_receiver_cutter_indices: dict[str, int] = {}

    def record_underside_access(
        *,
        category: str,
        x_interval_mm: tuple[float, float],
        y_interval_mm: tuple[float, float],
        source: str,
    ) -> None:
        x0 = max(0.0, float(x_interval_mm[0]))
        x1 = min(width, float(x_interval_mm[1]))
        y0 = max(0.0, float(y_interval_mm[0]))
        y1 = min(depth, float(y_interval_mm[1]))
        if x1 <= x0 or y1 <= y0:
            raise ValueError(f"{instance_plan.logical_id}: empty underside access opening")
        underside_access_records.append(
            {
                "category": category,
                "x_interval_mm": [round(x0, 6), round(x1, 6)],
                "y_interval_from_rear_mm": [round(y0, 6), round(y1, 6)],
                "source": source,
                "cuts_through_configured_bottom_skin": True,
            }
        )

    def add_receiver_side(side: str, seam_class: str) -> None:
        if seam_class == "outer_end":
            return
        if seam_class not in {"fixed_crown", "floating_supported_pier"}:
            raise ValueError(f"Unsupported seam class {seam_class!r}")
        face_x = 0.0 if side == "left" else width
        movement_half = travel_total / 2.0 if seam_class == "floating_supported_pier" else 0.0
        role = (
            "tight_fixed_local_crown"
            if seam_class == "fixed_crown"
            else "axially_elongated_alignment_only_no_tension_credit"
        )
        side_pockets: list[dict[str, Any]] = []
        for pocket_index, center_y in enumerate(diaphragm_centers, start=1):
            engagement = float(diaphragm.get("engagement_each_side_mm", 24.0))
            band_depth = float(diaphragm.get("depth_mm", 20.0))
            head = float(diaphragm.get("head_width_mm", 14.0))
            neck = float(diaphragm.get("neck_width_mm", 9.0))
            cutter, metrics = bottom_access_half_receiver_cutter(
                side=side,
                face_x_mm=face_x,
                engagement_mm=engagement,
                movement_extension_mm=movement_half,
                axial_fit_clearance_mm=axial_fit_half,
                head_height_mm=head,
                neck_height_mm=neck,
                band_center_y_mm=center_y,
                band_depth_mm=band_depth,
                # Preserve the configured 3.2 mm plan ligament between the
                # third diaphragm band and the 18 mm front chord receiver.
                # The removable key coupon is narrowed in Y for fit instead
                # of widening this structural pocket band.
                transverse_clearance_mm=0.0,
                vertical_clearance_mm=0.2,
            )
            cutters.append(cutter)
            receiver_length = float(metrics["receiver_length_from_seam_face_mm"])
            access_x = (
                (0.0, receiver_length)
                if side == "left"
                else (width - receiver_length, width)
            )
            access_half_y = float(
                metrics["band_depth_with_transverse_clearance_mm"]
            ) / 2.0
            record_underside_access(
                category="diaphragm_seam_receiver",
                x_interval_mm=access_x,
                y_interval_mm=(center_y - access_half_y, center_y + access_half_y),
                source=f"{side}_{seam_class}_diaphragm_{pocket_index}",
            )
            landing_length = metrics["receiver_length_from_seam_face_mm"] + minimum_wall
            landing_center_x = (
                landing_length / 2.0 if side == "left" else width - landing_length / 2.0
            )
            landing = clipped_landing_block(
                part_width_mm=width,
                part_depth_mm=depth,
                center_x_mm=landing_center_x,
                width_x_mm=landing_length,
                center_y_mm=center_y,
                depth_y_mm=metrics["band_depth_with_transverse_clearance_mm"]
                + 2.0 * minimum_wall,
                height_mm=height,
            )
            if landing is not None:
                landing_plan_shapes.append(
                    shapely_box(
                        float(landing.bounds[0][0]),
                        float(landing.bounds[0][1]),
                        float(landing.bounds[1][0]),
                        float(landing.bounds[1][1]),
                    )
                )
            side_pockets.append(
                {
                    "type": "diaphragm_bowtie",
                    "index": pocket_index,
                    **metrics,
                }
            )

        # The front entablature is tied only at the nine fixed crown seams.
        # The seven supported-pier seams keep their three diaphragm keys but
        # deliberately have no front key/receiver: the removed floating key
        # had zero longitudinal credit and collided with the pier-side top
        # receiver.  This deletion restores a true local material ligament.
        if seam_class == "fixed_crown":
            fixed_tie = front_joint.get("fixed_crown_tie_key", {})
            if not isinstance(fixed_tie, dict):
                raise ValueError("Fixed crown front-tie contract is incomplete")
            engagement = float(front_joint.get("engagement_each_side_mm", 30.0))
            head = float(front_joint.get("head_width_mm", 12.0))
            neck = float(front_joint.get("neck_width_mm", 8.0))
            vertical_clearance = float(
                fixed_tie.get("vertical_clearance_per_face_mm", 0.2)
            )
            receiver_q = tuple(
                float(value)
                for value in fixed_tie["front_open_receiver_q_envelope_mm"]
            )
            cutter, metrics = front_insert_half_receiver_cutter(
                side=side,
                face_x_mm=face_x,
                engagement_mm=engagement,
                axial_fit_clearance_mm=axial_fit_half,
                head_height_mm=head,
                neck_height_mm=neck,
                q_envelope_mm=receiver_q,
                vertical_clearance_per_face_mm=vertical_clearance,
            )
            front_receiver_cutter_indices[side] = len(cutters)
            cutters.append(cutter)
            # The full-height 18 mm front chord is already the receiver land.
            side_pockets.append(
                {
                    "type": "front_entablature_visible_front_inserted",
                    "index": 1,
                    "rear_hard_stop_q_mm": float(fixed_tie["rear_hard_stop_q_mm"]),
                    "positive_catch_receiver_notches_generated": False,
                    **metrics,
                }
            )
        front_receiver_count = int(seam_class == "fixed_crown")
        receiver_records.append(
            {
                "side": side,
                "seam_class": seam_class,
                "receiver_role": role,
                "bottom_access": True,
                "diaphragm_receiver_count": 3,
                "front_entablature_receiver_count": front_receiver_count,
                "total_receiver_pockets": 3 + front_receiver_count,
                "floating_pier_front_receiver_deleted": (
                    seam_class == "floating_supported_pier"
                ),
                "prototype_total_movement_reserve_across_seam_mm": (
                    travel_total if seam_class == "floating_supported_pier" else 0.0
                ),
                "pockets": side_pockets,
            }
        )

    add_receiver_side("left", left_class)
    add_receiver_side("right", right_class)

    final_x_cutters, final_x_receiver_bosses, final_x_metrics = (
        cassette_final_x_receiver_cutters(
        cfg,
        instance_plan=instance_plan,
        part_width_mm=width,
        part_depth_mm=depth,
        )
    )
    blank_body = safe_union_installed(
        [blank_body, *final_x_receiver_bosses],
        f"{instance_plan.logical_id} cassette plus positive cross-key bosses",
    )
    cutters.extend(final_x_cutters)
    for receiver in final_x_metrics["receivers"]:
        center_x = float(receiver["x_relative_to_saved_handed_cassette_mm"])
        receiver_width = float(receiver["receiver_run_width_mm"])
        receiver_depth = float(receiver["receiver_depth_mm"])
        record_underside_access(
            category="final_x_top_tenon_receiver",
            x_interval_mm=(
                center_x - receiver_width / 2.0,
                center_x + receiver_width / 2.0,
            ),
            y_interval_mm=(
                front_center - receiver_depth / 2.0,
                front_center + receiver_depth / 2.0,
            ),
            source=f"final_x_top_tenon_{receiver['index']}",
        )

    upper_x_cutter, upper_x_metrics, upper_x_land = (
        cassette_upper_x_cradle_cutter(
            cfg,
            support_local_x_mm=support_local,
            part_width_mm=width,
            cassette_height_mm=height,
            top_skin_mm=top_skin,
        )
    )
    cutters.append(upper_x_cutter)
    landing_plan_shapes.append(upper_x_land)
    upper_x_interval = tuple(
        float(value)
        for value in upper_x_metrics["run_interval_relative_to_physical_part_mm"]
    )
    record_underside_access(
        category="upper_x_buffered_cradle",
        x_interval_mm=upper_x_interval,
        y_interval_mm=(0.0, float(upper_x_metrics["maximum_q_from_rear_mm"])),
        source="integrated_cap_upper_x_3_4_5_diagonal",
    )

    # Two shallow underside locators index this cassette to its one integral
    # corbel-cap station.  Internal pier stations sit in the canonical seam
    # gap, so adjacent cassettes receive complementary half pockets.
    locator_spec = saddle_locator_spec(cfg)
    locator_is_floating = position_index == count - 1 or (
        position_index > 0 and support_side == "right"
    )
    locator_ownership = (
        "run_end_terminal_floating_release"
        if position_index == count - 1
        else (
            "internal_previous_cornerward_floating_release"
            if locator_is_floating
            else (
                "run_start_terminal_tight_wall_datum"
                if position_index == 0
                else "internal_next_outboard_tight_datum"
            )
        )
    )
    locator_width_x = float(
        locator_spec[
            "floating_pocket_width_along_run_mm"
            if locator_is_floating
            else "terminal_or_fixed_pocket_width_along_run_mm"
        ]
    )
    locator_depth_y = float(locator_spec["pocket_depth_along_shelf_mm"])
    locator_cut_depth = float(locator_spec["pocket_vertical_depth_mm"])
    locator_centers_y = tuple(float(value) for value in locator_spec["centers_from_rear_mm"])
    locator_records: list[dict[str, Any]] = []
    for locator_index, center_y in enumerate(locator_centers_y, start=1):
        landing = clipped_landing_block(
            part_width_mm=width,
            part_depth_mm=depth,
            center_x_mm=support_local,
            width_x_mm=locator_width_x + 2.0 * minimum_wall,
            center_y_mm=center_y,
            depth_y_mm=locator_depth_y + 2.0 * minimum_wall,
            height_mm=height,
        )
        if landing is None:
            raise ValueError("Saddle locator land does not intersect its cassette")
        landing_plan_shapes.append(
            shapely_box(
                float(landing.bounds[0][0]),
                float(landing.bounds[0][1]),
                float(landing.bounds[1][0]),
                float(landing.bounds[1][1]),
            )
        )
        cutters.append(
            cuboid(
                (locator_width_x, locator_depth_y, locator_cut_depth + 0.2),
                origin=(
                    support_local - locator_width_x / 2.0,
                    center_y - locator_depth_y / 2.0,
                    -0.2,
                ),
            )
        )
        record_underside_access(
            category="saddle_locator_receiver",
            x_interval_mm=(
                support_local - locator_width_x / 2.0,
                support_local + locator_width_x / 2.0,
            ),
            y_interval_mm=(
                center_y - locator_depth_y / 2.0,
                center_y + locator_depth_y / 2.0,
            ),
            source=f"saddle_locator_{locator_index}",
        )
        locator_records.append(
            {
                "index": locator_index,
                "center_x_relative_to_physical_part_mm": support_local,
                "center_y_from_rear_mm": center_y,
                "pocket_width_along_run_mm": locator_width_x,
                "pocket_depth_along_shelf_mm": locator_depth_y,
                "pocket_vertical_depth_mm": locator_cut_depth,
                "thermal_ownership": locator_ownership,
                "floating_total_axial_travel_mm": (
                    float(locator_spec["floating_total_axial_travel_mm"])
                    if locator_is_floating
                    else 0.0
                ),
            }
        )

    cap_lock_cutters, cap_lock_records, cap_lock_lands = (
        cassette_integrated_cap_lock_cutters(
            cfg,
            support_local_x_mm=support_local,
            support_side=support_side,
            position_index=position_index,
            position_count=count,
            part_width_mm=width,
            part_depth_mm=depth,
        )
    )
    cutters.extend(cap_lock_cutters)
    landing_plan_shapes.extend(cap_lock_lands)
    for lock_record in cap_lock_records:
        center_x = float(lock_record["center_x_relative_to_physical_part_mm"])
        center_q = float(lock_record["center_q_from_rear_mm"])
        receiver_run, receiver_q = (
            float(value) for value in lock_record["receiver_run_q_mm"]
        )
        record_underside_access(
            category="integrated_cap_cassette_lock_receiver",
            x_interval_mm=(
                center_x - receiver_run / 2.0,
                center_x + receiver_run / 2.0,
            ),
            y_interval_mm=(
                center_q - receiver_q / 2.0,
                center_q + receiver_q / 2.0,
            ),
            source=str(lock_record["ownership"]),
        )

    lock_to_locator_ligaments: list[float] = []
    for lock_record in cap_lock_records:
        lock_center_x = float(lock_record["center_x_relative_to_physical_part_mm"])
        lock_run = float(lock_record["receiver_run_q_mm"][0])
        lock_center_q = float(lock_record["center_q_from_rear_mm"])
        matching_locator = min(
            locator_records,
            key=lambda item: abs(float(item["center_y_from_rear_mm"]) - lock_center_q),
        )
        locator_center_x = float(
            matching_locator["center_x_relative_to_physical_part_mm"]
        )
        locator_run = float(matching_locator["pocket_width_along_run_mm"])
        lock_to_locator_ligaments.append(
            abs(lock_center_x - locator_center_x)
            - lock_run / 2.0
            - locator_run / 2.0
        )
    minimum_lock_to_locator_ligament = min(lock_to_locator_ligaments)
    if minimum_lock_to_locator_ligament < minimum_wall - 1.0e-7:
        raise ValueError(
            "Cassette lock receiver leaves less than 3.2 mm to its locator pocket"
        )

    # The left half at each fixed crown owns the fully dimensioned chamber for
    # the underside keeper-reach quarter-turn pin.  The separate rear bayonet
    # tongue remains fail-closed until its missing head-vs-throat plan split is
    # frozen, but this chamber/gate/roof/index pocket is authoritative and can
    # be embodied independently without inventing that strip geometry.
    keeper_pin_receiver_record: dict[str, Any] | None = None
    front_tie_pin_receiver_record: dict[str, Any] | None = None
    owns_keeper_pin_receiver = (
        str(instance_plan.spring_side) == "left" and right_class == "fixed_crown"
    )
    if owns_keeper_pin_receiver:
        shared_pin = crown_retention_pin_contract(cfg)
        keeper = shared_pin.keeper

        def crown_inward_u_to_local_x(
            envelope: tuple[float, float],
        ) -> tuple[float, float]:
            # The owning left cassette approaches its crown at the physical
            # right face, so increasing inward-u maps toward decreasing X.
            return width - envelope[1], width - envelope[0]

        entry_x = crown_inward_u_to_local_x(keeper.entry_gate_u_q_mm[0])
        chamber_x = crown_inward_u_to_local_x(keeper.chamber_u_q_mm[0])
        entry_q = keeper.entry_gate_u_q_mm[1]
        chamber_q = keeper.chamber_u_q_mm[1]
        entry_e = keeper.entry_throat_e_mm
        chamber_e = keeper.chamber_e_mm
        pocket_e = keeper.index_pocket_e_mm
        roof_e = keeper.roof_e_mm
        pin_raw = cfg["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"]
        nub_raw = pin_raw["shared_pin_geometry"]["single_index_nub"]
        pocket_dims = tuple(
            float(value)
            for value in nub_raw["locked_pocket_long_by_short_by_depth_mm"]
        )
        pocket_center_u = keeper.center_u_q_mm[0] + float(
            nub_raw["center_from_pin_axis_on_locked_positive_long_axis_mm"]
        )
        pocket_u = (
            pocket_center_u - pocket_dims[0] / 2.0,
            pocket_center_u + pocket_dims[0] / 2.0,
        )
        pocket_q = (
            keeper.center_u_q_mm[1] - pocket_dims[1] / 2.0,
            keeper.center_u_q_mm[1] + pocket_dims[1] / 2.0,
        )
        pocket_x = crown_inward_u_to_local_x(pocket_u)
        keeper_pin_cutters = [
            cuboid(
                (
                    entry_x[1] - entry_x[0],
                    entry_q[1] - entry_q[0],
                    entry_e[1] - entry_e[0] + 0.2,
                ),
                origin=(
                    entry_x[0],
                    entry_q[0],
                    entry_e[0] - cassette_bottom_e - 0.2,
                ),
            ),
            cuboid(
                (
                    chamber_x[1] - chamber_x[0],
                    chamber_q[1] - chamber_q[0],
                    chamber_e[1] - chamber_e[0],
                ),
                origin=(
                    chamber_x[0],
                    chamber_q[0],
                    chamber_e[0] - cassette_bottom_e,
                ),
            ),
            cuboid(
                (
                    pocket_x[1] - pocket_x[0],
                    pocket_q[1] - pocket_q[0],
                    pocket_e[1] - pocket_e[0],
                ),
                origin=(
                    pocket_x[0],
                    pocket_q[0],
                    pocket_e[0] - cassette_bottom_e,
                ),
            ),
        ]
        cutters.extend(keeper_pin_cutters)
        keeper_landing = clipped_landing_block(
            part_width_mm=width,
            part_depth_mm=depth,
            center_x_mm=(chamber_x[0] + chamber_x[1]) / 2.0,
            width_x_mm=(chamber_x[1] - chamber_x[0]) + 2.0 * minimum_wall,
            center_y_mm=(chamber_q[0] + chamber_q[1]) / 2.0,
            depth_y_mm=(chamber_q[1] - chamber_q[0]) + 2.0 * minimum_wall,
            height_mm=height,
        )
        if keeper_landing is None:
            raise ValueError("Keeper pin chamber has no cassette parent land")
        landing_plan_shapes.append(
            shapely_box(
                float(keeper_landing.bounds[0][0]),
                float(keeper_landing.bounds[0][1]),
                float(keeper_landing.bounds[1][0]),
                float(keeper_landing.bounds[1][1]),
            )
        )
        record_underside_access(
            category="fixed_crown_keeper_quarter_turn_pin_entry",
            x_interval_mm=entry_x,
            y_interval_mm=entry_q,
            source="left_crown_cassette_keeper_pin_gate",
        )
        keeper_pin_receiver_record = {
            "variant_id": keeper.variant_id,
            "owner": "left fixed-crown cassette only",
            "center_inward_u_q_mm": list(keeper.center_u_q_mm),
            "center_x_relative_to_physical_cassette_mm": (
                width - keeper.center_u_q_mm[0]
            ),
            "entry_gate_u_q_mm": [list(pair) for pair in keeper.entry_gate_u_q_mm],
            "rotation_chamber_u_q_mm": [
                list(pair) for pair in keeper.chamber_u_q_mm
            ],
            "entry_throat_e_mm": list(entry_e),
            "index_pocket_u_q_mm": [list(pocket_u), list(pocket_q)],
            "index_pocket_e_mm": list(pocket_e),
            "rotation_chamber_e_mm": list(chamber_e),
            "capture_roof_e_mm": list(roof_e),
            "minimum_parent_floor_after_pocket_mm": (
                keeper.minimum_parent_floor_after_pocket_mm
            ),
            "front_tongue_emitted": False,
            "rear_bayonet_strip_receiver_embodied": True,
            "software_model_mapping_complete": False,
            "physical_installation_mapping_qualified": False,
            "production_release_eligible": False,
        }

        # Embody the one frozen rear bayonet tongue receiver.  The chamber is
        # protected in the original cassette blank so coffer selection cannot
        # erase its 3.2 mm roof or side ledges; all three exact openings are
        # then cut once with their installed e datums.  The legacy front-track
        # envelopes remain a keepout only and never emit a second tongue.
        diaphragm_retention_contract(cfg)
        retention_raw = cfg["joinery"]["diaphragm_bowtie"][
            "positive_retention"
        ]
        bayonet = retention_raw["internal_upward_bayonet_track"]
        bayonet_chamber_u = tuple(
            float(value)
            for value in bayonet[
                "rear_head_chamber_run_envelope_inward_from_left_physical_face_mm"
            ]
        )
        bayonet_chamber_q = tuple(
            float(value)
            for value in bayonet["rear_head_chamber_q_envelope_mm"]
        )
        bayonet_chamber_e = tuple(
            float(value)
            for value in bayonet["rear_head_chamber_y_envelope_mm"]
        )
        bayonet_entry_u = bayonet_chamber_u
        bayonet_entry_q = tuple(
            float(value)
            for value in bayonet["rear_bottom_entry_window_q_envelope_mm"]
        )
        bayonet_throat_u = tuple(
            float(value)
            for value in bayonet[
                "rear_final_shank_throat_run_envelope_inward_from_left_physical_face_mm"
            ]
        )
        bayonet_throat_q = tuple(
            float(value)
            for value in bayonet["rear_final_shank_throat_q_envelope_mm"]
        )
        bayonet_throat_e = tuple(
            float(value)
            for value in bayonet[
                "rear_bottom_entry_and_final_throat_y_envelope_mm"
            ]
        )
        bayonet_roof_e = tuple(
            float(value) for value in bayonet["capture_roof_y_envelope_mm"]
        )
        bayonet_chamber_x = crown_inward_u_to_local_x(bayonet_chamber_u)
        bayonet_entry_x = crown_inward_u_to_local_x(bayonet_entry_u)
        bayonet_throat_x = crown_inward_u_to_local_x(bayonet_throat_u)
        bayonet_cutters = [
            cuboid(
                (
                    bayonet_chamber_x[1] - bayonet_chamber_x[0],
                    bayonet_chamber_q[1] - bayonet_chamber_q[0],
                    bayonet_chamber_e[1] - bayonet_chamber_e[0] + 0.2,
                ),
                origin=(
                    bayonet_chamber_x[0],
                    bayonet_chamber_q[0],
                    bayonet_chamber_e[0] - cassette_bottom_e - 0.2,
                ),
            ),
            cuboid(
                (
                    bayonet_entry_x[1] - bayonet_entry_x[0],
                    bayonet_entry_q[1] - bayonet_entry_q[0],
                    bayonet_throat_e[1] - bayonet_throat_e[0] + 0.2,
                ),
                origin=(
                    bayonet_entry_x[0],
                    bayonet_entry_q[0],
                    bayonet_throat_e[0] - cassette_bottom_e - 0.2,
                ),
            ),
            cuboid(
                (
                    bayonet_throat_x[1] - bayonet_throat_x[0],
                    bayonet_throat_q[1] - bayonet_throat_q[0],
                    bayonet_throat_e[1] - bayonet_throat_e[0] + 0.2,
                ),
                origin=(
                    bayonet_throat_x[0],
                    bayonet_throat_q[0],
                    bayonet_throat_e[0] - cassette_bottom_e - 0.2,
                ),
            ),
        ]
        cutters.extend(bayonet_cutters)
        bayonet_land_u = (
            max(0.0, bayonet_chamber_u[0] - minimum_wall),
            bayonet_chamber_u[1] + minimum_wall,
        )
        bayonet_land_x = crown_inward_u_to_local_x(bayonet_land_u)
        landing_plan_shapes.append(
            shapely_box(
                bayonet_land_x[0],
                bayonet_chamber_q[0] - minimum_wall,
                bayonet_land_x[1],
                bayonet_chamber_q[1] + minimum_wall,
            )
        )
        record_underside_access(
            category="fixed_crown_keeper_rear_bayonet_entry_window",
            x_interval_mm=bayonet_entry_x,
            y_interval_mm=bayonet_entry_q,
            source="left_crown_cassette_rear_bayonet_entry",
        )
        record_underside_access(
            category="fixed_crown_keeper_rear_bayonet_final_throat",
            x_interval_mm=bayonet_throat_x,
            y_interval_mm=bayonet_throat_q,
            source="left_crown_cassette_rear_bayonet_throat",
        )
        keeper_pin_receiver_record.update(
            {
                "rear_bayonet_head_chamber_u_q_e_mm": [
                    list(bayonet_chamber_u),
                    list(bayonet_chamber_q),
                    list(bayonet_chamber_e),
                ],
                "rear_bayonet_bottom_entry_u_q_e_mm": [
                    list(bayonet_entry_u),
                    list(bayonet_entry_q),
                    list(bayonet_throat_e),
                ],
                "rear_bayonet_final_throat_u_q_e_mm": [
                    list(bayonet_throat_u),
                    list(bayonet_throat_q),
                    list(bayonet_throat_e),
                ],
                "rear_bayonet_capture_roof_e_mm": list(bayonet_roof_e),
                "rear_bayonet_front_tongue_emitted": False,
            }
        )

        # Reserve the visible-front q-axis tie receiver in the original solid
        # blank before coffer selection.  The broad tie receiver and these
        # exact local cutters are removed together later, avoiding a late
        # coplanar union that can create a false non-volume shell.
        tie_pin = shared_pin.front_tie

        def tie_u_to_local_x(
            envelope: tuple[float, float],
        ) -> tuple[float, float]:
            return width - envelope[1], width - envelope[0]

        tie_chamber_u = tie_pin.chamber_u_e_mm[0]
        tie_chamber_e = tie_pin.chamber_u_e_mm[1]
        tie_chamber_q = tie_pin.chamber_q_mm
        tie_entry_q = tie_pin.entry_throat_q_mm
        tie_rear_q = tie_pin.rear_capture_wall_q_mm
        tie_boss_u = (
            tie_chamber_u[0] - minimum_wall,
            tie_chamber_u[1] + minimum_wall,
        )
        tie_boss_e = (
            tie_chamber_e[0] - minimum_wall,
            tie_chamber_e[1] + minimum_wall,
        )
        tie_boss_q = (tie_rear_q[0], tie_entry_q[1])
        tie_boss_x = tie_u_to_local_x(tie_boss_u)
        landing_plan_shapes.append(
            shapely_box(
                tie_boss_x[0], tie_boss_q[0], tie_boss_x[1], tie_boss_q[1]
            )
        )

        tie_fit_u = tie_pin.receiver_eye_u_e_mm[0]
        tie_fit_e = tie_pin.receiver_eye_u_e_mm[1]
        tie_eye_fit = tie_pin.tie_eye_u_e_mm[0][0] - tie_fit_u[0]
        tie_fit_q = (tie_entry_q[0] - tie_eye_fit, tie_entry_q[1])
        tie_fit_x = tie_u_to_local_x(tie_fit_u)
        tie_chamber_x = tie_u_to_local_x(tie_chamber_u)
        tie_entry_u = tie_pin.entry_gate_u_e_mm[0]
        tie_entry_e = tie_pin.entry_gate_u_e_mm[1]
        tie_entry_x = tie_u_to_local_x(tie_entry_u)
        generic_front_index = front_receiver_cutter_indices.get("right")
        if generic_front_index is None:
            raise ValueError("Fixed-crown tie owner lacks its generic front receiver")
        rear_wall_preserve = cuboid(
            (
                tie_chamber_x[1] - tie_chamber_x[0] + 0.2,
                tie_rear_q[1] - tie_rear_q[0] + 0.2,
                tie_chamber_e[1] - tie_chamber_e[0] + 0.2,
            ),
            origin=(
                tie_chamber_x[0] - 0.1,
                tie_rear_q[0] - 0.1,
                tie_chamber_e[0] - cassette_bottom_e - 0.1,
            ),
        )
        cutters[generic_front_index] = safe_difference_installed(
            cutters[generic_front_index],
            [rear_wall_preserve],
            f"{instance_plan.logical_id} preserve front-tie rear capture wall",
        )
        cutters.extend(
            [
                cuboid(
                    (
                        tie_fit_x[1] - tie_fit_x[0],
                        tie_fit_q[1] - tie_fit_q[0] + 0.2,
                        tie_fit_e[1] - tie_fit_e[0],
                    ),
                    origin=(
                        tie_fit_x[0],
                        tie_fit_q[0],
                        tie_fit_e[0] - cassette_bottom_e,
                    ),
                ),
                cuboid(
                    (
                        tie_chamber_x[1] - tie_chamber_x[0],
                        tie_chamber_q[1] - tie_chamber_q[0],
                        tie_chamber_e[1] - tie_chamber_e[0],
                    ),
                    origin=(
                        tie_chamber_x[0],
                        tie_chamber_q[0],
                        tie_chamber_e[0] - cassette_bottom_e,
                    ),
                ),
                cuboid(
                    (
                        tie_entry_x[1] - tie_entry_x[0],
                        tie_entry_q[1] - tie_entry_q[0] + 0.2,
                        tie_entry_e[1] - tie_entry_e[0],
                    ),
                    origin=(
                        tie_entry_x[0],
                        tie_entry_q[0],
                        tie_entry_e[0] - cassette_bottom_e,
                    ),
                ),
            ]
        )
        front_tie_pin_receiver_record = {
            "variant_id": tie_pin.variant_id,
            "owner": "left fixed-crown cassette only",
            "receiver_boss_outer_u_e_q_mm": [
                list(tie_boss_u),
                list(tie_boss_e),
                list(tie_boss_q),
            ],
            "receiver_boss_protected_in_original_blank": True,
            "front_open_fit_cavity_u_e_q_mm": [
                list(tie_fit_u),
                list(tie_fit_e),
                list(tie_fit_q),
            ],
            "rotation_chamber_u_e_q_mm": [
                list(tie_chamber_u),
                list(tie_chamber_e),
                list(tie_chamber_q),
            ],
            "rear_capture_wall_q_mm": list(tie_rear_q),
            "entry_gate_u_e_q_mm": [
                list(tie_entry_u),
                list(tie_entry_e),
                list(tie_entry_q),
            ],
            "software_model_mapping_complete": False,
            "physical_installation_mapping_qualified": False,
            "production_release_eligible": False,
        }

    seam_band_intervals = [
        (
            center_y - float(diaphragm.get("depth_mm", 20.0)) / 2.0,
            center_y + float(diaphragm.get("depth_mm", 20.0)) / 2.0,
        )
        for center_y in diaphragm_centers
    ]
    seam_band_intervals.append(
        (
            front_center - float(front_joint.get("depth_mm", 18.0)) / 2.0,
            front_center + float(front_joint.get("depth_mm", 18.0)) / 2.0,
        )
    )
    locator_intervals = [
        (center_y - locator_depth_y / 2.0, center_y + locator_depth_y / 2.0)
        for center_y in locator_centers_y
    ]

    def interval_gap(first: tuple[float, float], second: tuple[float, float]) -> float:
        if first[1] <= second[0]:
            return second[0] - first[1]
        if second[1] <= first[0]:
            return first[0] - second[1]
        return -min(first[1], second[1]) + max(first[0], second[0])

    minimum_locator_to_seam_gap = min(
        interval_gap(locator, receiver)
        for locator in locator_intervals
        for receiver in seam_band_intervals
    )
    upper_x_to_first_mouth_ligament = (
        seam_band_intervals[0][0]
        - float(upper_x_metrics["maximum_q_from_rear_mm"])
    )
    diaphragm_to_front_ligament = seam_band_intervals[-1][0] - seam_band_intervals[-2][1]

    landing_union = unary_union(landing_plan_shapes) if landing_plan_shapes else None
    coffer_component_records: list[dict[str, Any]] = []
    for cell_index, cell_plan in enumerate(coffer_cell_plans):
        cell_x_index = cell_index // depth_cells
        cell_y_index = cell_index % depth_cells
        remaining = (
            cell_plan
            if landing_union is None
            else cell_plan.difference(landing_union)
        )
        candidates = (
            list(remaining.geoms)
            if remaining.geom_type in {"MultiPolygon", "GeometryCollection"}
            else [remaining]
        )
        coffer_component_records.extend(
            {
                "shape": component,
                "cell_x_index": cell_x_index,
                "cell_y_index": cell_y_index,
            }
            for component in candidates
            if component.geom_type == "Polygon" and component.area > 1.0e-6
        )
    coffer_void_components = [record["shape"] for record in coffer_component_records]
    coffer_void_height = height - top_skin - bottom_skin
    if coffer_void_height <= 0.0 or not coffer_void_components:
        raise ValueError("Cassette coffer void topology is empty")
    # Link the coffer cells internally through a sparse spanning tree of 3.2 x
    # 3.2 mm neutral-plane communication ports, then use one printable 3.2 mm
    # exterior pressure/service vent.  This avoids dozens of nozzle-sensitive
    # 1.6 mm underside perforations while keeping a single connected boundary.
    preexisting_access_shapes = [
        shapely_box(
            record["x_interval_mm"][0],
            record["y_interval_from_rear_mm"][0],
            record["x_interval_mm"][1],
            record["y_interval_from_rear_mm"][1],
        )
        for record in underside_access_records
    ]
    vent_diameter = max(bottom_skin, minimum_wall)
    vent_radius = vent_diameter / 2.0
    coffer_void_cutters: list[trimesh.Trimesh] = []
    retained_coffer_records: list[dict[str, Any]] = []
    coffer_components_opened_by_existing_access = 0
    coffer_components_solidified_for_ligament = 0
    vent_center: tuple[float, float] | None = None
    for component_index, component_record in enumerate(
        coffer_component_records, start=1
    ):
        component = component_record["shape"]
        opened = any(
            component.intersection(access).area > 1.0e-6
            for access in preexisting_access_shapes
        )
        if opened:
            coffer_components_opened_by_existing_access += 1
            coffer_void_cutters.append(
                extrude_polygon(component, coffer_void_height, z0=bottom_skin)
            )
            retained_coffer_records.append(
                {**component_record, "opened_by_existing_access": True}
            )
            continue
        safe_center_region = component.buffer(-(minimum_wall + vent_radius))
        if safe_center_region.is_empty:
            # A receiver land can split a nominal cell into a narrow remnant.
            # Keeping that remnant solid is conservative and avoids either a
            # trapped void or a vent that violates the true 3.2 mm ligament.
            coffer_components_solidified_for_ligament += 1
            continue
        coffer_void_cutters.append(
            extrude_polygon(component, coffer_void_height, z0=bottom_skin)
        )
        retained_coffer_records.append(
            {**component_record, "opened_by_existing_access": False}
        )
        if vent_center is None:
            center = safe_center_region.representative_point()
            vent_center = (float(center.x), float(center.y))

    if vent_center is None:
        raise ValueError(f"{instance_plan.logical_id}: no coffer can host the 3.2 mm vent")
    coffer_vent_cutters = [
        cylinder_z(
            vent_diameter,
            bottom_skin + 0.4,
            center_xy=vent_center,
            z0=-0.2,
            sections=32,
        )
    ]
    record_underside_access(
        category="coffer_pressure_equalization_vent",
        x_interval_mm=(vent_center[0] - vent_radius, vent_center[0] + vent_radius),
        y_interval_mm=(vent_center[1] - vent_radius, vent_center[1] + vent_radius),
        source="coffer_network_pressure_vent",
    )

    communication_width = minimum_wall
    communication_height = minimum_wall
    communication_z0 = (bottom_skin + height - top_skin - communication_height) / 2.0
    if not retained_coffer_records:
        raise ValueError(f"{instance_plan.logical_id}: no retained coffer network")
    # Ports are allowed to cross only one intended 3.2 mm grid rib between
    # orthogonally adjacent coffer cells.  Arbitrary point-to-point diagonals
    # would cut across receiver lands, locators, and several ribs.  Generate
    # all safe adjacent-cell candidates, then take a deterministic Kruskal
    # spanning tree.  Every selected port stays at least one configured wall
    # away from every current receiver/access keep-out.
    protected_shapes = [*landing_plan_shapes, *preexisting_access_shapes]
    protected_union = unary_union(protected_shapes) if protected_shapes else None
    port_overlap_into_void = 0.4

    def candidate_centers(lower: float, upper: float) -> list[float]:
        if upper < lower - 1.0e-9:
            return []
        values = {round((lower + upper) / 2.0, 6), round(lower, 6), round(upper, 6)}
        cursor_value = math.ceil(lower / 0.4) * 0.4
        while cursor_value <= upper + 1.0e-9:
            values.add(round(cursor_value, 6))
            cursor_value += 0.4
        return sorted(values)

    def adjacent_port_candidate(
        left_index: int, right_index: int
    ) -> dict[str, Any] | None:
        first = retained_coffer_records[left_index]
        second = retained_coffer_records[right_index]
        dx = int(second["cell_x_index"]) - int(first["cell_x_index"])
        dy = int(second["cell_y_index"]) - int(first["cell_y_index"])
        if abs(dx) + abs(dy) != 1:
            return None
        first_shape = first["shape"]
        second_shape = second["shape"]
        half_width = communication_width / 2.0
        trials: list[dict[str, Any]] = []
        if dx:
            low_record, high_record = (
                (first, second) if dx > 0 else (second, first)
            )
            low_shape = low_record["shape"]
            high_shape = high_record["shape"]
            low_cell = int(low_record["cell_x_index"])
            high_cell = int(high_record["cell_x_index"])
            rib_start = x_clear_intervals[low_cell][1]
            rib_end = x_clear_intervals[high_cell][0]
            lower = max(float(low_shape.bounds[1]), float(high_shape.bounds[1])) + half_width
            upper = min(float(low_shape.bounds[3]), float(high_shape.bounds[3])) - half_width
            for center in candidate_centers(lower, upper):
                plan = LineString(
                    [
                        (rib_start - port_overlap_into_void, center),
                        (rib_end + port_overlap_into_void, center),
                    ]
                ).buffer(
                    half_width,
                    cap_style=1,
                    join_style=1,
                    quad_segs=6,
                )
                low_probe = shapely_box(
                    rib_start - port_overlap_into_void,
                    center - half_width,
                    rib_start,
                    center + half_width,
                )
                high_probe = shapely_box(
                    rib_end,
                    center - half_width,
                    rib_end + port_overlap_into_void,
                    center + half_width,
                )
                if (
                    low_probe.difference(low_shape).area > 1.0e-7
                    or high_probe.difference(high_shape).area > 1.0e-7
                ):
                    continue
                clearance = (
                    float("inf")
                    if protected_union is None
                    else float(plan.distance(protected_union))
                )
                if clearance + 1.0e-7 < minimum_wall:
                    continue
                trials.append(
                    {
                        "plan": plan,
                        "orientation": "across_run_grid_rib",
                        "rib_span_mm": rib_end - rib_start,
                        "center_mm": [round((rib_start + rib_end) / 2.0, 6), center],
                        "protected_clearance_mm": clearance,
                    }
                )
        else:
            low_record, high_record = (
                (first, second) if dy > 0 else (second, first)
            )
            low_shape = low_record["shape"]
            high_shape = high_record["shape"]
            low_cell = int(low_record["cell_y_index"])
            high_cell = int(high_record["cell_y_index"])
            rib_start = y_clear_intervals[low_cell][1]
            rib_end = y_clear_intervals[high_cell][0]
            lower = max(float(low_shape.bounds[0]), float(high_shape.bounds[0])) + half_width
            upper = min(float(low_shape.bounds[2]), float(high_shape.bounds[2])) - half_width
            for center in candidate_centers(lower, upper):
                plan = LineString(
                    [
                        (center, rib_start - port_overlap_into_void),
                        (center, rib_end + port_overlap_into_void),
                    ]
                ).buffer(
                    half_width,
                    cap_style=1,
                    join_style=1,
                    quad_segs=6,
                )
                low_probe = shapely_box(
                    center - half_width,
                    rib_start - port_overlap_into_void,
                    center + half_width,
                    rib_start,
                )
                high_probe = shapely_box(
                    center - half_width,
                    rib_end,
                    center + half_width,
                    rib_end + port_overlap_into_void,
                )
                if (
                    low_probe.difference(low_shape).area > 1.0e-7
                    or high_probe.difference(high_shape).area > 1.0e-7
                ):
                    continue
                clearance = (
                    float("inf")
                    if protected_union is None
                    else float(plan.distance(protected_union))
                )
                if clearance + 1.0e-7 < minimum_wall:
                    continue
                trials.append(
                    {
                        "plan": plan,
                        "orientation": "rear_front_grid_rib",
                        "rib_span_mm": rib_end - rib_start,
                        "center_mm": [center, round((rib_start + rib_end) / 2.0, 6)],
                        "protected_clearance_mm": clearance,
                    }
                )
        if not trials:
            return None
        selected = max(
            trials,
            key=lambda item: (
                item["protected_clearance_mm"],
                -item["center_mm"][0],
                -item["center_mm"][1],
            ),
        )
        return {
            "left_index": left_index,
            "right_index": right_index,
            **selected,
        }

    communication_candidates = [
        candidate
        for left_index in range(len(retained_coffer_records))
        for right_index in range(left_index + 1, len(retained_coffer_records))
        if (candidate := adjacent_port_candidate(left_index, right_index)) is not None
    ]
    parents = list(range(len(retained_coffer_records)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    communication_edges: list[dict[str, Any]] = []
    for candidate in sorted(
        communication_candidates,
        key=lambda item: (
            float(item["rib_span_mm"]),
            -float(item["protected_clearance_mm"]),
            int(item["left_index"]),
            int(item["right_index"]),
        ),
    ):
        left_root = root(int(candidate["left_index"]))
        right_root = root(int(candidate["right_index"]))
        if left_root == right_root:
            continue
        parents[right_root] = left_root
        communication_edges.append(candidate)
    network_roots = {root(index) for index in range(len(retained_coffer_records))}
    if len(network_roots) != 1:
        raise ValueError(
            f"{instance_plan.logical_id}: adjacency-only coffer network has "
            f"{len(network_roots)} disconnected groups"
        )
    communication_cutters = [
        extrude_polygon(
            record["plan"],
            communication_height,
            z0=communication_z0,
        )
        for record in communication_edges
    ]
    if len(communication_cutters) != len(retained_coffer_records) - 1:
        raise AssertionError("Coffer communication spanning-tree count drift")
    selected_port_plan_union = unary_union(
        [record["plan"] for record in communication_edges]
    )
    selected_port_land_intersection_area = (
        0.0
        if landing_union is None
        else float(selected_port_plan_union.intersection(landing_union).area)
    )
    selected_port_access_intersection_area = (
        0.0
        if not preexisting_access_shapes
        else float(
            selected_port_plan_union.intersection(
                unary_union(preexisting_access_shapes)
            ).area
        )
    )
    if max(
        selected_port_land_intersection_area,
        selected_port_access_intersection_area,
    ) > 1.0e-7:
        raise AssertionError("A coffer communication port intersects a protected land")

    access_shapes = [
        shapely_box(
            record["x_interval_mm"][0],
            record["y_interval_from_rear_mm"][0],
            record["x_interval_mm"][1],
            record["y_interval_from_rear_mm"][1],
        )
        for record in underside_access_records
    ]
    independent_access_pair_checks: list[dict[str, Any]] = []
    connected_access_corridor_pairs: list[dict[str, Any]] = []
    bayonet_corridor_categories = {
        "fixed_crown_keeper_rear_bayonet_entry_window",
        "fixed_crown_keeper_rear_bayonet_final_throat",
    }
    for left_index, left_shape in enumerate(access_shapes):
        for right_index in range(left_index + 1, len(access_shapes)):
            right_shape = access_shapes[right_index]
            left_record = underside_access_records[left_index]
            right_record = underside_access_records[right_index]
            intersection_area = float(left_shape.intersection(right_shape).area)
            if (
                {left_record["category"], right_record["category"]}
                == bayonet_corridor_categories
                and intersection_area > 1.0e-7
            ):
                connected_access_corridor_pairs.append(
                    {
                        "left_source": left_record["source"],
                        "right_source": right_record["source"],
                        "connected_plan_overlap_area_mm2": round(
                            intersection_area,
                            6,
                        ),
                        "classification": (
                            "expected same-channel entry-to-final-throat corridor"
                        ),
                    }
                )
                continue
            clearance = float(left_shape.distance(right_shape))
            independent_access_pair_checks.append(
                {
                    "left_source": left_record["source"],
                    "right_source": right_record["source"],
                    "clear_plan_ligament_mm": round(clearance, 6),
                }
            )
    minimum_independent_access_ligament = min(
        (
            record["clear_plan_ligament_mm"]
            for record in independent_access_pair_checks
        ),
        default=float("inf"),
    )
    colliding_independent_access_pairs = [
        record
        for record in independent_access_pair_checks
        if record["clear_plan_ligament_mm"] < minimum_wall - 1.0e-7
    ]
    expected_connected_corridors = int(keeper_pin_receiver_record is not None)
    if len(connected_access_corridor_pairs) != expected_connected_corridors:
        raise ValueError(
            f"{instance_plan.logical_id}: expected {expected_connected_corridors} "
            "rear-bayonet entry/throat access corridor(s), found "
            f"{len(connected_access_corridor_pairs)}"
        )
    if colliding_independent_access_pairs:
        raise ValueError(
            f"{instance_plan.logical_id}: independent underside openings violate "
            f"the {minimum_wall:.3f} mm plan ligament: "
            f"{colliding_independent_access_pairs}"
        )
    if minimum_locator_to_seam_gap < minimum_wall - 1.0e-7:
        raise ValueError(
            f"Saddle locator and seam receiver bands leave only "
            f"{minimum_locator_to_seam_gap:.3f} mm plan ligament"
        )
    if upper_x_to_first_mouth_ligament < minimum_wall - 1.0e-7:
        raise ValueError(
            f"Upper-X cradle and first diaphragm mouth leave only "
            f"{upper_x_to_first_mouth_ligament:.6f} mm plan ligament"
        )
    if diaphragm_to_front_ligament < minimum_wall - 1.0e-7:
        raise ValueError(
            f"Diaphragm/front receiver bands leave only "
            f"{diaphragm_to_front_ligament:.3f} mm plan ligament"
        )

    mesh = safe_difference(
        blank_body,
        [
            *coffer_void_cutters,
            *communication_cutters,
            *cutters,
            *coffer_vent_cutters,
        ],
        f"{run_plan.run_id} cassette {position_index + 1} coffer and receivers",
    )
    if keeper_pin_receiver_record is not None:
        probe_inset = 0.02
        chamber_probe = cuboid(
            (
                chamber_x[1] - chamber_x[0] - 2.0 * probe_inset,
                chamber_q[1] - chamber_q[0] - 2.0 * probe_inset,
                chamber_e[1] - chamber_e[0] - 2.0 * probe_inset,
            ),
            origin=(
                chamber_x[0] + probe_inset,
                chamber_q[0] + probe_inset,
                chamber_e[0] - cassette_bottom_e + probe_inset,
            ),
        )
        chamber_residual = positive_solid_intersection_volume_mm3(
            mesh, chamber_probe
        )
        if chamber_residual > 1.0e-5:
            raise ValueError(
                f"{instance_plan.logical_id}: keeper pin rotation chamber is "
                "not a real void"
            )
        roof_probe = cuboid(
            (
                chamber_x[1] - chamber_x[0] - 2.0 * probe_inset,
                chamber_q[1] - chamber_q[0] - 2.0 * probe_inset,
                roof_e[1] - roof_e[0] - 2.0 * probe_inset,
            ),
            origin=(
                chamber_x[0] + probe_inset,
                chamber_q[0] + probe_inset,
                roof_e[0] - cassette_bottom_e + probe_inset,
            ),
        )
        roof_occupied = positive_solid_intersection_volume_mm3(mesh, roof_probe)
        if roof_occupied < abs(float(roof_probe.volume)) - 1.0e-3:
            raise ValueError(
                f"{instance_plan.logical_id}: keeper pin capture roof is not "
                "continuously occupied"
            )
        floor_u = (
            max(pocket_u[0], keeper.entry_gate_u_q_mm[0][1]),
            pocket_u[1],
        )
        floor_x = crown_inward_u_to_local_x(floor_u)
        if floor_x[1] - floor_x[0] <= 2.0 * probe_inset:
            raise ValueError("Keeper index pocket has no floor outside its entry gate")
        floor_probe = cuboid(
            (
                floor_x[1] - floor_x[0] - 2.0 * probe_inset,
                pocket_q[1] - pocket_q[0] - 2.0 * probe_inset,
                pocket_e[0] - cassette_bottom_e - probe_inset,
            ),
            origin=(
                floor_x[0] + probe_inset,
                pocket_q[0] + probe_inset,
                probe_inset,
            ),
        )
        floor_occupied = positive_solid_intersection_volume_mm3(mesh, floor_probe)
        if floor_occupied < abs(float(floor_probe.volume)) - 1.0e-3:
            raise ValueError(
                f"{instance_plan.logical_id}: keeper pin index pocket lacks its "
                "3.2 mm parent floor"
            )
        bayonet_chamber_probe = cuboid(
            (
                bayonet_chamber_x[1] - bayonet_chamber_x[0]
                - 2.0 * probe_inset,
                bayonet_chamber_q[1] - bayonet_chamber_q[0]
                - 2.0 * probe_inset,
                bayonet_chamber_e[1] - bayonet_chamber_e[0]
                - 2.0 * probe_inset,
            ),
            origin=(
                bayonet_chamber_x[0] + probe_inset,
                bayonet_chamber_q[0] + probe_inset,
                bayonet_chamber_e[0] - cassette_bottom_e + probe_inset,
            ),
        )
        bayonet_chamber_residual = positive_solid_intersection_volume_mm3(
            mesh, bayonet_chamber_probe
        )
        if bayonet_chamber_residual > 1.0e-5:
            raise ValueError(
                f"{instance_plan.logical_id}: keeper rear-bayonet head chamber "
                "is not a real void"
            )
        bayonet_roof_probe = cuboid(
            (
                bayonet_chamber_x[1] - bayonet_chamber_x[0]
                - 2.0 * probe_inset,
                bayonet_chamber_q[1] - bayonet_chamber_q[0]
                - 2.0 * probe_inset,
                bayonet_roof_e[1] - bayonet_roof_e[0]
                - 2.0 * probe_inset,
            ),
            origin=(
                bayonet_chamber_x[0] + probe_inset,
                bayonet_chamber_q[0] + probe_inset,
                bayonet_roof_e[0] - cassette_bottom_e + probe_inset,
            ),
        )
        bayonet_roof_occupied = positive_solid_intersection_volume_mm3(
            mesh, bayonet_roof_probe
        )
        if bayonet_roof_occupied < abs(float(bayonet_roof_probe.volume)) - 1.0e-3:
            raise ValueError(
                f"{instance_plan.logical_id}: keeper rear-bayonet capture roof "
                "is not continuously occupied"
            )
        keeper_pin_receiver_record.update(
            {
                "rotation_chamber_residual_solid_volume_mm3": round(
                    chamber_residual, 9
                ),
                "capture_roof_probe_occupied_volume_mm3": round(
                    roof_occupied, 6
                ),
                "parent_floor_probe_occupied_volume_mm3": round(
                    floor_occupied, 6
                ),
                "rear_bayonet_head_chamber_residual_solid_volume_mm3": round(
                    bayonet_chamber_residual, 9
                ),
                "rear_bayonet_capture_roof_probe_occupied_volume_mm3": round(
                    bayonet_roof_occupied, 6
                ),
            }
        )

    if front_tie_pin_receiver_record is not None:
        probe_inset = 0.02
        chamber_probe = cuboid(
            (
                tie_chamber_x[1] - tie_chamber_x[0] - 2.0 * probe_inset,
                tie_chamber_q[1] - tie_chamber_q[0] - 2.0 * probe_inset,
                tie_chamber_e[1] - tie_chamber_e[0] - 2.0 * probe_inset,
            ),
            origin=(
                tie_chamber_x[0] + probe_inset,
                tie_chamber_q[0] + probe_inset,
                tie_chamber_e[0] - cassette_bottom_e + probe_inset,
            ),
        )
        chamber_residual = positive_solid_intersection_volume_mm3(mesh, chamber_probe)
        if chamber_residual > 1.0e-5:
            raise ValueError(
                f"{instance_plan.logical_id}: front-tie pin chamber is not a real void"
            )
        rear_probe_inset = 0.04
        rear_wall_probe = cuboid(
            (
                tie_chamber_x[1] - tie_chamber_x[0] - 2.0 * rear_probe_inset,
                tie_rear_q[1] - tie_rear_q[0] - 2.0 * rear_probe_inset,
                tie_chamber_e[1] - tie_chamber_e[0] - 2.0 * rear_probe_inset,
            ),
            origin=(
                tie_chamber_x[0] + rear_probe_inset,
                tie_rear_q[0] + rear_probe_inset,
                tie_chamber_e[0] - cassette_bottom_e + rear_probe_inset,
            ),
        )
        rear_wall_occupied = positive_solid_intersection_volume_mm3(
            mesh, rear_wall_probe
        )
        if rear_wall_occupied < abs(float(rear_wall_probe.volume)) - 1.0e-3:
            raise ValueError(
                f"{instance_plan.logical_id}: front-tie pin rear capture wall "
                f"is not continuously occupied ({rear_wall_occupied:.6f} / "
                f"{abs(float(rear_wall_probe.volume)):.6f} mm3)"
            )
        front_tie_pin_receiver_record.update(
            {
                "rotation_chamber_residual_solid_volume_mm3": round(
                    chamber_residual, 9
                ),
                "rear_capture_wall_probe_occupied_volume_mm3": round(
                    rear_wall_occupied, 6
                ),
            }
        )
    # The right half at every fixed crown owns the rear double-shear ear.  Its
    # 3.2 x 3.2 mm parent spine is the uncut cassette material immediately
    # beyond the third diaphragm mouth; the hanging portion flares rearward at
    # exactly 45 degrees in the top-skin-down saved build direction.
    crown_rear_ear_record: dict[str, Any] | None = None
    owns_crown_rear_ear = (
        str(instance_plan.spring_side) == "right" and left_class == "fixed_crown"
    )
    if owns_crown_rear_ear:
        crown_contract = crown_bridge_contract(cfg)
        bridge_cfg = cfg["tied_arcade"]["rear_crown_bridge"]
        pin_boss_u = tuple(
            float(value)
            for value in bridge_cfg["retention_pin_boss_u_envelope_mm"]
        )
        pin_boss_e = tuple(
            float(value)
            for value in bridge_cfg["retention_pin_boss_y_envelope_mm"]
        )
        rear_q = crown_contract.rear_ear_q_mm
        spine_q = crown_contract.rear_ear_parent_spine_q_mm
        spine_e = crown_contract.rear_ear_parent_spine_e_mm
        union_e = crown_contract.rear_ear_parent_union_e_mm
        transition_rise = spine_q[0] - rear_q[0]
        transition_start_e = cassette_bottom_e - transition_rise
        if abs(transition_rise - 1.6) > 1.0e-7:
            raise ValueError("Rear crown ear 45-degree transition drift")

        spine_probe = cuboid(
            (
                pin_boss_u[1] - pin_boss_u[0],
                spine_q[1] - spine_q[0],
                spine_e[1] - spine_e[0],
            ),
            origin=(
                pin_boss_u[0],
                spine_q[0],
                spine_e[0] - cassette_bottom_e,
            ),
        )
        spine_occupied_volume = positive_solid_intersection_volume_mm3(
            mesh, spine_probe
        )
        if spine_occupied_volume < abs(float(spine_probe.volume)) - 1.0e-3:
            raise ValueError(
                f"{instance_plan.logical_id}: rear crown ear parent spine is "
                "not continuously occupied"
            )

        rear_ear_profile = Polygon(
            [
                (rear_q[0], pin_boss_e[0] - cassette_bottom_e),
                (rear_q[1], pin_boss_e[0] - cassette_bottom_e),
                (rear_q[1], union_e[1] - cassette_bottom_e),
                (spine_q[0], union_e[1] - cassette_bottom_e),
                (spine_q[0], 0.0),
                (rear_q[0], transition_start_e - cassette_bottom_e),
            ]
        )
        rear_ear = extrude_yz_profile_along_x(
            rear_ear_profile,
            x0=pin_boss_u[0],
            width=pin_boss_u[1] - pin_boss_u[0],
        )
        rear_ear_parent_overlap = positive_solid_intersection_volume_mm3(
            mesh, rear_ear
        )
        if rear_ear_parent_overlap <= 1.0e-5:
            raise ValueError(
                f"{instance_plan.logical_id}: rear crown ear has no positive "
                "cassette-parent union"
            )
        mesh = safe_union_installed(
            [mesh, rear_ear],
            f"{instance_plan.logical_id} fixed-crown rear pin ear",
        )
        pin_center_u, pin_center_e = crown_contract.pin_center_u_e_mm
        pin_hole = cylinder_y(
            float(bridge_cfg["retention_pin_hole_diameter_mm"]),
            rear_q[1] - rear_q[0] + 0.8,
            center_xz=(pin_center_u, pin_center_e - cassette_bottom_e),
            y0=rear_q[0] - 0.4,
        )
        pin_hole_parent_intersection = positive_solid_intersection_volume_mm3(
            mesh, pin_hole
        )
        if pin_hole_parent_intersection <= 1.0e-5:
            raise ValueError(
                f"{instance_plan.logical_id}: rear crown pin bore misses its ear"
            )
        mesh = safe_difference_installed(
            mesh,
            [pin_hole],
            f"{instance_plan.logical_id} rear crown pin bore",
        )
        crown_rear_ear_record = {
            "owner": "right fixed-crown cassette only",
            "run_u_envelope_inward_from_physical_crown_face_mm": list(pin_boss_u),
            "q_envelope_mm": list(rear_q),
            "e_envelope_mm": list(pin_boss_e),
            "parent_union_e_envelope_mm": list(union_e),
            "parent_spine_q_envelope_mm": list(spine_q),
            "parent_spine_e_envelope_mm": list(spine_e),
            "parent_spine_occupied_volume_mm3": round(spine_occupied_volume, 6),
            "ear_parent_union_volume_mm3": round(rear_ear_parent_overlap, 6),
            "transition_rearward_run_per_vertical_mm": [transition_rise, transition_rise],
            "transition_angle_deg": 45.0,
            "retention_pin_hole_diameter_mm": float(
                bridge_cfg["retention_pin_hole_diameter_mm"]
            ),
            "retention_pin_hole_center_u_e_mm": [pin_center_u, pin_center_e],
            "retention_pin_hole_parent_intersection_volume_mm3": round(
                pin_hole_parent_intersection, 6
            ),
            "top_skin_down_layer_continuity_required": True,
        }
    ornament_contract = ornament_interface_contract(cfg)
    ornament_maps = cfg["palatine"]["ornament_keyhole_contract"][
        "per_parent_boss_placement_map"
    ]
    overhang = cfg["palatine"]["ornament_keyhole_contract"][
        "overhang_finish_contract"
    ]
    ornament_parent_family_id: str | None = None
    if position_index == 0:
        ornament_parent_family_id = (
            "corner_fixed_rosette"
            if str(run_plan.role) == "through"
            else "corner_floating_return"
        )
    elif position_index == count - 1:
        ornament_parent_family_id = "ordinary_endcap"

    ornament_panel_record: dict[str, Any] | None = None
    boss_union_volumes: list[float] = []
    visible_front_extension = -float(
        cfg["tied_arcade"]["retention_wedge"]["front_bayonet_boss"][
            "outer_q_envelope_mm"
        ][0]
    )
    if ornament_parent_family_id is not None:
        parent_map = ornament_maps[ornament_parent_family_id]
        panel_q = tuple(
            float(value)
            for value in overhang["cassette_parent_panel_q_envelope_mm"]
        )
        panel_e = tuple(
            float(value) for value in parent_map["parent_panel_e_envelope_mm"]
        )
        panel_width = float(
            parent_map.get(
                "parent_panel_width_mm",
                parent_map["physical_width_height_mm"][0],
            )
        )
        if ornament_parent_family_id == "ordinary_endcap":
            end_pier_inset = float(run_plan.end_pier_inset_mm)
            panel_s_global = (
                float(run_plan.length_mm)
                - end_pier_inset
                + float(overhang["outer_end_inset_mm"]),
                float(run_plan.length_mm) - float(overhang["outer_end_inset_mm"]),
            )
        else:
            panel_s_global = tuple(
                float(value) for value in parent_map["parent_panel_run_envelope_mm"]
            )
        if abs(panel_s_global[1] - panel_s_global[0] - panel_width) > 1.0e-7:
            raise ValueError("Cassette ornament panel width drifts from its parent map")
        panel_x = (
            panel_s_global[0] - physical_left,
            panel_s_global[1] - physical_left,
        )
        if panel_x[0] < -1.0e-7 or panel_x[1] > width + 1.0e-7:
            raise ValueError("Cassette ornament panel leaves its owning cassette")
        panel_local_z = (
            panel_e[0] - cassette_bottom_e,
            panel_e[1] - cassette_bottom_e,
        )
        panel = cuboid(
            (
                panel_x[1] - panel_x[0],
                panel_q[1] - panel_q[0],
                panel_local_z[1] - panel_local_z[0],
            ),
            origin=(panel_x[0], panel_q[0], panel_local_z[0]),
        )
        panel_parent = safe_union_installed(
            [mesh, panel],
            f"{instance_plan.logical_id} integral ornament backing panel",
        )
        panel_union_overlap = (
            abs(float(mesh.volume))
            + abs(float(panel.volume))
            - abs(float(panel_parent.volume))
        )
        if panel_union_overlap <= 1.0e-4:
            raise ValueError("Cassette ornament backing panel has no positive union")

        boss_centers_piece_local = [
            (float(center[0]), float(center[1]))
            for center in parent_map["locked_boss_centers_piece_local_x_e_mm"]
        ]
        boss_centers_parent_panel_local = [
            (float(center[0]), float(center[1]))
            for center in parent_map.get(
                "locked_boss_centers_parent_panel_local_x_e_mm",
                parent_map["locked_boss_centers_piece_local_x_e_mm"],
            )
        ]
        if (
            len(boss_centers_piece_local) != 3
            or len(boss_centers_parent_panel_local) != 3
        ):
            raise ValueError("Cassette ornament parent needs exactly three bosses")
        locked_piece_origin_s = float(
            parent_map.get("locked_piece_origin_run_s_mm", panel_s_global[0])
        )
        declared_boss_centers_run = parent_map.get(
            "locked_boss_centers_run_s_e_mm"
        )
        if declared_boss_centers_run is not None:
            declared_run = np.asarray(declared_boss_centers_run, dtype=float)
            from_panel = np.asarray(
                [
                    [panel_s_global[0] + center_x, center_e]
                    for center_x, center_e in boss_centers_parent_panel_local
                ],
                dtype=float,
            )
            from_piece = np.asarray(
                [
                    [locked_piece_origin_s + center_x, center_e]
                    for center_x, center_e in boss_centers_piece_local
                ],
                dtype=float,
            )
            if not (
                np.allclose(from_panel, declared_run, atol=1.0e-7, rtol=0.0)
                and np.allclose(from_piece, declared_run, atol=1.0e-7, rtol=0.0)
            ):
                raise ValueError(
                    "Cassette ornament panel/piece boss datums do not resolve "
                    "to the same installed run centers"
                )
        boss_to_installed = np.asarray(
            [
                [1.0, 0.0, 0.0, panel_x[0]],
                [0.0, 0.0, -1.0, depth + float(ornament_contract.global_depth_offset_mm)],
                [0.0, 1.0, 0.0, -cassette_bottom_e],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        boss_meshes: list[trimesh.Trimesh] = []
        for center_panel_x, center_e in boss_centers_parent_panel_local:
            boss = gravity_keyhole_boss_mesh(center_panel_x, center_e)
            boss.apply_transform(boss_to_installed)
            boss_meshes.append(clean_mesh_preserve_coordinates(boss))
        ornament_cross_key_feature_overlaps = [
            sum(
                positive_solid_intersection_volume_mm3(
                    ornament_boss, cross_key_boss
                )
                for cross_key_boss in final_x_receiver_bosses
            )
            for ornament_boss in boss_meshes
        ]
        mesh, boss_union_volumes = union_integral_ornament_bosses(
            panel_parent,
            boss_meshes,
            minimum_overlap_mm3=float(
                ornament_contract.parent_boss_union_volume_mm3
            ),
            label=f"{instance_plan.logical_id} ornament panel",
            overlap_reference=panel,
        )
        boss_local_z = tuple(
            float(value)
            for value in cfg["ornament_isolation"][
                "integral_boss_parent_local_z_envelope_mm"
            ]
        )
        visible_front_extension = max(visible_front_extension, -boss_local_z[0])
        ornament_panel_record = {
            "family_id": ornament_parent_family_id,
            "locked_piece_origin_run_s_mm": locked_piece_origin_s,
            "panel_run_global_s_envelope_mm": list(panel_s_global),
            "panel_x_relative_to_physical_cassette_mm": list(panel_x),
            "panel_q_envelope_mm": list(panel_q),
            "panel_e_envelope_mm": list(panel_e),
            "panel_parent_union_volume_mm3": round(panel_union_overlap, 6),
            "boss_count": len(boss_centers_piece_local),
            "boss_centers_piece_local_x_e_mm": [
                list(center) for center in boss_centers_piece_local
            ],
            "boss_centers_parent_panel_local_x_e_mm": [
                list(center) for center in boss_centers_parent_panel_local
            ],
            "boss_centers_run_s_e_mm": [
                [panel_s_global[0] + center_x, center_e]
                for center_x, center_e in boss_centers_parent_panel_local
            ],
            "boss_parent_union_volumes_mm3": [
                round(value, 9) for value in boss_union_volumes
            ],
            "boss_parent_overlap_mm": float(
                ornament_contract.parent_union_overlap_mm
            ),
            "positive_cross_key_parent_feature_overlap_volumes_mm3": [
                round(value, 6)
                for value in ornament_cross_key_feature_overlaps
            ],
            "positive_cross_key_parent_feature_overlap_requires_aperture": (
                max(ornament_cross_key_feature_overlaps, default=0.0) > 1.0e-5
            ),
            "structural_credit": False,
            "actual_parent_orientation_coupon_required": True,
        }
    # Geometry above is authored in installed coordinates (rear-to-front Y,
    # underside-to-top Z).  Use an explicit, exactly self-inverse 180-degree
    # X-axis transform so X handedness is unchanged and the unperforated TOP
    # skin—not a rib/land—is the saved z=0 build face.
    installed_local_z_min = float(mesh.bounds[0][2])
    saved_from_installed = np.asarray(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, -1.0, 0.0, depth + visible_front_extension],
            [0.0, 0.0, -1.0, height],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    mesh.apply_transform(saved_from_installed)
    mesh = finish_mesh(mesh)
    # Manifold's float32 result can leave the intended saved front datum a few
    # microns beyond its exact analytical plane (159.600006 instead of
    # 159.600000 mm).  When restored to installed coordinates that creates a
    # false positive-volume sliver through the corbel's q=0 rear plane.  Snap
    # only vertices belonging to this named Y-max datum; translating the
    # complete mesh would corrupt the opposite rear datum and handed widths.
    exact_saved_front_y = depth + visible_front_extension
    actual_saved_front_y = float(mesh.bounds[1][1])
    if abs(actual_saved_front_y - exact_saved_front_y) > 1.0e-4:
        raise ValueError("Cassette saved front datum drift exceeds snap allowance")
    snapped_vertices = np.asarray(mesh.vertices, dtype=float).copy()
    front_plane_mask = (
        np.abs(snapped_vertices[:, 1] - actual_saved_front_y) <= 1.0e-5
    )
    if not np.any(front_plane_mask):
        raise ValueError("Cassette saved front datum has no planar vertices")
    snapped_vertices[front_plane_mask, 1] = exact_saved_front_y
    rear_ear_plane_snap_count = 0
    rear_ear_saved_back_y: float | None = None
    if crown_rear_ear_record is not None:
        # The positive split-tail release window terminates exactly at the
        # rear ear's q-min plane.  Preserve that analytic clearance after the
        # float32 Boolean pipeline by snapping only vertices on this named
        # plane (installed q -> saved y = front datum - q).  This is not a
        # whole-mesh translation and therefore preserves both cassette datums.
        rear_ear_q_min = float(crown_rear_ear_record["q_envelope_mm"][0])
        rear_ear_saved_back_y = exact_saved_front_y - rear_ear_q_min
        rear_ear_plane_mask = (
            np.abs(snapped_vertices[:, 1] - rear_ear_saved_back_y) <= 1.0e-5
        )
        rear_ear_plane_snap_count = int(np.count_nonzero(rear_ear_plane_mask))
        if rear_ear_plane_snap_count == 0:
            raise ValueError(
                "Fixed-crown rear ear has no vertices on its analytic q-min plane"
            )
        snapped_vertices[rear_ear_plane_mask, 1] = rear_ear_saved_back_y
    mesh.vertices = snapped_vertices
    if not mesh.is_watertight or not mesh.is_volume:
        raise ValueError("Cassette front-datum snap broke the closed solid")
    actual_size = np.asarray(mesh.extents, dtype=float)
    overall_saved_height = height - installed_local_z_min
    expected_size = np.asarray(
        [width, depth + visible_front_extension, overall_saved_height],
        dtype=float,
    )
    if not np.allclose(actual_size, expected_size, atol=1.0e-5, rtol=0.0):
        raise ValueError(
            f"{run_plan.run_id} cassette {position_index + 1}: exact envelope changed "
            f"from {expected_size.tolist()} to {actual_size.tolist()}"
        )
    saved_to_run = np.asarray(
        [
            [1.0, 0.0, 0.0, physical_left],
            [0.0, -1.0, 0.0, depth + visible_front_extension],
            [0.0, 0.0, -1.0, cassette_bottom_e + height],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )

    role_token = str(run_plan.role).upper().replace("-", "_")
    name = f"R6_DEV_CASSETTE_{role_token}_{position_index + 1:02d}_OF_{count:02d}"
    seam_receiver_counts = {
        "outer_end": 0,
        "floating_supported_pier": 3,
        "fixed_crown": 4,
    }
    seam_metadata = {
        "left": {
            "class": left_class,
            "station_local_mm": round(nominal_left, 6),
            "receiver_pocket_count": seam_receiver_counts[left_class],
        },
        "right": {
            "class": right_class,
            "station_local_mm": round(nominal_right, 6),
            "receiver_pocket_count": seam_receiver_counts[right_class],
        },
    }
    return PrototypePart(
        name=name,
        mesh=mesh,
        purpose="Exact position-specific two-skin all-PETG half-bay cassette with terminated integral chords and localized underside-access receivers.",
        saved_orientation="continuous unperforated 3.2 mm TOP skin flat on build plate; underside access openings face upward",
        status="DEVELOPMENT TWO-SKIN CASSETTE; INTERFACE/FIT/LOAD QUALIFICATION REQUIRED; NO LOAD RATING",
        notes=[
            "Front and rear longitudinal chords terminate at both exact cassette faces; no separate rail bypasses a floating pier seam.",
            "Crown receivers are locally tight; supported-pier receivers are alignment-only and include the prototype axial movement reserve.",
            "Outer run ends have no seam-key receiver pockets.",
            "Three open-bottom top-tenon receivers install at their final run coordinates; the arcade half never slides longitudinally.",
            "The two integral-cap locator pockets position only; the matching split-tail cassette locks are positive zero-credit retainers and remain flex-coupon gated.",
            "The configured 3.2 mm bottom skin is continuous except for explicit localized underside installation/service openings.",
            "The explicit saved transform preserves X handedness and places the continuous unperforated top skin at z=0.",
        ],
        design_metrics={
            "family": "position_specific_two_skin_half_bay_cassette_chassis",
            "logical_instance_id": str(instance_plan.logical_id),
            "variant_id": str(instance_plan.variant_id),
            "spring_side": str(instance_plan.spring_side),
            "run_id": str(run_plan.run_id),
            "run_role": str(run_plan.role),
            "position_index_1_based": position_index + 1,
            "position_count_in_run": count,
            "nominal_interval_local_mm": [round(nominal_left, 6), round(nominal_right, 6)],
            "physical_interval_local_mm": [round(physical_left, 6), round(physical_right, 6)],
            "physical_interval_absolute_from_corner_mm": [
                round(float(run_plan.start_from_corner_mm) + physical_left, 6),
                round(float(run_plan.start_from_corner_mm) + physical_right, 6),
            ],
            "exact_physical_width_mm": round(width, 6),
            "height_mm": height,
            "overall_saved_envelope_mm": np.round(actual_size, 6).tolist(),
            "ornament_visible_front_extension_mm": visible_front_extension,
            "saved_front_datum_snapped_vertex_count": int(
                np.count_nonzero(front_plane_mask)
            ),
            "saved_front_datum_before_snap_mm": actual_saved_front_y,
            "saved_front_datum_after_snap_mm": exact_saved_front_y,
            "fixed_crown_rear_ear_saved_q_min_plane_after_snap_mm": (
                rear_ear_saved_back_y
            ),
            "fixed_crown_rear_ear_q_min_plane_snapped_vertex_count": (
                rear_ear_plane_snap_count
            ),
            "ornament_parent_family_id": ornament_parent_family_id,
            "integral_ornament_backing_panel": ornament_panel_record,
            "integral_ornament_boss_count": len(boss_union_volumes),
            "fixed_crown_rear_pin_ear": crown_rear_ear_record,
            "fixed_crown_rear_pin_ear_generated": crown_rear_ear_record is not None,
            "fixed_crown_keeper_pin_receiver": keeper_pin_receiver_record,
            "fixed_crown_keeper_pin_receiver_generated": (
                keeper_pin_receiver_record is not None
            ),
            "fixed_crown_front_tie_pin_receiver": front_tie_pin_receiver_record,
            "fixed_crown_front_tie_pin_receiver_generated": (
                front_tie_pin_receiver_record is not None
            ),
            "depth_mm": depth,
            "top_skin_mm": top_skin,
            "bottom_skin_mm": bottom_skin,
            "configured_bottom_skin_present": True,
            "bottom_skin_policy": "continuous baseline sheet with only localized underside access openings",
            "coffer_void_component_count": len(coffer_void_components),
            "coffer_void_components_retained_count": len(coffer_void_cutters),
            "coffer_pressure_equalization_vent_diameter_mm": vent_diameter,
            "coffer_pressure_equalization_vent_count": len(coffer_vent_cutters),
            "coffer_components_opened_by_existing_access_count": (
                coffer_components_opened_by_existing_access
            ),
            "coffer_components_solidified_to_preserve_ligament_count": (
                coffer_components_solidified_for_ligament
            ),
            "coffer_vent_minimum_edge_ligament_mm": minimum_wall,
            "coffer_internal_communication_port_count": len(
                communication_cutters
            ),
            "coffer_internal_communication_grid_adjacency_only": True,
            "coffer_internal_communication_maximum_grid_ribs_crossed_per_port": 1,
            "coffer_internal_communication_port_count_by_orientation": {
                orientation: sum(
                    record["orientation"] == orientation
                    for record in communication_edges
                )
                for orientation in (
                    "across_run_grid_rib",
                    "rear_front_grid_rib",
                )
            },
            "coffer_internal_communication_total_plan_cut_length_mm": round(
                sum(
                    float(record["rib_span_mm"])
                    + 2.0 * port_overlap_into_void
                    for record in communication_edges
                ),
                6,
            ),
            "coffer_internal_communication_maximum_rib_span_mm": round(
                max(float(record["rib_span_mm"]) for record in communication_edges),
                6,
            ),
            "coffer_internal_communication_minimum_current_keepout_clearance_mm": round(
                min(
                    float(record["protected_clearance_mm"])
                    for record in communication_edges
                ),
                6,
            ),
            "coffer_internal_communication_land_intersection_area_mm2": round(
                selected_port_land_intersection_area,
                9,
            ),
            "coffer_internal_communication_access_intersection_area_mm2": round(
                selected_port_access_intersection_area,
                9,
            ),
            "coffer_internal_communication_port_run_vertical_mm": [
                communication_width,
                communication_height,
            ],
            "coffer_internal_communication_minimum_skin_ligament_mm": min(
                communication_z0 - bottom_skin,
                height
                - top_skin
                - (communication_z0 + communication_height),
            ),
            "coffer_network_policy": (
                "one adjacent-grid-rib internal spanning tree plus one 3.2 mm "
                "external vent; no diagonal land-crossing channels and no "
                "per-cell microvent array"
            ),
            "localized_underside_access_opening_count": len(underside_access_records),
            "localized_underside_access_openings": underside_access_records,
            "expected_connected_access_corridor_count": (
                expected_connected_corridors
            ),
            "connected_access_corridor_count": len(
                connected_access_corridor_pairs
            ),
            "connected_access_corridors": connected_access_corridor_pairs,
            "independent_underside_access_pair_count": len(
                independent_access_pair_checks
            ),
            "minimum_pairwise_independent_underside_access_plan_ligament_mm": (
                minimum_independent_access_ligament
            ),
            "independent_underside_access_collision_count": len(
                colliding_independent_access_pairs
            ),
            "independent_underside_access_collisions": (
                colliding_independent_access_pairs
            ),
            "final_x_wedge_service_access": {
                "path": "visible front through the configured front-to-rear transverse mortise",
                "bottom_skin_opening_required": False,
                "minimum_straight_service_access_mm": final_x_metrics[
                    "minimum_straight_service_access_mm"
                ],
            },
            "coffered_open_bottom_land_mm": bottom_land,
            "perimeter_mm": perimeter,
            "coffer_cells_across_width": x_cells,
            "coffer_cells_across_depth": depth_cells,
            "maximum_actual_clear_coffer_span_mm": round(max(clear_x, clear_y), 6),
            "rear_integral_chord_zone_from_rear_mm": [0.0, rear_chord_depth],
            "front_integral_chord_zone_from_rear_mm": [
                front_chord_start,
                front_chord_end,
            ],
            "integral_chords_terminate_at_both_cassette_faces": True,
            "separate_longitudinal_rail_bypass_present": False,
            "seams": seam_metadata,
            "receiver_sides": receiver_records,
            "support_station": {
                "support_index_1_based": support_index + 1,
                "support_center_local_to_run_mm": round(support_station, 6),
                "support_center_absolute_from_corner_mm": round(
                    float(run_plan.support_centers_absolute_mm[support_index]), 6
                ),
                "support_center_relative_to_physical_part_mm": round(support_local, 6),
                "support_relation": support_relation,
                "support_side": support_side,
                "station_centered_in_canonical_seam_gap": support_side in {"left", "right"},
            },
            "saddle_locator_pocket_count": len(locator_records),
            "saddle_locator_pockets": locator_records,
            "integrated_cap_cassette_lock_receiver_count": len(cap_lock_records),
            "integrated_cap_cassette_lock_receivers": cap_lock_records,
            "minimum_lock_to_locator_pocket_run_ligament_mm": round(
                minimum_lock_to_locator_ligament, 6
            ),
            "upper_x_buffered_cradle": upper_x_metrics,
            "upper_x_cradle_to_first_diaphragm_plan_ligament_mm": round(
                upper_x_to_first_mouth_ligament, 6
            ),
            "minimum_saddle_locator_to_seam_receiver_plan_ligament_mm": round(
                minimum_locator_to_seam_gap, 6
            ),
            "diaphragm_to_front_receiver_plan_ligament_mm": round(
                diaphragm_to_front_ligament, 6
            ),
            "receiver_and_locator_plan_collision_check_passed": True,
            "arch_capture_receiver_count": int(final_x_metrics["receiver_count"]),
            "cassette_final_x_vertical_joint": final_x_metrics,
            "saved_print_transform": {
                "operation": "explicit 180 degree rotation about run axis X",
                "saved_from_installed_matrix_row_major": saved_from_installed.tolist(),
                "installed_from_saved_matrix_row_major": saved_from_installed.tolist(),
                "saved_to_run_matrix_row_major": saved_to_run.tolist(),
                "run_coordinate_axes": "s along run, q rear-to-front, e structural elevation",
                "transform_is_self_inverse": True,
                "x_handedness_preserved": True,
                "mesh_x_rule": "mesh x = installed run x",
                "mesh_y_rule": (
                    "mesh y = shelf depth + ornament visible-front extension "
                    "- installed rear-to-front q"
                ),
                "mesh_z_rule": "mesh z = cassette height - installed elevation z",
                "continuous_top_skin_on_build_plate": True,
                "localized_bottom_access_openings_face_upward_while_printing": True,
            },
        },
    )


def cassette_chassis_family(
    cfg: dict[str, Any],
    *,
    plan: Any,
) -> tuple[list[PrototypePart], dict[str, Any]]:
    """Generate and internally validate all 12 + 6 position families."""

    if plan is None:
        raise RuntimeError(
            "The complete cassette family requires calculate_plan; snapshot fallback is intentionally insufficient"
        )
    instances = enumerate_cassette_instances(cfg, plan)
    variants = group_cassette_variants(instances)
    run_by_id = {
        plan.through.run_id: plan.through,
        plan.return_run.run_id: plan.return_run,
    }
    parts: list[PrototypePart] = []
    for instance in instances:
        parts.append(
            cassette_chassis_for_position(
                cfg,
                run_plan=run_by_id[instance.run_id],
                instance_plan=instance,
            )
        )

    by_role: dict[str, int] = {}
    receiver_side_classes = {"fixed_crown": 0, "floating_supported_pier": 0}
    receiver_pockets = {"diaphragm": 0, "front_entablature": 0}
    outer_end_sides = 0
    saddle_pockets = 0
    cap_lock_receivers = 0
    final_x_receivers = 0
    final_x_wedge_paths = 0
    bottom_skin_closed = 0
    coffer_vents = 0
    coffer_solidified = 0
    ornament_parent_panels = 0
    ornament_parent_bosses = 0
    independent_access_collisions = 0
    connected_access_corridors = 0
    expected_connected_access_corridors = 0
    minimum_independent_access_ligament = float("inf")
    widths_by_run: dict[str, list[float]] = {}
    for part in parts:
        metrics = part.design_metrics
        role = str(metrics["run_role"])
        by_role[role] = by_role.get(role, 0) + 1
        run_id = str(metrics["run_id"])
        widths_by_run.setdefault(run_id, []).append(
            round(float(metrics["exact_physical_width_mm"]), 6)
        )
        saddle_pockets += int(metrics["saddle_locator_pocket_count"])
        cap_lock_receivers += int(
            metrics["integrated_cap_cassette_lock_receiver_count"]
        )
        final_x = metrics["cassette_final_x_vertical_joint"]
        final_x_receivers += int(final_x["receiver_count"])
        final_x_wedge_paths += int(final_x["wedge_access_path_count"])
        bottom_skin_closed += int(bool(metrics["configured_bottom_skin_present"]))
        coffer_vents += int(metrics["coffer_pressure_equalization_vent_count"])
        coffer_solidified += int(
            metrics["coffer_components_solidified_to_preserve_ligament_count"]
        )
        ornament_parent_panels += int(
            metrics["integral_ornament_backing_panel"] is not None
        )
        ornament_parent_bosses += int(metrics["integral_ornament_boss_count"])
        independent_access_collisions += int(
            metrics["independent_underside_access_collision_count"]
        )
        connected_access_corridors += int(
            metrics["connected_access_corridor_count"]
        )
        expected_connected_access_corridors += int(
            metrics["expected_connected_access_corridor_count"]
        )
        minimum_independent_access_ligament = min(
            minimum_independent_access_ligament,
            float(
                metrics[
                    "minimum_pairwise_independent_underside_access_plan_ligament_mm"
                ]
            ),
        )
        for seam_data in metrics["seams"].values():
            if seam_data["class"] == "outer_end":
                outer_end_sides += 1
        for receiver in metrics["receiver_sides"]:
            receiver_side_classes[receiver["seam_class"]] += 1
            receiver_pockets["diaphragm"] += int(receiver["diaphragm_receiver_count"])
            receiver_pockets["front_entablature"] += int(
                receiver["front_entablature_receiver_count"]
            )

    expected = {
        "total_position_specific_chassis": 18,
        "through_chassis": 12,
        "return_chassis": 6,
        "fixed_crown_receiver_sides": 18,
        "floating_pier_receiver_sides": 14,
        "outer_end_sides_without_receivers": 4,
        "diaphragm_receiver_pockets": 96,
        "front_entablature_receiver_pockets": 18,
        "saddle_locator_pockets": 36,
        "integrated_cap_cassette_lock_receivers": int(
            deep_get(
                cfg,
                "nominal_geometry_snapshot.nominal_part_topology.cassette_locks",
                0,
            )
        ),
        "cassette_final_x_top_tenon_receivers": int(
            deep_get(
                cfg,
                "nominal_geometry_snapshot.integral_feature_topology.per_level_cassette_vertical_tenons",
                0,
            )
        ),
        "cassette_final_x_top_wedge_access_paths": int(
            deep_get(
                cfg,
                "nominal_geometry_snapshot.integral_feature_topology.per_level_cassette_vertical_tenons",
                0,
            )
        ),
        "logical_variants": 8,
        "integral_ornament_parent_panels": 4,
        "integral_ornament_parent_bosses": 12,
    }
    actual = {
        "total_position_specific_chassis": len(parts),
        "through_chassis": by_role.get("through", 0),
        "return_chassis": by_role.get("return", 0),
        "fixed_crown_receiver_sides": receiver_side_classes["fixed_crown"],
        "floating_pier_receiver_sides": receiver_side_classes["floating_supported_pier"],
        "outer_end_sides_without_receivers": outer_end_sides,
        "diaphragm_receiver_pockets": receiver_pockets["diaphragm"],
        "front_entablature_receiver_pockets": receiver_pockets["front_entablature"],
        "saddle_locator_pockets": saddle_pockets,
        "integrated_cap_cassette_lock_receivers": cap_lock_receivers,
        "cassette_final_x_top_tenon_receivers": final_x_receivers,
        "cassette_final_x_top_wedge_access_paths": final_x_wedge_paths,
        "logical_variants": len(variants),
        "integral_ornament_parent_panels": ornament_parent_panels,
        "integral_ornament_parent_bosses": ornament_parent_bosses,
    }
    if actual != expected:
        raise ValueError(f"Cassette family topology mismatch: expected {expected}, got {actual}")
    expected_per_cassette = expected["cassette_final_x_top_tenon_receivers"] // len(parts)
    if expected_per_cassette * len(parts) != expected[
        "cassette_final_x_top_tenon_receivers"
    ]:
        raise ValueError("Configured top-receiver count is not uniform per cassette")
    if any(
        part.design_metrics["arch_capture_receiver_count"] != expected_per_cassette
        for part in parts
    ):
        raise ValueError(
            "Every final-X cassette must contain the configured top-receiver count"
        )
    if any(part.design_metrics["separate_longitudinal_rail_bypass_present"] for part in parts):
        raise ValueError("A cassette unexpectedly contains a longitudinal rail bypass")
    if expected_connected_access_corridors != 9 or connected_access_corridors != 9:
        raise ValueError(
            "The nine fixed-crown rear-bayonet entry/throat corridors were not "
            "classified exactly"
        )
    if independent_access_collisions != 0:
        raise ValueError("Independent underside access openings collide")
    if minimum_independent_access_ligament < number(
        cfg, "joinery.minimum_wall_mm", 3.2
    ) - 1.0e-7:
        raise ValueError("Independent underside access opening ligament is too small")

    report = {
        "status": "PASS: EXACT 18 POSITION-SPECIFIC TWO-SKIN MESHES / 8 LOGICAL VARIANTS; SOFTWARE GEOMETRY AND SERVICE CORRIDORS CLOSED; PHYSICAL QUALIFICATION PENDING",
        "expected_counts": expected,
        "actual_counts": actual,
        "release_planner_source": "development/r6/release_plan.py:enumerate_cassette_instances",
        "logical_variant_groups": {
            variant_id: {
                "instance_count": len(group),
                "logical_instance_ids": [item.logical_id for item in group],
                "physical_width_mm": round(float(group[0].physical_width_mm), 6),
                "spring_side": group[0].spring_side,
                "left_joint_class": group[0].left_joint_class,
                "right_joint_class": group[0].right_joint_class,
            }
            for variant_id, group in variants.items()
        },
        "exact_physical_widths_by_run_mm": widths_by_run,
        "all_integral_front_rear_chords_terminate_at_cassette_faces": True,
        "separate_longitudinal_rail_bypass_count": 0,
        "arch_capture_receiver_count": final_x_receivers,
        "top_wedge_access_path_count": final_x_wedge_paths,
        "whole_half_longitudinal_travel_mm": 0.0,
        "top_tenon_ligament_rules_mm": {"run_each_side_of_wedge": 7.0, "vertical_above_below_wedge": 9.0},
        "minimum_straight_service_access_mm": min(
            float(part.design_metrics["cassette_final_x_vertical_joint"]["minimum_straight_service_access_mm"])
            for part in parts
        ),
        "movement_policy": (
            "9 crown seams have tight local diaphragm and front-tie receivers; 7 "
            "supported-pier seams retain only axially elongated diaphragm receivers "
            "with zero longitudinal tension credit and no floating front key"
        ),
        "floating_pier_front_entablature_receiver_count": 0,
        "deleted_floating_pier_front_key_count_per_level": 7,
        "outer_end_policy": "Four run-end cassette sides have no seam receiver pockets.",
        "prototype_scope": "One shelf level; two selected levels require 36 chassis instances after qualification.",
        "configured_bottom_skin_present_on_all_18": bottom_skin_closed == 18,
        "configured_bottom_skin_mm": number(cfg, "structure.cassette_bottom_skin_mm", 3.2),
        "continuous_top_skin_saved_on_build_plate_all_18": all(
            bool(
                part.design_metrics["saved_print_transform"][
                    "continuous_top_skin_on_build_plate"
                ]
            )
            for part in parts
        ),
        "coffer_pressure_equalization_vent_count_all_18": coffer_vents,
        "coffer_components_solidified_to_preserve_ligament_all_18": coffer_solidified,
        "integral_ornament_parent_panel_count": ornament_parent_panels,
        "integral_ornament_boss_count": ornament_parent_bosses,
        "expected_connected_access_corridor_count_all_18": (
            expected_connected_access_corridors
        ),
        "connected_access_corridor_count_all_18": connected_access_corridors,
        "minimum_pairwise_independent_underside_access_plan_ligament_mm": (
            minimum_independent_access_ligament
        ),
        "independent_underside_access_collision_count_all_18": (
            independent_access_collisions
        ),
        "two_skin_chassis_and_upper_x_cradle_geometry_complete": True,
        "authoritative_installed_solid_collision_gate_passed": True,
        "authoritative_full_vertical_lift_collision_gate_passed": True,
        "software_chassis_geometry_complete": True,
        "physical_chassis_qualification_complete": False,
        "physical_qualification_blocker": dict(CASSETTE_COMPLETION_BLOCKER),
    }
    return parts, report


def x_braced_corbel(cfg: dict[str, Any], geometry: Any) -> PrototypePart:
    projection = float(geometry.projection_mm)
    wall_upper = tuple(float(value) for value in geometry.wall_upper_node)
    front_spring = tuple(float(value) for value in geometry.front_spring_node)
    wall_lower = tuple(float(value) for value in geometry.wall_lower_node)
    front_saddle = tuple(float(value) for value in geometry.front_saddle_node)
    thickness = number(cfg, "corbel.body_thickness_mm", 28.0)
    wall_chord = number(cfg, "corbel.wall_contact_chord_mm", 12.0)
    top_chord = number(cfg, "corbel.top_bearing_chord_mm", 10.0)
    brace_chord = number(cfg, "corbel.x_brace_chord_mm", 12.0)
    pier_width = number(cfg, "tied_arcade.pier_width_mm", 28.0)
    wall_bottom = number(cfg, "corbel.wall_plate_bottom_y_mm", 24.0)
    wall_top = number(cfg, "corbel.wall_plate_top_y_mm", 168.0)
    elevation_contract = structural_elevation_contract(cfg)
    cassette_under = float(elevation_contract.cassette_underside_y_mm)
    spring_y = float(elevation_contract.structural_spring_extrados_y_mm)
    envelope = shapely_box(0.0, 0.0, projection, wall_top)

    descending = LineString([wall_upper, front_spring]).buffer(
        brace_chord / 2.0,
        cap_style=1,
        join_style=1,
        quad_segs=12,
    ).intersection(envelope)
    rising = LineString([wall_lower, front_saddle]).buffer(
        brace_chord / 2.0,
        cap_style=1,
        join_style=1,
        quad_segs=12,
    ).intersection(envelope)
    # Boolean-union the five already-closed prisms.  Extruding the final
    # perforated 2D outline directly is attractive, but some earcut versions
    # create non-manifold T-junctions around its four internal openings.
    mesh = safe_union(
        [
            cuboid(
                (wall_chord, wall_top - wall_bottom, thickness),
                origin=(0.0, wall_bottom, 0.0),
            ),
            cuboid(
                (projection, top_chord, thickness),
                origin=(0.0, cassette_under - top_chord, 0.0),
            ),
            cuboid(
                (pier_width, wall_top - (spring_y - 8.0), thickness),
                origin=(projection - pier_width, spring_y - 8.0, 0.0),
            ),
            extrude_polygon(descending, thickness),
            extrude_polygon(rising, thickness),
        ],
        "X-braced corbel/pier",
    )
    descending_length = math.dist(wall_upper, front_spring)
    rising_length = math.dist(wall_lower, front_saddle)
    return PrototypePart(
        name="R6_DEV_X_BRACED_3_4_5_CORBEL_PIER_SOLID_WALL_PLATE",
        mesh=mesh,
        purpose="Broad-side X-corbel/pier proving the two direct 3:4:5 load-path centerlines and print orientation.",
        saved_orientation="broad elevation face on build plate",
        status="GEOMETRY PROTOTYPE; SOLID WALL PLATE; NO SCREW BORES; NO LOAD RATING",
        notes=[
            "The wall plate is intentionally solid because production fastener geometry is blocked.",
            "The curved arcade is a mixed-action tied frame; exact 3:4:5 centerlines do not establish capacity.",
            "Fine Roman/Greek/Egyptian ornament remains off this structural prototype.",
        ],
        design_metrics={
            "projection_mm": projection,
            "vertical_leg_mm": float(geometry.vertical_leg_mm),
            "configured_diagonal_mm": float(geometry.diagonal_mm),
            "descending_diagonal_centerline_mm": descending_length,
            "rising_diagonal_centerline_mm": rising_length,
            "brace_crossing_mm": list(geometry.brace_crossing),
            "body_thickness_mm": thickness,
            "production_screw_bore_count": 0,
        },
    )


def sliding_saddle(cfg: dict[str, Any]) -> PrototypePart:
    dims = deep_get(cfg, "corbel.sliding_saddle_mm", [48.0, 144.0, 10.0])
    if not isinstance(dims, list) or len(dims) != 3:
        raise ValueError("corbel.sliding_saddle_mm must be [width, depth, height]")
    width, depth, height = (positive(float(value), "saddle dimension") for value in dims)
    mesh = finish_mesh(rounded_prism(width, depth, height, min(2.0, height / 3.0)))
    return PrototypePart(
        name="R6_DEV_BROAD_BEARING_SLIDING_SADDLE_BLANK",
        mesh=mesh,
        purpose="Full-size broad-bearing saddle blank for surface finish, creep, and interface-layout trials.",
        saved_orientation="largest 48 x 144 mm bearing face on build plate",
        status="BLANK INTERFACE PROTOTYPE; LOCKS AND RECEIVERS NOT YET CUT",
        notes=[
            "This blank intentionally omits pins, locks, and cassette recesses until the complete interface is interference-checked.",
        ],
        design_metrics={"width_mm": width, "depth_mm": depth, "height_mm": height},
    )


def grand_arch_half(cfg: dict[str, Any], *, span: float) -> PrototypePart:
    rise = number(cfg, "tied_arcade.arch_extrados_rise_mm", 92.0)
    arc = grand_arc(span, rise)
    rib = number(cfg, "tied_arcade.arch_radial_rib_mm", 14.0)
    chassis_depth = number(cfg, "tied_arcade.chassis_depth_mm", 18.0)
    spring_absolute = number(cfg, "tied_arcade.arch_spring_extrados_y_mm", 60.0)
    chord_bottom = number(cfg, "tied_arcade.cassette_entablature_bottom_y_mm", 138.0) - spring_absolute
    chord_top = number(cfg, "tied_arcade.cassette_entablature_top_y_mm", 168.0) - spring_absolute
    web_width = number(cfg, "tied_arcade.minimum_haunch_web_mm", 8.0)
    tongue_engagement = number(cfg, "tied_arcade.spring_tongue_engagement_mm", 12.0)
    tongue_section = deep_get(cfg, "tied_arcade.spring_tongue_section_mm", [14.0, 22.0])
    tongue_height = float(tongue_section[1]) if isinstance(tongue_section, list) and len(tongue_section) == 2 else 22.0
    half_span = span / 2.0
    radius = arc.radius_mm
    inner_radius = radius - rib
    if inner_radius <= 0.0:
        raise ValueError("Arch rib is thicker than its circular radius")

    center_x = half_span
    center_y = rise - radius
    spring_angle = math.atan2(-center_y, -half_span)
    crown_angle = math.pi / 2.0
    samples = 96
    angles = np.linspace(spring_angle, crown_angle, samples)
    outer_points = [
        (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))
        for angle in angles
    ]
    inner_points = [
        (center_x + inner_radius * math.cos(angle), center_y + inner_radius * math.sin(angle))
        for angle in reversed(angles)
    ]
    radial_band = Polygon([*outer_points, *inner_points])

    components: list[Any] = [
        radial_band,
        shapely_box(0.0, chord_bottom - 0.2, half_span, chord_top),
        shapely_box(-tongue_engagement, -tongue_height / 2.0, 2.0, tongue_height / 2.0),
    ]
    # Three sparse haunch webs tie the circular band to the cassette chord
    # while retaining an unmistakable open Roman arcade silhouette.
    for fraction in (0.25, 0.50, 0.75):
        x = half_span * fraction
        outer_y = center_y + math.sqrt(max(0.0, radius * radius - (x - center_x) ** 2))
        if outer_y < chord_bottom + 0.5:
            components.append(
                shapely_box(
                    x - web_width / 2.0,
                    outer_y - rib * 0.65,
                    x + web_width / 2.0,
                    chord_bottom + 0.5,
                )
            )
    # As with the X-corbel, union independently watertight prisms.  This avoids
    # triangulator-dependent non-manifold vertices where sparse haunch webs
    # terminate at the annular rib and chord.
    mesh = safe_union(
        [extrude_polygon(component, chassis_depth) for component in components],
        "grand tied-frame half",
    )
    return PrototypePart(
        name="R6_DEV_GRAND_NEAR_SEMICIRCULAR_TIED_FRAME_HALF_LONG_BAY",
        mesh=mesh,
        purpose="Worst-span grand arcade half with radial rib, sparse haunch webs, spring tongue, and cassette-entablature chord.",
        saved_orientation="broad arcade elevation face on build plate",
        notes=[
            "The curved rib is part of a closed tied frame and is not represented as a pure compression arch.",
            "This first mesh omits T-lugs, compression-pad tolerances, spring-retainer bore, crown keyways, and ornament; those interfaces remain blocked pending fit prototypes.",
            "Compare a complete bay with and without the arcade before assigning any structural credit.",
        ],
        design_metrics={
            "full_bay_span_mm": span,
            "half_span_mm": half_span,
            "extrados_rise_mm": rise,
            "extrados_radius_mm": radius,
            "included_angle_deg": arc.included_angle_deg,
            "idealized_thrust_proxy_H_over_W": arc.horizontal_thrust_over_total_load_proxy,
            "radial_rib_mm": rib,
            "chassis_depth_mm": chassis_depth,
        },
    )


def final_x_arch_half(
    cfg: dict[str, Any],
    *,
    run_plan: Any,
    handedness: str,
    selected_levels: int,
) -> PrototypePart:
    """One final-coordinate half-frame with config-count top and spring tenons."""

    if handedness not in {"left", "right"}:
        raise ValueError("Arcade-half handedness must be left or right")
    span = float(run_plan.bay_span_mm)
    half_span = span / 2.0
    crown_face_shift = physical_crown_face_shift_mm(cfg)
    physical_half_span = half_span - crown_face_shift
    if physical_half_span <= 0.0:
        raise ValueError("Physical crown-face shift consumes the arch half span")
    rise = number(cfg, "tied_arcade.arch_extrados_rise_mm", 92.0)
    elevation_contract = structural_elevation_contract(cfg)
    spring_y = float(elevation_contract.structural_spring_extrados_y_mm)
    cassette_bottom_y = number(cfg, "tied_arcade.cassette_entablature_bottom_y_mm", 138.0)
    rib = number(cfg, "tied_arcade.arch_radial_rib_mm", 14.0)
    chassis_depth = number(cfg, "tied_arcade.chassis_depth_mm", 18.0)
    shelf_depth = number(cfg, "closet.shelf_depth_in", 6.0) * 25.4
    web_width = number(cfg, "tied_arcade.minimum_haunch_web_mm", 8.0)
    top_joint = deep_get(cfg, "tied_arcade.cassette_final_x_vertical_tenon_joint", {})
    spring_joint = deep_get(cfg, "tied_arcade.spring_final_x_vertical_joint", {})
    bridge = deep_get(cfg, "tied_arcade.rear_crown_bridge", {})
    if not all(isinstance(value, dict) for value in (top_joint, spring_joint, bridge)):
        raise ValueError("Final-X arch mechanics require top, spring, and crown objects")
    ornament_contract = ornament_interface_contract(cfg)
    ornament_family_id = f"{str(run_plan.role)}_carrier_{handedness}"
    ornament_parent_map = cfg["palatine"]["ornament_keyhole_contract"][
        "per_parent_boss_placement_map"
    ][ornament_family_id]
    run_centers = top_joint["run_centers_mm"][run_plan.run_id]
    final_centers_u = tuple(float(value) for value in run_centers["final_u_centers_mm"])
    entry_centers_u = tuple(float(value) for value in run_centers["entry_u_centers_mm"])
    if len(final_centers_u) < 2 or final_centers_u != entry_centers_u:
        raise ValueError(
            "Each final-X half needs at least two stationary top tenons"
        )

    arc_root = tuple(
        float(value)
        for value in spring_joint["structural_arc_root_from_support_toward_crown_mm"]
    )
    if len(arc_root) != 2:
        raise ValueError("Structural arc root must contain local u/e")
    arc_root_x, arc_root_e = arc_root
    if abs(arc_root_e - spring_y) > 1.0e-7:
        raise ValueError("Regenerated structural arc root must use the spring elevation")
    clear_half_run = physical_half_span - arc_root_x
    configured_clear_half_run = float(
        spring_joint[
            "through_clear_half_run_root_to_physical_crown_mm"
            if str(run_plan.role) == "through"
            else "return_clear_half_run_root_to_physical_crown_mm"
        ]
    )
    if abs(clear_half_run - configured_clear_half_run) > 1.0e-7:
        raise ValueError("Regenerated structural arc clear-half-run drift")
    radius = (clear_half_run * clear_half_run + rise * rise) / (2.0 * rise)
    inner_radius = radius - rib
    if inner_radius <= 0.0:
        raise ValueError("Configured radial rib exceeds the regenerated arc radius")

    pad_run, pad_depth, pad_height = (
        float(value) for value in top_joint["compression_pad_run_depth_height_mm"]
    )
    top_tenon_run = float(top_joint["tenon_run_width_mm"])
    top_tenon_depth = float(top_joint["tenon_depth_mm"])
    top_tenon_y0, top_tenon_y1 = (
        float(value) for value in top_joint["tenon_final_y_envelope_mm"]
    )
    top_hole_run, top_hole_y = (
        float(value)
        for value in deep_get(cfg, "tied_arcade.retention_wedge.through_hole_run_y_mm", [4.0, 4.0])
    )
    top_wedge_center_y = float(top_joint["retention_wedge_center_y_mm"])
    top_run_ligament = float(top_joint["minimum_tenon_clear_ligament_run_mm"])
    top_y_ligament = float(top_joint["minimum_tenon_clear_ligament_y_mm"])
    if abs((top_tenon_run - top_hole_run) / 2.0 - top_run_ligament) > 1.0e-7:
        raise ValueError("Final-X top-tenon run ligament is not the configured 7 mm")
    if abs(((top_tenon_y1 - top_tenon_y0) - top_hole_y) / 2.0 - top_y_ligament) > 1.0e-7:
        raise ValueError("Final-X top-tenon vertical ligament is not the configured 9 mm")

    spring_run = float(spring_joint["tenon_run_width_mm"])
    spring_depth = float(spring_joint["tenon_depth_mm"])
    spring_tenon_y0, spring_tenon_y1 = (
        float(value) for value in spring_joint["tenon_final_y_envelope_mm"]
    )
    shoulder_run, shoulder_depth = (
        float(value) for value in spring_joint["hard_stop_shoulder_run_depth_mm"]
    )
    shoulder_source_z = tuple(
        float(value)
        for value in spring_joint["hard_stop_shoulder_source_z_envelope_mm"]
    )
    transition_source_z = tuple(
        float(value)
        for value in spring_joint[
            "below_housing_transition_source_z_envelope_mm"
        ]
    )
    if (
        abs(shoulder_source_z[1] - shoulder_source_z[0] - shoulder_depth)
        > 1.0e-7
        or transition_source_z != shoulder_source_z
        or abs(shoulder_source_z[0] - 2.0) > 1.0e-7
        or abs(shoulder_source_z[1] - chassis_depth) > 1.0e-7
    ):
        raise ValueError("Spring shoulder/transition ornament clearance datum drift")
    spring_hole_run, spring_hole_y = (
        float(value) for value in spring_joint["retention_wedge_hole_run_y_mm"]
    )
    spring_wedge_center_y = float(spring_joint["retention_wedge_center_y_mm"])
    spring_run_ligament = float(spring_joint["minimum_tenon_clear_ligament_run_mm"])
    spring_y_ligament = float(spring_joint["minimum_tenon_clear_ligament_y_mm"])
    if abs((spring_run - spring_hole_run) / 2.0 - spring_run_ligament) > 1.0e-7:
        raise ValueError("Final-X spring-tenon run ligament is not the configured 8 mm")
    if abs(((spring_tenon_y1 - spring_tenon_y0) - spring_hole_y) / 2.0 - spring_y_ligament) > 1.0e-7:
        raise ValueError("Final-X spring-tenon vertical ligament is not the configured 9 mm")

    center_x = physical_half_span
    center_y = arc_root_e + rise - radius
    spring_angle = math.atan2(
        arc_root_e - center_y,
        arc_root_x - center_x,
    )
    # A fixed 92 mm rise is slightly greater than the return clear half-run.
    # atan2 then reports the root just below -pi; unwrap it to the equivalent
    # angle above +pi so interpolation follows the intended short clockwise
    # root-to-crown arc rather than a 266-degree loop.
    if spring_angle < 0.0:
        spring_angle += 2.0 * math.pi
    crown_angle = math.pi / 2.0
    angles = np.linspace(spring_angle, crown_angle, 96)
    outer_points = [
        (center_x + radius * math.cos(angle), center_y + radius * math.sin(angle))
        for angle in angles
    ]
    inner_points = [
        (
            center_x + inner_radius * math.cos(angle),
            center_y + inner_radius * math.sin(angle),
        )
        for angle in reversed(angles)
    ]
    radial_band = Polygon([*outer_points, *inner_points]).intersection(
        shapely_box(
            arc_root_x,
            arc_root_e - rib - 1.0,
            physical_half_span,
            cassette_bottom_y,
        )
    )
    if radial_band.is_empty or radial_band.geom_type != "Polygon":
        raise ValueError("Physical crown-face trim removed the structural arch band")
    # The exact short-return root can be represented twice about 1e-13 mm
    # apart after the analytic arc is clipped to its bounding box.  De-duplicate
    # that single closure point in 2D before extrusion; otherwise Earcut emits
    # two zero-area cap faces and Manifold correctly rejects the parent.  The
    # simplification tolerance is nine orders below the minimum 0.1 mm design
    # feature and its area/bounds are explicitly preserved.
    radial_area_before = float(radial_band.area)
    radial_bounds_before = np.asarray(radial_band.bounds, dtype=float)
    radial_band = radial_band.simplify(1.0e-10, preserve_topology=True)
    radial_area_after = float(radial_band.area)
    if (
        abs(radial_area_after - radial_area_before) > 1.0e-8
        or not np.allclose(
            np.asarray(radial_band.bounds, dtype=float),
            radial_bounds_before,
            atol=1.0e-10,
            rtol=0.0,
        )
    ):
        raise ValueError("Structural radial-band duplicate cleanup changed geometry")
    radial_parent = extrude_polygon(radial_band, chassis_depth)
    if not radial_parent.is_watertight or not radial_parent.is_volume:
        raise ValueError("Regenerated structural radial band is not a closed solid")
    components: list[trimesh.Trimesh] = [radial_parent]
    cutters: list[trimesh.Trimesh] = []
    top_records: list[dict[str, Any]] = []

    # One of the bridge's two depth-projecting lugs belongs to each half.  The
    # left half owns bridge u=-28 and the right half owns u=+28; both map to the
    # same crownward distance in their handed local coordinates.  Author the
    # open-bottom head and narrow visible-side neck in the unchanged installed
    # arch datum, before any saved-orientation normalization.
    crown_contract = crown_bridge_contract(cfg)
    crown_rails = bridge["dovetail_rails"]
    bridge_u = (
        float(crown_contract.rail_centers_u_mm[0])
        if handedness == "left"
        else float(crown_contract.rail_centers_u_mm[1])
    )
    keyway_source_center_from_physical_face = float(
        crown_rails["keyway_source_center_inward_from_physical_crown_face_mm"]
    )
    keyway_center_x = (
        physical_half_span - keyway_source_center_from_physical_face
    )
    keyway_head_width = float(crown_rails["keyway_head_width_along_u_mm"])
    keyway_neck_width = float(crown_rails["keyway_neck_width_along_u_mm"])
    keyway_q0, keyway_q1 = crown_contract.keyway_q_mm
    lug_q0, lug_q1 = crown_contract.rail_q_mm
    keyway_e0, keyway_e1 = crown_contract.keyway_open_e_mm
    keyway_head = cuboid(
        (
            keyway_head_width,
            keyway_e1 - keyway_e0,
            lug_q1 - lug_q0,
        ),
        origin=(
            keyway_center_x - keyway_head_width / 2.0,
            keyway_e0,
            shelf_depth - lug_q1,
        ),
    )
    keyway_neck = cuboid(
        (
            keyway_neck_width,
            keyway_e1 - keyway_e0,
            keyway_q1 - lug_q1,
        ),
        origin=(
            keyway_center_x - keyway_neck_width / 2.0,
            keyway_e0,
            shelf_depth - keyway_q1,
        ),
    )
    crown_keyway_cutters = [keyway_head, keyway_neck]
    cutters.extend(crown_keyway_cutters)

    front_ear_parent_overlap_volume = 0.0
    front_ear_pin_hole: trimesh.Trimesh | None = None
    front_ear_head_access: trimesh.Trimesh | None = None
    if handedness == "right":
        pin_boss_u = tuple(
            float(value)
            for value in bridge["retention_pin_boss_u_envelope_mm"]
        )
        pin_boss_e = tuple(
            float(value)
            for value in bridge["retention_pin_boss_y_envelope_mm"]
        )
        front_ear_q = crown_contract.front_ear_q_mm
        front_ear = cuboid(
            (
                pin_boss_u[1] - pin_boss_u[0],
                pin_boss_e[1] - pin_boss_e[0],
                front_ear_q[1] - front_ear_q[0],
            ),
            origin=(
                physical_half_span - pin_boss_u[1],
                pin_boss_e[0],
                shelf_depth - front_ear_q[1],
            ),
        )
        front_ear_parent_overlap_volume = positive_solid_intersection_volume_mm3(
            radial_parent, front_ear
        )
        if front_ear_parent_overlap_volume <= 1.0e-5:
            raise ValueError("Right crown pin ear has no positive union to the real rib")
        components.append(front_ear)
        pin_center_u, pin_center_e = crown_contract.pin_center_u_e_mm
        front_ear_pin_hole = cylinder_z(
            float(bridge["retention_pin_hole_diameter_mm"]),
            chassis_depth + 0.8,
            center_xy=(physical_half_span - pin_center_u, pin_center_e),
            z0=-0.4,
        )
        head_diameter = float(
            bridge["minimum_accessible_pin_head_or_pull_feature_mm"]
        )
        pin_diameter = float(bridge["retention_pin_diameter_mm"])
        pin_hole_diameter = float(bridge["retention_pin_hole_diameter_mm"])
        head_access_diameter = head_diameter + pin_hole_diameter - pin_diameter
        front_ear_head_access = cylinder_z(
            head_access_diameter,
            shelf_depth - front_ear_q[1] + 0.8,
            center_xy=(physical_half_span - pin_center_u, pin_center_e),
            z0=-0.4,
        )
        cutters.extend([front_ear_pin_hole, front_ear_head_access])

    for index, center_u in enumerate(final_centers_u, start=1):
        x = top_feature_x_from_spring_mm(
            cfg,
            nominal_half_span_mm=half_span,
            u_from_physical_crown_mm=center_u,
        )
        if x - pad_run / 2.0 < -1.0e-7 or x + pad_run / 2.0 > physical_half_span + 1.0e-7:
            raise ValueError(f"{run_plan.run_id}: compression pad {index} leaves half-frame")
        if x - pad_run / 2.0 < arc_root_x + 0.4 - 1.0e-7:
            raise ValueError(
                f"{run_plan.run_id}: compression pad {index} enters the compact "
                "clevis/root exclusion"
            )
        dx = x - center_x
        radial_term = radius * radius - dx * dx
        if radial_term <= 0.0:
            raise ValueError(
                f"{run_plan.run_id}: top feature {index} lies outside the real arc domain"
            )
        outer_y = center_y + math.sqrt(radial_term)
        web_bottom = max(spring_y, outer_y - rib)
        if web_bottom < cassette_bottom_y:
            components.append(
                cuboid(
                    (web_width, cassette_bottom_y - web_bottom, chassis_depth),
                    origin=(x - web_width / 2.0, web_bottom, 0.0),
                )
            )
        components.extend(
            [
                cuboid(
                    (pad_run, pad_height, pad_depth),
                    origin=(
                        x - pad_run / 2.0,
                        cassette_bottom_y - pad_height,
                        (chassis_depth - pad_depth) / 2.0,
                    ),
                ),
                cuboid(
                    (top_tenon_run, top_tenon_y1 - top_tenon_y0, top_tenon_depth),
                    origin=(
                        x - top_tenon_run / 2.0,
                        top_tenon_y0,
                        (chassis_depth - top_tenon_depth) / 2.0,
                    ),
                ),
            ]
        )
        cutters.append(
            cylinder_z(
                top_hole_run,
                chassis_depth + 0.4,
                center_xy=(x, top_wedge_center_y),
                z0=-0.2,
            )
        )
        top_records.append(
            {
                "index": index,
                "u_from_crown_physical_face_mm": center_u,
                "entry_u_mm": entry_centers_u[index - 1],
                "local_x_from_spring_mm": round(x, 6),
                "pad_run_depth_height_mm": [pad_run, pad_depth, pad_height],
                "tenon_run_depth_height_mm": [
                    top_tenon_run,
                    top_tenon_depth,
                    top_tenon_y1 - top_tenon_y0,
                ],
            }
        )

    # The spring shoulder and tenon occupy the springward end and lift at the
    # same final coordinate as the configured top tenons.
    spring_contract = spring_socket_contract(cfg)
    spring_tenon_center_from_support = float(spring_contract["support_offset_mm"])
    spring_tenon_x0 = spring_tenon_center_from_support - spring_run / 2.0
    components.extend(
        [
            cuboid(
                (shoulder_run, pad_height, shoulder_depth),
                origin=(
                    0.0,
                    spring_tenon_y0 - pad_height,
                    shoulder_source_z[0],
                ),
            ),
            cuboid(
                (spring_run, spring_tenon_y1 - spring_tenon_y0, spring_depth),
                origin=(
                    spring_tenon_x0,
                    spring_tenon_y0,
                    (chassis_depth - spring_depth) / 2.0,
                ),
            ),
        ]
    )
    # A transition above the clevis is kinematically impossible: while the
    # half is 22 mm low, any crownward expansion there sweeps through the
    # housing.  Keep the exact shoulder, extend a same-depth chord below the
    # housing hard-stop plane, then rise wholly crownward of the housing with
    # an 8 mm root web.  Both additions overlap the real radial band and remain
    # clear by 0.4 mm through the complete vertical lift.
    minimum_root_web = float(spring_joint["minimum_root_transition_web_mm"])
    if minimum_root_web < web_width - 1.0e-7:
        raise ValueError("Structural arc root transition is thinner than the haunch web")
    shoulder_e0 = float(spring_joint["hard_stop_shoulder_y_envelope_mm"][0])
    shoulder_e1 = float(spring_joint["hard_stop_shoulder_y_envelope_mm"][1])
    transition_chord_x1 = arc_root_x + minimum_root_web
    components.extend(
        [
            cuboid(
                (transition_chord_x1, shoulder_e1 - shoulder_e0, shoulder_depth),
                origin=(
                    0.0,
                    shoulder_e0,
                    transition_source_z[0],
                ),
            ),
            cuboid(
                (
                    minimum_root_web,
                    shoulder_e1 + minimum_root_web - shoulder_e0,
                    shoulder_depth,
                ),
                origin=(
                    arc_root_x,
                    shoulder_e0,
                    transition_source_z[0],
                ),
            ),
        ]
    )
    cutters.append(
        cylinder_z(
            spring_hole_run,
            chassis_depth + 0.4,
            center_xy=(spring_tenon_center_from_support, spring_wedge_center_y),
            z0=-0.2,
        )
    )
    blank = safe_union_installed(
        components, f"{run_plan.run_id} {handedness} final-X arch blank"
    )
    keyway_parent_intersection_volumes = [
        positive_solid_intersection_volume_mm3(blank, cutter)
        for cutter in crown_keyway_cutters
    ]
    if min(keyway_parent_intersection_volumes) <= 1.0e-5:
        raise ValueError(
            f"{run_plan.run_id} {handedness}: crown keyway misses its real rib"
        )
    front_ear_pin_parent_intersection_volume = (
        0.0
        if front_ear_pin_hole is None
        else positive_solid_intersection_volume_mm3(blank, front_ear_pin_hole)
    )
    if handedness == "right" and front_ear_pin_parent_intersection_volume <= 1.0e-5:
        raise ValueError("Right crown pin bore misses its integral front ear")
    front_ear_head_access_parent_intersection_volume = (
        0.0
        if front_ear_head_access is None
        else positive_solid_intersection_volume_mm3(blank, front_ear_head_access)
    )
    if (
        handedness == "right"
        and front_ear_head_access_parent_intersection_volume <= 1.0e-5
    ):
        raise ValueError("Right crown pin head lacks a visible-front access tunnel")
    front_pin_service_parent_intersection_volume = 0.0
    if front_ear_pin_hole is not None and front_ear_head_access is not None:
        pin_service_cutter = safe_union_installed(
            [front_ear_pin_hole, front_ear_head_access],
            f"{run_plan.run_id} right crown pin service cutter",
        )
        front_pin_service_parent_intersection_volume = (
            positive_solid_intersection_volume_mm3(blank, pin_service_cutter)
        )
    blank_volume = float(blank.volume)
    mesh = safe_difference_installed(
        blank,
        cutters,
        f"{run_plan.run_id} {handedness} final-X wedge mortises",
    )
    removed_all_interface_volume = blank_volume - float(mesh.volume)
    removed_crown_keyway_volume = sum(keyway_parent_intersection_volumes)
    removed_mortise_volume = (
        removed_all_interface_volume
        - removed_crown_keyway_volume
        - front_pin_service_parent_intersection_volume
    )
    bore_sections = 48
    bore_plan_area = (
        bore_sections
        * 0.5
        * (top_hole_run / 2.0) ** 2
        * math.sin(2.0 * math.pi / bore_sections)
    )
    minimum_expected_removed_volume = (
        len(final_centers_u)
        * bore_plan_area
        * top_tenon_depth
        + bore_plan_area * spring_depth
    )
    if removed_mortise_volume + 1.0e-3 < minimum_expected_removed_volume:
        raise ValueError(
            f"{run_plan.run_id} {handedness}: wedge mortises did not cut their "
            f"installed-coordinate tenons ({removed_mortise_volume:.9f} < "
            f"{minimum_expected_removed_volume:.9f} mm3)"
        )
    # Inspect a slightly inset real solid roof block after the Boolean.  This
    # is deliberately a mesh-occupancy gate rather than a repetition of the
    # scalar contract: it catches a misplaced installed-coordinate cutter or
    # an early normalization that silently removes the hard stop.
    roof_e0, roof_e1 = crown_contract.hard_stop_roof_e_mm
    roof_inset = 0.02
    roof_probe = cuboid(
        (
            keyway_head_width - 2.0 * roof_inset,
            roof_e1 - roof_e0 - 2.0 * roof_inset,
            lug_q1 - lug_q0 - 2.0 * roof_inset,
        ),
        origin=(
            keyway_center_x - keyway_head_width / 2.0 + roof_inset,
            roof_e0 + roof_inset,
            shelf_depth - lug_q1 + roof_inset,
        ),
    )
    roof_probe_occupied_volume = positive_solid_intersection_volume_mm3(
        mesh, roof_probe
    )
    if roof_probe_occupied_volume < abs(float(roof_probe.volume)) - 1.0e-3:
        raise ValueError(
            f"{run_plan.run_id} {handedness}: crown keyway hard-stop roof is "
            "not continuously occupied in the real mesh"
        )
    depth_offset = float(ornament_contract.global_depth_offset_mm)
    boss_centers = [
        (float(center[0]), float(center[1]))
        for center in ornament_parent_map[
            "locked_boss_centers_parent_local_u_e_mm"
        ]
    ]
    if len(boss_centers) != 3:
        raise ValueError(f"{ornament_family_id}: arch parent needs three bosses")
    boss_meshes: list[trimesh.Trimesh] = []
    for center_u, center_e in boss_centers:
        boss = gravity_keyhole_boss_mesh(center_u, center_e)
        boss.apply_translation([0.0, 0.0, -depth_offset])
        boss_meshes.append(clean_mesh_preserve_coordinates(boss))
    mesh, boss_union_volumes = union_integral_ornament_bosses(
        mesh,
        boss_meshes,
        minimum_overlap_mm3=float(ornament_contract.parent_boss_union_volume_mm3),
        label=f"{run_plan.run_id} {handedness} arch",
    )
    saved_y_min_installed = float(mesh.bounds[0][1])
    shoulder_y_min = float(spring_joint["hard_stop_shoulder_y_envelope_mm"][0])
    if saved_y_min_installed > shoulder_y_min + 1.0e-7:
        raise ValueError(
            "Final-X saved Y datum unexpectedly sits above the spring shoulder"
        )
    # Bosses project 5.2 mm from the visible front.  Save the continuous
    # structural REAR face (raw z=18) on the bed so those bosses grow upward,
    # never as three detached islands below a front-face-down parent.
    saved_from_raw_installed = np.asarray(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, -saved_y_min_installed],
            [0.0, 0.0, -1.0, chassis_depth],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    raw_installed_from_saved = np.linalg.inv(saved_from_raw_installed)
    mesh.apply_transform(saved_from_raw_installed)
    mesh = finish_mesh(mesh)

    shelf_depth = number(cfg, "closet.shelf_depth_in", 6.0) * 25.4
    cassette_height = number(cfg, "structure.cassette_total_height_mm", 30.0)
    cassette_top_e = cassette_bottom_y + cassette_height
    front_center_q = number(
        cfg,
        "joinery.front_entablature_joint.center_from_rear_mm",
        shelf_depth - 9.0,
    )
    supports = tuple(float(value) for value in run_plan.support_centers_local_mm)
    boundaries = tuple(
        float(value) for value in run_plan.cassette_boundary_stations_local_mm
    )
    placement_records: list[dict[str, Any]] = []
    all_top_center_errors: list[float] = []
    all_spring_center_errors: list[float] = []
    for bay_index in range(int(run_plan.bay_count)):
        cassette_index = 2 * bay_index + (0 if handedness == "left" else 1)
        spring_s = supports[bay_index if handedness == "left" else bay_index + 1]
        handed_sign = 1.0 if handedness == "left" else -1.0
        arch_to_run = np.asarray(
            [
                [handed_sign, 0.0, 0.0, spring_s],
                [0.0, 0.0, 1.0, shelf_depth - chassis_depth],
                [0.0, 1.0, 0.0, saved_y_min_installed],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        nominal_start = boundaries[cassette_index]
        physical_start = nominal_start + (
            0.0 if cassette_index == 0 else crown_face_shift
        )
        physical_width = float(run_plan.cassette_physical_widths_mm[cassette_index])
        cassette_to_run = cassette_saved_to_run_matrix(
            physical_start_s_mm=physical_start,
            shelf_depth_mm=shelf_depth,
            cassette_height_mm=cassette_height,
            cassette_underside_e_mm=cassette_bottom_y,
        )
        top_errors: list[float] = []
        for center_u, top_record in zip(final_centers_u, top_records):
            arch_center = arch_to_run @ np.asarray(
                [
                    float(top_record["local_x_from_spring_mm"]),
                    (top_tenon_y0 + top_tenon_y1) / 2.0 - saved_y_min_installed,
                    chassis_depth / 2.0,
                    1.0,
                ],
                dtype=float,
            )
            receiver_x = (
                physical_width - center_u
                if handedness == "left"
                else center_u
            )
            cassette_center = cassette_to_run @ np.asarray(
                [
                    receiver_x,
                    shelf_depth - front_center_q,
                    cassette_top_e - (top_tenon_y0 + top_tenon_y1) / 2.0,
                    1.0,
                ],
                dtype=float,
            )
            error = float(np.linalg.norm(arch_center[:3] - cassette_center[:3]))
            if error >= 1.0e-7:
                raise ValueError(
                    f"{run_plan.run_id} bay {bay_index + 1} {handedness} top "
                    f"center misses its physical-face receiver by {error:.12g} mm"
                )
            top_errors.append(error)
            all_top_center_errors.append(error)
        spring_center = arch_to_run @ np.asarray(
            [
                spring_tenon_center_from_support,
                (spring_tenon_y0 + spring_tenon_y1) / 2.0
                - saved_y_min_installed,
                chassis_depth / 2.0,
                1.0,
            ],
            dtype=float,
        )
        expected_spring_center = np.asarray(
            [
                spring_s + handed_sign * spring_tenon_center_from_support,
                front_center_q,
                (spring_tenon_y0 + spring_tenon_y1) / 2.0,
            ],
            dtype=float,
        )
        spring_error = float(
            np.linalg.norm(spring_center[:3] - expected_spring_center)
        )
        if spring_error >= 1.0e-7:
            raise ValueError(
                f"{run_plan.run_id} bay {bay_index + 1} {handedness} spring "
                f"center transform error {spring_error:.12g} mm"
            )
        all_spring_center_errors.append(spring_error)
        placement_records.append(
            {
                "bay_index_1_based": bay_index + 1,
                "cassette_index_1_based": cassette_index + 1,
                "spring_station_local_s_mm": spring_s,
                "arch_saved_to_run_matrix_row_major": arch_to_run.tolist(),
                "mating_cassette_saved_to_run_matrix_row_major": (
                    cassette_to_run.tolist()
                ),
                "top_receiver_center_errors_mm": top_errors,
                "spring_center_error_mm": spring_error,
            }
        )

    bridge_half = max(abs(float(value)) for value in bridge["final_u_envelope_from_crown_mm"])
    first_receiver_edge = final_centers_u[0] - float(top_joint["receiver_run_width_mm"]) / 2.0
    bridge_clearance = first_receiver_edge - bridge_half
    if bridge_clearance < -1.0e-7:
        raise ValueError("Top tenon receiver violates the configured crown bridge envelope")
    service_access = structural_cross_key_service_access_mm(cfg)
    role = str(run_plan.role)
    name_role = "THROUGH_LONG" if role == "through" else "RETURN_SHORT"
    quantity = int(run_plan.bay_count)
    return PrototypePart(
        name=f"R6_DEV_FINAL_X_GRAND_ARCH_HALF_{name_role}_{handedness.upper()}",
        mesh=mesh,
        purpose="Position-fixed grand near-semicircular half-frame with integral compression pads, top tenons, spring shoulder, and spring tenon.",
        saved_orientation="structural rear broad face on build plate; visible-front bosses grow upward; install only by the recorded handed transform",
        status="DEVELOPMENT FINAL-X TIED-FRAME HALF; ZERO CAPACITY CREDIT; NO LOAD RATING",
        notes=[
            "Lift straight upward at the final run coordinate; no whole-half longitudinal slide is allowed.",
            "Two broad top pads plus the spring shoulder are the candidate compression seats; all three positive quarter-turn cross-keys retain withdrawal only.",
            "The exact rear-crown lug keyway is open from below; only the right half carries the fixed front pin ear.",
            "Crown bridge insertion and pin flex/cycle qualification remain mandatory before release mapping.",
        ],
        design_metrics={
            "family": "final_x_grand_arch_half",
            "run_id": str(run_plan.run_id),
            "run_role": role,
            "handedness": handedness,
            "quantity_per_level": quantity,
            "quantity_selected_two_levels": selected_levels * quantity,
            "full_bay_span_mm": span,
            "half_span_mm": half_span,
            "physical_half_span_to_crown_face_mm": physical_half_span,
            "physical_crown_face_shift_from_nominal_seam_mm": crown_face_shift,
            "extrados_rise_mm": rise,
            "extrados_radius_mm": radius,
            "regenerated_structural_arc_root_u_e_mm": [arc_root_x, arc_root_e],
            "regenerated_structural_arc_clear_half_run_mm": clear_half_run,
            "radial_band_duplicate_cleanup_tolerance_mm": 1.0e-10,
            "radial_band_duplicate_cleanup_area_delta_mm2": abs(
                radial_area_after - radial_area_before
            ),
            "radial_band_parent_watertight_one_body_before_union": bool(
                radial_parent.is_watertight
                and radial_parent.is_volume
                and radial_parent.body_count == 1
            ),
            "root_transition_minimum_web_mm": minimum_root_web,
            "radial_rib_mm": rib,
            "integral_top_tenon_count_per_half": len(top_records),
            "integral_top_tenons": top_records,
            "integral_spring_tenon_count_per_half": 1,
            "spring_tenon_center_from_support_crownward_mm": (
                spring_tenon_center_from_support
            ),
            "spring_tenon_run_extent_from_support_crownward_mm": [
                spring_tenon_x0,
                spring_tenon_x0 + spring_run,
            ],
            "top_wedge_mortise_count": len(top_records),
            "spring_wedge_mortise_count": 1,
            "whole_half_longitudinal_travel_mm": float(top_joint["whole_half_longitudinal_travel_mm"]),
            "top_tenon_ligament_each_side_of_4mm_wedge_mm": top_run_ligament,
            "top_tenon_ligament_above_below_4mm_wedge_mm": top_y_ligament,
            "spring_tenon_ligament_each_side_of_4mm_wedge_mm": spring_run_ligament,
            "spring_tenon_ligament_above_below_4mm_wedge_mm": spring_y_ligament,
            "minimum_straight_service_access_mm": service_access,
            "crown_bridge_top_receiver_plan_clearance_mm": round(bridge_clearance, 6),
            "crown_bridge_top_tenon_depth_collision": False,
            "crown_bridge_owned_u_from_crown_mm": bridge_u,
            "crown_bridge_keyway_source_center_inward_from_physical_face_mm": (
                keyway_source_center_from_physical_face
            ),
            "crown_bridge_keyway_center_local_x_from_spring_mm": keyway_center_x,
            "crown_bridge_keyway_head_width_mm": keyway_head_width,
            "crown_bridge_keyway_neck_width_mm": keyway_neck_width,
            "crown_bridge_keyway_q_envelope_mm": list(crown_contract.keyway_q_mm),
            "crown_bridge_keyway_open_bottom_e_envelope_mm": list(
                crown_contract.keyway_open_e_mm
            ),
            "crown_bridge_keyway_parent_intersection_volumes_mm3": [
                round(value, 6) for value in keyway_parent_intersection_volumes
            ],
            "crown_bridge_keyway_hard_stop_roof_e_envelope_mm": list(
                crown_contract.hard_stop_roof_e_mm
            ),
            "crown_bridge_keyway_hard_stop_roof_probe_volume_mm3": round(
                roof_probe_occupied_volume, 6
            ),
            "fixed_crown_front_pin_ear_generated": handedness == "right",
            "fixed_crown_front_pin_ear_q_envelope_mm": (
                list(crown_contract.front_ear_q_mm)
                if handedness == "right"
                else None
            ),
            "fixed_crown_front_pin_ear_parent_union_volume_mm3": round(
                front_ear_parent_overlap_volume, 6
            ),
            "fixed_crown_front_pin_bore_parent_intersection_volume_mm3": round(
                front_ear_pin_parent_intersection_volume, 6
            ),
            "fixed_crown_front_pin_head_access_diameter_mm": (
                head_access_diameter if handedness == "right" else None
            ),
            "fixed_crown_front_pin_head_access_parent_intersection_volume_mm3": round(
                front_ear_head_access_parent_intersection_volume, 6
            ),
            "fixed_crown_front_pin_complete_service_cutter_removed_volume_mm3": round(
                front_pin_service_parent_intersection_volume, 6
            ),
            "saved_y_min_installed_mm": saved_y_min_installed,
            "saved_from_raw_installed_matrix_row_major": (
                saved_from_raw_installed.tolist()
            ),
            "raw_installed_from_saved_matrix_row_major": (
                raw_installed_from_saved.tolist()
            ),
            "saved_build_face": "structural rear source z=18 broad face",
            "ornament_parent_family_id": ornament_family_id,
            "integral_ornament_boss_count": len(boss_centers),
            "integral_ornament_boss_centers_parent_local_u_e_mm": [
                list(center) for center in boss_centers
            ],
            "integral_ornament_boss_parent_union_volumes_mm3": [
                round(value, 9) for value in boss_union_volumes
            ],
            "integral_ornament_boss_parent_overlap_mm": float(
                ornament_contract.parent_union_overlap_mm
            ),
            "integral_ornament_boss_structural_credit": False,
            "actual_parent_orientation_coupon_required": True,
            "authoritative_instance_placements": placement_records,
            "maximum_top_receiver_center_alignment_error_mm": max(
                all_top_center_errors, default=0.0
            ),
            "maximum_spring_center_transform_error_mm": max(
                all_spring_center_errors, default=0.0
            ),
            "installed_coordinate_wedge_mortise_removed_volume_mm3": round(
                removed_mortise_volume,
                6,
            ),
            "installed_coordinate_wedge_mortise_minimum_expected_volume_mm3": round(
                minimum_expected_removed_volume,
                6,
            ),
            "installed_coordinate_crown_keyway_removed_volume_mm3": round(
                removed_crown_keyway_volume, 6
            ),
            "installed_coordinate_all_interface_cutters_removed_volume_mm3": round(
                removed_all_interface_volume, 6
            ),
            "installation_transform_rule": (
                "spring at run-start, crown toward +run"
                if handedness == "left"
                else "spring at run-end, mirror about a run-normal plane so crown points toward -run"
            ),
        },
    )


def final_x_arch_family(
    cfg: dict[str, Any], plan: Any, *, selected_levels: int
) -> list[PrototypePart]:
    parts: list[PrototypePart] = []
    for run_plan in (plan.through, plan.return_run):
        for handedness in ("left", "right"):
            parts.append(
                final_x_arch_half(
                    cfg,
                    run_plan=run_plan,
                    handedness=handedness,
                    selected_levels=selected_levels,
                )
            )
    return parts


def final_x_retention_wedges(
    cfg: dict[str, Any], *, selected_levels: int
) -> list[PrototypePart]:
    """Emit the one universal positive quarter-turn cross-key source mesh.

    The release-inventory family names retain the historical ``wedge`` token,
    but a loose straight wedge is prohibited.  Geometry is authored in the
    frozen installed coordinates ``(u, y, q)`` and saved with the locked
    crossbar/handle broad faces on the plate.
    """

    wedge = deep_get(cfg, "tied_arcade.retention_wedge", {})
    if not isinstance(wedge, dict):
        raise ValueError("tied_arcade.retention_wedge is required")
    contract = positive_retention_cross_key_contract(cfg)
    if bool(wedge["legacy_straight_wedge_allowed"]):
        raise ValueError("A loose straight final-X wedge is forbidden")

    shaft_q = tuple(float(value) for value in wedge["shaft_installed_q_envelope_mm"])
    crossbar = wedge["crossbar"]
    handle = wedge["visible_handle_and_positive_index"]
    crossbar_q = tuple(float(value) for value in crossbar["installed_q_envelope_mm"])
    handle_q = tuple(float(value) for value in handle["handle_installed_q_envelope_mm"])
    shaft_diameter = float(wedge["shaft_diameter_mm"])
    cross_long = float(crossbar["actual_long_span_mm"])
    cross_short = float(crossbar["actual_short_span_mm"])
    cross_axial = float(crossbar["actual_axial_thickness_mm"])
    handle_long = float(handle["handle_long_span_mm"])
    handle_short = float(handle["handle_short_span_mm"])
    flex_thickness = float(handle["flexure_thickness_mm"])
    dog_engagement = float(handle["latch_dog_nominal_positive_engagement_mm"])
    folded = handle["folded_u_authored_geometry"]
    root_width = float(folded["root_width_u_mm"])
    dog_width = float(folded["dog_width_u_mm"])
    dog_inset_from_handle_end = float(
        folded["dog_inset_from_handle_end_u_mm"]
    )
    open_slot_q = float(folded["open_slot_q_mm"])
    neck_width = float(folded["shaft_spine_neck_width_u_mm"])
    neck_q_thickness = float(folded["neck_q_thickness_mm"])
    neck_shaft_union = float(folded["neck_shaft_positive_union_q_mm"])
    dog_front_union = float(folded["dog_front_beam_positive_union_q_mm"])
    dog_latch_projection = float(folded["dog_rear_latch_projection_q_mm"])
    dog_total_q_depth = float(folded["dog_total_q_depth_mm"])
    if abs(neck_width - handle_short) > 1.0e-7:
        raise ValueError("Cross-key folded-U neck width differs from handle width")
    if abs(dog_latch_projection - dog_engagement) > 1.0e-7:
        raise ValueError("Cross-key dog projection differs from latch engagement")

    # Locked installed geometry.  The U-routed visible handle has a 0.4 mm
    # open slot between its front flex beam and rear spine except at the left
    # root.  The right dog projects rearward into the unique receiver notch;
    # pulling the beam 1.6 mm toward -q clears that 1.2 mm dog by 0.4 mm.
    spine_q0 = handle_q[0] + flex_thickness + open_slot_q
    shaft = cylinder_z(
        shaft_diameter,
        shaft_q[1] - shaft_q[0],
        center_xy=(0.0, 0.0),
        z0=shaft_q[0],
        sections=8,
    )
    shaft.apply_transform(
        trimesh.transformations.rotation_matrix(
            math.pi / 8.0, [0.0, 0.0, 1.0]
        )
    )
    components = [
        shaft,
        cuboid(
            (cross_long, cross_short, cross_axial),
            origin=(-cross_long / 2.0, -cross_short / 2.0, crossbar_q[0]),
        ),
        cuboid(
            (cross_long, 0.1, cross_axial),
            origin=(-cross_long / 2.0, -handle_short / 2.0, crossbar_q[0]),
        ),
        cuboid(
            (handle_long, handle_short, handle_q[1] - spine_q0),
            origin=(-handle_long / 2.0, -handle_short / 2.0, spine_q0),
        ),
        cuboid(
            (handle_long, handle_short, flex_thickness),
            origin=(-handle_long / 2.0, -handle_short / 2.0, handle_q[0]),
        ),
        # U-beam root and shaft/spine neck use small positive overlaps while
        # remaining wholly inside the exact external envelope.
        cuboid(
            (root_width, handle_short, handle_q[1] - handle_q[0]),
            origin=(-handle_long / 2.0, -handle_short / 2.0, handle_q[0]),
        ),
        cuboid(
            (neck_width, handle_short, neck_q_thickness),
            origin=(
                -neck_width / 2.0,
                -handle_short / 2.0,
                handle_q[1] - neck_shaft_union,
            ),
        ),
        cuboid(
            (dog_width, handle_short, dog_total_q_depth),
            origin=(
                handle_long / 2.0 - dog_inset_from_handle_end,
                -handle_short / 2.0,
                handle_q[0] + flex_thickness - dog_front_union,
            ),
        ),
    ]
    locked_installed = safe_union_installed(
        components, "positive quarter-turn final-X cross-key"
    )
    locked_bounds = np.asarray(locked_installed.bounds, dtype=float)
    expected_installed_bounds = np.asarray(
        [
            [-handle_long / 2.0, -handle_short / 2.0, handle_q[0]],
            [handle_long / 2.0, handle_short / 2.0, shaft_q[1]],
        ],
        dtype=float,
    )
    if not np.allclose(locked_bounds, expected_installed_bounds, atol=1.0e-6, rtol=0.0):
        raise ValueError(
            "Positive cross-key installed envelope drift: "
            f"{locked_bounds.tolist()} != {expected_installed_bounds.tolist()}"
        )

    # saved x <- installed q, saved y <- installed u, saved z <- installed y
    saved_from_locked_installed = np.asarray(
        [
            [0.0, 0.0, 1.0, -handle_q[0]],
            [1.0, 0.0, 0.0, handle_long / 2.0],
            [0.0, 1.0, 0.0, handle_short / 2.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    locked_installed_from_saved = np.linalg.inv(saved_from_locked_installed)
    mesh = locked_installed.copy()
    mesh.apply_transform(saved_from_locked_installed)
    mesh = finish_mesh(mesh)
    expected_saved_extents = np.asarray(contract.saved_bare_envelope_mm, dtype=float)
    if not np.allclose(mesh.extents, expected_saved_extents, atol=1.0e-6, rtol=0.0):
        raise ValueError(
            f"Positive cross-key saved extents {mesh.extents.tolist()} do not match "
            f"{expected_saved_extents.tolist()}"
        )

    # Derive the flex path from the authored solids rather than accepting a
    # metadata-only developed length.  The moving dog follows the front beam
    # to the left root, turns through q, then returns along the rear spine to
    # the fixed-neck edge.  This lets a compact visible handle contain a
    # longer folded flexure without pretending the straight envelope is its
    # developed length.
    dog_center_u = (
        handle_long / 2.0
        - dog_inset_from_handle_end
        + dog_width / 2.0
    )
    left_root_center_u = -handle_long / 2.0 + root_width / 2.0
    fixed_neck_left_u = -handle_short / 2.0
    computed_flex_segments = (
        dog_center_u - left_root_center_u,
        spine_q0 - handle_q[0],
        fixed_neck_left_u - left_root_center_u,
    )
    configured_flex_segments = tuple(
        float(value)
        for value in handle["authored_folded_u_centerline_segment_lengths_mm"]
    )
    if not np.allclose(
        computed_flex_segments,
        configured_flex_segments,
        atol=1.0e-7,
        rtol=0.0,
    ):
        raise ValueError(
            "Cross-key folded-U mesh path segments differ from config: "
            f"{computed_flex_segments!r} != {configured_flex_segments!r}"
        )
    computed_flex_length = float(sum(computed_flex_segments))
    configured_authored_length = float(
        handle["authored_folded_u_centerline_length_mm"]
    )
    conservative_flex_length = float(
        handle["integral_u_flexure_developed_length_mm"]
    )
    if abs(computed_flex_length - configured_authored_length) > 1.0e-7:
        raise ValueError("Cross-key folded-U mesh path total differs from config")
    if computed_flex_length + 1.0e-7 < conservative_flex_length:
        raise ValueError("Authored folded-U flex path is shorter than its strain screen")
    release_deflection = float(handle["front_release_deflection_mm"])
    computed_strain_screen = (
        6.0
        * release_deflection
        * flex_thickness
        / conservative_flex_length**2
    )
    if abs(
        computed_strain_screen - float(handle["nominal_outer_fiber_strain"])
    ) > 1.0e-12:
        raise ValueError("Cross-key conservative flexure strain screen drifted")

    entry_from_locked = np.asarray(key_transform_q(-90.0), dtype=float)
    locked_from_entry = np.asarray(key_transform_q(90.0), dtype=float)
    if not np.allclose(entry_from_locked @ locked_from_entry, np.eye(4), atol=1.0e-9):
        raise ValueError("Positive cross-key entry/locked transforms are not inverse")

    build_face_contact_area = cross_long * cross_axial + handle_long * flex_thickness
    brim_width = float(wedge["saved_print_orientation"]["brim_each_side_mm"])
    saved_from_installed = np.asarray(
        saved_from_locked_installed,
    )
    installed_from_saved = np.asarray(
        locked_installed_from_saved,
    )
    common = {
        "family_id": str(wedge["family_id"]),
        "legacy_straight_wedge_present": False,
        "shaft_diameter_mm": shaft_diameter,
        "through_bore_diameter_mm": float(wedge["tenon_through_bore_diameter_mm"]),
        "installed_shaft_q_envelope_mm": list(shaft_q),
        "installed_crossbar_q_envelope_mm": list(crossbar_q),
        "installed_handle_q_envelope_mm": list(handle_q),
        "crossbar_actual_long_short_axial_mm": [cross_long, cross_short, cross_axial],
        "visible_handle_long_short_mm": [handle_long, handle_short],
        "integral_u_routed_flexure_developed_length_mm": computed_flex_length,
        "authored_folded_u_centerline_segment_lengths_mm": list(
            computed_flex_segments
        ),
        "conservative_effective_flexure_length_mm": conservative_flex_length,
        "computed_nominal_outer_fiber_strain": computed_strain_screen,
        "folded_u_authored_geometry": {
            key: float(value) for key, value in folded.items()
        },
        "latch_dog_nominal_positive_engagement_mm": dog_engagement,
        "latch_release_deflection_mm": float(handle["front_release_deflection_mm"]),
        "post_release_dog_clearance_mm": float(handle["post_release_dog_clearance_mm"]),
        "insertion_axis": str(wedge["insertion_axis"]),
        "retention_role": str(wedge["retention_role"]),
        "positive_quarter_turn_bayonet_encoded": True,
        "entry_to_locked_rotation_deg": 90.0,
        "exact_insertion_translation_q_mm": contract.exact_insertion_translation_mm,
        "entry_from_locked_matrix_row_major": entry_from_locked.tolist(),
        "locked_from_entry_matrix_row_major": locked_from_entry.tolist(),
        "saved_from_installed_matrix_row_major": saved_from_installed.tolist(),
        "installed_from_saved_matrix_row_major": installed_from_saved.tolist(),
        "saved_broad_side_bounding_envelope_mm": list(contract.saved_bare_envelope_mm[:2]),
        "saved_bounding_envelope_mm": list(contract.saved_bare_envelope_mm),
        "saved_build_face_contact_area_mm2": build_face_contact_area,
        "recommended_optional_brim_width_mm": brim_width,
        "optional_brim_bounding_envelope_mm": list(contract.saved_brim_envelope_mm),
        "fits_180_mm_envelope_with_recommended_brim": all(
            value <= 180.0 for value in contract.saved_brim_envelope_mm
        ),
        "same_petg_actual_parent_coupon_required": True,
        "production_orientation_allowed": False,
        "structural_credit": False,
    }
    topology = deep_get(cfg, "nominal_geometry_snapshot.nominal_part_topology", {})
    selected_topology = deep_get(
        cfg, "nominal_geometry_snapshot.selected_two_level_part_topology", {}
    )
    if not isinstance(topology, dict) or not isinstance(selected_topology, dict):
        raise ValueError("Configured wedge topology counts are required")
    top_count = int(topology["cassette_top_retention_wedges"])
    spring_count = int(topology["spring_retention_wedges"])
    selected_top_count = int(selected_topology["cassette_top_retention_wedges"])
    selected_spring_count = int(selected_topology["spring_retention_wedges"])
    if selected_top_count != top_count * selected_levels or selected_spring_count != spring_count * selected_levels:
        raise ValueError("Configured selected-level wedge counts are not exact independent doubles")
    return [
        PrototypePart(
            name="R6_DEV_FINAL_X_TOP_CAPTURE_WEDGE_UNIVERSAL",
            mesh=mesh.copy(),
            purpose="Universal visible-front positive quarter-turn cross-key for one cassette-top tenon interface.",
            saved_orientation="locked crossbar and U-routed handle broad faces on build plate; shaft axis parallel to plate",
            status="DEVELOPMENT POSITIVE CROSS-KEY; RETENTION ONLY; ZERO LOAD CREDIT; ACTUAL-PARENT COUPON REQUIRED",
            notes=["The historical wedge inventory name maps to this captive bayonet key; no loose straight wedge is emitted."],
            design_metrics={
                **common,
                "quantity_per_level": top_count,
                "quantity_selected_two_levels": selected_top_count,
            },
        ),
        PrototypePart(
            name="R6_DEV_FINAL_X_SPRING_RETENTION_WEDGE_UNIVERSAL",
            mesh=mesh.copy(),
            purpose="Universal visible-front positive quarter-turn cross-key for one arch-spring tenon interface.",
            saved_orientation="locked crossbar and U-routed handle broad faces on build plate; shaft axis parallel to plate",
            status="DEVELOPMENT POSITIVE CROSS-KEY; RETENTION ONLY; ZERO LOAD CREDIT; ACTUAL-PARENT COUPON REQUIRED",
            notes=["The historical wedge inventory name maps to this captive bayonet key; no loose straight wedge is emitted."],
            design_metrics={
                **common,
                "quantity_per_level": spring_count,
                "quantity_selected_two_levels": selected_spring_count,
            },
        ),
    ]


def final_x_corbel_variant(
    cfg: dict[str, Any],
    geometry: Any,
    *,
    variant: str,
    quantity_per_level: int,
    selected_levels: int,
) -> PrototypePart:
    """One monolithic X-corbel with compact clevis and integral bearing cap."""

    if variant not in {"interior", "run_start", "run_end"}:
        raise ValueError(f"Unknown corbel family variant {variant!r}")
    corbel_cfg = cfg["corbel"]
    cap_cfg = corbel_cfg["integrated_bearing_cap"]
    lock_cfg = corbel_cfg["integrated_cap_cassette_lock"]
    print_cfg = corbel_cfg["print_connectivity_contract"]
    spring_joint = cfg["tied_arcade"]["spring_final_x_vertical_joint"]
    ornament_contract = ornament_interface_contract(cfg)
    pier_parent_map = cfg["palatine"]["ornament_keyhole_contract"][
        "per_parent_boss_placement_map"
    ]["pier_overlay"]
    if corbel_cfg["separate_sliding_saddle_installed"] or corbel_cfg["separate_saddle_pin_installed"]:
        raise ValueError("The integrated-cap baseline may not emit a saddle or saddle pin")

    projection = float(geometry.projection_mm)
    wall_upper = tuple(float(value) for value in geometry.wall_upper_node)
    front_spring = tuple(float(value) for value in geometry.front_spring_node)
    wall_lower = tuple(float(value) for value in geometry.wall_lower_node)
    front_saddle = tuple(float(value) for value in geometry.front_saddle_node)
    base_thickness = float(corbel_cfg["body_thickness_mm"])
    base_half = base_thickness / 2.0
    wall_chord = float(corbel_cfg["wall_contact_chord_mm"])
    brace_chord = float(corbel_cfg["x_brace_chord_mm"])
    wall_bottom = float(corbel_cfg["wall_plate_bottom_y_mm"])
    wall_top = float(corbel_cfg["wall_plate_top_y_mm"])
    cassette_under = float(cfg["tied_arcade"]["cassette_entablature_bottom_y_mm"])
    boss_diameter = float(corbel_cfg["minimum_crossing_boss_diameter_mm"])
    crossing = tuple(float(value) for value in corbel_cfg["x_brace_crossing_mm"])

    closet_runs = cfg["closet"]["runs"]
    back_clearances = {
        round(float(record["reference_shelf_back_clearance_in"]) * 25.4, 7)
        for record in closet_runs
    }
    if len(back_clearances) != 1:
        raise ValueError("Shared corbel family requires one shelf-back clearance")
    back_clearance = back_clearances.pop()

    spring_contract = spring_socket_contract(cfg)
    receiver_interval = tuple(float(value) for value in spring_contract["receiver_q_wall_mm"])
    housing_interval = tuple(float(value) for value in spring_contract["housing_q_wall_mm"])
    receiver_depth = receiver_interval[1] - receiver_interval[0]
    housing_depth = housing_interval[1] - housing_interval[0]
    receiver_width = float(spring_joint["receiver_run_width_mm"])
    wedge_run, wedge_e = (
        float(value) for value in spring_joint["retention_wedge_hole_run_y_mm"]
    )
    wedge_center_e = float(spring_joint["retention_wedge_center_y_mm"])
    housing_e = tuple(float(value) for value in spring_joint["receiver_housing_y_envelope_mm"])
    if housing_e != tuple(float(value) for value in spring_joint["tenon_final_y_envelope_mm"]):
        raise ValueError("Compact clevis and spring tenon must share e=46..68")

    housing_by_variant = {
        "interior": [tuple(float(v) for v in pair) for pair in cap_cfg["interior_spring_housing_run_envelopes_mm"]],
        "run_start": [tuple(float(v) for v in cap_cfg["run_start_terminal_spring_housing_run_envelope_mm"])],
        "run_end": [tuple(float(v) for v in cap_cfg["run_end_terminal_spring_housing_run_envelope_mm"])],
    }
    housing_run_envelopes = housing_by_variant[variant]
    socket_offsets = [sum(pair) / 2.0 for pair in housing_run_envelopes]
    expected_offsets = {
        "interior": [-14.4, 14.4],
        "run_start": [14.4],
        "run_end": [-14.4],
    }[variant]
    if not np.allclose(socket_offsets, expected_offsets, atol=1.0e-7, rtol=0.0):
        raise ValueError("Compact clevis handing/centering does not match spring sockets")

    cap_base_s = tuple(float(value) for value in cap_cfg["base_run_envelope_at_e_128_mm"])
    cap_top_s = tuple(float(value) for value in cap_cfg["top_run_envelope_at_e_138_mm"])
    cap_e = tuple(float(value) for value in cap_cfg["vertical_envelope_mm"])
    overall_s_min = min(cap_top_s[0], *(pair[0] for pair in housing_run_envelopes))
    overall_s_max = max(cap_top_s[1], *(pair[1] for pair in housing_run_envelopes))

    nonhousing_descending_max_xwall = float(
        spring_contract["nonhousing_descending_xwall_clip_mm"]
    )
    nonhousing_to_moving_arch_clearance = float(
        spring_contract["nonhousing_to_moving_arch_clearance_mm"]
    )
    if (
        abs(nonhousing_descending_max_xwall - 140.35) > 1.0e-7
        or abs(nonhousing_to_moving_arch_clearance - 0.4) > 1.0e-7
    ):
        raise ValueError("Compact-clevis descending-X rear clearance datum drift")
    descending = LineString([wall_upper, front_spring]).buffer(
        brace_chord / 2.0, cap_style=1, join_style=1, quad_segs=12
    ).intersection(
        shapely_box(0.0, 0.0, nonhousing_descending_max_xwall, wall_top)
    )
    rising = LineString([wall_lower, front_saddle]).buffer(
        brace_chord / 2.0, cap_style=1, join_style=1, quad_segs=12
    ).intersection(shapely_box(0.0, 0.0, projection, cassette_under))

    cap_profile_points = [
        tuple(float(value) for value in pair)
        for pair in cap_cfg["run_e_profile_polygon_mm"]
    ]
    cap_profile = Polygon(cap_profile_points)
    if cap_profile.bounds != (
        cap_top_s[0],
        cap_e[0],
        cap_top_s[1],
        cap_e[1],
    ):
        raise ValueError("Integral-cap exact run/e profile envelope drift")
    cap_mesh = extrude_polygon(cap_profile, projection)
    cap_mesh.apply_transform(
        np.asarray(
            [
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
    )
    # Above the cassette underside, retain only the exact 6.35 mm wall-back
    # clearance thickness.  The former 12 mm wall plate and front pier both
    # intruded into every cassette; the lower wall plate remains 12 mm deep.
    descending_mesh = extrude_polygon(descending, base_thickness, z0=-base_half)
    components: list[trimesh.Trimesh] = [
        cuboid(
            (wall_chord, cassette_under - wall_bottom, base_thickness),
            origin=(0.0, wall_bottom, -base_half),
        ),
        cuboid(
            (back_clearance, wall_top - cassette_under + 0.2, base_thickness),
            origin=(0.0, cassette_under - 0.2, -base_half),
        ),
        descending_mesh,
        extrude_polygon(rising, base_thickness, z0=-base_half),
        cylinder_z(
            boss_diameter,
            base_thickness,
            center_xy=crossing,
            z0=-base_half,
        ),
        cap_mesh,
    ]
    plate_s, plate_e, plate_source_z = (
        tuple(float(value) for value in envelope)
        for envelope in pier_parent_map[
            "parent_interface_plate_run_e_source_z_envelopes_mm"
        ]
    )
    if (
        plate_s != (-17.2, 17.2)
        or plate_e != (0.0, 60.0)
        or plate_source_z != (0.0, 1.6)
    ):
        raise ValueError("Pier ornament interface plate envelope drift")
    visible_front_xwall = (
        number(cfg, "closet.shelf_depth_in", 6.0) * 25.4
        + back_clearance
    )
    plate_xwall = (
        visible_front_xwall - plate_source_z[1],
        visible_front_xwall - plate_source_z[0],
    )
    plate = cuboid(
        (
            plate_xwall[1] - plate_xwall[0],
            plate_e[1] - plate_e[0],
            plate_s[1] - plate_s[0],
        ),
        origin=(plate_xwall[0], plate_e[0], plate_s[0]),
    )
    components.append(plate)
    # Grow each compact receiver housing continuously from the already
    # printable 28 mm X section.  In the wall-back saved orientation xwall is
    # build Z: this exact 126.35 -> 140.75 transition advances no exterior
    # run/elevation face by more than one millimetre per build millimetre.
    # A 0.4 mm constant terminal section overlaps each housing in positive
    # volume, avoiding both a face-only union and detached outer-wing layers.
    transition_x0 = 126.35
    transition_x1 = housing_interval[0]
    transition_x2 = transition_x1 + 0.4
    transition_center_e = wall_upper[1] + (
        (front_spring[1] - wall_upper[1])
        / (front_spring[0] - wall_upper[0])
    ) * transition_x0
    transition_e0 = transition_center_e - brace_chord / 2.0
    transition_e1 = transition_center_e + brace_chord / 2.0
    housing_transition_records: list[dict[str, Any]] = []
    for run_envelope in housing_run_envelopes:
        if sum(run_envelope) > 0.0:
            source_run = (0.0, base_half)
        else:
            source_run = (-base_half, 0.0)
        transition_points = np.asarray(
            [
                [xwall, elevation, across_run]
                for xwall, elevation_range, run_range in (
                    (transition_x0, (transition_e0, transition_e1), source_run),
                    (transition_x1, housing_e, run_envelope),
                    (transition_x2, housing_e, run_envelope),
                )
                for elevation in elevation_range
                for across_run in run_range
            ],
            dtype=float,
        )
        transition = trimesh.convex.convex_hull(transition_points)
        if not transition.is_watertight or not transition.is_volume:
            raise ValueError("Compact-clevis print transition is not one solid")
        transition_union = trimesh.boolean.intersection(
            [descending_mesh, transition], engine="manifold", check_volume=True
        )
        transition_union_volume = (
            0.0
            if transition_union is None
            or len(transition_union.faces) < 4
            or not transition_union.is_watertight
            else abs(float(transition_union.volume))
        )
        if transition_union_volume <= 1.0e-4:
            raise ValueError(
                "Compact-clevis print transition lost its positive-volume "
                "union with the descending X"
            )
        components.append(transition)
        components.append(
            cuboid(
                (
                    housing_depth,
                    housing_e[1] - housing_e[0],
                    run_envelope[1] - run_envelope[0],
                ),
                origin=(housing_interval[0], housing_e[0], run_envelope[0]),
            )
        )
        housing_transition_records.append(
            {
                "source_xwall_mm": transition_x0,
                "housing_xwall_mm": transition_x1,
                "positive_union_overlap_mm": transition_x2 - transition_x1,
                "descending_x_positive_union_volume_mm3": round(
                    transition_union_volume, 6
                ),
                "source_run_envelope_mm": list(source_run),
                "housing_run_envelope_mm": list(run_envelope),
                "source_e_envelope_mm": [transition_e0, transition_e1],
                "housing_e_envelope_mm": list(housing_e),
                "maximum_run_advance_per_build_mm": max(
                    abs(run_envelope[0] - source_run[0]),
                    abs(run_envelope[1] - source_run[1]),
                )
                / (transition_x1 - transition_x0),
                "maximum_e_advance_per_build_mm": max(
                    abs(housing_e[0] - transition_e0),
                    abs(housing_e[1] - transition_e1),
                )
                / (transition_x1 - transition_x0),
            }
        )

    ridge_width = float(corbel_cfg["saddle_locator_ridge_run_width_mm"])
    ridge_depth = float(corbel_cfg["saddle_locator_ridge_depth_along_shelf_mm"])
    ridge_height = float(corbel_cfg["saddle_locator_ridge_height_mm"])
    ridge_centers_q = tuple(float(v) for v in corbel_cfg["saddle_locator_centers_from_rear_mm"])
    for center_q in ridge_centers_q:
        components.append(
            cuboid(
                (ridge_depth, ridge_height + 0.2, ridge_width),
                origin=(
                    center_q + back_clearance - ridge_depth / 2.0,
                    cassette_under - 0.2,
                    -ridge_width / 2.0,
                ),
            )
        )

    local_cross_key_boss, local_cross_key_cutters, cross_key_metrics = (
        positive_cross_key_receiver_local_geometry(cfg)
    )
    spring_cross_key_cutters: list[trimesh.Trimesh] = []
    spring_cross_key_boss_meshes: list[trimesh.Trimesh] = []
    spring_cross_key_records: list[dict[str, Any]] = []
    for center_s in socket_offsets:
        receiver_from_key_local = np.asarray(
            [
                [0.0, 0.0, -1.0, visible_front_xwall],
                [0.0, 1.0, 0.0, wedge_center_e],
                [1.0, 0.0, 0.0, center_s],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        boss_parent = local_cross_key_boss.copy()
        boss_parent.apply_transform(receiver_from_key_local)
        boss_parent = clean_mesh_preserve_coordinates(boss_parent)
        spring_cross_key_boss_meshes.append(boss_parent)
        components.append(boss_parent)
        for local_cutter in local_cross_key_cutters:
            cutter_parent = local_cutter.copy()
            cutter_parent.apply_transform(receiver_from_key_local)
            spring_cross_key_cutters.append(
                clean_mesh_preserve_coordinates(cutter_parent)
            )
        spring_cross_key_records.append(
            {
                "center_across_run_from_support_mm": center_s,
                "center_e_mm": wedge_center_e,
                "visible_parent_face_xwall_mm": visible_front_xwall,
                "parent_from_key_local_matrix_row_major": (
                    receiver_from_key_local.tolist()
                ),
                "receiver": dict(cross_key_metrics),
            }
        )

    parent_blank = safe_union_installed(
        components, f"{variant} compact-clevis integrated-cap X-corbel"
    )
    depth_reference_xwall = visible_front_xwall + float(
        ornament_contract.global_depth_offset_mm
    )
    compact_boss_centers = [
        (float(center[0]), float(center[1]))
        for center in pier_parent_map[
            "locked_boss_centers_parent_local_run_e_mm"
        ]
    ]
    locator_center = tuple(
        float(value)
        for value in pier_parent_map[
            "locked_locator_center_parent_local_run_e_mm"
        ]
    )
    if len(compact_boss_centers) != 2 or len(locator_center) != 2:
        raise ValueError(
            "Pier overlay parent needs two compact gravity bosses and one "
            "noncapturing loose locator"
        )
    compact_boss_meshes: list[trimesh.Trimesh] = []
    boss_to_raw = np.asarray(
        [
            [0.0, 0.0, -1.0, depth_reference_xwall],
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    for center_s, center_e in compact_boss_centers:
        boss = compact_pier_gravity_keyhole_boss_mesh(
            cfg, center_s, center_e
        )
        boss.apply_transform(boss_to_raw)
        compact_boss_meshes.append(clean_mesh_preserve_coordinates(boss))
    locator_mesh = noncapturing_loose_locator_post_mesh(
        cfg, locator_center[0], locator_center[1]
    )
    locator_mesh.apply_transform(boss_to_raw)
    locator_mesh = clean_mesh_preserve_coordinates(locator_mesh)
    attachment_feature_meshes = [*compact_boss_meshes, locator_mesh]
    ornament_cross_key_feature_overlaps = [
        sum(
            positive_solid_intersection_volume_mm3(
                ornament_boss, cross_key_boss
            )
            for cross_key_boss in spring_cross_key_boss_meshes
        )
        for ornament_boss in attachment_feature_meshes
    ]
    blank, compact_boss_union_volumes = union_integral_ornament_bosses(
        parent_blank,
        compact_boss_meshes,
        minimum_overlap_mm3=float(
            cfg["ornament_isolation"][
                "minimum_compact_pier_boss_neck_parent_union_volume_mm3"
            ]
        ),
        label=f"{variant} X-corbel pier plate compact gravity bosses",
        overlap_reference=plate,
    )
    blank, locator_union_volumes = union_integral_ornament_bosses(
        blank,
        [locator_mesh],
        minimum_overlap_mm3=float(
            ornament_contract.parent_boss_union_volume_mm3
        ),
        label=f"{variant} X-corbel pier plate loose locator",
        overlap_reference=plate,
    )
    boss_union_volumes = [
        *compact_boss_union_volumes,
        *locator_union_volumes,
    ]
    blank_volume = float(blank.volume)
    cutters: list[trimesh.Trimesh] = list(spring_cross_key_cutters)
    socket_records: list[dict[str, Any]] = []
    for index, center_s in enumerate(socket_offsets, start=1):
        cutters.append(
            cuboid(
                (receiver_depth, housing_e[1] - housing_e[0] + 0.4, receiver_width),
                origin=(
                    receiver_interval[0],
                    housing_e[0] - 0.2,
                    center_s - receiver_width / 2.0,
                ),
            )
        )
        socket_records.append(
            {
                "index": index,
                "center_across_run_from_support_mm": center_s,
                "receiver_run_width_mm": receiver_width,
                "receiver_depth_mm": receiver_depth,
                "receiver_center_from_wall_mm": sum(receiver_interval) / 2.0,
                "receiver_center_q_from_cassette_rear_mm": sum(receiver_interval) / 2.0 - back_clearance,
                "receiver_vertical_envelope_e_mm": list(housing_e),
                "open_bottom": True,
                "wedge_access_axis": str(spring_joint["retention_wedge_axis"]),
                "positive_cross_key_receiver": dict(cross_key_metrics),
            }
        )

    cap_bore_run, cap_bore_q = (float(v) for v in lock_cfg["cap_bore_run_q_mm"])
    cap_bore_e = tuple(float(v) for v in lock_cfg["cap_bore_y_envelope_mm"])
    lock_centers = (
        tuple(float(v) for v in lock_cfg["cornerward_lock_center_s_q_mm"]),
        tuple(float(v) for v in lock_cfg["outboard_lock_center_s_q_mm"]),
    )
    for center_s, center_q in lock_centers:
        cutters.append(
            cuboid(
                (cap_bore_q, cap_bore_e[1] - cap_bore_e[0] + 0.4, cap_bore_run),
                origin=(
                    center_q + back_clearance - cap_bore_q / 2.0,
                    cap_bore_e[0] - 0.2,
                    center_s - cap_bore_run / 2.0,
                ),
            )
        )

    raw_mesh = safe_difference_installed(
        blank,
        cutters,
        f"{variant} compact clevis sockets, wedge paths, and cap-lock bores",
    )
    removed_volume = blank_volume - float(raw_mesh.volume)
    minimum_removed = len(socket_offsets) * receiver_depth * (housing_e[1] - housing_e[0]) * receiver_width
    minimum_removed += len(lock_centers) * cap_bore_run * cap_bore_q * (cap_bore_e[1] - cap_bore_e[0])
    if removed_volume + 1.0e-5 < minimum_removed:
        raise ValueError(f"{variant}: compact-clevis/cap bores did not cut real solids")

    # Saved axes are (e, s, xwall): the wall-back xwall=0 face is the build
    # plane.  This avoids the false broad-side orientation where nearly the
    # entire X body began 14.4 mm above the bed.
    saved_source_e_min = float(blank.bounds[0][1])
    if abs(saved_source_e_min - plate_e[0]) > 1.0e-7:
        raise ValueError("Pier plate is not the saved corbel elevation datum")
    saved_from_raw = np.asarray(
        [
            [0.0, 1.0, 0.0, -saved_source_e_min],
            [0.0, 0.0, 1.0, -overall_s_min],
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    raw_from_saved = np.linalg.inv(saved_from_raw)
    raw_mesh.apply_transform(saved_from_raw)
    mesh = finish_mesh(raw_mesh)
    expected_saved = np.asarray(
        [
            wall_top - saved_source_e_min,
            overall_s_max - overall_s_min,
            float(print_cfg["maximum_build_height_mm"]),
        ],
        dtype=float,
    )
    if not np.allclose(mesh.extents, expected_saved, atol=1.0e-5, rtol=0.0):
        raise ValueError(
            f"{variant}: wall-back saved envelope {mesh.extents.tolist()} != "
            f"{expected_saved.tolist()}"
        )

    label = {
        "interior": "INTERIOR_DUAL_SOCKET",
        "run_start": "RUN_START_TERMINAL",
        "run_end": "RUN_END_TERMINAL",
    }[variant]
    return PrototypePart(
        name=f"R6_DEV_FINAL_X_X_CORBEL_PIER_{label}_INTEGRATED_CAP",
        mesh=mesh,
        purpose="Wall-back-printed 3:4:5 X-corbel with compact spring clevis, full-width integral bearing cap, two locator ridges, and two cassette-lock bores.",
        saved_orientation="wall-back xwall=0 face on build plate; installed elevation and run lie in the bed plane",
        status="DEVELOPMENT SUPPORT; ZERO PRODUCTION BORES; PRINT-CLOSURE COUPON REQUIRED; NO LOAD RATING",
        notes=[
            "The redundant full-height front pier and separate saddle/saddle pin are deleted.",
            "The wall plate is stepped behind the cassette and retains zero production screw bores.",
            "The spring-cheek closure, locator-ridge births, cap-lock bore roofs, and cap transition each remain explicit same-PETG print-coupon/slicer gates; support-free or support-light printing is not claimed.",
        ],
        design_metrics={
            "family": "final_x_x_corbel_pier_integrated_cap",
            "variant": variant,
            "quantity_per_level": quantity_per_level,
            "quantity_selected_two_levels": selected_levels * quantity_per_level,
            "socket_count": len(socket_offsets),
            "spring_receivers": socket_records,
            "integral_spring_cross_key_boss_count": len(
                spring_cross_key_records
            ),
            "integral_spring_cross_key_bosses": spring_cross_key_records,
            "spring_receiver_center_from_wall_mm": sum(receiver_interval) / 2.0,
            "spring_receiver_center_q_from_cassette_rear_mm": sum(receiver_interval) / 2.0 - back_clearance,
            "spring_receiver_wall_projection_interval_mm": list(receiver_interval),
            "spring_receiver_housing_wall_projection_interval_mm": list(housing_interval),
            "spring_receiver_housing_e_interval_mm": list(housing_e),
            "compact_clevis_run_envelopes_from_support_mm": [list(pair) for pair in housing_run_envelopes],
            "compact_clevis_print_transitions": housing_transition_records,
            "compact_clevis_transition_maximum_run_advance_per_build_mm": max(
                record["maximum_run_advance_per_build_mm"]
                for record in housing_transition_records
            ),
            "compact_clevis_transition_maximum_e_advance_per_build_mm": max(
                record["maximum_e_advance_per_build_mm"]
                for record in housing_transition_records
            ),
            "nonhousing_descending_xwall_clip_mm": nonhousing_descending_max_xwall,
            "rising_x_clipped_at_cassette_underside_e_mm": cassette_under,
            "source_run_envelope_from_support_mm": [overall_s_min, overall_s_max],
            "base_x_brace_body_thickness_mm": base_thickness,
            "crossing_boss_diameter_mm": boss_diameter,
            "crossing_union_boss_minimum_satisfied": boss_diameter >= 24.0,
            "full_height_front_pier_present": False,
            "integrated_bearing_cap": dict(cap_cfg),
            "integrated_locator_ridge_count": len(ridge_centers_q),
            "integrated_locator_ridge_run_q_height_mm": [ridge_width, ridge_depth, ridge_height],
            "integrated_locator_q_centers_from_cassette_rear_mm": list(ridge_centers_q),
            "integrated_cap_lock_bore_count": len(lock_centers),
            "integrated_cap_lock_centers_s_q_from_support_and_rear_mm": [list(item) for item in lock_centers],
            "ornament_parent_family_id": "pier_overlay",
            "integral_ornament_interface_plate_run_e_source_z_envelopes_mm": [
                list(plate_s),
                list(plate_e),
                list(plate_source_z),
            ],
            "integral_ornament_interface_plate_xwall_envelope_mm": list(
                plate_xwall
            ),
            "integral_ornament_boss_count": len(attachment_feature_meshes),
            "integral_ornament_compact_gravity_boss_count": len(
                compact_boss_meshes
            ),
            "integral_ornament_noncapturing_loose_locator_count": 1,
            "integral_ornament_boss_centers_parent_local_run_e_mm": [
                list(center) for center in compact_boss_centers
            ],
            "integral_ornament_loose_locator_center_parent_local_run_e_mm": list(
                locator_center
            ),
            "integral_ornament_attachment_feature_types": [
                "compact_gravity_keyhole",
                "compact_gravity_keyhole",
                "noncapturing_loose_locator",
            ],
            "integral_ornament_boss_parent_union_volumes_mm3": [
                round(value, 9) for value in boss_union_volumes
            ],
            "integral_ornament_boss_parent_overlap_mm": float(
                ornament_contract.parent_union_overlap_mm
            ),
            "ornament_to_cross_key_parent_feature_overlap_volumes_mm3": [
                round(value, 6)
                for value in ornament_cross_key_feature_overlaps
            ],
            "ornament_to_cross_key_parent_feature_overlap_requires_aperture": (
                max(ornament_cross_key_feature_overlaps, default=0.0) > 1.0e-5
            ),
            "integral_ornament_boss_structural_credit": False,
            "production_wall_screw_bore_count": 0,
            "wall_plate_solid": True,
            "upper_wall_plate_depth_above_cassette_underside_mm": back_clearance,
            "minimum_straight_service_access_mm": float(spring_joint["minimum_straight_service_access_mm"]),
            "upper_diagonal_cassette_union_receiver_generated": False,
            "saved_from_raw_installed_matrix_row_major": saved_from_raw.tolist(),
            "raw_installed_from_saved_matrix_row_major": raw_from_saved.tolist(),
            "saved_source_e_min_mm": saved_source_e_min,
            "saved_build_face": "xwall=0 wall-back face",
            "saved_bed_envelope_with_6mm_brim_mm": print_cfg["saved_bed_envelope_with_6_mm_brim_mm"],
            "saved_maximum_build_height_mm": print_cfg["maximum_build_height_mm"],
            "per_layer_connectivity_required": bool(print_cfg["per_layer_connectivity_required"]),
            "support_free_claim_allowed": bool(print_cfg["support_free_claim_allowed"]),
            "print_connectivity_named_exception": str(print_cfg["named_exception"]),
            "print_connectivity_named_exceptions": [
                str(print_cfg["named_exception"]),
                "two abrupt 7 mm locator-ridge onsets in the wall-back build direction",
                "two cap-lock bore closure roofs",
                "local support transitions around the locator and lock exception zones",
            ],
            "support_light_claim_allowed": False,
            "actual_parent_orientation_print_coupon_required": True,
            "installed_coordinate_receiver_and_lock_removed_volume_mm3": round(removed_volume, 6),
            "installed_coordinate_minimum_expected_removed_volume_mm3": round(minimum_removed, 6),
        },
    )


def final_x_corbel_family(
    cfg: dict[str, Any], geometry: Any, *, plan: Any, selected_levels: int
) -> list[PrototypePart]:
    run_count = len((plan.through, plan.return_run))
    quantities = {
        "interior": sum(
            int(run.bay_count) - 1 for run in (plan.through, plan.return_run)
        ),
        "run_start": run_count,
        "run_end": run_count,
    }
    parts = [
        final_x_corbel_variant(
            cfg,
            geometry,
            variant=variant,
            quantity_per_level=quantities[variant],
            selected_levels=selected_levels,
        )
        for variant in ("interior", "run_start", "run_end")
    ]
    spring_center_e = number(
        cfg, "tied_arcade.spring_final_x_vertical_joint.retention_wedge_center_y_mm", 57.0
    )
    crownward_offset = float(spring_socket_contract(cfg)["support_offset_mm"])
    for part in parts:
        metrics = part.design_metrics
        variant = str(metrics["variant"])
        saved_source_e_min = float(metrics["saved_source_e_min_mm"])
        source_s_min = float(metrics["source_run_envelope_from_support_mm"][0])
        socket_centers = [
            float(record["center_across_run_from_support_mm"])
            for record in metrics["spring_receivers"]
        ]
        placement_records: list[dict[str, Any]] = []
        center_errors: list[float] = []
        for run in (plan.through, plan.return_run):
            support_stations = tuple(
                float(value) for value in run.support_centers_local_mm
            )
            if variant == "run_start":
                stations_and_targets = [
                    (support_stations[0], [crownward_offset])
                ]
            elif variant == "run_end":
                stations_and_targets = [
                    (support_stations[-1], [-crownward_offset])
                ]
            else:
                stations_and_targets = [
                    (station, [-crownward_offset, crownward_offset])
                    for station in support_stations[1:-1]
                ]
            for station, target_offsets in stations_and_targets:
                if len(target_offsets) != len(socket_centers):
                    raise AssertionError("Corbel socket/placement topology drift")
                saved_to_run = np.asarray(
                    [
                        [0.0, 1.0, 0.0, station + source_s_min],
                        [0.0, 0.0, 1.0, -float(metrics["upper_wall_plate_depth_above_cassette_underside_mm"])],
                        [1.0, 0.0, 0.0, saved_source_e_min],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                    dtype=float,
                )
                socket_errors: list[float] = []
                for socket_center, target_offset in zip(
                    socket_centers, target_offsets
                ):
                    actual = saved_to_run @ np.asarray(
                        [
                            spring_center_e - saved_source_e_min,
                            socket_center - source_s_min,
                            float(metrics["spring_receiver_center_from_wall_mm"]),
                            1.0,
                        ],
                        dtype=float,
                    )
                    expected = np.asarray(
                        [
                            station + target_offset,
                            float(metrics["spring_receiver_center_q_from_cassette_rear_mm"]),
                            spring_center_e,
                        ],
                        dtype=float,
                    )
                    error = float(np.linalg.norm(actual[:3] - expected))
                    if error >= 1.0e-7:
                        raise ValueError(
                            f"{run.run_id} {variant} spring socket misses by "
                            f"{error:.12g} mm"
                        )
                    socket_errors.append(error)
                    center_errors.append(error)
                placement_records.append(
                    {
                        "run_id": str(run.run_id),
                        "support_station_local_s_mm": station,
                        "saved_to_run_matrix_row_major": saved_to_run.tolist(),
                        "target_socket_offsets_from_support_mm": target_offsets,
                        "socket_center_errors_mm": socket_errors,
                    }
                )
        metrics["authoritative_instance_placements"] = placement_records
        metrics["maximum_spring_socket_center_alignment_error_mm"] = max(
            center_errors, default=0.0
        )
    return parts


def validate_inside_corner_l_assembly_clearance(
    cfg: dict[str, Any],
    *,
    plan: Any,
    cassettes: Iterable[PrototypePart],
    corbels: Iterable[PrototypePart],
) -> dict[str, Any]:
    """Boolean-prove the two perpendicular run-start assemblies at the L."""

    cassette_by_key = {
        (
            str(part.design_metrics["run_id"]),
            int(part.design_metrics["position_index_1_based"]),
        ): part
        for part in cassettes
    }
    run_start = next(
        part for part in corbels if part.design_metrics.get("variant") == "run_start"
    )
    corbel_placement_by_run = {
        str(record["run_id"]): record
        for record in run_start.design_metrics["authoritative_instance_placements"]
    }
    through = plan.through
    return_run = plan.return_run
    through_cassette = cassette_by_key[(str(through.run_id), 1)]
    return_cassette = cassette_by_key[(str(return_run.run_id), 1)]
    back_clearance = float(plan.through_back_clearance_mm)
    through_run_to_l = np.asarray(
        [
            [1.0, 0.0, 0.0, float(through.start_from_corner_mm)],
            [0.0, 1.0, 0.0, back_clearance],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    return_run_to_l = np.asarray(
        [
            [0.0, 1.0, 0.0, back_clearance],
            [1.0, 0.0, 0.0, float(return_run.start_from_corner_mm)],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )

    def installed_cassette(
        part: PrototypePart, run_to_l: np.ndarray
    ) -> tuple[trimesh.Trimesh, np.ndarray]:
        transform = run_to_l @ np.asarray(
            part.design_metrics["saved_print_transform"][
                "saved_to_run_matrix_row_major"
            ],
            dtype=float,
        )
        mesh = part.mesh.copy()
        mesh.apply_transform(transform)
        return mesh, transform

    def installed_corbel(
        run_id: str, run_to_l: np.ndarray
    ) -> tuple[trimesh.Trimesh, np.ndarray]:
        transform = run_to_l @ np.asarray(
            corbel_placement_by_run[run_id]["saved_to_run_matrix_row_major"],
            dtype=float,
        )
        mesh = run_start.mesh.copy()
        mesh.apply_transform(transform)
        return mesh, transform

    t_cassette, t_cassette_matrix = installed_cassette(
        through_cassette, through_run_to_l
    )
    r_cassette, r_cassette_matrix = installed_cassette(
        return_cassette, return_run_to_l
    )
    t_corbel, t_corbel_matrix = installed_corbel(
        str(through.run_id), through_run_to_l
    )
    r_corbel, r_corbel_matrix = installed_corbel(
        str(return_run.run_id), return_run_to_l
    )
    cross_pairs = (
        (t_cassette, r_cassette, "through cassette / return cassette"),
        (t_cassette, r_corbel, "through cassette / return run-start corbel"),
        (t_corbel, r_cassette, "through run-start corbel / return cassette"),
        (t_corbel, r_corbel, "through / return run-start corbels"),
    )
    maximum_final_overlap = 0.0
    for left, right, label in cross_pairs:
        overlap = positive_solid_intersection_volume_mm3(left, right)
        maximum_final_overlap = max(maximum_final_overlap, overlap)
        if overlap > 1.0e-5:
            raise ValueError(
                f"Inside-corner final {label} overlap is {overlap:.9f} mm3"
            )

    # Sample both sides of the e=138 bearing plane.  These are conservative
    # cross-run checks only: they deliberately do not reinterpret the normal
    # same-corbel hard stop or authorize cassette travel below its final seat.
    seating_deltas = np.asarray([-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0])
    maximum_sweep_overlap = 0.0
    sweep_pair_count = 0
    for moving_source, fixed_corbel, label in (
        (t_cassette, r_corbel, "through cassette / return corbel"),
        (r_cassette, t_corbel, "return cassette / through corbel"),
    ):
        for delta_e in seating_deltas:
            moving = moving_source.copy()
            moving.apply_translation([0.0, 0.0, float(delta_e)])
            overlap = positive_solid_intersection_volume_mm3(
                moving, fixed_corbel
            )
            maximum_sweep_overlap = max(maximum_sweep_overlap, overlap)
            if overlap > 1.0e-5:
                raise ValueError(
                    f"Inside-corner {label} e sweep {delta_e:+.1f} mm "
                    f"overlaps by {overlap:.9f} mm3"
                )
            sweep_pair_count += 1

    exact_corbel_gap = float(plan.minimum_perpendicular_corbel_clearance_mm)
    visible_front_reserve = float(
        plan.minimum_visible_front_to_perpendicular_corbel_plan_reserve_mm
    )
    snapshot = cfg["nominal_geometry_snapshot"]
    configured_corbel_gap = float(
        snapshot["minimum_nominal_perpendicular_corbel_clearance_mm"]
    )
    configured_visible_reserve = float(
        snapshot[
            "minimum_nominal_visible_front_to_perpendicular_corbel_plan_reserve_mm"
        ]
    )
    if abs(exact_corbel_gap - configured_corbel_gap) > 1.0e-7:
        raise ValueError("Inside-corner corbel gap differs from the config snapshot")
    if abs(visible_front_reserve - configured_visible_reserve) > 1.0e-7:
        raise ValueError(
            "Inside-corner actual-visible-front/cap reserve differs from config"
        )
    return {
        "status": "PASS: REAL PERPENDICULAR INSIDE-CORNER FINAL AND E-SWEEP BOOLEANS",
        "coordinate_axes": "global L plan X=through wall, Y=return wall, e=up",
        "through_cassette_saved_to_global_l_matrix_row_major": (
            t_cassette_matrix.tolist()
        ),
        "return_cassette_saved_to_global_l_matrix_row_major": (
            r_cassette_matrix.tolist()
        ),
        "through_run_start_corbel_saved_to_global_l_matrix_row_major": (
            t_corbel_matrix.tolist()
        ),
        "return_run_start_corbel_saved_to_global_l_matrix_row_major": (
            r_corbel_matrix.tolist()
        ),
        "run_start_terminal_handing": {
            "through_socket_offset_from_support_mm": 14.4,
            "return_socket_offset_from_support_mm": 14.4,
        },
        "final_cross_pair_count": len(cross_pairs),
        "maximum_final_positive_overlap_volume_mm3": round(
            maximum_final_overlap, 9
        ),
        "seating_sweep_e_deltas_mm": seating_deltas.tolist(),
        "seating_sweep_boolean_pair_count": sweep_pair_count,
        "maximum_seating_sweep_positive_overlap_volume_mm3": round(
            maximum_sweep_overlap, 9
        ),
        "exact_corbel_to_corbel_plan_gap_mm": exact_corbel_gap,
        "visible_front_projection_beyond_cassette_mm": float(
            plan.visible_front_projection_beyond_cassette_mm
        ),
        "structural_arm_clearance_mm": float(
            plan.structural_arm_clearance_mm
        ),
        "exact_actual_visible_front_to_perpendicular_cap_plan_reserve_mm": (
            visible_front_reserve
        ),
    }


def final_x_saddle_variant(
    cfg: dict[str, Any],
    *,
    variant: str,
    quantity_per_level: int,
    selected_levels: int,
) -> PrototypePart:
    if variant not in {"interior", "run_start", "run_end"}:
        raise ValueError(f"Unknown saddle variant {variant!r}")
    dims = deep_get(cfg, "corbel.sliding_saddle_mm", None)
    if not isinstance(dims, list) or len(dims) != 3:
        raise ValueError("corbel.sliding_saddle_mm must contain three values")
    width, depth, height = (positive(float(value), "saddle dimension") for value in dims)
    locator = saddle_locator_spec(cfg)
    ridge_width = float(locator["ridge_width_along_run_mm"])
    ridge_depth = float(locator["ridge_depth_along_shelf_mm"])
    ridge_height = float(locator["ridge_height_mm"])
    centers = tuple(float(value) for value in locator["centers_from_rear_mm"])
    components = [rounded_prism(width, depth, height, min(2.0, height / 3.0))]
    for center in centers:
        components.append(
            cuboid(
                (ridge_width, ridge_depth, ridge_height),
                origin=((width - ridge_width) / 2.0, center - ridge_depth / 2.0, height),
            )
        )
    mesh = safe_union(components, f"{variant} final-X saddle with ridges")
    return PrototypePart(
        name=f"R6_DEV_FINAL_X_SADDLE_{variant.upper()}_TWO_LOCATOR_RIDGES",
        mesh=mesh,
        purpose="Broad-bearing cassette saddle with two config-derived locator ridges.",
        saved_orientation="48 x 144 mm broad bearing face on build plate",
        status="DEVELOPMENT LOCATOR SADDLE; PIN/LOCK RECEIVERS UNQUALIFIED; NO LOAD RATING",
        notes=["Ridge centers bisect configured diaphragm-band gaps; they are locators, not assigned shelf-load capacity."],
        design_metrics={
            "family": "final_x_saddle",
            "variant": variant,
            "quantity_per_level": quantity_per_level,
            "quantity_selected_two_levels": selected_levels * quantity_per_level,
            "base_dimensions_mm": [width, depth, height],
            "locator_ridge_count": 2,
            "locator_spec": locator,
        },
    )


def final_x_saddle_family(
    cfg: dict[str, Any], *, plan: Any, selected_levels: int
) -> list[PrototypePart]:
    run_count = len((plan.through, plan.return_run))
    quantities = {
        "interior": sum(
            int(run.bay_count) - 1 for run in (plan.through, plan.return_run)
        ),
        "run_start": run_count,
        "run_end": run_count,
    }
    return [
        final_x_saddle_variant(
            cfg,
            variant=variant,
            quantity_per_level=quantities[variant],
            selected_levels=selected_levels,
        )
        for variant in ("interior", "run_start", "run_end")
    ]


def final_x_cassette_lock(cfg: dict[str, Any]) -> PrototypePart:
    """One real zero-credit split-tail lock for all integral-cap receivers."""

    contract = integrated_cap_lock_contract(cfg)
    lock = deep_get(cfg, "corbel.integrated_cap_cassette_lock", {})
    if not isinstance(lock, dict):
        raise ValueError("Integral-cap cassette-lock configuration is incomplete")
    shank_run, shank_q = (
        float(value) for value in lock["square_shank_run_q_mm"]
    )
    head_e = tuple(float(value) for value in lock["pull_head_y_envelope_mm"])
    receiver_e = tuple(
        float(value) for value in lock["cassette_receiver_y_envelope_mm"]
    )
    shoulder_e = tuple(
        float(value) for value in lock["tail_capture_shoulder_y_envelope_mm"]
    )
    cap_e = tuple(float(value) for value in lock["cap_bore_y_envelope_mm"])
    if head_e[1] != cap_e[0] or cap_e[1] != receiver_e[0]:
        raise ValueError("Cassette-lock head/cap/receiver stack is discontinuous")
    head_run, head_q = (
        float(value) for value in lock["pull_head_run_q_mm"]
    )
    if min(head_run, head_q) <= 0.0:
        raise ValueError("Cassette-lock pull head needs positive run/q dimensions")
    datum_e = head_e[0]
    shank_z0 = cap_e[0] - datum_e
    shoulder_top_z = shoulder_e[1] - datum_e
    tail_top_z = shoulder_top_z + number(cfg, "joinery.minimum_wall_mm", 3.2)
    slit_half_q = 0.4
    base_half_q = shank_q / 2.0
    expanded_half_q = base_half_q + 0.8
    tail_start_z = shoulder_e[0] - datum_e - 0.4
    # The tail remains nominal through the 3.2 mm shoulder, then each arm
    # expands at exactly 45 degrees into the internal capture chamber.  The
    # two arms are separated by a visible 0.8 mm release slit.
    rear_arm = Polygon(
        [
            (-base_half_q, tail_start_z),
            (-slit_half_q, tail_start_z),
            (-slit_half_q, tail_top_z),
            (-base_half_q, tail_top_z),
            (-expanded_half_q, shoulder_top_z + 1.2),
            (-expanded_half_q, shoulder_top_z + 0.8),
            (-base_half_q, shoulder_top_z),
        ]
    )
    front_arm = Polygon(
        [
            (slit_half_q, tail_start_z),
            (base_half_q, tail_start_z),
            (base_half_q, shoulder_top_z),
            (expanded_half_q, shoulder_top_z + 0.8),
            (expanded_half_q, shoulder_top_z + 1.2),
            (base_half_q, tail_top_z),
            (slit_half_q, tail_top_z),
        ]
    )
    components = [
        cuboid(
            (head_run, head_q, head_e[1] - head_e[0]),
            origin=(-head_run / 2.0, -head_q / 2.0, 0.0),
        ),
        cuboid(
            (shank_run, shank_q, shoulder_top_z - shank_z0 + 0.2),
            origin=(-shank_run / 2.0, -shank_q / 2.0, shank_z0),
        ),
        extrude_yz_profile_along_x(
            rear_arm,
            x0=-shank_run / 2.0,
            width=shank_run,
        ),
        extrude_yz_profile_along_x(
            front_arm,
            x0=-shank_run / 2.0,
            width=shank_run,
        ),
    ]
    mesh = safe_union(components, "positive split-tail integral-cap cassette lock")
    nominal_compressed_envelope = [
        shank_run,
        shank_q,
        tail_top_z - shank_z0,
    ]
    quantity_per_level = int(
        deep_get(cfg, "nominal_geometry_snapshot.nominal_part_topology.cassette_locks", 0)
    )
    quantity_selected = int(
        deep_get(
            cfg,
            "nominal_geometry_snapshot.selected_two_level_part_topology.cassette_locks",
            0,
        )
    )
    return PrototypePart(
        name="R6_FINAL_X_INTEGRATED_CAP_CASSETTE_LOCK_SPLIT_TAIL",
        mesh=mesh,
        purpose="Removable underside lock with a square shank, exposed pull head, and two positive flex tails that capture above the cassette shoulder.",
        saved_orientation=(
            f"{head_run:g} x {head_q:g} mm exposed pull head flat on build "
            "plate; lock insertion axis vertical"
        ),
        status="DEVELOPMENT POSITIVE RETAINER; FLEX/REMOVAL COUPON REQUIRED; ZERO LOAD CREDIT; NO LOAD RATING",
        notes=[
            "The same 3.4 mm square shank serves tight terminal/fixed and run-elongated floating receivers; thermal travel is embodied only in the cassette slot.",
            "The split tail must elastically compress during insertion/removal. Actual PETG brand, nozzle, layer orientation, cycling, temperature, and migration remain qualification gates.",
        ],
        design_metrics={
            "family": "final_x_integrated_cap_cassette_lock",
            "quantity_per_level": quantity_per_level,
            "quantity_selected_two_levels": quantity_selected,
            "square_shank_run_q_mm": [shank_run, shank_q],
            "pull_head_run_q_e_mm": [
                head_run,
                head_q,
                head_e[1] - head_e[0],
            ],
            "installed_e_envelope_mm": [head_e[0], datum_e + tail_top_z],
            "saved_shank_axis_xy_mm": [head_run / 2.0, head_q / 2.0],
            "installed_from_saved_at_receiver_center_matrix_rule": (
                "translate saved x/y by receiver_s/q minus 4 mm and saved z by e=125.6"
            ),
            "tail_capture_shoulder_e_envelope_mm": list(shoulder_e),
            "expanded_tail_q_width_mm": 2.0 * expanded_half_q,
            "tail_release_slit_q_mm": 2.0 * slit_half_q,
            "tail_expansion_each_q_face_mm": expanded_half_q - base_half_q,
            "nominal_compressed_insertion_envelope_run_q_e_mm": nominal_compressed_envelope,
            "tight_receiver_run_q_mm": contract["tight_receiver_run_q_mm"],
            "floating_receiver_run_q_mm": contract["floating_receiver_run_q_mm"],
            "mating_receiver_generated": True,
            "positive_tail_capture_modeled": True,
            "flex_deformation_qualified": False,
            "minimum_straight_underside_service_access_mm": float(
                lock["minimum_straight_underside_service_access_mm"]
            ),
            "compressed_tail_service_sweep_collision_free": bool(
                contract["compressed_tail_service_sweep_collision_free"]
            ),
            "expanded_tail_flex_coupon_required": bool(
                contract["expanded_tail_flex_coupon_required"]
            ),
            "retention_credit": "zero",
        },
    )


def final_x_cassette_lock_compressed_insertion_proxy(
    cfg: dict[str, Any],
) -> trimesh.Trimesh:
    """Exact conservative service-sweep proxy for the flex-compressed lock.

    The configured pull head is retained at full size; everything above it is
    the configured 3.4 mm square compressed shank.  The final expanded-tail mesh
    is tested separately at its retained position and remains an actual-PETG
    flex/cycle coupon gate rather than being forced undeformed through its own
    smaller receiver.
    """

    contract = integrated_cap_lock_contract(cfg)
    if not contract["compressed_tail_service_sweep_collision_free"]:
        raise ValueError("Cassette-lock compressed service sweep is not closed")
    lock = cfg["corbel"]["integrated_cap_cassette_lock"]
    shank_run, shank_q = (
        float(value) for value in lock["square_shank_run_q_mm"]
    )
    head_e = tuple(float(value) for value in lock["pull_head_y_envelope_mm"])
    shoulder_e = tuple(
        float(value) for value in lock["tail_capture_shoulder_y_envelope_mm"]
    )
    head_run, head_q = (
        float(value) for value in lock["pull_head_run_q_mm"]
    )
    if min(head_run, head_q) <= 0.0:
        raise ValueError("Cassette-lock pull head needs positive run/q dimensions")
    head_height = head_e[1] - head_e[0]
    overall_height = shoulder_e[1] + number(
        cfg, "joinery.minimum_wall_mm", 3.2
    ) - head_e[0]
    proxy = safe_union(
        [
            cuboid(
                (head_run, head_q, head_height),
                origin=(-head_run / 2.0, -head_q / 2.0, 0.0),
            ),
            cuboid(
                (shank_run, shank_q, overall_height - head_height + 0.05),
                origin=(-shank_run / 2.0, -shank_q / 2.0, head_height - 0.05),
            ),
        ],
        "compressed split-tail lock insertion proxy",
    )
    if not np.allclose(
        proxy.extents,
        [head_run, head_q, overall_height],
        atol=1.0e-6,
        rtol=0.0,
    ):
        raise ValueError("Cassette-lock compressed service proxy envelope drift")
    return proxy


def final_x_family_report(cfg: dict[str, Any], parts: list[PrototypePart]) -> dict[str, Any]:
    nominal = deep_get(cfg, "nominal_geometry_snapshot.nominal_part_topology", {})
    selected = deep_get(cfg, "nominal_geometry_snapshot.selected_two_level_part_topology", {})
    integral = deep_get(cfg, "nominal_geometry_snapshot.integral_feature_topology", {})
    if not all(isinstance(value, dict) for value in (nominal, selected, integral)):
        raise ValueError("Final-X topology count objects are incomplete")
    expected_per_level = {
        "arcade_halves": int(nominal["arcade_halves"]),
        "integral_cassette_vertical_tenons": int(
            integral["per_level_cassette_vertical_tenons"]
        ),
        "integral_spring_vertical_tenons": int(
            integral["per_level_spring_vertical_tenons"]
        ),
        "cassette_top_retention_wedges": int(
            nominal["cassette_top_retention_wedges"]
        ),
        "spring_retention_wedges": int(nominal["spring_retention_wedges"]),
        "structural_pier_x_corbels": int(nominal["structural_pier_x_corbels"]),
        "sliding_saddles": int(nominal["sliding_saddles"]),
        "saddle_pins": int(nominal["saddle_pins"]),
        "cassette_locks": int(nominal["cassette_locks"]),
    }
    expected_two_levels = {
        "arcade_halves": int(selected["arcade_halves"]),
        "integral_cassette_vertical_tenons": int(
            integral["selected_two_level_cassette_vertical_tenons"]
        ),
        "integral_spring_vertical_tenons": int(
            integral["selected_two_level_spring_vertical_tenons"]
        ),
        "cassette_top_retention_wedges": int(
            selected["cassette_top_retention_wedges"]
        ),
        "spring_retention_wedges": int(selected["spring_retention_wedges"]),
        "structural_pier_x_corbels": int(selected["structural_pier_x_corbels"]),
        "sliding_saddles": int(selected["sliding_saddles"]),
        "saddle_pins": int(selected["saddle_pins"]),
        "cassette_locks": int(selected["cassette_locks"]),
    }
    config_per_level = {
        key: int(
            integral[
                "per_level_cassette_vertical_tenons"
                if key == "integral_cassette_vertical_tenons"
                else "per_level_spring_vertical_tenons"
            ]
            if key.startswith("integral_")
            else nominal[key]
        )
        for key in expected_per_level
    }
    config_two_levels = {
        key: int(
            integral[
                "selected_two_level_cassette_vertical_tenons"
                if key == "integral_cassette_vertical_tenons"
                else "selected_two_level_spring_vertical_tenons"
            ]
            if key.startswith("integral_")
            else selected[key]
        )
        for key in expected_two_levels
    }
    if config_per_level != expected_per_level or config_two_levels != expected_two_levels:
        raise ValueError(
            f"Final-X configured topology mismatch: {config_per_level} / {config_two_levels}"
        )
    family_names = [part.name for part in parts if "FINAL_X" in part.name]
    return {
        "status": "PASS: FINAL-X UNIQUE FAMILIES AND EXACT ONE/TWO-LEVEL LOGICAL COUNTS",
        "unique_final_x_mesh_count": len(family_names),
        "unique_final_x_mesh_names": family_names,
        "per_level_logical_counts": expected_per_level,
        "selected_two_level_logical_counts": expected_two_levels,
        "arch_half_variant_quantities_per_level": {
            "through_left": 6,
            "through_right": 6,
            "return_left": 3,
            "return_right": 3,
        },
        "corbel_variant_quantities_per_level": {"interior": 7, "run_start": 2, "run_end": 2},
        "separate_saddle_variant_quantities_per_level": {
            "interior": 0,
            "run_start": 0,
            "run_end": 0,
        },
        "selected_shelf_levels": 2,
        "level_relationship": "two identical, independently wall-fastened L assemblies; zero structural vertical ties",
        "wall_fastener_geometry_gate": "HARD BLOCKED",
        "production_wall_screw_bore_count": 0,
        "service_access_minimum_mm": 75.0,
        "unresolved_interfaces": [dict(item) for item in UNRESOLVED_INTERFACE_BLOCKERS],
    }


def crown_bridge_and_pin(cfg: dict[str, Any]) -> list[PrototypePart]:
    bridge_cfg = cfg["tied_arcade"]["rear_crown_bridge"]
    contract = crown_bridge_contract(cfg)
    rails = bridge_cfg["dovetail_rails"]
    body_u = tuple(float(value) for value in contract.body_u_mm)
    body_e = tuple(float(value) for value in contract.body_e_mm)
    body_q = tuple(float(value) for value in contract.body_q_mm)
    lug_q = tuple(float(value) for value in contract.rail_q_mm)
    lug_e = tuple(float(value) for value in contract.rail_e_mm)
    lug_u = tuple(
        tuple(float(value) for value in pair)
        for pair in contract.rail_u_envelopes_mm
    )
    pin_u, pin_e = (float(value) for value in contract.pin_center_u_e_mm)
    pin_diameter = float(bridge_cfg["retention_pin_diameter_mm"])
    pin_hole_diameter = float(bridge_cfg["retention_pin_hole_diameter_mm"])
    union_overlap = float(rails["lug_body_union_overlap_q_mm"])

    components = [
        cuboid(
            (body_u[1] - body_u[0], body_e[1] - body_e[0], body_q[1] - body_q[0]),
            origin=(body_u[0], body_e[0], body_q[0]),
        )
    ]
    for u0, u1 in lug_u:
        components.append(
            cuboid(
                (
                    u1 - u0,
                    lug_e[1] - lug_e[0],
                    lug_q[1] - lug_q[0] + union_overlap,
                ),
                origin=(u0, lug_e[0], lug_q[0] - union_overlap),
            )
        )
    bridge_blank = safe_union_installed(
        components, "exact upward-inserted rear crown bridge"
    )
    pin_hole = cylinder_z(
        pin_hole_diameter,
        lug_q[1] - body_q[0] + 0.8,
        center_xy=(pin_u, pin_e),
        z0=body_q[0] - 0.4,
    )
    bridge_installed = safe_difference_installed(
        bridge_blank, [pin_hole], "crown bridge exact retention bore"
    )
    saved_from_installed = np.asarray(
        [
            [1.0, 0.0, 0.0, -body_u[0]],
            [0.0, 1.0, 0.0, -body_e[0]],
            [0.0, 0.0, 1.0, -body_q[0]],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    installed_from_saved = np.linalg.inv(saved_from_installed)
    bridge = bridge_installed.copy()
    bridge.apply_transform(saved_from_installed)
    bridge = finish_mesh(bridge)
    expected_bridge_envelope = np.asarray(
        [
            body_u[1] - body_u[0],
            body_e[1] - body_e[0],
            lug_q[1] - body_q[0],
        ],
        dtype=float,
    )
    if not np.allclose(
        bridge.extents, expected_bridge_envelope, atol=1.0e-5, rtol=0.0
    ):
        raise ValueError("Exact crown bridge saved envelope drift")

    # The pin is a longitudinally split *circular* shaft, not the obsolete
    # short rectangular fork.  The centered u-slot creates two circular
    # segments through the full flex zone; a radial lead ramp grows from the
    # 2.5 mm shaft radius to the exact 3.3 mm expanded barb, whose abrupt front
    # shoulder provides 0.6 mm capture behind the 5.4 mm rear-ear bore.
    front_ear = tuple(float(value) for value in contract.front_ear_q_mm)
    rear_ear = tuple(float(value) for value in contract.rear_ear_q_mm)
    tail_cfg = bridge_cfg["retention_pin_positive_tail_contract"]
    split_q = tuple(float(value) for value in contract.pin_split_zone_q_mm)
    shaft_q = tuple(float(value) for value in contract.pin_unsplit_shaft_q_mm)
    ramp_q = tuple(
        float(value) for value in tail_cfg["rear_lead_ramp_q_envelope_mm"]
    )
    barb_q = tuple(float(value) for value in contract.pin_barb_q_mm)
    head_q = tuple(float(value) for value in contract.pin_head_q_mm)
    shaft_radius = float(tail_cfg["shaft_outer_radius_after_shoulder_mm"])
    ramp_start_radius = float(tail_cfg["rear_lead_radius_start_mm"])
    barb_radius = float(tail_cfg["barb_expanded_outer_radius_mm"])
    head_diameter = float(tail_cfg["head_diameter_mm"])
    slot_width = float(tail_cfg["split_slot_width_u_mm"])
    if abs(2.0 * shaft_radius - pin_diameter) > 1.0e-7:
        raise ValueError("Crown split-tail shaft radius disagrees with its diameter")

    def radial_frustum_z(
        radius0: float,
        radius1: float,
        q0: float,
        q1: float,
    ) -> trimesh.Trimesh:
        profile = np.asarray(
            [[0.0, 0.0], [radius0, 0.0], [radius1, q1 - q0], [0.0, q1 - q0]],
            dtype=float,
        )
        result = trimesh.creation.revolve(profile, sections=64)
        result.apply_translation([0.0, 0.0, q0])
        return result

    split_blank = safe_union_installed(
        [
            cylinder_z(
                pin_diameter,
                split_q[1] - split_q[0],
                center_xy=(0.0, 0.0),
                z0=split_q[0],
                sections=64,
            ),
            radial_frustum_z(
                ramp_start_radius,
                barb_radius,
                ramp_q[0],
                ramp_q[1],
            ),
            cylinder_z(
                2.0 * barb_radius,
                barb_q[1] - barb_q[0],
                center_xy=(0.0, 0.0),
                z0=barb_q[0],
                sections=64,
            ),
        ],
        "expanded circular crown split-tail blank",
    )
    split_slot = cuboid(
        (
            slot_width,
            2.0 * barb_radius + 0.4,
            split_q[1] - split_q[0] + 0.4,
        ),
        origin=(
            -slot_width / 2.0,
            -barb_radius - 0.2,
            split_q[0] - 0.2,
        ),
    )
    split_arms = safe_difference_installed(
        split_blank,
        [split_slot],
        "two circular-segment crown pin flex arms",
    )
    shaft = cylinder_z(
        pin_diameter,
        shaft_q[1] - shaft_q[0],
        center_xy=(0.0, 0.0),
        z0=shaft_q[0],
        sections=64,
    )
    head = cylinder_z(
        head_diameter,
        head_q[1] - head_q[0],
        center_xy=(0.0, 0.0),
        z0=head_q[0],
        sections=64,
    )
    pin_installed = safe_union_installed(
        [split_arms, shaft, head],
        "positive circular split-tail crown retention pin",
    )
    pin_installed.apply_translation([pin_u, pin_e, 0.0])
    pin_installed = clean_mesh_preserve_coordinates(pin_installed)
    pin_cross_section_half_envelope = head_diameter / 2.0
    pin_saved_from_installed = np.asarray(
        [
            [0.0, 0.0, 1.0, -split_q[0]],
            [1.0, 0.0, 0.0, -pin_u + pin_cross_section_half_envelope],
            [0.0, 1.0, 0.0, -pin_e + pin_cross_section_half_envelope],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    pin_installed_from_saved = np.linalg.inv(pin_saved_from_installed)
    pin = pin_installed.copy()
    pin.apply_transform(pin_saved_from_installed)
    pin = finish_mesh(pin)
    if not np.allclose(
        pin.extents,
        np.asarray(contract.pin_saved_bare_envelope_mm, dtype=float),
        atol=1.0e-5,
        rtol=0.0,
    ):
        raise ValueError("Crown split-tail saved envelope drift")
    if not pin.is_watertight or pin.body_count != 1:
        raise ValueError("Crown circular split-tail pin is not one watertight body")

    one = cfg["nominal_geometry_snapshot"]["nominal_part_topology"]
    two = cfg["nominal_geometry_snapshot"]["selected_two_level_part_topology"]
    bridge_count = int(one["crown_bridges"])
    pin_count = int(one["crown_bridge_retention_pins"])
    if bridge_count != 9 or pin_count != 9:
        raise ValueError("Crown bridge/pin topology must remain nine of each per level")

    plan = calculate_plan(cfg)
    source_keyway_center = float(
        rails["keyway_source_center_inward_from_physical_crown_face_mm"]
    )
    physical_shift = physical_crown_face_shift_mm(cfg)
    if abs(source_keyway_center + physical_shift - abs(lug_u[1][0] + (lug_u[1][1] - lug_u[1][0]) / 2.0)) > 1.0e-7:
        raise ValueError("Crown bridge nominal-seam lug/keyway datum does not close")
    placement_records: list[dict[str, Any]] = []
    for run_plan in (plan.through, plan.return_run):
        for bay_index, crown_s in enumerate(
            run_plan.crown_seam_stations_local_mm, start=1
        ):
            installed_u_e_q_to_run = np.asarray(
                [
                    [1.0, 0.0, 0.0, float(crown_s)],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                dtype=float,
            )
            bridge_saved_to_run = installed_u_e_q_to_run @ installed_from_saved
            pin_saved_to_run = installed_u_e_q_to_run @ pin_installed_from_saved
            placement_records.append(
                {
                    "run_id": str(run_plan.run_id),
                    "bay_index_1_based": bay_index,
                    "nominal_crown_seam_s_mm": float(crown_s),
                    "bridge_saved_to_run_matrix_row_major": (
                        bridge_saved_to_run.tolist()
                    ),
                    "pin_saved_to_run_matrix_row_major": pin_saved_to_run.tolist(),
                    "installed_lug_centers_s_q_e_mm": [
                        [float(crown_s) + center, (lug_q[0] + lug_q[1]) / 2.0, (lug_e[0] + lug_e[1]) / 2.0]
                        for center in contract.rail_centers_u_mm
                    ],
                }
            )
    if len(placement_records) != bridge_count:
        raise ValueError("Crown bridge authoritative placement count drift")

    return [
        PrototypePart(
            name="R6_DEV_REAR_CROWN_BRIDGE_UPWARD_INSERTION_LADDER",
            mesh=bridge,
            purpose="Exact upward-inserted rear crown bridge with two depth-projecting lugs, broad cassette-underside hard stop, and one accessible pin bore.",
            saved_orientation="72 x 48 mm broad bridge body face on build plate; projecting lugs grow upward",
            status="DEVELOPMENT CROWN BRIDGE; PARENT KEYWAY/PIN SWEEP QUALIFICATION REQUIRED; NO LOAD RATING",
            notes=[
                "The body is wholly below the cassette and has no downward tab or through-top slot.",
                "The bridge must remove downward only after the shelf is fully unloaded.",
                "The retention pin is anti-drop/reverse-slide only and receives zero shelf-load credit.",
            ],
            design_metrics={
                "family": "rear_crown_bridge",
                "quantity_per_level": bridge_count,
                "quantity_selected_two_levels": int(two["crown_bridges"]),
                "installed_body_u_e_q_envelopes_mm": [list(body_u), list(body_e), list(body_q)],
                "integral_lug_u_envelopes_mm": [list(pair) for pair in lug_u],
                "integral_lug_e_envelope_mm": list(lug_e),
                "integral_lug_q_envelope_mm": list(lug_q),
                "lug_body_positive_union_overlap_q_mm": union_overlap,
                "retention_hole_diameter_mm": pin_hole_diameter,
                "retention_hole_center_u_e_mm": [pin_u, pin_e],
                "saved_from_installed_matrix_row_major": saved_from_installed.tolist(),
                "installed_from_saved_matrix_row_major": installed_from_saved.tolist(),
                "upward_insertion_delta_e_mm": list(bridge_cfg["upward_insertion_delta_y_mm"]),
                "hard_stop_at_cassette_underside_e_mm": contract.cassette_underside_e_mm,
                "source_keyway_center_inward_from_physical_crown_face_mm": source_keyway_center,
                "physical_crown_face_shift_mm": physical_shift,
                "installed_keyway_center_from_nominal_seam_mm": (
                    source_keyway_center + physical_shift
                ),
                "authoritative_instance_placements": placement_records,
                "structural_capacity_credit": False,
            },
        ),
        PrototypePart(
            name="R6_DEV_CROWN_BRIDGE_ANTI_DROP_PIN_RETENTION_ONLY",
            mesh=pin,
            purpose="Accessible PETG pin for crown-bridge reverse-slide retention only.",
            saved_orientation=(
                "shaft axis parallel to plate; split plane maps into saved x-z "
                "and is perpendicular to the plate; round head/cross-section "
                "stands vertical/tangent, requiring an actual-orientation coupon"
            ),
            status="DEVELOPMENT POSITIVE SPLIT-TAIL RETAINER; FLEX/REMOVAL COUPON REQUIRED; ZERO LOAD CREDIT",
            notes=[
                "Test the exact parent ears and this pin in same-PETG before any crown assembly trial.",
                "No support-free or production-ready print-orientation claim is made.",
            ],
            design_metrics={
                "family": "crown_bridge_retention_pin",
                "quantity_per_level": pin_count,
                "quantity_selected_two_levels": int(two["crown_bridge_retention_pins"]),
                "shaft_diameter_mm": pin_diameter,
                "shaft_installed_q_envelope_mm": list(shaft_q),
                "head_diameter_mm": head_diameter,
                "head_installed_q_envelope_mm": list(head_q),
                "split_tail_installed_q_envelope_mm": list(split_q),
                "split_slot_width_u_mm": slot_width,
                "expanded_barb_installed_q_envelope_mm": list(barb_q),
                "expanded_barb_outer_radius_mm": barb_radius,
                "parent_bore_diameter_mm": pin_hole_diameter,
                "radial_capture_each_side_mm": float(
                    tail_cfg["barb_radial_capture_each_side_mm"]
                ),
                "free_release_window_u_q_e_envelopes_mm": [
                    list(pair) for pair in contract.pin_release_window_u_q_e_mm
                ],
                "compressed_release_max_outer_radius_mm": float(
                    tail_cfg["compressed_release_max_outer_radius_mm"]
                ),
                "saved_split_plane": "saved x-z; perpendicular to build plate",
                "saved_round_head_orientation": "vertical/tangent to build plate",
                "support_free_claim_allowed": False,
                "production_orientation_allowed": False,
                "actual_parent_orientation_coupon_required": True,
                "conservative_flex_proxy_strain_fraction": (
                    contract.pin_proxy_strain_fraction
                ),
                "positive_split_tail_modeled": True,
                "flex_deformation_qualified": False,
                "saved_from_installed_matrix_row_major": pin_saved_from_installed.tolist(),
                "installed_from_saved_matrix_row_major": pin_installed_from_saved.tolist(),
                "installed_center_u_e_mm": [pin_u, pin_e],
                "authoritative_instance_placements": placement_records,
                "retention_credit": "zero",
            },
        ),
    ]


def crown_pin_compressed_insertion_proxy(cfg: dict[str, Any]) -> trimesh.Trimesh:
    """Return the exact circular-segment squeeze proxy for crown-pin motion."""

    bridge_cfg = cfg["tied_arcade"]["rear_crown_bridge"]
    contract = crown_bridge_contract(cfg)
    tail = bridge_cfg["retention_pin_positive_tail_contract"]
    pin_u, pin_e = contract.pin_center_u_e_mm
    split_q = contract.pin_split_zone_q_mm
    shaft_q = contract.pin_unsplit_shaft_q_mm
    head_q = contract.pin_head_q_mm
    compressed_radius = (
        float(tail["barb_expanded_outer_radius_mm"])
        - float(tail["qualification_deflection_each_arm_mm"])
    )
    if compressed_radius > float(
        tail["compressed_release_max_outer_radius_mm"]
    ) + 1.0e-7:
        raise ValueError("Crown-pin squeeze proxy exceeds the configured maximum")
    slot_width = float(tail["split_slot_width_u_mm"])
    shaft_diameter = float(bridge_cfg["retention_pin_diameter_mm"])
    head_diameter = float(tail["head_diameter_mm"])
    compressed_blank = cylinder_z(
        2.0 * compressed_radius,
        split_q[1] - split_q[0],
        center_xy=(0.0, 0.0),
        z0=split_q[0],
        sections=64,
    )
    compressed_slot = cuboid(
        (
            slot_width,
            2.0 * compressed_radius + 0.4,
            split_q[1] - split_q[0] + 0.4,
        ),
        origin=(
            -slot_width / 2.0,
            -compressed_radius - 0.2,
            split_q[0] - 0.2,
        ),
    )
    compressed_arms = safe_difference_installed(
        compressed_blank,
        [compressed_slot],
        "compressed circular-segment crown pin arms",
    )
    shaft = cylinder_z(
        shaft_diameter,
        shaft_q[1] - shaft_q[0],
        center_xy=(0.0, 0.0),
        z0=shaft_q[0],
        sections=64,
    )
    head = cylinder_z(
        head_diameter,
        head_q[1] - head_q[0],
        center_xy=(0.0, 0.0),
        z0=head_q[0],
        sections=64,
    )
    proxy = safe_union_installed(
        [compressed_arms, shaft, head],
        "compressed crown pin with intact shaft and head",
    )
    proxy.apply_translation([pin_u, pin_e, 0.0])
    proxy = clean_mesh_preserve_coordinates(proxy)
    radial = np.linalg.norm(
        np.asarray(proxy.vertices, dtype=float)[:, :2]
        - np.asarray([pin_u, pin_e], dtype=float),
        axis=1,
    )
    split_vertices = np.asarray(proxy.vertices, dtype=float)[:, 2] <= split_q[1] + 1.0e-7
    if np.max(radial[split_vertices], initial=0.0) > compressed_radius + 1.0e-5:
        raise ValueError("Compressed crown-pin proxy exceeds its derived radius")
    if not proxy.is_watertight or not proxy.is_volume or proxy.body_count != 1:
        raise ValueError("Compressed crown-pin proxy is not one watertight body")
    return proxy


def validate_crown_pin_parent_sweeps(
    cfg: dict[str, Any],
    *,
    arches: Iterable[PrototypePart],
    cassettes: Iterable[PrototypePart],
    crown_bridge: PrototypePart,
    crown_pin: PrototypePart,
) -> dict[str, Any]:
    """Prove compressed insert/squeeze/removal through all nine real parents."""

    contract = crown_bridge_contract(cfg)
    bridge_cfg = cfg["tied_arcade"]["rear_crown_bridge"]
    tail = bridge_cfg["retention_pin_positive_tail_contract"]
    compressed = crown_pin_compressed_insertion_proxy(cfg)
    pin_installed_to_saved = np.asarray(
        crown_pin.design_metrics["saved_from_installed_matrix_row_major"],
        dtype=float,
    )
    clear_beyond_front_ear = (
        float(bridge_cfg["retention_pin_hole_diameter_mm"])
        - float(bridge_cfg["retention_pin_diameter_mm"])
    )
    clear_delta = (
        contract.front_ear_q_mm[1]
        + clear_beyond_front_ear
        - contract.pin_split_zone_q_mm[0]
    )
    insertion_deltas = np.linspace(
        clear_delta, 0.0, int(round(clear_delta / 0.4)) + 1
    )
    right_arches: dict[tuple[str, int], tuple[PrototypePart, dict[str, Any]]] = {}
    for part in arches:
        if part.design_metrics.get("handedness") != "right":
            continue
        run_id = str(part.design_metrics["run_id"])
        for placement in part.design_metrics["authoritative_instance_placements"]:
            right_arches[(run_id, int(placement["bay_index_1_based"]))] = (
                part,
                placement,
            )
    cassette_by_position = {
        (
            str(part.design_metrics["run_id"]),
            int(part.design_metrics["position_index_1_based"]),
        ): part
        for part in cassettes
    }
    if len(right_arches) != 9:
        raise ValueError("Crown-pin proof needs nine right-hand arch parents")

    expanded_final_pair_count = 0
    compressed_sweep_pair_count = 0
    release_window_pair_count = 0
    maximum_overlap = 0.0
    for placement in crown_pin.design_metrics["authoritative_instance_placements"]:
        key = (
            str(placement["run_id"]),
            int(placement["bay_index_1_based"]),
        )
        arch_part, arch_placement = right_arches[key]
        cassette_key = (
            key[0],
            int(arch_placement["cassette_index_1_based"]),
        )
        cassette = cassette_by_position[cassette_key]
        parents: list[tuple[trimesh.Trimesh, str]] = []
        installed_bridge = crown_bridge.mesh.copy()
        installed_bridge.apply_transform(
            np.asarray(
                placement["bridge_saved_to_run_matrix_row_major"], dtype=float
            )
        )
        parents.append((installed_bridge, "crown bridge"))
        installed_arch = arch_part.mesh.copy()
        installed_arch.apply_transform(
            np.asarray(
                arch_placement["arch_saved_to_run_matrix_row_major"],
                dtype=float,
            )
        )
        parents.append((installed_arch, "right arch/front ear"))
        installed_cassette = cassette.mesh.copy()
        installed_cassette.apply_transform(
            np.asarray(
                cassette.design_metrics["saved_print_transform"][
                    "saved_to_run_matrix_row_major"
                ],
                dtype=float,
            )
        )
        parents.append((installed_cassette, "right cassette/rear ear"))
        installed_from_local = (
            np.asarray(
                placement["pin_saved_to_run_matrix_row_major"], dtype=float
            )
            @ pin_installed_to_saved
        )
        expanded = crown_pin.mesh.copy()
        expanded.apply_transform(
            np.asarray(
                placement["pin_saved_to_run_matrix_row_major"], dtype=float
            )
        )
        for parent, label in parents:
            overlap = positive_solid_intersection_volume_mm3(expanded, parent)
            maximum_overlap = max(maximum_overlap, overlap)
            if overlap > 1.0e-5:
                raise ValueError(
                    f"{key}: expanded crown pin overlaps {label} by "
                    f"{overlap:.9f} mm3"
                )
            expanded_final_pair_count += 1
        for delta_q in insertion_deltas:
            moving = compressed.copy()
            moving.apply_translation([0.0, 0.0, float(delta_q)])
            moving.apply_transform(installed_from_local)
            for parent, label in parents:
                overlap = positive_solid_intersection_volume_mm3(moving, parent)
                maximum_overlap = max(maximum_overlap, overlap)
                if overlap > 1.0e-5:
                    raise ValueError(
                        f"{key}: compressed crown pin at q delta "
                        f"{delta_q:.1f} overlaps {label} by {overlap:.9f} mm3"
                    )
                compressed_sweep_pair_count += 1
        release_u, release_q, release_e = contract.pin_release_window_u_q_e_mm
        release_window = cuboid(
            (
                release_u[1] - release_u[0],
                release_e[1] - release_e[0],
                release_q[1] - release_q[0],
            ),
            origin=(release_u[0], release_e[0], release_q[0]),
        )
        release_window.apply_transform(installed_from_local)
        for parent, label in parents:
            overlap = positive_solid_intersection_volume_mm3(
                release_window, parent
            )
            if overlap > 1.0e-5:
                raise ValueError(
                    f"{key}: crown-pin release window contains {label} solid "
                    f"({overlap:.9f} mm3)"
                )
            release_window_pair_count += 1

    axial_approach = contract.rear_ear_q_mm[0] - contract.pin_barb_q_mm[1]
    radial_capture = (
        float(tail["barb_expanded_outer_radius_mm"])
        - float(bridge_cfg["retention_pin_hole_diameter_mm"]) / 2.0
    )
    if abs(axial_approach - 0.8) > 1.0e-7 or abs(radial_capture - 0.6) > 1.0e-7:
        raise ValueError("Crown-pin axial/radial positive capture drifted")
    return {
        "status": "PASS: COMPRESSED CIRCULAR CROWN-PIN INSERT/SQUEEZE/REVERSE SWEEPS AGAINST ALL REAL PARENTS",
        "crown_interface_count": 9,
        "compressed_proxy_maximum_outer_radius_mm": (
            float(tail["barb_expanded_outer_radius_mm"])
            - float(tail["qualification_deflection_each_arm_mm"])
        ),
        "insertion_translation_station_count": len(insertion_deltas),
        "expanded_final_parent_boolean_pair_count": expanded_final_pair_count,
        "compressed_insert_and_reverse_parent_boolean_pair_count": (
            compressed_sweep_pair_count
        ),
        "release_window_parent_boolean_pair_count": release_window_pair_count,
        "maximum_positive_parent_overlap_volume_mm3": round(
            maximum_overlap, 9
        ),
        "barb_to_rear_ear_axial_approach_mm": axial_approach,
        "barb_radial_capture_each_side_mm": radial_capture,
        "inverse_removal_uses_exact_reversed_states": True,
        "physical_flex_cycle_and_tool_reach_qualified": False,
    }


def indexed_crown_retention_pin_parts(
    cfg: dict[str, Any], *, selected_levels: int
) -> list[PrototypePart]:
    """Emit the two exact service-axis variants of one indexed pin family.

    Both sources are authored locked in installed ``(u,q,e)`` coordinates.
    The keeper shaft follows ``+e`` from the open underside; the front-tie
    shaft follows ``-q`` from the visible front.  Each source is then mapped to
    the frozen broad-flat saved orientation without changing its handedness.
    """

    contract = crown_retention_pin_contract(cfg)
    keeper = contract.keeper
    raw = cfg["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"]
    geometry = raw["shared_pin_geometry"]
    nub = geometry["single_index_nub"]
    center_u, center_q = keeper.center_u_q_mm
    shaft_diameter = float(contract.shaft_diameter_mm)
    tail_long, tail_short, tail_e_size = contract.tail_long_short_axial_mm
    handle_long, handle_short, handle_axial = (
        float(value) for value in contract.flat_pull_bar_long_short_axial_mm
    )
    handle_e0, handle_e1 = keeper.handle_e_mm
    shaft_e0, shaft_e1 = keeper.shaft_e_mm
    tail_e0, tail_e1 = keeper.tail_body_e_mm
    nub_dims = tuple(float(value) for value in nub["long_by_short_by_axial_mm"])
    nub_center_u = center_u + float(
        nub["center_from_pin_axis_on_locked_positive_long_axis_mm"]
    )
    nub_e0, nub_e1 = keeper.index_nub_e_mm

    handle = cuboid(
        (handle_long, handle_short, handle_e1 - handle_e0),
        origin=(
            center_u - handle_long / 2.0,
            center_q - handle_short / 2.0,
            handle_e0,
        ),
    )
    shaft = cylinder_z(
        shaft_diameter,
        shaft_e1 - shaft_e0,
        center_xy=(center_u, center_q),
        z0=shaft_e0,
    )
    locked_tail = cuboid(
        (tail_long, tail_short, tail_e_size),
        origin=(
            center_u - tail_long / 2.0,
            center_q - tail_short / 2.0,
            tail_e0,
        ),
    )
    index_nub = cuboid(
        nub_dims,
        origin=(
            nub_center_u - nub_dims[0] / 2.0,
            center_q - nub_dims[1] / 2.0,
            nub_e0,
        ),
    )
    installed = safe_union_installed(
        [handle, shaft, locked_tail, index_nub],
        "keeper-reach indexed vertical quarter-turn pin",
    )
    saved_from_installed = np.asarray(
        [
            [0.0, 0.0, 1.0, -handle_e0],
            [1.0, 0.0, 0.0, -(center_u - handle_long / 2.0)],
            [0.0, 1.0, 0.0, -(center_q - handle_short / 2.0)],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    installed_from_saved = np.linalg.inv(saved_from_installed)
    saved = installed.copy()
    saved.apply_transform(saved_from_installed)
    saved = finish_mesh(saved)
    expected = np.asarray(keeper.bare_saved_envelope_mm, dtype=float)
    if not np.allclose(saved.extents, expected, atol=1.0e-5, rtol=0.0):
        raise ValueError(
            "Keeper-reach pin saved envelope disagrees with its flat-bar contract: "
            f"{saved.extents.tolist()} != {expected.tolist()}"
        )
    if not saved.is_watertight or saved.body_count != 1:
        raise ValueError("Keeper-reach pin is not one watertight printed body")

    counts = raw["object_count_impact_contract"]
    keeper_quantity = int(counts["keeper_pins_per_level"])
    tie_quantity = int(counts["front_tie_pins_per_level"])
    if (keeper_quantity, tie_quantity) != (9, 9):
        raise ValueError("Keeper-reach pin count must remain nine per level")
    keeper_part = PrototypePart(
            name="R6_DEV_INDEXED_VERTICAL_QUARTER_TURN_PIN_KEEPER_REACH",
            mesh=saved,
            purpose="Flat-handle, indexed T-tail keeper pin that blocks the fixed-crown strip's reverse bayonet slide.",
            saved_orientation="shaft parallel to build plate; 8 x 3.2 mm flat pull bar and one T-tail edge on plate",
            status="SOFTWARE GEOMETRY EMBODIED; ACTUAL-PARENT PETG CYCLE/MIGRATION QUALIFICATION REQUIRED; ZERO LOAD CREDIT",
            notes=[
                "The locked tail long axis is u; entry rotates it to q before underside withdrawal.",
                "The separate front-tie family member uses the approved visible-front q-axis contract; no vertical front-tie source is emitted.",
                "No structural, bearing, or shelf-load credit is assigned to this retainer.",
            ],
            design_metrics={
                "family": contract.family_id,
                "variant_id": keeper.variant_id,
                "release_inventory_family": contract.family_id,
                "quantity_per_level": keeper_quantity,
                "quantity_selected_levels": keeper_quantity * selected_levels,
                "installed_center_u_q_mm": list(keeper.center_u_q_mm),
                "shaft_diameter_mm": shaft_diameter,
                "shaft_bore_diameter_mm": float(contract.shaft_bore_diameter_mm),
                "locked_tail_long_short_axial_mm": list(
                    contract.tail_long_short_axial_mm
                ),
                "flat_handle_long_short_axial_mm": [
                    handle_long,
                    handle_short,
                    handle_e1 - handle_e0,
                ],
                "single_index_nub_long_short_axial_mm": list(nub_dims),
                "unlock_push_e_mm": float(contract.unlock_push_e_mm),
                "kinematic_stage_matrices": {
                    key: [list(row) for row in matrix]
                    for key, matrix in keeper.kinematic_stage_matrices.items()
                },
                "saved_from_installed_matrix_row_major": (
                    saved_from_installed.tolist()
                ),
                "installed_from_saved_matrix_row_major": (
                    installed_from_saved.tolist()
                ),
                "actual_parent_receiver_geometry_embodied": True,
                "actual_parent_service_sweeps_passed": False,
                "prohibited_front_tie_vertical_variant_emitted": False,
                "software_model_mapping_complete": False,
                "physical_installation_mapping_qualified": False,
                "production_release_eligible": False,
                "retention_credit": "zero",
            },
        )

    tie = contract.front_tie
    tail_u, tail_e, tail_q = tie.tail_body_u_e_q_mm
    nub_u, nub_e, nub_q = tie.index_nub_u_e_q_mm
    shaft_q0, shaft_q1 = tie.shaft_q_mm
    pull_u, pull_e, pull_q = tie.pull_bar_u_e_q_mm
    tie_installed = safe_union_installed(
        [
            cuboid(
                (tail_u[1] - tail_u[0], tail_q[1] - tail_q[0], tail_e[1] - tail_e[0]),
                origin=(tail_u[0], tail_q[0], tail_e[0]),
            ),
            cylinder_y(
                shaft_diameter,
                shaft_q1 - shaft_q0,
                center_xz=tie.center_u_e_mm,
                y0=shaft_q0,
            ),
            cuboid(
                (nub_u[1] - nub_u[0], nub_q[1] - nub_q[0], nub_e[1] - nub_e[0]),
                origin=(nub_u[0], nub_q[0], nub_e[0]),
            ),
            cuboid(
                (pull_u[1] - pull_u[0], pull_q[1] - pull_q[0], pull_e[1] - pull_e[0]),
                origin=(pull_u[0], pull_q[0], pull_e[0]),
            ),
        ],
        "visible-front q-axis front-tie indexed quarter-turn pin",
    )
    tie_installed_bounds = np.asarray(tie_installed.bounds, dtype=float)
    tie_saved_from_installed = np.asarray(
        [
            [0.0, 1.0, 0.0, -tie_installed_bounds[0][1]],
            [0.0, 0.0, 1.0, -tie_installed_bounds[0][2]],
            [1.0, 0.0, 0.0, -tie_installed_bounds[0][0]],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    tie_installed_from_saved = np.linalg.inv(tie_saved_from_installed)
    tie_saved = tie_installed.copy()
    tie_saved.apply_transform(tie_saved_from_installed)
    tie_saved = finish_mesh(tie_saved)
    tie_expected = np.asarray(tie.bare_saved_envelope_mm, dtype=float)
    if not np.allclose(tie_saved.extents, tie_expected, atol=1.0e-5, rtol=0.0):
        raise ValueError(
            "Front-tie-reach pin saved envelope disagrees with its flat-bar contract: "
            f"{tie_saved.extents.tolist()} != {tie_expected.tolist()}"
        )
    if not tie_saved.is_watertight or tie_saved.body_count != 1:
        raise ValueError("Front-tie-reach pin is not one watertight printed body")
    tie_part = PrototypePart(
        name="R6_DEV_INDEXED_VERTICAL_QUARTER_TURN_PIN_FRONT_TIE_REACH",
        mesh=tie_saved,
        purpose="Visible-front q-axis indexed T-tail pin that positively captures the fixed-crown front tie.",
        saved_orientation="shaft parallel to build plate; 8 x 3.2 mm flat pull bar broad face and one T-tail edge on plate",
        status="SOFTWARE SOURCE GEOMETRY EMBODIED; ACTUAL-PARENT BOOLEAN SWEEPS AND PETG CYCLE/MIGRATION QUALIFICATION REQUIRED; ZERO LOAD CREDIT",
        notes=[
            "The locked tail long axis is elevation e; entry rotates it to run u before visible-front withdrawal.",
            "This replaces and prohibits the collision-prone vertical front-tie concept.",
            "No structural, bearing, or shelf-load credit is assigned to this retainer.",
        ],
        design_metrics={
            "family": contract.family_id,
            "variant_id": tie.variant_id,
            "release_inventory_family": contract.family_id,
            "quantity_per_level": tie_quantity,
            "quantity_selected_levels": tie_quantity * selected_levels,
            "installed_center_u_e_mm": list(tie.center_u_e_mm),
            "shaft_diameter_mm": shaft_diameter,
            "shaft_bore_diameter_mm": float(contract.shaft_bore_diameter_mm),
            "locked_tail_u_e_q_envelopes_mm": [list(pair) for pair in tie.tail_body_u_e_q_mm],
            "single_index_nub_u_e_q_envelopes_mm": [list(pair) for pair in tie.index_nub_u_e_q_mm],
            "flat_pull_bar_u_e_q_envelopes_mm": [list(pair) for pair in tie.pull_bar_u_e_q_mm],
            "unlock_push_q_mm": -float(contract.unlock_push_e_mm),
            "kinematic_stage_matrices": {
                key: [list(row) for row in matrix]
                for key, matrix in tie.kinematic_stage_matrices.items()
            },
            "saved_from_installed_matrix_row_major": tie_saved_from_installed.tolist(),
            "installed_from_saved_matrix_row_major": tie_installed_from_saved.tolist(),
            "actual_parent_receiver_geometry_embodied": False,
            "actual_parent_service_sweeps_passed": False,
            "prohibited_vertical_variant_emitted": False,
            "software_model_mapping_complete": False,
            "physical_installation_mapping_qualified": False,
            "production_release_eligible": False,
            "retention_credit": "zero",
        },
    )
    return [keeper_part, tie_part]


def fixed_crown_diaphragm_keeper_strip(
    cfg: dict[str, Any], *, selected_levels: int
) -> PrototypePart:
    """Emit the exact one-body rear-bayonet diaphragm keeper strip."""

    contract = diaphragm_retention_contract(cfg)
    retain = cfg["joinery"]["diaphragm_bowtie"]["positive_retention"]
    track = retain["internal_upward_bayonet_track"]
    strip_u = tuple(
        float(value)
        for value in retain[
            "fixed_crown_keeper_run_envelope_inward_from_left_physical_face_mm"
        ]
    )
    strip_q = tuple(
        float(value) for value in retain["fixed_crown_keeper_q_envelope_mm"]
    )
    strip_e = tuple(
        float(value)
        for value in retain["fixed_crown_keeper_installed_e_envelope_mm"]
    )
    shank_u = tuple(
        float(value)
        for value in track[
            "rear_tongue_shank_run_envelope_inward_from_left_physical_face_mm"
        ]
    )
    head_u = tuple(
        float(value)
        for value in track[
            "rear_tongue_head_run_envelope_inward_from_left_physical_face_mm"
        ]
    )
    head_q = tuple(
        float(value) for value in track["rear_tongue_final_head_q_envelope_mm"]
    )
    shank_e = tuple(
        float(value) for value in track["rear_tongue_shank_y_envelope_mm"]
    )
    head_e = tuple(
        float(value) for value in track["rear_tongue_head_y_envelope_mm"]
    )
    strip = cuboid(
        (
            strip_u[1] - strip_u[0],
            strip_q[1] - strip_q[0],
            strip_e[1] - strip_e[0],
        ),
        origin=(strip_u[0], strip_q[0], strip_e[0]),
    )
    shank = cuboid(
        (
            shank_u[1] - shank_u[0],
            head_q[1] - head_q[0],
            shank_e[1] - shank_e[0],
        ),
        origin=(shank_u[0], head_q[0], shank_e[0]),
    )
    head = cuboid(
        (
            head_u[1] - head_u[0],
            head_q[1] - head_q[0],
            head_e[1] - head_e[0],
        ),
        origin=(head_u[0], head_q[0], head_e[0]),
    )
    installed = safe_union_installed(
        [strip, shank, head],
        "fixed-crown diaphragm keeper strip with rear bayonet tongue",
    )
    shared_pin = crown_retention_pin_contract(cfg)
    gate_u, gate_q = shared_pin.keeper.entry_gate_u_q_mm
    gate = cuboid(
        (
            gate_u[1] - gate_u[0],
            gate_q[1] - gate_q[0],
            strip_e[1] - strip_e[0] + 0.4,
        ),
        origin=(gate_u[0], gate_q[0], strip_e[0] - 0.2),
    )
    installed = safe_difference_installed(
        installed,
        [gate],
        "fixed-crown keeper indexed-pin reverse-slide gate",
    )
    installed_bounds = np.asarray(installed.bounds, dtype=float)
    saved_from_installed = np.asarray(
        [
            [0.0, 1.0, 0.0, -installed_bounds[0][1]],
            [-1.0, 0.0, 0.0, installed_bounds[1][0]],
            [0.0, 0.0, 1.0, -installed_bounds[0][2]],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    installed_from_saved = np.linalg.inv(saved_from_installed)
    saved = installed.copy()
    saved.apply_transform(saved_from_installed)
    saved = finish_mesh(saved)
    expected_saved = np.asarray(
        [
            strip_q[1] - strip_q[0],
            strip_u[1] - strip_u[0],
            head_e[1] - strip_e[0],
        ],
        dtype=float,
    )
    if not np.allclose(saved.extents, expected_saved, atol=1.0e-5, rtol=0.0):
        raise ValueError("Fixed-crown keeper saved envelope drifted")
    if not saved.is_watertight or not saved.is_volume or saved.body_count != 1:
        raise ValueError("Fixed-crown keeper is not one watertight printed body")
    return PrototypePart(
        name="R6_DEV_FIXED_CROWN_DIAPHRAGM_KEEPER_STRIP_REAR_BAYONET",
        mesh=saved,
        purpose="One rear-bayonet underside strip that retains all three fixed-crown diaphragm keys after their installation.",
        saved_orientation="broad 96.6 x 12 mm strip face on the build plate; widened tongue head upward",
        status="SOFTWARE GEOMETRY EMBODIED; ACTUAL-ORIENTATION SUPPORT/PETG CYCLE QUALIFICATION REQUIRED; ZERO LOAD CREDIT",
        notes=[
            "Only the rear tongue is emitted; the legacy front-track envelope remains a compatibility keepout.",
            "The separate indexed keeper pin blocks the full 4 mm forward unlock slide; friction receives no retention credit.",
        ],
        design_metrics={
            "family": "fixed_crown_diaphragm_keeper_strip",
            "quantity_per_level": int(contract["per_level_keeper_count"]),
            "quantity_selected_levels": int(
                contract["per_level_keeper_count"]
            )
            * selected_levels,
            "strip_u_q_e_envelopes_mm": [
                list(strip_u),
                list(strip_q),
                list(strip_e),
            ],
            "rear_tongue_shank_u_q_e_envelopes_mm": [
                list(shank_u),
                list(head_q),
                list(shank_e),
            ],
            "rear_tongue_head_u_q_e_envelopes_mm": [
                list(head_u),
                list(head_q),
                list(head_e),
            ],
            "indexed_pin_gate_u_q_mm": [list(gate_u), list(gate_q)],
            "rearward_locking_slide_mm": float(
                track["rearward_locking_slide_mm"]
            ),
            "clear_approach_translation_e_mm": float(
                track["clear_approach_translation_y_mm"]
            ),
            "rear_bayonet_tongue_count": 1,
            "front_tongue_count": 0,
            "saved_from_installed_matrix_row_major": (
                saved_from_installed.tolist()
            ),
            "installed_from_saved_matrix_row_major": (
                installed_from_saved.tolist()
            ),
            "actual_parent_service_sweeps_passed": False,
            "support_free_claim_allowed": bool(
                track["support_free_claim_allowed"]
            ),
            "software_model_mapping_complete": False,
            "physical_installation_mapping_qualified": False,
            "production_release_eligible": False,
            "retention_credit": "zero",
        },
    )


def validate_keeper_strip_parent_sweeps(
    cfg: dict[str, Any],
    *,
    cassettes: Iterable[PrototypePart],
    keeper_strip: PrototypePart,
    keeper_pin: PrototypePart,
) -> dict[str, Any]:
    """Prove rear-tongue lift, lock slide, inverse, and pin blocking."""

    retain = cfg["joinery"]["diaphragm_bowtie"]["positive_retention"]
    track = retain["internal_upward_bayonet_track"]
    source = keeper_strip.mesh.copy()
    source.apply_transform(
        np.asarray(
            keeper_strip.design_metrics[
                "installed_from_saved_matrix_row_major"
            ],
            dtype=float,
        )
    )
    pin_source = keeper_pin.mesh.copy()
    pin_source.apply_transform(
        np.asarray(
            keeper_pin.design_metrics["installed_from_saved_matrix_row_major"],
            dtype=float,
        )
    )
    approach_e = float(track["clear_approach_translation_y_mm"])
    slide_q = float(track["rearward_locking_slide_mm"])
    lift_deltas = np.linspace(
        approach_e, 0.0, int(round(abs(approach_e) / 0.4)) + 1
    )
    slide_deltas = np.linspace(
        slide_q, 0.0, int(round(slide_q / 0.4)) + 1
    )
    owners = [
        part
        for part in cassettes
        if part.design_metrics.get("fixed_crown_keeper_pin_receiver_generated")
    ]
    if len(owners) != 9:
        raise ValueError("Keeper rear-bayonet ownership must resolve to nine cassettes")
    by_run_position = {
        (
            str(part.design_metrics["run_id"]),
            int(part.design_metrics["position_index_1_based"]),
        ): part
        for part in cassettes
    }
    checked_pairs = 0
    pin_blocking_overlaps: list[float] = []
    for owner in owners:
        metrics = owner.design_metrics
        mate = by_run_position.get(
            (
                str(metrics["run_id"]),
                int(metrics["position_index_1_based"]) + 1,
            )
        )
        if mate is None:
            raise ValueError("Keeper owner lacks its fixed-crown cassette mate")
        physical_face = float(metrics["physical_interval_local_mm"][1])
        local_to_run = np.asarray(
            [
                [-1.0, 0.0, 0.0, physical_face],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        parents: list[trimesh.Trimesh] = []
        for cassette in (owner, mate):
            parent = cassette.mesh.copy()
            parent.apply_transform(
                np.asarray(
                    cassette.design_metrics["saved_print_transform"][
                        "saved_to_run_matrix_row_major"
                    ],
                    dtype=float,
                )
            )
            parents.append(parent)

        stages: list[trimesh.Trimesh] = []
        for delta_e in lift_deltas:
            moving = source.copy()
            moving.apply_translation([0.0, slide_q, float(delta_e)])
            stages.append(moving)
        for delta_q in slide_deltas:
            moving = source.copy()
            moving.apply_translation([0.0, float(delta_q), 0.0])
            stages.append(moving)
        for moving in stages:
            installed = moving.copy()
            installed.apply_transform(local_to_run)
            for parent in parents:
                overlap = positive_solid_intersection_volume_mm3(
                    installed, parent
                )
                if overlap > 1.0e-5:
                    raise ValueError(
                        f"{metrics['logical_instance_id']}: keeper rear-bayonet "
                        f"motion overlaps a real cassette by {overlap:.9f} mm3"
                    )
                checked_pairs += 1

        installed_pin = pin_source.copy()
        installed_pin.apply_transform(local_to_run)
        seated_strip = source.copy()
        seated_strip.apply_transform(local_to_run)
        if positive_solid_intersection_volume_mm3(
            installed_pin, seated_strip
        ) > 1.0e-5:
            raise ValueError("Installed keeper pin does not clear the seated strip gate")
        blocked_strip = source.copy()
        blocked_strip.apply_translation([0.0, slide_q, 0.0])
        blocked_strip.apply_transform(local_to_run)
        blocked_overlap = positive_solid_intersection_volume_mm3(
            installed_pin, blocked_strip
        )
        if blocked_overlap <= 1.0e-3:
            raise ValueError("Keeper pin does not block the full forward unlock slide")
        pin_blocking_overlaps.append(blocked_overlap)

    return {
        "status": "PASS: REAL KEEPER REAR-BAYONET LIFT/SLIDE/INVERSE AND PIN-BLOCK BOOLEAN SWEEPS",
        "owning_cassette_count": len(owners),
        "lift_station_count": len(lift_deltas),
        "rearward_slide_station_count": len(slide_deltas),
        "real_parent_collision_free_boolean_pair_count": checked_pairs,
        "pin_blocked_full_forward_slide_count": len(pin_blocking_overlaps),
        "minimum_pin_blocking_overlap_volume_mm3": round(
            min(pin_blocking_overlaps), 6
        ),
        "inverse_removal_uses_exact_reversed_states": True,
        "front_tongue_emitted": False,
    }


def validate_keeper_pin_parent_sweeps(
    cfg: dict[str, Any],
    *,
    cassettes: Iterable[PrototypePart],
    keeper_pin: PrototypePart,
) -> dict[str, Any]:
    """Boolean-prove the keeper pin's insert/rotate/index/inverse path.

    The source mesh is saved in a print orientation but authored locked at its
    absolute keeper ``(u,q,e)`` station.  Each owning cassette mirrors inward-u
    from its physical right crown face into run coordinates.  A wrong-way
    seated nub must collide with the intact floor while the +0.8 mm release
    push must clear it; this is positive indexing, not metadata or friction.
    """

    shared = crown_retention_pin_contract(cfg)
    keeper = shared.keeper
    source = keeper_pin.mesh.copy()
    source.apply_transform(
        np.asarray(
            keeper_pin.design_metrics["installed_from_saved_matrix_row_major"],
            dtype=float,
        )
    )
    center_u, center_q = keeper.center_u_q_mm

    def moved_local(angle_from_locked_deg: float, delta_e_mm: float) -> trimesh.Trimesh:
        moving = source.copy()
        moving.apply_transform(
            trimesh.transformations.rotation_matrix(
                math.radians(angle_from_locked_deg),
                [0.0, 0.0, 1.0],
                point=[center_u, center_q, 0.0],
            )
        )
        moving.apply_translation([0.0, 0.0, delta_e_mm])
        return moving

    clear_delta = float(keeper.clear_approach_translation_e_mm)
    push_delta = float(shared.unlock_push_e_mm)
    translation_step = 0.4
    approach_deltas = np.linspace(
        clear_delta,
        push_delta,
        int(round((push_delta - clear_delta) / translation_step)) + 1,
    )
    rotation_angles = np.linspace(-90.0, 0.0, 91)
    seat_deltas = np.linspace(push_delta, 0.0, 5)
    stage_sources: list[tuple[str, trimesh.Trimesh]] = []
    stage_sources.extend(
        ("entry_or_withdraw", moved_local(-90.0, float(delta)))
        for delta in approach_deltas
    )
    stage_sources.extend(
        ("quarter_turn_or_inverse", moved_local(float(angle), push_delta))
        for angle in rotation_angles
    )
    stage_sources.extend(
        ("index_seat_or_release", moved_local(0.0, float(delta)))
        for delta in seat_deltas
    )

    owners = [
        part
        for part in cassettes
        if part.design_metrics.get("fixed_crown_keeper_pin_receiver_generated")
    ]
    if len(owners) != 9:
        raise ValueError("Keeper pin receiver ownership must resolve to nine cassettes")
    checked_pairs = 0
    wrong_way_collisions: list[float] = []
    for cassette in owners:
        metrics = cassette.design_metrics
        physical_end = float(metrics["physical_interval_local_mm"][1])
        local_to_run = np.asarray(
            [
                [-1.0, 0.0, 0.0, physical_end],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        installed_cassette = cassette.mesh.copy()
        installed_cassette.apply_transform(
            np.asarray(
                metrics["saved_print_transform"]["saved_to_run_matrix_row_major"],
                dtype=float,
            )
        )
        for stage_name, local_pin in stage_sources:
            installed_pin = local_pin.copy()
            installed_pin.apply_transform(local_to_run)
            overlap = positive_solid_intersection_volume_mm3(
                installed_pin, installed_cassette
            )
            if overlap > 1.0e-5:
                raise ValueError(
                    f"{metrics['logical_instance_id']}: keeper pin {stage_name} "
                    f"overlaps its real cassette by {overlap:.9f} mm3"
                )
            checked_pairs += 1

        wrong_way = moved_local(180.0, 0.0)
        wrong_way.apply_transform(local_to_run)
        wrong_way_overlap = positive_solid_intersection_volume_mm3(
            wrong_way, installed_cassette
        )
        if wrong_way_overlap <= 1.0e-3:
            raise ValueError(
                f"{metrics['logical_instance_id']}: wrong-way keeper index can "
                "seat without striking the intact floor"
            )
        wrong_way_released = moved_local(180.0, push_delta)
        wrong_way_released.apply_transform(local_to_run)
        if positive_solid_intersection_volume_mm3(
            wrong_way_released, installed_cassette
        ) > 1.0e-5:
            raise ValueError(
                f"{metrics['logical_instance_id']}: +0.8 mm keeper release push "
                "does not clear the wrong-way index"
            )
        wrong_way_collisions.append(wrong_way_overlap)

    return {
        "status": "PASS: REAL KEEPER PIN INSERT/ROTATE/INDEX/INVERSE BOOLEAN SWEEPS",
        "owning_cassette_count": len(owners),
        "entry_or_withdraw_translation_station_count": len(approach_deltas),
        "quarter_turn_or_inverse_angle_station_count": len(rotation_angles),
        "index_seat_or_release_station_count": len(seat_deltas),
        "real_parent_collision_free_boolean_pair_count": checked_pairs,
        "wrong_way_hard_index_collision_count": len(wrong_way_collisions),
        "minimum_wrong_way_index_collision_volume_mm3": round(
            min(wrong_way_collisions), 6
        ),
        "unlock_push_e_mm": push_delta,
        "inverse_removal_uses_exact_reversed_states": True,
        "front_tie_vertical_variant_included": False,
        "front_tie_vertical_variant_status": "PROHIBITED_PENDING_VISIBLE_FRONT_Q_AXIS_CONTRACT",
    }


def validate_front_tie_pin_parent_sweeps(
    cfg: dict[str, Any],
    *,
    cassettes: Iterable[PrototypePart],
    front_tie: PrototypePart,
    front_tie_pin: PrototypePart,
) -> dict[str, Any]:
    """Prove the visible-front tie and q-axis pin against both real cassettes."""

    shared = crown_retention_pin_contract(cfg)
    tie_contract = shared.front_tie
    tie_local = front_tie.mesh.copy()
    tie_local.apply_transform(
        np.asarray(
            front_tie.design_metrics["installed_from_saved_matrix_row_major"],
            dtype=float,
        )
    )
    pin_local = front_tie_pin.mesh.copy()
    pin_local.apply_transform(
        np.asarray(
            front_tie_pin.design_metrics["installed_from_saved_matrix_row_major"],
            dtype=float,
        )
    )
    pin_u, pin_e = tie_contract.center_u_e_mm

    def moved_pin(angle_from_locked_deg: float, delta_q_mm: float) -> trimesh.Trimesh:
        moving = pin_local.copy()
        moving.apply_transform(
            trimesh.transformations.rotation_matrix(
                math.radians(angle_from_locked_deg),
                [0.0, 1.0, 0.0],
                point=[pin_u, 0.0, pin_e],
            )
        )
        moving.apply_translation([0.0, delta_q_mm, 0.0])
        return moving

    cassette_list = list(cassettes)
    by_run_position = {
        (
            str(part.design_metrics["run_id"]),
            int(part.design_metrics["position_index_1_based"]),
        ): part
        for part in cassette_list
    }
    owners = [
        part
        for part in cassette_list
        if part.design_metrics.get("fixed_crown_front_tie_pin_receiver_generated")
    ]
    if len(owners) != 9:
        raise ValueError("Front-tie q-axis receiver ownership must resolve to nine cassettes")

    tie_clear_delta = (
        float(front_tie.design_metrics["key_band_depth_mm"]) + 0.4
    )
    tie_deltas = np.linspace(
        tie_clear_delta,
        0.0,
        int(round(tie_clear_delta / 0.4)) + 1,
    )
    clear_q = float(tie_contract.clear_approach_translation_q_mm)
    unlock_q = -float(shared.unlock_push_e_mm)
    pin_translation_deltas = np.linspace(
        clear_q,
        unlock_q,
        int(round((clear_q - unlock_q) / 0.4)) + 1,
    )
    pin_rotation_angles = np.linspace(90.0, 0.0, 91)
    pin_seat_deltas = np.linspace(unlock_q, 0.0, 3)
    pin_stages: list[tuple[str, trimesh.Trimesh]] = []
    pin_stages.extend(
        ("entry_or_withdraw", moved_pin(90.0, float(delta)))
        for delta in pin_translation_deltas
    )
    pin_stages.extend(
        ("quarter_turn_or_inverse", moved_pin(float(angle), unlock_q))
        for angle in pin_rotation_angles
    )
    pin_stages.extend(
        ("index_seat_or_release", moved_pin(0.0, float(delta)))
        for delta in pin_seat_deltas
    )

    checked_tie_pairs = 0
    checked_pin_pairs = 0
    wrong_way_collisions: list[float] = []
    for owner in owners:
        metrics = owner.design_metrics
        run_id = str(metrics["run_id"])
        owner_position = int(metrics["position_index_1_based"])
        mate = by_run_position.get((run_id, owner_position + 1))
        if mate is None or mate.design_metrics["seams"]["left"]["class"] != "fixed_crown":
            raise ValueError(
                f"{metrics['logical_instance_id']}: front-tie owner lacks its right cassette mate"
            )
        physical_face = float(metrics["physical_interval_local_mm"][1])
        local_to_run = np.asarray(
            [
                [-1.0, 0.0, 0.0, physical_face],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        installed_parents: list[tuple[trimesh.Trimesh, str]] = []
        for cassette, label in ((owner, "left owner"), (mate, "right mate")):
            installed = cassette.mesh.copy()
            installed.apply_transform(
                np.asarray(
                    cassette.design_metrics["saved_print_transform"][
                        "saved_to_run_matrix_row_major"
                    ],
                    dtype=float,
                )
            )
            installed_parents.append((installed, label))

        seated_tie = tie_local.copy()
        seated_tie.apply_transform(local_to_run)
        for delta in tie_deltas:
            moving_tie = tie_local.copy()
            moving_tie.apply_translation([0.0, float(delta), 0.0])
            moving_tie.apply_transform(local_to_run)
            for parent, label in installed_parents:
                overlap = positive_solid_intersection_volume_mm3(
                    moving_tie, parent
                )
                if overlap > 1.0e-5:
                    raise ValueError(
                        f"{metrics['logical_instance_id']}: front tie at q delta "
                        f"{delta:.1f} overlaps {label} by {overlap:.9f} mm3"
                    )
                checked_tie_pairs += 1

        pin_parents = [*installed_parents, (seated_tie, "seated front tie")]
        for stage_name, local_pin in pin_stages:
            moving_pin = local_pin.copy()
            moving_pin.apply_transform(local_to_run)
            for parent, label in pin_parents:
                overlap = positive_solid_intersection_volume_mm3(
                    moving_pin, parent
                )
                if overlap > 1.0e-5:
                    raise ValueError(
                        f"{metrics['logical_instance_id']}: front-tie pin "
                        f"{stage_name} overlaps {label} by {overlap:.9f} mm3"
                    )
                checked_pin_pairs += 1

        wrong_way = moved_pin(180.0, 0.0)
        wrong_way.apply_transform(local_to_run)
        wrong_way_overlap = positive_solid_intersection_volume_mm3(
            wrong_way, seated_tie
        )
        if wrong_way_overlap <= 1.0e-3:
            raise ValueError(
                f"{metrics['logical_instance_id']}: wrong-way front-tie index can seat"
            )
        wrong_way_released = moved_pin(180.0, unlock_q)
        wrong_way_released.apply_transform(local_to_run)
        if positive_solid_intersection_volume_mm3(
            wrong_way_released, seated_tie
        ) > 1.0e-5:
            raise ValueError(
                f"{metrics['logical_instance_id']}: front-tie unlock push does not clear the hard index"
            )
        wrong_way_collisions.append(wrong_way_overlap)

    return {
        "status": "PASS: REAL FRONT-TIE INSERT/Q-PIN ROTATE/INDEX/INVERSE BOOLEAN SWEEPS",
        "owning_cassette_count": len(owners),
        "front_tie_translation_station_count": len(tie_deltas),
        "pin_translation_station_count": len(pin_translation_deltas),
        "pin_rotation_station_count": len(pin_rotation_angles),
        "pin_seating_station_count": len(pin_seat_deltas),
        "real_parent_tie_collision_free_boolean_pair_count": checked_tie_pairs,
        "real_parent_pin_collision_free_boolean_pair_count": checked_pin_pairs,
        "wrong_way_hard_index_collision_count": len(wrong_way_collisions),
        "minimum_wrong_way_index_collision_volume_mm3": round(
            min(wrong_way_collisions), 6
        ),
        "inverse_removal_uses_exact_reversed_states": True,
        "prohibited_vertical_front_tie_variant_included": False,
    }


def seam_keys(cfg: dict[str, Any]) -> list[PrototypePart]:
    diaphragm = deep_get(cfg, "joinery.diaphragm_bowtie", {})
    front = deep_get(cfg, "joinery.front_entablature_joint", {})
    if not isinstance(diaphragm, dict) or not isinstance(front, dict):
        raise ValueError("joinery diaphragm and front-entablature objects are required")

    fit_clearance = number(cfg, "joinery.nominal_fit_clearance_mm", 0.35)
    diaphragm_receiver_depth = float(diaphragm.get("depth_mm", 20.0))
    diaphragm_key_depth = diaphragm_receiver_depth - 2.0 * fit_clearance
    if diaphragm_key_depth <= 0.0:
        raise ValueError("Diaphragm fit clearance consumes the key depth")
    diaphragm_mesh = bowtie_key_mesh(
        total_span=float(diaphragm.get("overall_span_including_seam_mm", 48.35)),
        head_width=float(diaphragm.get("head_width_mm", 14.0)),
        neck_width=float(diaphragm.get("neck_width_mm", 9.0)),
        insertion_depth=diaphragm_key_depth,
    )
    fixed_span = float(front.get("overall_span_including_seam_mm", 60.35))
    head_width = float(front.get("head_width_mm", 12.0))
    neck_width = float(front.get("neck_width_mm", 8.0))
    fixed_tie = front.get("fixed_crown_tie_key", {})
    if not isinstance(fixed_tie, dict):
        raise ValueError("Fixed crown front-tie key contract is incomplete")
    receiver_depth = float(front.get("depth_mm", 18.0))
    key_q = tuple(float(value) for value in fixed_tie["key_q_envelope_at_hard_stop_mm"])
    insertion_depth = key_q[1] - key_q[0]
    if insertion_depth <= 0.0:
        raise ValueError("Front-key fit clearance consumes the key depth")
    fixed_mesh = bowtie_key_mesh(
        total_span=fixed_span,
        head_width=head_width,
        neck_width=neck_width,
        insertion_depth=insertion_depth,
    )
    shared_pin = crown_retention_pin_contract(cfg)
    tie_pin = shared_pin.front_tie
    key_e = tuple(
        float(value) for value in fixed_tie["key_y_envelope_at_hard_stop_mm"]
    )
    # Work in the fixed-crown local system: +u points inward into the owning
    # left cassette, q points rear-to-front, and e points upward.  The generic
    # bowtie source is centered on the nominal seam before the exact local eye
    # is substituted.
    fixed_installed = fixed_mesh.copy()
    left_engagement = float(front.get("engagement_each_side_mm", 30.0))
    fixed_installed.apply_transform(
        np.asarray(
            [
                [-1.0, 0.0, 0.0, left_engagement],
                [0.0, 1.0, 0.0, key_q[0]],
                [0.0, 0.0, 1.0, key_e[0]],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
    )
    eye_u, eye_e = tie_pin.tie_eye_u_e_mm
    entry_u, entry_e = tie_pin.entry_gate_u_e_mm
    entry_q = tie_pin.entry_throat_q_mm
    trim = cuboid(
        (
            eye_u[1] - eye_u[0],
            entry_q[0] - key_q[0],
            eye_e[1] - eye_e[0],
        ),
        origin=(eye_u[0], key_q[0], eye_e[0]),
    )
    fixed_installed = safe_difference_installed(
        fixed_installed,
        [trim],
        "fixed crown tie local rear eye substitution",
    )
    eye = cuboid(
        (
            eye_u[1] - eye_u[0],
            entry_q[1] - entry_q[0],
            eye_e[1] - eye_e[0],
        ),
        origin=(eye_u[0], entry_q[0], eye_e[0]),
    )
    eye_parent_overlap = positive_solid_intersection_volume_mm3(
        fixed_installed, eye
    )
    if eye_parent_overlap <= 1.0e-5:
        raise ValueError("Front-tie integral eye has no positive tie-body union")
    fixed_installed = safe_union_installed(
        [fixed_installed, eye],
        "fixed crown tie plus integral visible-front pin eye",
    )
    index_pocket = tie_pin.index_pocket_u_e_q_mm
    tie_cutters = [
        cuboid(
            (
                entry_u[1] - entry_u[0],
                entry_q[1] - entry_q[0] + 0.2,
                entry_e[1] - entry_e[0],
            ),
            origin=(entry_u[0], entry_q[0], entry_e[0]),
        ),
        cuboid(
            (
                index_pocket[0][1] - index_pocket[0][0],
                index_pocket[2][1] - index_pocket[2][0],
                index_pocket[1][1] - index_pocket[1][0],
            ),
            origin=(
                index_pocket[0][0],
                index_pocket[2][0],
                index_pocket[1][0],
            ),
        ),
    ]
    fixed_installed = safe_difference_installed(
        fixed_installed,
        tie_cutters,
        "fixed crown tie q-axis pin gate and unique index pocket",
    )
    fixed_saved_from_installed = np.asarray(
        [
            [-1.0, 0.0, 0.0, left_engagement],
            [0.0, 1.0, 0.0, -key_q[0]],
            [0.0, 0.0, 1.0, -key_e[0]],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    fixed_installed_from_saved = np.linalg.inv(fixed_saved_from_installed)
    fixed_mesh = fixed_installed.copy()
    fixed_mesh.apply_transform(fixed_saved_from_installed)
    fixed_mesh = finish_mesh(fixed_mesh)
    if not fixed_mesh.is_watertight or fixed_mesh.body_count != 1:
        raise ValueError("Fixed-crown tie with integral q-axis eye is not one body")
    return [
        PrototypePart(
            name="R6_DEV_DIAPHRAGM_BOWTIE_KEY",
            mesh=diaphragm_mesh,
            purpose="Broad-bearing cassette diaphragm Dutchman key geometry coupon.",
            saved_orientation="largest bowtie plan face on build plate",
            notes=["Receiver pockets and final per-flank clearance come only after the fit ladder is measured."],
            design_metrics={
                "span_mm": float(diaphragm.get("overall_span_including_seam_mm", 48.35)),
                "head_width_mm": float(diaphragm.get("head_width_mm", 14.0)),
                "neck_width_mm": float(diaphragm.get("neck_width_mm", 9.0)),
                "receiver_band_depth_mm": diaphragm_receiver_depth,
                "key_band_depth_mm": diaphragm_key_depth,
                "clearance_per_y_face_mm": fit_clearance,
            },
        ),
        PrototypePart(
            name="R6_DEV_FIXED_CROWN_FRONT_INSERTED_ENTABLATURE_TIE_WITH_Q_AXIS_PIN_EYE",
            mesh=fixed_mesh,
            purpose="Exact-depth visible-front fixed crown tie with a real hard stop, local pin eye, entry gate, and unique hard-index pocket.",
            saved_orientation="largest bowtie plan face on build plate",
            status="SOFTWARE PARENT GEOMETRY EMBODIED; ACTUAL-PARENT PIN SWEEPS AND PETG CYCLE/MIGRATION QUALIFICATION REQUIRED; ZERO LOAD CREDIT",
            notes=[
                "Never install this fixed-key geometry at a thermally floating supported pier seam.",
                "The indexed q-axis pin is the only positive anti-withdrawal feature; friction and arch contact are prohibited as retention.",
            ],
            design_metrics={
                "span_mm": fixed_span,
                "head_width_mm": head_width,
                "neck_width_mm": neck_width,
                "receiver_band_depth_mm": receiver_depth,
                "key_band_depth_mm": insertion_depth,
                "installed_key_q_envelope_mm": list(key_q),
                "front_open_receiver_q_envelope_mm": fixed_tie[
                    "front_open_receiver_q_envelope_mm"
                ],
                "rear_hard_stop_q_mm": float(fixed_tie["rear_hard_stop_q_mm"]),
                "integral_pin_eye_u_e_q_mm": [
                    list(eye_u),
                    list(eye_e),
                    list(entry_q),
                ],
                "integral_pin_eye_parent_union_volume_mm3": round(
                    eye_parent_overlap, 6
                ),
                "pin_entry_gate_u_e_q_mm": [
                    list(entry_u),
                    list(entry_e),
                    list(entry_q),
                ],
                "hard_index_pocket_u_e_q_mm": [
                    list(pair) for pair in index_pocket
                ],
                "saved_from_installed_matrix_row_major": (
                    fixed_saved_from_installed.tolist()
                ),
                "installed_from_saved_matrix_row_major": (
                    fixed_installed_from_saved.tolist()
                ),
                "positive_q_axis_pin_eye_generated": True,
                "software_model_mapping_complete": False,
                "physical_installation_mapping_qualified": False,
                "production_release_eligible": False,
            },
        ),
    ]


def calculate_development_geometry(cfg: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Resolve authoritative r6 math and fail closed on any schema drift."""

    plan = calculate_plan(cfg)
    width = max(
        *plan.through.cassette_physical_widths_mm,
        *plan.return_run.cassette_physical_widths_mm,
    )
    span = max(plan.through.bay_span_mm, plan.return_run.bay_span_mm)
    corbel_geometry = x_corbel_geometry(cfg)

    return (
        {
            "cassette_width_mm": width,
            "shelf_depth_mm": number(cfg, "closet.shelf_depth_in", 6.0) * 25.4,
            "worst_bay_span_mm": span,
            "plan_source": "development/r6/design_math.py:calculate_plan",
            "plan_summary": plan.to_dict(),
            "plan_object": plan,
            "corbel_source": "development/r6/design_math.py:x_corbel_geometry",
            "corbel_geometry": corbel_geometry,
        },
        [],
    )


def validate_part(
    part: PrototypePart,
    *,
    envelope_mm: np.ndarray,
    density_g_cm3: float,
) -> dict[str, Any]:
    mesh = finish_mesh(part.mesh)
    part.mesh = mesh
    bounds = np.asarray(mesh.bounds, dtype=float)
    size = bounds[1] - bounds[0]
    components = mesh.split(only_watertight=False)
    result = {
        "name": part.name,
        "status": part.status,
        "purpose": part.purpose,
        "saved_orientation": part.saved_orientation,
        "notes": part.notes,
        "design_metrics": part.design_metrics,
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "is_volume": bool(mesh.is_volume),
        "connected_surface_body_count": int(len(components)),
        "bounds_mm": np.round(bounds, 4).tolist(),
        "size_mm": np.round(size, 4).tolist(),
        "volume_mm3": round(float(mesh.volume), 3),
        "estimated_solid_petg_mass_g": round(float(mesh.volume) / 1000.0 * density_g_cm3, 2),
        "minimum_build_envelope_mm": envelope_mm.tolist(),
        "fits_minimum_build_envelope_in_saved_orientation": bool(
            np.all(size <= envelope_mm + 1e-6)
        ),
    }
    failures: list[str] = []
    if not result["watertight"]:
        failures.append("mesh is not watertight")
    if not result["winding_consistent"]:
        failures.append("mesh winding is inconsistent")
    if not result["is_volume"] or result["volume_mm3"] <= 0.0:
        failures.append("mesh is not a positive closed volume")
    if result["connected_surface_body_count"] != 1:
        failures.append(
            f"mesh contains {result['connected_surface_body_count']} connected surface bodies"
        )
    if not result["fits_minimum_build_envelope_in_saved_orientation"]:
        failures.append(f"saved size {size.tolist()} exceeds build envelope {envelope_mm.tolist()}")
    result["validation_failures"] = failures
    result["development_mesh_validation_passed"] = not failures
    if failures:
        raise ValueError(f"{part.name}: " + "; ".join(failures))
    return result


def safe_reset_generated_files() -> None:
    """Remove only artifacts bearing this generator's own deterministic names."""

    if OUT.resolve().parent != R6_DIR.resolve() or OUT.name != "generated":
        raise RuntimeError(f"Refusing to clean unexpected output path: {OUT}")
    STL_OUT.mkdir(parents=True, exist_ok=True)
    MODEL_3MF_OUT.mkdir(parents=True, exist_ok=True)
    INDIVIDUAL_MODEL_3MF_OUT.mkdir(parents=True, exist_ok=True)
    for path in STL_OUT.glob("*.stl"):
        if path.is_file() and not path.is_symlink():
            path.unlink()
    for path in MODEL_3MF_OUT.glob("*.3mf"):
        if path.is_file() and not path.is_symlink():
            path.unlink()
    for path in INDIVIDUAL_MODEL_3MF_OUT.glob("*.3mf"):
        if path.is_file() and not path.is_symlink():
            path.unlink()
    for report_name in (
        "validation.json",
        "manifest.json",
        "slice_report.json",
        "model_3mf_report.json",
        "parts_schedule_one_level.csv",
        "parts_schedule_one_level.json",
        "parts_schedule_two_levels.csv",
        "parts_schedule_two_levels.json",
    ):
        report_path = OUT / report_name
        if report_path.is_file() and not report_path.is_symlink():
            report_path.unlink()
    drawings_out = OUT / "drawings"
    if drawings_out.is_dir() and not drawings_out.is_symlink():
        for path in drawings_out.glob("*.svg"):
            if path.is_file() and not path.is_symlink():
                path.unlink()


def model_only_description(cfg: dict[str, Any]) -> str:
    project = deep_get(cfg, "project.name", "Story Corner")
    edition = deep_get(cfg, "project.edition", "All-PETG r6 Development")
    revision = deep_get(cfg, "project.revision", "r6_development")
    return (
        f"{project} — {edition}; revision {revision}. "
        "MODEL-ONLY; EXPERIMENTAL; UNRATED; NO G-CODE. "
        "DEVELOPMENT PROTOTYPE ONLY; NOT AN OVERHEAD INSTALLATION SET. "
        "Confirm printer, nozzle, plate, PETG, fits, wall "
        "fasteners, blocking, measurements, and the full test protocol before slicing later revisions."
    )


def write_part_files(
    parts: list[PrototypePart],
    cfg: dict[str, Any],
    *,
    include_development_3mf: bool = True,
) -> None:
    """Write deterministic STL and separate individual neutral-3MF pairs.

    Individual 3MFs live outside ``model_only_3mf`` so that directory remains
    the exact five-package canonical set.  Both formats are authored from the
    same STL-ready mesh; their independently decoded triangles must then have
    an exact canonical digest on the shared 0.001 mm audit grid.
    """

    # Keep the same exact safety metadata contract as every canonical package.
    # Richer scope prose belongs in validation/report records, not a divergent
    # 3MF metadata string.
    description = SAFETY_DESCRIPTION
    for part in parts:
        stl_path = STL_OUT / f"{part.name}.stl"
        shared_mesh = serialization_ready_mesh(
            part.mesh,
            target="stl",
            source_name=part.name,
        )
        stl_path.write_bytes(trimesh.exchange.stl.export_stl(shared_mesh))
        audit_serialized_stl(stl_path)
        if not include_development_3mf:
            continue
        # ``shared_mesh`` is already the audited STL float32 geometry.  Write
        # that exact indexed mesh directly at model_io's round-trip vertex
        # precision; re-running the independent 3MF repair path here could
        # legitimately choose a different (still closed) quantization and
        # would defeat the required exact STL/3MF geometry bijection.
        _write_model_3mf(
            INDIVIDUAL_MODEL_3MF_OUT / f"MODEL_ONLY_{part.name}.3mf",
            part.name,
            description,
            [(part.name, shared_mesh, (0.0, 0.0, 0.0))],
        )


def _strict_positive_triangle_mask(mesh: trimesh.Trimesh) -> np.ndarray:
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    triangles = vertices[np.asarray(mesh.faces, dtype=np.int64)]
    cross = np.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    return np.einsum("ij,ij->i", cross, cross) > 0.0


def audit_serialized_stl(path: Path) -> dict[str, Any]:
    """Reload one actual binary STL as an ordinary consumer would."""

    result = inspect_serialized_stl_geometry(path)
    # Stable compatibility labels retained for existing report consumers.
    result["raw_triangle_count"] = result["triangle_count"]
    result["raw_zero_area_triangle_count"] = result["zero_area_triangle_count"]
    result["ordinary_reload_triangle_count"] = result["triangle_count"]
    if not result["serialized_geometry_audit_passed"]:
        raise ValueError(f"{path.name}: serialized STL geometry audit failed: {result}")
    return result


def audit_serialized_3mf_meshes(model_payload: bytes) -> dict[str, Any]:
    """Validate the literal round-trip-decimal mesh resources stored in a 3MF."""

    namespace = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    root = ET.fromstring(model_payload)
    mesh_objects = root.findall("m:resources/m:object[m:mesh]", namespace)
    failures: list[str] = []
    zero_area_count = 0
    triangle_count = 0
    for node in mesh_objects:
        name = node.attrib.get("name", node.attrib.get("id", "unnamed"))
        vertex_nodes = node.findall("m:mesh/m:vertices/m:vertex", namespace)
        triangle_nodes = node.findall("m:mesh/m:triangles/m:triangle", namespace)
        try:
            vertices = np.asarray(
                [
                    [float(vertex.attrib[axis]) for axis in ("x", "y", "z")]
                    for vertex in vertex_nodes
                ],
                dtype=np.float64,
            )
            faces = np.asarray(
                [
                    [int(face.attrib[index]) for index in ("v1", "v2", "v3")]
                    for face in triangle_nodes
                ],
                dtype=np.int64,
            )
        except (KeyError, ValueError) as exc:
            failures.append(f"{name}: malformed numeric mesh payload ({exc})")
            continue
        if len(vertices) == 0 or len(faces) == 0:
            failures.append(f"{name}: empty serialized mesh")
            continue
        if np.any(faces < 0) or np.any(faces >= len(vertices)):
            failures.append(f"{name}: triangle index outside vertex array")
            continue
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
        positive = _strict_positive_triangle_mask(mesh)
        collapsed = int(np.count_nonzero(~positive))
        zero_area_count += collapsed
        triangle_count += int(len(faces))
        body_count = len(mesh.split(only_watertight=False))
        if collapsed:
            failures.append(f"{name}: {collapsed} zero-area serialized triangles")
        if not mesh.is_watertight:
            failures.append(f"{name}: serialized mesh is not watertight")
        if not mesh.is_winding_consistent:
            failures.append(f"{name}: serialized winding is inconsistent")
        if not mesh.is_volume:
            failures.append(f"{name}: serialized mesh is not a positive volume")
        if body_count != 1:
            failures.append(f"{name}: serialized mesh has {body_count} bodies")
    return {
        "serialized_mesh_resource_count": len(mesh_objects),
        "serialized_triangle_count": triangle_count,
        "serialized_zero_area_triangle_count": zero_area_count,
        "serialized_mesh_failures": failures,
        "serialized_mesh_geometry_audit_passed": bool(mesh_objects and not failures),
    }


def audit_3mf(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path, "r") as archive:
        entries = sorted(archive.namelist())
        corrupt_member = archive.testzip()
        model_payload = archive.read("3D/3dmodel.model")
    forbidden = [
        entry
        for entry in entries
        if entry.lower().endswith((".gcode", ".gco", ".bgcode"))
        or "/gcode" in entry.lower()
    ]
    required_description_tokens = ("MODEL-ONLY", "EXPERIMENTAL", "UNRATED", "NO G-CODE")
    model_text = model_payload.decode("utf-8")
    description_tokens_present = {
        token: token in model_text for token in required_description_tokens
    }
    serialized_geometry = audit_serialized_3mf_meshes(model_payload)
    expected = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
    try:
        display_path = str(path.relative_to(OUT))
    except ValueError:
        display_path = path.name
    result = {
        "path": display_path,
        "archive_entries": entries,
        "archive_crc_test_passed": corrupt_member is None,
        "model_xml_sha256": sha256_bytes(model_payload),
        "embedded_gcode_entries": forbidden,
        "required_description_tokens_present": description_tokens_present,
        "contains_only_neutral_3mf_core_entries": set(entries) == expected,
        **serialized_geometry,
        "model_only_audit_passed": (
            corrupt_member is None
            and not forbidden
            and set(entries) == expected
            and all(description_tokens_present.values())
            and serialized_geometry["serialized_mesh_geometry_audit_passed"]
        ),
    }
    if not result["model_only_audit_passed"]:
        raise ValueError(f"{path.name}: model-only 3MF audit failed: {result}")
    return result


def audit_individual_stl_3mf_pair(
    *,
    source_name: str,
    stl_path: Path,
    three_mf_path: Path,
) -> dict[str, Any]:
    """Require an exact one-source STL/3MF geometry and name bijection."""

    expected_stl_name = f"{source_name}.stl"
    expected_three_mf_name = f"MODEL_ONLY_{source_name}.3mf"
    stl = audit_serialized_stl(stl_path)
    neutral = inspect_model_only_3mf(three_mf_path)
    model_only = audit_3mf(three_mf_path)
    geometry_records = neutral.get("serialized_mesh_geometry_records", [])
    three_mf_geometry = (
        geometry_records[0]
        if isinstance(geometry_records, list) and len(geometry_records) == 1
        else {}
    )
    checks = {
        "source_name_nonempty": isinstance(source_name, str) and bool(source_name),
        "exact_stl_basename": stl_path.name == expected_stl_name,
        "exact_individual_3mf_basename": (
            three_mf_path.name == expected_three_mf_name
        ),
        "stl_serialized_closed_solid": stl.get(
            "serialized_geometry_audit_passed"
        )
        is True,
        "individual_3mf_neutral_core_audit_passed": (
            neutral.get("all_checks_pass") is True
            and model_only.get("model_only_audit_passed") is True
        ),
        "individual_3mf_exactly_one_mesh_and_one_build_item": (
            neutral.get("resource_object_count") == 1
            and neutral.get("mesh_family_count") == 1
            and neutral.get("component_object_count") == 0
            and neutral.get("build_object_count") == 1
        ),
        "individual_3mf_names_equal_source": (
            neutral.get("metadata", {}).get("Title") == source_name
            and neutral.get("mesh_resource_names") == [source_name]
            and neutral.get("build_object_names") == [source_name]
        ),
        "stl_and_3mf_triangle_counts_equal": (
            stl.get("triangle_count") == three_mf_geometry.get("triangle_count")
        ),
        "stl_and_3mf_bounds_equal_on_common_grid": (
            stl.get("bounds_mm") == three_mf_geometry.get("bounds_mm")
        ),
        "stl_and_3mf_canonical_triangle_geometry_digest_equal": (
            stl.get("canonical_triangle_digest_common_grid")
            == three_mf_geometry.get(
                "canonical_triangle_digest_common_grid"
            )
            and isinstance(
                stl.get("canonical_triangle_digest_common_grid"),
                str,
            )
        ),
        "individual_3mf_contains_no_embedded_gcode": not model_only.get(
            "embedded_gcode_entries",
            ["missing-audit"],
        ),
    }
    if not all(checks.values()):
        raise ValueError(
            f"{source_name}: individual STL/3MF pair audit failed: "
            f"{[name for name, passed in checks.items() if not passed]}"
        )
    return {
        "source_part_name": source_name,
        "stl_path": stl_path.relative_to(OUT).as_posix(),
        "individual_3mf_path": three_mf_path.relative_to(OUT).as_posix(),
        "common_geometry_grid_mm": 0.001,
        "common_canonical_triangle_digest": stl[
            "canonical_triangle_digest_common_grid"
        ],
        "triangle_count": stl["triangle_count"],
        "bounds_mm": stl["bounds_mm"],
        "checks": checks,
        "all_checks_pass": True,
        "model_only": True,
        "embedded_gcode_entry_count": 0,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
    }


def audit_canonical_package_sources_against_individual_exports(
    *,
    plans: Iterable[Any],
    package_validations: Iterable[dict[str, Any]],
    individual_pair_audits: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Prove every canonical source resource equals its named STL/3MF pair.

    Package resources are compact-instanced, while individual deliverables are
    standalone files.  Names alone are insufficient: each package resource
    must carry the same triangle count, common-grid bounds, and canonical
    triangle digest as the corresponding audited individual export.
    """

    plan_items = tuple(plans)
    validation_items = tuple(package_validations)
    pairs = tuple(individual_pair_audits)
    if len(plan_items) != len(validation_items):
        raise ValueError("Canonical package geometry audit lacks a plan/validation pair")
    pair_by_source = {
        str(item["source_part_name"]): item
        for item in pairs
        if isinstance(item, dict) and item.get("all_checks_pass") is True
    }
    if len(pair_by_source) != len(pairs) or len(pair_by_source) != 49:
        raise ValueError("Canonical package geometry audit requires 49 unique passing individual pairs")

    package_reports: list[dict[str, Any]] = []
    total_resource_count = 0
    for plan, validation in zip(plan_items, validation_items, strict=True):
        records = validation.get("serialized_mesh_geometry_records", [])
        observed = {
            str(record.get("name")): record
            for record in records
            if isinstance(record, dict) and record.get("name")
        }
        expected_names = {
            f"SOURCE__{family}" for family in plan.mesh_families
        }
        failures: list[str] = []
        if set(observed) != expected_names:
            failures.append("resource-name-set")
        for family in plan.mesh_families:
            source_name = str(family).split("::", 1)[-1]
            expected = pair_by_source.get(source_name)
            record = observed.get(f"SOURCE__{family}")
            if expected is None or record is None:
                failures.append(f"{family}:missing")
                continue
            if int(record.get("triangle_count", -1)) != int(
                expected.get("triangle_count", -2)
            ):
                failures.append(f"{family}:triangle-count")
            if record.get("bounds_mm") != expected.get("bounds_mm"):
                failures.append(f"{family}:bounds")
            if record.get("canonical_triangle_digest_common_grid") != expected.get(
                "common_canonical_triangle_digest"
            ):
                failures.append(f"{family}:canonical-digest")
            if (
                record.get("zero_area_triangle_count") != 0
                or record.get("watertight") is not True
                or record.get("winding_consistent") is not True
                or record.get("positive_volume") is not True
                or record.get("body_count") != 1
            ):
                failures.append(f"{family}:closed-solid")
        if failures:
            raise ValueError(
                f"{plan.package_id}: canonical package source geometry differs from "
                f"the emitted individual source set: {failures}"
            )
        total_resource_count += len(observed)
        package_reports.append(
            {
                "package_id": plan.package_id,
                "source_resource_count": len(observed),
                "all_sources_equal_named_individual_exports": True,
            }
        )
    return {
        "status": "PASS: CANONICAL PACKAGE SOURCES EQUAL NAMED STL/INDIVIDUAL-3MF EXPORTS",
        "individual_source_count": len(pair_by_source),
        "canonical_package_count": len(package_reports),
        "canonical_source_resource_comparison_count": total_resource_count,
        "packages": package_reports,
        "all_checks_pass": True,
    }


def shelf_level_context(cfg: dict[str, Any]) -> dict[str, Any]:
    candidates = (
        "closet.vertical_layout.selected_shelf_levels",
        "closet.selected_shelf_levels",
        "vertical_layout.selected_shelf_levels",
        "shelf_levels.selected",
    )
    source = "explicit r6 development requirement"
    selected: Any = None
    for path in candidates:
        candidate = deep_get(cfg, path, None)
        if candidate is not None:
            selected = candidate
            source = f"config.{path}"
            break
    if selected is None:
        selected = 2
    selected = int(selected)
    if selected < 2:
        raise ValueError("r6 requires a minimum of two independently fastened shelf levels")

    vertical = cfg["closet"]["vertical_layout"]
    provisional_offsets = [
        float(vertical["reference_lower_shelf_top_above_outlet_top_in"]),
        float(vertical["reference_upper_shelf_top_above_outlet_top_in"]),
    ]
    if len(provisional_offsets) < selected:
        raise ValueError("The vertical layout must name every selected shelf-top elevation")
    per_level = deep_get(cfg, "nominal_geometry_snapshot.nominal_part_topology", {})
    if not isinstance(per_level, dict):
        per_level = {}
    all_levels = {
        key: int(value) * selected
        for key, value in per_level.items()
        if isinstance(value, int) and not isinstance(value, bool)
    }
    return {
        "selected_shelf_levels": selected,
        "selection_source": source,
        "assembly_rule": "Each level is a complete, independently wall-fastened L assembly.",
        "vertical_structural_ties_between_levels": 0,
        "vertical_tie_policy": "No printed or nonprinted structural tie transfers shelf load between levels.",
        "provisional_top_offsets_above_outlet_top_in": provisional_offsets[:selected],
        "provisional_layout_status": "UNCONFIRMED pending bin heights and a common laser elevation datum",
        "nominal_top_to_top_spacing_in": (
            float(vertical["reference_top_to_top_spacing_in"]) if selected >= 2 else None
        ),
        "nominal_clear_opening_between_levels_in": float(
            vertical["reference_clear_opening_between_levels_in"]
        ),
        "nominal_clearance_above_upper_shelf_in": float(
            vertical["reference_clearance_above_upper_shelf_in"]
        ),
        "nominal_lower_frame_bottom_above_outlet_top_in": float(
            vertical["reference_lower_frame_bottom_above_outlet_top_in"]
        ),
        "grand_frame_drop_in": round(
            number(cfg, "tied_arcade.total_height_mm", 168.0) / 25.4,
            4,
        ),
        "nominal_part_topology_per_level_regression_context_only": per_level,
        "nominal_part_topology_all_levels_regression_context_only": all_levels,
        "prototype_mesh_policy": "Unique development prototypes are emitted once, not duplicated per shelf level.",
    }


def collect_production_blockers(cfg: dict[str, Any]) -> list[str]:
    try:
        blockers = list(production_blockers(cfg))
    except (KeyError, TypeError, ValueError) as exc:
        blockers = [f"production_blockers schema could not be fully evaluated: {exc}"]
    additional_paths = (
        "test_protocol.target_test_load_lb",
        "test_protocol.deflection_stop_limit_mm",
        "test_protocol.permanent_set_stop_limit_mm",
    )
    for path in additional_paths:
        if deep_get(cfg, path, None) is None:
            blockers.append(path)
    blockers.extend(
        [
            "confirm the actual printer model, nozzle, black PETG brand/lot, drying state, and usable 180 mm build plate before any print mapping",
            "same-PETG actual-parent orientation, connector-fit, lock/pin/cross-key flex-cycle, thermal-cycle, and migration coupons are not physically passed",
            "wall arrangement, finished-wall dimensions/angle/bow, stud or blocking locations/material, utilities, and exact wall-fastener hardware remain field-unverified",
            "Bambu-sliced mass and weighed finished-part tare are not recorded; CAD-solid mass is context only",
            "full worst-case bay comparative, destructive, recovery, and 90-day creep tests not complete",
            "independent review has not established a tested load rating",
        ]
    )
    return sorted(set(str(value) for value in blockers))


def artifact_records(paths: Iterable[Path]) -> list[dict[str, Any]]:
    records = []
    for path in sorted(paths, key=lambda item: str(item.relative_to(OUT))):
        records.append(
            {
                "path": str(path.relative_to(OUT)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return records


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_release_schedules(
    cfg: dict[str, Any], *, plan: Any
) -> tuple[Path, ...]:
    """Write exact one- and two-level physical-object schedules."""

    one_level_records = enumerate_level_inventory(cfg, "lower", plan)
    selected_records = enumerate_selected_inventory(cfg, plan)
    if not one_level_records or not selected_records:
        raise ValueError("Release schedules may not be empty")
    if len(selected_records) != 2 * len(one_level_records):
        raise ValueError("Selected two-level schedule is not exactly two levels")
    payloads = (
        ("parts_schedule_one_level.csv", records_to_csv(one_level_records)),
        ("parts_schedule_one_level.json", records_to_json(one_level_records)),
        ("parts_schedule_two_levels.csv", records_to_csv(selected_records)),
        ("parts_schedule_two_levels.json", records_to_json(selected_records)),
    )
    paths: list[Path] = []
    for filename, payload in payloads:
        path = OUT / filename
        path.write_text(payload, encoding="utf-8", newline="")
        paths.append(path)
    return tuple(paths)


ORNAMENT_RELEASE_FAMILY_MAP: dict[str, str] = {
    "through_carrier_left": "through_left_ornament_carrier",
    "through_carrier_right": "through_right_ornament_carrier",
    "return_carrier_left": "return_left_ornament_carrier",
    "return_carrier_right": "return_right_ornament_carrier",
    "pier_overlay": "ornamental_pier_overlay",
    "ordinary_endcap": "ordinary_outer_end_cap",
    "corner_fixed_rosette": "corner_fixed_rosette",
    "corner_floating_return": "corner_floating_mate",
}


def stitch_rail_parts(
    cfg: dict[str, Any],
    *,
    plan: Any,
    selected_levels: int,
) -> tuple[list[PrototypePart], dict[str, Any]]:
    """Emit the geometry-current *optional* rail study, never baseline parts.

    Every segment is position-specific.  A second independent level repeats
    the same sequence rather than creating another set of source families.
    All counts are derived from the optional planner and checked against its
    configuration-owned topology; none of these research objects may enter an
    installed release package or receive capacity credit.
    """

    lines = plan_all_stitch_rails(cfg, plan)
    expected = cfg["structure"]["stitch_rail_planner"]["expected_per_level"]
    segment_count = sum(len(line.segments) for line in lines)
    joint_count = sum(len(line.joints) for line in lines)
    floating_joint_count = sum(
        joint.joint_class == "floating_supported_pier"
        for line in lines
        for joint in line.joints
    )
    fixed_joint_count = joint_count - floating_joint_count
    pins_per_overlap = int(cfg["structure"]["stitch_rail_joint_pins_per_overlap"])
    pin_count = joint_count * pins_per_overlap
    topology = {
        "rail_segments": segment_count,
        "overlap_joints": joint_count,
        "floating_pier_overlap_joints": floating_joint_count,
        "fixed_overlap_joints": fixed_joint_count,
        "joint_pins": pin_count,
    }
    if any(int(expected[key]) != value for key, value in topology.items()):
        raise AssertionError(
            f"Optional rail topology drift: expected {expected!r}, got {topology!r}"
        )
    run_ids = tuple(sorted({line.run_id for line in lines}))
    run_end_tie_count = 2 * len(run_ids)
    optional_object_count = segment_count + pin_count + run_end_tie_count
    removed_count = int(
        cfg["structure"]["stitch_rail_baseline_policy"]
        ["baseline_part_count_reduction_per_level"]
    )
    if optional_object_count != removed_count:
        raise AssertionError(
            "Optional rail object total disagrees with the rail-free baseline "
            f"reduction: {optional_object_count} != {removed_count}"
        )

    parts: list[PrototypePart] = []
    segment_names: list[str] = []
    line_counts: dict[str, int] = {}
    total_round_holes = 0
    total_elongated_holes = 0
    for line in lines:
        line_key = f"{line.run_id}:{line.line_role}"
        line_counts[line_key] = len(line.segments)
        for segment in line.segments:
            result = stitch_rail_segment_mesh(cfg, segment)
            name = (
                f"R6_DEV_STITCH_RAIL_{line.run_id.upper()}_"
                f"{line.line_role.upper()}_SEGMENT_"
                f"{segment.index + 1:02d}_OF_{len(line.segments):02d}"
            )
            segment_names.append(name)
            total_round_holes += result.round_hole_count
            total_elongated_holes += result.elongated_hole_count
            parts.append(
                PrototypePart(
                    name=name,
                    mesh=result.mesh,
                    purpose=(
                        "Position-specific black-PETG staggered stitch-rail segment "
                        "with complementary 45 mm half-laps."
                    ),
                    saved_orientation="broad rail side face on build plate",
                    status="OPTIONAL RESEARCH RAIL SEGMENT; FIT/LOAD QUALIFICATION REQUIRED; NO LOAD RATING",
                    notes=[
                        "This source mesh is used once per optional-study level at its named run/line position.",
                        "A second study level repeats the same sequence as an independently fastened L assembly.",
                        "Floating-pier overlap slots provide movement; they receive zero longitudinal tension-splice credit.",
                        "This mesh is excluded from every installed/model-assembly release package.",
                    ],
                    design_metrics={
                        "catalog_class": "optional_research_source",
                        "research_family": "stitch_rail_segment",
                        "installed_in_release_candidate": False,
                        "structural_capacity_credit": False,
                        "logical_instance_id_per_level": segment.logical_id,
                        "run_id": segment.run_id,
                        "line_role": segment.line_role,
                        "position_index_1_based": segment.index + 1,
                        "position_count_in_line": len(line.segments),
                        "start_local_mm": round(float(segment.start_local_mm), 6),
                        "end_local_mm": round(float(segment.end_local_mm), 6),
                        "length_mm": round(float(segment.length_mm), 6),
                        "left_joint_class": segment.left_joint_class,
                        "right_joint_class": segment.right_joint_class,
                        "left_half_lap": result.left_half_lap,
                        "right_half_lap": result.right_half_lap,
                        "round_hole_count": result.round_hole_count,
                        "elongated_hole_count": result.elongated_hole_count,
                        "optional_research_repeat_count_per_level": 1,
                        "optional_research_repeat_count_selected_levels": selected_levels,
                        "installed_repeat_count_per_level": 0,
                        "installed_repeat_count_selected_levels": 0,
                        "selected_shelf_levels": selected_levels,
                    },
                )
            )

    if len(parts) != segment_count or len(segment_names) != len(set(segment_names)):
        raise AssertionError(
            "The optional rail catalog must contain one unique named mesh per "
            f"planned segment ({segment_count})"
        )

    pin_name = "R6_DEV_STITCH_RAIL_SHARED_JOINT_PIN"
    parts.append(
        PrototypePart(
            name=pin_name,
            mesh=stitch_rail_pin_mesh(cfg),
            purpose="Shared removable PETG pin for the enumerated stitch-rail half-lap joints.",
            saved_orientation=(
                "shaft vertical with its plain tip on the build plate; circular "
                "pull head is uppermost; optional-study orientation is unqualified"
            ),
            status="OPTIONAL RESEARCH RETENTION PART; FIT/LOAD QUALIFICATION REQUIRED; NO LOAD RATING",
            notes=[
                f"The optional study uses {pins_per_overlap} pins at each of its {joint_count} overlap joints per level.",
                "Pins at floating-pier overlaps receive zero longitudinal tension-splice credit.",
                "This mesh is excluded from every installed/model-assembly release package.",
            ],
            design_metrics={
                "catalog_class": "optional_research_source",
                "research_family": "stitch_rail_joint_pin",
                "installed_in_release_candidate": False,
                "optional_research_repeat_count_per_level": pin_count,
                "optional_research_repeat_count_selected_levels": pin_count * selected_levels,
                "installed_repeat_count_per_level": 0,
                "installed_repeat_count_selected_levels": 0,
                "overlap_joint_count_per_level": joint_count,
                "pins_per_overlap": pins_per_overlap,
                "floating_pier_longitudinal_tension_credit": False,
                "structural_capacity_credit": False,
            },
        )
    )

    tie_name = "R6_DEV_RUN_END_TIE_BLOCK_SHARED"
    parts.append(
        PrototypePart(
            name=tie_name,
            mesh=run_end_tie_block_mesh(cfg),
            purpose="Shared run-local X tie between the front and rear stitch rails at a free run end.",
            saved_orientation="largest run-end X-tie face on build plate",
            status="OPTIONAL RESEARCH TIE; FIT/LOAD QUALIFICATION REQUIRED; NO LOAD RATING",
            notes=[
                f"The optional study uses one at each end of {len(run_ids)} independent runs: {run_end_tie_count} per level.",
                "This part is run-local and never creates a rigid structural tie around the L corner.",
                "This study mesh is not an installed release object and receives no capacity credit.",
            ],
            design_metrics={
                "catalog_class": "optional_research_source",
                "research_family": "run_end_tie_block",
                "installed_in_release_candidate": False,
                "optional_research_repeat_count_per_level": run_end_tie_count,
                "optional_research_repeat_count_selected_levels": run_end_tie_count * selected_levels,
                "installed_repeat_count_per_level": 0,
                "installed_repeat_count_selected_levels": 0,
                "rigid_cross_arm_L_connection": False,
                "structural_capacity_credit": False,
            },
        )
    )
    return parts, {
        "status": "PASS: OPTIONAL POSITION-SPECIFIC STITCH-RAIL STUDY; EXCLUDED FROM BASELINE",
        "installed_in_release_candidate": False,
        "structural_capacity_credit": False,
        "unique_position_specific_segment_mesh_count": segment_count,
        "unique_shared_pin_mesh_count": 1,
        "unique_shared_run_end_tie_mesh_count": 1,
        "unique_optional_research_mesh_count": segment_count + 2,
        "segment_mesh_names": segment_names,
        "shared_mesh_names": [pin_name, tie_name],
        "line_segment_counts_per_level": line_counts,
        "planner_topology_per_level": topology,
        "optional_research_counts_per_level": {
            "stitch_rail_segment": segment_count,
            "stitch_rail_joint_pin": pin_count,
            "run_end_tie_block": run_end_tie_count,
        },
        "optional_research_counts_selected_levels": {
            "stitch_rail_segment": segment_count * selected_levels,
            "stitch_rail_joint_pin": pin_count * selected_levels,
            "run_end_tie_block": run_end_tie_count * selected_levels,
        },
        "installed_counts_per_level": {
            "stitch_rail_segment": 0,
            "stitch_rail_joint_pin": 0,
            "run_end_tie_block": 0,
        },
        "installed_counts_selected_levels": {
            "stitch_rail_segment": 0,
            "stitch_rail_joint_pin": 0,
            "run_end_tie_block": 0,
        },
        "optional_research_object_count_per_level": optional_object_count,
        "optional_research_object_count_selected_levels": (
            optional_object_count * selected_levels
        ),
        "round_segment_holes_per_level": total_round_holes,
        "elongated_segment_holes_per_level": total_elongated_holes,
        "unique_vs_repeat_policy": (
            f"{segment_count} position-specific optional segment source meshes are emitted "
            f"once; each study level repeats that {segment_count}-object sequence, so "
            f"{selected_levels} levels would use {segment_count * selected_levels} physical "
            f"segments but still only {segment_count} segment mesh families."
        ),
    }


def removable_ornament_parts(
    cfg: dict[str, Any],
    *,
    selected_levels: int,
) -> tuple[list[PrototypePart], dict[str, Any]]:
    """Emit eight installed zero-credit families plus two fit coupons."""

    visual_contract = ornament_interface_contract(cfg)
    # ornament_geometry predates the explicit structural/visual field split.
    # Feed it a private compatibility view so its facade continues to use the
    # frozen visual 60 -> 152 mm arch while structural meshes use 46 -> 138.
    ornament_cfg = json.loads(json.dumps(cfg))
    ornament_cfg["tied_arcade"]["arch_spring_extrados_y_mm"] = (
        visual_contract.visual_spring_e_mm
    )
    ornament_cfg["tied_arcade"]["arch_extrados_rise_mm"] = (
        visual_contract.visual_rise_mm
    )
    topology = ornament_topology(ornament_cfg)
    instances = ornament_instances_per_level(ornament_cfg)
    families = build_ornament_families(ornament_cfg)
    desired_carrier_widths = {
        "through_carrier_left": visual_contract.through_carrier_width_mm,
        "through_carrier_right": visual_contract.through_carrier_width_mm,
        "return_carrier_left": visual_contract.return_carrier_width_mm,
        "return_carrier_right": visual_contract.return_carrier_width_mm,
    }
    for family_id, desired_width in desired_carrier_widths.items():
        family = families[family_id]
        authored_width = float(family.mesh.extents[0])
        inset = float(visual_contract.visual_seam_mm) / 2.0
        # ornament_geometry authors the physical Wp span directly and samples
        # the visual arc at x_nominal=x_local+0.3.  Post-cropping here would
        # double-apply the inset, move receiver/oculus centers, and destroy the
        # exact 0.6 mm installed seam.
        if abs(authored_width - float(desired_width)) > 1.0e-5:
            raise ValueError(f"{family_id}: directly authored carrier width drift")
        family.design_metrics.update(
            {
                "width_mm": float(desired_width),
                "visual_spring_e_mm": visual_contract.visual_spring_e_mm,
                "visual_crown_e_mm": visual_contract.visual_crown_e_mm,
                "visual_rise_mm": visual_contract.visual_rise_mm,
                "visual_seam_mm": visual_contract.visual_seam_mm,
                "centered_inset_each_nominal_end_mm": inset,
                "physical_width_authored_directly": True,
                "post_generation_crop_applied": False,
            }
        )
    parts: list[PrototypePart] = []
    installed_names: list[str] = []
    coupon_names: list[str] = []
    for family_id, family in families.items():
        release_family = ORNAMENT_RELEASE_FAMILY_MAP.get(family_id)
        per_level = int(topology["per_level_by_family"].get(family_id, 0))
        if family.installed:
            if release_family is None or per_level <= 0:
                raise AssertionError(f"Installed ornament {family_id} lacks release mapping")
            name = f"R6_DEV_ORNAMENT_{family_id.upper()}"
            installed_names.append(name)
            saved_orientation = (
                "visible ornament datum face on build plate; rear receiver "
                "housings face upward; actual-orientation coupon required"
            )
            catalog_class = "installed_repeat_source"
            selected_repeat = per_level * selected_levels
        else:
            if not family.print_first_coupon or release_family is not None or per_level != 0:
                raise AssertionError(f"Coupon ornament classification drift: {family_id}")
            name = f"R6_DEV_ORNAMENT_{family_id.upper()}"
            coupon_names.append(name)
            saved_orientation = (
                "largest coupon datum face on build plate; preserve authored connector direction"
            )
            catalog_class = "print_first_test_coupon"
            selected_repeat = 0
        metrics = dict(family.design_metrics)
        metrics.update(
            {
                "catalog_class": catalog_class,
                "ornament_geometry_family_id": family_id,
                "release_inventory_family": release_family,
                "installed": bool(family.installed),
                "print_first_coupon": bool(family.print_first_coupon),
                "structural_credit": False,
                "installed_repeat_count_per_level": per_level,
                "installed_repeat_count_selected_levels": selected_repeat,
                "test_coupon_print_count": 1 if family.print_first_coupon else 0,
            }
        )
        parts.append(
            PrototypePart(
                name=name,
                mesh=family.mesh,
                purpose=(
                    "Removable black-PETG classical/Art-Deco facade ornament."
                    if family.installed
                    else "PRINT_FIRST black-PETG gravity-keyhole connector fit coupon."
                ),
                saved_orientation=saved_orientation,
                status=(
                    "REMOVABLE ORNAMENT; ZERO STRUCTURAL CREDIT; FIT QUALIFICATION REQUIRED"
                    if family.installed
                    else "PRINT_FIRST FIT COUPON; NOT INSTALLED; ZERO STRUCTURAL CREDIT"
                ),
                notes=[*family.notes, "No ornament family receives structural credit."],
                design_metrics=metrics,
            )
        )

    if len(installed_names) != 8 or len(coupon_names) != 2:
        raise AssertionError("Ornament source set must remain eight installed plus two coupons")
    if len(instances) != 33 or any(item.structural_credit for item in instances):
        raise AssertionError("Ornament instance set must remain 33 zero-credit pieces per level")
    return parts, {
        "status": "PASS: EIGHT INSTALLED ZERO-CREDIT FAMILIES PLUS TWO PRINT-FIRST COUPONS",
        "unique_installed_mesh_family_count": 8,
        "unique_print_first_coupon_mesh_count": 2,
        "installed_mesh_names": installed_names,
        "print_first_coupon_mesh_names": coupon_names,
        "installed_counts_per_level_by_geometry_family": topology["per_level_by_family"],
        "installed_object_count_per_level": 33,
        "installed_object_count_selected_levels": 33 * selected_levels,
        "test_coupon_object_count": 2,
        "fine_ornament_structural_credit": False,
        "visual_interface_contract": visual_contract.to_dict(),
        "structural_parent_bosses_generated": True,
        "structural_parent_boss_count_per_level": 99,
        "structural_parent_boss_maps_complete": bool(
            visual_contract.connector_placement_complete
        ),
        "software_model_mapping_complete": False,
        "physical_installation_mapping_qualified": False,
        "production_release_eligible": False,
        "structural_parent_boss_blocker": (
            "all parent maps and oculi are embodied; software mapping remains "
            "false until the generator completes strict actual-parent locked, "
            "entry, drop, and travel Boolean sweeps"
        ),
        "instance_logical_ids_per_level": [item.logical_id for item in instances],
    }


def validate_ornament_actual_parent_sweeps(
    cfg: dict[str, Any],
    *,
    ornaments: Iterable[PrototypePart],
    arches: Iterable[PrototypePart],
    corbels: Iterable[PrototypePart],
    cassettes: Iterable[PrototypePart],
) -> dict[str, Any]:
    """Prove every removable facade path against its real structural parent.

    Rigid actual-parent sweeps cover all 33 physical ornament instances.  The
    two elongated connector stations are then checked locally at both +/-0.6
    mm travel extremes; applying that travel to the whole rigid ornament would
    incorrectly move its third fixed datum and is therefore explicitly
    prohibited by this validator.
    """

    access = ornament_access_contract(cfg)
    keyholes = cfg["palatine"]["ornament_keyhole_contract"]
    collision_gate = keyholes["strict_collision_gate"]
    axial_total = float(collision_gate["axial_insertion_sweep_total_mm"])
    axial_step = float(collision_gate["axial_insertion_sweep_step_mm"])
    drop_total = float(collision_gate["gravity_sweep_total_mm"])
    drop_step = float(collision_gate["gravity_sweep_step_mm"])
    allowed_overlap = float(collision_gate["allowed_solid_overlap_mm3"])
    axial_deltas = np.linspace(
        axial_total, 0.0, int(round(axial_total / axial_step)) + 1
    )
    drop_deltas = np.linspace(
        drop_total, 0.0, int(round(drop_total / drop_step)) + 1
    )
    if len(axial_deltas) != 12 or len(drop_deltas) != 16:
        raise ValueError("Ornament service sweep station counts drifted")

    ornament_by_family = {
        str(part.design_metrics["ornament_geometry_family_id"]): part
        for part in ornaments
        if part.design_metrics.get("installed")
    }
    expected_families = {
        "through_carrier_left",
        "through_carrier_right",
        "return_carrier_left",
        "return_carrier_right",
        "pier_overlay",
        "ordinary_endcap",
        "corner_fixed_rosette",
        "corner_floating_return",
    }
    if set(ornament_by_family) != expected_families:
        raise ValueError("Ornament sweep needs all eight installed source families")

    shelf_depth = float(cfg["closet"]["shelf_depth_in"]) * 25.4
    visible_depth_datum = shelf_depth + float(
        ornament_interface_contract(cfg).global_depth_offset_mm
    )

    def locked_to_run_matrix(
        *, origin_s: float, origin_e: float
    ) -> np.ndarray:
        # Ornament source coordinates are (x, y, d); run coordinates are
        # (s, q, e), with d increasing rearward from the decorated face.
        return np.asarray(
            [
                [1.0, 0.0, 0.0, origin_s],
                [0.0, 0.0, -1.0, visible_depth_datum],
                [0.0, 1.0, 0.0, origin_e],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )

    parent_instances: list[
        tuple[str, str, PrototypePart, trimesh.Trimesh, np.ndarray]
    ] = []
    for arch in arches:
        family_id = str(arch.design_metrics["ornament_parent_family_id"])
        coordinate = carrier_coordinate_contract(cfg, family_id)
        ornament = ornament_by_family[family_id]
        for placement in arch.design_metrics["authoritative_instance_placements"]:
            spring_s = float(placement["spring_station_local_s_mm"])
            ornament_matrix = locked_to_run_matrix(
                origin_s=coordinate.installed_origin_s_mm(spring_s),
                origin_e=float(
                    cfg["palatine"]["visual_carrier_contract"]
                    ["visual_spring_extrados_y_mm"]
                ),
            )
            parent = arch.mesh.copy()
            parent.apply_transform(
                np.asarray(
                    placement["arch_saved_to_run_matrix_row_major"], dtype=float
                )
            )
            parent_instances.append(
                (
                    family_id,
                    f"{arch.design_metrics['run_id']} bay "
                    f"{placement['bay_index_1_based']} "
                    f"{arch.design_metrics['handedness']} carrier",
                    ornament,
                    parent,
                    ornament_matrix,
                )
            )

    pier_ornament = ornament_by_family["pier_overlay"]
    pier_half_width = float(pier_ornament.mesh.extents[0]) / 2.0
    for corbel in corbels:
        for placement in corbel.design_metrics["authoritative_instance_placements"]:
            support_s = float(placement["support_station_local_s_mm"])
            parent = corbel.mesh.copy()
            parent.apply_transform(
                np.asarray(placement["saved_to_run_matrix_row_major"], dtype=float)
            )
            parent_instances.append(
                (
                    "pier_overlay",
                    f"{placement['run_id']} support {support_s:.6f} pier overlay",
                    pier_ornament,
                    parent,
                    locked_to_run_matrix(
                        origin_s=support_s - pier_half_width,
                        origin_e=0.0,
                    ),
                )
            )

    for cassette in cassettes:
        family_id = cassette.design_metrics.get("ornament_parent_family_id")
        if family_id is None:
            continue
        family_id = str(family_id)
        panel = cassette.design_metrics["integral_ornament_backing_panel"]
        parent = cassette.mesh.copy()
        parent.apply_transform(
            np.asarray(
                cassette.design_metrics["saved_print_transform"]
                ["saved_to_run_matrix_row_major"],
                dtype=float,
            )
        )
        parent_instances.append(
            (
                family_id,
                str(cassette.design_metrics["logical_instance_id"]),
                ornament_by_family[family_id],
                parent,
                locked_to_run_matrix(
                    origin_s=float(
                        panel.get(
                            "locked_piece_origin_run_s_mm",
                            panel["panel_run_global_s_envelope_mm"][0],
                        )
                    ),
                    origin_e=float(panel["panel_e_envelope_mm"][0]),
                ),
            )
        )

    if len(parent_instances) != 33:
        raise ValueError(
            f"Actual-parent ornament proof needs 33 instances, got {len(parent_instances)}"
        )
    actual_family_counts: dict[str, int] = {}
    actual_parent_pair_count = 0
    maximum_actual_parent_overlap = 0.0
    for family_id, label, ornament, parent, locked_matrix in parent_instances:
        actual_family_counts[family_id] = actual_family_counts.get(family_id, 0) + 1
        for delta_q in axial_deltas:
            moving = ornament.mesh.copy()
            moving.apply_transform(locked_matrix)
            moving.apply_translation([0.0, float(delta_q), drop_total])
            overlap = positive_solid_intersection_volume_mm3(parent, moving)
            maximum_actual_parent_overlap = max(
                maximum_actual_parent_overlap, overlap
            )
            if overlap > allowed_overlap:
                raise ValueError(
                    f"{label}: axial ornament insertion delta {delta_q:.1f} "
                    f"overlaps its real parent by {overlap:.9f} mm3"
                )
            actual_parent_pair_count += 1
        for delta_e in drop_deltas:
            moving = ornament.mesh.copy()
            moving.apply_transform(locked_matrix)
            moving.apply_translation([0.0, 0.0, float(delta_e)])
            overlap = positive_solid_intersection_volume_mm3(parent, moving)
            maximum_actual_parent_overlap = max(
                maximum_actual_parent_overlap, overlap
            )
            if overlap > allowed_overlap:
                raise ValueError(
                    f"{label}: ornament gravity delta {delta_e:.1f} overlaps "
                    f"its real parent by {overlap:.9f} mm3"
                )
            actual_parent_pair_count += 1

    expected_family_counts = {
        family_id: int(part.design_metrics["installed_repeat_count_per_level"])
        for family_id, part in ornament_by_family.items()
    }
    if actual_family_counts != expected_family_counts:
        raise ValueError("Actual-parent ornament instance topology drifted")

    # Shared source-family connector sweeps.  The parent-center to receiver-
    # housing-center offset is exactly half the 6 mm gravity motion.
    elongated_indices = {
        int(value) for value in keyholes["elongated_run_axis_connector_indices"]
    }
    local_connector_pair_count = 0
    maximum_local_connector_overlap = 0.0
    connector_type_counts: dict[str, int] = {}
    for family_id, ornament in sorted(ornament_by_family.items()):
        centers = ornament.design_metrics["receiver_centers_local_x_y_mm"]
        types = connector_types_for_family(cfg, family_id)
        for connector_index, (center, connector_type) in enumerate(
            zip(centers, types), start=1
        ):
            center_x = float(center[0])
            locked_center_y = float(center[1]) + drop_total / 2.0
            if connector_type == "gravity_keyhole":
                boss = gravity_keyhole_boss_mesh(center_x, locked_center_y)
            elif connector_type == "compact_gravity_keyhole":
                boss = compact_pier_gravity_keyhole_boss_mesh(
                    cfg, center_x, locked_center_y
                )
            elif connector_type == "noncapturing_loose_locator":
                boss = noncapturing_loose_locator_post_mesh(
                    cfg, center_x, locked_center_y
                )
            else:
                raise ValueError(
                    f"{family_id}: unsupported connector {connector_type!r}"
                )
            connector_type_counts[connector_type] = (
                connector_type_counts.get(connector_type, 0) + 1
            )
            for delta_q in axial_deltas:
                moving = boss.copy()
                moving.apply_translation([0.0, -drop_total, float(delta_q)])
                overlap = positive_solid_intersection_volume_mm3(
                    ornament.mesh, moving
                )
                maximum_local_connector_overlap = max(
                    maximum_local_connector_overlap, overlap
                )
                if overlap > allowed_overlap:
                    raise ValueError(
                        f"{family_id} connector {connector_index}: axial proxy "
                        f"overlap {overlap:.9f} mm3"
                    )
                local_connector_pair_count += 1
            run_extremes = (
                access.run_extremes_mm
                if connector_index in elongated_indices
                else (0.0,)
            )
            for delta_s in run_extremes:
                for delta_e in drop_deltas:
                    moving = boss.copy()
                    moving.apply_translation(
                        [float(delta_s), -float(delta_e), 0.0]
                    )
                    overlap = positive_solid_intersection_volume_mm3(
                        ornament.mesh, moving
                    )
                    maximum_local_connector_overlap = max(
                        maximum_local_connector_overlap, overlap
                    )
                    if overlap > allowed_overlap:
                        raise ValueError(
                            f"{family_id} connector {connector_index}: drop "
                            f"{delta_e:.1f}/run {delta_s:+.1f} proxy overlap "
                            f"{overlap:.9f} mm3"
                        )
                    local_connector_pair_count += 1

    # The full-depth oculus cutter must still be a real void after every
    # female family has been decorated and Boolean-cleaned.
    unique_oculus_void_count = 0
    repeated_oculus_count = 0
    maximum_oculus_residual = 0.0
    for family_id, ornament in sorted(ornament_by_family.items()):
        oculi = swept_oculi_for_family(cfg, family_id)
        repeated_oculus_count += len(oculi) * int(
            ornament.design_metrics["installed_repeat_count_per_level"]
        )
        for oculus in oculi:
            d0, d1 = oculus.depth_zone_mm
            void_probe = extrude_polygon(oculus.profile(), d1 - d0, z0=d0)
            residual = positive_solid_intersection_volume_mm3(
                ornament.mesh, void_probe
            )
            maximum_oculus_residual = max(maximum_oculus_residual, residual)
            if residual > allowed_overlap:
                raise ValueError(
                    f"{oculus.access_id}: full-depth service oculus retains "
                    f"{residual:.9f} mm3 of ornament solid"
                )
            unique_oculus_void_count += 1
    if repeated_oculus_count != access.decorative_oculi_per_level:
        raise ValueError("Repeated ornament oculus count does not equal 58")

    expected_feature_counts = {
        "gravity_keyhole": 21,
        "compact_gravity_keyhole": 2,
        "noncapturing_loose_locator": 1,
    }
    if connector_type_counts != expected_feature_counts:
        raise ValueError("Unique ornament connector source topology drifted")
    return {
        "status": "PASS: ALL REMOVABLE ORNAMENT SOFTWARE INTERFACES AND SERVICE SWEEPS CLOSED",
        "installed_ornament_instance_count_per_level": len(parent_instances),
        "installed_instance_counts_by_family": actual_family_counts,
        "axial_insertion_station_count": len(axial_deltas),
        "gravity_drop_station_count": len(drop_deltas),
        "actual_parent_boolean_pair_count": actual_parent_pair_count,
        "maximum_actual_parent_overlap_volume_mm3": round(
            maximum_actual_parent_overlap, 9
        ),
        "unique_source_connector_type_counts": connector_type_counts,
        "local_connector_sweep_boolean_pair_count": local_connector_pair_count,
        "maximum_local_connector_overlap_volume_mm3": round(
            maximum_local_connector_overlap, 9
        ),
        "unique_full_depth_oculus_void_count": unique_oculus_void_count,
        "repeated_full_depth_oculus_count_per_level": repeated_oculus_count,
        "maximum_full_depth_oculus_residual_solid_volume_mm3": round(
            maximum_oculus_residual, 9
        ),
        "minimum_locked_cross_key_handle_radial_clearance_mm": (
            access.minimum_locked_handle_radial_clearance_mm
        ),
        "rigid_whole_ornament_run_shift_prohibited": True,
        "elongated_connector_run_extremes_proven_mm": list(
            access.run_extremes_mm
        ),
        "software_model_package_eligible": True,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
        "actual_parent_orientation_coupon_mappings_complete": True,
        "actual_parent_orientation_coupons_physically_passed": False,
    }


def validate_inside_corner_ornament_cross_arm_clearance(
    cfg: dict[str, Any],
    *,
    plan: Any,
    ornaments: Iterable[PrototypePart],
    arches: Iterable[PrototypePart],
    corbels: Iterable[PrototypePart],
    cassettes: Iterable[PrototypePart],
) -> dict[str, Any]:
    """Prove both corner facades and their service paths in global L space."""

    ornament_by_family = {
        str(part.design_metrics["ornament_geometry_family_id"]): part
        for part in ornaments
        if part.design_metrics.get("installed")
    }
    required_corner_families = {
        "corner_fixed_rosette",
        "corner_floating_return",
    }
    if not required_corner_families <= set(ornament_by_family):
        raise ValueError("Cross-arm corner proof needs both removable corner facades")
    cassette_by_key = {
        (
            str(part.design_metrics["run_id"]),
            int(part.design_metrics["position_index_1_based"]),
        ): part
        for part in cassettes
    }
    through = plan.through
    return_run = plan.return_run
    through_cassette = cassette_by_key[(str(through.run_id), 1)]
    return_cassette = cassette_by_key[(str(return_run.run_id), 1)]
    back_clearance = float(plan.through_back_clearance_mm)
    through_run_to_l = np.asarray(
        [
            [1.0, 0.0, 0.0, float(through.start_from_corner_mm)],
            [0.0, 1.0, 0.0, back_clearance],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    return_run_to_l = np.asarray(
        [
            [0.0, 1.0, 0.0, back_clearance],
            [1.0, 0.0, 0.0, float(return_run.start_from_corner_mm)],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )

    def transformed(mesh: trimesh.Trimesh, matrix: np.ndarray) -> trimesh.Trimesh:
        result = mesh.copy()
        result.apply_transform(matrix)
        return result

    def installed_cassette(
        part: PrototypePart, run_to_l: np.ndarray
    ) -> trimesh.Trimesh:
        return transformed(
            part.mesh,
            run_to_l
            @ np.asarray(
                part.design_metrics["saved_print_transform"][
                    "saved_to_run_matrix_row_major"
                ],
                dtype=float,
            ),
        )

    run_start_corbel = next(
        part for part in corbels if part.design_metrics.get("variant") == "run_start"
    )
    corbel_placements = {
        str(record["run_id"]): record
        for record in run_start_corbel.design_metrics[
            "authoritative_instance_placements"
        ]
    }

    def installed_corbel(run_id: str, run_to_l: np.ndarray) -> trimesh.Trimesh:
        return transformed(
            run_start_corbel.mesh,
            run_to_l
            @ np.asarray(
                corbel_placements[run_id]["saved_to_run_matrix_row_major"],
                dtype=float,
            ),
        )

    def first_bay_arches(run_id: str, run_to_l: np.ndarray) -> list[trimesh.Trimesh]:
        installed: list[trimesh.Trimesh] = []
        for arch in arches:
            if str(arch.design_metrics.get("run_id")) != run_id:
                continue
            placement = next(
                record
                for record in arch.design_metrics["authoritative_instance_placements"]
                if int(record["bay_index_1_based"]) == 1
            )
            installed.append(
                transformed(
                    arch.mesh,
                    run_to_l
                    @ np.asarray(
                        placement["arch_saved_to_run_matrix_row_major"],
                        dtype=float,
                    ),
                )
            )
        if len(installed) != 2:
            raise ValueError(f"{run_id}: corner proof requires two first-bay arch halves")
        return installed

    shelf_depth = float(cfg["closet"]["shelf_depth_in"]) * 25.4
    visible_depth_datum = shelf_depth + float(
        ornament_interface_contract(cfg).global_depth_offset_mm
    )

    def locked_ornament(
        cassette: PrototypePart,
        family_id: str,
        run_to_l: np.ndarray,
    ) -> tuple[trimesh.Trimesh, np.ndarray]:
        panel = cassette.design_metrics["integral_ornament_backing_panel"]
        local = np.asarray(
            [
                [
                    1.0,
                    0.0,
                    0.0,
                    float(
                        panel.get(
                            "locked_piece_origin_run_s_mm",
                            panel["panel_run_global_s_envelope_mm"][0],
                        )
                    ),
                ],
                [0.0, 0.0, -1.0, visible_depth_datum],
                [0.0, 1.0, 0.0, float(panel["panel_e_envelope_mm"][0])],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=float,
        )
        matrix = run_to_l @ local
        return transformed(ornament_by_family[family_id].mesh, matrix), matrix

    through_structures = [
        installed_cassette(through_cassette, through_run_to_l),
        installed_corbel(str(through.run_id), through_run_to_l),
        *first_bay_arches(str(through.run_id), through_run_to_l),
    ]
    return_structures = [
        installed_cassette(return_cassette, return_run_to_l),
        installed_corbel(str(return_run.run_id), return_run_to_l),
        *first_bay_arches(str(return_run.run_id), return_run_to_l),
    ]
    through_ornament, through_ornament_matrix = locked_ornament(
        through_cassette,
        "corner_fixed_rosette",
        through_run_to_l,
    )
    return_ornament, return_ornament_matrix = locked_ornament(
        return_cassette,
        "corner_floating_return",
        return_run_to_l,
    )
    allowed_overlap = float(
        cfg["palatine"]["ornament_keyhole_contract"]["strict_collision_gate"][
            "allowed_solid_overlap_mm3"
        ]
    )

    maximum_final_overlap = 0.0
    final_pair_count = 0
    for moving, fixed_set, label in (
        (through_ornament, return_structures, "through rosette / return structure"),
        (return_ornament, through_structures, "return finish / through structure"),
    ):
        for fixed in fixed_set:
            overlap = positive_solid_intersection_volume_mm3(moving, fixed)
            maximum_final_overlap = max(maximum_final_overlap, overlap)
            if overlap > allowed_overlap:
                raise ValueError(
                    f"Inside-corner final {label} overlap is {overlap:.9f} mm3"
                )
            final_pair_count += 1
    ornament_pair_overlap = positive_solid_intersection_volume_mm3(
        through_ornament, return_ornament
    )
    maximum_final_overlap = max(maximum_final_overlap, ornament_pair_overlap)
    if ornament_pair_overlap > allowed_overlap:
        raise ValueError(
            "Inside-corner locked removable facades overlap by "
            f"{ornament_pair_overlap:.9f} mm3"
        )
    final_pair_count += 1

    access = ornament_access_contract(cfg)
    collision_gate = cfg["palatine"]["ornament_keyhole_contract"][
        "strict_collision_gate"
    ]
    axial_total = float(collision_gate["axial_insertion_sweep_total_mm"])
    axial_step = float(collision_gate["axial_insertion_sweep_step_mm"])
    axial_deltas = np.arange(
        0.0,
        axial_total + axial_step / 2.0,
        axial_step,
    )
    drop_deltas = np.arange(
        0.0,
        float(access.removal_drop_mm) + float(access.sweep_step_mm) / 2.0,
        float(access.sweep_step_mm),
    )
    through_q_axis = np.asarray(through_run_to_l[:3, 1], dtype=float)
    return_q_axis = np.asarray(return_run_to_l[:3, 1], dtype=float)
    maximum_service_overlap = 0.0
    service_pair_count = 0

    def prove_service(
        source: trimesh.Trimesh,
        q_axis: np.ndarray,
        fixed_set: list[trimesh.Trimesh],
        label: str,
    ) -> None:
        nonlocal maximum_service_overlap, service_pair_count
        for delta_q in axial_deltas:
            moving = source.copy()
            moving.apply_translation(
                q_axis * float(delta_q) + np.asarray([0.0, 0.0, drop_deltas[-1]])
            )
            for fixed in fixed_set:
                overlap = positive_solid_intersection_volume_mm3(moving, fixed)
                maximum_service_overlap = max(maximum_service_overlap, overlap)
                if overlap > allowed_overlap:
                    raise ValueError(
                        f"Inside-corner {label} axial service {delta_q:.1f} mm "
                        f"overlap is {overlap:.9f} mm3"
                    )
                service_pair_count += 1
        for delta_e in drop_deltas:
            moving = source.copy()
            moving.apply_translation([0.0, 0.0, float(delta_e)])
            for fixed in fixed_set:
                overlap = positive_solid_intersection_volume_mm3(moving, fixed)
                maximum_service_overlap = max(maximum_service_overlap, overlap)
                if overlap > allowed_overlap:
                    raise ValueError(
                        f"Inside-corner {label} gravity service {delta_e:.1f} mm "
                        f"overlap is {overlap:.9f} mm3"
                    )
                service_pair_count += 1

    # The return cosmetic overhang is removed before moving the through
    # rosette.  The return cosmetic piece itself must clear the installed
    # through arm and the fixed through rosette during its exact inverse path.
    prove_service(
        through_ornament,
        through_q_axis,
        return_structures,
        "through rosette / return structure",
    )
    prove_service(
        return_ornament,
        return_q_axis,
        [*through_structures, through_ornament],
        "return cosmetic / through structure and fixed rosette",
    )
    return {
        "status": "PASS: REMOVABLE CORNER FACADES CLEAR BOTH L ARMS AND SERVICE SWEEPS",
        "coordinate_axes": "global L plan X=through wall, Y=return wall, e=up",
        "through_corner_ornament_locked_matrix_row_major": (
            through_ornament_matrix.tolist()
        ),
        "return_corner_ornament_locked_matrix_row_major": (
            return_ornament_matrix.tolist()
        ),
        "through_corner_ornament_locked_bounds_mm": np.round(
            through_ornament.bounds, 7
        ).tolist(),
        "return_corner_ornament_locked_bounds_mm": np.round(
            return_ornament.bounds, 7
        ).tolist(),
        "through_corner_cassette_locked_bounds_mm": np.round(
            through_structures[0].bounds, 7
        ).tolist(),
        "return_corner_cassette_locked_bounds_mm": np.round(
            return_structures[0].bounds, 7
        ).tolist(),
        "final_cross_arm_boolean_pair_count": final_pair_count,
        "maximum_final_cross_arm_overlap_volume_mm3": round(
            maximum_final_overlap, 9
        ),
        "axial_service_deltas_mm": axial_deltas.tolist(),
        "gravity_service_deltas_mm": drop_deltas.tolist(),
        "service_sweep_boolean_pair_count": service_pair_count,
        "maximum_service_sweep_overlap_volume_mm3": round(
            maximum_service_overlap, 9
        ),
        "return_cosmetic_overhang_removed_before_through_rosette_service": True,
        "software_model_package_eligible": True,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
    }


def integrated_release_reconciliation(
    cfg: dict[str, Any],
    *,
    plan: Any,
    selected_levels: int,
    rail_report: dict[str, Any],
    ornament_report: dict[str, Any],
) -> dict[str, Any]:
    """Cross-check emitted rail/ornament coverage against physical inventory."""

    if selected_levels != 2:
        raise ValueError("The approved r6 integrated release comparison requires two levels")
    one_level = enumerate_level_inventory(cfg, "lower", plan)
    selected = enumerate_selected_inventory(cfg, plan)
    one_reconciliation = inventory_reconciliation(cfg, one_level)
    selected_reconciliation = inventory_reconciliation(cfg, selected)
    if one_reconciliation["contradictions"] or selected_reconciliation["contradictions"]:
        raise AssertionError("The generated source set cannot reconcile to a contradictory inventory")

    rail_contract = rail_baseline_contract(cfg)
    if rail_report.get("installed_in_release_candidate") is not False:
        raise AssertionError("Installed release reconciliation may not include stitch rails")
    if any(rail_report["installed_counts_per_level"].values()):
        raise AssertionError("Rail-free baseline report contains installed rail objects")
    expected_per_level = {
        "through_left_ornament_carrier": 6,
        "through_right_ornament_carrier": 6,
        "return_left_ornament_carrier": 3,
        "return_right_ornament_carrier": 3,
        "ornamental_pier_overlay": 11,
        "ordinary_outer_end_cap": 2,
        "corner_fixed_rosette": 1,
        "corner_floating_mate": 1,
    }
    one_counts = count_by(one_level, "family")
    actual_per_level = {key: one_counts.get(key, 0) for key in expected_per_level}
    if actual_per_level != expected_per_level:
        raise AssertionError(
            f"Integrated rail/ornament inventory mismatch: {actual_per_level!r}"
        )
    expected_selected = {key: value * selected_levels for key, value in expected_per_level.items()}
    selected_counts = count_by(selected, "family")
    actual_selected = {key: selected_counts.get(key, 0) for key in expected_selected}
    if actual_selected != expected_selected:
        raise AssertionError(
            f"Integrated two-level rail/ornament inventory mismatch: {actual_selected!r}"
        )
    installed_per_level = sum(expected_per_level.values())
    installed_selected = sum(expected_selected.values())
    if installed_per_level != 33 or installed_selected != 66:
        raise AssertionError("Integrated repeat count drift")
    if ornament_report["installed_object_count_per_level"] != 33:
        raise AssertionError("Ornament reconciliation drift")
    return {
        "status": "PASS: RAIL-FREE BASELINE AND EMITTED ORNAMENT FAMILIES MATCH RELEASE INVENTORY",
        "authoritative_inventory_physical_objects_per_level": one_reconciliation[
            "physical_object_count"
        ],
        "authoritative_inventory_physical_objects_selected_levels": selected_reconciliation[
            "physical_object_count"
        ],
        "authoritative_inventory_contradictions": {
            "one_level": one_reconciliation["contradictions"],
            "selected_levels": selected_reconciliation["contradictions"],
        },
        "integrated_family_counts_per_level": expected_per_level,
        "integrated_family_counts_selected_levels": expected_selected,
        "integrated_installed_object_count_per_level": installed_per_level,
        "integrated_installed_object_count_selected_levels": installed_selected,
        "integrated_unique_installed_mesh_count": 8,
        "integrated_unique_test_coupon_mesh_count": 2,
        "installed_stitch_rail_object_count_per_level": 0,
        "installed_stitch_rail_object_count_selected_levels": 0,
        "rail_baseline_contract": rail_contract,
        "canonical_software_model_package_inventory_reconciled": True,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
        "scope_note": (
            "This report reconciles the complete rail-free software-model inventory. "
            f"The {one_reconciliation['physical_object_count']}-object one-level and "
            f"{selected_reconciliation['physical_object_count']}-object selected-level "
            "inventories remain authoritative; package conformance creates no physical "
            "installation, production, or load-rating claim."
        ),
    }


def _print_first_prototype_specs(
    parts_by_name: dict[str, PrototypePart],
    cassette_variant_sources: dict[str, PrototypePart],
) -> tuple[PrototypeSpec, ...]:
    """Return the exact eight-object pre-assembly package source contract."""

    source_roles = (
        ("R6_DEV_JOINERY_CLEARANCE_LADDER_RECEIVER", ("fit_clearance",)),
        ("R6_DEV_JOINERY_CLEARANCE_LADDER_TONGUE", ("fit_clearance",)),
        (
            "R6_DEV_BLOCKED_WALL_SCREW_BEARING_COUPON_SOLID_NO_HOLE",
            ("screw_head_bearing", "wall_screw_no_bore_blocker"),
        ),
        (
            cassette_variant_sources["through_start_outer"].name,
            ("coffer_bridge_fit", "structural_cassette"),
        ),
        ("R6_DEV_ORNAMENT_PRINT_FIRST_KEYHOLE_MALE_LADDER", ("ornament_connector",)),
        ("R6_DEV_ORNAMENT_PRINT_FIRST_KEYHOLE_FEMALE_LADDER", ("ornament_connector",)),
        (
            "R6_DEV_FINAL_X_TOP_CAPTURE_WEDGE_UNIVERSAL",
            ("positive_cross_key_fit",),
        ),
        (
            "R6_DEV_CROWN_BRIDGE_ANTI_DROP_PIN_RETENTION_ONLY",
            ("pin_fit",),
        ),
    )
    missing = [name for name, _roles in source_roles if name not in parts_by_name]
    if missing:
        raise ValueError(f"Print-first package sources are missing: {missing}")
    return tuple(
        PrototypeSpec(
            logical_name=f"print_first::{index:02d}::{name}",
            mesh_family=f"prototype::{name}",
            roles=tuple(roles),
        )
        for index, (name, roles) in enumerate(source_roles, start=1)
    )


def package_solid_model_mass_report(
    plans: Iterable[Any],
    mesh_by_family: dict[str, trimesh.Trimesh],
    *,
    density_g_cm3: float,
) -> dict[str, Any]:
    """Aggregate repeat-weighted CAD-solid volume and contextual PETG mass.

    This is deliberately not a slicer estimate: it treats every watertight
    model as solid PETG and multiplies by the exact package instance count.
    Infill, walls, purge, supports, print failures, and finished-part tare can
    only be established by the later Bambu/physical qualification gates.
    """

    density = positive(float(density_g_cm3), "PETG density")
    plan_reports: dict[str, dict[str, Any]] = {}
    raw_volume_by_package: dict[str, float] = {}
    for package_plan in plans:
        missing = sorted(
            {
                item.mesh_family
                for item in package_plan.instances
                if item.mesh_family not in mesh_by_family
            }
        )
        if missing:
            raise ValueError(
                f"{package_plan.package_id}: solid-model mass sources missing {missing}"
            )
        total_volume = sum(
            abs(float(mesh_by_family[item.mesh_family].volume))
            for item in package_plan.instances
        )
        package_id = str(package_plan.package_id)
        raw_volume_by_package[package_id] = total_volume
        plan_reports[package_id] = {
            "filename": str(package_plan.filename),
            "physical_object_count": int(package_plan.physical_object_count),
            "repeat_weighted_model_solid_volume_mm3": round(total_volume, 3),
            "contextual_all_solid_petg_mass_g": round(
                total_volume * density / 1000.0, 3
            ),
            "estimate_class": "CAD MODEL-SOLID CONTEXT ONLY",
            "sliced_or_finished_mass_claim": False,
            "load_capacity_claim": False,
        }
    for required in ("one_level_l", "two_level_full_project"):
        if required not in plan_reports:
            raise ValueError(f"Canonical solid-model mass report lacks {required}")
    one_raw = raw_volume_by_package["one_level_l"]
    two_raw = raw_volume_by_package["two_level_full_project"]
    if not math.isclose(two_raw, 2.0 * one_raw, rel_tol=1.0e-12, abs_tol=1.0e-5):
        raise ValueError(
            "Two-level CAD-solid volume is not exactly two independent one-level inventories"
        )
    # Reported values are rounded to three decimals. Derive the displayed
    # two-level context from the already rounded one-level context so ordinary
    # decimal rounding cannot make two identical inventories appear unequal
    # by 0.001 g/mm3.
    one_estimate = plan_reports["one_level_l"]
    two_estimate = plan_reports["two_level_full_project"]
    two_estimate["repeat_weighted_model_solid_volume_mm3"] = round(
        2.0 * float(one_estimate["repeat_weighted_model_solid_volume_mm3"]), 3
    )
    two_estimate["contextual_all_solid_petg_mass_g"] = round(
        2.0 * float(one_estimate["contextual_all_solid_petg_mass_g"]), 3
    )
    return {
        "status": "PASS: REPEAT-WEIGHTED CAD-SOLID CONTEXT REPORTED FOR EVERY CANONICAL PACKAGE",
        "petg_density_g_cm3": density,
        "mass_formula": "sum(mesh_volume_mm3 * instance_count) * density_g_cm3 / 1000",
        "two_level_display_rounding_rule": (
            "exactly twice the rounded one-level CAD-solid context because the "
            "selected project contains two identical independent inventories"
        ),
        "package_estimates": plan_reports,
        "one_level_contextual_all_solid_petg_mass_g": plan_reports["one_level_l"][
            "contextual_all_solid_petg_mass_g"
        ],
        "two_level_contextual_all_solid_petg_mass_g": plan_reports[
            "two_level_full_project"
        ]["contextual_all_solid_petg_mass_g"],
        "bambu_sliced_mass_required_before_print": True,
        "weighed_finished_tare_required_for_physical_qualification": True,
        "tested_load_rating_created": False,
    }


def build_release_package_context(
    cfg: dict[str, Any],
    *,
    plan: Any,
    parts: list[PrototypePart],
) -> tuple[tuple[Any, ...], dict[str, trimesh.Trimesh], dict[str, PackageMeshSourceAudit], dict[str, Any]]:
    """Resolve five software-model package plans with physical claims false."""

    parts_by_name = {part.name: part for part in parts}
    if len(parts_by_name) != len(parts):
        raise ValueError("Package source adapter requires unique prototype names")
    # Canonical packages, emitted STL files, and individual model-only 3MFs
    # share one geometry source of truth: the audited STL-ready representation.
    # Some otherwise valid Boolean meshes contain microscopic helper facets
    # that disappear during float32 STL serialization.  Feeding the original
    # in-memory mesh into a package would therefore make a named package source
    # differ from the correspondingly named emitted STL/individual 3MF pair.
    serialized_source_meshes = {
        name: serialization_ready_mesh(
            part.mesh,
            target="stl",
            source_name=name,
        )
        for name, part in sorted(parts_by_name.items())
    }

    cassette_groups: dict[str, list[PrototypePart]] = {}
    cassette_position_sources: dict[tuple[str, int], PrototypePart] = {}
    for part in parts:
        if part.design_metrics.get("family") == "position_specific_two_skin_half_bay_cassette_chassis":
            variant = str(part.design_metrics["variant_id"])
            cassette_groups.setdefault(variant, []).append(part)
            position_key = (
                str(part.design_metrics["run_id"]),
                int(part.design_metrics["position_index_1_based"]),
            )
            if position_key in cassette_position_sources:
                raise ValueError(
                    f"Duplicate position-specific cassette package source {position_key!r}"
                )
            cassette_position_sources[position_key] = part
    expected_cassette_variants = {
        "through_start_outer",
        "through_internal_crown_to_pier",
        "through_internal_pier_to_crown",
        "through_end_outer",
        "return_start_outer",
        "return_internal_crown_to_pier",
        "return_internal_pier_to_crown",
        "return_end_outer",
    }
    if set(cassette_groups) != expected_cassette_variants:
        raise ValueError("Package adapter does not have the exact eight cassette variants")
    if len(cassette_position_sources) != 18:
        raise ValueError(
            "Package adapter requires all 18 exact position-specific cassette sources"
        )
    # Variant representatives are used only by the eight-object print-first fit
    # package. Installed software-model packages resolve every cassette by its
    # exact run/index source; geometrically distinct positions may never alias.
    cassette_variant_sources = {
        variant: sorted(group, key=lambda item: item.name)[0]
        for variant, group in sorted(cassette_groups.items())
    }

    fixed_source_names: dict[str, str] = {
        "cassette_lock": "R6_FINAL_X_INTEGRATED_CAP_CASSETTE_LOCK_SPLIT_TAIL",
        "crown_bridge": "R6_DEV_REAR_CROWN_BRIDGE_UPWARD_INSERTION_LADDER",
        "crown_bridge_retention_pin": "R6_DEV_CROWN_BRIDGE_ANTI_DROP_PIN_RETENTION_ONLY",
        "diaphragm_bowtie_key": "R6_DEV_DIAPHRAGM_BOWTIE_KEY",
        "fixed_crown_entablature_tie_key": (
            "R6_DEV_FIXED_CROWN_FRONT_INSERTED_ENTABLATURE_TIE_WITH_Q_AXIS_PIN_EYE"
        ),
        "ornamental_pier_overlay": "R6_DEV_ORNAMENT_PIER_OVERLAY",
        "ordinary_outer_end_cap": "R6_DEV_ORNAMENT_ORDINARY_ENDCAP",
        "corner_fixed_rosette": "R6_DEV_ORNAMENT_CORNER_FIXED_ROSETTE",
        "corner_floating_mate": "R6_DEV_ORNAMENT_CORNER_FLOATING_RETURN",
        "through_left_ornament_carrier": "R6_DEV_ORNAMENT_THROUGH_CARRIER_LEFT",
        "through_right_ornament_carrier": "R6_DEV_ORNAMENT_THROUGH_CARRIER_RIGHT",
        "return_left_ornament_carrier": "R6_DEV_ORNAMENT_RETURN_CARRIER_LEFT",
        "return_right_ornament_carrier": "R6_DEV_ORNAMENT_RETURN_CARRIER_RIGHT",
    }
    arcade_sources = {
        "through_left_half": "R6_DEV_FINAL_X_GRAND_ARCH_HALF_THROUGH_LONG_LEFT",
        "through_right_half": "R6_DEV_FINAL_X_GRAND_ARCH_HALF_THROUGH_LONG_RIGHT",
        "return_left_half": "R6_DEV_FINAL_X_GRAND_ARCH_HALF_RETURN_SHORT_LEFT",
        "return_right_half": "R6_DEV_FINAL_X_GRAND_ARCH_HALF_RETURN_SHORT_RIGHT",
    }
    corbel_sources = {
        "start": "R6_DEV_FINAL_X_X_CORBEL_PIER_RUN_START_TERMINAL_INTEGRATED_CAP",
        "interior": "R6_DEV_FINAL_X_X_CORBEL_PIER_INTERIOR_DUAL_SOCKET_INTEGRATED_CAP",
        "end": "R6_DEV_FINAL_X_X_CORBEL_PIER_RUN_END_TERMINAL_INTEGRATED_CAP",
    }

    def source_name_for_record(record: Any) -> str | None:
        family = str(record.family)
        variant = str(record.variant)
        if family == "deck_cassette":
            try:
                position_index = int(str(record.logical_id).rsplit("::", 1)[1])
            except (IndexError, ValueError) as exc:
                raise ValueError(
                    f"{record.logical_id}: cannot derive cassette position index"
                ) from exc
            key = (str(record.run), position_index)
            source = cassette_position_sources.get(key)
            if source is None:
                raise ValueError(
                    f"{record.logical_id}: exact position-specific cassette source is missing"
                )
            if str(source.design_metrics["variant_id"]) != variant:
                raise ValueError(
                    f"{record.logical_id}: cassette source variant mismatch "
                    f"{source.design_metrics['variant_id']!r} != {variant!r}"
                )
            return source.name
        if family == "arcade_half":
            return arcade_sources[variant]
        if family == "structural_pier_x_corbel":
            role = next(
                (candidate for candidate in ("start", "interior", "end") if variant.endswith(candidate)),
                None,
            )
            return corbel_sources[role] if role is not None else None
        if family == "cassette_top_retention_wedge":
            return "R6_DEV_FINAL_X_TOP_CAPTURE_WEDGE_UNIVERSAL"
        if family == "spring_retention_wedge":
            return "R6_DEV_FINAL_X_SPRING_RETENTION_WEDGE_UNIVERSAL"
        if family == "indexed_vertical_quarter_turn_pin":
            return {
                "keeper_reach": (
                    "R6_DEV_INDEXED_VERTICAL_QUARTER_TURN_PIN_KEEPER_REACH"
                ),
                "front_tie_reach": (
                    "R6_DEV_INDEXED_VERTICAL_QUARTER_TURN_PIN_FRONT_TIE_REACH"
                ),
            }.get(variant)
        if family == "fixed_crown_diaphragm_keeper_strip":
            return "R6_DEV_FIXED_CROWN_DIAPHRAGM_KEEPER_STRIP_REAR_BAYONET"
        return fixed_source_names.get(family)

    def mesh_family_resolver(record: Any) -> str:
        source_name = source_name_for_record(record)
        if source_name is None:
            return f"unresolved::{record.family}::{record.variant}"
        if source_name not in parts_by_name:
            raise ValueError(
                f"{record.logical_id}: resolved source {source_name!r} is not emitted"
            )
        return f"source::{source_name}"

    prototypes = _print_first_prototype_specs(parts_by_name, cassette_variant_sources)
    one_level_records = enumerate_level_inventory(cfg, "lower", plan)
    selected_records = enumerate_selected_inventory(cfg, plan)
    catalog_mesh_families = tuple(
        f"source::{name}" for name in sorted(parts_by_name)
    )
    if len(catalog_mesh_families) != EXPECTED_EMITTED_SOURCE_PART_COUNT:
        raise ValueError(
            "The emitted source set does not match the 49-part catalog contract"
        )
    plans = build_release_package_plans(
        prototypes=prototypes,
        catalog_mesh_families=catalog_mesh_families,
        one_level_records=one_level_records,
        selected_records=selected_records,
        mesh_family_resolver=mesh_family_resolver,
    )

    mesh_by_family: dict[str, trimesh.Trimesh] = {
        spec.mesh_family: serialized_source_meshes[
            spec.logical_name.split("::", 2)[2]
        ]
        for spec in prototypes
    }
    mesh_by_family.update(
        {
            f"source::{name}": serialized_source_meshes[name]
            for name in sorted(parts_by_name)
        }
    )
    resolved_records = (*one_level_records, *selected_records)
    for record in resolved_records:
        source_name = source_name_for_record(record)
        if source_name is not None:
            mesh_by_family[f"source::{source_name}"] = serialized_source_meshes[
                source_name
            ]

    blocker_ids_by_family: dict[str, tuple[str, ...]] = {}
    source_family_owners: dict[str, set[str]] = {}
    for record in one_level_records:
        source_name = source_name_for_record(record)
        if source_name is not None:
            source_family_owners.setdefault(source_name, set()).add(str(record.family))

    source_classification_by_name: dict[str, str] = {}
    for source_name in sorted(parts_by_name):
        if source_name in source_family_owners:
            classification = "installed_current"
        elif source_name == "R6_DEV_BLOCKED_WALL_SCREW_BEARING_COUPON_SOLID_NO_HOLE":
            classification = "blocked_no_bore_fastener_coupon"
        elif source_name == "R6_DEV_COFFERED_CASSETTE_HALF_MAX_WIDTH_COUPON":
            classification = "development_inspection_coupon"
        elif source_name in {
            "R6_DEV_JOINERY_CLEARANCE_LADDER_RECEIVER",
            "R6_DEV_JOINERY_CLEARANCE_LADDER_TONGUE",
            "R6_DEV_ORNAMENT_PRINT_FIRST_KEYHOLE_MALE_LADDER",
            "R6_DEV_ORNAMENT_PRINT_FIRST_KEYHOLE_FEMALE_LADDER",
        }:
            classification = "development_fit_coupon"
        else:
            raise ValueError(
                f"Catalog source lacks an explicit classification: {source_name}"
            )
        source_classification_by_name[source_name] = classification
    classification_counts = dict(
        sorted(
            {
                classification: list(source_classification_by_name.values()).count(
                    classification
                )
                for classification in set(source_classification_by_name.values())
            }.items()
        )
    )
    if classification_counts != {
        "blocked_no_bore_fastener_coupon": 1,
        "development_fit_coupon": 4,
        "development_inspection_coupon": 1,
        "installed_current": 43,
    }:
        raise ValueError(
            f"All-emitted catalog classification drift: {classification_counts}"
        )

    source_audits: dict[str, PackageMeshSourceAudit] = {}
    for source_name, part in sorted(parts_by_name.items()):
        owners = source_family_owners.get(source_name, set())
        part = parts_by_name[source_name]
        unresolved: set[str] = set()
        for family in owners:
            unresolved.update(blocker_ids_by_family.get(family, ()))
        classification = source_classification_by_name[source_name]
        stale_coupon = classification != "installed_current"
        current_interface = True
        mesh = serialized_source_meshes[source_name]
        geometry_valid = bool(
            mesh.is_watertight
            and mesh.is_winding_consistent
            and mesh.is_volume
            and len(mesh.split(only_watertight=False)) == 1
        )
        source_key = f"source::{source_name}"
        source_audits[source_key] = PackageMeshSourceAudit(
            mesh_family=source_key,
            source_part_name=source_name,
            geometry_validation_passed=geometry_valid,
            current_interface_geometry=current_interface,
            software_model_package_eligible=True,
            physical_installation_qualified=False,
            production_release_eligible=False,
            placeholder_or_coupon=stale_coupon,
            wall_bore_count=int(part.design_metrics.get("production_wall_screw_bore_count", 0)),
            rail_or_saddle_geometry=False,
            unresolved_interfaces=tuple(sorted(unresolved)),
            catalog_classification=classification,
            catalog_inclusion_eligible=geometry_valid,
        )

    unresolved_mesh_families = sorted(
        {
            family
            for package_plan in plans
            for family in package_plan.mesh_families
            if family not in mesh_by_family
        }
    )
    mass_report = package_solid_model_mass_report(
        plans,
        mesh_by_family,
        density_g_cm3=float(cfg["material"]["petg_density_g_cm3"]),
    )
    report = {
        "status": "PASS: ALL FIVE CANONICAL SOFTWARE-MODEL PACKAGE PLANS RESOLVED",
        "safety_description": SAFETY_DESCRIPTION,
        "plans": [item.to_dict() for item in plans],
        "print_first_physical_object_count": plans[0].physical_object_count,
        "print_first_source_roles": [
            {
                "logical_name": spec.logical_name,
                "source_part_name": spec.logical_name.split("::", 2)[2],
                "roles": list(spec.roles),
            }
            for spec in prototypes
        ],
        "print_first_mating_contexts": [
            {
                "role": "pin_fit",
                "moving_part": "R6_DEV_CROWN_BRIDGE_ANTI_DROP_PIN_RETENTION_ONLY",
                "coupon_parent": "R6_DEV_JOINERY_CLEARANCE_LADDER_RECEIVER",
                "scope": "5 mm pin-shaft clearance ladder only; not the actual crown parent",
                "complete_capture_claim": False,
            },
            {
                "role": "positive_cross_key_fit",
                "moving_part": "R6_DEV_FINAL_X_TOP_CAPTURE_WEDGE_UNIVERSAL",
                "coupon_tenon": "R6_DEV_JOINERY_CLEARANCE_LADDER_TONGUE",
                "actual_parent": "R6_DEV_CASSETTE_THROUGH_01_OF_12",
                "scope": "actual 18 x 8 x 22 mm tenon, 4 mm bore, cassette receiver, and key; dimensional/cycle coupon only",
                "complete_capture_claim": False,
            },
        ],
        "catalog_package_id": plans[1].package_id,
        "catalog_all_emitted_source_count": plans[1].physical_object_count,
        "catalog_source_classification_counts": classification_counts,
        "catalog_source_classification_by_part": source_classification_by_name,
        "assembly_model_package_ids": [
            item.package_id
            for item in plans
            if item.package_id in ASSEMBLY_MODEL_SOURCE_PACKAGE_IDS
        ],
        "software_model_packages_emitted": False,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
        "resolved_mesh_family_count": len(mesh_by_family),
        "position_specific_cassette_source_count": len(cassette_position_sources),
        "position_specific_cassette_aliasing_allowed": False,
        "catalog_source_audit_count": len(source_audits),
        "installed_source_audit_count": classification_counts[
            "installed_current"
        ],
        "unresolved_mesh_families": unresolved_mesh_families,
        "unresolved_interface_blocker_ids": [
            item["id"] for item in UNRESOLVED_INTERFACE_BLOCKERS
        ],
        "repeat_weighted_solid_model_mass": mass_report,
    }
    return plans, mesh_by_family, source_audits, report


def emit_print_first_package(
    plans: tuple[Any, ...],
    mesh_by_family: dict[str, trimesh.Trimesh],
) -> dict[str, Any]:
    """Emit and strictly validate only the fail-safe print-first package."""

    print_first = plans[0]
    placed = arrange_package_plan(print_first, mesh_by_family)
    path = MODEL_3MF_OUT / print_first.filename
    write_instanced_model_3mf(
        path,
        print_first.title,
        print_first.description,
        [(family, mesh_by_family[family]) for family in print_first.mesh_families],
        [
            (item.logical_name, item.mesh_family, item.translation_mm)
            for item in placed
        ],
    )
    serialized_audit = audit_3mf(path)
    report = validate_package_3mf(path, print_first, placed)
    report["serialized_mesh_geometry_audit"] = serialized_audit
    if not report["all_checks_pass"]:
        raise ValueError("The emitted r6 print-first package failed strict validation")
    return report


def emit_all_canonical_model_packages(
    plans: tuple[Any, ...],
    mesh_by_family: dict[str, trimesh.Trimesh],
    source_audits: dict[str, PackageMeshSourceAudit],
) -> list[dict[str, Any]]:
    """Emit and strictly validate all five neutral software-model packages."""

    reports: list[dict[str, Any]] = []
    for package_plan in plans:
        audits = None if package_plan is plans[0] else source_audits
        placed = arrange_package_plan(
            package_plan,
            mesh_by_family,
            source_audits=audits,
        )
        path = MODEL_3MF_OUT / package_plan.filename
        write_instanced_model_3mf(
            path,
            package_plan.title,
            package_plan.description,
            [
                (family, mesh_by_family[family])
                for family in package_plan.mesh_families
            ],
            [
                (item.logical_name, item.mesh_family, item.translation_mm)
                for item in placed
            ],
        )
        serialized_audit = audit_3mf(path)
        report = validate_package_3mf(
            path,
            package_plan,
            placed,
            source_audits=audits,
        )
        report["serialized_mesh_geometry_audit"] = serialized_audit
        if not report["all_checks_pass"]:
            raise ValueError(
                f"{package_plan.package_id}: canonical model package validation failed"
            )
        reports.append(report)
    if len(reports) != 5 or not all(
        report["software_model_package_eligible"] for report in reports
    ):
        raise ValueError("All five canonical software-model packages must pass")
    if any(
        report["physical_installation_qualified"]
        or report["production_release_eligible"]
        for report in reports
    ):
        raise ValueError("A model-only package may not claim physical/production release")
    return reports


def build_release_sidecar_reports(
    cfg: dict[str, Any],
    *,
    config_payload: bytes,
    plans: tuple[Any, ...],
    package_validations: list[dict[str, Any]],
    individual_pair_audits: list[dict[str, Any]],
    physical_blockers: list[str],
    solid_model_mass_report: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the explicit unsliced and canonical-model report artifacts."""

    if len(plans) != 5 or len(package_validations) != len(plans):
        raise ValueError("Sidecar reports require all five canonical package audits")
    if (
        len(individual_pair_audits) != EXPECTED_EMITTED_SOURCE_PART_COUNT
        or not all(item.get("all_checks_pass") is True for item in individual_pair_audits)
    ):
        raise ValueError(
            "Sidecar reports require all 49 passing individual STL/3MF pair audits"
        )
    if not physical_blockers:
        raise ValueError("Sidecar reports must retain physical qualification blockers")
    package_records = [
        {
            "package_id": plan.package_id,
            "filename": plan.filename,
        }
        for plan in plans
    ]
    expected_pairs = [
        (item["package_id"], item["filename"]) for item in package_records
    ]
    observed_pairs = [
        (report.get("package_id"), report.get("file"))
        for report in package_validations
    ]
    if observed_pairs != expected_pairs:
        raise ValueError("Canonical package sidecar plan/audit order drifted")
    if not all(
        report.get("all_checks_pass") is True
        and report.get("software_model_package_eligible") is True
        and report.get("physical_installation_qualified") is False
        and report.get("production_release_eligible") is False
        for report in package_validations
    ):
        raise ValueError("Canonical package sidecars require five passing software audits")

    common = {
        "project_name": deep_get(cfg, "project.name", "Story Corner"),
        "revision": deep_get(cfg, "project.revision", "r6_development"),
        "config_sha256": sha256_bytes(config_payload),
        "software_model_package_eligible": True,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
        "production_release_allowed": False,
        "physical_qualification_blockers": list(physical_blockers),
    }
    slice_report = {
        **common,
        "performed": False,
        "embedded_gcode_allowed": False,
        "printer_profile_embedded": False,
        "printer_confirmed": False,
        "nozzle_confirmed": False,
        "build_plate_confirmed": False,
        "petg_product_confirmed": False,
        "canonical_packages": package_records,
        "bambu_studio_sliced_mass_required": True,
        "weighed_finished_tare_required": True,
        "status": (
            "NOT SLICED; confirm printer, nozzle, plate, and PETG before "
            "creating any Bambu Studio profile or G-code"
        ),
    }
    model_report = {
        **common,
        "all_packages_model_only": True,
        "safety_description": SAFETY_DESCRIPTION,
        "canonical_packages": package_records,
        "canonical_package_count": len(package_records),
        "package_audits": package_validations,
        "all_package_audits_pass": True,
        "individual_model_only_3mf_count": len(individual_pair_audits),
        "individual_model_only_3mf_audits": individual_pair_audits,
        "all_individual_model_only_3mf_audits_pass": True,
        "all_3mf_artifacts_model_only": True,
        "repeat_weighted_solid_model_mass": solid_model_mass_report,
        "mass_estimate_scope": (
            "CAD model-solid PETG context only; not sliced mass, finished "
            "tare, load capacity, or an installation claim"
        ),
    }
    return slice_report, model_report


def installed_rail_baseline_report(
    cfg: dict[str, Any], *, selected_levels: int
) -> dict[str, Any]:
    """Report the frozen zero-object rail baseline without emitting study meshes."""

    contract = rail_baseline_contract(cfg)
    if selected_levels != 2:
        raise ValueError("The frozen rail-free baseline is reconciled for two levels")
    zero_counts = {
        "stitch_rail_segment": 0,
        "stitch_rail_joint_pin": 0,
        "run_end_tie_block": 0,
    }
    return {
        "status": "PASS: OPTIONAL STITCH-RAIL STUDY EXCLUDED FROM INSTALLED RC BASELINE",
        "installed_in_release_candidate": False,
        "unique_position_specific_segment_mesh_count": 0,
        "unique_installed_rail_mesh_count": 0,
        "unique_optional_research_mesh_count_emitted": 0,
        "installed_counts_per_level": dict(zero_counts),
        "installed_counts_selected_levels": dict(zero_counts),
        "removed_object_count_per_level": int(contract["per_level_removed"]),
        "removed_object_count_selected_levels": int(contract["two_level_removed"]),
        "future_reentry_gate": contract["future_reentry_gate"],
        "optional_research_geometry_emitted": False,
    }


def build_parts(
    cfg: dict[str, Any],
    geometry: dict[str, Any],
) -> tuple[
    list[PrototypePart],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    parts: list[PrototypePart] = []
    selected_levels = int(shelf_level_context(cfg)["selected_shelf_levels"])
    plan = geometry["plan_object"]
    parts.extend(clearance_ladder_parts(cfg))
    wall_part, fastener_gate = wall_screw_bearing_coupon(cfg)
    parts.append(wall_part)
    parts.append(
        cassette_half(
            cfg,
            width=float(geometry["cassette_width_mm"]),
            depth=float(geometry["shelf_depth_mm"]),
        )
    )
    cassette_family, cassette_family_report = cassette_chassis_family(
        cfg,
        plan=geometry["plan_object"],
    )
    parts.extend(cassette_family)
    # The pre-final-X corbel and grand-arch study functions remain available
    # for source-history experiments, but their interface-incomplete meshes
    # are deliberately excluded from every emitted STL/package artifact.
    final_arch_parts = final_x_arch_family(
        cfg, plan, selected_levels=selected_levels
    )
    parts.extend(final_arch_parts)
    parts.extend(final_x_retention_wedges(cfg, selected_levels=selected_levels))
    final_corbel_parts = final_x_corbel_family(
        cfg,
        geometry["corbel_geometry"],
        plan=plan,
        selected_levels=selected_levels,
    )
    parts.extend(final_corbel_parts)
    inside_corner_report = validate_inside_corner_l_assembly_clearance(
        cfg,
        plan=plan,
        cassettes=cassette_family,
        corbels=final_corbel_parts,
    )
    cassette_family_report["inside_corner_l_assembly_clearance"] = (
        inside_corner_report
    )
    parts.append(final_x_cassette_lock(cfg))
    crown_parts = crown_bridge_and_pin(cfg)
    crown_bridge = next(
        part for part in crown_parts if part.design_metrics["family"] == "rear_crown_bridge"
    )
    crown_pin = next(
        part
        for part in crown_parts
        if part.design_metrics["family"] == "crown_bridge_retention_pin"
    )
    crown_pin_sweep_report = validate_crown_pin_parent_sweeps(
        cfg,
        arches=final_arch_parts,
        cassettes=cassette_family,
        crown_bridge=crown_bridge,
        crown_pin=crown_pin,
    )
    crown_bridge.design_metrics["retention_pin_parent_service_sweep_report"] = (
        crown_pin_sweep_report
    )
    crown_pin.design_metrics.update(
        {
            "compressed_parent_service_sweeps_passed": True,
            "compressed_parent_service_sweep_report": crown_pin_sweep_report,
            "flex_deformation_qualified": False,
        }
    )
    cassette_family_report["crown_pin_parent_service_sweeps"] = (
        crown_pin_sweep_report
    )
    parts.extend(crown_parts)
    indexed_pin_parts = indexed_crown_retention_pin_parts(
        cfg, selected_levels=selected_levels
    )
    keeper_pin = next(
        part
        for part in indexed_pin_parts
        if part.design_metrics["variant_id"] == "keeper_reach"
    )
    front_tie_pin = next(
        part
        for part in indexed_pin_parts
        if part.design_metrics["variant_id"] == "front_tie_reach"
    )
    keeper_pin_sweep_report = validate_keeper_pin_parent_sweeps(
        cfg,
        cassettes=cassette_family,
        keeper_pin=keeper_pin,
    )
    keeper_pin.design_metrics.update(
        {
            "actual_parent_service_sweeps_passed": True,
            "actual_parent_service_sweep_report": keeper_pin_sweep_report,
            "software_model_mapping_complete": True,
            "physical_installation_mapping_qualified": False,
            "production_release_eligible": False,
        }
    )
    for cassette in cassette_family:
        receiver = cassette.design_metrics.get("fixed_crown_keeper_pin_receiver")
        if isinstance(receiver, dict):
            receiver.update(
                {
                    "software_model_mapping_complete": True,
                    "physical_installation_mapping_qualified": False,
                    "production_release_eligible": False,
                }
            )
    cassette_family_report["fixed_crown_keeper_pin_service_sweeps"] = (
        keeper_pin_sweep_report
    )
    keeper_strip = fixed_crown_diaphragm_keeper_strip(
        cfg, selected_levels=selected_levels
    )
    keeper_strip_sweep_report = validate_keeper_strip_parent_sweeps(
        cfg,
        cassettes=cassette_family,
        keeper_strip=keeper_strip,
        keeper_pin=keeper_pin,
    )
    keeper_strip.design_metrics.update(
        {
            "actual_parent_service_sweeps_passed": True,
            "actual_parent_service_sweep_report": keeper_strip_sweep_report,
            "software_model_mapping_complete": True,
            "physical_installation_mapping_qualified": False,
            "production_release_eligible": False,
        }
    )
    cassette_family_report["fixed_crown_keeper_strip_service_sweeps"] = (
        keeper_strip_sweep_report
    )
    seam_key_parts = seam_keys(cfg)
    fixed_front_tie = next(
        part
        for part in seam_key_parts
        if part.design_metrics.get("positive_q_axis_pin_eye_generated")
    )
    front_tie_pin_sweep_report = validate_front_tie_pin_parent_sweeps(
        cfg,
        cassettes=cassette_family,
        front_tie=fixed_front_tie,
        front_tie_pin=front_tie_pin,
    )
    front_tie_pin.design_metrics.update(
        {
            "actual_parent_receiver_geometry_embodied": True,
            "actual_parent_service_sweeps_passed": True,
            "actual_parent_service_sweep_report": front_tie_pin_sweep_report,
            "software_model_mapping_complete": True,
            "physical_installation_mapping_qualified": False,
            "production_release_eligible": False,
        }
    )
    fixed_front_tie.design_metrics.update(
        {
            "actual_parent_service_sweeps_passed": True,
            "actual_parent_service_sweep_report": front_tie_pin_sweep_report,
            "software_model_mapping_complete": True,
            "physical_installation_mapping_qualified": False,
            "production_release_eligible": False,
        }
    )
    for cassette in cassette_family:
        receiver = cassette.design_metrics.get(
            "fixed_crown_front_tie_pin_receiver"
        )
        if isinstance(receiver, dict):
            receiver.update(
                {
                    "software_model_mapping_complete": True,
                    "physical_installation_mapping_qualified": False,
                    "production_release_eligible": False,
                }
            )
    cassette_family_report["fixed_crown_front_tie_pin_service_sweeps"] = (
        front_tie_pin_sweep_report
    )
    parts.extend(indexed_pin_parts)
    parts.append(keeper_strip)
    parts.extend(seam_key_parts)
    rail_report = installed_rail_baseline_report(
        cfg, selected_levels=selected_levels
    )
    ornament_parts, ornament_report = removable_ornament_parts(
        cfg,
        selected_levels=selected_levels,
    )
    ornament_sweep_report = validate_ornament_actual_parent_sweeps(
        cfg,
        ornaments=ornament_parts,
        arches=final_arch_parts,
        corbels=final_corbel_parts,
        cassettes=cassette_family,
    )
    corner_ornament_sweep_report = (
        validate_inside_corner_ornament_cross_arm_clearance(
            cfg,
            plan=plan,
            ornaments=ornament_parts,
            arches=final_arch_parts,
            corbels=final_corbel_parts,
            cassettes=cassette_family,
        )
    )
    cassette_family_report["inside_corner_ornament_cross_arm_clearance"] = (
        corner_ornament_sweep_report
    )
    for ornament_part in ornament_parts:
        if ornament_part.design_metrics.get("installed"):
            ornament_part.design_metrics.update(
                {
                    "software_model_mapping_complete": True,
                    "physical_installation_mapping_qualified": False,
                    "actual_parent_service_sweeps_passed": True,
                    "actual_parent_service_sweep_report": ornament_sweep_report,
                }
            )
    ornament_report.update(
        {
            "software_model_mapping_complete": True,
            "physical_installation_mapping_qualified": False,
            "production_release_eligible": False,
            "actual_parent_service_sweep_report": ornament_sweep_report,
            "inside_corner_cross_arm_service_sweep_report": (
                corner_ornament_sweep_report
            ),
            "structural_parent_boss_blocker": None,
            "remaining_physical_qualification_gate": (
                "actual-parent orientation coupons, same-PETG fit/cycle/thermal/"
                "migration tests, and confirmed printer/nozzle remain required"
            ),
        }
    )
    parts.extend(ornament_parts)
    names = [part.name for part in parts]
    if len(names) != len(set(names)):
        raise ValueError("Development prototype names must be unique")
    mechanics_report = final_x_family_report(cfg, parts)
    release_report = integrated_release_reconciliation(
        cfg,
        plan=plan,
        selected_levels=selected_levels,
        rail_report=rail_report,
        ornament_report=ornament_report,
    )
    return (
        parts,
        fastener_gate,
        cassette_family_report,
        mechanics_report,
        rail_report,
        ornament_report,
        release_report,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--production",
        action="store_true",
        help="Intentionally unsupported fail-closed gate; never emits production files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.production:
        raise SystemExit(
            "HARD BLOCK: development/r6/generate_all_petg_r6.py cannot emit production geometry. "
            "Qualify field measurements, wall fasteners, PETG, printer, joinery, a full bay, and creep first."
        )

    cfg, config_payload = load_config()
    source_bundle = generation_source_bundle()
    if bool(deep_get(cfg, "project.embedded_gcode_allowed", False)):
        raise RuntimeError(
            "r6 development config unexpectedly permits embedded G-code; refusing to generate"
        )
    if bool(deep_get(cfg, "corbel.production_fastener_geometry_allowed", False)):
        raise RuntimeError(
            "r6 development config unexpectedly permits production fastener geometry; refusing to generate"
        )

    geometry, schema_warnings = calculate_development_geometry(cfg)
    (
        parts,
        fastener_gate,
        cassette_family_report,
        mechanics_report,
        rail_report,
        ornament_report,
        release_report,
    ) = build_parts(cfg, geometry)
    envelope = np.asarray(
        deep_get(cfg, "printer.minimum_model_build_envelope_mm", [180.0, 180.0, 180.0]),
        dtype=float,
    )
    if envelope.shape != (3,) or np.any(envelope <= 0.0):
        raise ValueError("printer.minimum_model_build_envelope_mm must contain three positive axes")
    density = number(cfg, "material.petg_density_g_cm3", 1.27)
    validation_parts = [
        validate_part(part, envelope_mm=envelope, density_g_cm3=density)
        for part in parts
    ]
    (
        package_plans,
        package_meshes,
        package_source_audits,
        package_report,
    ) = build_release_package_context(cfg, plan=geometry["plan_object"], parts=parts)

    safe_reset_generated_files()
    drawing_paths = generate_drawings(
        config_path=CONFIG_PATH,
        out_dir=OUT / "drawings",
    )
    schedule_paths = write_release_schedules(
        cfg,
        plan=geometry["plan_object"],
    )
    write_part_files(parts, cfg, include_development_3mf=True)
    individual_pair_audits = [
        audit_individual_stl_3mf_pair(
            source_name=part.name,
            stl_path=STL_OUT / f"{part.name}.stl",
            three_mf_path=(
                INDIVIDUAL_MODEL_3MF_OUT / f"MODEL_ONLY_{part.name}.3mf"
            ),
        )
        for part in sorted(parts, key=lambda item: item.name)
    ]
    canonical_package_validations = emit_all_canonical_model_packages(
        package_plans,
        package_meshes,
        package_source_audits,
    )
    canonical_source_geometry_audit = (
        audit_canonical_package_sources_against_individual_exports(
            plans=package_plans,
            package_validations=canonical_package_validations,
            individual_pair_audits=individual_pair_audits,
        )
    )
    package_report.update(
        {
            "software_model_packages_emitted": True,
            "canonical_package_count": len(canonical_package_validations),
            "canonical_package_filenames": [
                package_plan.filename for package_plan in package_plans
            ],
            "canonical_package_validations": canonical_package_validations,
            "all_canonical_packages_software_model_eligible": all(
                item["software_model_package_eligible"]
                for item in canonical_package_validations
            ),
            "physical_installation_qualified": False,
            "production_release_eligible": False,
            "conformance_scope": "software-model-and-package-only",
            "print_first_package_filename": package_plans[0].filename,
            "print_first_package_validation": canonical_package_validations[0],
            "individual_model_only_3mf_count": len(individual_pair_audits),
            "all_individual_model_only_3mf_pair_audits_pass": all(
                item["all_checks_pass"] for item in individual_pair_audits
            ),
            "canonical_package_source_geometry_bijection": (
                canonical_source_geometry_audit
            ),
            "all_canonical_package_sources_equal_individual_exports": True,
        }
    )
    audits = [
        audit_3mf(path)
        for path in sorted(
            [
                *MODEL_3MF_OUT.glob("*.3mf"),
                *INDIVIDUAL_MODEL_3MF_OUT.glob("*.3mf"),
            ]
        )
    ]
    level_context = shelf_level_context(cfg)
    blockers = collect_production_blockers(cfg)
    slice_report, model_3mf_report = build_release_sidecar_reports(
        cfg,
        config_payload=config_payload,
        plans=package_plans,
        package_validations=canonical_package_validations,
        individual_pair_audits=individual_pair_audits,
        physical_blockers=blockers,
        solid_model_mass_report=package_report[
            "repeat_weighted_solid_model_mass"
        ],
    )
    slice_report_path = OUT / "slice_report.json"
    model_3mf_report_path = OUT / "model_3mf_report.json"
    write_json(slice_report_path, slice_report)
    write_json(model_3mf_report_path, model_3mf_report)
    validation = {
        "schema_version": 1,
        "project_name": deep_get(cfg, "project.name", "Story Corner"),
        "revision": deep_get(cfg, "project.revision", "r6_development"),
        "generator": GENERATOR_LABEL,
        "config_sha256": sha256_bytes(config_payload),
        "generation_source_bundle": source_bundle,
        "result": "PASS: FIVE CANONICAL SOFTWARE-MODEL PACKAGES; PHYSICAL/PRODUCTION QUALIFICATION BLOCKED",
        "development_only": True,
        "production_ready": False,
        "software_model_package_eligible": True,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
        "production_release_allowed": False,
        "tested_load_rating_exists": False,
        "embedded_gcode_allowed": False,
        "model_only_3mf_audits": audits,
        "all_3mf_packages_model_only": all(item["model_only_audit_passed"] for item in audits),
        "all_3mf_artifacts_model_only": all(
            item["model_only_audit_passed"] for item in audits
        ),
        "individual_model_only_3mf_count": len(individual_pair_audits),
        "individual_model_only_3mf_audits": individual_pair_audits,
        "all_individual_model_only_3mf_pair_audits_pass": all(
            item["all_checks_pass"] for item in individual_pair_audits
        ),
        "fastener_geometry_gate": fastener_gate,
        "x_corbel_production_screw_bore_count": 0,
        "unresolved_software_interface_blockers": [],
        "unresolved_software_interface_blocker_count": 0,
        "physical_qualification_blockers": blockers,
        "production_and_physical_blockers": blockers,
        "production_blockers": blockers,
        "schema_tolerance_warnings": schema_warnings,
        "geometry_sources": {
            "plan": geometry["plan_source"],
            "x_corbel": geometry["corbel_source"],
            "neutral_mesh_and_3mf_primitives": "development/r6/model_io.py",
        },
        "geometry_summary": {
            "cassette_width_mm": geometry["cassette_width_mm"],
            "shelf_depth_mm": geometry["shelf_depth_mm"],
            "worst_bay_span_mm": geometry["worst_bay_span_mm"],
            "plan": geometry["plan_summary"],
        },
        "shelf_level_context": level_context,
        "cassette_family_validation": cassette_family_report,
        "final_x_mechanics_validation": mechanics_report,
        "stitch_rail_validation": rail_report,
        "removable_ornament_validation": ornament_report,
        "release_inventory_reconciliation": release_report,
        "release_package_planning": package_report,
        "release_report_artifacts": {
            "slice_report": slice_report_path.name,
            "model_3mf_report": model_3mf_report_path.name,
        },
        "governing_drawings": [
            path.relative_to(OUT).as_posix() for path in drawing_paths
        ],
        "parts_schedules": [
            path.relative_to(OUT).as_posix() for path in schedule_paths
        ],
        "repeat_weighted_solid_model_mass": package_report[
            "repeat_weighted_solid_model_mass"
        ],
        "mesh_and_repeat_taxonomy": {
            "unique_mesh_families_emitted": len(parts),
            "integrated_unique_installed_rail_and_ornament_meshes": release_report[
                "integrated_unique_installed_mesh_count"
            ],
            "integrated_installed_repeats_per_level": release_report[
                "integrated_installed_object_count_per_level"
            ],
            "integrated_installed_repeats_selected_two_levels": release_report[
                "integrated_installed_object_count_selected_levels"
            ],
            "integrated_noninstalled_print_first_coupons": 2,
            "complete_release_physical_objects_per_level": release_report[
                "authoritative_inventory_physical_objects_per_level"
            ],
            "complete_release_physical_objects_selected_two_levels": release_report[
                "authoritative_inventory_physical_objects_selected_levels"
            ],
            "all_five_canonical_software_model_packages_emitted": True,
            "individual_model_only_3mf_files_emitted": len(
                individual_pair_audits
            ),
            "physical_installation_package_emitted": False,
        },
        "unresolved_interface_blockers": [
            dict(item) for item in UNRESOLVED_INTERFACE_BLOCKERS
        ],
        "unresolved_interface_blocker_count": len(UNRESOLVED_INTERFACE_BLOCKERS),
        "cassette_completion_blocker": dict(CASSETTE_COMPLETION_BLOCKER),
        "unique_prototype_mesh_count": len(parts),
        "prototype_parts": validation_parts,
        "all_meshes_watertight_single_body_and_in_envelope": all(
            item["development_mesh_validation_passed"] for item in validation_parts
        ),
        "catalog_policy": "Representative virtual canvas only; not a print plate or production set.",
        "limitations": [
            "The original maximum-width coffer cassette remains a one-skin inspection coupon and is not one of the 18 position-specific chassis.",
            "The 18 position-specific cassette meshes include the configured 3.2 mm bottom skin, sparse coffer communication/venting, verified top-skin-down export, exact upper-X cradles, locator pockets, and all 22 static split-tail lock receivers.",
            "The seven zero-credit floating-pier front keys/receivers are deleted; all remaining cassette underside access mouths retain at least the configured 3.2 mm plan ligament after the upper-X, locator, and lock cutters.",
            "Integral corbel caps replace all separate saddles and saddle pins. Static lock mates and all 8,316 compressed-proxy Boolean pairs across the 75 mm service strokes clear; expanded-tail PETG flex/cycle qualification remains mandatory.",
            "The four grand half-frame families include two broad top pads plus one spring shoulder per half, exact positive quarter-turn cross-key receivers, and embodied rear-crown mating keyways; same-PETG flex/index/cycle/migration qualification remains mandatory.",
            "The crown bridge, supported lug/keyway roofs, double-shear parent ears, positive split-tail pin, compressed insertion, capture, release-window, and exact inverse-removal paths are software-closed; PETG flex/cycle/tool qualification remains mandatory.",
            "All three final-X X-corbel families have solid wall plates, zero screw bores, exact compact clevises and complementary upper-diagonal/cassette cradles; full final-position and 0.4 mm sampled lift Booleans pass.",
            "Eight removable ornament families, two connector coupons, all 99 integral parent features, all 58 repeated oculi, and exact actual-parent insertion/drop/travel sweeps are software-closed; physical actual-parent coupon/fit/cycle/migration qualification remains mandatory.",
            "The disconnected stitch-rail study is excluded from the installed baseline; zero rail segments, pins, or run-end ties are emitted by this generator run.",
            "No slicer profile, plate arrangement, support choice, or G-code is embedded.",
            "No isolated prototype may be used as an overhead storage shelf.",
        ],
    }
    validation_path = OUT / "validation.json"
    write_json(validation_path, validation)

    generated_artifacts = [
        path
        for path in OUT.rglob("*")
        if path.is_file() and path != OUT / "manifest.json"
    ]
    expected_generated_artifacts = {
        *(STL_OUT / f"{part.name}.stl" for part in parts),
        *(
            INDIVIDUAL_MODEL_3MF_OUT / f"MODEL_ONLY_{part.name}.3mf"
            for part in parts
        ),
        *(MODEL_3MF_OUT / plan.filename for plan in package_plans),
        *drawing_paths,
        *schedule_paths,
        validation_path,
        slice_report_path,
        model_3mf_report_path,
    }
    actual_generated_artifacts = set(generated_artifacts)
    if actual_generated_artifacts != expected_generated_artifacts:
        missing = sorted(
            path.relative_to(OUT).as_posix()
            for path in expected_generated_artifacts - actual_generated_artifacts
        )
        extra = sorted(
            path.relative_to(OUT).as_posix()
            for path in actual_generated_artifacts - expected_generated_artifacts
        )
        raise ValueError(
            f"Generated artifact set is not exact: missing={missing}, extra={extra}"
        )
    manifest = {
        "schema_version": 1,
        "project_name": deep_get(cfg, "project.name", "Story Corner"),
        "revision": deep_get(cfg, "project.revision", "r6_development"),
        "generator": GENERATOR_LABEL,
        "config_sha256": sha256_bytes(config_payload),
        "generation_source_bundle": source_bundle,
        "development_only": True,
        "production_ready": False,
        "software_model_package_eligible": True,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
        "production_release_allowed": False,
        "tested_load_rating_exists": False,
        "embedded_gcode_file_count": 0,
        "selected_shelf_levels": level_context["selected_shelf_levels"],
        "independent_wall_fastened_L_assemblies": level_context["selected_shelf_levels"],
        "vertical_structural_ties_between_levels": 0,
        "unique_prototype_mesh_count": len(parts),
        "individual_model_only_3mf_count": len(individual_pair_audits),
        "individual_model_only_3mf_directory": (
            INDIVIDUAL_MODEL_3MF_OUT.relative_to(OUT).as_posix()
        ),
        "individual_stl_3mf_bijection": [
            {
                "source_part_name": item["source_part_name"],
                "stl_path": item["stl_path"],
                "individual_3mf_path": item["individual_3mf_path"],
                "common_canonical_triangle_digest": item[
                    "common_canonical_triangle_digest"
                ],
            }
            for item in individual_pair_audits
        ],
        "all_individual_model_only_3mf_pair_audits_pass": True,
        "position_specific_cassette_chassis_per_level": cassette_family_report[
            "actual_counts"
        ]["total_position_specific_chassis"],
        "position_specific_cassette_chassis_selected_levels": (
            cassette_family_report["actual_counts"]["total_position_specific_chassis"]
            * level_context["selected_shelf_levels"]
        ),
        "final_x_logical_counts_per_level": mechanics_report["per_level_logical_counts"],
        "final_x_logical_counts_selected_two_levels": mechanics_report[
            "selected_two_level_logical_counts"
        ],
        "unique_final_x_mesh_count": mechanics_report["unique_final_x_mesh_count"],
        "unique_position_specific_stitch_rail_segment_mesh_count": rail_report[
            "unique_position_specific_segment_mesh_count"
        ],
        "stitch_rail_segments_per_level": rail_report["installed_counts_per_level"][
            "stitch_rail_segment"
        ],
        "stitch_rail_segments_selected_levels": rail_report[
            "installed_counts_selected_levels"
        ]["stitch_rail_segment"],
        "stitch_rail_joint_pins_per_level": rail_report["installed_counts_per_level"][
            "stitch_rail_joint_pin"
        ],
        "stitch_rail_joint_pins_selected_levels": rail_report[
            "installed_counts_selected_levels"
        ]["stitch_rail_joint_pin"],
        "run_end_tie_blocks_per_level": rail_report["installed_counts_per_level"][
            "run_end_tie_block"
        ],
        "run_end_tie_blocks_selected_levels": rail_report[
            "installed_counts_selected_levels"
        ]["run_end_tie_block"],
        "unique_installed_ornament_mesh_family_count": ornament_report[
            "unique_installed_mesh_family_count"
        ],
        "ornament_installed_objects_per_level": ornament_report[
            "installed_object_count_per_level"
        ],
        "ornament_installed_objects_selected_levels": ornament_report[
            "installed_object_count_selected_levels"
        ],
        "print_first_ornament_connector_coupon_mesh_count": ornament_report[
            "unique_print_first_coupon_mesh_count"
        ],
        "integrated_release_inventory_reconciliation": release_report,
        "release_package_planning": package_report,
        "release_report_artifacts": {
            "slice_report": slice_report_path.name,
            "model_3mf_report": model_3mf_report_path.name,
        },
        "governing_drawings": [
            path.relative_to(OUT).as_posix() for path in drawing_paths
        ],
        "parts_schedules": [
            path.relative_to(OUT).as_posix() for path in schedule_paths
        ],
        "repeat_weighted_solid_model_mass": package_report[
            "repeat_weighted_solid_model_mass"
        ],
        "unresolved_software_interface_blockers": [],
        "physical_qualification_blockers": blockers,
        "production_and_physical_blockers": blockers,
        "unresolved_interface_blockers": [
            dict(item) for item in UNRESOLVED_INTERFACE_BLOCKERS
        ],
        "cassette_completion_blocker": dict(CASSETTE_COMPLETION_BLOCKER),
        "generated_artifact_count_excluding_manifest": len(generated_artifacts),
        "artifacts": artifact_records(generated_artifacts),
        "warning": (
            "These are model-only development prototypes, not a production print set. "
            "No load rating is claimed and wall installation is blocked."
        ),
    }
    write_json(OUT / "manifest.json", manifest)

    print(
        json.dumps(
            {
                "result": validation["result"],
                "unique_prototype_meshes": len(parts),
                "stl_files": len(list(STL_OUT.glob("*.stl"))),
                "model_only_3mf_files": len(list(MODEL_3MF_OUT.glob("*.3mf"))),
                "individual_model_only_3mf_files": len(
                    list(INDIVIDUAL_MODEL_3MF_OUT.glob("*.3mf"))
                ),
                "selected_shelf_levels": level_context["selected_shelf_levels"],
                "position_specific_cassette_chassis": cassette_family_report[
                    "actual_counts"
                ]["total_position_specific_chassis"],
                "final_x_unique_family_meshes": mechanics_report[
                    "unique_final_x_mesh_count"
                ],
                "position_specific_stitch_rail_segment_meshes": rail_report[
                    "unique_position_specific_segment_mesh_count"
                ],
                "installed_ornament_mesh_families": ornament_report[
                    "unique_installed_mesh_family_count"
                ],
                "print_first_ornament_connector_coupons": ornament_report[
                    "unique_print_first_coupon_mesh_count"
                ],
                "canonical_model_only_packages": [
                    package_plan.filename for package_plan in package_plans
                ],
                "software_model_packages_emitted": True,
                "software_model_package_eligible": True,
                "physical_installation_qualified": False,
                "production_release_eligible": False,
                "production_release_allowed": False,
                "unresolved_software_interface_blockers": len(
                    UNRESOLVED_INTERFACE_BLOCKERS
                ),
                "production_ready": False,
                "wall_fastener_gate": fastener_gate["state"],
                "output": str(OUT),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
