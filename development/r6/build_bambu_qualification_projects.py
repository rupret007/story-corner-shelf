#!/usr/bin/env python3
"""Build fail-closed, unsliced Bambu Studio qualification projects for r6.

This helper deliberately emits only four small qualification projects.  It
does not emit a full shelf, G-code, or a production release.  Geometry is read
from the manifest-hashed individual model-only 3MF exports, never regenerated.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import plistlib
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from xml.etree import ElementTree as ET

from publish_root import _exclusive_atomic_rename


NS_3MF = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_PRODUCTION = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
NS_BAMBU = "http://schemas.bambulab.com/package/2021"
NS_XML = "http://www.w3.org/XML/1998/namespace"

BED_SIZE_MM = (180.0, 180.0, 180.0)
MACHINE_PROFILE = "Bambu Lab A1 mini 0.4 nozzle"
PROCESS_PROFILE = "0.20mm Strength @BBL A1M"
FILAMENT_PROFILE = "SUNLU PETG @BBL A1M 0.4 nozzle"
BED_TYPE = "Textured PEI Plate"
FILAMENT_COLOUR = "#000000"
MANIFEST_NAME = "QUALIFICATION_PROJECTS_MANIFEST.json"
README_NAME = "README_BAMBU_STUDIO.md"
CANONICAL_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
CANONICAL_ZIP_MODE = 0o100644
CANONICAL_ZIP_COMPRESSION = zipfile.ZIP_DEFLATED
CANONICAL_ZIP_COMPRESSLEVEL = 9

EXCLUDED_SOURCE = "R6_DEV_BLOCKED_WALL_SCREW_BEARING_COUPON_SOLID_NO_HOLE"
EXCLUDED_REASON = (
    "Deliberately omitted: this fail-closed placeholder is solid and has no "
    "screw bore. The actual metal screw shank, head/washer, embedment, and tool "
    "envelope remain unconfirmed, so printing it cannot qualify wall bearing."
)


class BambuQualificationError(RuntimeError):
    """Raised when any qualification-project precondition or audit fails."""


@dataclass(frozen=True)
class ProjectSpec:
    project_id: str
    filename: str
    title: str
    sources: tuple[str, ...]
    translations_mm: tuple[tuple[float, float, float], ...]
    process_overrides: tuple[tuple[str, Any], ...]
    support_review: str

    @property
    def overrides(self) -> dict[str, Any]:
        return dict(self.process_overrides)


PROJECT_SPECS: tuple[ProjectSpec, ...] = (
    ProjectSpec(
        project_id="clearance_receiver_tongue_top_key",
        filename="QUALIFICATION_ONLY_R6_A1M_CLEARANCE_AND_TOP_KEY_UNSLICED.3mf",
        title="r6 qualification only — clearance receiver, tongue, and top key",
        sources=(
            "R6_DEV_JOINERY_CLEARANCE_LADDER_RECEIVER",
            "R6_DEV_JOINERY_CLEARANCE_LADDER_TONGUE",
            "R6_DEV_FINAL_X_TOP_CAPTURE_WEDGE_UNIVERSAL",
        ),
        translations_mm=((10.0, 10.0, 0.0), (120.0, 10.0, 0.0), (120.0, 80.0, 0.0)),
        process_overrides=(
            ("enable_support", "1"),
            ("support_type", "normal(auto)"),
            ("support_on_build_plate_only", "1"),
            ("brim_type", "no_brim"),
            ("brim_width", "0"),
        ),
        support_review=(
            "Review the saved-orientation transverse bore support on the tongue; "
            "do not rotate or scale any object."
        ),
    ),
    ProjectSpec(
        project_id="ornament_connector_pair",
        filename="QUALIFICATION_ONLY_R6_A1M_ORNAMENT_CONNECTORS_UNSLICED.3mf",
        title="r6 qualification only — ornament male and female connector ladders",
        sources=(
            "R6_DEV_ORNAMENT_PRINT_FIRST_KEYHOLE_MALE_LADDER",
            "R6_DEV_ORNAMENT_PRINT_FIRST_KEYHOLE_FEMALE_LADDER",
        ),
        translations_mm=((15.0, 45.0, 0.0), (15.0, 100.0, 0.0)),
        process_overrides=(
            ("enable_support", "1"),
            ("support_type", "normal(auto)"),
            ("support_on_build_plate_only", "1"),
            ("brim_type", "no_brim"),
            ("brim_width", "0"),
        ),
        support_review=(
            "Review support contact at the upward receiver housings while keeping "
            "the saved decorated-face-down orientation."
        ),
    ),
    ProjectSpec(
        project_id="crown_pin_support_brim_candidate",
        filename="QUALIFICATION_ONLY_R6_A1M_CROWN_PIN_CANDIDATE_UNSLICED.3mf",
        title="r6 qualification only — crown pin support and brim candidate",
        sources=("R6_DEV_CROWN_BRIDGE_ANTI_DROP_PIN_RETENTION_ONLY",),
        translations_mm=((79.4, 86.0, 0.0),),
        process_overrides=(
            ("enable_support", "1"),
            ("support_type", "normal(auto)"),
            ("support_on_build_plate_only", "1"),
            ("brim_type", "outer_only"),
            ("brim_width", "6"),
        ),
        support_review=(
            "This is a support/brim candidate only. Verify shaft, split plane, "
            "round-head contact, cooling, removal, and flexure before acceptance."
        ),
    ),
    ProjectSpec(
        project_id="through_cassette_actual_parent_fit",
        filename="QUALIFICATION_ONLY_R6_A1M_THROUGH_CASSETTE_PARENT_FIT_UNSLICED.3mf",
        title="r6 qualification only — through cassette actual-parent fit",
        sources=("R6_DEV_CASSETTE_THROUGH_01_OF_12",),
        translations_mm=((13.8875, 10.2, 0.0),),
        process_overrides=(
            ("enable_support", "1"),
            ("support_type", "normal(auto)"),
            ("support_on_build_plate_only", "1"),
            ("brim_type", "outer_only"),
            ("brim_width", "5"),
        ),
        support_review=(
            "Review every support contact and removal path on the saved continuous-"
            "top-skin-down cassette orientation before this actual-parent fit trial."
        ),
    ),
)


@dataclass(frozen=True)
class ProfileNode:
    name: str
    profile_type: str
    path: Path
    payload: Mapping[str, Any]


@dataclass(frozen=True)
class MeshAudit:
    source_name: str
    path: Path
    sha256: str
    bytes: int
    vertex_count: int
    triangle_count: int
    bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    geometry_sha256_0p0001mm: str
    object_xml: ET.Element


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BambuQualificationError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BambuQualificationError(f"cannot read strict JSON {path}: {exc}") from exc


def _json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_r6_root(script: Path) -> Path:
    """Resolve the development layout or its flattened publication relocation."""

    parent = script.resolve().parent
    if parent.name == "r6" and parent.parent.name == "development":
        candidate = parent
    else:
        candidate = parent
    required = candidate / "generated" / "individual_model_only_3mf"
    if not required.is_dir() or not (candidate / "generated" / "manifest.json").is_file():
        raise BambuQualificationError(
            f"cannot locate r6 generated inputs beside builder: {candidate}"
        )
    return candidate


def default_profile_root() -> Path:
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "BambuStudio"
        / "system"
        / "BBL"
    )


def default_bambu_executable() -> Path:
    return Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")


class ProfileCatalog:
    """Strict recursive resolver for Bambu ``inherits`` and ``include`` graphs."""

    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)
        self._nodes: dict[tuple[str, str], ProfileNode] = {}
        for path in sorted(self.root.rglob("*.json")):
            payload = _load_json(path)
            if not isinstance(payload, dict):
                continue
            name = payload.get("name")
            profile_type = payload.get("type")
            if profile_type is None:
                first_directory = path.relative_to(self.root).parts[0]
                if first_directory in {"machine", "process", "filament"}:
                    profile_type = first_directory
            if not isinstance(name, str) or not name or not isinstance(profile_type, str):
                continue
            key = (profile_type, name)
            if key in self._nodes:
                raise BambuQualificationError(
                    f"duplicate {profile_type} profile name {name!r}: "
                    f"{self._nodes[key].path}, {path}"
                )
            self._nodes[key] = ProfileNode(name, profile_type, path, payload)

    def flatten(self, name: str, profile_type: str) -> tuple[dict[str, Any], list[ProfileNode]]:
        chain: list[ProfileNode] = []
        seen_chain: set[tuple[str, str, Path]] = set()

        def resolve(current_name: str, stack: tuple[str, ...]) -> dict[str, Any]:
            if current_name in stack:
                raise BambuQualificationError(
                    f"profile inheritance/include cycle: {' -> '.join((*stack, current_name))}"
                )
            key = (profile_type, current_name)
            node = self._nodes.get(key)
            if node is None:
                raise BambuQualificationError(
                    f"missing {profile_type} profile dependency {current_name!r}"
                )
            marker = (node.profile_type, node.name, node.path)
            if marker not in seen_chain:
                chain.append(node)
                seen_chain.add(marker)
            merged: dict[str, Any] = {}
            parent = node.payload.get("inherits")
            if parent not in (None, ""):
                if not isinstance(parent, str):
                    raise BambuQualificationError(f"invalid inherits in {node.path}")
                merged.update(resolve(parent, (*stack, current_name)))
            includes = node.payload.get("include", [])
            if isinstance(includes, str):
                includes = [includes]
            if not isinstance(includes, list) or not all(
                isinstance(value, str) and value for value in includes
            ):
                raise BambuQualificationError(f"invalid include list in {node.path}")
            for included in includes:
                merged.update(resolve(included, (*stack, current_name)))
            merged.update(
                {
                    key_name: copy.deepcopy(value)
                    for key_name, value in node.payload.items()
                    if key_name not in {"inherits", "include"}
                }
            )
            return merged

        flattened = resolve(name, ())
        flattened["name"] = name
        flattened["type"] = profile_type
        flattened["inherits"] = ""
        flattened.pop("include", None)
        return flattened, chain


def qualification_profiles(
    catalog: ProfileCatalog,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, list[ProfileNode]]]:
    machine, machine_chain = catalog.flatten(MACHINE_PROFILE, "machine")
    process, process_chain = catalog.flatten(PROCESS_PROFILE, "process")
    filament, filament_chain = catalog.flatten(FILAMENT_PROFILE, "filament")

    process.update(
        {
            "layer_height": "0.2",
            "wall_loops": "6",
            "sparse_infill_density": "25%",
        }
    )
    filament.update(
        {
            "filament_colour": [FILAMENT_COLOUR],
            "filament_flow_ratio": ["0.94"],
            "filament_max_volumetric_speed": ["9"],
            "nozzle_temperature_initial_layer": ["250"],
            "nozzle_temperature": ["245"],
            "textured_plate_temp_initial_layer": ["60"],
            "textured_plate_temp": ["60"],
        }
    )
    required = {
        "machine printer": machine.get("printer_model") == "Bambu Lab A1 mini",
        "machine variant": machine.get("printer_variant") == "0.4",
        "machine nozzle": machine.get("nozzle_diameter") == ["0.4"],
        "machine area": machine.get("printable_area")
        == ["0x0", "180x0", "180x180", "0x180"],
        "machine height": machine.get("printable_height") == "180",
        "filament type": filament.get("filament_type") == ["PETG"],
        "filament vendor": filament.get("filament_vendor") == ["SUNLU"],
        "process infill pattern": process.get("sparse_infill_pattern") == "grid",
        "process top shells": process.get("top_shell_layers") == "5",
        "process bottom shells": process.get("bottom_shell_layers") == "3",
        "filament minimum fan": filament.get("fan_min_speed") == ["10"],
        "filament maximum fan": filament.get("fan_max_speed") == ["30"],
        "filament overhang fan": filament.get("overhang_fan_speed") == ["90"],
    }
    failures = [label for label, passed in required.items() if not passed]
    if failures:
        raise BambuQualificationError(
            f"flattened installed profiles fail qualification contract: {failures}"
        )
    return machine, process, filament, {
        "machine": machine_chain,
        "process": process_chain,
        "filament": filament_chain,
    }


def _parse_transform(value: str | None) -> tuple[float, ...]:
    if value is None:
        return (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
    try:
        values = tuple(float(item) for item in value.split())
    except ValueError as exc:
        raise BambuQualificationError(f"invalid 3MF transform {value!r}") from exc
    if len(values) != 12:
        raise BambuQualificationError(f"3MF transform does not have 12 values: {value!r}")
    if not all(math.isfinite(item) for item in values):
        raise BambuQualificationError(f"3MF transform contains a non-finite value: {value!r}")
    return values


def _identity_linear(transform: Sequence[float], tolerance: float = 1.0e-7) -> bool:
    expected = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
    return all(abs(transform[index] - expected[index]) <= tolerance for index in range(9))


def _translation(transform: Sequence[float]) -> tuple[float, float, float]:
    return float(transform[9]), float(transform[10]), float(transform[11])


def _mesh_values(mesh: ET.Element) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    namespace = {"m": NS_3MF}
    try:
        vertices = [
            (float(node.attrib["x"]), float(node.attrib["y"]), float(node.attrib["z"]))
            for node in mesh.findall("m:vertices/m:vertex", namespace)
        ]
        triangles = [
            (int(node.attrib["v1"]), int(node.attrib["v2"]), int(node.attrib["v3"]))
            for node in mesh.findall("m:triangles/m:triangle", namespace)
        ]
    except (KeyError, ValueError) as exc:
        raise BambuQualificationError("invalid numeric mesh payload") from exc
    if not vertices or not triangles:
        raise BambuQualificationError("empty 3MF mesh payload")
    if not all(math.isfinite(value) for vertex in vertices for value in vertex):
        raise BambuQualificationError("3MF mesh contains a non-finite coordinate")
    if any(index < 0 or index >= len(vertices) for face in triangles for index in face):
        raise BambuQualificationError("3MF triangle index outside vertex array")
    return vertices, triangles


def _mesh_evidence(
    mesh: ET.Element,
) -> tuple[int, int, tuple[tuple[float, float, float], tuple[float, float, float]], str]:
    vertices, triangles = _mesh_values(mesh)
    lower = tuple(min(vertex[axis] for vertex in vertices) for axis in range(3))
    upper = tuple(max(vertex[axis] for vertex in vertices) for axis in range(3))
    grid_vertices = [
        tuple(int(round((vertex[axis] - lower[axis]) * 10000.0)) for axis in range(3))
        for vertex in vertices
    ]
    canonical_triangles = sorted(
        tuple(sorted((grid_vertices[face[0]], grid_vertices[face[1]], grid_vertices[face[2]])))
        for face in triangles
    )
    digest = _sha256_bytes(
        json.dumps(canonical_triangles, separators=(",", ":")).encode("ascii")
    )
    return len(vertices), len(triangles), (lower, upper), digest


def _manifest_artifacts(release_manifest: Path) -> dict[str, Mapping[str, Any]]:
    payload = _load_json(release_manifest)
    records = payload.get("artifacts") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise BambuQualificationError("generated manifest has no artifact records")
    result: dict[str, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise BambuQualificationError("generated manifest has an invalid artifact record")
        relative = record["path"]
        if relative in result:
            raise BambuQualificationError(f"duplicate generated artifact {relative}")
        result[relative] = record
    return result


def audit_individual_source(
    source_dir: Path,
    source_name: str,
    artifact_records: Mapping[str, Mapping[str, Any]],
) -> MeshAudit:
    filename = f"MODEL_ONLY_{source_name}.3mf"
    relative = f"individual_model_only_3mf/{filename}"
    path = source_dir / filename
    record = artifact_records.get(relative)
    if record is None or not path.is_file() or path.is_symlink():
        raise BambuQualificationError(f"missing exact individual source {relative}")
    digest = _sha256_file(path)
    if record.get("sha256") != digest or record.get("bytes") != path.stat().st_size:
        raise BambuQualificationError(f"individual source differs from manifest: {relative}")
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise BambuQualificationError(f"individual source CRC failure: {relative}")
        names = _audit_zip_container(archive, relative)
        if names != ["[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"]:
            raise BambuQualificationError(f"individual source is not exact neutral 3MF: {relative}")
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
    namespace = {"m": NS_3MF}
    description = root.find("m:metadata[@name='Description']", namespace)
    if description is None or not all(
        token in (description.text or "")
        for token in ("MODEL-ONLY", "EXPERIMENTAL", "UNRATED", "NO G-CODE")
    ):
        raise BambuQualificationError(f"source safety metadata drift: {relative}")
    objects = root.findall("m:resources/m:object", namespace)
    builds = root.findall("m:build/m:item", namespace)
    if len(objects) != 1 or len(builds) != 1:
        raise BambuQualificationError(f"individual source is not one exact object: {relative}")
    obj = objects[0]
    mesh = obj.find("m:mesh", namespace)
    if obj.attrib.get("name") != source_name or mesh is None:
        raise BambuQualificationError(f"individual source name/mesh drift: {relative}")
    if builds[0].attrib.get("objectid") != obj.attrib.get("id"):
        raise BambuQualificationError(f"individual build reference drift: {relative}")
    transform = _parse_transform(builds[0].attrib.get("transform"))
    if not _identity_linear(transform) or any(abs(value) > 1.0e-7 for value in _translation(transform)):
        raise BambuQualificationError(f"individual source has a nonidentity saved transform: {relative}")
    vertex_count, triangle_count, bounds, geometry_digest = _mesh_evidence(mesh)
    return MeshAudit(
        source_name=source_name,
        path=path,
        sha256=digest,
        bytes=path.stat().st_size,
        vertex_count=vertex_count,
        triangle_count=triangle_count,
        bounds_mm=bounds,
        geometry_sha256_0p0001mm=geometry_digest,
        object_xml=copy.deepcopy(obj),
    )


def _indent_xml(element: ET.Element, level: int = 0) -> None:
    space = "\n" + "  " * level
    if len(element):
        if not element.text or not element.text.strip():
            element.text = space + "  "
        for child in element:
            _indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = space
    if level and (not element.tail or not element.tail.strip()):
        element.tail = space


def _zip_write(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=CANONICAL_ZIP_TIMESTAMP)
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.compress_type = CANONICAL_ZIP_COMPRESSION
    info.flag_bits = 0
    info.volume = 0
    info.internal_attr = 0
    info.external_attr = CANONICAL_ZIP_MODE << 16
    info.extra = b""
    info.comment = b""
    archive.writestr(
        info,
        payload,
        compress_type=CANONICAL_ZIP_COMPRESSION,
        compresslevel=CANONICAL_ZIP_COMPRESSLEVEL,
    )


def _neutral_content_types() -> bytes:
    namespace = "http://schemas.openxmlformats.org/package/2006/content-types"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}Types")
    ET.SubElement(
        root,
        f"{{{namespace}}}Default",
        {
            "Extension": "rels",
            "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
        },
    )
    ET.SubElement(
        root,
        f"{{{namespace}}}Default",
        {
            "Extension": "model",
            "ContentType": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml",
        },
    )
    _indent_xml(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _neutral_relationships() -> bytes:
    namespace = "http://schemas.openxmlformats.org/package/2006/relationships"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}Relationships")
    ET.SubElement(
        root,
        f"{{{namespace}}}Relationship",
        {
            "Target": "/3D/3dmodel.model",
            "Id": "rel0",
            "Type": "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel",
        },
    )
    _indent_xml(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_qualification_source_3mf(
    path: Path, spec: ProjectSpec, sources: Sequence[MeshAudit]
) -> dict[str, Any]:
    """Merge exact source mesh XML while applying translation-only placement."""

    if tuple(source.source_name for source in sources) != spec.sources:
        raise BambuQualificationError(f"source order differs from project {spec.project_id}")
    if len(sources) != len(spec.translations_mm):
        raise BambuQualificationError(f"placement count differs for {spec.project_id}")
    ET.register_namespace("", NS_3MF)
    model = ET.Element(
        f"{{{NS_3MF}}}model",
        {"unit": "millimeter", f"{{{NS_XML}}}lang": "en-US"},
    )
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Title"}).text = spec.title
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Description"}).text = (
        "QUALIFICATION ONLY; UNSLICED; EXPERIMENTAL; UNRATED; NO GENERATED G-CODE"
    )
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Application"}).text = (
        "Story Corner r6 Bambu qualification source assembler"
    )
    resources = ET.SubElement(model, f"{{{NS_3MF}}}resources")
    materials = ET.SubElement(resources, f"{{{NS_3MF}}}basematerials", {"id": "1"})
    ET.SubElement(
        materials,
        f"{{{NS_3MF}}}base",
        {"name": "Black SUNLU PETG qualification candidate", "displaycolor": "#000000FF"},
    )
    build = ET.SubElement(model, f"{{{NS_3MF}}}build")
    placed_bounds: list[dict[str, Any]] = []
    for index, (source, translation) in enumerate(zip(sources, spec.translations_mm), start=2):
        obj = copy.deepcopy(source.object_xml)
        obj.attrib["id"] = str(index)
        obj.attrib["name"] = source.source_name
        obj.attrib["pid"] = "1"
        obj.attrib["pindex"] = "0"
        resources.append(obj)
        x, y, z = translation
        ET.SubElement(
            build,
            f"{{{NS_3MF}}}item",
            {
                "objectid": str(index),
                "transform": f"1 0 0 0 1 0 0 0 1 {x:.6f} {y:.6f} {z:.6f}",
            },
        )
        lower = tuple(source.bounds_mm[0][axis] + translation[axis] for axis in range(3))
        upper = tuple(source.bounds_mm[1][axis] + translation[axis] for axis in range(3))
        if any(lower[axis] < -1.0e-6 or upper[axis] > BED_SIZE_MM[axis] + 1.0e-6 for axis in range(3)):
            raise BambuQualificationError(
                f"saved placement exceeds A1 mini envelope in {spec.project_id}: {source.source_name}"
            )
        placed_bounds.append(
            {
                "source_name": source.source_name,
                "translation_mm": list(translation),
                "bounds_mm": [list(lower), list(upper)],
            }
        )
    _indent_xml(model)
    model_bytes = ET.tostring(model, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _zip_write(archive, "[Content_Types].xml", _neutral_content_types())
        _zip_write(archive, "_rels/.rels", _neutral_relationships())
        _zip_write(archive, "3D/3dmodel.model", model_bytes)
    return {"model_xml_sha256": _sha256_bytes(model_bytes), "placed_bounds": placed_bounds}


def _common_settings_expected() -> dict[str, Any]:
    return {
        "curr_bed_type": BED_TYPE,
        "printer_model": "Bambu Lab A1 mini",
        "printer_variant": "0.4",
        "nozzle_diameter": ["0.4"],
        "filament_type": ["PETG"],
        "filament_vendor": ["SUNLU"],
        "filament_colour": [FILAMENT_COLOUR],
        "nozzle_temperature_initial_layer": ["250"],
        "nozzle_temperature": ["245"],
        "textured_plate_temp_initial_layer": ["60"],
        "textured_plate_temp": ["60"],
        "filament_flow_ratio": ["0.94"],
        "filament_max_volumetric_speed": ["9"],
        "layer_height": "0.2",
        "wall_loops": "6",
        "sparse_infill_density": "25%",
        "sparse_infill_pattern": "grid",
        "top_shell_layers": "5",
        "bottom_shell_layers": "3",
        "fan_min_speed": ["10"],
        "fan_max_speed": ["30"],
        "overhang_fan_speed": ["90"],
    }


def _settings_expected(spec: ProjectSpec) -> dict[str, Any]:
    expected = _common_settings_expected()
    expected.update(spec.overrides)
    return expected


def build_bambu_command(
    executable: Path,
    source_3mf: Path,
    output_3mf: Path,
    machine_json: Path,
    process_json: Path,
    filament_json: Path,
) -> list[str]:
    """Return the fixed unsliced, no-rotate/no-scale local export command."""

    return [
        os.fspath(executable),
        "--debug",
        "2",
        "--arrange",
        "0",
        "--curr-bed-type",
        BED_TYPE,
        "--filament-colour=#000000",
        "--load-settings",
        f"{machine_json};{process_json}",
        "--load-filaments",
        os.fspath(filament_json),
        "--export-3mf",
        os.fspath(output_3mf),
        os.fspath(source_3mf),
    ]


def _run_bambu(command: Sequence[str], cwd: Path) -> None:
    environment = dict(os.environ)
    environment["LC_ALL"] = "C"
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()[-3000:]
        raise BambuQualificationError(
            f"Bambu Studio unsliced export failed ({result.returncode}): {detail}"
        )


def _toolpath_entry(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered.endswith((".gcode", ".gco", ".bgcode"))
        or ".gcode." in lowered
        or "/gcode/" in lowered
    )


_PRIVATE_BYTE_PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    ("absolute macOS user path", re.compile(rb"/" + rb"Users" + rb"/")),
    ("file URI", re.compile(rb"(?i)file:" + rb"//")),
    ("absolute Windows user path", re.compile(rb"(?i)[A-Z]:[\\/]Users[\\/]")),
    ("private key", re.compile(rb"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    (
        "email address",
        re.compile(rb"(?i)\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b"),
    ),
    (
        "credential/token assignment",
        re.compile(
            rb"(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|access[_-]?code|password|private[_-]?key|authorization)"
            rb"[^\r\n]{0,12}[=:]\s*[\"']?[A-Za-z0-9_./+\-=]{8,}"
        ),
    ),
)


def _privacy_scan_bytes(label: str, payload: bytes) -> None:
    for description, pattern in _PRIVATE_BYTE_PATTERNS:
        if pattern.search(payload):
            raise BambuQualificationError(f"privacy scan found {description} in {label}")


def _safe_zip_member(name: str) -> bool:
    normalized = name.replace("\\", "/")
    parts = normalized.split("/")
    return bool(name) and not (
        normalized.startswith("/")
        or re.match(r"(?i)^[a-z]:/", normalized)
        or any(part in {"", ".", ".."} for part in parts)
    )


def _audit_zip_container(archive: zipfile.ZipFile, label: str) -> list[str]:
    infos = archive.infolist()
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise BambuQualificationError(f"duplicate ZIP member in {label}")
    for info in infos:
        if not _safe_zip_member(info.filename):
            raise BambuQualificationError(f"unsafe ZIP member {info.filename!r} in {label}")
        if info.flag_bits & 0x1:
            raise BambuQualificationError(f"encrypted ZIP member {info.filename!r} in {label}")
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise BambuQualificationError(f"symlink ZIP member {info.filename!r} in {label}")
        payload = archive.read(info)
        _privacy_scan_bytes(f"{label}:{info.filename}", payload)
        if info.filename.lower().endswith(".rels"):
            relationships = ET.fromstring(payload)
            for relationship in relationships:
                target = relationship.attrib.get("Target", "")
                if relationship.attrib.get("TargetMode", "").lower() == "external" or re.match(
                    r"(?i)^(?:https?|file):", target
                ):
                    raise BambuQualificationError(
                        f"external package relationship in {label}:{info.filename}"
                    )
    return names


def _audit_canonical_zip_container(archive: zipfile.ZipFile, label: str) -> None:
    """Require the fixed ZIP header contract used for reproducible projects."""

    infos = archive.infolist()
    names = [info.filename for info in infos]
    if names != sorted(names):
        raise BambuQualificationError(f"noncanonical ZIP member order in {label}")
    if archive.comment:
        raise BambuQualificationError(f"noncanonical ZIP archive comment in {label}")
    for info in infos:
        if info.date_time != CANONICAL_ZIP_TIMESTAMP:
            raise BambuQualificationError(
                f"noncanonical ZIP timestamp for {info.filename!r} in {label}"
            )
        if info.compress_type != CANONICAL_ZIP_COMPRESSION:
            raise BambuQualificationError(
                f"noncanonical ZIP compression for {info.filename!r} in {label}"
            )
        if info.create_system != 3 or info.create_version != 20 or info.extract_version != 20:
            raise BambuQualificationError(
                f"noncanonical ZIP version fields for {info.filename!r} in {label}"
            )
        if info.external_attr != CANONICAL_ZIP_MODE << 16:
            raise BambuQualificationError(
                f"noncanonical ZIP mode for {info.filename!r} in {label}"
            )
        if info.internal_attr or info.extra or info.comment:
            raise BambuQualificationError(
                f"noncanonical ZIP member metadata for {info.filename!r} in {label}"
            )


def _zip_payload_set_sha256(entries: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in entries:
        encoded_name = name.encode("utf-8")
        digest.update(len(encoded_name).to_bytes(8, "big"))
        digest.update(encoded_name)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


def canonicalize_3mf_zip(path: Path) -> dict[str, Any]:
    """Rewrite a staged 3MF deterministically without changing member payloads."""

    if not path.is_file() or path.is_symlink():
        raise BambuQualificationError(f"cannot canonicalize non-file project: {path.name}")
    try:
        with zipfile.ZipFile(path) as source:
            bad_crc = source.testzip()
            if bad_crc is not None:
                raise BambuQualificationError(
                    f"bad ZIP CRC for {bad_crc!r} in {path.name}"
                )
            _audit_zip_container(source, path.name)
            original_entries = sorted(
                ((info.filename, source.read(info)) for info in source.infolist()),
                key=lambda item: item[0],
            )
    except zipfile.BadZipFile as exc:
        raise BambuQualificationError(f"invalid ZIP container: {path.name}") from exc

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.canonical-", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=CANONICAL_ZIP_COMPRESSION,
            compresslevel=CANONICAL_ZIP_COMPRESSLEVEL,
        ) as destination:
            for name, payload in original_entries:
                _zip_write(destination, name, payload)
        with zipfile.ZipFile(temporary) as rebuilt:
            bad_crc = rebuilt.testzip()
            if bad_crc is not None:
                raise BambuQualificationError(
                    f"canonical ZIP has bad CRC for {bad_crc!r} in {path.name}"
                )
            _audit_zip_container(rebuilt, path.name)
            _audit_canonical_zip_container(rebuilt, path.name)
            rebuilt_entries = [
                (info.filename, rebuilt.read(info)) for info in rebuilt.infolist()
            ]
        if rebuilt_entries != original_entries:
            raise BambuQualificationError(
                f"ZIP canonicalization changed a member payload in {path.name}"
            )
        os.replace(temporary, path)
    except zipfile.BadZipFile as exc:
        raise BambuQualificationError(
            f"invalid canonical ZIP container: {path.name}"
        ) from exc
    finally:
        temporary.unlink(missing_ok=True)

    return {
        "member_count": len(original_entries),
        "member_order": "UTF-8 bytewise filename sort",
        "member_payload_set_sha256": _zip_payload_set_sha256(original_entries),
        "timestamp": "1980-01-01T00:00:00",
        "mode": "0100644",
        "compression": f"deflate level {CANONICAL_ZIP_COMPRESSLEVEL}",
        "payloads_preserved_exactly": True,
    }


_SENSITIVE_METADATA_KEYS = (
    "account",
    "email",
    "device_id",
    "device_serial",
    "serial_number",
    "cloud",
    "user_id",
    "userid",
    "user_name",
    "username",
    "access_code",
    "access_token",
    "refresh_token",
    "api_key",
    "password",
    "private_key",
)


def _nonempty(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def _audit_json_metadata_privacy(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower().replace("-", "_")
            if any(token in lowered for token in _SENSITIVE_METADATA_KEYS) and _nonempty(child):
                raise BambuQualificationError(f"private account/device metadata at {path}.{key}")
            if "source_path" in lowered and _nonempty(child):
                raise BambuQualificationError(f"source-path metadata at {path}.{key}")
            _audit_json_metadata_privacy(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _audit_json_metadata_privacy(child, f"{path}[{index}]")


def _audit_xml_metadata_privacy(root: ET.Element, label: str) -> None:
    for node in root.iter():
        key = node.attrib.get("key") or node.attrib.get("name") or ""
        value = node.attrib.get("value")
        if value is None:
            value = node.text or ""
        lowered = key.lower().replace("-", "_")
        if any(token in lowered for token in _SENSITIVE_METADATA_KEYS) and value.strip():
            raise BambuQualificationError(f"private account/device metadata in {label}:{key}")
        if "source_path" in lowered and value.strip():
            raise BambuQualificationError(f"source-path metadata in {label}:{key}")
        if lowered == "source_file" and value.strip():
            source_value = value.strip()
            if Path(source_value).name != source_value or "\\" in source_value:
                raise BambuQualificationError(f"non-basename source_file metadata in {label}")


def _object_name_map(model_settings: bytes) -> dict[str, str]:
    root = ET.fromstring(model_settings)
    result: dict[str, str] = {}
    for obj in root.findall("object"):
        object_id = obj.attrib.get("id")
        if object_id is None:
            continue
        for metadata in obj.findall("metadata"):
            if metadata.attrib.get("key") == "name":
                result[object_id] = metadata.attrib.get("value", "")
                break
    return result


def _external_path(component: ET.Element) -> str | None:
    return component.attrib.get(f"{{{NS_PRODUCTION}}}path") or component.attrib.get("path")


def _built_meshes(
    archive: zipfile.ZipFile, root: ET.Element
) -> list[tuple[str, ET.Element, tuple[float, float, float]]]:
    namespace = {"m": NS_3MF}
    objects = {
        node.attrib["id"]: node
        for node in root.findall("m:resources/m:object", namespace)
        if "id" in node.attrib
    }
    names = _object_name_map(archive.read("Metadata/model_settings.config"))
    records: list[tuple[str, ET.Element, tuple[float, float, float]]] = []
    for build in root.findall("m:build/m:item", namespace):
        object_id = build.attrib.get("objectid")
        obj = objects.get(object_id or "")
        if obj is None:
            raise BambuQualificationError("Bambu project build references missing object")
        build_transform = _parse_transform(build.attrib.get("transform"))
        if not _identity_linear(build_transform, tolerance=2.0e-6):
            raise BambuQualificationError("Bambu export rotated or scaled a saved object")
        total = _translation(build_transform)
        mesh = obj.find("m:mesh", namespace)
        if mesh is None:
            components = obj.findall("m:components/m:component", namespace)
            if len(components) != 1:
                raise BambuQualificationError("Bambu object is not one exact mesh/component")
            component = components[0]
            component_transform = _parse_transform(component.attrib.get("transform"))
            if not _identity_linear(component_transform, tolerance=2.0e-6):
                raise BambuQualificationError("Bambu component rotated or scaled saved geometry")
            component_translation = _translation(component_transform)
            total = tuple(total[axis] + component_translation[axis] for axis in range(3))
            external_path = _external_path(component)
            if external_path:
                member = external_path.lstrip("/")
                external_root = ET.fromstring(archive.read(member))
                external_objects = {
                    node.attrib["id"]: node
                    for node in external_root.findall("m:resources/m:object", namespace)
                    if "id" in node.attrib
                }
                external_obj = external_objects.get(component.attrib.get("objectid", ""))
                mesh = (
                    external_obj.find("m:mesh", namespace)
                    if external_obj is not None
                    else None
                )
            else:
                source_obj = objects.get(component.attrib.get("objectid", ""))
                mesh = source_obj.find("m:mesh", namespace) if source_obj is not None else None
        if mesh is None:
            raise BambuQualificationError("Bambu project component does not resolve to a mesh")
        records.append((names.get(object_id or "", obj.attrib.get("name", "")), mesh, total))
    return records


def validate_bambu_project(
    path: Path, spec: ProjectSpec, source_audits: Sequence[MeshAudit]
) -> dict[str, Any]:
    """Audit native project metadata, exact meshes, settings, and no toolpath."""

    with zipfile.ZipFile(path) as archive:
        bad_crc = archive.testzip()
        names = _audit_zip_container(archive, path.name)
        _audit_canonical_zip_container(archive, path.name)
        required = {
            "3D/3dmodel.model",
            "Metadata/project_settings.config",
            "Metadata/model_settings.config",
            "Metadata/slice_info.config",
        }
        if bad_crc is not None or not required <= set(names):
            raise BambuQualificationError(f"invalid Bambu-native project container: {path.name}")
        toolpaths = sorted(name for name in names if _toolpath_entry(name))
        if toolpaths:
            raise BambuQualificationError(f"unsliced project contains toolpath files: {toolpaths}")
        settings = json.loads(archive.read("Metadata/project_settings.config"))
        _audit_json_metadata_privacy(settings)
        expected = _settings_expected(spec)
        mismatches = {
            key: {"expected": value, "observed": settings.get(key)}
            for key, value in expected.items()
            if settings.get(key) != value
        }
        if mismatches:
            raise BambuQualificationError(
                f"embedded Bambu settings differ in {path.name}: {mismatches}"
            )
        root = ET.fromstring(archive.read("3D/3dmodel.model"))
        _audit_xml_metadata_privacy(root, "3D/3dmodel.model")
        namespace = {"m": NS_3MF}
        application = root.find("m:metadata[@name='Application']", namespace)
        if application is None or not (application.text or "").startswith("BambuStudio-"):
            raise BambuQualificationError(f"project lacks BambuStudio application metadata: {path.name}")
        model_settings = ET.fromstring(archive.read("Metadata/model_settings.config"))
        _audit_xml_metadata_privacy(model_settings, "Metadata/model_settings.config")
        nonempty_gcode_refs = [
            node.attrib.get("value")
            for node in model_settings.findall(".//metadata")
            if node.attrib.get("key") == "gcode_file" and node.attrib.get("value")
        ]
        if nonempty_gcode_refs:
            raise BambuQualificationError(f"unsliced project references G-code: {nonempty_gcode_refs}")
        slice_info = ET.fromstring(archive.read("Metadata/slice_info.config"))
        _audit_xml_metadata_privacy(slice_info, "Metadata/slice_info.config")
        if slice_info.findall(".//plate"):
            raise BambuQualificationError("unsliced project unexpectedly has slice plate records")
        built_meshes = _built_meshes(archive, root)

    expected_by_digest = {
        source.geometry_sha256_0p0001mm: source for source in source_audits
    }
    if len(expected_by_digest) != len(source_audits) or len(built_meshes) != len(source_audits):
        raise BambuQualificationError(f"project object count differs in {path.name}")
    observed_records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for object_name, mesh, translation in built_meshes:
        vertex_count, triangle_count, local_bounds, digest = _mesh_evidence(mesh)
        source = expected_by_digest.get(digest)
        if source is None or digest in seen:
            raise BambuQualificationError(f"project has changed/unplanned mesh geometry: {path.name}")
        seen.add(digest)
        if vertex_count != source.vertex_count or triangle_count != source.triangle_count:
            raise BambuQualificationError(f"project mesh topology differs: {source.source_name}")
        bounds = [
            [local_bounds[0][axis] + translation[axis] for axis in range(3)],
            [local_bounds[1][axis] + translation[axis] for axis in range(3)],
        ]
        if any(
            bounds[0][axis] < -1.0e-4
            or bounds[1][axis] > BED_SIZE_MM[axis] + 1.0e-4
            for axis in range(3)
        ):
            raise BambuQualificationError(
                f"Bambu project exceeds 180 mm envelope: {source.source_name} {bounds}"
            )
        observed_records.append(
            {
                "source_name": source.source_name,
                "bambu_object_name": object_name,
                "geometry_sha256_0p0001mm": digest,
                "bounds_mm": bounds,
                "saved_orientation_preserved": True,
                "scaling_applied": False,
            }
        )
    if seen != set(expected_by_digest):
        raise BambuQualificationError(f"Bambu project omits an exact source mesh: {path.name}")
    return {
        "filename": path.name,
        "sha256": _sha256_file(path),
        "bytes": path.stat().st_size,
        "bambu_native": True,
        "unsliced": True,
        "embedded_toolpath_file_count": 0,
        "generated_gcode_present": False,
        "settings": expected,
        "objects": observed_records,
        "all_objects_inside_180x180x180_mm": True,
        "saved_orientation_preserved": True,
        "scaling_applied": False,
    }


def repository_anchor(r6_root: Path) -> Path:
    """Return the repository/publication root that owns this relocated helper."""

    root = r6_root.resolve(strict=True)
    if root.name == "r6" and root.parent.name == "development":
        return root.parents[1]
    return root


def validate_output_path(r6_root: Path, output: Path) -> Path:
    """Require a fresh sibling of the development repo or publication root."""

    anchor = repository_anchor(r6_root)
    parent = output.expanduser().absolute().parent.resolve(strict=True)
    destination = parent / output.name
    if not destination.name or destination.name in {".", ".."}:
        raise BambuQualificationError("output must name a new directory")
    if parent != anchor.parent.resolve(strict=True):
        raise BambuQualificationError(
            "output must be a new sibling of the development repository or "
            f"flattened publication root: expected parent {anchor.parent}"
        )
    if os.path.lexists(destination):
        raise FileExistsError(f"refusing existing qualification output: {destination}")
    return destination


def _profile_chain_records(
    root: Path, chains: Mapping[str, Sequence[ProfileNode]]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for profile_type, nodes in chains.items():
        result[profile_type] = [
            {
                "name": node.name,
                "type": node.profile_type,
                "path": node.path.relative_to(root).as_posix(),
                "sha256": _sha256_file(node.path),
                "bytes": node.path.stat().st_size,
            }
            for node in nodes
        ]
    return result


def _bambu_application_record(executable: Path) -> dict[str, Any]:
    executable = executable.resolve(strict=True)
    info_path = executable.parents[1] / "Info.plist"
    version = None
    if info_path.is_file():
        with info_path.open("rb") as stream:
            info = plistlib.load(stream)
        version = info.get("CFBundleShortVersionString")
    if not isinstance(version, str) or not version:
        raise BambuQualificationError(f"cannot determine Bambu Studio version from {info_path}")
    return {
        "version": version,
        "bundle_relative_executable": "BambuStudio.app/Contents/MacOS/BambuStudio",
        "executable_sha256": _sha256_file(executable),
        "cli_export_mode": "UNSLICED --export-3mf; --slice deliberately absent",
    }


def _readme_text(projects: Sequence[Mapping[str, Any]]) -> str:
    order = "\n".join(
        f"{index}. `{project['filename']}` — {project['title']}"
        for index, project in enumerate(projects, start=1)
    )
    return f"""# Story Corner r6 — Bambu Studio qualification projects

These files are **qualification-only, experimental, unrated, and unsliced**.
They contain no generated G-code and are not a full shelf or production release.

## Fixed local setup

- Printer: Bambu Lab A1 mini, 180 × 180 × 180 mm build volume
- Nozzle: 0.4 mm
- Plate: Textured PEI Plate
- Material candidate: black SUNLU PETG only (`#000000`)
- Nozzle: 250 °C first layer, 245 °C other layers
- Bed: 60 °C first and other layers
- Flow ratio: 0.94
- Maximum volumetric speed: 9 mm³/s
- Layer height: 0.20 mm
- Walls: 6
- Sparse infill: 25%

The PETG product/lot and these support/brim mappings are still qualification
candidates. Do not substitute PLA, PETG-CF, another polymer, another PETG
product, or another material lot and carry test results forward.

## Project order

{order}

Open each `.3mf` **as a project** in Bambu Studio. Preserve every saved
orientation and use 100% scale. Do not auto-orient, rotate to reduce supports,
or scale. Review all support and brim contacts/removal paths before slicing.
Slice locally in Bambu Studio; this bundle neither slices nor sends anything to
a printer or cloud service.

Before printing, dry the confirmed SUNLU PETG at 60–65 °C for 6 hours, then keep
it dry during the trial. Wash the Textured PEI plate with detergent and water,
rinse, dry, and avoid acetone. Inspect the 0.4 mm nozzle. Let the plate cool to
35 °C or below before removal. Run the A1 mini calibration and Bambu Studio's
manual Flow Rate calibration, including both coarse and fine passes. Record
printer serial, Bambu Studio version, exported profile digest, filament
product/lot/drying record, support edits, sliced time/mass, and the resulting
project digest.

The solid/no-hole wall-screw placeholder is deliberately absent. It cannot
qualify wall bearing because the actual metal screw shank, head or washer,
embedment, driver envelope, and corresponding bore are not yet selected.

Passing these prints does not qualify physical installation, overhead use,
production release, or any load rating. Follow the r6 test protocol and use a
guarded bench or low sacrificial mockup.
"""


def _audit_bundle_privacy_and_containers(root: Path, relative_files: Iterable[str]) -> None:
    for relative in sorted(relative_files):
        path = root / relative
        if path.suffix.lower() == ".3mf":
            with zipfile.ZipFile(path) as archive:
                _audit_zip_container(archive, relative)
        else:
            _privacy_scan_bytes(relative, path.read_bytes())


Runner = Callable[[Sequence[str], Path], None]


def build_qualification_projects(
    *,
    r6_root: Path,
    output: Path,
    profile_root: Path,
    bambu_executable: Path,
    runner: Runner | None = None,
    committer: Callable[[Path, Path], None] | None = None,
) -> dict[str, Any]:
    """Build, audit, and exclusively publish the four fixed projects."""

    r6_root = r6_root.resolve(strict=True)
    destination = validate_output_path(r6_root, output)
    profile_root = profile_root.resolve(strict=True)
    bambu_executable = bambu_executable.resolve(strict=True)
    if not bambu_executable.is_file():
        raise BambuQualificationError(f"Bambu Studio executable is missing: {bambu_executable}")

    catalog = ProfileCatalog(profile_root)
    machine, base_process, filament, chains = qualification_profiles(catalog)
    release_manifest = r6_root / "generated" / "manifest.json"
    source_dir = r6_root / "generated" / "individual_model_only_3mf"
    artifact_records = _manifest_artifacts(release_manifest)
    selected_names = tuple(name for spec in PROJECT_SPECS for name in spec.sources)
    if len(selected_names) != len(set(selected_names)):
        raise BambuQualificationError("qualification project sources must be unique")
    if EXCLUDED_SOURCE in selected_names:
        raise BambuQualificationError("solid screw placeholder must remain excluded")
    source_audits = {
        name: audit_individual_source(source_dir, name, artifact_records)
        for name in selected_names
    }

    stage = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.unpublished-", dir=destination.parent)
    )
    work = stage / ".builder_work"
    work.mkdir()
    run = runner or _run_bambu
    commit = committer or _exclusive_atomic_rename
    committed = False
    try:
        machine_path = work / "machine_full.json"
        filament_path = work / "filament_full.json"
        machine_path.write_bytes(_json_bytes(machine))
        filament_path.write_bytes(_json_bytes(filament))
        project_reports: list[dict[str, Any]] = []
        for index, spec in enumerate(PROJECT_SPECS, start=1):
            process = copy.deepcopy(base_process)
            process.update(spec.overrides)
            process["name"] = f"Story Corner r6 QUALIFICATION ONLY — {spec.project_id}"
            process["from"] = "User"
            process_path = work / f"process_{index:02d}.json"
            process_path.write_bytes(_json_bytes(process))
            merged_source = work / f"source_{index:02d}.3mf"
            inputs = [source_audits[name] for name in spec.sources]
            source_assembly = write_qualification_source_3mf(merged_source, spec, inputs)
            project_path = stage / spec.filename
            command = build_bambu_command(
                bambu_executable,
                merged_source,
                project_path,
                machine_path,
                process_path,
                filament_path,
            )
            if any(flag in command for flag in ("--slice", "--orient", "--scale", "--rotate")):
                raise BambuQualificationError("unsafe slicing/orientation flag entered command")
            run(command, work)
            if not project_path.is_file() or project_path.is_symlink():
                raise BambuQualificationError(f"Bambu Studio did not create {spec.filename}")
            archive_canonicalization = canonicalize_3mf_zip(project_path)
            audit = validate_bambu_project(project_path, spec, inputs)
            project_reports.append(
                {
                    "order": index,
                    "project_id": spec.project_id,
                    "title": spec.title,
                    "filename": spec.filename,
                    "qualification_only": True,
                    "physical_installation_qualified": False,
                    "production_release_eligible": False,
                    "support_review": spec.support_review,
                    "process_overrides": spec.overrides,
                    "archive_canonicalization": archive_canonicalization,
                    "source_assembly": source_assembly,
                    "source_files": [
                        {
                            "source_name": item.source_name,
                            "path": item.path.relative_to(r6_root / "generated").as_posix(),
                            "sha256": item.sha256,
                            "bytes": item.bytes,
                            "geometry_sha256_0p0001mm": item.geometry_sha256_0p0001mm,
                        }
                        for item in inputs
                    ],
                    "audit": audit,
                }
            )

        shutil.rmtree(work)
        readme_path = stage / README_NAME
        readme_path.write_text(_readme_text(project_reports), encoding="utf-8")
        expected_files = {spec.filename for spec in PROJECT_SPECS} | {README_NAME}
        actual_files = {
            path.relative_to(stage).as_posix()
            for path in stage.rglob("*")
            if path.is_file()
        }
        if actual_files != expected_files:
            raise BambuQualificationError(
                f"unexpected derived output before manifest: {sorted(actual_files ^ expected_files)}"
            )
        file_records = [
            {
                "path": relative,
                "sha256": _sha256_file(stage / relative),
                "bytes": (stage / relative).stat().st_size,
            }
            for relative in sorted(expected_files)
        ]
        manifest: dict[str, Any] = {
            "schema": "story-corner-r6-bambu-qualification-projects-v1",
            "qualification_only": True,
            "unsliced": True,
            "generated_gcode_present": False,
            "embedded_toolpath_file_count": 0,
            "remote_send_performed": False,
            "full_shelf_project_present": False,
            "physical_installation_qualified": False,
            "production_release_eligible": False,
            "tested_load_rating_exists": False,
            "local_bambu_studio_review_and_slice_required": True,
            "printer_contract": {
                "model": "Bambu Lab A1 mini",
                "build_volume_mm": list(BED_SIZE_MM),
                "nozzle_diameter_mm": 0.4,
                "build_plate": BED_TYPE,
            },
            "material_contract": {
                "profile": FILAMENT_PROFILE,
                "vendor": "SUNLU",
                "type": "PETG",
                "colour": "black",
                "colour_hex": FILAMENT_COLOUR,
                "product_lot_and_drying_record_required": True,
            },
            "required_common_settings": _common_settings_expected(),
            "support_and_brim": "project-specific qualification candidates; see each project",
            "bambu_studio": _bambu_application_record(bambu_executable),
            "builder_source": {
                "path_after_publication_relocation": "build_bambu_qualification_projects.py",
                "sha256": _sha256_file(Path(__file__).resolve()),
            },
            "profile_sources": _profile_chain_records(profile_root, chains),
            "flattened_profile_sha256": {
                "machine": _sha256_bytes(_json_bytes(machine)),
                "base_process_before_project_overrides": _sha256_bytes(
                    _json_bytes(base_process)
                ),
                "filament": _sha256_bytes(_json_bytes(filament)),
            },
            "release_source_manifest": {
                "path": "generated/manifest.json",
                "sha256": _sha256_file(release_manifest),
            },
            "projects": project_reports,
            "deliberate_exclusions": [
                {
                    "source_name": EXCLUDED_SOURCE,
                    "included": False,
                    "reason": EXCLUDED_REASON,
                }
            ],
            "files": file_records,
            "file_count_excluding_manifest": len(file_records),
        }
        (stage / MANIFEST_NAME).write_bytes(_json_bytes(manifest))
        final_files = {
            path.relative_to(stage).as_posix()
            for path in stage.rglob("*")
            if path.is_file()
        }
        if final_files != expected_files | {MANIFEST_NAME}:
            raise BambuQualificationError("final qualification output file set drift")
        _audit_bundle_privacy_and_containers(stage, final_files)
        commit(stage, destination)
        committed = True
        return manifest
    finally:
        if not committed and stage.parent == destination.parent and stage.name.startswith(
            f".{destination.name}.unpublished-"
        ):
            shutil.rmtree(stage, ignore_errors=True)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build four fixed, unsliced Bambu Studio r6 qualification projects; "
            "the destination must be a new sibling of the repo/publication root."
        )
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile-root", type=Path, default=default_profile_root())
    parser.add_argument("--bambu-studio", type=Path, default=default_bambu_executable())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    r6_root = discover_r6_root(Path(__file__))
    manifest = build_qualification_projects(
        r6_root=r6_root,
        output=args.output,
        profile_root=args.profile_root,
        bambu_executable=args.bambu_studio,
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": os.fspath(args.output.absolute()),
                "project_count": len(manifest["projects"]),
                "unsliced": True,
                "generated_gcode_present": False,
                "qualification_only": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
