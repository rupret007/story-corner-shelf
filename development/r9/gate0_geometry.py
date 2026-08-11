"""R9-owned Gate-0 controls derived from frozen R8 geometry.

The R8 receiver is reused without a geometric change.  The 0.4 mm-per-face
key is subjected only to a proper 180-degree rotation about X and a positive
translation.  That puts the 20 x 16 mm handle on the plate and removes the
large floating handle cantilever present in the frozen R8 saved pose.

The keyed T-head still begins with a small empirical overhang.  This module
therefore reports new unsupported plan area as well as disconnected islands;
the corrected key is a process/fit control, not a claimed ideal overhang-free
production part.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path

import numpy as np
from shapely.geometry import GeometryCollection, Polygon
import trimesh

import cable_geometry
import model_io
import support_geometry


R9_ROOT = Path(__file__).resolve().parent
R8_V2_STL_ROOT = R9_ROOT.parent / "r8" / "generated" / "qualification_v2" / "stl"
RECEIVER_SOURCE = R8_V2_STL_ROOT / "r8_clearance_ladder_receiver.stl"
KEY_SOURCE = R8_V2_STL_ROOT / "r8_clearance_key_0p4.stl"
EXPECTED_RECEIVER_STL_SHA256 = (
    "edcc0ca5a2fb8a959de5bf70db305b10627f3c78a890adc6c72dd4bc0512cabf"
)
EXPECTED_KEY_STL_SHA256 = (
    "92c1b673523921b72868b62166fb3515cb538bcdcbd1e4abb82d5b2128e6f45e"
)
LAYER_HEIGHT_MM = 0.2


@dataclass(frozen=True)
class LayerOverhangReport:
    layer_height_mm: float
    sampled_layer_count: int
    first_layer_contact_area_mm2: float
    island_layer_indices: tuple[int, ...]
    largest_new_unsupported_area_mm2: float
    largest_new_unsupported_layer_index: int


@dataclass(frozen=True)
class SavedGate0PartEvidence:
    part_name: str
    orientation_id: str
    support_required: bool
    support_evidence: str
    first_layer_contact_area_mm2: float
    largest_new_unsupported_area_mm2: float
    largest_new_unsupported_layer_index: int
    slicer_preview_required: bool
    physical_overhang_screen_required: bool
    envelope: support_geometry.PrintEnvelope


def _load_frozen_mesh(path: Path, expected_sha256: str) -> trimesh.Trimesh:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"missing or unsafe frozen Gate-0 source: {path}")
    observed = model_io.sha256_file(path)
    if observed != expected_sha256:
        raise RuntimeError(
            f"frozen Gate-0 source changed: expected {expected_sha256}, "
            f"observed {observed}"
        )
    serialized = model_io.read_binary_stl(path)
    mesh = trimesh.Trimesh(
        vertices=np.asarray(serialized.vertices, dtype=float),
        faces=np.asarray(serialized.faces, dtype=np.int64),
        process=False,
    )
    if (
        mesh.is_empty
        or not mesh.is_watertight
        or not mesh.is_winding_consistent
        or len(mesh.split(only_watertight=False)) != 1
        or float(mesh.volume) <= 0.0
    ):
        raise RuntimeError("frozen Gate-0 source is not a closed positive body")
    return mesh


def build_receiver_control() -> trimesh.Trimesh:
    """Return the exact frozen R8 ladder receiver geometry."""

    return _load_frozen_mesh(RECEIVER_SOURCE, EXPECTED_RECEIVER_STL_SHA256)


def build_frozen_saved_key_control() -> trimesh.Trimesh:
    """Return the flawed frozen saved pose solely for regression evidence."""

    return _load_frozen_mesh(KEY_SOURCE, EXPECTED_KEY_STL_SHA256)


def build_handle_down_key_control() -> trimesh.Trimesh:
    """Return the exact 0.4 key in the R9 handle-down empirical print pose."""

    mesh = build_frozen_saved_key_control()
    transform = np.eye(4, dtype=float)
    transform[1, 1] = -1.0
    transform[2, 2] = -1.0
    mesh.apply_transform(transform)
    mesh.apply_translation(-np.asarray(mesh.bounds[0], dtype=float))
    return mesh


def build_saved_gate0_parts() -> dict[str, trimesh.Trimesh]:
    return {
        "r8_clearance_ladder_receiver": build_receiver_control(),
        "r9_gate0_clearance_key_0p4_handle_down": build_handle_down_key_control(),
    }


def _section_material_region(
    mesh: trimesh.Trimesh, z_mm: float
) -> Polygon | GeometryCollection:
    section = mesh.section(
        plane_origin=(0.0, 0.0, float(z_mm)),
        plane_normal=(0.0, 0.0, 1.0),
    )
    if section is None:
        return GeometryCollection()
    region: Polygon | GeometryCollection = GeometryCollection()
    for discrete in section.discrete:
        points = np.asarray(discrete, dtype=float)[:, :2]
        if len(points) < 4:
            continue
        polygon = Polygon(points)
        if not polygon.is_valid:
            polygon = polygon.buffer(0.0)
        region = region.symmetric_difference(polygon)
    return region


def layer_overhang_report(
    oriented_mesh: trimesh.Trimesh, *, layer_height_mm: float = LAYER_HEIGHT_MM
) -> LayerOverhangReport:
    """Report islands and exact new plan area at each deposited layer."""

    if not isinstance(oriented_mesh, trimesh.Trimesh) or oriented_mesh.is_empty:
        raise ValueError("A nonempty saved mesh is required")
    layer = float(layer_height_mm)
    if not math.isfinite(layer) or layer <= 0.0:
        raise ValueError("Layer height must be a positive finite number")
    height = float(oriented_mesh.extents[2])
    count = int(math.ceil(height / layer - 1.0e-9))
    minimum_z = float(oriented_mesh.bounds[0, 2])
    previous = None
    first_area = 0.0
    islands: list[int] = []
    largest_area = 0.0
    largest_index = 0
    for index in range(count):
        deposited = min(layer, height - index * layer)
        z_mm = minimum_z + index * layer + 0.5 * deposited
        region = _section_material_region(oriented_mesh, z_mm)
        if index == 0:
            first_area = float(region.area)
        elif region.is_empty or previous is None:
            islands.append(index)
        else:
            for component in cable_geometry._filled_components(region):
                if component.intersection(previous).area <= 1.0e-8:
                    islands.append(index)
                    break
            new_area = float(region.difference(previous).area)
            if new_area > largest_area:
                largest_area = new_area
                largest_index = index
        previous = region
    return LayerOverhangReport(
        layer_height_mm=layer,
        sampled_layer_count=count,
        first_layer_contact_area_mm2=first_area,
        island_layer_indices=tuple(islands),
        largest_new_unsupported_area_mm2=largest_area,
        largest_new_unsupported_layer_index=largest_index,
    )


def saved_gate0_print_evidence() -> tuple[SavedGate0PartEvidence, ...]:
    parts = build_saved_gate0_parts()
    receiver_report = layer_overhang_report(parts["r8_clearance_ladder_receiver"])
    key_report = layer_overhang_report(
        parts["r9_gate0_clearance_key_0p4_handle_down"]
    )
    return (
        SavedGate0PartEvidence(
            part_name="r8_clearance_ladder_receiver",
            orientation_id="frozen_r8_v2_broad_back_face_on_plate",
            support_required=False,
            support_evidence=(
                "frozen receiver pose; every sampled layer remains connected; "
                "Bambu Preview review is still mandatory"
            ),
            first_layer_contact_area_mm2=receiver_report.first_layer_contact_area_mm2,
            largest_new_unsupported_area_mm2=(
                receiver_report.largest_new_unsupported_area_mm2
            ),
            largest_new_unsupported_layer_index=(
                receiver_report.largest_new_unsupported_layer_index
            ),
            slicer_preview_required=True,
            physical_overhang_screen_required=False,
            envelope=support_geometry.print_envelope_with_margins(
                parts["r8_clearance_ladder_receiver"]
            ),
        ),
        SavedGate0PartEvidence(
            part_name="r9_gate0_clearance_key_0p4_handle_down",
            orientation_id="proper_rotation_x_180_handle_down",
            support_required=False,
            support_evidence=(
                "handle-down empirical control: no disconnected islands; the "
                "52 mm2 keyed-head step requires a warning-free Bambu Preview "
                "and a cooled-part droop/fit screen"
            ),
            first_layer_contact_area_mm2=key_report.first_layer_contact_area_mm2,
            largest_new_unsupported_area_mm2=(
                key_report.largest_new_unsupported_area_mm2
            ),
            largest_new_unsupported_layer_index=(
                key_report.largest_new_unsupported_layer_index
            ),
            slicer_preview_required=True,
            physical_overhang_screen_required=True,
            envelope=support_geometry.print_envelope_with_margins(
                parts["r9_gate0_clearance_key_0p4_handle_down"]
            ),
        ),
    )


__all__ = (
    "EXPECTED_KEY_STL_SHA256",
    "EXPECTED_RECEIVER_STL_SHA256",
    "LayerOverhangReport",
    "SavedGate0PartEvidence",
    "build_frozen_saved_key_control",
    "build_handle_down_key_control",
    "build_receiver_control",
    "build_saved_gate0_parts",
    "layer_overhang_report",
    "saved_gate0_print_evidence",
)
