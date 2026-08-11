#!/usr/bin/env python3
"""Deterministic, neutral mesh serialization for the R8 qualification bundle.

The writer deliberately supports only the small subset needed here: binary
STL and model-only 3MF with millimetre units, one material, mesh resources,
and translation-only build items.  It cannot emit slicer profiles, G-code,
toolpaths, or printer instructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import struct
import sys
from typing import Sequence
from xml.etree import ElementTree as ET
import zipfile

import numpy as np
import trimesh


NS_3MF = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

MODEL_ONLY_ENTRY_ORDER = (
    "[Content_Types].xml",
    "_rels/.rels",
    "3D/3dmodel.model",
)
CANONICAL_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
CANONICAL_ZIP_MODE = 0o100644
CANONICAL_ZIP_COMPRESSLEVEL = 9
APPLICATION_NAME = "Story Corner R8 deterministic neutral model writer"
MATERIAL_NAME = "Black PETG qualification candidate"
MATERIAL_COLOR = "#111111FF"
STL_HEADER = b"Story Corner R8 deterministic qualification STL"
STL_RECORD_DTYPE = np.dtype(
    [
        ("normal", "<f4", (3,)),
        ("vertices", "<f4", (3, 3)),
        ("attribute", "<u2"),
    ]
)


@dataclass(frozen=True)
class SerializedMesh:
    """One canonical float32 indexed triangle mesh."""

    vertices: np.ndarray
    faces: np.ndarray


@dataclass(frozen=True)
class ModelObject:
    """One neutral 3MF mesh resource and its translation-only build item."""

    name: str
    mesh: SerializedMesh
    translation_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class ThreeMFInspection:
    """Strictly parsed source meshes, build translations, and package checks."""

    objects: dict[str, SerializedMesh]
    translations_mm: dict[str, tuple[float, float, float]]
    checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return bool(self.checks and all(self.checks.values()))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_bytes_exclusive(path: Path, payload: bytes) -> None:
    """Write one complete staged artifact and refuse every existing path."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _canonical_faces(faces: np.ndarray) -> np.ndarray:
    """Rotate faces cyclically, then sort them without changing winding."""

    source = np.asarray(faces, dtype=np.int64)
    rotated = np.empty_like(source)
    for index, face in enumerate(source):
        offset = int(np.argmin(face))
        rotated[index] = np.roll(face, -offset)
    order = np.lexsort((rotated[:, 2], rotated[:, 1], rotated[:, 0]))
    return np.ascontiguousarray(rotated[order], dtype=np.int64)


def _from_triangles(triangles: np.ndarray) -> SerializedMesh:
    coordinates = np.array(triangles, dtype="<f4", copy=True)
    if coordinates.ndim != 3 or coordinates.shape[1:] != (3, 3) or len(coordinates) == 0:
        raise ValueError("Serialized geometry needs a nonempty N x 3 x 3 triangle array")
    if not np.isfinite(coordinates).all():
        raise ValueError("Serialized geometry contains a non-finite coordinate")
    coordinates[coordinates == 0.0] = 0.0
    flat = coordinates.reshape((-1, 3))
    vertices, inverse = np.unique(flat, axis=0, return_inverse=True)
    raw_faces = inverse.reshape((-1, 3))
    # Manifold can retain zero-area bookkeeping triangles where tangent
    # primitives meet. They carry no surface or volume and may collapse on
    # STL's mandatory float32 grid. Remove only those rows; the closed-body
    # audit below still fails if removal opens or otherwise changes topology.
    keep = (
        (raw_faces[:, 0] != raw_faces[:, 1])
        & (raw_faces[:, 1] != raw_faces[:, 2])
        & (raw_faces[:, 2] != raw_faces[:, 0])
    )
    faces = _canonical_faces(raw_faces[keep])
    if len(faces) == 0:
        raise ValueError("Float32 serialization removed every triangle")
    return SerializedMesh(
        vertices=np.ascontiguousarray(vertices, dtype="<f4"),
        faces=np.ascontiguousarray(faces, dtype=np.int64),
    )


def canonicalize_mesh(mesh: trimesh.Trimesh) -> SerializedMesh:
    """Freeze a CAD mesh onto the exact float32 surface shared by STL/3MF."""

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty Trimesh is required")
    if not mesh.is_watertight or not mesh.is_winding_consistent or float(mesh.volume) <= 0.0:
        raise ValueError("Source mesh must be watertight, consistently wound, and positive")
    if len(mesh.split(only_watertight=False)) != 1:
        raise ValueError("Source mesh must contain exactly one connected body")
    result = _from_triangles(np.asarray(mesh.triangles, dtype=np.float64))
    evidence = serialized_mesh_evidence(result)
    if not evidence["closed_one_body_positive"]:
        raise ValueError("Float32 serialization changed the source into an invalid body")
    return result


def canonical_triangle_digest(mesh: SerializedMesh) -> str:
    """Hash exact float32 triangle bits independent of indexing and winding."""

    triangles = np.asarray(mesh.vertices, dtype="<f4")[np.asarray(mesh.faces, dtype=np.int64)]
    triangle_rows: list[tuple[int, ...]] = []
    for triangle in triangles:
        points = sorted(
            tuple(int(value) for value in np.asarray(point, dtype="<f4").view("<u4"))
            for point in triangle
        )
        triangle_rows.append(tuple(value for point in points for value in point))
    triangle_rows.sort()
    canonical = np.asarray(triangle_rows, dtype="<u4")
    header = f"r8-float32-triangles-v1\0{len(triangle_rows)}\0".encode("ascii")
    return sha256_bytes(header + canonical.tobytes(order="C"))


def serialized_mesh_evidence(mesh: SerializedMesh) -> dict[str, object]:
    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)
    if (
        vertices.ndim != 2
        or vertices.shape[1:] != (3,)
        or faces.ndim != 2
        or faces.shape[1:] != (3,)
        or len(vertices) == 0
        or len(faces) == 0
        or not np.isfinite(vertices).all()
        or np.any(faces < 0)
        or np.any(faces >= len(vertices))
    ):
        raise ValueError("Invalid indexed serialized mesh")
    rendered = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    triangles = vertices[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    zero_area = int(np.count_nonzero(np.einsum("ij,ij->i", cross, cross) <= 1.0e-20))
    body_count = int(len(rendered.split(only_watertight=False)))
    watertight = bool(rendered.is_watertight)
    winding = bool(rendered.is_winding_consistent)
    positive = bool(rendered.is_volume and float(rendered.volume) > 0.0)
    return {
        "vertex_count": int(len(vertices)),
        "triangle_count": int(len(faces)),
        "zero_area_triangle_count": zero_area,
        "bounds_mm": np.round(rendered.bounds, 6).tolist(),
        "extents_mm": np.round(rendered.extents, 6).tolist(),
        "volume_mm3": round(float(rendered.volume), 6),
        "watertight": watertight,
        "winding_consistent": winding,
        "positive_volume": positive,
        "body_count": body_count,
        "closed_one_body_positive": bool(
            zero_area == 0 and watertight and winding and positive and body_count == 1
        ),
        "canonical_float32_triangle_digest": canonical_triangle_digest(mesh),
    }


def binary_stl_bytes(mesh: SerializedMesh) -> bytes:
    vertices = np.asarray(mesh.vertices, dtype="<f4")
    faces = np.asarray(mesh.faces, dtype=np.int64)
    triangles = vertices[faces]
    records = np.zeros(len(faces), dtype=STL_RECORD_DTYPE)
    records["vertices"] = triangles
    cross = np.cross(
        triangles[:, 1].astype(np.float64) - triangles[:, 0].astype(np.float64),
        triangles[:, 2].astype(np.float64) - triangles[:, 0].astype(np.float64),
    )
    lengths = np.linalg.norm(cross, axis=1)
    if np.any(lengths <= 1.0e-12):
        raise ValueError("Cannot serialize a zero-area STL triangle")
    records["normal"] = (cross / lengths[:, None]).astype("<f4")
    header = STL_HEADER.ljust(80, b"\0")[:80]
    return header + struct.pack("<I", len(records)) + records.tobytes(order="C")


def write_binary_stl(path: Path, mesh: SerializedMesh) -> None:
    write_bytes_exclusive(path, binary_stl_bytes(mesh))


def read_binary_stl(path: Path) -> SerializedMesh:
    payload = Path(path).read_bytes()
    if len(payload) < 84:
        raise ValueError("Binary STL is shorter than its header")
    count = struct.unpack_from("<I", payload, 80)[0]
    expected = 84 + count * STL_RECORD_DTYPE.itemsize
    if count == 0 or len(payload) != expected:
        raise ValueError("Binary STL triangle count or payload length is invalid")
    records = np.frombuffer(payload, dtype=STL_RECORD_DTYPE, count=count, offset=84)
    if np.any(records["attribute"] != 0):
        raise ValueError("R8 binary STL must not contain attribute payloads")
    return _from_triangles(records["vertices"])


def _indent_xml(element: ET.Element, level: int = 0) -> None:
    whitespace = "\n" + "  " * level
    if len(element):
        if not element.text or not element.text.strip():
            element.text = whitespace + "  "
        for child in element:
            _indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = whitespace
    if level and (not element.tail or not element.tail.strip()):
        element.tail = whitespace


def _xml_bytes(root: ET.Element) -> bytes:
    _indent_xml(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _content_types_xml() -> bytes:
    ET.register_namespace("", NS_TYPES)
    root = ET.Element(f"{{{NS_TYPES}}}Types")
    ET.SubElement(
        root,
        f"{{{NS_TYPES}}}Default",
        {
            "Extension": "rels",
            "ContentType": "application/vnd.openxmlformats-package.relationships+xml",
        },
    )
    ET.SubElement(
        root,
        f"{{{NS_TYPES}}}Default",
        {
            "Extension": "model",
            "ContentType": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml",
        },
    )
    return _xml_bytes(root)


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
    return _xml_bytes(root)


def _float32_text(value: float) -> str:
    number = np.float32(value)
    if not np.isfinite(number):
        raise ValueError("3MF coordinate is not finite")
    if number == 0.0:
        return "0"
    return format(float(number), ".9g")


def _translation_text(values: tuple[float, float, float]) -> str:
    if len(values) != 3 or not all(np.isfinite(value) for value in values):
        raise ValueError("3MF translation must contain three finite values")
    tx, ty, tz = (0.0 if float(value) == 0.0 else float(value) for value in values)
    return f"1 0 0 0 1 0 0 0 1 {tx:.6f} {ty:.6f} {tz:.6f}"


def model_xml(title: str, description: str, objects: Sequence[ModelObject]) -> bytes:
    if not title.strip() or not description.strip() or not objects:
        raise ValueError("3MF title, description, and objects are required")
    names = [item.name for item in objects]
    if any(not name.strip() for name in names) or len(names) != len(set(names)):
        raise ValueError("3MF object names must be nonempty and unique")

    ET.register_namespace("", NS_3MF)
    model = ET.Element(
        f"{{{NS_3MF}}}model",
        {"unit": "millimeter", XML_LANG: "en-US"},
    )
    for name, value in (
        ("Title", title),
        ("Description", description),
        ("Application", APPLICATION_NAME),
    ):
        ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": name}).text = value
    resources = ET.SubElement(model, f"{{{NS_3MF}}}resources")
    materials = ET.SubElement(resources, f"{{{NS_3MF}}}basematerials", {"id": "1"})
    ET.SubElement(
        materials,
        f"{{{NS_3MF}}}base",
        {"name": MATERIAL_NAME, "displaycolor": MATERIAL_COLOR},
    )
    build = ET.SubElement(model, f"{{{NS_3MF}}}build")

    for object_id, item in enumerate(objects, start=2):
        obj = ET.SubElement(
            resources,
            f"{{{NS_3MF}}}object",
            {
                "id": str(object_id),
                "type": "model",
                "pid": "1",
                "pindex": "0",
                "name": item.name,
            },
        )
        mesh_node = ET.SubElement(obj, f"{{{NS_3MF}}}mesh")
        vertices_node = ET.SubElement(mesh_node, f"{{{NS_3MF}}}vertices")
        for vertex in np.asarray(item.mesh.vertices, dtype="<f4"):
            ET.SubElement(
                vertices_node,
                f"{{{NS_3MF}}}vertex",
                {
                    "x": _float32_text(vertex[0]),
                    "y": _float32_text(vertex[1]),
                    "z": _float32_text(vertex[2]),
                },
            )
        triangles_node = ET.SubElement(mesh_node, f"{{{NS_3MF}}}triangles")
        for face in np.asarray(item.mesh.faces, dtype=np.int64):
            ET.SubElement(
                triangles_node,
                f"{{{NS_3MF}}}triangle",
                {"v1": str(face[0]), "v2": str(face[1]), "v3": str(face[2])},
            )
        ET.SubElement(
            build,
            f"{{{NS_3MF}}}item",
            {"objectid": str(object_id), "transform": _translation_text(item.translation_mm)},
        )
    return _xml_bytes(model)


def _zip_entry(name: str, payload: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    info = zipfile.ZipInfo(name, date_time=CANONICAL_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = CANONICAL_ZIP_MODE << 16
    return info, payload


def model_only_3mf_bytes(
    title: str,
    description: str,
    objects: Sequence[ModelObject],
) -> bytes:
    payloads = (
        (MODEL_ONLY_ENTRY_ORDER[0], _content_types_xml()),
        (MODEL_ONLY_ENTRY_ORDER[1], _relationships_xml()),
        (MODEL_ONLY_ENTRY_ORDER[2], model_xml(title, description, objects)),
    )
    buffer = BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=CANONICAL_ZIP_COMPRESSLEVEL,
    ) as archive:
        for name, payload in payloads:
            info, data = _zip_entry(name, payload)
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=CANONICAL_ZIP_COMPRESSLEVEL)
    return buffer.getvalue()


def write_model_only_3mf(
    path: Path,
    title: str,
    description: str,
    objects: Sequence[ModelObject],
) -> None:
    write_bytes_exclusive(path, model_only_3mf_bytes(title, description, objects))


def _parse_transform(value: str) -> tuple[float, float, float]:
    tokens = value.split()
    if len(tokens) != 12:
        raise ValueError("3MF build transform must contain 12 values")
    numbers = tuple(float(token) for token in tokens)
    if not all(np.isfinite(numbers)) or numbers[:9] != (
        1.0,
        0.0,
        0.0,
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        1.0,
    ):
        raise ValueError("3MF build transform must be finite and translation-only")
    return numbers[9], numbers[10], numbers[11]


def inspect_model_only_3mf(path: Path) -> ThreeMFInspection:
    """Reject anything outside the exact neutral R8 3MF contract."""

    with zipfile.ZipFile(path) as archive:
        names = tuple(archive.namelist())
        infos = archive.infolist()
        corrupt = archive.testzip()
        payloads = {name: archive.read(name) for name in names}
    checks: dict[str, bool] = {
        "zip_crc_ok": corrupt is None,
        "entry_order_exact": names == MODEL_ONLY_ENTRY_ORDER,
        "entry_names_unique": len(names) == len(set(names)),
        "canonical_zip_metadata": bool(
            len(infos) == len(MODEL_ONLY_ENTRY_ORDER)
            and all(
                info.date_time == CANONICAL_ZIP_TIMESTAMP
                and info.compress_type == zipfile.ZIP_DEFLATED
                and info.create_system == 3
                and (info.external_attr >> 16) == CANONICAL_ZIP_MODE
                for info in infos
            )
        ),
        "content_types_exact": payloads.get(MODEL_ONLY_ENTRY_ORDER[0]) == _content_types_xml(),
        "relationships_exact": payloads.get(MODEL_ONLY_ENTRY_ORDER[1]) == _relationships_xml(),
        "no_slicer_gcode_or_toolpath_entries": bool(
            names == MODEL_ONLY_ENTRY_ORDER
            and not any(
                token in name.lower()
                for name in names
                for token in ("gcode", "toolpath", "slice_info", "metadata/")
            )
        ),
    }
    model_payload = payloads.get(MODEL_ONLY_ENTRY_ORDER[2], b"")
    if not model_payload:
        raise ValueError("3MF is missing its model payload")
    root = ET.fromstring(model_payload)
    checks["model_root_exact"] = bool(
        root.tag == f"{{{NS_3MF}}}model"
        and root.attrib == {"unit": "millimeter", XML_LANG: "en-US"}
    )
    checks["core_namespace_only"] = all(
        isinstance(node.tag, str) and node.tag.startswith(f"{{{NS_3MF}}}")
        for node in root.iter()
    )
    metadata = root.findall(f"{{{NS_3MF}}}metadata")
    checks["metadata_exact"] = bool(
        [node.attrib.get("name") for node in metadata]
        == ["Title", "Description", "Application"]
        and all(len(node) == 0 and set(node.attrib) == {"name"} for node in metadata)
        and (metadata[2].text if len(metadata) == 3 else None) == APPLICATION_NAME
    )
    resources = root.find(f"{{{NS_3MF}}}resources")
    build = root.find(f"{{{NS_3MF}}}build")
    if resources is None or build is None:
        raise ValueError("3MF lacks resources or build section")
    resource_children = list(resources)
    objects = resources.findall(f"{{{NS_3MF}}}object")
    checks["resource_shape_exact"] = bool(
        len(resource_children) == len(objects) + 1
        and resource_children[0].tag == f"{{{NS_3MF}}}basematerials"
        and resource_children[0].attrib == {"id": "1"}
        and all(child.tag == f"{{{NS_3MF}}}object" for child in resource_children[1:])
    )
    bases = resources.findall(f"{{{NS_3MF}}}basematerials/{{{NS_3MF}}}base")
    checks["petg_material_exact"] = bool(
        len(bases) == 1
        and bases[0].attrib == {"name": MATERIAL_NAME, "displaycolor": MATERIAL_COLOR}
    )

    parsed: dict[str, SerializedMesh] = {}
    id_to_name: dict[str, str] = {}
    object_shape_exact = True
    for expected_id, node in enumerate(objects, start=2):
        name = node.attrib.get("name", "")
        object_id = node.attrib.get("id", "")
        object_shape_exact &= bool(
            node.attrib
            == {
                "id": str(expected_id),
                "type": "model",
                "pid": "1",
                "pindex": "0",
                "name": name,
            }
            and name
            and name not in parsed
        )
        mesh_node = node.find(f"{{{NS_3MF}}}mesh")
        if mesh_node is None:
            raise ValueError("3MF object is not a direct mesh resource")
        vertices_nodes = mesh_node.findall(f"{{{NS_3MF}}}vertices/{{{NS_3MF}}}vertex")
        triangle_nodes = mesh_node.findall(f"{{{NS_3MF}}}triangles/{{{NS_3MF}}}triangle")
        vertices = np.asarray(
            [[float(vertex.attrib[key]) for key in ("x", "y", "z")] for vertex in vertices_nodes],
            dtype="<f4",
        )
        faces = np.asarray(
            [[int(face.attrib[key]) for key in ("v1", "v2", "v3")] for face in triangle_nodes],
            dtype=np.int64,
        )
        if len(vertices) == 0 or len(faces) == 0 or np.any(faces < 0) or np.any(faces >= len(vertices)):
            raise ValueError("3MF contains invalid mesh indices")
        serialized = _from_triangles(vertices[faces])
        if not serialized_mesh_evidence(serialized)["closed_one_body_positive"]:
            raise ValueError("3MF source mesh is not one closed positive body")
        parsed[name] = serialized
        id_to_name[object_id] = name
    checks["mesh_object_shape_exact"] = object_shape_exact

    items = build.findall(f"{{{NS_3MF}}}item")
    translations: dict[str, tuple[float, float, float]] = {}
    build_exact = len(items) == len(objects)
    for item in items:
        object_id = item.attrib.get("objectid", "")
        name = id_to_name.get(object_id)
        build_exact &= bool(
            name
            and name not in translations
            and set(item.attrib) == {"objectid", "transform"}
            and len(item) == 0
        )
        if name:
            translations[name] = _parse_transform(item.attrib.get("transform", ""))
    checks["each_mesh_built_once_translation_only"] = bool(
        build_exact and set(translations) == set(parsed)
    )
    checks["no_components_or_extensions"] = not bool(
        root.findall(f".//{{{NS_3MF}}}components")
        or root.findall(f".//{{{NS_3MF}}}component")
    )
    checks["all_source_meshes_closed_one_body_positive"] = all(
        bool(serialized_mesh_evidence(mesh)["closed_one_body_positive"])
        for mesh in parsed.values()
    )
    inspection = ThreeMFInspection(parsed, translations, checks)
    if not inspection.passed:
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise ValueError(f"3MF failed neutral-model audit: {failed}")
    return inspection


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_publish_directory(stage: Path, target: Path) -> None:
    """Atomically rename a staged directory while refusing any target.

    No check-then-overwrite fallback is provided.  Unsupported platforms fail
    closed instead of weakening the publication contract.
    """

    source = Path(stage)
    destination = Path(target)
    if not source.is_dir():
        raise ValueError("Atomic publication source must be a directory")
    if os.path.lexists(destination):
        raise FileExistsError(f"Refusing existing output directory: {destination}")
    _fsync_directory(source)
    encoded_source = os.fsencode(source)
    encoded_destination = os.fsencode(destination)
    libc = ctypes.CDLL(None, use_errno=True)

    if sys.platform == "darwin":
        renamex = getattr(libc, "renamex_np", None)
        if renamex is None:
            raise RuntimeError("renamex_np is unavailable; refusing non-atomic fallback")
        renamex.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        renamex.restype = ctypes.c_int
        result = renamex(encoded_source, encoded_destination, 0x00000004)  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise RuntimeError("renameat2 is unavailable; refusing non-atomic fallback")
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
        result = renameat2(-100, encoded_source, -100, encoded_destination, 1)  # RENAME_NOREPLACE
    elif os.name == "nt":
        try:
            os.rename(source, destination)
        except FileExistsError:
            raise
        result = 0
    else:
        raise RuntimeError("No supported atomic no-replace directory primitive")

    if result != 0:
        error = ctypes.get_errno()
        if error in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError(f"Refusing existing output directory: {destination}")
        raise OSError(error, os.strerror(error), str(destination))
    _fsync_directory(destination.parent)
