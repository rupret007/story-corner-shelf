#!/usr/bin/env python3
"""Emit the unsliced R7 cable-hook qualification models into a fresh directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import trimesh


ROOT = Path(__file__).resolve().parent
R6_ROOT = ROOT.parent / "r6"
for candidate in (ROOT, R6_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cable_peg_geometry import (  # noqa: E402
    all_meshes_closed,
    load_config,
    qualification_meshes,
    validate_geometry,
)
from model_io import write_model_3mf  # noqa: E402


PACKAGE_FILENAME = "MODEL_ONLY_R7_CABLE_PEG_COLUMN_QUALIFICATION.3mf"
MANIFEST_FILENAME = "manifest.json"
MODEL_NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_bytes_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    _write_bytes_exclusive(
        path,
        (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def _canonical_triangle_digest_0p001mm(
    vertices: np.ndarray,
    faces: np.ndarray,
) -> str:
    quantized = np.rint(np.asarray(vertices, dtype=float) / 0.001).astype(np.int64)
    canonical = sorted(
        tuple(sorted(tuple(int(value) for value in vertex) for vertex in triangle))
        for triangle in quantized[np.asarray(faces, dtype=np.int64)]
    )
    return sha256_bytes(
        json.dumps(canonical, separators=(",", ":")).encode("ascii")
    )


def _read_3mf_meshes(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"{path.name}: corrupt 3MF member")
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for node in root.findall("m:resources/m:object", MODEL_NS):
        mesh = node.find("m:mesh", MODEL_NS)
        if mesh is None:
            continue
        name = node.attrib.get("name")
        if not name or name in result:
            raise ValueError(f"{path.name}: missing or duplicate mesh name")
        vertices = np.asarray(
            [
                [float(vertex.attrib[key]) for key in ("x", "y", "z")]
                for vertex in mesh.findall("m:vertices/m:vertex", MODEL_NS)
            ],
            dtype=float,
        )
        faces = np.asarray(
            [
                [int(triangle.attrib[key]) for key in ("v1", "v2", "v3")]
                for triangle in mesh.findall("m:triangles/m:triangle", MODEL_NS)
            ],
            dtype=np.int64,
        )
        if len(vertices) == 0 or len(faces) == 0 or not np.isfinite(vertices).all():
            raise ValueError(f"{path.name}: invalid mesh payload")
        result[name] = (vertices, faces)
    return result


def _audit_3mf_source_geometry(
    path: Path,
    expected: dict[str, trimesh.Trimesh],
) -> dict[str, str]:
    observed = _read_3mf_meshes(path)
    if set(observed) != set(expected):
        raise ValueError(f"{path.name}: 3MF source-name set drifted")
    digests: dict[str, str] = {}
    for name, mesh in expected.items():
        expected_digest = _canonical_triangle_digest_0p001mm(
            np.asarray(mesh.vertices), np.asarray(mesh.faces)
        )
        vertices, faces = observed[name]
        observed_digest = _canonical_triangle_digest_0p001mm(vertices, faces)
        if expected_digest != observed_digest or len(faces) != len(mesh.faces):
            raise ValueError(f"{path.name}: {name} serialized geometry drifted")
        digests[name] = expected_digest
    return digests


def _stl_round_trip(
    mesh: trimesh.Trimesh,
    name: str,
) -> tuple[bytes, dict[str, Any], trimesh.Trimesh]:
    payload = bytes(mesh.export(file_type="stl"))
    loaded = trimesh.load_mesh(trimesh.util.wrap_as_stream(payload), file_type="stl")
    if isinstance(loaded, trimesh.Scene):
        loaded = loaded.to_geometry()
    if not isinstance(loaded, trimesh.Trimesh):
        raise ValueError(f"{name}: STL did not reload as a mesh")
    loaded.remove_unreferenced_vertices()
    loaded.fix_normals()
    areas = np.asarray(loaded.area_faces, dtype=float)
    if (
        not loaded.is_watertight
        or not loaded.is_volume
        or loaded.body_count != 1
        or len(areas) == 0
        or np.any(areas <= 1.0e-12)
    ):
        raise ValueError(f"{name}: serialized STL is not one clean closed body")
    return payload, {
        "triangle_count": int(len(loaded.faces)),
        "bounds_mm": np.round(loaded.bounds, 6).tolist(),
        "volume_mm3": float(loaded.volume),
        "watertight": True,
        "positive_volume": True,
        "body_count": 1,
        "zero_area_triangle_count": 0,
    }, loaded


def build(output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"Refusing existing output directory: {output}")
    output.mkdir(parents=True, exist_ok=False)

    cfg = load_config()
    metrics = validate_geometry(cfg)
    meshes = qualification_meshes(cfg)
    if len(meshes) != 3 or not all_meshes_closed(meshes.values()):
        raise ValueError("R7 cable-hook qualification requires exactly three closed meshes")

    artifact_records: list[dict[str, Any]] = []
    stl_dir = output / "stl"
    individual_dir = output / "individual_model_only_3mf"
    package_dir = output / "model_only_3mf"
    individual_translation = (5.2, 5.2, 0.0)
    serialized_meshes: dict[str, trimesh.Trimesh] = {}

    for name, mesh in sorted(meshes.items()):
        stl_payload, stl_audit, serialized_mesh = _stl_round_trip(mesh, name)
        serialized_meshes[name] = serialized_mesh
        stl_path = stl_dir / f"{name}.stl"
        _write_bytes_exclusive(stl_path, stl_payload)
        artifact_records.append(
            {
                "path": stl_path.relative_to(output).as_posix(),
                "bytes": len(stl_payload),
                "sha256": sha256_bytes(stl_payload),
                "kind": "individual_stl",
                "mesh_name": name,
                "mesh_audit": stl_audit,
            }
        )

        individual_path = individual_dir / f"MODEL_ONLY_{name}.3mf"
        write_model_3mf(
            individual_path,
            f"Story Corner {name}",
            "UNSLICED QUALIFICATION-ONLY MODEL; PETG PHYSICAL TESTING REQUIRED; NO LOAD RATING",
            [(name, serialized_mesh, individual_translation)],
        )
        individual_geometry = _audit_3mf_source_geometry(
            individual_path,
            {name: serialized_mesh},
        )
        artifact_records.append(
            {
                "path": individual_path.relative_to(output).as_posix(),
                "bytes": individual_path.stat().st_size,
                "sha256": sha256_file(individual_path),
                "kind": "individual_model_only_3mf",
                "mesh_name": name,
                "translation_mm": list(individual_translation),
                "canonical_triangle_digest_0p001mm": individual_geometry[name],
            }
        )

    ordered = list(sorted(serialized_meshes.items()))
    translations = {
        "R7_DEV_CABLE_PEG_EXACT_R6_PIER_OVERLAY_COUPON": (5.2, 5.2, 0.0),
        "R7_DEV_CABLE_PEG_FRONT_SNAP_C_COLLAR_HOOK": (52.2, 5.2, 0.0),
        "R7_DEV_CABLE_PEG_COLLAR_CLEARANCE_LADDER_0P2_0P3_0P4_0P5": (
            100.2,
            5.2,
            0.0,
        ),
    }
    plate = np.asarray(cfg["printing"]["printable_volume_mm"], dtype=float)
    brim_margin = float(cfg["printing"]["brim_mm"]) + float(
        cfg["printing"]["brim_object_gap_mm"]
    )
    placed_bounds: dict[str, list[list[float]]] = {}
    brim_adjusted_xy: list[tuple[str, float, float, float, float]] = []
    for name, mesh in ordered:
        translation = np.asarray(translations[name], dtype=float)
        bounds = np.asarray(mesh.bounds, dtype=float) + translation
        adjusted = bounds.copy()
        adjusted[0, :2] -= brim_margin
        adjusted[1, :2] += brim_margin
        if np.any(adjusted[0] < -1.0e-6) or np.any(adjusted[1] > plate + 1.0e-6):
            raise ValueError(f"{name}: brim-adjusted placement exceeds A1 mini volume")
        placed_bounds[name] = np.round(bounds, 6).tolist()
        brim_adjusted_xy.append(
            (name, adjusted[0, 0], adjusted[1, 0], adjusted[0, 1], adjusted[1, 1])
        )
    minimum_brim_gap = float("inf")
    for index, left in enumerate(brim_adjusted_xy):
        for right in brim_adjusted_xy[index + 1 :]:
            x_gap = max(right[1] - left[2], left[1] - right[2], 0.0)
            y_gap = max(right[3] - left[4], left[3] - right[4], 0.0)
            if x_gap == 0.0 and y_gap == 0.0:
                raise ValueError(f"{left[0]} and {right[0]} have overlapping brim envelopes")
            minimum_brim_gap = min(minimum_brim_gap, max(x_gap, y_gap))
    required_brim_gap = float(cfg["printing"]["minimum_brim_to_brim_gap_mm"])
    if minimum_brim_gap < required_brim_gap - 1.0e-6:
        raise ValueError("Qualification objects lose the required brim-to-brim gap")
    package_path = package_dir / PACKAGE_FILENAME
    write_model_3mf(
        package_path,
        "Story Corner R7 cable-peg column qualification",
        "UNSLICED QUALIFICATION-ONLY A1 MINI MODEL; SUNLU PETG TEST ARTICLE; ZERO RATED LOAD",
        [(name, mesh, translations[name]) for name, mesh in ordered],
    )
    package_geometry = _audit_3mf_source_geometry(
        package_path,
        dict(ordered),
    )
    artifact_records.append(
        {
            "path": package_path.relative_to(output).as_posix(),
            "bytes": package_path.stat().st_size,
            "sha256": sha256_file(package_path),
            "kind": "qualification_model_only_3mf",
            "object_count": 3,
            "object_names": [name for name, _mesh in ordered],
            "translations_mm": {
                name: list(translations[name]) for name, _mesh in ordered
            },
            "placed_bounds_mm": placed_bounds,
            "brim_plus_object_gap_mm": brim_margin,
            "minimum_brim_to_brim_gap_mm": minimum_brim_gap,
            "canonical_source_triangle_digests_0p001mm": package_geometry,
        }
    )

    manifest = {
        "schema_version": 1,
        "project": cfg["project"],
        "package_id": "r7_cable_peg_column_qualification",
        "package_filename": PACKAGE_FILENAME,
        "qualification_object_count": 3,
        "qualification_only": True,
        "unsliced": True,
        "generated_gcode_present": False,
        "embedded_toolpath_file_count": 0,
        "physical_qualification_complete": False,
        "installed_release_allowed": False,
        "production_ready": False,
        "load_rating_allowed": False,
        "normal_hook_locations_per_level_after_qualification": 9,
        "excluded_run_start_corner_locations_per_level": 2,
        "base_r6_installed_counts_unchanged": {"one_level": 258, "two_levels": 516},
        "promoted_counts_if_all_physical_gates_pass": {
            "one_level": 267,
            "two_levels": 534,
        },
        "hook_metrics": metrics.to_dict(),
        "printing": cfg["printing"],
        "load_qualification": cfg["load_qualification"],
        "source_provenance": {
            "r7_config": {
                "path": "development/r7/config.json",
                "sha256": sha256_file(ROOT / "config.json"),
            },
            "r7_geometry": {
                "path": "development/r7/cable_peg_geometry.py",
                "sha256": sha256_file(ROOT / "cable_peg_geometry.py"),
            },
            "r7_generator": {
                "path": "development/r7/generate_cable_peg_qualification.py",
                "sha256": sha256_file(ROOT / "generate_cable_peg_qualification.py"),
            },
            "r6_config": {
                "path": "development/r6/config.json",
                "sha256": sha256_file(R6_ROOT / "config.json"),
            },
            "r6_ornament_geometry": {
                "path": "development/r6/ornament_geometry.py",
                "sha256": sha256_file(R6_ROOT / "ornament_geometry.py"),
            },
        },
        "artifacts": sorted(artifact_records, key=lambda item: item["path"]),
    }
    manifest["artifact_count_excluding_manifest"] = len(artifact_records)
    manifest["artifact_bytes_excluding_manifest"] = sum(
        int(item["bytes"]) for item in artifact_records
    )
    _write_json_exclusive(output / MANIFEST_FILENAME, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Fresh output directory; existing destinations are refused.",
    )
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(
        f"PASS: {manifest['artifact_count_excluding_manifest']} unsliced artifacts + manifest"
    )


if __name__ == "__main__":
    main()
