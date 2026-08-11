#!/usr/bin/env python3
"""Project-owned neutral mesh and deterministic model-only 3MF utilities.

The functions in this module contain no r5/r6 shelf dimensions and no slicer or
printer profile data.  They are the active r6 replacement for importing neutral
helpers from the preserved hybrid generator.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import trimesh
from shapely.geometry import box as shapely_box


NS_3MF = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"


def cuboid(
    size: tuple[float, float, float],
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> trimesh.Trimesh:
    if len(size) != 3 or any(float(value) <= 0.0 for value in size):
        raise ValueError(f"Cuboid sizes must be positive: {size!r}")
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(np.asarray(origin, dtype=float) + np.asarray(size, dtype=float) / 2.0)
    return mesh


def rounded_prism(width: float, depth: float, height: float, radius: float) -> trimesh.Trimesh:
    if min(width, depth, height) <= 0.0:
        raise ValueError("Rounded-prism dimensions must be positive")
    radius = min(float(radius), width / 2.0 - 0.01, depth / 2.0 - 0.01)
    if radius <= 0.0:
        return cuboid((width, depth, height))
    center = shapely_box(radius, radius, width - radius, depth - radius)
    mesh = trimesh.creation.extrude_polygon(
        center.buffer(radius, quad_segs=8),
        height=height,
        engine="earcut",
    )
    mesh.remove_unreferenced_vertices()
    return mesh


def boolean_union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("A boolean union needs at least one mesh")
    result = trimesh.boolean.union(meshes, engine="manifold", check_volume=True)
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    result.remove_unreferenced_vertices()
    result.merge_vertices()
    result.fix_normals()
    return result


def boolean_difference(
    body: trimesh.Trimesh, cutters: list[trimesh.Trimesh]
) -> trimesh.Trimesh:
    if not cutters:
        return body.copy()
    result = trimesh.boolean.difference(
        [body, *cutters], engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    result.remove_unreferenced_vertices()
    result.merge_vertices()
    result.fix_normals()
    return result


def normalize_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Move a mesh into the positive octant without changing its geometry."""

    mesh.apply_translation(-np.asarray(mesh.bounds[0], dtype=float))
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    return mesh


def _indent_xml(element: ET.Element, level: int = 0) -> None:
    space = "\n" + level * "  "
    if len(element):
        if not element.text or not element.text.strip():
            element.text = space + "  "
        for child in element:
            _indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = space
    if level and (not element.tail or not element.tail.strip()):
        element.tail = space


def _model_xml(
    title: str,
    description: str,
    objects: list[tuple[str, trimesh.Trimesh, tuple[float, float, float]]],
) -> bytes:
    if not objects:
        raise ValueError("A model-only 3MF must contain at least one object")
    names = [name for name, _mesh, _translation in objects]
    if any(not name.strip() for name in names) or len(names) != len(set(names)):
        raise ValueError("3MF object names must be nonempty and unique")
    ET.register_namespace("", NS_3MF)
    model = ET.Element(
        f"{{{NS_3MF}}}model",
        {"unit": "millimeter", "{http://www.w3.org/XML/1998/namespace}lang": "en-US"},
    )
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Title"}).text = title
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Description"}).text = description
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Application"}).text = (
        "Story Corner deterministic neutral model writer"
    )
    resources = ET.SubElement(model, f"{{{NS_3MF}}}resources")
    materials = ET.SubElement(resources, f"{{{NS_3MF}}}basematerials", {"id": "1"})
    ET.SubElement(
        materials,
        f"{{{NS_3MF}}}base",
        {"name": "Black PETG (unconfirmed product/preset)", "displaycolor": "#111111FF"},
    )
    build = ET.SubElement(model, f"{{{NS_3MF}}}build")

    for object_id, (name, source_mesh, translation) in enumerate(objects, start=2):
        mesh = source_mesh.copy()
        mesh.remove_unreferenced_vertices()
        mesh.fix_normals()
        obj = ET.SubElement(
            resources,
            f"{{{NS_3MF}}}object",
            {
                "id": str(object_id),
                "type": "model",
                "pid": "1",
                "pindex": "0",
                "name": name,
            },
        )
        mesh_node = ET.SubElement(obj, f"{{{NS_3MF}}}mesh")
        vertices = ET.SubElement(mesh_node, f"{{{NS_3MF}}}vertices")
        for vertex in np.asarray(mesh.vertices):
            ET.SubElement(
                vertices,
                f"{{{NS_3MF}}}vertex",
                {
                    "x": f"{vertex[0]:.17g}",
                    "y": f"{vertex[1]:.17g}",
                    "z": f"{vertex[2]:.17g}",
                },
            )
        triangles = ET.SubElement(mesh_node, f"{{{NS_3MF}}}triangles")
        for face in np.asarray(mesh.faces, dtype=int):
            ET.SubElement(
                triangles,
                f"{{{NS_3MF}}}triangle",
                {"v1": str(face[0]), "v2": str(face[1]), "v3": str(face[2])},
            )
        tx, ty, tz = translation
        ET.SubElement(
            build,
            f"{{{NS_3MF}}}item",
            {
                "objectid": str(object_id),
                "transform": f"1 0 0 0 1 0 0 0 1 {tx:.6f} {ty:.6f} {tz:.6f}",
            },
        )
    _indent_xml(model)
    return ET.tostring(model, encoding="utf-8", xml_declaration=True)


def _append_mesh_object(
    resources: ET.Element,
    *,
    object_id: int,
    name: str,
    source_mesh: trimesh.Trimesh,
) -> None:
    """Append one neutral mesh resource to a 3MF resources element."""

    mesh = source_mesh.copy()
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()
    obj = ET.SubElement(
        resources,
        f"{{{NS_3MF}}}object",
        {
            "id": str(object_id),
            "type": "model",
            "pid": "1",
            "pindex": "0",
            "name": name,
        },
    )
    mesh_node = ET.SubElement(obj, f"{{{NS_3MF}}}mesh")
    vertices = ET.SubElement(mesh_node, f"{{{NS_3MF}}}vertices")
    for vertex in np.asarray(mesh.vertices):
        ET.SubElement(
            vertices,
            f"{{{NS_3MF}}}vertex",
            {
                "x": f"{vertex[0]:.17g}",
                "y": f"{vertex[1]:.17g}",
                "z": f"{vertex[2]:.17g}",
            },
        )
    triangles = ET.SubElement(mesh_node, f"{{{NS_3MF}}}triangles")
    for face in np.asarray(mesh.faces, dtype=int):
        ET.SubElement(
            triangles,
            f"{{{NS_3MF}}}triangle",
            {"v1": str(face[0]), "v2": str(face[1]), "v3": str(face[2])},
        )


def _instanced_model_xml(
    title: str,
    description: str,
    mesh_families: list[tuple[str, trimesh.Trimesh]],
    instances: list[tuple[str, str, tuple[float, float, float]]],
) -> bytes:
    """Build compact 3MF XML with one mesh resource per printable family.

    Every physical instance receives its own named component object and exactly
    one build item. Repeated parts therefore remain countable without embedding
    the same vertex/triangle payload hundreds of times.
    """

    family_names = [name for name, _mesh in mesh_families]
    logical_names = [name for name, _family, _translation in instances]
    if not mesh_families or not instances:
        raise ValueError("An instanced 3MF needs mesh families and build instances")
    if any(not name.strip() for name in family_names + logical_names):
        raise ValueError("3MF family and logical object names must be nonempty")
    if len(family_names) != len(set(family_names)):
        raise ValueError("3MF mesh-family names must be unique")
    if len(logical_names) != len(set(logical_names)):
        raise ValueError("3MF logical instance names must be unique")
    family_lookup = {name for name in family_names}
    unknown = sorted({family for _name, family, _translation in instances} - family_lookup)
    if unknown:
        raise ValueError(f"3MF instances reference unknown mesh families: {unknown}")

    ET.register_namespace("", NS_3MF)
    model = ET.Element(
        f"{{{NS_3MF}}}model",
        {"unit": "millimeter", "{http://www.w3.org/XML/1998/namespace}lang": "en-US"},
    )
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Title"}).text = title
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Description"}).text = description
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Application"}).text = (
        "Story Corner deterministic neutral instanced model writer"
    )
    resources = ET.SubElement(model, f"{{{NS_3MF}}}resources")
    materials = ET.SubElement(resources, f"{{{NS_3MF}}}basematerials", {"id": "1"})
    ET.SubElement(
        materials,
        f"{{{NS_3MF}}}base",
        {"name": "Black PETG (unconfirmed product/preset)", "displaycolor": "#111111FF"},
    )

    family_ids: dict[str, int] = {}
    next_id = 2
    for family_name, mesh in mesh_families:
        family_ids[family_name] = next_id
        _append_mesh_object(
            resources,
            object_id=next_id,
            name=f"SOURCE__{family_name}",
            source_mesh=mesh,
        )
        next_id += 1

    build = ET.SubElement(model, f"{{{NS_3MF}}}build")
    for logical_name, family_name, translation in instances:
        object_id = next_id
        next_id += 1
        obj = ET.SubElement(
            resources,
            f"{{{NS_3MF}}}object",
            {"id": str(object_id), "type": "model", "name": logical_name},
        )
        components = ET.SubElement(obj, f"{{{NS_3MF}}}components")
        ET.SubElement(
            components,
            f"{{{NS_3MF}}}component",
            {"objectid": str(family_ids[family_name])},
        )
        tx, ty, tz = translation
        ET.SubElement(
            build,
            f"{{{NS_3MF}}}item",
            {
                "objectid": str(object_id),
                "transform": f"1 0 0 0 1 0 0 0 1 {tx:.6f} {ty:.6f} {tz:.6f}",
            },
        )
    _indent_xml(model)
    return ET.tostring(model, encoding="utf-8", xml_declaration=True)


def _content_types_xml() -> bytes:
    ET.register_namespace("", NS_TYPES)
    root = ET.Element(f"{{{NS_TYPES}}}Types")
    ET.SubElement(
        root,
        f"{{{NS_TYPES}}}Default",
        {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"},
    )
    ET.SubElement(
        root,
        f"{{{NS_TYPES}}}Default",
        {"Extension": "model", "ContentType": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"},
    )
    _indent_xml(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _relationships_xml() -> bytes:
    ET.register_namespace("", NS_RELS)
    root = ET.Element(f"{{{NS_RELS}}}Relationships")
    ET.SubElement(
        root,
        f"{{{NS_RELS}}}Relationship",
        {
            "Target": "/3D/3dmodel.model",
            "Id": "rel0",
            "Type": "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel",
        },
    )
    _indent_xml(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_model_3mf(
    path: Path,
    title: str,
    description: str,
    objects: list[tuple[str, trimesh.Trimesh, tuple[float, float, float]]],
) -> None:
    """Write a deterministic neutral-core 3MF containing no slicer payload."""

    path.parent.mkdir(parents=True, exist_ok=True)

    def write_entry(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, payload)

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        write_entry(archive, "[Content_Types].xml", _content_types_xml())
        write_entry(archive, "_rels/.rels", _relationships_xml())
        write_entry(archive, "3D/3dmodel.model", _model_xml(title, description, objects))


def write_instanced_model_3mf(
    path: Path,
    title: str,
    description: str,
    mesh_families: list[tuple[str, trimesh.Trimesh]],
    instances: list[tuple[str, str, tuple[float, float, float]]],
) -> None:
    """Write a compact deterministic 3MF for an exact physical-object set."""

    path.parent.mkdir(parents=True, exist_ok=True)

    def write_entry(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, payload)

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        write_entry(archive, "[Content_Types].xml", _content_types_xml())
        write_entry(archive, "_rels/.rels", _relationships_xml())
        write_entry(
            archive,
            "3D/3dmodel.model",
            _instanced_model_xml(title, description, mesh_families, instances),
        )
