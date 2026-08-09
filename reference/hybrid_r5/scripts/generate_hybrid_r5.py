#!/usr/bin/env python3
"""Generate the Story Corner PETG finish, model-only 3MFs, and field plans.

The permanent load path is intentionally outside the printed parts:
contents -> plywood / front steel angle -> steel brackets -> steel standards
-> verified wood studs or purpose-installed structural blocking.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import trimesh
from shapely.affinity import scale as shapely_scale
from shapely.affinity import translate as shapely_translate
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry import box as shapely_box
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.hybrid.json"
OUT = ROOT / "generated"
MODEL_3MF = OUT / "model_only_3mf"
PARTS_CATALOG_3MF_NAME = "MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_PARTS_CATALOG.3mf"
FULL_PRINT_SET_3MF_NAME = "MODEL_ONLY_STORY_CORNER_TRIADIC_PALATINE_FULL_PRINT_SET.3mf"

NS_3MF = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"


@dataclass(frozen=True)
class Part:
    name: str
    mesh: trimesh.Trimesh
    run_id: str | None
    repeat_count: int
    purpose: str


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_config() -> dict:
    return json.loads(
        CONFIG_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )


def inches(value: float) -> float:
    return float(value) * 25.4


def cuboid(size: tuple[float, float, float], origin=(0.0, 0.0, 0.0)) -> trimesh.Trimesh:
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(np.asarray(origin, dtype=float) + np.asarray(size, dtype=float) / 2.0)
    return mesh


def rounded_prism(width: float, depth: float, height: float, radius: float) -> trimesh.Trimesh:
    radius = min(radius, width / 2.0 - 0.01, depth / 2.0 - 0.01)
    center = shapely_box(radius, radius, width - radius, depth - radius)
    outline = center.buffer(radius, quad_segs=8)
    mesh = trimesh.creation.extrude_polygon(outline, height=height, engine="earcut")
    mesh.remove_unreferenced_vertices()
    return mesh


def horizontal_slot_cutter(
    length: float,
    width: float,
    height: float,
    *,
    center: tuple[float, float, float],
    angle_deg: float = 0.0,
) -> trimesh.Trimesh:
    """Create a printable capsule-shaped clearance-slot cutter."""
    if length <= width:
        raise ValueError("A clearance slot must be longer than it is wide")
    radius = width / 2.0
    outline = LineString([(radius, radius), (length - radius, radius)]).buffer(
        radius,
        cap_style=1,
        quad_segs=12,
    )
    mesh = trimesh.creation.extrude_polygon(outline, height=height, engine="earcut")
    if abs(angle_deg) > 1e-9:
        mesh.apply_transform(
            trimesh.transformations.rotation_matrix(
                np.deg2rad(angle_deg),
                [0.0, 0.0, 1.0],
                point=[length / 2.0, width / 2.0, 0.0],
            )
        )
    mesh.apply_translation(
        np.asarray(center, dtype=float) - np.asarray([length / 2.0, width / 2.0, height / 2.0])
    )
    return mesh


def boolean_union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    result = trimesh.boolean.union(meshes, engine="manifold", check_volume=True)
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    result.remove_unreferenced_vertices()
    result.merge_vertices()
    result.fix_normals()
    return result


def boolean_difference(body: trimesh.Trimesh, cutters: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    result = trimesh.boolean.difference([body, *cutters], engine="manifold", check_volume=True)
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


def module_layout(
    cfg: dict,
    length_mm: float,
    *,
    rows: int,
    columns_override: int | None,
    label: str,
) -> dict:
    """Resolve a center-bay count and two symmetric field-fit end modules."""
    gap = float(cfg["skin"]["tile_gap_mm"])
    pitch = float(cfg["skin"]["module_pitch_mm"])
    center_module_width = pitch - gap
    min_end = float(cfg["skin"]["minimum_parametric_end_module_width_mm"])
    max_end = float(cfg["skin"]["maximum_parametric_end_module_width_mm"])

    def end_width_for(columns: int) -> float:
        center_columns = columns - 2
        return (
            length_mm - center_columns * center_module_width - (columns - 1) * gap
        ) / 2.0

    if columns_override is not None:
        columns = int(columns_override)
        if columns < 3:
            raise ValueError(f"{label} needs two end modules and at least one reusable center module")
        end_module_width = end_width_for(columns)
    else:
        ideal_columns = length_mm / pitch
        candidate_limit = max(6, int(np.ceil(ideal_columns)) + 5)
        candidates: list[tuple[tuple[float, float], int, float]] = []
        for candidate in range(3, candidate_limit + 1):
            width = end_width_for(candidate)
            if min_end <= width <= max_end:
                score = (abs(candidate - ideal_columns), abs(width - center_module_width))
                candidates.append((score, candidate, width))
        if not candidates:
            raise ValueError(
                f"{label} cannot produce symmetric end modules within "
                f"{min_end:.1f}-{max_end:.1f} mm; adjust the pitch or set a reviewed column override"
            )
        _, columns, end_module_width = min(candidates, key=lambda item: item[0])

    if not min_end <= end_module_width <= max_end:
        raise ValueError(
            f"{label} parametric end module is {end_module_width:.3f} mm; "
            f"change the column override so it remains within {min_end:.1f}-{max_end:.1f} mm"
        )

    center_columns = columns - 2

    reconstructed_length = (
        center_columns * center_module_width
        + 2.0 * end_module_width
        + (columns - 1) * gap
    )
    if abs(reconstructed_length - length_mm) > 0.001:
        raise ValueError(f"{label} module reconstruction does not match its target length")

    return {
        "length_mm": length_mm,
        "module_pitch_mm": pitch,
        "center_module_width_mm": center_module_width,
        "parametric_end_module_width_mm": end_module_width,
        "columns": columns,
        "center_columns": center_columns,
        "end_columns": 2,
        "rows": rows,
    }


def arcade_layout(cfg: dict, length_mm: float, *, bay_count: int, label: str) -> dict:
    """Split a run into equal handed half-arches with explicit finish seams."""
    if bay_count < 1:
        raise ValueError(f"{label} requires at least one arcade bay")
    gap = float(cfg["skin"]["tile_gap_mm"])
    segment_count = bay_count * 2
    segment_width = (length_mm - (segment_count - 1) * gap) / segment_count
    if segment_width <= 0.0:
        raise ValueError(f"{label} has no usable half-arch width")
    reconstructed = segment_count * segment_width + (segment_count - 1) * gap
    if abs(reconstructed - length_mm) > 0.001:
        raise ValueError(f"{label} half-arch reconstruction does not match its target length")
    build = np.asarray(cfg["printer"]["minimum_model_build_envelope_mm"], dtype=float)
    total_height = fascia_total_height(cfg) + float(cfg["palatine"]["arch_drop_mm"])
    if segment_width > build[0] + 1e-6 or total_height > build[1] + 1e-6:
        raise ValueError(
            f"{label} Palatine half-arch is {segment_width:.3f} x {total_height:.3f} mm, "
            "outside the declared saved-orientation build envelope"
        )
    return {
        "length_mm": length_mm,
        "bay_count": bay_count,
        "segment_count": segment_count,
        "half_arch_width_mm": segment_width,
        "bay_pitch_mm": 2.0 * segment_width + gap,
        "segment_seam_mm": gap,
        "left_half_count": bay_count,
        "right_half_count": bay_count,
        "total_height_mm": total_height,
    }


def component_override(run: dict, component: str) -> int | None:
    override = run.get("module_columns_override")
    if isinstance(override, dict):
        value = override.get(component)
        return None if value is None else int(value)
    return None if override is None else int(override)


def wall_back_offset(cfg: dict, run_id: str) -> tuple[float, str]:
    """Return the installed shelf-back offset for one wall/run.

    The two walls are measured independently.  Equal catalog standard
    projections do not guarantee equal installed planes after drywall mud,
    wall bow, shims, and fastener seating are included.
    """
    run = next((candidate for candidate in cfg["closet"]["runs"] if candidate["id"] == run_id), None)
    if run is None:
        raise ValueError(f"Unknown shelf run {run_id!r} in inside-corner offset lookup")
    field_value = run.get("field_verified_installed_shelf_back_offset_in")
    if field_value is not None:
        return float(field_value), "field_verified_per_wall"
    return (
        float(cfg["structural"]["reference_standard_wall_projection_in"]),
        "reference_standard_projection_pending_per_wall_verification",
    )


def run_dimensions(cfg: dict, run: dict) -> dict:
    inside_corner = cfg["closet"]["inside_corner"]
    role = str(run["corner_role"])
    if role not in {"through", "return"}:
        raise ValueError(f"{run['id']} has unsupported inside-corner role {role!r}")

    field_width = run.get("field_verified_min_clear_wall_width_in")
    clear_width_source = "field_verified_minimum_across_adjustment_zone" if field_width is not None else "nominal_pending_field_verification"
    clear_width_in = float(field_width if field_width is not None else run["nominal_clear_wall_width_in"])
    end_clearance = float(run["target_outer_end_clearance_in"])
    depth_in = float(cfg["closet"]["shelf_depth_in"])
    depth_mm = inches(depth_in)
    gap = float(cfg["skin"]["tile_gap_mm"])
    rows = int(cfg["skin"]["tile_depth_rows"])

    through_id = inside_corner["through_run_id"]
    return_id = inside_corner["return_run_id"]
    through_wall_offset_in, through_wall_offset_source = wall_back_offset(cfg, through_id)
    return_wall_offset_in, return_wall_offset_source = wall_back_offset(cfg, return_id)
    if role == "through":
        own_wall_offset_in = through_wall_offset_in
        own_wall_offset_source = through_wall_offset_source
        perpendicular_wall_offset_in = return_wall_offset_in
        perpendicular_wall_offset_source = return_wall_offset_source
    else:
        own_wall_offset_in = return_wall_offset_in
        own_wall_offset_source = return_wall_offset_source
        perpendicular_wall_offset_in = through_wall_offset_in
        perpendicular_wall_offset_source = through_wall_offset_source
    corner_front_plane_in = perpendicular_wall_offset_in + depth_in
    joint_gap_in = float(inside_corner["deck_joint_gap_mm"]) / 25.4

    # The through board begins at the installed shelf-back plane of the
    # perpendicular wall, not at an arbitrary cosmetic wall gap. This makes
    # the through-owned corner square exactly D x D. The return starts beyond
    # the through front line plus a deliberate field-fit gap.
    deck_start = perpendicular_wall_offset_in if role == "through" else corner_front_plane_in + joint_gap_in
    deck_end = clear_width_in - end_clearance
    deck_length = deck_end - deck_start
    if deck_length <= 0.0:
        raise ValueError(f"{run['id']} has no usable deck length after inside-corner fitting allowances")

    # The through-owned D x D corner square receives four dedicated quadrants.
    # Both straight top arms begin one finish seam beyond the common front
    # plane. On the return this lets the PETG overhang the concealed wood gap
    # by only (joint gap - finish seam), without giving it structural credit.
    front_start = corner_front_plane_in if role == "through" else deck_start
    front_end = deck_end
    front_length = front_end - front_start
    top_start = corner_front_plane_in + gap / 25.4
    top_end = deck_end
    top_length = top_end - top_start
    fascia_endcap_in = float(cfg["fascia"]["endcap_thickness_mm"]) / 25.4
    fascia_start = front_start
    fascia_end = front_end - fascia_endcap_in
    fascia_length = fascia_end - fascia_start
    rear_connector_leg_mm = float(cfg["skin"]["rear_curb_inside_corner_leg_mm"])
    rear_corner_straight_start = perpendicular_wall_offset_in + (rear_connector_leg_mm + gap) / 25.4
    rear_start = rear_corner_straight_start if role == "through" else deck_start
    rear_end = deck_end
    rear_length = rear_end - rear_start
    corner_side_rear_start = own_wall_offset_in + (rear_connector_leg_mm + gap) / 25.4
    corner_side_rear_end = own_wall_offset_in + depth_in
    corner_side_rear_length_mm = inches(corner_side_rear_end - corner_side_rear_start)
    if role == "through" and corner_side_rear_length_mm <= 0.0:
        raise ValueError("The rear-curb corner replacement consumes the entire through-owned corner side")
    if min(front_length, top_length, fascia_length, rear_length) <= 0.0:
        raise ValueError(f"{run['id']} has an invalid finish-perimeter length")

    top_layout = module_layout(
        cfg,
        inches(top_length),
        rows=rows,
        columns_override=component_override(run, "top"),
        label=f"{run['id']} top",
    )
    top_layout["module_depth_mm"] = (depth_mm - (rows - 1) * gap) / rows
    arcade_bays = int(
        cfg["palatine"]["long_arm_arcade_bays"]
        if role == "through"
        else cfg["palatine"]["short_arm_arcade_bays"]
    )
    palatine_arcade_layout = arcade_layout(
        cfg,
        inches(fascia_length),
        bay_count=arcade_bays,
        label=f"{run['id']} Triadic Palatine arcade",
    )
    rear_layout = module_layout(
        cfg,
        inches(rear_length),
        rows=1,
        columns_override=component_override(run, "rear_curb"),
        label=f"{run['id']} rear curb",
    )

    field_supports = [float(value) for value in run.get("field_verified_support_centers_in", [])]
    if not all(np.isfinite(value) for value in field_supports):
        raise ValueError(f"{run['id']} field support centers must all be finite numbers")
    support_count = len(field_supports) if field_supports else int(run["support_count"])
    if support_count < 2:
        raise ValueError(f"{run['id']} requires at least two independently supported lines")
    maximum_spacing = float(cfg["structural"]["maximum_support_spacing_in"])
    if field_supports:
        support_centers = sorted(field_supports)
        minimum_distinct_spacing = float(cfg["structural"]["minimum_distinct_support_center_spacing_in"])
        field_center_gaps = [
            support_centers[index + 1] - support_centers[index]
            for index in range(len(support_centers) - 1)
        ]
        if field_center_gaps and min(field_center_gaps) < minimum_distinct_spacing - 1e-9:
            raise ValueError(
                f"{run['id']} field support centers are duplicated or closer than the "
                f"{minimum_distinct_spacing:.3f} in independent-support development guard"
            )
        if any(center < deck_start or center > deck_end for center in support_centers):
            raise ValueError(
                f"{run['id']} has a field support center outside its deck; "
                "centers are absolute distances from the inside finished-wall corner"
            )
        support_spacings = field_center_gaps
        left_overhang = support_centers[0] - deck_start
        right_overhang = deck_end - support_centers[-1]
        support_geometry_source = "field_verified"
    else:
        preferred_overhang = float(cfg["structural"]["preferred_end_overhang_in"])
        preferred_spacing = (deck_length - 2.0 * preferred_overhang) / (support_count - 1)
        if preferred_spacing <= maximum_spacing:
            support_spacing = preferred_spacing
            left_overhang = preferred_overhang
            right_overhang = preferred_overhang
        else:
            support_spacing = maximum_spacing
            left_overhang = (deck_length - support_spacing * (support_count - 1)) / 2.0
            right_overhang = left_overhang
        if min(left_overhang, right_overhang) < 0.0:
            raise ValueError(f"{run['id']} has too many supports for the selected nominal placement rule")
        support_centers = [deck_start + left_overhang + index * support_spacing for index in range(support_count)]
        support_spacings = [support_spacing] * max(0, support_count - 1)
        support_geometry_source = "nominal_desired_geometry_not_drill_coordinates"

    max_overhang = float(cfg["structural"]["maximum_end_overhang_in"])
    if support_spacings and max(support_spacings) > maximum_spacing + 1e-6:
        raise ValueError(f"{run['id']} support spacing exceeds {maximum_spacing:.3f} in")
    if max(left_overhang, right_overhang) > max_overhang + 1e-6:
        raise ValueError(f"{run['id']} end overhang exceeds {max_overhang:.3f} in")

    return {
        "clear_width_basis_in": clear_width_in,
        "clear_width_source": clear_width_source,
        "corner_role": role,
        "installed_shelf_back_offset_in": own_wall_offset_in,
        "installed_shelf_back_offset_source": own_wall_offset_source,
        "perpendicular_wall_installed_shelf_back_offset_in": perpendicular_wall_offset_in,
        "perpendicular_wall_installed_shelf_back_offset_source": perpendicular_wall_offset_source,
        "through_wall_installed_shelf_back_offset_in": through_wall_offset_in,
        "return_wall_installed_shelf_back_offset_in": return_wall_offset_in,
        "corner_front_plane_from_inside_corner_in": corner_front_plane_in,
        "deck_start_from_inside_corner_in": deck_start,
        "deck_end_from_inside_corner_in": deck_end,
        "deck_length_in": deck_length,
        "finished_length_in": deck_length,
        "length_mm": inches(deck_length),
        "depth_mm": depth_mm,
        "deck_joint_gap_in": joint_gap_in,
        "front_perimeter_start_from_inside_corner_in": front_start,
        "front_perimeter_end_from_inside_corner_in": front_end,
        "front_perimeter_length_in": front_length,
        "fascia_straight_start_from_inside_corner_in": fascia_start,
        "fascia_straight_end_from_inside_corner_in": fascia_end,
        "fascia_straight_length_in": fascia_length,
        "fascia_outer_endcap_thickness_mm": float(cfg["fascia"]["endcap_thickness_mm"]),
        "top_arm_start_from_inside_corner_in": top_start,
        "top_arm_end_from_inside_corner_in": top_end,
        "top_arm_length_in": top_length,
        "corner_to_top_arm_finish_seam_mm": gap,
        "top_inner_overhang_into_wood_joint_mm": max(0.0, (deck_start - top_start) * 25.4),
        "owns_corner_top_zone": role == "through",
        "corner_top_zone_size_in": depth_in if role == "through" else 0.0,
        "rear_curb_start_from_inside_corner_in": rear_start,
        "rear_curb_end_from_inside_corner_in": rear_end,
        "rear_curb_length_in": rear_length,
        "rear_curb_corner_connector_leg_mm": rear_connector_leg_mm,
        "rear_curb_connector_to_straight_seam_mm": gap,
        "owns_corner_side_rear_curb": role == "through",
        "corner_side_rear_curb_start_from_inside_corner_in": corner_side_rear_start if role == "through" else None,
        "corner_side_rear_curb_end_from_inside_corner_in": corner_side_rear_end if role == "through" else None,
        "corner_side_rear_curb_length_mm": corner_side_rear_length_mm if role == "through" else 0.0,
        "top_layout": top_layout,
        "palatine_arcade_layout": palatine_arcade_layout,
        "rear_curb_layout": rear_layout,
        "support_geometry_source": support_geometry_source,
        "support_spacings_in": support_spacings,
        "left_end_overhang_in": left_overhang,
        "right_end_overhang_in": right_overhang,
        "nominal_support_centers_in": support_centers,
        "support_centers_local_to_deck_start_in": [center - deck_start for center in support_centers],
    }


def corner_geometry(cfg: dict, dimensions: dict[str, dict]) -> dict:
    corner = cfg["closet"]["inside_corner"]
    roles = [d["corner_role"] for d in dimensions.values()]
    if roles.count("through") != 1 or roles.count("return") != 1:
        raise ValueError("The fitted L needs exactly one through run and exactly one return run")
    through = dimensions[corner["through_run_id"]]
    return_run = dimensions[corner["return_run_id"]]
    angle = corner.get("field_verified_angle_deg")
    angle_source = "field_verified" if angle is not None else "nominal_pending_field_verification"
    angle = float(angle if angle is not None else corner["nominal_angle_deg"])
    if not 75.0 <= angle <= 105.0:
        raise ValueError("The fitted L-corner parts support only reviewed near-square inside corners (75-105 degrees)")
    maximum_square_deviation = float(corner["maximum_square_corner_deviation_deg"])
    depth_mm = inches(cfg["closet"]["shelf_depth_in"])
    joint_gap_mm = float(corner["deck_joint_gap_mm"])
    minimum_residual_gap_mm = float(corner["minimum_residual_joint_clearance_mm"])
    if not 0.0 < minimum_residual_gap_mm < joint_gap_mm:
        raise ValueError("The residual corner-joint clearance must be positive and smaller than the nominal joint gap")
    physical_overlap_limit_deg = float(np.rad2deg(np.arctan(joint_gap_mm / depth_mm)))
    residual_clearance_limit_deg = float(
        np.rad2deg(np.arctan((joint_gap_mm - minimum_residual_gap_mm) / depth_mm))
    )
    if maximum_square_deviation > residual_clearance_limit_deg + 1e-9:
        raise ValueError(
            f"Configured corner policy +/-{maximum_square_deviation:.3f} degrees would leave less than "
            f"{minimum_residual_gap_mm:.3f} mm of the {joint_gap_mm:.3f} mm joint gap"
        )
    angle_deviation_deg = abs(angle - 90.0)
    angular_edge_shift_mm = float(depth_mm * np.tan(np.deg2rad(angle_deviation_deg)))
    residual_joint_clearance_mm = joint_gap_mm - angular_edge_shift_mm
    if corner.get("field_verified_angle_deg") is not None and abs(angle - 90.0) > maximum_square_deviation:
        raise ValueError(
            f"Field corner angle {angle:.3f} degrees exceeds the +/-{maximum_square_deviation:.3f}-degree "
            "square-deck prototype limit; make a full-size template and revise the corner footprints before production"
        )
    if corner.get("field_verified_angle_deg") is not None and residual_joint_clearance_mm < minimum_residual_gap_mm - 1e-6:
        raise ValueError(
            f"Field corner angle {angle:.3f} degrees leaves only {residual_joint_clearance_mm:.3f} mm of nominal "
            f"joint clearance; the square footprints require at least {minimum_residual_gap_mm:.3f} mm"
        )

    field_reach = cfg["structural"].get("field_verified_bracket_reach_in")
    bracket_reach = float(
        field_reach if field_reach is not None else cfg["structural"]["reference_bracket_reach_in"]
    )
    bracket_reach_source = "field_verified" if field_reach is not None else "reference_pending_field_verification"
    return_first_support = min(return_run["nominal_support_centers_in"])
    nominal_bracket_clearance = return_first_support - (
        through["installed_shelf_back_offset_in"] + bracket_reach
    )
    conservative_shelf_envelope_clearance = return_first_support - through["corner_front_plane_from_inside_corner_in"]
    minimum_clearance = float(cfg["structural"]["minimum_nominal_corner_bracket_clearance_in"])
    if min(nominal_bracket_clearance, conservative_shelf_envelope_clearance) < minimum_clearance - 1e-6:
        raise ValueError(
            "Inside-corner bracket bodies may collide: nominal clearance is "
            f"{min(nominal_bracket_clearance, conservative_shelf_envelope_clearance):.3f} in, "
            f"below the {minimum_clearance:.3f} in design minimum"
        )

    configured_bay_total = int(cfg["palatine"]["total_arcade_bays"])
    resolved_bay_total = sum(
        int(dimensions[run_id]["palatine_arcade_layout"]["bay_count"])
        for run_id in (corner["through_run_id"], corner["return_run_id"])
    )
    if resolved_bay_total != configured_bay_total:
        raise ValueError(
            f"Triadic Palatine arcade resolves to {resolved_bay_total} bays, not configured total {configured_bay_total}"
        )
    groin_size_mm = float(cfg["palatine"]["groin_vault_size_mm"])
    finish_seam_mm = float(cfg["skin"]["tile_gap_mm"])
    front_station = through["corner_front_plane_from_inside_corner_in"]
    corner_zone_supports = [
        center for center in through["nominal_support_centers_in"] if center < front_station
    ]
    if not corner_zone_supports:
        raise ValueError("The through-owned corner needs a verified support plane before the front line")
    nearest_corner_support = max(corner_zone_supports)
    groin_inner_station = front_station - (groin_size_mm + finish_seam_mm) / 25.4
    groin_bracket_clearance_mm = (groin_inner_station - nearest_corner_support) * 25.4
    minimum_groin_clearance_mm = float(cfg["palatine"]["minimum_groin_vault_bracket_clearance_mm"])
    if groin_bracket_clearance_mm < minimum_groin_clearance_mm - 1e-6:
        raise ValueError(
            f"Palatine groin-vault soffit leaves {groin_bracket_clearance_mm:.3f} mm to the nearest "
            f"through support plane, below the {minimum_groin_clearance_mm:.3f} mm development minimum"
        )

    return {
        "strategy": "5 ft through-deck plus 3 ft return deck with an unloaded fit gap; both runs retain independent steel-bracket support",
        "coordinate_datum": corner["coordinate_datum"],
        "plan_handedness": corner["plan_handedness"],
        "coordinate_axes": corner["coordinate_axes"],
        "inside_angle_deg": angle,
        "inside_angle_source": angle_source,
        "angle_deviation_from_square_deg": angle_deviation_deg,
        "maximum_square_corner_deviation_deg": maximum_square_deviation,
        "physical_overlap_limit_from_joint_gap_deg": physical_overlap_limit_deg,
        "residual_clearance_policy_limit_deg": residual_clearance_limit_deg,
        "angular_edge_shift_across_depth_mm": angular_edge_shift_mm,
        "minimum_residual_joint_clearance_mm": minimum_residual_gap_mm,
        "remaining_nominal_joint_clearance_mm": residual_joint_clearance_mm,
        "installed_shelf_back_offsets_in": {
            corner["through_run_id"]: through["installed_shelf_back_offset_in"],
            corner["return_run_id"]: return_run["installed_shelf_back_offset_in"],
        },
        "corner_zone_bounds_in": {
            "long_wall_axis": [
                through["deck_start_from_inside_corner_in"],
                through["corner_front_plane_from_inside_corner_in"],
            ],
            "short_wall_axis": [
                return_run["perpendicular_wall_installed_shelf_back_offset_in"],
                return_run["corner_front_plane_from_inside_corner_in"],
            ],
        },
        "corner_front_planes_in": {
            "long_wall_axis": through["corner_front_plane_from_inside_corner_in"],
            "short_wall_axis": return_run["corner_front_plane_from_inside_corner_in"],
        },
        "deck_joint_gap_mm": float(corner["deck_joint_gap_mm"]),
        "top_arm_finish_seam_mm": float(cfg["skin"]["tile_gap_mm"]),
        "return_top_tile_overhang_into_joint_mm": return_run["top_inner_overhang_into_wood_joint_mm"],
        "bracket_reach_in": bracket_reach,
        "bracket_reach_source": bracket_reach_source,
        "nominal_nearest_bracket_body_clearance_in": nominal_bracket_clearance,
        "nominal_nearest_conservative_8in_shelf_envelope_clearance_in": conservative_shelf_envelope_clearance,
        "minimum_nominal_corner_bracket_clearance_in": minimum_clearance,
        "through_corner_top_zone_size_in": through["corner_top_zone_size_in"],
        "return_deck_start_from_inside_corner_in": return_run["deck_start_from_inside_corner_in"],
        "deck_footprint_overlap_in": 0.0,
        "palatine_arcade_total_bays": resolved_bay_total,
        "palatine_groin_vault_footprint_station_in": [
            groin_inner_station,
            front_station - finish_seam_mm / 25.4,
        ],
        "palatine_groin_vault_nearest_support_station_in": nearest_corner_support,
        "palatine_groin_vault_bracket_clearance_mm": groin_bracket_clearance_mm,
        "minimum_palatine_groin_vault_bracket_clearance_mm": minimum_groin_clearance_mm,
        "load_path_note": "PETG corner parts cover and align finish seams only; they do not tie, support, or rate the plywood-and-steel structure.",
    }


def fascia_opening_height(cfg: dict) -> float:
    deck_mm = inches(cfg["structural"]["deck_thickness_in"])
    angle_vertical_leg_mm = inches(1.0)
    tile_mm = float(cfg["skin"]["tile_thickness_mm"])
    return (
        deck_mm
        + angle_vertical_leg_mm
        + tile_mm
        + float(cfg["fascia"]["fitting_clearance_mm"])
    )


def fascia_total_height(cfg: dict) -> float:
    f = cfg["fascia"]
    return (
        float(f["flange_thickness_mm"]) * 2.0
        + fascia_opening_height(cfg)
        + float(f["front_lip_height_mm"])
    )


def top_tile(cfg: dict, width: float, depth: float) -> trimesh.Trimesh:
    skin = cfg["skin"]
    return rounded_prism(
        width,
        depth,
        float(skin["tile_thickness_mm"]),
        radius=float(skin["top_tile_plan_radius_mm"]),
    )


def corner_top_quadrant(cfg: dict) -> trimesh.Trimesh:
    skin = cfg["skin"]
    depth_mm = inches(cfg["closet"]["shelf_depth_in"])
    gap = float(skin["tile_gap_mm"])
    quadrant = (depth_mm - gap) / 2.0
    return rounded_prism(
        quadrant,
        quadrant,
        float(skin["tile_thickness_mm"]),
        radius=float(skin["corner_mating_radius_mm"]),
    )


def fascia(cfg: dict, width: float) -> trimesh.Trimesh:
    f = cfg["fascia"]
    face_t = float(f["face_thickness_mm"])
    flange_t = float(f["flange_thickness_mm"])
    opening_h = fascia_opening_height(cfg)
    channel_d = float(f["channel_depth_mm"])
    top_d = float(f["top_flange_depth_mm"])
    total_h = fascia_total_height(cfg)

    # Saved with the broad front face on the build plate. The channel flanges
    # grow in Z in this orientation, avoiding support material.
    face = cuboid((width, total_h, face_t))
    bottom = cuboid((width, flange_t, channel_d))
    top_y = flange_t + opening_h
    top = cuboid((width, flange_t, top_d), origin=(0.0, top_y, 0.0))
    # The upper and lower flanges capture the finish channel around the real
    # plywood/tile/angle stack. Lateral endcaps and a qualified removable
    # silicone dot prevent creep and rattle; the continuous steel angle is not
    # drilled or notched for cosmetic retention.
    return boolean_union([face, bottom, top])


def segmental_arch_opening(
    bay_width: float,
    shared_pier_width: float,
    crown_y: float,
    rise: float,
    *,
    bottom_y: float = -1.0,
) -> tuple[Polygon, float, float]:
    """Return a circular-segment arch opening with vertical jambs.

    A segmental Roman arch keeps the shared pier narrow enough for the 3/6/9
    bay rhythm while the integrated fascia remains inside a 180 mm printer.
    """
    half_span = (bay_width - shared_pier_width) / 2.0
    if min(half_span, rise) <= 0.0:
        raise ValueError("Palatine arch span and rise must be positive")
    radius = (half_span**2 + rise**2) / (2.0 * rise)
    center_x = bay_width / 2.0
    center_y = crown_y - radius
    spring_y = crown_y - rise
    right_angle = float(np.arctan2(spring_y - center_y, half_span))
    angles = np.linspace(np.pi - right_angle, right_angle, 96)
    arc = [
        (center_x + radius * np.cos(angle), center_y + radius * np.sin(angle))
        for angle in angles
    ]
    opening = Polygon(
        [
            (center_x - half_span, bottom_y),
            (center_x - half_span, spring_y),
            *arc,
            (center_x + half_span, bottom_y),
        ]
    ).buffer(0)
    if opening.geom_type != "Polygon":
        raise ValueError("Segmental Palatine arch opening did not resolve to one polygon")
    return opening, spring_y, radius


def palatine_arcade_profile(cfg: dict, half_width: float, handedness: str) -> Polygon:
    p = cfg["palatine"]
    seam = float(p["arch_half_seam_mm"])
    bay_width = 2.0 * half_width + seam
    drop = float(p["arch_drop_mm"])
    overlap = float(p["arch_overlap_into_fascia_mm"])
    crown_y = drop
    profile_top = drop + overlap
    shared_pier = float(p["pier_width_mm"])
    opening, spring_y, _ = segmental_arch_opening(
        bay_width,
        shared_pier,
        crown_y,
        float(p["arch_rise_mm"]),
    )
    outer = shapely_box(0.0, 0.0, bay_width, profile_top)
    inner_band = float(p["archivolt_inner_band_mm"])
    shadow_slot = float(p["archivolt_shadow_slot_mm"])
    ring_slot = (
        opening.buffer(inner_band + shadow_slot, join_style=1)
        .difference(opening.buffer(inner_band, join_style=1))
        .intersection(shapely_box(-1.0, spring_y + 2.0, bay_width + 1.0, profile_top + 1.0))
    )
    # A central keystone bridge and the two lower imposts keep each inner
    # archivolt connected to its half-panel while preserving a true shadow gap.
    center_x = bay_width / 2.0
    keystone_bridge = float(p["keystone_width_mm"]) * 0.72
    ring_slot = ring_slot.difference(
        shapely_box(
            center_x - keystone_bridge / 2.0,
            spring_y,
            center_x + keystone_bridge / 2.0,
            profile_top + 1.0,
        )
    )
    body = outer.difference(opening).difference(ring_slot)

    # Classical bases and capitals are silhouette, not applied decoration.
    # At a bay boundary, the two neighboring half-piers reconstruct one full
    # column while preserving the 0.6 mm finish seam between printed pieces.
    base_projection = float(p["pier_base_projection_mm"])
    base_height = float(p["pier_base_height_mm"])
    capital_projection = float(p["pier_capital_projection_mm"])
    capital_height = float(p["pier_capital_height_mm"])
    pier_half = shared_pier / 2.0
    classical_orders = unary_union(
        [
            shapely_box(0.0, 0.0, pier_half + base_projection, base_height),
            shapely_box(
                bay_width - pier_half - base_projection,
                0.0,
                bay_width,
                base_height,
            ),
            shapely_box(
                0.0,
                spring_y - capital_height,
                pier_half + capital_projection,
                spring_y + 1.0,
            ),
            shapely_box(
                bay_width - pier_half - capital_projection,
                spring_y - capital_height,
                bay_width,
                spring_y + 1.0,
            ),
        ]
    )
    body = body.union(classical_orders)

    # One 3:4:5 void in each spandrel makes the triangulation explicit without
    # asking decorative PETG to carry the shelf load.
    triangle_scale = 7.5
    horizontal_leg = 4.0 * triangle_scale
    vertical_leg = 3.0 * triangle_scale
    triangle_y = profile_top - 11.0
    left_triangle = Polygon(
        [
            (pier_half + 3.0, triangle_y),
            (pier_half + 3.0 + horizontal_leg, triangle_y),
            (pier_half + 3.0, triangle_y - vertical_leg),
        ]
    )
    right_triangle = Polygon(
        [
            (bay_width - pier_half - 3.0, triangle_y),
            (bay_width - pier_half - 3.0 - horizontal_leg, triangle_y),
            (bay_width - pier_half - 3.0, triangle_y - vertical_leg),
        ]
    )
    body = body.difference(left_triangle).difference(right_triangle)

    flute_width = float(p["pier_flute_width_mm"])
    flute_bottom = base_height + 3.0
    flute_top = spring_y - capital_height - 2.0
    flute_height = max(8.0, flute_top - flute_bottom)
    flute_cutters = []
    for index in range(3):
        offset = (index + 1) * pier_half / 4.0
        flute_cutters.append(
            shapely_box(
                offset - flute_width / 2.0,
                flute_bottom,
                offset + flute_width / 2.0,
                flute_bottom + flute_height,
            )
        )
        mirrored = bay_width - offset
        flute_cutters.append(
            shapely_box(
                mirrored - flute_width / 2.0,
                flute_bottom,
                mirrored + flute_width / 2.0,
                flute_bottom + flute_height,
            )
        )
    body = body.difference(unary_union(flute_cutters)).buffer(0)

    right_start = half_width + seam
    clipped = body.intersection(shapely_box(right_start, 0.0, bay_width, profile_top))
    local = shapely_translate(clipped, xoff=-right_start)
    if handedness == "left":
        local = shapely_scale(local, xfact=-1.0, yfact=1.0, origin=(half_width / 2.0, 0.0))
    elif handedness != "right":
        raise ValueError(f"Unsupported Palatine half-arch handedness {handedness!r}")
    if local.geom_type != "Polygon":
        raise ValueError(f"Palatine {handedness} half-arch did not resolve to one connected polygon")
    return local


def palatine_arcade_fascia_half(cfg: dict, half_width: float, handedness: str) -> trimesh.Trimesh:
    profile = palatine_arcade_profile(cfg, half_width, handedness)
    web = trimesh.creation.extrude_polygon(
        profile,
        height=float(cfg["palatine"]["arch_panel_thickness_mm"]),
        engine="earcut",
    )
    channel = fascia(cfg, half_width)
    channel.apply_translation((0.0, float(cfg["palatine"]["arch_drop_mm"]), 0.0))
    return normalize_mesh(boolean_union([web, channel]))


def palatine_entablature_overlay(cfg: dict, width: float) -> trimesh.Trimesh:
    p = cfg["palatine"]
    height = float(p["entablature_overlay_height_mm"])
    base_t = float(p["entablature_overlay_base_mm"])
    relief = float(p["entablature_overlay_relief_mm"])
    base = rounded_prism(width, height, base_t, radius=0.8)
    details: list[trimesh.Trimesh] = []
    # Three continuous orders: architrave, frieze, and corona/cavetto line.
    for y in (0.0, height / 2.0 - 1.2, height - 2.4):
        details.append(cuboid((width, 2.4, relief), origin=(0.0, y, base_t)))
    # Nine dentils preserve the 3-6-9 grammar on every removable half-arch.
    dentils = int(p["dentils_per_half_arch"])
    pitch = width / dentils
    dentil_width = max(float(p["minimum_relief_feature_mm"]), pitch * 0.54)
    for index in range(dentils):
        x = (index + 0.5) * pitch - dentil_width / 2.0
        details.append(cuboid((dentil_width, 4.0, relief), origin=(x, height - 7.2, base_t)))
    # Three triglyph groups, each expressed by three narrow vertical ribs.
    for group in range(3):
        center = (group + 0.5) * width / 3.0
        for rib in (-1, 0, 1):
            x = center + rib * 2.2 - 0.6
            details.append(cuboid((1.2, 7.0, relief), origin=(x, 4.0, base_t)))
    # A shallow central patera gives the modular overlay a calm focal point;
    # attachment remains one qualified removable silicone dot behind the
    # plate, so there is no through-hole and no drilling of the steel angle.
    patera = trimesh.creation.cylinder(
        radius=float(p["entablature_patera_diameter_mm"]) / 2.0,
        height=relief,
        sections=48,
    )
    patera.apply_translation((width / 2.0, height / 2.0, base_t + relief / 2.0))
    details.append(patera)
    return normalize_mesh(boolean_union([base, *details]))


def palatine_keystone(cfg: dict) -> trimesh.Trimesh:
    p = cfg["palatine"]
    width = float(p["keystone_width_mm"])
    height = float(p["keystone_height_mm"])
    outline = Polygon(
        [
            (3.0, 0.0),
            (width - 3.0, 0.0),
            (width, height),
            (0.0, height),
        ]
    )
    return normalize_mesh(
        trimesh.creation.extrude_polygon(
            outline,
            height=float(p["keystone_thickness_mm"]),
            engine="earcut",
        )
    )


def palatine_fascia_endcap(cfg: dict) -> trimesh.Trimesh:
    f = cfg["fascia"]
    p = cfg["palatine"]
    drop = float(p["arch_drop_mm"])
    functional_height = fascia_total_height(cfg)
    channel_depth = float(f["channel_depth_mm"])
    thickness = float(f["endcap_thickness_mm"])
    web = float(p["arch_panel_thickness_mm"])
    lower_return = cuboid((drop, web, thickness))
    upper_cap = rounded_prism(
        functional_height,
        channel_depth,
        thickness,
        radius=1.2,
    )
    upper_cap.apply_translation((drop, 0.0, 0.0))
    return normalize_mesh(boolean_union([lower_return, upper_cap]))


def palatine_groin_vault_corner_soffit(cfg: dict) -> trimesh.Trimesh:
    p = cfg["palatine"]
    size = float(p["groin_vault_size_mm"])
    base_t = float(p["groin_vault_base_mm"])
    relief = float(p["groin_vault_relief_mm"])
    base = rounded_prism(size, size, base_t, radius=1.2)
    details: list[trimesh.Trimesh] = []
    for coordinates in (
        [(3.0, 3.0), (size - 3.0, size - 3.0)],
        [(3.0, size - 3.0), (size - 3.0, 3.0)],
    ):
        outline = LineString(coordinates).buffer(1.2, cap_style=1, quad_segs=8)
        rib = trimesh.creation.extrude_polygon(outline, height=relief, engine="earcut")
        rib.apply_translation((0.0, 0.0, base_t))
        details.append(rib)
    border = 2.0
    for origin, extents in (
        ((0.0, 0.0, base_t), (size, border, relief)),
        ((0.0, size - border, base_t), (size, border, relief)),
        ((0.0, 0.0, base_t), (border, size, relief)),
        ((size - border, 0.0, base_t), (border, size, relief)),
    ):
        details.append(cuboid(extents, origin=origin))
    center = size / 2.0
    boss = trimesh.creation.cylinder(radius=3.6, height=relief, sections=48)
    boss.apply_translation((center, center, base_t + relief / 2.0))
    details.append(boss)
    for index in range(int(p["corner_rosette_petals"])):
        angle = index * 2.0 * np.pi / float(p["corner_rosette_petals"])
        petal = rounded_prism(5.0, 2.2, relief, radius=1.0)
        petal.apply_translation((-2.5, -1.1, base_t))
        petal.apply_transform(
            trimesh.transformations.rotation_matrix(angle, [0.0, 0.0, 1.0])
        )
        petal.apply_translation((center + 4.8 * np.cos(angle), center + 4.8 * np.sin(angle), 0.0))
        details.append(petal)
    body = boolean_union([base, *details])
    slot_length = float(cfg["skin"]["rear_curb_fastener_slot_length_mm"])
    slot_width = float(cfg["skin"]["rear_curb_fastener_slot_width_mm"])
    cutters = [
        horizontal_slot_cutter(
            slot_length,
            slot_width,
            base_t + relief + 2.0,
            center=(size * fraction, 5.5, (base_t + relief) / 2.0),
        )
        for fraction in (0.32, 0.68)
    ]
    return normalize_mesh(boolean_difference(body, cutters))


def palatine_detail_coupon(cfg: dict) -> trimesh.Trimesh:
    width = 75.9
    height = float(cfg["palatine"]["arch_drop_mm"]) + float(
        cfg["palatine"]["arch_overlap_into_fascia_mm"]
    )
    web = float(cfg["palatine"]["arch_panel_thickness_mm"])
    profile = palatine_arcade_profile(cfg, width, "right")
    panel = trimesh.creation.extrude_polygon(profile, height=web, engine="earcut")
    overlay = palatine_entablature_overlay(cfg, width)
    overlay.apply_translation((0.0, height - float(cfg["palatine"]["entablature_overlay_height_mm"]), 0.0))
    return normalize_mesh(boolean_union([panel, overlay]))


def rear_curb(cfg: dict, width: float) -> trimesh.Trimesh:
    skin = cfg["skin"]
    thickness = float(skin["rear_curb_thickness_mm"])
    base_depth = float(skin["rear_curb_base_depth_mm"])
    height = float(skin["rear_curb_height_mm"])
    base = cuboid((width, base_depth, thickness))
    upright = cuboid((width, thickness, height))
    body = boolean_union([base, upright])
    if width >= 30.0:
        slot = horizontal_slot_cutter(
            float(skin["rear_curb_fastener_slot_length_mm"]),
            float(skin["rear_curb_fastener_slot_width_mm"]),
            thickness + 2.0,
            center=(width / 2.0, base_depth * 0.65, thickness / 2.0),
        )
        body = boolean_difference(body, [slot])
    return body


def corner_angle_deg(cfg: dict) -> float:
    corner = cfg["closet"]["inside_corner"]
    verified = corner.get("field_verified_angle_deg")
    return float(verified if verified is not None else corner["nominal_angle_deg"])


def angle_strip_polygon(leg: float, strip_width: float, angle_deg: float):
    arm = shapely_box(0.0, 0.0, leg, strip_width)
    if abs(angle_deg - 90.0) < 1e-9:
        # Avoid floating-point sliver edges at the nominal square corner.
        second_arm = shapely_box(0.0, 0.0, strip_width, leg)
    else:
        angle_rad = np.deg2rad(angle_deg)
        direction = np.array([np.cos(angle_rad), np.sin(angle_rad)])
        inward_normal = np.array([np.sin(angle_rad), -np.cos(angle_rad)])
        second_arm = Polygon(
            [
                (0.0, 0.0),
                tuple(direction * leg),
                tuple(direction * leg + inward_normal * strip_width),
                tuple(inward_normal * strip_width),
            ]
        )
    polygon = unary_union([arm, second_arm]).buffer(0)
    if polygon.geom_type != "Polygon":
        raise ValueError(f"Corner angle {angle_deg:.3f} degrees did not produce a single printable polygon")
    return polygon


def extrude_angle_strip(leg: float, strip_width: float, height: float, angle_deg: float) -> trimesh.Trimesh:
    mesh = trimesh.creation.extrude_polygon(
        angle_strip_polygon(leg, strip_width, angle_deg),
        height=height,
        engine="earcut",
    )
    return normalize_mesh(mesh)


def fascia_outside_corner_cover(cfg: dict) -> trimesh.Trimesh:
    skin = cfg["skin"]
    total_h = fascia_total_height(cfg) + float(cfg["palatine"]["arch_drop_mm"])
    mesh = extrude_angle_strip(
        float(skin["fascia_outside_corner_cover_leg_mm"]),
        float(skin["fascia_outside_corner_cover_thickness_mm"]),
        total_h,
        corner_angle_deg(cfg),
    )
    # Save with one tall face on the build plate instead of balancing the
    # 74 mm-tall shell on its 18 x 18 mm end footprint.
    mesh.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1.0, 0.0, 0.0]))
    return normalize_mesh(mesh)


def rear_curb_inside_corner_connector(cfg: dict) -> trimesh.Trimesh:
    skin = cfg["skin"]
    leg = float(skin["rear_curb_inside_corner_leg_mm"])
    base_depth = float(skin["rear_curb_base_depth_mm"])
    thickness = float(skin["rear_curb_thickness_mm"])
    height = float(skin["rear_curb_height_mm"])
    angle = corner_angle_deg(cfg)
    base = trimesh.creation.extrude_polygon(
        angle_strip_polygon(leg, base_depth, angle),
        height=thickness,
        engine="earcut",
    )
    upright = trimesh.creation.extrude_polygon(
        angle_strip_polygon(leg, thickness, angle),
        height=height,
        engine="earcut",
    )
    body = boolean_union([base, upright])
    slot_length = float(skin["rear_curb_fastener_slot_length_mm"])
    slot_width = float(skin["rear_curb_fastener_slot_width_mm"])
    slots = [
        horizontal_slot_cutter(
            slot_length,
            slot_width,
            thickness + 2.0,
            center=(leg * 0.58, base_depth * 0.65, thickness / 2.0),
        ),
        horizontal_slot_cutter(
            slot_length,
            slot_width,
            thickness + 2.0,
            center=(base_depth * 0.65, leg * 0.58, thickness / 2.0),
            angle_deg=90.0,
        ),
    ]
    return normalize_mesh(boolean_difference(body, slots))


def corner_fit_gauge(cfg: dict) -> trimesh.Trimesh:
    skin = cfg["skin"]
    return extrude_angle_strip(
        float(skin["corner_fit_gauge_arm_mm"]),
        float(skin["corner_fit_gauge_width_mm"]),
        float(skin["corner_fit_gauge_thickness_mm"]),
        corner_angle_deg(cfg),
    )


def fit_coupon(cfg: dict) -> trimesh.Trimesh:
    return fascia(cfg, width=35.0)


def validate_mesh(part: Part, cfg: dict) -> dict:
    mesh = part.mesh.copy()
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()
    bounds = np.asarray(mesh.bounds)
    size = bounds[1] - bounds[0]
    build = np.asarray(cfg["printer"]["minimum_model_build_envelope_mm"], dtype=float)
    density = float(cfg["skin"]["petg_density_g_cm3"])
    mass_g = mesh.volume / 1000.0 * density
    result = {
        "name": part.name,
        "run_id": part.run_id,
        "repeat_count": part.repeat_count,
        "purpose": part.purpose,
        "vertices": int(len(mesh.vertices)),
        "triangles": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "body_count": int(len(mesh.split(only_watertight=False))),
        "bounds_mm": np.round(bounds, 4).tolist(),
        "size_mm": np.round(size, 4).tolist(),
        "volume_mm3": round(float(mesh.volume), 2),
        "estimated_petg_g_each": round(float(mass_g), 1),
        "fits_minimum_180mm_envelope_in_saved_orientation": bool(np.all(size <= build + 1e-6)),
    }
    if not result["watertight"] or not result["winding_consistent"]:
        raise ValueError(f"{part.name} is not a closed, consistently wound mesh")
    if result["body_count"] != 1:
        raise ValueError(f"{part.name} unexpectedly has {result['body_count']} bodies")
    if not result["fits_minimum_180mm_envelope_in_saved_orientation"]:
        raise ValueError(f"{part.name} exceeds the 180 mm minimum model envelope: {size}")
    return result


def save_stl(part: Part) -> Path:
    path = OUT / f"{part.name}.stl"
    path.write_bytes(trimesh.exchange.stl.export_stl(part.mesh))
    return path


def indent_xml(element: ET.Element, level: int = 0) -> None:
    space = "\n" + level * "  "
    if len(element):
        if not element.text or not element.text.strip():
            element.text = space + "  "
        for child in element:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = space
    if level and (not element.tail or not element.tail.strip()):
        element.tail = space


def model_xml(title: str, description: str, objects: list[tuple[str, trimesh.Trimesh, tuple[float, float, float]]]) -> bytes:
    ET.register_namespace("", NS_3MF)
    model = ET.Element(f"{{{NS_3MF}}}model", {"unit": "millimeter", "{http://www.w3.org/XML/1998/namespace}lang": "en-US"})
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Title"}).text = title
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Description"}).text = description
    ET.SubElement(model, f"{{{NS_3MF}}}metadata", {"name": "Application"}).text = "PETG Closet Shelf parametric generator"
    resources = ET.SubElement(model, f"{{{NS_3MF}}}resources")
    materials = ET.SubElement(resources, f"{{{NS_3MF}}}basematerials", {"id": "1"})
    ET.SubElement(materials, f"{{{NS_3MF}}}base", {"name": "Black PETG (unconfirmed preset)", "displaycolor": "#111111FF"})
    build = ET.SubElement(model, f"{{{NS_3MF}}}build")

    for object_id, (name, source_mesh, translation) in enumerate(objects, start=2):
        mesh = source_mesh.copy()
        mesh.remove_unreferenced_vertices()
        mesh.fix_normals()
        obj = ET.SubElement(
            resources,
            f"{{{NS_3MF}}}object",
            {"id": str(object_id), "type": "model", "pid": "1", "pindex": "0", "name": name},
        )
        mesh_node = ET.SubElement(obj, f"{{{NS_3MF}}}mesh")
        vertices = ET.SubElement(mesh_node, f"{{{NS_3MF}}}vertices")
        for vertex in np.asarray(mesh.vertices):
            ET.SubElement(
                vertices,
                f"{{{NS_3MF}}}vertex",
                {"x": f"{vertex[0]:.6f}", "y": f"{vertex[1]:.6f}", "z": f"{vertex[2]:.6f}"},
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
    indent_xml(model)
    return ET.tostring(model, encoding="utf-8", xml_declaration=True)


def content_types_xml() -> bytes:
    ET.register_namespace("", NS_TYPES)
    root = ET.Element(f"{{{NS_TYPES}}}Types")
    ET.SubElement(root, f"{{{NS_TYPES}}}Default", {"Extension": "rels", "ContentType": "application/vnd.openxmlformats-package.relationships+xml"})
    ET.SubElement(root, f"{{{NS_TYPES}}}Default", {"Extension": "model", "ContentType": "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"})
    indent_xml(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def relationships_xml() -> bytes:
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
    indent_xml(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def write_model_3mf(path: Path, title: str, description: str, objects: list[tuple[str, trimesh.Trimesh, tuple[float, float, float]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def write_deterministic(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
        # A fixed timestamp and permission mode keep model-only packages byte-for-byte
        # reproducible across rebuilds and prevent noisy Git diffs.
        info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, payload)

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        write_deterministic(archive, "[Content_Types].xml", content_types_xml())
        write_deterministic(archive, "_rels/.rels", relationships_xml())
        write_deterministic(archive, "3D/3dmodel.model", model_xml(title, description, objects))


def write_part_3mfs(parts: list[Part], cfg: dict) -> None:
    project_name = cfg["project"]["name"]
    edition = cfg["project"]["edition"]
    revision = cfg["project"]["revision"]
    description = (
        f"{project_name} — {edition}; revision {revision}. MODEL ONLY - NO EMBEDDED G-CODE. "
        "Select the confirmed printer, nozzle, plate, and PETG preset before slicing."
    )
    for part in parts:
        write_model_3mf(
            MODEL_3MF / f"MODEL_ONLY_{part.name}.3mf",
            part.name,
            description,
            [(part.name, part.mesh, (0.0, 0.0, 0.0))],
        )

    # A representative catalog with one instance of every unique part.
    master_objects: list[tuple[str, trimesh.Trimesh, tuple[float, float, float]]] = []
    y_cursor = 0.0
    for part in parts:
        master_objects.append((part.name, part.mesh, (0.0, y_cursor, 0.0)))
        size = np.asarray(part.mesh.extents)
        y_cursor += float(size[1]) + 15.0
    write_model_3mf(
        MODEL_3MF / PARTS_CATALOG_3MF_NAME,
        f"{project_name} — {edition} PETG parts catalog",
        description + " This package is a representative parts catalog, not an arranged print plate; use the repeat counts in validation.json.",
        master_objects,
    )

    # Exact project quantities in one model-only package. The instances are
    # laid out on a virtual catalog canvas; the user must select the confirmed
    # printer and use Arrange to distribute them across real plates.
    full_objects: list[tuple[str, trimesh.Trimesh, tuple[float, float, float]]] = []
    x_cursor = 0.0
    y_cursor = 0.0
    row_height = 0.0
    catalog_width = 750.0
    for part in parts:
        size = np.asarray(part.mesh.extents)
        for index in range(part.repeat_count):
            if x_cursor and x_cursor + float(size[0]) > catalog_width:
                x_cursor = 0.0
                y_cursor += row_height + 15.0
                row_height = 0.0
            full_objects.append((f"{part.name}_{index + 1:02d}", part.mesh, (x_cursor, y_cursor, 0.0)))
            x_cursor += float(size[0]) + 15.0
            row_height = max(row_height, float(size[1]))
    write_model_3mf(
        MODEL_3MF / FULL_PRINT_SET_3MF_NAME,
        f"{project_name} — {edition} full PETG print set",
        description + " Contains exact repeat quantities on a virtual catalog canvas. Select the confirmed printer, then use Arrange to create real plates.",
        full_objects,
    )


def write_cut_plan(cfg: dict, dimensions: dict[str, dict]) -> None:
    structural = cfg["structural"]
    with (OUT / "cut_plan.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["part", "quantity", "finished size", "material / product basis", "notes"])
        for run in cfg["closet"]["runs"]:
            d = dimensions[run["id"]]
            writer.writerow([
                f"{run['label']} structural deck",
                run["quantity"],
                f"{d['deck_length_in']:.3f} x {cfg['closet']['shelf_depth_in']:.3f} in",
                structural["deck_material"],
                f"stations {d['deck_start_from_inside_corner_in']:.3f}-{d['deck_end_from_inside_corner_in']:.3f} in from inside-corner datum; FIELD VERIFY before cutting",
            ])
            writer.writerow([
                f"{run['label']} continuous front stiffener",
                run["quantity"],
                f"{d['deck_length_in']:.3f} in",
                structural["front_stiffener"],
                (
                    "continuous within this deck; through-run corner segment remains hidden behind the return, "
                    "and the return end is field-trimmed to clear the through angle; do not credit the corner contact as a splice"
                ),
            ])
            writer.writerow([
                f"{run['label']} wall standard",
                len(d["nominal_support_centers_in"]),
                f"{structural['standard_length_in']:.0f} in",
                structural["standard_basis"],
                "one standard per verified stud/blocking line; nominal drawing positions are not drill coordinates",
            ])
            writer.writerow([
                f"{run['label']} steel shelf bracket",
                len(d["nominal_support_centers_in"]),
                "7 in bracket for 8 in shelf",
                structural["bracket_basis"],
                "include bracket lock and manufacturer-prescribed shelf attachment",
            ])
            top = d["top_layout"]
            arcade = d["palatine_arcade_layout"]
            rear = d["rear_curb_layout"]
            rear_note = (
                f"straight long-wall curb begins at station {d['rear_curb_start_from_inside_corner_in']:.3f} in after the fitted corner replacement"
                if d["owns_corner_side_rear_curb"]
                else f"return curb begins on its own plywood at station {d['rear_curb_start_from_inside_corner_in']:.3f} in; no PETG curb crosses the wood joint"
            )
            writer.writerow([
                f"{run['label']} PETG top center module",
                top["center_columns"] * top["rows"] * run["quantity"],
                f"{top['center_module_width_mm']:.3f} x {top['module_depth_mm']:.3f} x {cfg['skin']['tile_thickness_mm']:.1f} mm",
                "black PETG",
                "reusable universal 6 in-pitch center; nonstructural finish",
            ])
            writer.writerow([
                f"{run['label']} PETG top parametric end module",
                top["end_columns"] * top["rows"] * run["quantity"],
                f"{top['parametric_end_module_width_mm']:.3f} x {top['module_depth_mm']:.3f} x {cfg['skin']['tile_thickness_mm']:.1f} mm",
                "black PETG",
                f"two ends per row; common corner seam is {d['corner_to_top_arm_finish_seam_mm']:.1f} mm; inner tile overhang into the wood gap is {d['top_inner_overhang_into_wood_joint_mm']:.1f} mm; regenerate after field changes",
            ])
            if d["owns_corner_top_zone"]:
                quadrant = (inches(cfg["closet"]["shelf_depth_in"]) - cfg["skin"]["tile_gap_mm"]) / 2.0
                writer.writerow([
                    "Through-owned PETG top corner quadrant",
                    4,
                    f"{quadrant:.3f} x {quadrant:.3f} x {cfg['skin']['tile_thickness_mm']:.1f} mm",
                    "black PETG",
                    "four identical pieces cover the 8 x 8 in through-deck corner square; near-square mating corners minimize the center seam opening",
                ])
            for handedness in ("left", "right"):
                writer.writerow([
                    f"{run['label']} Triadic Palatine arcade/fascia {handedness} half",
                    arcade[f"{handedness}_half_count"] * run["quantity"],
                    f"{arcade['half_arch_width_mm']:.3f} x {arcade['total_height_mm']:.3f} x {cfg['fascia']['channel_depth_mm']:.1f} mm",
                    "black PETG",
                    f"{arcade['bay_count']} complete bays on this arm; captured channel, 3:4:5 spandrel void, segmental archivolt, fluted pier with base/capital, and no steel-angle drilling; nonstructural",
                ])
            writer.writerow([
                f"{run['label']} removable Palatine entablature overlay",
                arcade["segment_count"] * run["quantity"],
                f"{arcade['half_arch_width_mm']:.3f} x {cfg['palatine']['entablature_overlay_height_mm']:.1f} mm",
                "black PETG",
                "one per half arch; nine dentils, three triglyph groups, three-order cornice, and central patera; qualify one removable silicone dot and retain to its own segment only",
            ])
            writer.writerow([
                f"{run['label']} PETG rear-curb center module",
                rear["center_columns"] * run["quantity"],
                f"{rear['center_module_width_mm']:.3f} mm module",
                "black PETG",
                f"reusable universal center; {rear_note}; nonstructural",
            ])
            writer.writerow([
                f"{run['label']} PETG rear-curb parametric end module",
                rear["end_columns"] * run["quantity"],
                f"{rear['parametric_end_module_width_mm']:.3f} mm module",
                "black PETG",
                "one generated clearance slot; field-drill the matching top tile only after layout, then use a short nonstructural screw with bottom clearance; regenerate when field width changes",
            ])
            if d["owns_corner_side_rear_curb"]:
                writer.writerow([
                    "Through-owned short-wall rear-curb corner-side piece",
                    1,
                    f"{d['corner_side_rear_curb_length_mm']:.3f} mm",
                    "black PETG",
                    "rests on the PETG tile/plywood stack over the through-deck corner square, stops before the plywood joint, and has one generated clearance slot; nonstructural",
                ])
        writer.writerow([
            "Optional inside-corner underside alignment kit",
            "1 if field fit requires",
            "field fitted after bracket dry-fit",
            "nonprinted slotted steel plates and mechanical fasteners",
            "alignment only; does not replace either run's independent brackets and is not a load-rating basis",
        ])
        writer.writerow(["Triadic Palatine keystone seam cover", cfg["palatine"]["total_arcade_bays"], f"{cfg['palatine']['keystone_width_mm']:.1f} x {cfg['palatine']['keystone_height_mm']:.1f} mm", "black PETG", "one per arch; retain to one half only so the opposite half can float across the 0.6 mm seam"])
        writer.writerow(["Palatine full-height fascia endcap", 2, f"{fascia_total_height(cfg) + cfg['palatine']['arch_drop_mm']:.3f} mm tall x {cfg['fascia']['endcap_thickness_mm']:.1f} mm", "black PETG", "one at each exposed outer end; straight fascia length already reserves its thickness"])
        writer.writerow(["Palatine re-entrant-corner pilaster slip cover", 1, f"18 mm legs x {fascia_total_height(cfg) + cfg['palatine']['arch_drop_mm']:.3f} mm tall", "black PETG", "fix one upper leg only and let the perpendicular leg float; no structural function"])
        writer.writerow(["Palatine groin-vault corner soffit", 1, f"{cfg['palatine']['groin_vault_size_mm']:.1f} mm square", "black PETG", "mount only beneath the through-owned corner square; keep the generated bracket clearance and never bridge the plywood joint"])
        writer.writerow(["PETG rear-curb inside-corner replacement", 1, "30 mm-leg fitted L curb with one clearance slot per arm", "black PETG", "sits on the top tile, replaces—not overlays—the first 30 mm of both straight curbs, and never crosses the plywood joint"])
        writer.writerow(["Corner fit gauge", 1, "60 mm-arm nominal L gauge", "black PETG", "print before corner production; confirm the real corner angle and regenerate if needed"])
        writer.writerow(["Fascia fit coupon", 1, "35 mm-wide test slice", "black PETG", "print and fit before any fascia production run"])
        writer.writerow(["Palatine detail coupon", 1, "75.9 x 98 mm true-scale detail montage", "black PETG", "approve the archivolt reveal, triangle, flutes, dentils, and finish before any ornate production run"])


def write_support_plan(cfg: dict, dimensions: dict[str, dict]) -> None:
    with (OUT / "support_plan.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["run", "geometry_source", "support_number", "center_from_inside_corner_wall_datum_in", "center_local_to_deck_start_in", "previous_spacing_in", "field_requirement"])
        for run in cfg["closet"]["runs"]:
            d = dimensions[run["id"]]
            previous = None
            for index, center in enumerate(d["nominal_support_centers_in"], start=1):
                spacing = "" if previous is None else f"{center - previous:.3f}"
                writer.writerow([
                    run["id"],
                    d["support_geometry_source"],
                    index,
                    f"{center:.3f}",
                    f"{center - d['deck_start_from_inside_corner_in']:.3f}",
                    spacing,
                    "verified wood stud or purpose-installed structural blocking; not hollow wall",
                ])
                previous = center


def write_structural_sanity_check(cfg: dict) -> None:
    """Write a deliberately limited plywood-span serviceability calculation.

    This is not a capacity analysis. It checks whether the short longitudinal
    plywood spans are plausibly stiff under the project's uniform line load;
    wall, fastener, standard, bracket, connection, point-load, and cumulative
    multi-shelf behavior are explicitly outside its scope.
    """
    structural = cfg["structural"]
    span = float(structural["maximum_support_spacing_in"])
    overhang = float(structural["maximum_end_overhang_in"])
    line_load = float(structural["serviceability_check_development_line_load_proxy_lb_per_ft"]) / 12.0
    modulus = float(structural["serviceability_check_plywood_modulus_psi"])
    width = float(cfg["closet"]["shelf_depth_in"])
    thickness = float(structural["deck_thickness_in"])
    inertia = width * thickness**3 / 12.0
    section_modulus = inertia / (thickness / 2.0)
    simple_moment = line_load * span**2 / 8.0
    simple_stress = simple_moment / section_modulus
    simple_deflection = 5.0 * line_load * span**4 / (384.0 * modulus * inertia)
    overhang_deflection = line_load * overhang**4 / (8.0 * modulus * inertia)
    report = {
        "warning": "Simplified serviceability sanity check only; not a load rating or complete structural analysis.",
        "scope": "Plywood deck acting alone as a longitudinal beam under an evenly distributed total development line-load proxy. The continuous steel angle is omitted, which is conservative for deck stiffness but does not validate its connections.",
        "load_scope_note": structural["serviceability_check_load_scope"],
        "excluded": [
            "wall and stud capacity",
            "standard, bracket, lock, and fastener capacity",
            "cumulative loading from multiple shelves",
            "point, impact, front-edge, seismic, and accidental loads",
            "plywood defects, moisture, orthotropic direction, holes, bearing, and connection slip",
            "the L-corner butt seam, corner alignment hardware, differential arm movement, and non-square wall geometry",
        ],
        "inputs": {
            "development_line_load_proxy_lb_per_ft": structural["serviceability_check_development_line_load_proxy_lb_per_ft"],
            "support_span_in": span,
            "maximum_end_overhang_in": overhang,
            "deck_depth_in": width,
            "deck_thickness_in": thickness,
            "assumed_plywood_modulus_psi": modulus,
        },
        "section": {
            "moment_of_inertia_in4": round(inertia, 6),
            "section_modulus_in3": round(section_modulus, 6),
        },
        "results": {
            "simple_span_max_moment_lb_in": round(simple_moment, 3),
            "simple_span_nominal_bending_stress_psi": round(simple_stress, 2),
            "simple_span_center_deflection_in": round(simple_deflection, 5),
            "uniform_load_end_overhang_tip_deflection_in": round(overhang_deflection, 5),
        },
        "interpretation": "Under these narrow assumptions, the 16 in plywood span is a serviceability rather than a governing concern; the wall attachment, complete steel support system, and field-fitted L junction remain the critical verification items.",
    }
    (OUT / "structural_sanity_check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def write_support_svg(cfg: dict, dimensions: dict[str, dict]) -> None:
    scale = 9.0
    rows: list[str] = []
    y = 155
    for run in cfg["closet"]["runs"]:
        d = dimensions[run["id"]]
        clear_width = float(d["clear_width_basis_in"]) * scale
        deck_x = 110 + float(d["deck_start_from_inside_corner_in"]) * scale
        deck_width = float(d["deck_length_in"]) * scale
        rows.append(f'<text x="110" y="{y - 60}" class="title">{run["label"]}: {d["deck_length_in"]:.3f} in deck, {d["corner_role"]} arm</text>')
        rows.append(f'<line x1="110" y1="{y - 20}" x2="{110 + clear_width:.1f}" y2="{y - 20}" class="wall"/>')
        rows.append(f'<circle cx="110" cy="{y - 20}" r="5" class="datum"/>')
        rows.append(f'<rect x="{deck_x:.1f}" y="{y}" width="{deck_width:.1f}" height="55" rx="6" class="shelf"/>')
        rows.append(f'<text x="110" y="{y + 152}" class="small">Deck stations: {d["deck_start_from_inside_corner_in"]:.3f}&quot; to {d["deck_end_from_inside_corner_in"]:.3f}&quot; from inside-corner datum</text>')
        for number, center in enumerate(d["nominal_support_centers_in"], start=1):
            x = 110 + float(center) * scale
            rows.append(f'<line x1="{x:.1f}" y1="{y - 35}" x2="{x:.1f}" y2="{y + 105}" class="standard"/>')
            rows.append(f'<path d="M {x:.1f} {y + 55} L {x:.1f} {y + 100} L {x + 52:.1f} {y + 55}" class="bracket"/>')
            rows.append(f'<text x="{x - 25:.1f}" y="{y + 128}" class="tiny">S{number} {center:.3f}&quot;</text>')
        y += 275
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="720" viewBox="0 0 900 720">
  <style>
    .heading{{font:700 26px Arial,sans-serif;fill:#16191c}} .title{{font:700 19px Arial,sans-serif;fill:#222}}
    .small{{font:14px Arial,sans-serif;fill:#343a40}} .tiny{{font:12px Arial,sans-serif;fill:#343a40}} .note{{font:16px Arial,sans-serif;fill:#7a3100}}
    .shelf{{fill:#161616;stroke:#000;stroke-width:2}} .standard{{stroke:#333;stroke-width:8}}
    .bracket{{fill:none;stroke:#111;stroke-width:9;stroke-linejoin:round}} .wall{{stroke:#8b9299;stroke-width:5}}
    .datum{{fill:#e55300;stroke:#8f2d00;stroke-width:2}}
  </style>
  <rect width="900" height="720" fill="#f7f8fa"/>
  <text x="55" y="45" class="heading">Nominal support stations from the inside-corner datum</text>
  {''.join(rows)}
  <rect x="55" y="625" width="790" height="65" rx="9" fill="#fff3cd" stroke="#b77900" stroke-width="2"/>
  <text x="75" y="652" class="note">These centers are desired geometry, not drilling coordinates.</text>
  <text x="75" y="677" class="note">Every standard must land on verified wood framing/blocking; dry-fit the perpendicular corner brackets.</text>
</svg>\n'''
    (OUT / "support_layout.svg").write_text(svg, encoding="utf-8")


def write_corner_svg(cfg: dict, dimensions: dict[str, dict], corner_data: dict) -> None:
    corner = cfg["closet"]["inside_corner"]
    through = dimensions[corner["through_run_id"]]
    return_run = dimensions[corner["return_run_id"]]
    scale = 8.0
    ox = 105.0
    oy = 105.0
    depth = float(cfg["closet"]["shelf_depth_in"])
    through_wall_back = float(through["installed_shelf_back_offset_in"])
    return_wall_back = float(return_run["installed_shelf_back_offset_in"])
    through_corner_end = float(through["corner_front_plane_from_inside_corner_in"])
    return_corner_end = float(return_run["corner_front_plane_from_inside_corner_in"])

    tx = ox + through["deck_start_from_inside_corner_in"] * scale
    ty = oy + through_wall_back * scale
    tw = through["deck_length_in"] * scale
    th = depth * scale
    rx = ox + return_wall_back * scale
    ry = oy + return_run["deck_start_from_inside_corner_in"] * scale
    rw = depth * scale
    rh = return_run["deck_length_in"] * scale
    corner_x = ox + return_wall_back * scale
    corner_y = oy + through_wall_back * scale
    corner_size = depth * scale
    seam = float(cfg["skin"]["tile_gap_mm"]) / 25.4 * scale
    quad = (corner_size - seam) / 2.0

    through_supports = "".join(
        f'<line x1="{ox + center * scale:.1f}" y1="{oy:.1f}" x2="{ox + center * scale:.1f}" y2="{oy + return_corner_end * scale:.1f}" class="support"/>'
        for center in through["nominal_support_centers_in"]
    )
    return_supports = "".join(
        f'<line x1="{ox:.1f}" y1="{oy + center * scale:.1f}" x2="{ox + through_corner_end * scale:.1f}" y2="{oy + center * scale:.1f}" class="support"/>'
        for center in return_run["nominal_support_centers_in"]
    )
    quadrants = "".join(
        f'<rect x="{corner_x + col * (quad + seam):.1f}" y="{corner_y + row * (quad + seam):.1f}" width="{quad:.1f}" height="{quad:.1f}" class="quad"/>'
        for row in range(2)
        for col in range(2)
    )
    joint_y = oy + return_corner_end * scale
    return_y = oy + return_run["deck_start_from_inside_corner_in"] * scale
    rear_leg_in = float(cfg["skin"]["rear_curb_inside_corner_leg_mm"]) / 25.4
    rear_replacement_end_x = return_wall_back + rear_leg_in
    rear_replacement_end_y = through_wall_back + rear_leg_in
    rear_through_start = through["rear_curb_start_from_inside_corner_in"]
    rear_corner_side_start = through["corner_side_rear_curb_start_from_inside_corner_in"]
    rear_corner_side_end = through["corner_side_rear_curb_end_from_inside_corner_in"]
    rear_return_start = return_run["rear_curb_start_from_inside_corner_in"]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="650" viewBox="0 0 900 650">
  <style>
    .heading{{font:700 26px Arial,sans-serif;fill:#16191c}} .title{{font:700 17px Arial,sans-serif;fill:#222}}
    .small{{font:14px Arial,sans-serif;fill:#343a40}} .note{{font:15px Arial,sans-serif;fill:#7a3100}}
    .wall{{stroke:#687078;stroke-width:7}} .deck{{fill:#222;stroke:#000;stroke-width:2}}
    .return{{fill:#303030;stroke:#000;stroke-width:2}} .quad{{fill:#111;stroke:#d6d9dc;stroke-width:1}}
    .support{{stroke:#4aa3df;stroke-width:3;stroke-dasharray:7 5}} .fascia{{stroke:#e55300;stroke-width:7;stroke-linecap:round}}
    .rear{{stroke:#2b8a3e;stroke-width:5;stroke-linecap:butt}} .curbseam{{stroke:#fff;stroke-width:3}}
    .topseam{{stroke:#f8f9fa;stroke-width:2;stroke-dasharray:3 2}}
    .joint{{fill:#ffd8a8;stroke:#e67700;stroke-width:1}} .dimension{{stroke:#555;stroke-width:1.5}}
  </style>
  <rect width="900" height="650" fill="#f7f8fa"/>
  <text x="45" y="42" class="heading">Fitted same-height L corner — plan view</text>
  <line x1="{ox}" y1="{oy}" x2="{ox + 64 * scale}" y2="{oy}" class="wall"/>
  <line x1="{ox}" y1="{oy}" x2="{ox}" y2="{oy + 40 * scale}" class="wall"/>
  <rect x="{tx:.1f}" y="{ty:.1f}" width="{tw:.1f}" height="{th:.1f}" class="deck"/>
  <rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" class="return"/>
  {quadrants}
  <rect x="{rx:.1f}" y="{joint_y:.1f}" width="{rw:.1f}" height="{max(1.5, return_y - joint_y):.1f}" class="joint"/>
  <line x1="{ox + through['top_arm_start_from_inside_corner_in'] * scale:.1f}" y1="{oy + through_wall_back * scale:.1f}" x2="{ox + through['top_arm_start_from_inside_corner_in'] * scale:.1f}" y2="{oy + return_corner_end * scale:.1f}" class="topseam"/>
  <line x1="{ox + return_wall_back * scale:.1f}" y1="{oy + return_run['top_arm_start_from_inside_corner_in'] * scale:.1f}" x2="{ox + through_corner_end * scale:.1f}" y2="{oy + return_run['top_arm_start_from_inside_corner_in'] * scale:.1f}" class="topseam"/>
  {through_supports}{return_supports}
  <line x1="{ox + through_corner_end * scale:.1f}" y1="{oy + return_corner_end * scale:.1f}" x2="{ox + through['deck_end_from_inside_corner_in'] * scale:.1f}" y2="{oy + return_corner_end * scale:.1f}" class="fascia"/>
  <line x1="{ox + through_corner_end * scale:.1f}" y1="{return_y:.1f}" x2="{ox + through_corner_end * scale:.1f}" y2="{oy + return_run['deck_end_from_inside_corner_in'] * scale:.1f}" class="fascia"/>
  <line x1="{ox + return_wall_back * scale:.1f}" y1="{oy + through_wall_back * scale:.1f}" x2="{ox + rear_replacement_end_x * scale:.1f}" y2="{oy + through_wall_back * scale:.1f}" class="rear"/>
  <line x1="{ox + return_wall_back * scale:.1f}" y1="{oy + through_wall_back * scale:.1f}" x2="{ox + return_wall_back * scale:.1f}" y2="{oy + rear_replacement_end_y * scale:.1f}" class="rear"/>
  <line x1="{ox + rear_through_start * scale:.1f}" y1="{oy + through_wall_back * scale:.1f}" x2="{ox + through['deck_end_from_inside_corner_in'] * scale:.1f}" y2="{oy + through_wall_back * scale:.1f}" class="rear"/>
  <line x1="{ox + return_wall_back * scale:.1f}" y1="{oy + rear_corner_side_start * scale:.1f}" x2="{ox + return_wall_back * scale:.1f}" y2="{oy + rear_corner_side_end * scale:.1f}" class="rear"/>
  <line x1="{ox + return_wall_back * scale:.1f}" y1="{oy + rear_return_start * scale:.1f}" x2="{ox + return_wall_back * scale:.1f}" y2="{oy + return_run['deck_end_from_inside_corner_in'] * scale:.1f}" class="rear"/>
  <line x1="{ox + rear_replacement_end_x * scale:.1f}" y1="{oy + through_wall_back * scale - 4:.1f}" x2="{ox + rear_replacement_end_x * scale:.1f}" y2="{oy + through_wall_back * scale + 4:.1f}" class="curbseam"/>
  <line x1="{ox + return_wall_back * scale - 4:.1f}" y1="{oy + rear_replacement_end_y * scale:.1f}" x2="{ox + return_wall_back * scale + 4:.1f}" y2="{oy + rear_replacement_end_y * scale:.1f}" class="curbseam"/>
  <line x1="{ox + return_wall_back * scale - 4:.1f}" y1="{oy + rear_corner_side_end * scale:.1f}" x2="{ox + return_wall_back * scale + 4:.1f}" y2="{oy + rear_corner_side_end * scale:.1f}" class="curbseam"/>
  <line x1="{ox + return_wall_back * scale - 4:.1f}" y1="{oy + rear_return_start * scale:.1f}" x2="{ox + return_wall_back * scale + 4:.1f}" y2="{oy + rear_return_start * scale:.1f}" class="curbseam"/>
  <circle cx="{ox}" cy="{oy}" r="6" fill="#e55300"/>
  <text x="{ox + 12}" y="{oy - 12}" class="small">inside finished-wall datum</text>
  <text x="{ox + 250}" y="{oy - 25}" class="title">5 ft through deck: {through['deck_length_in']:.3f} in</text>
  <text x="{ox + 82}" y="{oy + 245}" class="title">3 ft return: {return_run['deck_length_in']:.3f} in</text>
  <text x="{ox + 82}" y="{oy + 268}" class="small">starts at {return_run['deck_start_from_inside_corner_in']:.3f} in</text>
  <text x="{ox + 82}" y="{oy + 291}" class="small">wood fit gap: {corner_data['deck_joint_gap_mm']:.1f} mm</text>
  <text x="{ox + 82}" y="{oy + 314}" class="small">nominal bracket-envelope clearance: {corner_data['nominal_nearest_conservative_8in_shelf_envelope_clearance_in']:.3f} in</text>
  <text x="{ox + 82}" y="{oy + 342}" class="small">rear curb: 30 mm fitted corner replacement + 0.6 mm seams</text>
  <rect x="620" y="105" width="235" height="235" rx="9" fill="#fff" stroke="#b8bec4"/>
  <text x="640" y="133" class="title">Legend</text>
  <rect x="640" y="150" width="28" height="16" class="deck"/><text x="680" y="163" class="small">through-owned plywood</text>
  <rect x="640" y="178" width="28" height="16" class="return"/><text x="680" y="191" class="small">return plywood</text>
  <line x1="640" y1="214" x2="668" y2="214" class="support"/><text x="680" y="219" class="small">desired support line</text>
  <line x1="640" y1="242" x2="668" y2="242" class="fascia"/><text x="680" y="247" class="small">exposed fascia</text>
  <line x1="640" y1="274" x2="668" y2="274" class="rear"/><text x="680" y="279" class="small">rear curb on deck</text>
  <line x1="640" y1="306" x2="668" y2="306" class="topseam"/><text x="680" y="311" class="small">0.6 mm top seam</text>
  <rect x="45" y="555" width="810" height="65" rx="9" fill="#fff3cd" stroke="#b77900" stroke-width="2"/>
  <text x="65" y="582" class="note">The through deck supplies the entire 8 x 8 in corner surface; the return does not overlap it.</text>
  <text x="65" y="607" class="note">PETG corner pieces hide finish seams only. Field angle, wall bow, bracket bodies, and framing still govern.</text>
</svg>\n'''
    (OUT / "corner_layout.svg").write_text(svg, encoding="utf-8")


def write_palatine_elevation_svg(cfg: dict, dimensions: dict[str, dict]) -> None:
    """Write an exact-count/station schematic elevation of the PETG skin."""
    p = cfg["palatine"]
    scale = 0.56
    x0 = 210.0
    fascia_h = fascia_total_height(cfg) * scale
    drop = float(p["arch_drop_mm"]) * scale
    rise = float(p["arch_rise_mm"]) * scale
    pier = float(p["pier_width_mm"]) * scale
    base_projection = float(p["pier_base_projection_mm"]) * scale
    base_h = float(p["pier_base_height_mm"]) * scale
    capital_projection = float(p["pier_capital_projection_mm"]) * scale
    capital_h = float(p["pier_capital_height_mm"]) * scale

    def draw_run(run_id: str, y_top: float) -> str:
        run = next(item for item in cfg["closet"]["runs"] if item["id"] == run_id)
        layout = dimensions[run_id]["palatine_arcade_layout"]
        length = float(layout["length_mm"]) * scale
        bay_pitch = float(layout["bay_pitch_mm"]) * scale
        bays = int(layout["bay_count"])
        fascia_bottom = y_top + fascia_h
        spring_y = fascia_bottom + rise
        pier_bottom = fascia_bottom + drop
        elements = [
            f'<text x="55" y="{y_top + 26:.1f}" class="runlabel">{run["label"]}</text>',
            f'<text x="55" y="{y_top + 48:.1f}" class="small">{bays} bays · {layout["half_arch_width_mm"]:.3f} mm halves</text>',
            f'<rect x="{x0:.1f}" y="{y_top:.1f}" width="{length:.1f}" height="{fascia_h:.1f}" class="fascia"/>',
        ]
        # Three restrained horizontal orders and a dentil rhythm mark the
        # captured channel without implying any structural function.
        for fraction in (0.18, 0.48, 0.82):
            y_rule = y_top + fascia_h * fraction
            elements.append(
                f'<line x1="{x0:.1f}" y1="{y_rule:.1f}" x2="{x0 + length:.1f}" y2="{y_rule:.1f}" class="order"/>'
            )
        dentil_pitch = length / (bays * 18)
        for index in range(bays * 18):
            dx = x0 + (index + 0.22) * dentil_pitch
            elements.append(
                f'<rect x="{dx:.1f}" y="{y_top + fascia_h * 0.68:.1f}" width="{dentil_pitch * 0.55:.1f}" height="{max(2.0, fascia_h * 0.12):.1f}" class="detail"/>'
            )

        for bay in range(bays):
            left = x0 + bay * bay_pitch
            right = left + bay_pitch
            center = (left + right) / 2.0
            jamb_left = left + pier / 2.0
            jamb_right = right - pier / 2.0
            # The exact generated mesh uses a circular segment. The elevation
            # uses a quadratic display path while retaining exact bay stations.
            arch_path = (
                f'M {jamb_left:.1f} {spring_y:.1f} '
                f'Q {center:.1f} {fascia_bottom:.1f} {jamb_right:.1f} {spring_y:.1f}'
            )
            elements.append(f'<path d="{arch_path}" class="archouter"/>')
            elements.append(f'<path d="{arch_path}" class="archreveal"/>')
            triangle_y = fascia_bottom + 8.0
            tri_w = min(23.0, bay_pitch * 0.18)
            tri_h = tri_w * 0.75
            elements.append(
                f'<path d="M {jamb_left + 3:.1f} {triangle_y:.1f} h {tri_w:.1f} v {tri_h:.1f} z" class="triangle"/>'
            )
            elements.append(
                f'<path d="M {jamb_right - 3:.1f} {triangle_y:.1f} h {-tri_w:.1f} v {tri_h:.1f} z" class="triangle"/>'
            )
            key_w = float(p["keystone_width_mm"]) * scale
            key_h = float(p["keystone_height_mm"]) * scale
            elements.append(
                f'<path d="M {center - key_w * 0.32:.1f} {fascia_bottom - 1:.1f} '
                f'L {center + key_w * 0.32:.1f} {fascia_bottom - 1:.1f} '
                f'L {center + key_w / 2:.1f} {fascia_bottom + key_h:.1f} '
                f'L {center - key_w / 2:.1f} {fascia_bottom + key_h:.1f} Z" class="keystone"/>'
            )

        for boundary in range(bays + 1):
            cx = x0 + boundary * bay_pitch
            elements.append(
                f'<rect x="{cx - pier / 2:.1f}" y="{spring_y - 1:.1f}" width="{pier:.1f}" height="{pier_bottom - spring_y + 1:.1f}" class="pier"/>'
            )
            elements.append(
                f'<rect x="{cx - pier / 2 - capital_projection:.1f}" y="{spring_y - capital_h:.1f}" width="{pier + 2 * capital_projection:.1f}" height="{capital_h:.1f}" class="detail"/>'
            )
            elements.append(
                f'<rect x="{cx - pier / 2 - base_projection:.1f}" y="{pier_bottom - base_h:.1f}" width="{pier + 2 * base_projection:.1f}" height="{base_h:.1f}" class="detail"/>'
            )
            for flute in (-0.27, 0.0, 0.27):
                fx = cx + flute * pier
                elements.append(
                    f'<line x1="{fx:.1f}" y1="{spring_y + 7:.1f}" x2="{fx:.1f}" y2="{pier_bottom - base_h - 3:.1f}" class="flute"/>'
                )
        elements.extend(
            [
                f'<line x1="{x0:.1f}" y1="{pier_bottom + 18:.1f}" x2="{x0 + length:.1f}" y2="{pier_bottom + 18:.1f}" class="dim"/>',
                f'<text x="{x0 + length / 2:.1f}" y="{pier_bottom + 35:.1f}" text-anchor="middle" class="small">{layout["length_mm"]:.3f} mm facade train · {layout["segment_count"]} printed halves</text>',
            ]
        )
        return "".join(elements)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="650" viewBox="0 0 1100 650">
  <style>
    .heading{{font:700 27px Georgia,serif;fill:#171717}} .sub{{font:15px Arial,sans-serif;fill:#4b4f53}}
    .runlabel{{font:700 18px Georgia,serif;fill:#202020}} .small{{font:13px Arial,sans-serif;fill:#4b4f53}}
    .fascia,.pier{{fill:#171717;stroke:#030303;stroke-width:1}} .detail,.keystone{{fill:#292929;stroke:#050505;stroke-width:1}}
    .order{{stroke:#62676b;stroke-width:1.4}} .archouter{{fill:none;stroke:#171717;stroke-width:11;stroke-linecap:round}}
    .archreveal{{fill:none;stroke:#8b9195;stroke-width:2.2;stroke-linecap:round}} .triangle{{fill:none;stroke:#62676b;stroke-width:2}}
    .flute{{stroke:#8b9195;stroke-width:1}} .dim{{stroke:#676c70;stroke-width:1;stroke-dasharray:5 4}}
  </style>
  <rect width="1100" height="650" fill="#f6f3ec"/>
  <text x="55" y="48" class="heading">Story Corner — Triadic Palatine Order</text>
  <text x="55" y="74" class="sub">Exact unfolded PETG facade rhythm: 3 short-wall bays + 6 long-wall bays = 9. Hidden plywood-and-steel chassis not shown.</text>
  {draw_run("short_wall_3ft", 105.0)}
  {draw_run("long_wall_5ft", 355.0)}
  <rect x="820" y="90" width="225" height="105" rx="10" fill="#fff" stroke="#a8adb1"/>
  <text x="842" y="122" class="runlabel">3 · 6 · 9 grammar</text>
  <text x="842" y="148" class="small">3 bays / 6 bays / 9 keystones</text>
  <text x="842" y="171" class="small">3:4:5 spandrels · 6 flutes · 9-petal vault</text>
  <text x="55" y="628" class="sub">Ornament is removable PETG finish only. It receives no shelf-load, bracket, wall-anchor, or cargo-restraint credit.</text>
</svg>\n'''
    (OUT / "palatine_elevation.svg").write_text(svg, encoding="utf-8")


def write_artifact_manifest(cfg: dict) -> None:
    artifact_paths = sorted(
        [*OUT.glob("*.stl"), *MODEL_3MF.glob("*.3mf")],
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    artifacts = []
    for path in artifact_paths:
        payload = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    report = {
        "project_name": cfg["project"]["name"],
        "design_edition": cfg["project"]["edition"],
        "repository_slug": cfg["project"]["repository_slug"],
        "repository_url": cfg["project"]["repository_url"],
        "revision": cfg["project"]["revision"],
        "scope": "Printable STL and model-only 3MF artifacts generated from config.json",
        "embedded_gcode_allowed": cfg["project"]["embedded_gcode_allowed"],
        "artifacts": artifacts,
    }
    (OUT / "artifact_manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def clear_generator_owned_printables() -> None:
    """Remove only derived mesh/packages so renamed parts cannot leave stale files."""
    for path in sorted(OUT.glob("*.stl")):
        path.unlink()
    for path in sorted(MODEL_3MF.glob("*.3mf")):
        path.unlink()


def append_end_group_parts(
    parts: list[Part],
    cfg: dict,
    runs: list[dict],
    dimensions: dict[str, dict],
    *,
    layout_key: str,
    name_base: str,
    mesh_factory,
    purpose: str,
) -> None:
    groups: list[dict] = []
    for run in runs:
        layout = dimensions[run["id"]][layout_key]
        width = float(layout["parametric_end_module_width_mm"])
        matching = next((group for group in groups if abs(group["width"] - width) < 0.001), None)
        if matching is None:
            matching = {"width": width, "runs": []}
            groups.append(matching)
        matching["runs"].append(run)

    for group in groups:
        group_runs = group["runs"]
        if len(groups) == 1:
            suffix = ""
            run_id = "shared_modular"
        else:
            identifiers = "_and_".join(run["id"] for run in group_runs)
            suffix = "_" + re.sub(r"[^A-Za-z0-9_]+", "_", identifiers).strip("_")
            run_id = identifiers
        repeat_count = sum(
            dimensions[run["id"]][layout_key]["end_columns"]
            * dimensions[run["id"]][layout_key]["rows"]
            * int(run["quantity"])
            for run in group_runs
        )
        parts.append(
            Part(
                f"{name_base}{suffix}",
                mesh_factory(float(group["width"])),
                run_id,
                repeat_count,
                purpose,
            )
        )


def main() -> None:
    cfg = load_config()
    OUT.mkdir(parents=True, exist_ok=True)
    MODEL_3MF.mkdir(parents=True, exist_ok=True)
    clear_generator_owned_printables()

    dimensions = {run["id"]: run_dimensions(cfg, run) for run in cfg["closet"]["runs"]}
    corner_data = corner_geometry(cfg, dimensions)
    runs = cfg["closet"]["runs"]
    run_values = [dimensions[run["id"]] for run in runs]
    top_radius = float(cfg["skin"]["top_tile_plan_radius_mm"])
    corner_radius = float(cfg["skin"]["corner_mating_radius_mm"])
    tile_gap = float(cfg["skin"]["tile_gap_mm"])
    if top_radius > tile_gap / 2.0 + 1e-9:
        raise ValueError("Top-tile plan radius must not exceed half the finish seam")
    if abs(top_radius - corner_radius) > 1e-9:
        raise ValueError("Ordinary top tiles and corner quadrants must share the same near-square mating radius")
    center_width = run_values[0]["top_layout"]["center_module_width_mm"]
    module_depth = run_values[0]["top_layout"]["module_depth_mm"]
    all_layouts = [
        d[key]
        for d in run_values
        for key in ("top_layout", "rear_curb_layout")
    ]
    if not all(abs(layout["center_module_width_mm"] - center_width) < 0.001 for layout in all_layouts):
        raise ValueError("All component runs must use the same universal center-module width")
    if not all(abs(d["top_layout"]["module_depth_mm"] - module_depth) < 0.001 for d in run_values):
        raise ValueError("All runs must use the same universal top-module depth")

    top_center_count = sum(
        d["top_layout"]["center_columns"] * d["top_layout"]["rows"] * int(run["quantity"])
        for run, d in zip(runs, run_values)
    )
    rear_center_count = sum(
        d["rear_curb_layout"]["center_columns"] * int(run["quantity"])
        for run, d in zip(runs, run_values)
    )

    parts: list[Part] = [
        Part(
            "PETG_TopTile_Center_6inPitch",
            top_tile(cfg, center_width, module_depth),
            "shared_modular",
            top_center_count,
            "universal reusable nonstructural top-finish center module",
        ),
        Part(
            "PETG_RearCurb_Center_6inPitch",
            rear_curb(cfg, center_width),
            "shared_modular",
            rear_center_count,
            "universal reusable nonstructural rear item-retention center module that remains entirely on top of the plywood",
        ),
        Part(
            "PETG_TopTile_CornerQuadrant_SquareMating",
            corner_top_quadrant(cfg),
            cfg["closet"]["inside_corner"]["through_run_id"],
            4,
            "four-piece nonstructural finish for the through-owned 8 x 8 in corner square",
        ),
        Part(
            "PETG_RearCurb_CornerSide_ThroughZone",
            rear_curb(
                cfg,
                dimensions[cfg["closet"]["inside_corner"]["through_run_id"]]["corner_side_rear_curb_length_mm"],
            ),
            cfg["closet"]["inside_corner"]["through_run_id"],
            1,
            "nonstructural short-wall curb segment resting only on the through-owned corner square; stops before the plywood joint",
        ),
    ]

    append_end_group_parts(
        parts,
        cfg,
        runs,
        dimensions,
        layout_key="top_layout",
        name_base="PETG_TopTile_ParametricEnd",
        mesh_factory=lambda width: top_tile(cfg, width, module_depth),
        purpose="symmetric nonstructural top-arm end-fit module; regenerate after field-width changes",
    )
    for run in runs:
        run_id = run["id"]
        arcade = dimensions[run_id]["palatine_arcade_layout"]
        width = float(arcade["half_arch_width_mm"])
        for handedness in ("left", "right"):
            parts.append(
                Part(
                    f"PETG_Palatine_ArcadeFascia_Half_{handedness}_{run_id}",
                    palatine_arcade_fascia_half(cfg, width, handedness),
                    run_id,
                    int(arcade[f"{handedness}_half_count"]) * int(run["quantity"]),
                    "integrated captured fascia channel and Triadic Palatine segmental-arch half with base/capital; no hole is added to the continuous steel angle",
                )
            )
        parts.append(
            Part(
                f"PETG_Palatine_EntablatureOverlay_{run_id}",
                palatine_entablature_overlay(cfg, width),
                run_id,
                int(arcade["segment_count"]) * int(run["quantity"]),
                "removable face-up three-order entablature detail with nine dentils, three triglyph groups, and central patera; retain to its own fascia segment only",
            )
        )
    append_end_group_parts(
        parts,
        cfg,
        runs,
        dimensions,
        layout_key="rear_curb_layout",
        name_base="PETG_RearCurb_ParametricEnd",
        mesh_factory=lambda width: rear_curb(cfg, width),
        purpose="symmetric nonstructural rear item-retention end module; remains entirely on top of plywood and regenerates after field-width changes",
    )
    parts.extend(
        [
            Part(
                "PETG_Palatine_Keystone_SeamCover",
                palatine_keystone(cfg),
                "shared_modular",
                int(cfg["palatine"]["total_arcade_bays"]),
                "nonstructural center-seam cover; retain on one arch half and let the other side float",
            ),
            Part(
                "PETG_Palatine_Fascia_EndCap",
                palatine_fascia_endcap(cfg),
                None,
                2,
                "full-height nonstructural finish for the two exposed outer arcade/fascia ends",
            ),
            Part(
                "PETG_Palatine_ReentrantCorner_Pilaster_SlipCover",
                fascia_outside_corner_cover(cfg),
                "inside_corner_L",
                1,
                "full-height thin nonstructural pilaster overlay; fasten one upper leg and let the perpendicular leg float",
            ),
            Part(
                "PETG_Palatine_GroinVault_CornerSoffit",
                palatine_groin_vault_corner_soffit(cfg),
                cfg["closet"]["inside_corner"]["through_run_id"],
                1,
                "nonstructural 42 mm fitted corner soffit with diagonal ribs and nine-petal boss; stays entirely on the through-owned corner square",
            ),
            Part(
                "PETG_RearCurb_InsideCorner_Replacement",
                rear_curb_inside_corner_connector(cfg),
                "inside_corner_L",
                1,
                "nonstructural fitted replacement for the first 30 mm of both straight rear-curb arms; install before the straight pieces and do not overlay them",
            ),
            Part("PRINT_FIRST_FasciaFitCoupon", fit_coupon(cfg), None, 1, "fit test for the real plywood and steel stack"),
            Part(
                "PRINT_FIRST_PalatineDetailCoupon",
                palatine_detail_coupon(cfg),
                None,
                1,
                "true-scale printability and finish test for shadow reveal, triangle, flutes, dentils, and three-order entablature",
            ),
            Part(
                "PRINT_FIRST_CornerFitGauge",
                corner_fit_gauge(cfg),
                "inside_corner_L",
                1,
                "nominal-angle gauge; compare with the wall and a full-size corner template before cutting",
            ),
        ]
    )

    validation = []
    for part in parts:
        validation.append(validate_mesh(part, cfg))
        save_stl(part)
    write_part_3mfs(parts, cfg)
    write_cut_plan(cfg, dimensions)
    write_support_plan(cfg, dimensions)
    write_structural_sanity_check(cfg)
    write_support_svg(cfg, dimensions)
    write_corner_svg(cfg, dimensions, corner_data)
    write_palatine_elevation_svg(cfg, dimensions)
    write_artifact_manifest(cfg)

    by_name = {entry["name"]: entry for entry in validation}
    packaged_mass_g = sum(entry["estimated_petg_g_each"] * entry["repeat_count"] for entry in validation)
    installed_mass_g = sum(
        entry["estimated_petg_g_each"] * entry["repeat_count"]
        for entry in validation
        if not entry["name"].startswith("PRINT_FIRST_")
    )
    report = {
        "project_name": cfg["project"]["name"],
        "design_edition": cfg["project"]["edition"],
        "repository_slug": cfg["project"]["repository_slug"],
        "repository_url": cfg["project"]["repository_url"],
        "revision": cfg["project"]["revision"],
        "warning": cfg["project"]["warning"],
        "measurement_status": cfg["project"]["measurement_status"],
        "embedded_gcode_allowed": cfg["project"]["embedded_gcode_allowed"],
        "printer_assumption": cfg["printer"],
        "closet_basis": {
            "shelf_depth_in": cfg["closet"]["shelf_depth_in"],
            "shelf_depth_status": cfg["closet"]["shelf_depth_status"],
            "arrangement": cfg["closet"]["arrangement"],
            "common_shelf_top_elevation_from_finished_floor_in": cfg["closet"]["common_shelf_top_elevation_from_finished_floor_in"],
            "common_shelf_top_elevation_status": cfg["closet"]["common_shelf_top_elevation_status"],
            "measured_vertical_zone_from_outlet_top_to_ceiling_in": cfg["closet"]["measured_vertical_zone_from_outlet_top_to_ceiling_in"],
            "vertical_zone_measurement_status": cfg["closet"]["vertical_zone_measurement_status"],
        },
        "printable_material_scope": "Every generated printable component is PETG-only and nonstructural.",
        "structural_load_path": "contents -> each run's continuous plywood deck / continuous steel front angle -> its independent steel brackets -> steel standards -> verified wood studs or purpose-installed blocking",
        "support_rule": cfg["closet"]["support_rule"],
        "inside_corner": corner_data,
        "palatine_design": cfg["palatine"],
        "finish_attachment": cfg["finish_attachment"],
        "modularity": {
            "safe_reconfiguration_boundary": "Steel standards provide vertical movement; the two arms of an assembled L level are unloaded and moved together. Universal PETG centers move between runs; measured ends and corner pieces are regenerated as needed. Each plywood deck and steel front angle remains continuous within its own run.",
            "module_pitch_mm": cfg["skin"]["module_pitch_mm"],
            "shared_center_module_width_mm": round(center_width, 4),
            "corner_quadrant_size_mm": round((inches(cfg["closet"]["shelf_depth_in"]) - cfg["skin"]["tile_gap_mm"]) / 2.0, 4),
            "component_parametric_end_widths_mm": {
                key: sorted({round(float(d[key]["parametric_end_module_width_mm"]), 4) for d in run_values})
                for key in ("top_layout", "rear_curb_layout")
            },
            "palatine_arcade_half_widths_mm": {
                run["id"]: round(
                    float(dimensions[run["id"]]["palatine_arcade_layout"]["half_arch_width_mm"]),
                    4,
                )
                for run in runs
            },
            "full_set_object_count": sum(part.repeat_count for part in parts),
            "arcade_bay_counts": {
                run["id"]: dimensions[run["id"]]["palatine_arcade_layout"]["bay_count"]
                for run in runs
            },
        },
        "runs": [
            {
                **run,
                "computed": {
                    key: round(value, 4) if isinstance(value, float) else value
                    for key, value in dimensions[run["id"]].items()
                },
            }
            for run in cfg["closet"]["runs"]
        ],
        "meshes": validation,
        "estimated_packaged_petg_mass_kg": round(packaged_mass_g / 1000.0, 2),
        "estimated_installed_petg_mass_kg": round(installed_mass_g / 1000.0, 2),
        "mass_estimate_note": "Geometry volume times nominal PETG density; excludes purge, supports, failures, spares, fasteners, plywood, and steel.",
        "model_3mf_packages": {
            "parts_catalog": PARTS_CATALOG_3MF_NAME,
            "full_print_set": FULL_PRINT_SET_3MF_NAME,
        },
        "model_3mf_files": sorted(path.name for path in MODEL_3MF.glob("*.3mf")),
        "model_3mf_note": "Model-only 3MFs contain no embedded G-code. Confirm printer, nozzle, plate, and PETG before slicing.",
    }
    (OUT / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "revision": report["revision"],
                "mesh_count": len(by_name),
                "full_set_object_count": report["modularity"]["full_set_object_count"],
                "estimated_packaged_petg_mass_kg": report["estimated_packaged_petg_mass_kg"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
