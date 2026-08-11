#!/usr/bin/env python3
"""Strict neutral-3MF and exact-package validation for Story Corner r6."""

from __future__ import annotations

import hashlib
import json
import math
import re
import zipfile
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping
from xml.etree import ElementTree as ET

import numpy as np
import trimesh

from package_layout import (
    SAFETY_DESCRIPTION,
    PackageMeshSourceAudit,
    PackagePlan,
    PlacedPackageInstance,
    bounds_overlap_in_xy,
    forbidden_package_term,
    mesh_source_audit_checks,
)


NS_3MF = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
NS = {"m": NS_3MF, "r": NS_RELS, "t": NS_TYPES}

REQUIRED_ENTRY_ORDER: tuple[str, ...] = (
    "[Content_Types].xml",
    "_rels/.rels",
    "3D/3dmodel.model",
)
REQUIRED_ENTRIES = set(REQUIRED_ENTRY_ORDER)
REQUIRED_METADATA_ORDER: tuple[str, ...] = ("Title", "Description", "Application")
ALLOWED_APPLICATIONS: frozenset[str] = frozenset(
    {
        "Story Corner deterministic neutral model writer",
        "Story Corner deterministic neutral instanced model writer",
    }
)
MODEL_RELATIONSHIP_TYPE = (
    "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"
)
MODEL_CONTENT_TYPE = "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"
RELATIONSHIP_CONTENT_TYPE = "application/vnd.openxmlformats-package.relationships+xml"
_CANONICAL_TRANSFORM = re.compile(
    r"^1 0 0 0 1 0 0 0 1 -?\d+\.\d{6} -?\d+\.\d{6} -?\d+\.\d{6}$"
)
COMMON_SERIALIZED_GEOMETRY_GRID_DECIMALS = 3


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_serialized_triangle_digest(
    vertices: np.ndarray,
    faces: np.ndarray,
    *,
    decimals: int = COMMON_SERIALIZED_GEOMETRY_GRID_DECIMALS,
) -> str:
    """Hash an orientation/index-order-independent quantized triangle set.

    STL float32 decoding and 3MF decimal decoding can differ in
    their least significant binary bits, so this digest compares the exact
    common 0.001 mm audit grid rather than implementation-specific
    floating-point payloads.  That grid is 350 times finer than the nominal
    0.35 mm fit clearance and is coupled to exact triangle-count, bounds, and
    closed-one-body checks.
    """

    vertex_array = np.asarray(vertices, dtype=np.float64)
    face_array = np.asarray(faces, dtype=np.int64)
    if (
        vertex_array.ndim != 2
        or vertex_array.shape[1:] != (3,)
        or face_array.ndim != 2
        or face_array.shape[1:] != (3,)
        or len(vertex_array) == 0
        or len(face_array) == 0
        or np.any(~np.isfinite(vertex_array))
        or np.any(face_array < 0)
        or np.any(face_array >= len(vertex_array))
    ):
        raise ValueError("Serialized geometry digest needs finite indexed triangles")
    scale = 10**decimals
    quantized = np.rint(vertex_array * scale).astype(np.int64)
    canonical_triangles = [
        tuple(sorted(tuple(int(value) for value in point) for point in quantized[face]))
        for face in face_array
    ]
    canonical_triangles.sort()
    payload = json.dumps(
        canonical_triangles,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    return _sha256(payload)


def serialized_mesh_geometry_evidence(
    vertices: np.ndarray,
    faces: np.ndarray,
) -> dict[str, Any]:
    """Return the common closed-solid evidence used for STL/3MF pairing."""

    vertex_array = np.asarray(vertices, dtype=np.float64)
    face_array = np.asarray(faces, dtype=np.int64)
    mesh = trimesh.Trimesh(vertices=vertex_array, faces=face_array, process=False)
    triangles = vertex_array[face_array]
    cross = np.cross(
        triangles[:, 1] - triangles[:, 0],
        triangles[:, 2] - triangles[:, 0],
    )
    zero_area = int(np.count_nonzero(np.einsum("ij,ij->i", cross, cross) <= 0.0))
    return {
        "triangle_count": int(len(face_array)),
        "zero_area_triangle_count": zero_area,
        "bounds_mm": np.round(np.asarray(mesh.bounds, dtype=float), 4).tolist(),
        "absolute_volume_mm3": round(abs(float(mesh.volume)), 6),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "positive_volume": bool(mesh.is_volume and float(mesh.volume) > 0.0),
        "body_count": int(len(mesh.split(only_watertight=False))),
        "canonical_geometry_grid_mm": 0.001,
        "canonical_triangle_digest_common_grid": (
            canonical_serialized_triangle_digest(vertex_array, face_array)
        ),
    }


def inspect_serialized_stl_geometry(path: Path) -> dict[str, Any]:
    """Inspect one emitted STL with the same evidence schema used for 3MF."""

    raw = trimesh.load_mesh(path, file_type="stl", force="mesh", process=False)
    evidence = serialized_mesh_geometry_evidence(raw.vertices, raw.faces)
    processed = trimesh.load_mesh(path, file_type="stl", force="mesh", process=True)
    processed_triangles = np.asarray(processed.vertices, dtype=float)[
        np.asarray(processed.faces, dtype=np.int64)
    ]
    processed_cross = np.cross(
        processed_triangles[:, 1] - processed_triangles[:, 0],
        processed_triangles[:, 2] - processed_triangles[:, 0],
    )
    evidence.update(
        {
            "path": path.name,
            "ordinary_reload_zero_area_triangle_count": int(
                np.count_nonzero(
                    np.einsum("ij,ij->i", processed_cross, processed_cross) <= 0.0
                )
            ),
            "ordinary_reload_watertight": bool(processed.is_watertight),
            "ordinary_reload_winding_consistent": bool(
                processed.is_winding_consistent
            ),
            "ordinary_reload_is_volume": bool(processed.is_volume),
            "ordinary_reload_body_count": int(
                len(processed.split(only_watertight=False))
            ),
        }
    )
    evidence["serialized_geometry_audit_passed"] = bool(
        evidence["zero_area_triangle_count"] == 0
        and evidence["ordinary_reload_zero_area_triangle_count"] == 0
        and evidence["ordinary_reload_watertight"]
        and evidence["ordinary_reload_winding_consistent"]
        and evidence["ordinary_reload_is_volume"]
        and evidence["ordinary_reload_body_count"] == 1
    )
    return evidence


def _metadata_entries(root: ET.Element) -> list[tuple[str, str]]:
    return [
        (node.attrib.get("name", ""), node.text or "")
        for node in root.findall("m:metadata", NS)
    ]


def _parse_translation(value: str | None) -> tuple[float, float, float] | None:
    if value is None:
        return None
    tokens = value.split()
    if len(tokens) != 12:
        return None
    try:
        numbers = tuple(float(token) for token in tokens)
    except ValueError:
        return None
    if not all(math.isfinite(number) for number in numbers):
        return None
    if numbers[:9] != (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0):
        return None
    return numbers[9], numbers[10], numbers[11]


def _core_elements_only(root: ET.Element) -> bool:
    return all(
        isinstance(node.tag, str) and node.tag.startswith(f"{{{NS_3MF}}}")
        for node in root.iter()
    )


def _model_structure_exact(
    root: ET.Element,
    mesh_objects: list[ET.Element],
    component_objects: list[ET.Element],
    build_items: list[ET.Element],
) -> bool:
    """Accept only the small neutral-core tree emitted by ``model_io``."""

    xml_lang = "{http://www.w3.org/XML/1998/namespace}lang"
    if root.tag != f"{{{NS_3MF}}}model" or root.attrib != {
        "unit": "millimeter",
        xml_lang: "en-US",
    }:
        return False
    children = list(root)
    if [node.tag for node in children] != [
        f"{{{NS_3MF}}}metadata",
        f"{{{NS_3MF}}}metadata",
        f"{{{NS_3MF}}}metadata",
        f"{{{NS_3MF}}}resources",
        f"{{{NS_3MF}}}build",
    ]:
        return False
    metadata_nodes = children[:3]
    if any(
        set(node.attrib) != {"name"} or len(node) != 0 for node in metadata_nodes
    ):
        return False
    resources = children[3]
    build = children[4]
    if resources.attrib or build.attrib or list(build) != build_items:
        return False
    resource_children = list(resources)
    if not resource_children or resource_children[0].tag != f"{{{NS_3MF}}}basematerials":
        return False
    material = resource_children[0]
    if set(material.attrib) != {"id"} or len(material) != 1:
        return False
    base = list(material)[0]
    if (
        base.tag != f"{{{NS_3MF}}}base"
        or set(base.attrib) != {"name", "displaycolor"}
        or len(base) != 0
    ):
        return False
    for node in mesh_objects:
        if (
            set(node.attrib) != {"id", "type", "pid", "pindex", "name"}
            or node.attrib.get("type") != "model"
            or node.attrib.get("pid") != "1"
            or node.attrib.get("pindex") != "0"
        ):
            return False
        mesh_children = list(node)
        if len(mesh_children) != 1 or mesh_children[0].tag != f"{{{NS_3MF}}}mesh":
            return False
        mesh = mesh_children[0]
        if mesh.attrib or [child.tag for child in mesh] != [
            f"{{{NS_3MF}}}vertices",
            f"{{{NS_3MF}}}triangles",
        ]:
            return False
        vertices, triangles = list(mesh)
        if vertices.attrib or triangles.attrib:
            return False
        if any(
            child.tag != f"{{{NS_3MF}}}vertex"
            or set(child.attrib) != {"x", "y", "z"}
            or len(child) != 0
            for child in vertices
        ):
            return False
        if any(
            child.tag != f"{{{NS_3MF}}}triangle"
            or set(child.attrib) != {"v1", "v2", "v3"}
            or len(child) != 0
            for child in triangles
        ):
            return False
    for node in component_objects:
        if (
            set(node.attrib) != {"id", "type", "name"}
            or node.attrib.get("type") != "model"
        ):
            return False
        children = list(node)
        if len(children) != 1 or children[0].tag != f"{{{NS_3MF}}}components":
            return False
        components = children[0]
        if components.attrib or any(
            child.tag != f"{{{NS_3MF}}}component"
            or set(child.attrib) != {"objectid"}
            or len(child) != 0
            for child in components
        ):
            return False
    return all(
        node.tag == f"{{{NS_3MF}}}item" and len(node) == 0 for node in build_items
    )


def _content_types_exact(root: ET.Element) -> bool:
    if root.tag != f"{{{NS_TYPES}}}Types" or root.attrib:
        return False
    return [node.attrib for node in root] == [
        {"Extension": "rels", "ContentType": RELATIONSHIP_CONTENT_TYPE},
        {"Extension": "model", "ContentType": MODEL_CONTENT_TYPE},
    ] and all(node.tag == f"{{{NS_TYPES}}}Default" and len(node) == 0 for node in root)


def inspect_model_only_3mf(path: Path) -> dict[str, Any]:
    """Return strict integrity evidence for a simple or compact-instanced 3MF."""

    package_payload = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        bad_entry = archive.testzip()
        payloads = {
            name: archive.read(name)
            for name in REQUIRED_ENTRY_ORDER
            if name in names
        }
    name_set = set(names)
    model_payload = payloads.get("3D/3dmodel.model", b"")
    types_payload = payloads.get("[Content_Types].xml", b"")
    rels_payload = payloads.get("_rels/.rels", b"")
    root = ET.fromstring(model_payload) if model_payload else ET.Element("missing")
    types_root = ET.fromstring(types_payload) if types_payload else ET.Element("missing")
    rels_root = ET.fromstring(rels_payload) if rels_payload else ET.Element("missing")

    resources_node = root.find("m:resources", NS)
    resource_children = list(resources_node) if resources_node is not None else []
    resource_ids = [node.attrib.get("id") for node in resource_children]
    objects = root.findall("m:resources/m:object", NS)
    build_items = root.findall("m:build/m:item", NS)
    object_ids = [node.attrib.get("id") for node in objects]
    object_by_id = {node.attrib.get("id"): node for node in objects}
    object_names = [node.attrib.get("name") for node in objects]
    mesh_objects = [node for node in objects if node.find("m:mesh", NS) is not None]
    component_objects = [node for node in objects if node.find("m:components", NS) is not None]

    triangle_indices_valid = True
    mesh_payloads_nonempty = True
    serialized_mesh_geometry_records: list[dict[str, Any]] = []
    for node in mesh_objects:
        vertices = node.findall("m:mesh/m:vertices/m:vertex", NS)
        triangles = node.findall("m:mesh/m:triangles/m:triangle", NS)
        mesh_payloads_nonempty &= bool(vertices) and bool(triangles)
        for vertex in vertices:
            try:
                coordinates = [float(vertex.attrib[key]) for key in ("x", "y", "z")]
            except (KeyError, ValueError):
                mesh_payloads_nonempty = False
                continue
            mesh_payloads_nonempty &= all(math.isfinite(value) for value in coordinates)
        for triangle in triangles:
            try:
                indices = [int(triangle.attrib[key]) for key in ("v1", "v2", "v3")]
            except (KeyError, ValueError):
                triangle_indices_valid = False
                continue
            if not all(0 <= index < len(vertices) for index in indices):
                triangle_indices_valid = False
        if mesh_payloads_nonempty and triangle_indices_valid:
            try:
                coordinate_array = np.asarray(
                    [
                        [float(vertex.attrib[key]) for key in ("x", "y", "z")]
                        for vertex in vertices
                    ],
                    dtype=np.float64,
                )
                face_array = np.asarray(
                    [
                        [int(triangle.attrib[key]) for key in ("v1", "v2", "v3")]
                        for triangle in triangles
                    ],
                    dtype=np.int64,
                )
                serialized_mesh_geometry_records.append(
                    {
                        "name": node.attrib.get("name"),
                        **serialized_mesh_geometry_evidence(
                            coordinate_array,
                            face_array,
                        ),
                    }
                )
            except (KeyError, ValueError, IndexError):
                mesh_payloads_nonempty = False

    component_source_ids: list[str | None] = []
    component_shape_valid = True
    component_source_by_name: dict[str, str | None] = {}
    for node in component_objects:
        components = node.findall("m:components/m:component", NS)
        component_shape_valid &= (
            len(components) == 1
            and set(components[0].attrib) == {"objectid"}
            and set(node.find("m:components", NS).attrib) == set()
        )
        source_id = components[0].attrib.get("objectid") if len(components) == 1 else None
        component_source_ids.append(source_id)
        component_name = node.attrib.get("name")
        source = object_by_id.get(source_id)
        if component_name is not None:
            component_source_by_name[component_name] = (
                source.attrib.get("name") if source is not None else None
            )

    build_ids = [node.attrib.get("objectid") for node in build_items]
    build_counter = Counter(build_ids)
    source_counter = Counter(component_source_ids)
    mesh_ids = {node.attrib.get("id") for node in mesh_objects}
    component_ids = {node.attrib.get("id") for node in component_objects}
    built_ids = set(build_ids)
    build_names = [
        object_by_id[item].attrib.get("name") if item in object_by_id else None
        for item in build_ids
    ]
    build_translations = [_parse_translation(node.attrib.get("transform")) for node in build_items]

    metadata_entries = _metadata_entries(root)
    metadata = dict(metadata_entries)
    metadata_names = [name for name, _value in metadata_entries]
    applications = metadata.get("Application", "")

    type_defaults = {
        node.attrib.get("Extension"): node.attrib.get("ContentType")
        for node in types_root.findall("t:Default", NS)
    }
    relationships = rels_root.findall("r:Relationship", NS)
    exact_relationship = (
        rels_root.tag == f"{{{NS_RELS}}}Relationships"
        and not rels_root.attrib
        and len(relationships) == 1
        and relationships[0].attrib
        == {
            "Target": "/3D/3dmodel.model",
            "Id": "rel0",
            "Type": MODEL_RELATIONSHIP_TYPE,
        }
        and len(relationships[0]) == 0
        and list(rels_root) == relationships
    )
    basematerials = root.findall("m:resources/m:basematerials", NS)
    bases = root.findall("m:resources/m:basematerials/m:base", NS)
    exact_material_contract = (
        len(basematerials) == 1
        and basematerials[0].attrib == {"id": "1"}
        and len(bases) == 1
        and bases[0].attrib
        == {
            "name": "Black PETG (unconfirmed product/preset)",
            "displaycolor": "#111111FF",
        }
    )

    canonical_object_ids = object_ids == [str(index) for index in range(2, 2 + len(objects))]
    canonical_resource_order = bool(resource_children) and (
        resource_children[0].tag == f"{{{NS_3MF}}}basematerials"
        and all(node.tag == f"{{{NS_3MF}}}object" for node in resource_children[1:])
    )
    canonical_build_attributes = all(
        set(node.attrib) == {"objectid", "transform"}
        and bool(_CANONICAL_TRANSFORM.fullmatch(node.attrib.get("transform", "")))
        for node in build_items
    )

    checks = {
        "zip_crc_ok": bad_entry is None,
        "exact_neutral_entries_only": name_set == REQUIRED_ENTRIES and len(names) == 3,
        "neutral_entry_order_exact": tuple(names) == REQUIRED_ENTRY_ORDER,
        "content_types_exact": type_defaults
        == {"rels": RELATIONSHIP_CONTENT_TYPE, "model": MODEL_CONTENT_TYPE}
        and _content_types_exact(types_root),
        "single_internal_model_relationship_exact": exact_relationship,
        "millimeter_units": root.attrib.get("unit") == "millimeter",
        "core_model_namespace_only": _core_elements_only(root),
        "neutral_model_structure_exact": _model_structure_exact(
            root, mesh_objects, component_objects, build_items
        ),
        "metadata_fields_exact_and_unique": tuple(metadata_names) == REQUIRED_METADATA_ORDER,
        "title_present": bool(metadata.get("Title", "").strip()),
        "safety_metadata_exact": metadata.get("Description") == SAFETY_DESCRIPTION,
        "neutral_application_exact": applications in ALLOWED_APPLICATIONS,
        "no_printer_or_slicer_profile": (
            tuple(metadata_names) == REQUIRED_METADATA_ORDER
            and applications in ALLOWED_APPLICATIONS
            and name_set == REQUIRED_ENTRIES
        ),
        "resource_ids_present_and_unique_across_types": (
            all(resource_ids) and len(resource_ids) == len(set(resource_ids))
        ),
        "resource_ids_present_and_unique": (
            all(object_ids) and len(object_ids) == len(set(object_ids))
        ),
        "canonical_resource_id_sequence": canonical_object_ids,
        "canonical_resource_order": canonical_resource_order,
        "resource_names_present_and_unique": (
            all(name and name.strip() for name in object_names)
            and len(object_names) == len(set(object_names))
        ),
        "resource_object_kinds_valid": (
            bool(objects)
            and len(mesh_objects) + len(component_objects) == len(objects)
            and not (mesh_ids & component_ids)
        ),
        "black_petg_material_contract_exact": exact_material_contract,
        "mesh_payloads_nonempty": bool(mesh_objects) and mesh_payloads_nonempty,
        "triangle_indices_valid": triangle_indices_valid,
        "component_shape_valid": component_shape_valid,
        "component_sources_exist_and_are_meshes": (
            all(source_id in mesh_ids for source_id in component_source_ids)
            and all(source_id in object_by_id for source_id in component_source_ids)
        ),
        "build_references_exist": bool(build_items)
        and all(item in object_by_id for item in build_ids),
        "build_attributes_and_transforms_canonical": canonical_build_attributes,
        "build_transforms_finite_identity_plus_translation": (
            bool(build_items) and all(value is not None for value in build_translations)
        ),
        "every_build_object_referenced_exactly_once": (
            bool(build_items) and all(count == 1 for count in build_counter.values())
        ),
        "built_object_names_present_and_unique": (
            all(name and name.strip() for name in build_names)
            and len(build_names) == len(set(build_names))
        ),
        "every_component_object_is_built_once": all(
            build_counter[component_id] == 1 for component_id in component_ids
        ),
        "mesh_resources_are_used_once_or_shared_as_sources": all(
            (build_counter[mesh_id] == 1 and source_counter[mesh_id] == 0)
            or (build_counter[mesh_id] == 0 and source_counter[mesh_id] >= 1)
            for mesh_id in mesh_ids
        ),
        "no_component_source_is_directly_built": all(
            source_id not in built_ids for source_id in component_source_ids
        ),
        "contains_no_embedded_gcode": not any("gcode" in name.lower() for name in names),
        "no_forbidden_release_part_names": not any(
            forbidden_package_term(name or "") for name in object_names
        ),
    }
    # Compatibility alias for older report consumers; now intentionally exact.
    checks["safety_metadata_present"] = checks["safety_metadata_exact"]
    mesh_resource_names = [node.attrib.get("name") for node in mesh_objects]
    component_object_names = [node.attrib.get("name") for node in component_objects]
    return {
        "file": path.name,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "package_sha256": _sha256(package_payload),
        "model_xml_sha256": _sha256(model_payload),
        "metadata": metadata,
        "resource_object_count": len(objects),
        "resource_object_ids": object_ids,
        "mesh_family_count": len(mesh_objects),
        "mesh_resource_names": mesh_resource_names,
        "serialized_mesh_geometry_records": serialized_mesh_geometry_records,
        "component_object_count": len(component_objects),
        "component_object_names": component_object_names,
        "component_source_by_name": component_source_by_name,
        "build_object_count": len(build_items),
        "build_object_names": build_names,
        "build_translations_mm": build_translations,
        "unexpected_entries": sorted(name_set - REQUIRED_ENTRIES),
        "missing_entries": sorted(REQUIRED_ENTRIES - name_set),
    }


def _observed_inventory_sha256(
    plan: PackagePlan,
    report: dict[str, Any],
) -> str | None:
    expected_by_name = {item.logical_name: item for item in plan.instances}
    payload: list[dict[str, str | None]] = []
    for name in report["build_object_names"]:
        if not isinstance(name, str) or name not in expected_by_name:
            return None
        source_name = report["component_source_by_name"].get(name)
        if not isinstance(source_name, str) or not source_name.startswith("SOURCE__"):
            return None
        payload.append(
            {
                "logical_name": name,
                "mesh_family": source_name.removeprefix("SOURCE__"),
                "level": expected_by_name[name].level,
            }
        )
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _placed_contract_checks(
    plan: PackagePlan,
    placed_instances: Iterable[PlacedPackageInstance],
    report: dict[str, Any],
) -> dict[str, bool]:
    placed = tuple(placed_instances)
    expected_pairs = [(item.logical_name, item.mesh_family) for item in plan.instances]
    placed_pairs = [(item.logical_name, item.mesh_family) for item in placed]
    placed_names = [item.logical_name for item in placed]
    report_names = report["build_object_names"]
    observed_translations = report["build_translations_mm"]
    translations_match = len(placed) == len(observed_translations)
    if translations_match:
        for expected, observed in zip(placed, observed_translations):
            if observed is None or any(
                not math.isclose(left, right, rel_tol=0.0, abs_tol=5e-7)
                for left, right in zip(expected.translation_mm, observed)
            ):
                translations_match = False
                break
    placed_bounds_valid = all(
        all(math.isfinite(value) for bound in item.placed_bounds_mm for value in bound)
        and all(
            item.placed_bounds_mm[1][axis] > item.placed_bounds_mm[0][axis]
            for axis in range(3)
        )
        for item in placed
    )
    nonoverlap = placed_bounds_valid and not any(
        bounds_overlap_in_xy(left, right) for left, right in combinations(placed, 2)
    )
    return {
        "placed_instances_equal_plan_order_and_families": placed_pairs == expected_pairs,
        "placed_names_unique": len(placed_names) == len(set(placed_names)),
        "build_order_equals_placed_order": report_names == placed_names,
        "build_translations_equal_placed_plan": translations_match,
        "virtual_canvas_bounds_valid_and_nonoverlapping": nonoverlap,
    }


def validate_package_3mf(
    path: Path,
    plan: PackagePlan,
    placed_instances: Iterable[PlacedPackageInstance],
    *,
    source_audits: Mapping[str, PackageMeshSourceAudit] | None = None,
) -> dict[str, Any]:
    """Validate an emitted compact-instanced 3MF against one exact plan."""

    report = inspect_model_only_3mf(path)
    build_names = report["build_object_names"]
    expected_names = [item.logical_name for item in plan.instances]
    expected_source_names = [f"SOURCE__{family}" for family in plan.mesh_families]
    expected_source_by_name = {
        item.logical_name: f"SOURCE__{item.mesh_family}" for item in plan.instances
    }
    observed_hash = _observed_inventory_sha256(plan, report)
    package_policy = plan.to_dict()
    plan_checks = {
        "filename_equals_plan": path.name == plan.filename,
        "title_equals_plan": report["metadata"].get("Title") == plan.title,
        "description_equals_exact_plan_safety_contract": (
            report["metadata"].get("Description") == plan.description == SAFETY_DESCRIPTION
        ),
        "all_physical_objects_are_named_components": (
            report["component_object_count"] == plan.physical_object_count
            and report["build_object_count"] == plan.physical_object_count
        ),
        "exact_ordered_physical_inventory_names": build_names == expected_names,
        "exact_ordered_mesh_source_inventory": (
            report["mesh_resource_names"] == expected_source_names
        ),
        "every_named_component_resolves_to_planned_mesh_family": (
            report["component_source_by_name"] == expected_source_by_name
        ),
        "exact_physical_inventory_sha256": observed_hash == plan.inventory_sha256,
        "no_unplanned_mesh_families": report["mesh_family_count"]
        == len(plan.mesh_families),
        "plan_is_model_only_experimental_unrated_no_gcode": (
            package_policy["model_only"]
            and package_policy["experimental"]
            and package_policy["unrated"]
            and not package_policy["embedded_gcode_allowed"]
            and not package_policy["printer_profile_allowed"]
        ),
        "plan_explicitly_disclaims_physical_and_production_eligibility": (
            package_policy["physical_installation_qualified"] is False
            and package_policy["production_release_eligible"] is False
        ),
        "plan_forbids_wall_bores_rails_saddles_and_cross_level_ties": (
            not package_policy["wall_bores_allowed"]
            and not package_policy["rails_saddles_or_saddle_pins_allowed"]
            and not package_policy["cross_level_ties_allowed"]
            and not any(
                forbidden_package_term(value)
                for item in plan.instances
                for value in (item.logical_name, item.mesh_family)
            )
        ),
    }
    plan_checks.update(
        {
            f"mesh_source::{name}": passed
            for name, passed in mesh_source_audit_checks(plan, source_audits).items()
        }
    )
    plan_checks.update(_placed_contract_checks(plan, placed_instances, report))
    all_checks_pass = report["all_checks_pass"] and all(plan_checks.values())
    return {
        **report,
        "package_id": plan.package_id,
        "plan_sha256": plan.plan_sha256,
        "expected_inventory_sha256": plan.inventory_sha256,
        "observed_inventory_sha256": observed_hash,
        "plan_checks": plan_checks,
        "neutral_3mf_checks_pass": report["all_checks_pass"],
        "software_model_package_eligible": all_checks_pass,
        "physical_installation_qualified": False,
        "production_release_eligible": False,
        "conformance_scope": "software-model-and-package-only",
        "all_checks_pass": all_checks_pass,
    }


__all__ = [
    "ALLOWED_APPLICATIONS",
    "COMMON_SERIALIZED_GEOMETRY_GRID_DECIMALS",
    "MODEL_CONTENT_TYPE",
    "MODEL_RELATIONSHIP_TYPE",
    "NS",
    "NS_3MF",
    "REQUIRED_ENTRIES",
    "REQUIRED_ENTRY_ORDER",
    "canonical_serialized_triangle_digest",
    "inspect_model_only_3mf",
    "inspect_serialized_stl_geometry",
    "serialized_mesh_geometry_evidence",
    "validate_package_3mf",
]
