#!/usr/bin/env python3
"""Qualification-only R7 cable-hook collar for the unchanged R6 pier overlay.

The accessory is deliberately separate from the frozen R6 shelf and ornament
inventory.  It snaps over the visible column face, is removed before any
facade or cross-key service, and receives no load rating until the physical
PETG qualification matrix in ``config.json`` passes.
"""

from __future__ import annotations

import json
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import trimesh
from shapely.geometry import LineString, Point, Polygon, box as shapely_box
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parent
R6_ROOT = ROOT.parent / "r6"
if str(R6_ROOT) not in sys.path:
    sys.path.insert(0, str(R6_ROOT))

from model_io import boolean_difference, boolean_union, cuboid, normalize_mesh  # noqa: E402
from ornament_geometry import build_ornament_families  # noqa: E402


EPSILON = 1.0e-7
ALLOWED_OVERLAP_MM3 = 1.0e-5


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"Duplicate JSON key: {key}")
        output[key] = value
    return output


def load_config(path: Path = ROOT / "config.json") -> dict[str, Any]:
    return json.loads(path.read_text(), object_pairs_hook=_reject_duplicate_keys)


def load_r6_config(path: Path = R6_ROOT / "config.json") -> dict[str, Any]:
    return json.loads(path.read_text(), object_pairs_hook=_reject_duplicate_keys)


def _finish(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    if float(mesh.volume) < 0.0:
        mesh.invert()
    return mesh


def _validated_null_facet_cleanup(
    mesh: trimesh.Trimesh,
    *,
    label: str,
) -> trimesh.Trimesh:
    """Remove only Boolean-generated zero-area helper facets, fail closed."""

    raw = _finish(mesh)
    raw_bounds = np.asarray(raw.bounds, dtype=float)
    raw_volume = float(raw.volume)
    cleaned = raw.copy()
    cleaned.process(validate=True)
    cleaned = _finish(cleaned)
    if (
        float(np.max(np.abs(np.asarray(cleaned.bounds) - raw_bounds))) > 1.0e-6
        or abs(float(cleaned.volume) - raw_volume) > 1.0e-6
    ):
        raise ValueError(f"{label}: null-facet cleanup changed measurable geometry")
    if (
        not cleaned.is_watertight
        or not cleaned.is_volume
        or cleaned.body_count != 1
        or np.any(np.asarray(cleaned.area_faces, dtype=float) <= 1.0e-12)
    ):
        raise ValueError(f"{label}: expected one clean closed positive-volume body")
    return cleaned


def _extrude_xy(shape: Any, z0: float, z1: float) -> trimesh.Trimesh:
    if z1 <= z0 or shape.is_empty:
        raise ValueError("A positive nonempty XY extrusion is required")
    mesh = trimesh.creation.extrude_polygon(shape, height=z1 - z0, engine="earcut")
    mesh.apply_translation((0.0, 0.0, z0))
    return _finish(mesh)


def _extrude_yz(shape: Any, x0: float, width: float) -> trimesh.Trimesh:
    """Extrude a polygon authored as ``(depth, elevation)`` across run X."""

    if width <= 0.0 or shape.is_empty:
        raise ValueError("A positive nonempty YZ extrusion is required")
    source = trimesh.creation.extrude_polygon(shape, height=width, engine="earcut")
    vertices = np.asarray(source.vertices, dtype=float)
    source.vertices = np.column_stack(
        (vertices[:, 2] + x0, vertices[:, 1], vertices[:, 0])
    )
    return _finish(source)


def positive_overlap_volume_mm3(
    left: trimesh.Trimesh,
    right: trimesh.Trimesh,
) -> float:
    if np.any(left.bounds[1] < right.bounds[0]) or np.any(right.bounds[1] < left.bounds[0]):
        return 0.0
    # Manifold may truthfully return an empty zero-volume shell for separated
    # or tangent solids; Trimesh's center-of-mass helper warns while wrapping
    # that empty result even though the overlap is exactly zero.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="invalid value encountered in divide",
            category=RuntimeWarning,
            module="trimesh.triangles",
        )
        result = trimesh.boolean.intersection(
            [left, right], engine="manifold", check_volume=True
        )
        if result is None:
            return 0.0
        meshes = result if isinstance(result, list) else [result]
        return float(sum(max(0.0, float(mesh.volume)) for mesh in meshes))


@dataclass(frozen=True)
class CableHookMetrics:
    installed_bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    saved_bounds_mm: tuple[tuple[float, float, float], tuple[float, float, float]]
    volume_mm3: float
    estimated_petg_mass_g: float
    maximum_seated_overlay_overlap_mm3: float
    maximum_compressed_approach_overlap_mm3: float
    maximum_free_downward_travel_mm: float
    downward_stop_overlap_at_gate_mm3: float
    flex_strain_proxy: float
    saved_plate_contact_area_mm2: float
    maximum_cable_bundle_to_bridge_overlap_mm3: float
    maximum_cable_bundle_to_collar_overlap_mm3: float
    cable_bundle_to_tip_clearance_mm: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "installed_bounds_mm": [list(row) for row in self.installed_bounds_mm],
            "saved_bounds_mm": [list(row) for row in self.saved_bounds_mm],
            "volume_mm3": self.volume_mm3,
            "estimated_petg_mass_g": self.estimated_petg_mass_g,
            "maximum_seated_overlay_overlap_mm3": self.maximum_seated_overlay_overlap_mm3,
            "maximum_compressed_approach_overlap_mm3": (
                self.maximum_compressed_approach_overlap_mm3
            ),
            "maximum_free_downward_travel_mm": self.maximum_free_downward_travel_mm,
            "downward_stop_overlap_at_gate_mm3": self.downward_stop_overlap_at_gate_mm3,
            "flex_strain_proxy": self.flex_strain_proxy,
            "saved_plate_contact_area_mm2": self.saved_plate_contact_area_mm2,
            "maximum_cable_bundle_to_bridge_overlap_mm3": (
                self.maximum_cable_bundle_to_bridge_overlap_mm3
            ),
            "maximum_cable_bundle_to_collar_overlap_mm3": (
                self.maximum_cable_bundle_to_collar_overlap_mm3
            ),
            "cable_bundle_to_tip_clearance_mm": (
                self.cable_bundle_to_tip_clearance_mm
            ),
        }


def overlay_edges_mm(y_mm: float, cfg: dict[str, Any]) -> tuple[float, float]:
    base = cfg["base_interface"]
    bottom = float(base["overlay_width_bottom_mm"])
    top = float(base["overlay_width_top_mm"])
    height = float(base["overlay_height_mm"])
    inset = (bottom - top) / 2.0 * float(y_mm) / height
    return (inset, bottom - inset)


def _tapered_strip(
    cfg: dict[str, Any],
    *,
    left_offset_outer_mm: float,
    left_offset_inner_mm: float,
    right_side: bool,
) -> Polygon:
    y0, y1 = (float(value) for value in cfg["cable_hook"]["collar_band_elevation_mm"])
    left0, right0 = overlay_edges_mm(y0, cfg)
    left1, right1 = overlay_edges_mm(y1, cfg)
    if right_side:
        return Polygon(
            [
                (right0 + left_offset_inner_mm, y0),
                (right0 + left_offset_outer_mm, y0),
                (right1 + left_offset_outer_mm, y1),
                (right1 + left_offset_inner_mm, y1),
            ]
        )
    return Polygon(
        [
            (left0 - left_offset_outer_mm, y0),
            (left0 - left_offset_inner_mm, y0),
            (left1 - left_offset_inner_mm, y1),
            (left1 - left_offset_outer_mm, y1),
        ]
    )


def _cylinder_along_elevation(
    *,
    center_x: float,
    center_depth: float,
    elevation_start: float,
    elevation_end: float,
    radius: float,
    run_slope_per_elevation: float,
) -> trimesh.Trimesh:
    """Create a rounded jaw-root gusset whose axis follows elevation Y."""

    if elevation_end <= elevation_start or radius <= 0.0:
        raise ValueError("A positive fillet radius and elevation span are required")
    source = trimesh.creation.cylinder(
        radius=radius,
        height=elevation_end - elevation_start,
        sections=48,
    )
    vertices = np.asarray(source.vertices, dtype=float)
    source.vertices = np.column_stack(
        (
            vertices[:, 0] + center_x,
            vertices[:, 2] + (elevation_start + elevation_end) / 2.0,
            vertices[:, 1] + center_depth,
        )
    )
    elevation_mid = (elevation_start + elevation_end) / 2.0
    source.vertices[:, 0] += run_slope_per_elevation * (
        source.vertices[:, 1] - elevation_mid
    )
    return _finish(source)


def _collar_components(cfg: dict[str, Any]) -> dict[str, trimesh.Trimesh]:
    hook = cfg["cable_hook"]
    y0, y1 = (float(value) for value in hook["collar_band_elevation_mm"])
    clearance = float(hook["nominal_clearance_per_face_mm"])
    jaw_thickness = float(hook["side_jaw_thickness_mm"])
    lip_undercut = float(hook["rear_lip_inward_undercut_mm"])
    lip_z0, lip_z1 = (float(value) for value in hook["rear_lip_depth_zone_mm"])
    bridge_z0, bridge_z1 = (
        float(value) for value in hook["front_bridge_depth_zone_mm"]
    )
    arm_z0, arm_z1 = (float(value) for value in hook["flex_arm_depth_zone_mm"])
    stop_z0, stop_z1 = (
        float(value) for value in hook["front_stop_pad_depth_zone_mm"]
    )
    vertical_foot_y0 = float(hook["vertical_stop_foot_bottom_elevation_mm"])
    vertical_foot_y1 = y0 + float(hook["vertical_stop_foot_overlap_into_band_mm"])

    left0, right0 = overlay_edges_mm(y0, cfg)
    left1, right1 = overlay_edges_mm(y1, cfg)
    outer_left0 = left0 - clearance - jaw_thickness
    outer_left1 = left1 - clearance - jaw_thickness
    outer_right0 = right0 + clearance + jaw_thickness
    outer_right1 = right1 + clearance + jaw_thickness

    left_jaw_shape = _tapered_strip(
        cfg,
        left_offset_outer_mm=clearance + jaw_thickness,
        left_offset_inner_mm=clearance,
        right_side=False,
    )
    right_jaw_shape = _tapered_strip(
        cfg,
        left_offset_outer_mm=clearance + jaw_thickness,
        left_offset_inner_mm=clearance,
        right_side=True,
    )
    crossbar_height = float(hook["front_bridge_crossbar_height_mm"])
    crossbar_y1 = y0 + crossbar_height
    crossbar_left, crossbar_right = overlay_edges_mm(crossbar_y1, cfg)
    crossbar_outline = Polygon(
        [
            (outer_left0, y0),
            (outer_right0, y0),
            (crossbar_right + clearance + jaw_thickness, crossbar_y1),
            (crossbar_left - clearance - jaw_thickness, crossbar_y1),
        ]
    )
    bridge = _validated_null_facet_cleanup(
        boolean_union(
            [
                _extrude_xy(crossbar_outline, bridge_z0, bridge_z1),
                _extrude_xy(left_jaw_shape, bridge_z0, bridge_z1),
                _extrude_xy(right_jaw_shape, bridge_z0, bridge_z1),
            ]
        ),
        label="Open-center front bridge",
    )
    left_jaw = _extrude_xy(left_jaw_shape, arm_z0, arm_z1)
    right_jaw = _extrude_xy(right_jaw_shape, arm_z0, arm_z1)

    left_lip_shape = Polygon(
        [
            (outer_left0, y0),
            (left0 + lip_undercut, y0),
            (left1 + lip_undercut, y1),
            (outer_left1, y1),
        ]
    )
    right_lip_shape = Polygon(
        [
            (right0 - lip_undercut, y0),
            (outer_right0, y0),
            (outer_right1, y1),
            (right1 - lip_undercut, y1),
        ]
    )
    left_lip = _extrude_xy(left_lip_shape, lip_z0, lip_z1)
    right_lip = _extrude_xy(right_lip_shape, lip_z0, lip_z1)
    left_stop = _extrude_xy(left_lip_shape, stop_z0, stop_z1)
    right_stop = _extrude_xy(right_lip_shape, stop_z0, stop_z1)

    foot_left0, foot_right0 = overlay_edges_mm(vertical_foot_y0, cfg)
    foot_left1, foot_right1 = overlay_edges_mm(vertical_foot_y1, cfg)
    left_vertical_foot_shape = Polygon(
        [
            (foot_left0 - clearance - jaw_thickness, vertical_foot_y0),
            (foot_left0 + lip_undercut, vertical_foot_y0),
            (foot_left1 + lip_undercut, vertical_foot_y1),
            (foot_left1 - clearance - jaw_thickness, vertical_foot_y1),
        ]
    )
    right_vertical_foot_shape = Polygon(
        [
            (foot_right0 - lip_undercut, vertical_foot_y0),
            (foot_right0 + clearance + jaw_thickness, vertical_foot_y0),
            (foot_right1 + clearance + jaw_thickness, vertical_foot_y1),
            (foot_right1 - lip_undercut, vertical_foot_y1),
        ]
    )
    left_vertical_foot = _extrude_xy(left_vertical_foot_shape, lip_z0, lip_z1)
    right_vertical_foot = _extrude_xy(right_vertical_foot_shape, lip_z0, lip_z1)

    fillet_radius = float(hook["jaw_root_fillet_mm"])
    side_slope = float(cfg["base_interface"]["side_edge_slope_run_per_elevation"])
    jaw_center_y = (y0 + y1) / 2.0
    left_mid, right_mid = overlay_edges_mm(jaw_center_y, cfg)
    left_outer_mid = left_mid - clearance - jaw_thickness
    right_outer_mid = right_mid + clearance + jaw_thickness
    left_fillet = _cylinder_along_elevation(
        # Keep the rounded gusset tangent to, never proud of, the tapered
        # print face so the authored flat remains a real plate-contact patch.
        center_x=left_outer_mid + fillet_radius,
        center_depth=(bridge_z1 + arm_z0) / 2.0,
        elevation_start=y0,
        elevation_end=y1,
        radius=fillet_radius,
        run_slope_per_elevation=side_slope,
    )
    right_fillet = _cylinder_along_elevation(
        center_x=right_outer_mid - fillet_radius,
        center_depth=(bridge_z1 + arm_z0) / 2.0,
        elevation_start=y0,
        elevation_end=y1,
        radius=fillet_radius,
        run_slope_per_elevation=-side_slope,
    )

    center_x = float(cfg["base_interface"]["overlay_width_bottom_mm"]) / 2.0
    center_y = (y0 + y1) / 2.0
    usable_projection = float(
        hook["hook_usable_projection_from_overlay_face_mm"]
    )
    root_radius = float(hook["hook_root_radius_mm"])
    stem_radius = float(hook["hook_stem_radius_mm"])
    tip_radius = float(hook["hook_tip_radius_mm"])
    root_center_d = float(hook["hook_root_center_depth_mm"])
    seat_d = -usable_projection
    tip_rise = float(hook["hook_tip_height_mm"])
    tip_onset_offset = float(hook["hook_tip_onset_outward_of_seat_mm"])
    root = Point(root_center_d, center_y).buffer(root_radius, quad_segs=12)
    stem = LineString(
        [(root_center_d, center_y), (seat_d, center_y)]
    ).buffer(stem_radius, cap_style=1, join_style=1, quad_segs=12)
    tip = LineString(
        [
            (seat_d - tip_onset_offset, center_y),
            (seat_d - tip_onset_offset - tip_rise, center_y + tip_rise),
        ]
    ).buffer(tip_radius, cap_style=1, join_style=1, quad_segs=12)
    hook_profile = unary_union([root, stem, tip]).intersection(
        shapely_box(-100.0, 0.0, -0.2, 100.0)
    )
    hook_mesh = _extrude_yz(
        hook_profile,
        center_x - float(hook["hook_width_across_run_mm"]) / 2.0,
        float(hook["hook_width_across_run_mm"]),
    )
    return {
        "bridge": bridge,
        "left_jaw": left_jaw,
        "right_jaw": right_jaw,
        "left_stop": left_stop,
        "right_stop": right_stop,
        "left_vertical_foot": left_vertical_foot,
        "right_vertical_foot": right_vertical_foot,
        "left_fillet": left_fillet,
        "right_fillet": right_fillet,
        "left_lip": left_lip,
        "right_lip": right_lip,
        "hook": hook_mesh,
    }


def cable_hook_mesh(cfg: dict[str, Any] | None = None) -> trimesh.Trimesh:
    cfg = load_config() if cfg is None else cfg
    components = _collar_components(cfg)
    # Manifold can retain zero-area helper facets where the vertical-stop and
    # rear-lip skins share an exact boundary.  Validate-process removes only
    # those topologically null facets; fail closed if any measurable envelope
    # or volume change accompanies that cleanup.
    return _validated_null_facet_cleanup(
        boolean_union(list(components.values())),
        label="Cable collar-hook",
    )


def cable_bundle_envelope_mesh(
    cfg: dict[str, Any] | None = None,
) -> trimesh.Trimesh:
    """Five-millimetre qualification cable seated on top of the hook stem."""

    cfg = load_config() if cfg is None else cfg
    hook = cfg["cable_hook"]
    y0, y1 = (float(value) for value in hook["collar_band_elevation_mm"])
    center_y = (y0 + y1) / 2.0
    cable_radius = float(hook["maximum_qualified_cable_bundle_diameter_mm"]) / 2.0
    cable_center_y = center_y + float(hook["hook_stem_radius_mm"]) + cable_radius
    seat_d = -float(hook["hook_usable_projection_from_overlay_face_mm"])
    profile = Point(seat_d, cable_center_y).buffer(cable_radius, quad_segs=24)
    center_x = float(cfg["base_interface"]["overlay_width_bottom_mm"]) / 2.0
    width = float(hook["hook_width_across_run_mm"])
    return _extrude_yz(profile, center_x - width / 2.0, width)


def compressed_approach_components(
    cfg: dict[str, Any] | None = None,
) -> tuple[trimesh.Trimesh, ...]:
    """Collision proxy with the two jaws spread for front snap installation.

    This is not a strain or cycle proof.  Physical PETG flex qualification is
    explicitly required before any installed use.
    """

    cfg = load_config() if cfg is None else cfg
    spread = float(cfg["cable_hook"]["compressed_proxy_jaw_spread_each_side_mm"])
    components = _collar_components(cfg)
    fixed = _validated_null_facet_cleanup(
        boolean_union([components["bridge"], components["hook"]]),
        label="Compressed fixed bridge",
    )
    left = _validated_null_facet_cleanup(boolean_union(
        [
            components["left_jaw"],
            components["left_stop"],
            components["left_vertical_foot"],
            components["left_fillet"],
            components["left_lip"],
        ]
    ), label="Compressed left jaw")
    right = _validated_null_facet_cleanup(boolean_union(
        [
            components["right_jaw"],
            components["right_stop"],
            components["right_vertical_foot"],
            components["right_fillet"],
            components["right_lip"],
        ]
    ), label="Compressed right jaw")
    left.apply_translation((-spread, 0.0, 0.0))
    right.apply_translation((spread, 0.0, 0.0))
    return (fixed, left, right)


def reference_pier_overlay_mesh(r6_cfg: dict[str, Any] | None = None) -> trimesh.Trimesh:
    r6_cfg = load_r6_config() if r6_cfg is None else r6_cfg
    return _finish(build_ornament_families(r6_cfg)["pier_overlay"].mesh.copy())


def clearance_ladder_mesh(cfg: dict[str, Any] | None = None) -> trimesh.Trimesh:
    cfg = load_config() if cfg is None else cfg
    clearances = [
        float(value)
        for value in cfg["cable_hook"]["fit_ladder_clearances_per_face_mm"]
    ]
    body = cuboid((48.0, 16.0, 8.0))
    cutters: list[trimesh.Trimesh] = []
    overlay_depth = float(cfg["base_interface"]["overlay_visible_body_depth_mm"])
    for index, clearance in enumerate(clearances):
        slot = overlay_depth + 2.0 * clearance
        center_x = 7.5 + index * 11.0
        cutters.append(
            cuboid(
                (6.0, 9.0, slot),
                origin=(center_x - 3.0, 7.5, 4.0 - slot / 2.0),
            )
        )
    ladder = _finish(boolean_difference(body, cutters))
    if not ladder.is_watertight or not ladder.is_volume or ladder.body_count != 1:
        raise ValueError("Clearance ladder must be one closed positive-volume body")
    return ladder


def saved_hook_mesh(
    mesh: trimesh.Trimesh,
    cfg: dict[str, Any] | None = None,
) -> trimesh.Trimesh:
    """Seat the tapered left run-side jaw face exactly on the build plate."""

    cfg = load_config() if cfg is None else cfg
    saved = mesh.copy()
    vertices = np.asarray(saved.vertices, dtype=float)
    saved.vertices = np.column_stack((vertices[:, 2], vertices[:, 1], vertices[:, 0]))
    rotation_deg = float(cfg["printing"]["saved_left_run_side_rotation_deg"])
    expected_deg = -float(
        np.degrees(np.arctan(float(cfg["base_interface"]["side_edge_slope_run_per_elevation"])))
    )
    if abs(rotation_deg - expected_deg) > 1.0e-10:
        raise ValueError("Saved hook rotation no longer matches the tapered overlay side")
    saved.apply_transform(
        trimesh.transformations.rotation_matrix(
            np.radians(rotation_deg),
            (1.0, 0.0, 0.0),
        )
    )
    return _finish(normalize_mesh(saved))


def qualification_meshes(
    cfg: dict[str, Any] | None = None,
) -> dict[str, trimesh.Trimesh]:
    cfg = load_config() if cfg is None else cfg
    return {
        "R7_DEV_CABLE_PEG_EXACT_R6_PIER_OVERLAY_COUPON": normalize_mesh(
            reference_pier_overlay_mesh()
        ),
        "R7_DEV_CABLE_PEG_FRONT_SNAP_C_COLLAR_HOOK": saved_hook_mesh(
            cable_hook_mesh(cfg), cfg
        ),
        "R7_DEV_CABLE_PEG_COLLAR_CLEARANCE_LADDER_0P2_0P3_0P4_0P5": (
            normalize_mesh(clearance_ladder_mesh(cfg))
        ),
    }


def validate_geometry(cfg: dict[str, Any] | None = None) -> CableHookMetrics:
    cfg = load_config() if cfg is None else cfg
    hook_contract = cfg["cable_hook"]
    bridge_z1 = float(hook_contract["front_bridge_depth_zone_mm"][1])
    arm_z0 = float(hook_contract["flex_arm_depth_zone_mm"][0])
    lip_z0 = float(hook_contract["rear_lip_depth_zone_mm"][0])
    fillet_radius = float(hook_contract["jaw_root_fillet_mm"])
    flex_length = float(hook_contract["flex_arm_effective_length_mm"])
    flex_thickness = float(hook_contract["flex_arm_bending_thickness_mm"])
    jaw_spread = float(hook_contract["compressed_proxy_jaw_spread_each_side_mm"])
    fillet_rear_depth = (bridge_z1 + arm_z0) / 2.0 + fillet_radius
    if abs((lip_z0 - fillet_rear_depth) - flex_length) > EPSILON:
        raise ValueError("Flex-arm effective length is not the live fillet-to-lip span")
    if fillet_radius < 2.0 - EPSILON:
        raise ValueError("Jaw-root fillet falls below the frozen physical screen")
    if not bool(hook_contract["manual_jaw_pre_spread_required"]):
        raise ValueError("The uncamed qualification clip requires manual jaw pre-spread")
    if bool(hook_contract["automatic_insertion_cam_claimed"]):
        raise ValueError("The square rear lips cannot claim automatic cam insertion")
    strain_proxy = 1.5 * flex_thickness * jaw_spread / (flex_length * flex_length)
    if abs(strain_proxy - float(hook_contract["conservative_flex_strain_proxy"])) > 1.0e-12:
        raise ValueError("Cable collar flex-strain proxy drifted")
    if strain_proxy > float(hook_contract["maximum_flex_strain_proxy"]) + EPSILON:
        raise ValueError("Cable collar flex-strain proxy exceeds the qualification screen")
    overlay = reference_pier_overlay_mesh()
    hook = cable_hook_mesh(cfg)
    seated_overlap = positive_overlap_volume_mm3(overlay, hook)
    if seated_overlap > ALLOWED_OVERLAP_MM3:
        raise ValueError(f"Seated collar overlaps overlay by {seated_overlap:.9f} mm3")

    components = _collar_components(cfg)
    cable_envelope = cable_bundle_envelope_mesh(cfg)
    cable_bridge_overlap = positive_overlap_volume_mm3(
        components["bridge"], cable_envelope
    )
    if cable_bridge_overlap > ALLOWED_OVERLAP_MM3:
        raise ValueError(
            "The maximum qualified cable bundle is obstructed by the flex bridge"
        )
    cable_collar_overlap = positive_overlap_volume_mm3(hook, cable_envelope)
    if cable_collar_overlap > ALLOWED_OVERLAP_MM3:
        raise ValueError(
            "The maximum qualified cable bundle is obstructed by the collar or tip"
        )
    y0, y1 = (
        float(value) for value in hook_contract["collar_band_elevation_mm"]
    )
    hook_center_y = (y0 + y1) / 2.0
    seat_d = -float(hook_contract["hook_usable_projection_from_overlay_face_mm"])
    cable_radius = (
        float(hook_contract["maximum_qualified_cable_bundle_diameter_mm"]) / 2.0
    )
    cable_center = Point(
        seat_d,
        hook_center_y + float(hook_contract["hook_stem_radius_mm"]) + cable_radius,
    )
    tip_offset = float(hook_contract["hook_tip_onset_outward_of_seat_mm"])
    tip_rise = float(hook_contract["hook_tip_height_mm"])
    tip_centerline = LineString(
        [
            (seat_d - tip_offset, hook_center_y),
            (seat_d - tip_offset - tip_rise, hook_center_y + tip_rise),
        ]
    )
    cable_tip_clearance = float(cable_center.distance(tip_centerline)) - (
        cable_radius + float(hook_contract["hook_tip_radius_mm"])
    )
    if cable_tip_clearance < float(
        hook_contract["minimum_cable_to_tip_clearance_mm"]
    ) - EPSILON:
        raise ValueError("Qualified cable bundle loses its positive tip clearance")
    bridge_top = float(hook_contract["collar_band_elevation_mm"][0]) + float(
        hook_contract["front_bridge_crossbar_height_mm"]
    )
    cable_bottom = float(cable_envelope.bounds[0, 1])
    authored_cable_gap = float(
        hook_contract["minimum_cable_bundle_clearance_above_bridge_mm"]
    )
    if abs(cable_bottom - bridge_top - authored_cable_gap) > 1.0e-5:
        raise ValueError("Cable-bundle clearance above the front bridge drifted")

    proxy = compressed_approach_components(cfg)
    step = float(cfg["cable_hook"]["snap_motion_sample_step_mm"])
    maximum_approach_overlap = 0.0
    for outward in np.arange(8.0, -EPSILON, -step):
        for component in proxy:
            moving = component.copy()
            moving.apply_translation((0.0, 0.0, -float(outward)))
            maximum_approach_overlap = max(
                maximum_approach_overlap,
                positive_overlap_volume_mm3(overlay, moving),
            )
    if maximum_approach_overlap > ALLOWED_OVERLAP_MM3:
        raise ValueError(
            "Compressed snap approach overlaps the exact R6 overlay by "
            f"{maximum_approach_overlap:.9f} mm3"
        )

    rear_max = float(hook.bounds[1, 2])
    contract_rear_max = float(cfg["clearance_contract"]["collar_rear_solid_max_depth_mm"])
    if abs(rear_max - contract_rear_max) > 1.0e-5:
        raise ValueError("Rear collar depth envelope drifted")
    structure_start = float(cfg["base_interface"]["structure_start_depth_mm"])
    minimum_gap = float(
        cfg["clearance_contract"]["required_minimum_unloaded_clearance_mm"]
    )
    if structure_start - rear_max < minimum_gap - EPSILON:
        raise ValueError("Cable collar violates the chassis isolation gap")

    vertical_clearance = float(hook_contract["vertical_stop_clearance_mm"])
    support_top = float(hook_contract["vertical_stop_support_top_elevation_mm"])
    foot_bottom = float(hook_contract["vertical_stop_foot_bottom_elevation_mm"])
    if abs(foot_bottom - support_top - vertical_clearance) > EPSILON:
        raise ValueError("Vertical-stop foot does not derive from its real support top")
    if (
        abs(
            support_top
            - float(
                cfg["clearance_contract"][
                    "lower_compact_housing_upper_elevation_mm"
                ]
            )
        )
        > EPSILON
    ):
        raise ValueError("Vertical stop is not tied to the R6 compact-housing datum")
    vertical_gate = float(cfg["load_qualification"]["maximum_clip_migration_mm"])
    if vertical_clearance >= vertical_gate - EPSILON:
        raise ValueError("Vertical stop clearance must remain below the migration gate")
    free_overlap = 0.0
    for downward in np.arange(0.0, vertical_clearance + EPSILON, 0.05):
        moving = hook.copy()
        moving.apply_translation((0.0, -float(downward), 0.0))
        free_overlap = max(free_overlap, positive_overlap_volume_mm3(overlay, moving))
    if free_overlap > ALLOWED_OVERLAP_MM3:
        raise ValueError(
            "Vertical stop collides before its authored clearance is consumed by "
            f"{free_overlap:.9f} mm3"
        )
    gate_probe = hook.copy()
    gate_probe.apply_translation((0.0, -vertical_gate, 0.0))
    gate_overlap = positive_overlap_volume_mm3(overlay, gate_probe)
    if gate_overlap <= ALLOWED_OVERLAP_MM3:
        raise ValueError("Vertical stop does not positively arrest the migration gate")

    saved = saved_hook_mesh(hook, cfg)
    plate_z = float(saved.bounds[0, 2])
    on_plate = np.all(
        np.isclose(saved.triangles[:, :, 2], plate_z, atol=1.0e-6), axis=1
    )
    plate_contact_area = float(np.sum(saved.area_faces[on_plate]))
    minimum_plate_contact = float(cfg["printing"]["minimum_plate_contact_area_mm2"])
    if plate_contact_area < minimum_plate_contact - EPSILON:
        raise ValueError(
            "Saved tapered jaw face does not provide the required flat plate contact"
        )
    density = 1.27e-3
    return CableHookMetrics(
        installed_bounds_mm=tuple(
            tuple(float(value) for value in row) for row in hook.bounds
        ),
        saved_bounds_mm=tuple(
            tuple(float(value) for value in row) for row in saved.bounds
        ),
        volume_mm3=float(hook.volume),
        estimated_petg_mass_g=float(hook.volume) * density,
        maximum_seated_overlay_overlap_mm3=seated_overlap,
        maximum_compressed_approach_overlap_mm3=maximum_approach_overlap,
        maximum_free_downward_travel_mm=vertical_clearance,
        downward_stop_overlap_at_gate_mm3=gate_overlap,
        flex_strain_proxy=strain_proxy,
        saved_plate_contact_area_mm2=plate_contact_area,
        maximum_cable_bundle_to_bridge_overlap_mm3=cable_bridge_overlap,
        maximum_cable_bundle_to_collar_overlap_mm3=cable_collar_overlap,
        cable_bundle_to_tip_clearance_mm=cable_tip_clearance,
    )


def all_meshes_closed(meshes: Iterable[trimesh.Trimesh]) -> bool:
    return all(
        mesh.is_watertight and mesh.is_volume and mesh.body_count == 1
        for mesh in meshes
    )
