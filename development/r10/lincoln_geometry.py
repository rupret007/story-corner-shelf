#!/usr/bin/env python3
"""R10 qualification geometry for one printed Lincoln-log shelf bay.

This module authors a deliberately fail-closed, mostly-PETG architecture.  It
does not create a load rating or authorize a wall installation.  The geometry
models one 254 mm planning bay, while retaining the exact field topology of
seven supports on 254 mm (10 inch) centers.

Installed axes are X along the wall run, Y from wall to shelf front, and Z
upward.  A support is authored in ``q/e/run`` axes (wall projection, elevation,
wall run) and mapped to installed XYZ only for assembly evidence.  Cassette
halves, splice logs, and removable retainers are authored directly in installed
axes.  Every saved orientation is chosen for the Bambu Lab A1 mini and keeps
Support disabled as the design intent; slicer Preview and first-article prints
remain mandatory physical gates.

The structural idea is intentionally simple:

* cassette ends bear directly on printed support capitals;
* three independent dovetailed PETG logs bridge each cassette midpoint;
* one removable retainer captures each log independently;
* one bay-local removable retainer captures each cassette/support contact; and
* neither retainer type receives gravity, bending, or load-capacity credit.

Nominal planning lengths remain useful layout datums, but printable parts carry
real 0.35 mm gaps at midpoint seams, support lines, and wall endpoints.  Thus a
regular half is 126.65 mm, a terminal half is 142.35 mm, and the log is 159.10
mm so its physical engagement remains 79.375 mm in both halves.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence
import warnings

import numpy as np
from shapely.geometry import Polygon
import trimesh


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PHYSICAL_QUALIFICATION_COMPLETE = False
WALL_INSTALLATION_AUTHORIZED = False
PRINTED_MATERIAL = "SUNLU standard black PETG, ASIN B0D1KC72YP"
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0

A1_MINI_BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
BRIM_MM = 5.0
BRIM_OBJECT_GAP_MM = 0.1
RESERVE_PER_BED_EDGE_MM = 2.0
GEOMETRY_EPSILON = 1.0e-7

FIELD_SUPPORT_COUNT = 7
FIELD_BAY_COUNT = 6
SUPPORT_PITCH_MM = 254.0
ONE_BAY_SUPPORT_CENTERS_MM = (0.0, SUPPORT_PITCH_MM)
ONE_BAY_MIDPOINT_MM = SUPPORT_PITCH_MM / 2.0

SHELF_DEPTH_MM = 152.4
SHELF_TOTAL_HEIGHT_MM = 32.0
SUPPORT_RUN_WIDTH_MM = 31.75
SUPPORT_HALF_LAND_NOMINAL_MM = SUPPORT_RUN_WIDTH_MM / 2.0
SUPPORT_WALL_CHORD_MM = 19.05
SUPPORT_TOTAL_DROP_MM = 158.75
SUPPORT_TOP_CHORD_MM = 19.05
SUPPORT_COMPRESSION_WEB_MM = 19.05
SUPPORT_FRONT_NOSE_MM = 31.75
COMPACT_VISIBLE_DROP_MM = 76.2

WALL_BORE_COUNT = 3
WALL_BORE_DIAMETER_MM = 7.0
WALL_BORE_DROPS_BELOW_UNDERSIDE_MM = (19.05, 79.375, 139.7)
WASHER_BEARING_LAND_OUTER_DIAMETER_MM = 27.025
WASHER_LAND_EVIDENCE_THICKNESS_MM = 1.0

PLANNING_REGULAR_HALF_LENGTH_MM = 127.0
PLANNING_TERMINAL_HALF_LENGTH_MM = 142.875
MIDPOINT_SEAM_CLEARANCE_MM = 0.35
SUPPORT_LINE_CLEARANCE_MM = 0.35
WALL_ENDPOINT_CLEARANCE_MM = 0.35
PRINTED_REGULAR_HALF_LENGTH_MM = 126.65
PRINTED_TERMINAL_HALF_LENGTH_MM = 142.35
PHYSICAL_BEARING_CONTACT_PER_HALF_MM = 15.70

TOP_SKIN_MM = 4.0
BOTTOM_SKIN_MM = 3.2
LOAD_WEB_MM = 4.0

LOG_COUNT_PER_BAY = 3
LOG_LENGTH_MM = 159.10
LOG_WIDTH_MM = 20.0
LOG_TOP_WIDTH_MM = 18.0
LOG_HEIGHT_MM = 24.0
LOG_ENGAGEMENT_PER_HALF_MM = 79.375
LOG_REDUCED_NOSE_LENGTH_MM = 0.4
LOG_NOSE_AXIAL_CLEARANCE_MM = 0.4
JOINERY_CLEARANCE_PER_FACE_MM = 0.4
CHANNEL_CLEAR_HEIGHT_MM = LOG_HEIGHT_MM + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM
CHANNEL_MAX_WIDTH_MM = LOG_WIDTH_MM + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM
CHANNEL_TOP_WIDTH_MM = LOG_TOP_WIDTH_MM + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM
CHANNEL_STATIONS_Y_MM = (16.0, 76.2, 136.4)
CHANNEL_OUTER_WIDTH_MM = CHANNEL_MAX_WIDTH_MM + 2.0 * LOAD_WEB_MM

LOG_RETAINER_RUN_MM = 12.0
LOG_RETAINER_STATION_MM = 28.0
LOG_RETAINER_HEIGHT_MM = 6.0
LOG_RETAINER_COUNT_PER_BAY = 3
LOG_KEY_TOP_ACCESS_POCKETS_PER_BAY = 3
FIELD_LOG_KEY_TOP_ACCESS_POCKET_COUNT = 18
LOG_RETAINER_CAP_RUN_MM = 6.0
LOG_RETAINER_CAP_HEIGHT_MM = 4.8
LOG_RETAINER_CAP_X_START_MM = -0.4

SUPPORT_RETAINER_RUN_MM = 8.0
SUPPORT_RETAINER_DEPTH_MM = 136.0
SUPPORT_RETAINER_HEIGHT_MM = 6.0
SUPPORT_RETAINERS_PER_BAY = 2
FULL_RUN_SUPPORT_RETAINER_COUNT = 12
SUPPORT_RETAINER_SHAFT_RUN_MM = 3.8
SUPPORT_RETAINER_REAR_DOG_DEPTH_MM = 8.0
SUPPORT_RETAINER_FRONT_HANDLE_DEPTH_MM = 12.0
SUPPORT_RETAINER_BAYONET_SHIFT_MM = 2.4
SUPPORT_RETAINER_HAND_GRIP_PROTRUSION_MM = 4.0

# Each half-land owns its own small, no-credit capture lug.  The two lugs in a
# support are separate, so removing one bay's retainer cannot release its
# neighbor.  The lug/pocket is a locator and anti-lift candidate only.
# A 12 mm lug leaves a real side shoulder around the 8.8 mm service lane.
# The prior 4 mm lug was narrower than its own slot and therefore could not
# create a positive bayonet stop even when its end pocket was shifted.
CAPTURE_LUG_RUN_MM = 12.0
CAPTURE_LUG_HEIGHT_MM = 12.0
CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM = 8.025
CAPTURE_LUG_CENTERS_SOURCE_RUN_MM = (
    SUPPORT_RUN_WIDTH_MM / 2.0 - CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM,
    SUPPORT_RUN_WIDTH_MM / 2.0 + CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM,
)
CAPTURE_LUG_CENTER_IN_REGULAR_HALF_MM = (
    CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM - SUPPORT_LINE_CLEARANCE_MM / 2.0
)
CAPTURE_KEY_BASE_ABOVE_SHELF_UNDERSIDE_MM = 4.0

LOG_KEY_SLOT_BASE_MM = (
    LOG_HEIGHT_MM
    - LOG_RETAINER_HEIGHT_MM
    - 2.0 * JOINERY_CLEARANCE_PER_FACE_MM
)
MIDPOINT_KEY_BASE_IN_CASSETTE_MM = (
    BOTTOM_SKIN_MM
    + JOINERY_CLEARANCE_PER_FACE_MM
    + LOG_KEY_SLOT_BASE_MM
    + JOINERY_CLEARANCE_PER_FACE_MM
)

AESTHETIC_CONTRACT_ID = "r10_palatine_lincoln_arcade_v1"


@dataclass(frozen=True)
class PrintEnvelope:
    """A saved part's exact axis-aligned A1 mini envelope."""

    raw_part_mm: tuple[float, float, float]
    required_build_volume_mm: tuple[float, float, float]
    available_build_volume_mm: tuple[float, float, float]
    brim_mm: float
    brim_object_gap_mm: float
    reserve_per_bed_edge_mm: float
    fits: bool


@dataclass(frozen=True)
class JoineryClearanceEvidence:
    """Analytic dimensions; physical fit still requires printed coupons."""

    midpoint_seam_mm: float
    support_line_seam_mm: float
    wall_endpoint_mm: float
    channel_clearance_per_face_mm: float
    channel_clear_height_mm: float
    cassette_internal_height_mm: float
    log_engagement_per_half_mm: float
    physical_bearing_contact_per_half_mm: float
    independent_log_retainers_per_bay: int
    bay_local_support_retainers_per_bay: int


@dataclass(frozen=True)
class LogSectionEvidence:
    """Pure cross-section geometry; never a material or load capacity."""

    gross_area_mm2: float
    gross_centroid_z_mm: float
    gross_second_moment_about_y_mm4: float
    gross_governing_section_modulus_mm3: float
    net_area_mm2: float
    net_centroid_z_mm: float
    net_second_moment_about_y_mm4: float
    net_governing_section_modulus_mm3: float
    net_to_gross_area_ratio: float
    net_to_gross_second_moment_ratio: float
    net_to_gross_section_modulus_ratio: float
    material_capacity_claimed: bool


@dataclass(frozen=True)
class WasherLandEvidence:
    """Surface-annulus coverage in the final support mesh; no screw credit."""

    bore_drop_below_shelf_underside_mm: float
    bore_diameter_mm: float
    outer_diameter_mm: float
    radial_land_mm: float
    surface_thickness_checked_mm: float
    minimum_run_edge_margin_mm: float
    minimum_vertical_edge_margin_mm: float
    annulus_probe_volume_mm3: float
    annulus_solid_volume_mm3: float
    solid_volume_ratio: float
    continuous_single_body: bool
    full_solid: bool


@dataclass(frozen=True)
class OneBayPart:
    name: str
    installed_mesh: trimesh.Trimesh
    saved_print_mesh: trimesh.Trimesh
    saved_orientation: str
    support_required: bool
    capacity_credit: bool


@dataclass(frozen=True)
class OneBayEvidence:
    parts: tuple[OneBayPart, ...]
    support_centers_mm: tuple[float, float]
    planning_bay_pitch_mm: float
    printed_regular_half_length_mm: float
    printed_terminal_half_length_mm: float
    printed_log_length_mm: float
    joinery: JoineryClearanceEvidence
    one_bay_part_count: int
    field_support_count: int
    field_bay_count: int
    aesthetic_contract_id: str
    positive_log_body_shoulders_authored: bool
    log_retainer_preassembly_path_authored: bool
    log_key_top_access_pockets_per_bay: int
    flush_log_key_access_closures_authored: bool
    target_pose_maximum_intersection_mm3: float
    target_pose_collision_free: bool
    right_half_capture_path_maximum_intersection_mm3: float
    right_half_capture_path_collision_free: bool
    support_retainer_positive_capture_authored: bool
    support_retainer_service_path_maximum_intersection_mm3: float
    support_retainer_service_path_collision_free: bool
    support_retainer_walkout_stop_intersection_mm3: float
    support_retainer_hand_grip_protrusion_mm: float
    log_section: LogSectionEvidence
    washer_lands: tuple[WasherLandEvidence, ...]
    midpoint_net_section_geometry_authored: bool
    midpoint_notched_log_section_qualified: bool
    release_blockers: tuple[str, ...]
    tabletop_assembly_order: tuple[str, ...]
    no_load_boundary: str


def _positive(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return result


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("R10 geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("R10 geometry contains non-finite coordinates")
    return mesh


def _copy(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty Trimesh is required")
    return _clean(mesh.copy())


def _box(
    extents: tuple[float, float, float],
    origin: tuple[float, float, float],
) -> trimesh.Trimesh:
    size = np.asarray([_positive(item, "box dimension") for item in extents])
    start = np.asarray(origin, dtype=float)
    if start.shape != (3,) or not np.isfinite(start).all():
        raise ValueError("Box origin must contain three finite coordinates")
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(start + size / 2.0)
    return _clean(mesh)


def _union(meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("At least one mesh is required for union")
    result = trimesh.boolean.union(
        [_copy(mesh) for mesh in meshes], engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _difference(
    body: trimesh.Trimesh, cutters: Sequence[trimesh.Trimesh]
) -> trimesh.Trimesh:
    if not cutters:
        return _copy(body)
    result = trimesh.boolean.difference(
        [_copy(body), *[_copy(cutter) for cutter in cutters]],
        engine="manifold",
        check_volume=True,
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _normalize(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    result = _copy(mesh)
    result.apply_translation(-np.asarray(result.bounds[0], dtype=float))
    return _clean(result)


def _one_body(mesh: trimesh.Trimesh, name: str) -> trimesh.Trimesh:
    result = _clean(mesh)
    if (
        len(result.split(only_watertight=False)) != 1
        or not result.is_watertight
        or not result.is_winding_consistent
        or float(result.volume) <= 0.0
    ):
        raise ValueError(f"{name} must be one watertight positive body")
    return result


def _support_profile() -> Polygon:
    """Full strap plus a compact 76.2 mm Palatine compression field."""

    visible_bottom = SUPPORT_TOTAL_DROP_MM - COMPACT_VISIBLE_DROP_MM
    front_underside = SUPPORT_TOTAL_DROP_MM - SUPPORT_FRONT_NOSE_MM
    profile = Polygon(
        (
            (0.0, 0.0),
            (SUPPORT_WALL_CHORD_MM, 0.0),
            (SUPPORT_WALL_CHORD_MM, visible_bottom),
            (2.0 * SUPPORT_WALL_CHORD_MM, visible_bottom),
            (SHELF_DEPTH_MM, front_underside),
            (SHELF_DEPTH_MM, SUPPORT_TOTAL_DROP_MM),
            (0.0, SUPPORT_TOTAL_DROP_MM),
        )
    )
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise ValueError("Support profile is invalid")
    return profile


def _support_core() -> trimesh.Trimesh:
    mesh = trimesh.creation.extrude_polygon(
        _support_profile(), height=SUPPORT_RUN_WIDTH_MM, engine="earcut"
    )
    return _clean(mesh)


def _wall_bore_cutters() -> tuple[trimesh.Trimesh, ...]:
    cutters: list[trimesh.Trimesh] = []
    q_length = SUPPORT_WALL_CHORD_MM + 2.0
    for drop in WALL_BORE_DROPS_BELOW_UNDERSIDE_MM:
        transform = trimesh.transformations.rotation_matrix(
            math.pi / 2.0, (0.0, 1.0, 0.0)
        )
        transform[:3, 3] = (
            SUPPORT_WALL_CHORD_MM / 2.0,
            SUPPORT_TOTAL_DROP_MM - drop,
            SUPPORT_RUN_WIDTH_MM / 2.0,
        )
        source = trimesh.creation.cylinder(
            radius=WALL_BORE_DIAMETER_MM / 2.0,
            height=q_length,
            sections=64,
            transform=transform,
        )
        cutters.append(_clean(source))
    return tuple(cutters)


def _palatine_additive_ornament() -> trimesh.Trimesh:
    """A stepped pendant added below the shell, inside the exact run width."""

    profile = Polygon(
        (
            (58.0, 88.0),
            (70.0, 92.0),
            (70.0, 96.0),
            (82.0, 96.0),
            (82.0, 101.0),
            (94.0, 101.0),
            (94.0, 106.0),
            (106.0, 106.0),
            (106.0, 118.0),
            (94.0, 114.0),
            (94.0, 112.0),
            (82.0, 112.0),
            (82.0, 108.0),
            (70.0, 108.0),
            (70.0, 104.0),
            (58.0, 100.0),
        )
    )
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise ValueError("Palatine ornament profile is invalid")
    ornament = trimesh.creation.extrude_polygon(
        profile, height=SUPPORT_RUN_WIDTH_MM - 0.8, engine="earcut"
    )
    # The pendant overlaps the shell in Q/E but stays 0.4 mm inboard of each
    # run face.  It therefore changes neither 31.75 mm support endpoint.
    ornament.apply_translation((0.0, 0.0, 0.4))
    return _clean(ornament)


def _capture_lugs() -> tuple[trimesh.Trimesh, ...]:
    # A 10 mm rear ramp grows from the capital instead of appearing as a new
    # island in the wall-face-down support orientation.  The lug is absent in
    # the first 4 mm of shelf depth, which also leaves a continuous rear bridge
    # in the mating cassette pocket.
    qe_profile = Polygon(
        (
            (4.0, SUPPORT_TOTAL_DROP_MM),
            (SHELF_DEPTH_MM, SUPPORT_TOTAL_DROP_MM),
            (SHELF_DEPTH_MM, SUPPORT_TOTAL_DROP_MM + CAPTURE_LUG_HEIGHT_MM),
            (14.0, SUPPORT_TOTAL_DROP_MM + CAPTURE_LUG_HEIGHT_MM),
        )
    )
    return tuple(
        _clean(
            trimesh.creation.extrude_polygon(
                qe_profile, height=CAPTURE_LUG_RUN_MM, engine="earcut"
            ).apply_translation((0.0, 0.0, center - CAPTURE_LUG_RUN_MM / 2.0))
        )
        for center in CAPTURE_LUG_CENTERS_SOURCE_RUN_MM
    )


def _capture_lug_slot_cutters() -> tuple[trimesh.Trimesh, ...]:
    # The removable key is front-inserted.  Preserve a 16 mm rear bridge so the
    # material above each slot
    # remains part of the support body instead of becoming a loose cap.
    q_start = SHELF_DEPTH_MM - SUPPORT_RETAINER_DEPTH_MM - JOINERY_CLEARANCE_PER_FACE_MM
    q_length = SHELF_DEPTH_MM - q_start + 1.0
    cutters: list[trimesh.Trimesh] = []
    slot_e_start = (
        SUPPORT_TOTAL_DROP_MM
        + CAPTURE_KEY_BASE_ABOVE_SHELF_UNDERSIDE_MM
        - JOINERY_CLEARANCE_PER_FACE_MM
    )
    slot_e_height = (
        SUPPORT_RETAINER_HEIGHT_MM + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM
    )
    for index, center in enumerate(CAPTURE_LUG_CENTERS_SOURCE_RUN_MM):
        cutters.append(
            _box(
            (
                q_length,
                slot_e_height,
                SUPPORT_RETAINER_RUN_MM + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM,
            ),
            (
                q_start,
                slot_e_start,
                center
                - SUPPORT_RETAINER_RUN_MM / 2.0
                - JOINERY_CLEARANCE_PER_FACE_MM,
            ),
            )
        )
        direction = -1.0 if index == 0 else 1.0
        shifted_center = center + direction * SUPPORT_RETAINER_BAYONET_SHIFT_MM
        pocket_min_run = min(
            center - SUPPORT_RETAINER_RUN_MM / 2.0,
            shifted_center - SUPPORT_RETAINER_RUN_MM / 2.0,
        ) - JOINERY_CLEARANCE_PER_FACE_MM
        pocket_max_run = max(
            center + SUPPORT_RETAINER_RUN_MM / 2.0,
            shifted_center + SUPPORT_RETAINER_RUN_MM / 2.0,
        ) + JOINERY_CLEARANCE_PER_FACE_MM
        for pocket_q_start, pocket_q_length in (
            (
                q_start + SUPPORT_RETAINER_HAND_GRIP_PROTRUSION_MM,
                SUPPORT_RETAINER_REAR_DOG_DEPTH_MM
                + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM,
            ),
            (
                SHELF_DEPTH_MM
                - SUPPORT_RETAINER_FRONT_HANDLE_DEPTH_MM
                - JOINERY_CLEARANCE_PER_FACE_MM,
                SUPPORT_RETAINER_FRONT_HANDLE_DEPTH_MM
                + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM,
            ),
        ):
            cutters.append(
                _box(
                    (
                        pocket_q_length,
                        slot_e_height,
                        pocket_max_run - pocket_min_run,
                    ),
                    (pocket_q_start, slot_e_start, pocket_min_run),
                )
            )
    return tuple(cutters)


def build_support_candidate() -> trimesh.Trimesh:
    """Build one full-drop, dual-bay-capital compact support candidate."""

    body = _union(
        (_support_core(), *_capture_lugs(), _palatine_additive_ornament())
    )
    result = _difference(
        body,
        (
            *_wall_bore_cutters(),
            *_capture_lug_slot_cutters(),
        ),
    )
    return _one_body(result, "R10 support")


def _channel_profile(center_y_mm: float) -> Polygon:
    """Asymmetric captured dovetail with one flat printable log face."""

    center = float(center_y_mm)
    bottom = BOTTOM_SKIN_MM
    return Polygon(
        (
            (center - CHANNEL_MAX_WIDTH_MM / 2.0, bottom),
            (center + CHANNEL_MAX_WIDTH_MM / 2.0, bottom),
            (center + CHANNEL_MAX_WIDTH_MM / 2.0, bottom + 6.4),
            (center + CHANNEL_TOP_WIDTH_MM / 2.0, bottom + 10.4),
            (center + CHANNEL_TOP_WIDTH_MM / 2.0, bottom + CHANNEL_CLEAR_HEIGHT_MM),
            (center - CHANNEL_MAX_WIDTH_MM / 2.0, bottom + CHANNEL_CLEAR_HEIGHT_MM),
        )
    )


def _nose_channel_profile(center_y_mm: float) -> Polygon:
    center = float(center_y_mm)
    return Polygon(
        (
            (center - 6.4, 7.2),
            (center + 6.4, 7.2),
            (center + 6.4, 13.2),
            (center + 5.4, 17.2),
            (center + 5.4, 24.0),
            (center - 6.4, 24.0),
        )
    )


def _extrude_yz_along_x(
    profile: Polygon, *, x_length_mm: float, x_start_mm: float
) -> trimesh.Trimesh:
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise ValueError("Y/Z extrusion profile is invalid")
    source = trimesh.creation.extrude_polygon(
        profile, height=_positive(x_length_mm, "X extrusion length"), engine="earcut"
    )
    source.vertices = np.asarray(source.vertices, dtype=float)[:, (2, 0, 1)]
    source.vertices[:, 0] += float(x_start_mm)
    return _clean(source)


def _extrude_xz_through_y(
    profile: Polygon, *, y_start_mm: float = -1.0
) -> trimesh.Trimesh:
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise ValueError("X/Z extrusion profile is invalid")
    source = trimesh.creation.extrude_polygon(
        profile,
        height=SHELF_DEPTH_MM - float(y_start_mm) + 1.0,
        engine="earcut",
    )
    # extrude_polygon emits X/Z/extrusion; relabel X/Y/Z.
    source.vertices = np.asarray(source.vertices, dtype=float)[:, (0, 2, 1)]
    source.vertices[:, 1] += float(y_start_mm)
    return _clean(source)


def _cassette_end_capture_cutters(
    length_mm: float, *, hand: str, lug_center_from_end_mm: float
) -> tuple[trimesh.Trimesh, ...]:
    """Pocket and tapered key-slot closure for one bay-local support lug."""

    if hand not in ("left", "right"):
        raise ValueError("Cassette hand must be 'left' or 'right'")
    center = float(lug_center_from_end_mm)
    lug_left = center - CAPTURE_LUG_RUN_MM / 2.0 - JOINERY_CLEARANCE_PER_FACE_MM
    lug_right = center + CAPTURE_LUG_RUN_MM / 2.0 + JOINERY_CLEARANCE_PER_FACE_MM
    key_left = center - SUPPORT_RETAINER_RUN_MM / 2.0 - JOINERY_CLEARANCE_PER_FACE_MM
    key_right = center + SUPPORT_RETAINER_RUN_MM / 2.0 + JOINERY_CLEARANCE_PER_FACE_MM

    # Both cavities close with <=45-degree ramps in the support-end print
    # direction instead of creating a sudden unsupported roof.
    pocket = Polygon(
        (
            (lug_left, -0.2),
            (lug_right, -0.2),
            (lug_right + CAPTURE_LUG_HEIGHT_MM, CAPTURE_LUG_HEIGHT_MM + 0.4),
            (lug_left - 0.2, CAPTURE_LUG_HEIGHT_MM + 0.4),
        )
    )
    key_bottom = (
        CAPTURE_KEY_BASE_ABOVE_SHELF_UNDERSIDE_MM
        - JOINERY_CLEARANCE_PER_FACE_MM
    )
    key_top = (
        CAPTURE_KEY_BASE_ABOVE_SHELF_UNDERSIDE_MM
        + SUPPORT_RETAINER_HEIGHT_MM
        + JOINERY_CLEARANCE_PER_FACE_MM
    )
    key_slot = Polygon(
        (
            (key_left, key_bottom),
            (key_right, key_bottom),
            (key_right, key_top),
            (key_left, key_top),
        )
    )
    cutters: list[trimesh.Trimesh] = [
        _extrude_xz_through_y(pocket, y_start_mm=4.0),
        _extrude_xz_through_y(
            key_slot,
            y_start_mm=(
                SHELF_DEPTH_MM
                - SUPPORT_RETAINER_DEPTH_MM
                - JOINERY_CLEARANCE_PER_FACE_MM
            ),
        ),
    ]
    shifted_center = center + SUPPORT_RETAINER_BAYONET_SHIFT_MM
    side_min_x = min(key_left, shifted_center - SUPPORT_RETAINER_RUN_MM / 2.0)
    side_max_x = max(key_right, shifted_center + SUPPORT_RETAINER_RUN_MM / 2.0)
    side_min_x -= JOINERY_CLEARANCE_PER_FACE_MM
    side_max_x += JOINERY_CLEARANCE_PER_FACE_MM
    for pocket_y_start, pocket_y_length in (
        (
            SHELF_DEPTH_MM
            - SUPPORT_RETAINER_DEPTH_MM
            + SUPPORT_RETAINER_HAND_GRIP_PROTRUSION_MM
            - JOINERY_CLEARANCE_PER_FACE_MM,
            SUPPORT_RETAINER_REAR_DOG_DEPTH_MM
            + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM,
        ),
        (
            SHELF_DEPTH_MM
            - SUPPORT_RETAINER_FRONT_HANDLE_DEPTH_MM
            - JOINERY_CLEARANCE_PER_FACE_MM,
            SUPPORT_RETAINER_FRONT_HANDLE_DEPTH_MM
            + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM,
        ),
    ):
        cutters.append(
            _box(
                (
                    side_max_x - side_min_x,
                    pocket_y_length,
                    key_top - key_bottom,
                ),
                (side_min_x, pocket_y_start, key_bottom),
            )
        )
    if hand == "left":
        return tuple(cutters)
    mirrored: list[trimesh.Trimesh] = []
    for cutter in cutters:
        result = _copy(cutter)
        result.vertices[:, 0] = length_mm - result.vertices[:, 0]
        result.fix_normals(multibody=True)
        mirrored.append(_clean(result))
    return tuple(mirrored)


def _cassette_midpoint_retainer_cutters(
    length_mm: float, *, hand: str
) -> tuple[trimesh.Trimesh, ...]:
    if hand == "left":
        x_start = length_mm - (
            LOG_RETAINER_RUN_MM / 2.0 + JOINERY_CLEARANCE_PER_FACE_MM
        )
    elif hand == "right":
        x_start = -(LOG_RETAINER_RUN_MM / 2.0 + JOINERY_CLEARANCE_PER_FACE_MM)
    else:
        raise ValueError("Cassette hand must be 'left' or 'right'")
    cutters: list[trimesh.Trimesh] = []
    for station in CHANNEL_STATIONS_Y_MM:
        slot_height = (
            SHELF_TOTAL_HEIGHT_MM
            - (MIDPOINT_KEY_BASE_IN_CASSETTE_MM - JOINERY_CLEARANCE_PER_FACE_MM)
            + 0.2
            if hand == "left"
            else LOG_RETAINER_HEIGHT_MM
            + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM
        )
        cutters.append(
            _box(
            (
                LOG_RETAINER_RUN_MM + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM,
                LOG_RETAINER_STATION_MM
                + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM,
                slot_height,
            ),
            (
                x_start,
                station
                - LOG_RETAINER_STATION_MM / 2.0
                - JOINERY_CLEARANCE_PER_FACE_MM,
                MIDPOINT_KEY_BASE_IN_CASSETTE_MM
                - JOINERY_CLEARANCE_PER_FACE_MM,
            ),
            )
        )
    return tuple(cutters)


def _build_cassette_half(
    *, printed_length_mm: float, hand: str, lug_center_from_end_mm: float
) -> trimesh.Trimesh:
    length = _positive(printed_length_mm, "printed cassette length")
    if hand not in ("left", "right"):
        raise ValueError("Cassette hand must be 'left' or 'right'")

    parts: list[trimesh.Trimesh] = [
        _box((length, SHELF_DEPTH_MM, BOTTOM_SKIN_MM), (0.0, 0.0, 0.0)),
        _box(
            (length, SHELF_DEPTH_MM, TOP_SKIN_MM),
            (0.0, 0.0, SHELF_TOTAL_HEIGHT_MM - TOP_SKIN_MM),
        ),
        _box((length, LOAD_WEB_MM, SHELF_TOTAL_HEIGHT_MM), (0.0, 0.0, 0.0)),
        _box(
            (length, LOAD_WEB_MM, SHELF_TOTAL_HEIGHT_MM),
            (0.0, SHELF_DEPTH_MM - LOAD_WEB_MM, 0.0),
        ),
    ]
    for station in CHANNEL_STATIONS_Y_MM:
        parts.append(
            _box(
                (length, CHANNEL_OUTER_WIDTH_MM, SHELF_TOTAL_HEIGHT_MM),
                (0.0, station - CHANNEL_OUTER_WIDTH_MM / 2.0, 0.0),
            )
        )

    # A complete support-end diaphragm seeds the saved end-on-plate build.
    main_channel_length = LOG_ENGAGEMENT_PER_HALF_MM - LOG_REDUCED_NOSE_LENGTH_MM
    nose_channel_length = LOG_REDUCED_NOSE_LENGTH_MM + LOG_NOSE_AXIAL_CLEARANCE_MM
    if hand == "left":
        end_origin = 0.0
        channel_start = length - main_channel_length
        nose_channel_start = channel_start - nose_channel_length
    else:
        end_origin = length - LOAD_WEB_MM
        channel_start = -0.2
        nose_channel_start = main_channel_length
    parts.append(
        _box(
            (LOAD_WEB_MM, SHELF_DEPTH_MM, SHELF_TOTAL_HEIGHT_MM),
            (end_origin, 0.0, 0.0),
        )
    )
    body = _union(parts)

    channel_length = main_channel_length + 0.2
    channel_cutters = tuple(
        _extrude_yz_along_x(
            _channel_profile(station),
            x_length_mm=channel_length,
            x_start_mm=channel_start,
        )
        for station in CHANNEL_STATIONS_Y_MM
    )
    nose_cutters = tuple(
        _extrude_yz_along_x(
            _nose_channel_profile(station),
            x_length_mm=nose_channel_length,
            x_start_mm=nose_channel_start,
        )
        for station in CHANNEL_STATIONS_Y_MM
    )
    result = _difference(
        body,
        (
            *channel_cutters,
            *nose_cutters,
            *_cassette_midpoint_retainer_cutters(length, hand=hand),
            *_cassette_end_capture_cutters(
                length, hand=hand, lug_center_from_end_mm=lug_center_from_end_mm
            ),
        ),
    )
    return _one_body(result, f"R10 {hand} cassette half")


def build_regular_cassette_half(*, hand: str) -> trimesh.Trimesh:
    """Build a 126.65 mm physical half for an interior planning bay."""

    return _build_cassette_half(
        printed_length_mm=PRINTED_REGULAR_HALF_LENGTH_MM,
        hand=hand,
        lug_center_from_end_mm=CAPTURE_LUG_CENTER_IN_REGULAR_HALF_MM,
    )


def build_terminal_cassette_half(*, hand: str) -> trimesh.Trimesh:
    """Build a 142.35 mm wall-terminal half with 0.35 mm wall clearance."""

    # The first support center is 15.875 mm from the wall.  Subtract the wall
    # clearance to obtain its local position, then select the bay-facing land.
    support_center_local = SUPPORT_HALF_LAND_NOMINAL_MM - WALL_ENDPOINT_CLEARANCE_MM
    lug_center = support_center_local + CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM
    return _build_cassette_half(
        printed_length_mm=PRINTED_TERMINAL_HALF_LENGTH_MM,
        hand=hand,
        lug_center_from_end_mm=lug_center,
    )


def _splice_log_profile() -> Polygon:
    """One-sided dovetail: flat minimum-Y face is the saved print face."""

    return Polygon(
        (
            (-LOG_WIDTH_MM / 2.0, 0.0),
            (LOG_WIDTH_MM / 2.0, 0.0),
            (LOG_WIDTH_MM / 2.0, 6.0),
            (LOG_TOP_WIDTH_MM / 2.0, 10.0),
            (LOG_TOP_WIDTH_MM / 2.0, LOG_HEIGHT_MM),
            (-LOG_WIDTH_MM / 2.0, LOG_HEIGHT_MM),
        )
    )


def _splice_log_nose_profile() -> Polygon:
    return Polygon(
        (
            (-6.0, 4.0),
            (6.0, 4.0),
            (6.0, 10.0),
            (5.0, 14.0),
            (5.0, 20.0),
            (-6.0, 20.0),
        )
    )


def build_splice_log() -> trimesh.Trimesh:
    """Build one 159.10 mm dovetailed log with one independent key slot."""

    main = _extrude_yz_along_x(
        _splice_log_profile(),
        x_length_mm=LOG_LENGTH_MM - 2.0 * LOG_REDUCED_NOSE_LENGTH_MM,
        x_start_mm=LOG_REDUCED_NOSE_LENGTH_MM,
    )
    left_nose = _extrude_yz_along_x(
        _splice_log_nose_profile(),
        x_length_mm=LOG_REDUCED_NOSE_LENGTH_MM + 0.1,
        x_start_mm=0.0,
    )
    right_nose = _extrude_yz_along_x(
        _splice_log_nose_profile(),
        x_length_mm=LOG_REDUCED_NOSE_LENGTH_MM + 0.1,
        x_start_mm=LOG_LENGTH_MM - LOG_REDUCED_NOSE_LENGTH_MM - 0.1,
    )
    body = _union((main, left_nose, right_nose))
    cutter = _box(
        (
            LOG_RETAINER_RUN_MM + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM,
            LOG_WIDTH_MM + 2.0,
            LOG_RETAINER_HEIGHT_MM + 2.0 * JOINERY_CLEARANCE_PER_FACE_MM,
        ),
        (
            LOG_LENGTH_MM / 2.0
            - LOG_RETAINER_RUN_MM / 2.0
            - JOINERY_CLEARANCE_PER_FACE_MM,
            -LOG_WIDTH_MM / 2.0 - 1.0,
            LOG_KEY_SLOT_BASE_MM,
        ),
    )
    return _one_body(_difference(body, (cutter,)), "R10 splice log")


def build_log_retainer() -> trimesh.Trimesh:
    """Build one keyed retainer with its own flush left-half access cap."""

    return _one_body(
        _union(
            (
                _box(
                    (
                        LOG_RETAINER_RUN_MM,
                        LOG_RETAINER_STATION_MM,
                        LOG_RETAINER_HEIGHT_MM,
                    ),
                    (0.0, 0.0, 0.0),
                ),
                _box(
                    (
                        LOG_RETAINER_CAP_RUN_MM,
                        LOG_RETAINER_STATION_MM,
                        LOG_RETAINER_CAP_HEIGHT_MM + 0.1,
                    ),
                    (
                        LOG_RETAINER_CAP_X_START_MM,
                        0.0,
                        LOG_RETAINER_HEIGHT_MM - 0.1,
                    ),
                ),
            )
        ),
        "R10 log retainer",
    )


def build_support_retainer() -> trimesh.Trimesh:
    """Build one T-ended bayonet bar; retention only, never load credit."""

    return _one_body(
        _union(
            (
                _box(
                    (
                        SUPPORT_RETAINER_SHAFT_RUN_MM,
                        SUPPORT_RETAINER_DEPTH_MM,
                        SUPPORT_RETAINER_HEIGHT_MM,
                    ),
                    (
                        (SUPPORT_RETAINER_RUN_MM - SUPPORT_RETAINER_SHAFT_RUN_MM)
                        / 2.0,
                        0.0,
                        0.0,
                    ),
                ),
                _box(
                    (
                        SUPPORT_RETAINER_RUN_MM,
                        SUPPORT_RETAINER_REAR_DOG_DEPTH_MM,
                        SUPPORT_RETAINER_HEIGHT_MM,
                    ),
                    (0.0, 0.0, 0.0),
                ),
                _box(
                    (
                        SUPPORT_RETAINER_RUN_MM,
                        SUPPORT_RETAINER_FRONT_HANDLE_DEPTH_MM,
                        SUPPORT_RETAINER_HEIGHT_MM,
                    ),
                    (
                        0.0,
                        SUPPORT_RETAINER_DEPTH_MM
                        - SUPPORT_RETAINER_FRONT_HANDLE_DEPTH_MM,
                        0.0,
                    ),
                ),
            )
        ),
        "R10 support retainer",
    )


def orient_support_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Put the wall-contact face down, then rotate 45 degrees on the bed."""

    result = _copy(mesh)
    old = np.asarray(result.vertices, dtype=float).copy()
    # saved X/Y/Z = source run/elevation/q; the complete wall face is layer 1.
    result.vertices = old[:, (2, 1, 0)]
    result.fix_normals(multibody=True)
    result = _normalize(result)
    rotation = trimesh.transformations.rotation_matrix(
        math.radians(45.0), (0.0, 0.0, 1.0)
    )
    result.apply_transform(rotation)
    return _normalize(result)


def orient_cassette_for_print(mesh: trimesh.Trimesh, *, hand: str) -> trimesh.Trimesh:
    """Put the solid support-end diaphragm on the plate."""

    if hand not in ("left", "right"):
        raise ValueError("Cassette hand must be 'left' or 'right'")
    result = _copy(mesh)
    old = np.asarray(result.vertices, dtype=float).copy()
    if hand == "right":
        old[:, 0] = float(result.bounds[1, 0]) - old[:, 0]
    # saved X/Y/Z = installed Y/Z/X.
    result.vertices = old[:, (1, 2, 0)]
    result.fix_normals(multibody=True)
    return _normalize(result)


def orient_log_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Put the log's complete flat minimum-Y side on the plate."""

    result = _copy(mesh)
    old = np.asarray(result.vertices, dtype=float).copy()
    # saved X/Y/Z = installed X/Z/Y.
    result.vertices = old[:, (0, 2, 1)]
    result.fix_normals(multibody=True)
    return _normalize(result)


def orient_flat_retainer_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    return _normalize(mesh)


def _support_to_installed(mesh: trimesh.Trimesh, center_x_mm: float) -> trimesh.Trimesh:
    result = _copy(mesh)
    old = np.asarray(result.vertices, dtype=float).copy()
    result.vertices = old[:, (2, 0, 1)]
    result.fix_normals(multibody=True)
    result.apply_translation((center_x_mm - SUPPORT_RUN_WIDTH_MM / 2.0, 0.0, 0.0))
    return _clean(result)


def _installed_support_retainer(
    *, center_x_mm: float, bay_direction: float, lateral_shift_mm: float, outward_mm: float
) -> trimesh.Trimesh:
    """Place one key in its straight lane, then optionally shift toward its bay."""

    if bay_direction not in (-1.0, 1.0):
        raise ValueError("Bay direction must be -1 or +1")
    shift = float(lateral_shift_mm)
    outward = float(outward_mm)
    if not math.isfinite(shift) or not 0.0 <= shift <= SUPPORT_RETAINER_BAYONET_SHIFT_MM:
        raise ValueError("Support-retainer shift is outside its authored bayonet travel")
    if not math.isfinite(outward) or outward < 0.0:
        raise ValueError("Support-retainer outward travel must be finite and nonnegative")
    key = build_support_retainer()
    key.apply_translation(
        (
            center_x_mm
            - SUPPORT_RETAINER_RUN_MM / 2.0
            + bay_direction * shift,
            SHELF_DEPTH_MM
            - SUPPORT_RETAINER_DEPTH_MM
            + SUPPORT_RETAINER_HAND_GRIP_PROTRUSION_MM
            + outward,
            SUPPORT_TOTAL_DROP_MM
            + CAPTURE_KEY_BASE_ABOVE_SHELF_UNDERSIDE_MM,
        )
    )
    return _clean(key)


def build_installed_one_bay_parts() -> dict[str, trimesh.Trimesh]:
    """Return the twelve separate articles in the nominal tabletop pose."""

    left_half = build_regular_cassette_half(hand="left")
    left_half.apply_translation(
        (SUPPORT_LINE_CLEARANCE_MM / 2.0, 0.0, SUPPORT_TOTAL_DROP_MM)
    )
    right_half = build_regular_cassette_half(hand="right")
    right_half.apply_translation(
        (
            ONE_BAY_MIDPOINT_MM + MIDPOINT_SEAM_CLEARANCE_MM / 2.0,
            0.0,
            SUPPORT_TOTAL_DROP_MM,
        )
    )

    result: dict[str, trimesh.Trimesh] = {
        "r10_one_bay_left_support": _support_to_installed(
            build_support_candidate(), ONE_BAY_SUPPORT_CENTERS_MM[0]
        ),
        "r10_one_bay_right_support": _support_to_installed(
            build_support_candidate(), ONE_BAY_SUPPORT_CENTERS_MM[1]
        ),
        "r10_one_bay_left_cassette_half": _clean(left_half),
        "r10_one_bay_right_cassette_half": _clean(right_half),
    }

    log_x = ONE_BAY_MIDPOINT_MM - LOG_LENGTH_MM / 2.0
    log_z = SUPPORT_TOTAL_DROP_MM + BOTTOM_SKIN_MM + JOINERY_CLEARANCE_PER_FACE_MM
    for label, station in zip(("rear", "center", "front"), CHANNEL_STATIONS_Y_MM):
        log = build_splice_log()
        log.apply_translation((log_x, station, log_z))
        result[f"r10_one_bay_{label}_splice_log"] = _clean(log)

        key = build_log_retainer()
        key.apply_translation(
            (
                ONE_BAY_MIDPOINT_MM - LOG_RETAINER_RUN_MM / 2.0,
                station - LOG_RETAINER_STATION_MM / 2.0,
                SUPPORT_TOTAL_DROP_MM + MIDPOINT_KEY_BASE_IN_CASSETTE_MM,
            )
        )
        result[f"r10_one_bay_{label}_log_retainer"] = _clean(key)

    support_key_specs = (
        ("left", CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM, 1.0),
        (
            "right",
            SUPPORT_PITCH_MM - CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM,
            -1.0,
        ),
    )
    for label, center_x, bay_direction in support_key_specs:
        result[f"r10_one_bay_{label}_support_retainer"] = (
            _installed_support_retainer(
                center_x_mm=center_x,
                bay_direction=bay_direction,
                lateral_shift_mm=SUPPORT_RETAINER_BAYONET_SHIFT_MM,
                outward_mm=0.0,
            )
        )

    return result


def build_saved_one_bay_parts() -> dict[str, trimesh.Trimesh]:
    """Return every one-bay article in a deterministic A1 mini orientation."""

    support_mesh = build_support_candidate()
    left_half = build_regular_cassette_half(hand="left")
    right_half = build_regular_cassette_half(hand="right")
    log_mesh = build_splice_log()
    log_key = build_log_retainer()
    support_key = build_support_retainer()
    return {
        "r10_one_bay_left_support": orient_support_for_print(support_mesh),
        "r10_one_bay_right_support": orient_support_for_print(support_mesh),
        "r10_one_bay_left_cassette_half": orient_cassette_for_print(
            left_half, hand="left"
        ),
        "r10_one_bay_right_cassette_half": orient_cassette_for_print(
            right_half, hand="right"
        ),
        "r10_one_bay_rear_splice_log": orient_log_for_print(log_mesh),
        "r10_one_bay_center_splice_log": orient_log_for_print(log_mesh),
        "r10_one_bay_front_splice_log": orient_log_for_print(log_mesh),
        "r10_one_bay_rear_log_retainer": orient_flat_retainer_for_print(log_key),
        "r10_one_bay_center_log_retainer": orient_flat_retainer_for_print(log_key),
        "r10_one_bay_front_log_retainer": orient_flat_retainer_for_print(log_key),
        "r10_one_bay_left_support_retainer": orient_flat_retainer_for_print(
            support_key
        ),
        "r10_one_bay_right_support_retainer": orient_flat_retainer_for_print(
            support_key
        ),
    }


def build_saved_terminal_halves() -> dict[str, trimesh.Trimesh]:
    left = build_terminal_cassette_half(hand="left")
    right = build_terminal_cassette_half(hand="right")
    return {
        "r10_left_wall_terminal_cassette_half": orient_cassette_for_print(
            left, hand="left"
        ),
        "r10_right_wall_terminal_cassette_half": orient_cassette_for_print(
            right, hand="right"
        ),
    }


def _intersection_volume(first: trimesh.Trimesh, second: trimesh.Trimesh) -> float:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        overlap = trimesh.boolean.intersection(
            [_copy(first), _copy(second)], engine="manifold", check_volume=False
        )
        if overlap is None:
            return 0.0
        if isinstance(overlap, list):
            return float(
                sum(abs(float(item.volume)) for item in overlap if not item.is_empty)
            )
        if overlap.is_empty:
            return 0.0
        volume = abs(float(overlap.volume))
        return 0.0 if volume <= 1.0e-8 else volume


def installed_target_maximum_intersection_mm3() -> float:
    parts = build_installed_one_bay_parts()
    names = tuple(parts)
    maximum = 0.0
    for index, first_name in enumerate(names):
        first = parts[first_name]
        for second_name in names[index + 1 :]:
            second = parts[second_name]
            if not (
                np.all(first.bounds[1] > second.bounds[0] + GEOMETRY_EPSILON)
                and np.all(second.bounds[1] > first.bounds[0] + GEOMETRY_EPSILON)
            ):
                continue
            maximum = max(maximum, _intersection_volume(first, second))
    return float(maximum)


def right_half_capture_path_maximum_intersection_mm3() -> float:
    """Sample the off-support preassembly slide and its exact reverse."""

    parts = build_installed_one_bay_parts()
    moving_source = parts["r10_one_bay_right_cassette_half"]
    fixed_names = (
        "r10_one_bay_rear_splice_log",
        "r10_one_bay_center_splice_log",
        "r10_one_bay_front_splice_log",
        "r10_one_bay_rear_log_retainer",
        "r10_one_bay_center_log_retainer",
        "r10_one_bay_front_log_retainer",
    )
    maximum = 0.0
    for outward in np.linspace(80.0, 0.0, 17):
        moving = _copy(moving_source)
        moving.apply_translation((float(outward), 0.0, 0.0))
        for fixed_name in fixed_names:
            maximum = max(
                maximum,
                _intersection_volume(moving, parts[fixed_name]),
            )
    return float(maximum)


def support_retainer_service_path_maximum_intersection_mm3() -> float:
    """Prove the reversible insert-then-shift path for both bay-local keys.

    Each key enters from the shelf front in its straight four-millimetre shaft
    lane.  Only after its rear dog reaches the end pocket is it shifted 2.4 mm
    toward its own bay.  Disassembly reverses those two motions exactly.
    """

    parts = build_installed_one_bay_parts()
    cases = (
        (
            CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM,
            1.0,
            parts["r10_one_bay_left_support"],
            parts["r10_one_bay_left_cassette_half"],
        ),
        (
            SUPPORT_PITCH_MM - CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM,
            -1.0,
            parts["r10_one_bay_right_support"],
            parts["r10_one_bay_right_cassette_half"],
        ),
    )
    maximum = 0.0
    for center_x, direction, support, cassette in cases:
        # Start with the entire 136 mm key beyond the front face, then enter
        # the unshifted service lane.  Reverse removal uses the same samples.
        for outward in np.linspace(SUPPORT_RETAINER_DEPTH_MM, 0.0, 35):
            moving = _installed_support_retainer(
                center_x_mm=center_x,
                bay_direction=direction,
                lateral_shift_mm=0.0,
                outward_mm=float(outward),
            )
            maximum = max(
                maximum,
                _intersection_volume(moving, support),
                _intersection_volume(moving, cassette),
            )
        # With the key fully inserted, the two widened ends move only inside
        # their authored end pockets while the narrow shaft remains in-lane.
        for shift in np.linspace(0.0, SUPPORT_RETAINER_BAYONET_SHIFT_MM, 13):
            moving = _installed_support_retainer(
                center_x_mm=center_x,
                bay_direction=direction,
                lateral_shift_mm=float(shift),
                outward_mm=0.0,
            )
            maximum = max(
                maximum,
                _intersection_volume(moving, support),
                _intersection_volume(moving, cassette),
            )
    return float(maximum)


def support_retainer_walkout_stop_intersection_mm3() -> float:
    """Return the weaker of two positive stop contacts under a 1 mm pull.

    A positive value is desired here: after the lateral bayonet shift, the
    rear eight-millimetre dog collides with the narrow service-lane shoulder
    if the key is pulled toward the front.  No friction or snap is credited.
    """

    parts = build_installed_one_bay_parts()
    cases = (
        (
            CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM,
            1.0,
            parts["r10_one_bay_left_support"],
            parts["r10_one_bay_left_cassette_half"],
        ),
        (
            SUPPORT_PITCH_MM - CAPTURE_LUG_CENTER_FROM_SUPPORT_LINE_MM,
            -1.0,
            parts["r10_one_bay_right_support"],
            parts["r10_one_bay_right_cassette_half"],
        ),
    )
    stop_contacts: list[float] = []
    for center_x, direction, support, cassette in cases:
        pulled = _installed_support_retainer(
            center_x_mm=center_x,
            bay_direction=direction,
            lateral_shift_mm=SUPPORT_RETAINER_BAYONET_SHIFT_MM,
            outward_mm=1.0,
        )
        stop_contacts.append(
            _intersection_volume(pulled, support)
            + _intersection_volume(pulled, cassette)
        )
    return float(min(stop_contacts))


def _section_polygon_from_mesh(mesh: trimesh.Trimesh, x_mm: float) -> Polygon:
    """Extract the single final-mesh Y/Z loop at an exact X station."""

    section = mesh.section(
        plane_origin=(float(x_mm), 0.0, 0.0), plane_normal=(1.0, 0.0, 0.0)
    )
    if section is None:
        raise ValueError("Requested splice-log section does not exist")
    loops = tuple(section.discrete)
    if len(loops) != 1:
        raise ValueError("Splice-log section must remain one continuous loop")
    points = np.asarray(loops[0], dtype=float)
    polygon = Polygon(points[:, (1, 2)])
    if (
        polygon.is_empty
        or not polygon.is_valid
        or polygon.area <= 0.0
        or len(polygon.interiors) != 0
    ):
        raise ValueError("Splice-log section is not one valid continuous polygon")
    return polygon


def _polygon_section_properties(
    polygon: Polygon,
) -> tuple[float, float, float, float]:
    """Area, Z centroid, centroidal I-y, and governing elastic S."""

    coordinates = np.asarray(polygon.exterior.coords, dtype=float)
    y0 = coordinates[:-1, 0]
    z0 = coordinates[:-1, 1]
    y1 = coordinates[1:, 0]
    z1 = coordinates[1:, 1]
    cross = y0 * z1 - y1 * z0
    signed_area = 0.5 * float(np.sum(cross))
    if abs(signed_area) <= GEOMETRY_EPSILON:
        raise ValueError("Section polygon has zero signed area")
    centroid_z = float(np.sum((z0 + z1) * cross) / (6.0 * signed_area))
    second_moment_origin = float(
        np.sum((z0 * z0 + z0 * z1 + z1 * z1) * cross) / 12.0
    )
    if signed_area < 0.0:
        signed_area = -signed_area
        second_moment_origin = -second_moment_origin
    second_moment_centroid = (
        second_moment_origin - signed_area * centroid_z * centroid_z
    )
    z_min, z_max = float(polygon.bounds[1]), float(polygon.bounds[3])
    extreme_distance = max(z_max - centroid_z, centroid_z - z_min)
    governing_section_modulus = second_moment_centroid / extreme_distance
    if second_moment_centroid <= 0.0 or governing_section_modulus <= 0.0:
        raise ValueError("Section properties must be positive")
    return (
        float(signed_area),
        centroid_z,
        float(second_moment_centroid),
        float(governing_section_modulus),
    )


def log_section_evidence() -> LogSectionEvidence:
    """Measure gross and notched midpoint properties from the final log mesh."""

    log = build_splice_log()
    gross = _polygon_section_properties(
        _section_polygon_from_mesh(log, LOG_REDUCED_NOSE_LENGTH_MM + 1.0)
    )
    net = _polygon_section_properties(
        _section_polygon_from_mesh(log, LOG_LENGTH_MM / 2.0)
    )
    return LogSectionEvidence(
        gross_area_mm2=gross[0],
        gross_centroid_z_mm=gross[1],
        gross_second_moment_about_y_mm4=gross[2],
        gross_governing_section_modulus_mm3=gross[3],
        net_area_mm2=net[0],
        net_centroid_z_mm=net[1],
        net_second_moment_about_y_mm4=net[2],
        net_governing_section_modulus_mm3=net[3],
        net_to_gross_area_ratio=net[0] / gross[0],
        net_to_gross_second_moment_ratio=net[2] / gross[2],
        net_to_gross_section_modulus_ratio=net[3] / gross[3],
        material_capacity_claimed=False,
    )


def _washer_land_annulus_probe(drop_mm: float) -> trimesh.Trimesh:
    transform = trimesh.transformations.rotation_matrix(
        math.pi / 2.0, (0.0, 1.0, 0.0)
    )
    transform[:3, 3] = (
        WASHER_LAND_EVIDENCE_THICKNESS_MM / 2.0,
        SUPPORT_TOTAL_DROP_MM - float(drop_mm),
        SUPPORT_RUN_WIDTH_MM / 2.0,
    )
    outer = trimesh.creation.cylinder(
        radius=WASHER_BEARING_LAND_OUTER_DIAMETER_MM / 2.0,
        height=WASHER_LAND_EVIDENCE_THICKNESS_MM,
        sections=64,
        transform=transform,
    )
    inner_transform = transform.copy()
    inner_transform[:3, 3] = (
        WASHER_LAND_EVIDENCE_THICKNESS_MM / 2.0,
        SUPPORT_TOTAL_DROP_MM - float(drop_mm),
        SUPPORT_RUN_WIDTH_MM / 2.0,
    )
    inner = trimesh.creation.cylinder(
        radius=WALL_BORE_DIAMETER_MM / 2.0,
        height=WASHER_LAND_EVIDENCE_THICKNESS_MM + 0.2,
        sections=64,
        transform=inner_transform,
    )
    return _one_body(_difference(_clean(outer), (_clean(inner),)), "washer annulus")


def wall_washer_land_evidence() -> tuple[WasherLandEvidence, ...]:
    """Prove a continuous 27.025 mm surface annulus at every round bore."""

    support = build_support_candidate()
    records: list[WasherLandEvidence] = []
    for drop in WALL_BORE_DROPS_BELOW_UNDERSIDE_MM:
        probe = _washer_land_annulus_probe(drop)
        overlap = trimesh.boolean.intersection(
            [_copy(probe), _copy(support)], engine="manifold", check_volume=False
        )
        if overlap is None or isinstance(overlap, list):
            solid_volume = 0.0
            continuous = False
        else:
            overlap = _clean(overlap)
            solid_volume = abs(float(overlap.volume))
            continuous = (
                not overlap.is_empty
                and len(overlap.split(only_watertight=False)) == 1
                and overlap.is_watertight
            )
        probe_volume = abs(float(probe.volume))
        ratio = solid_volume / probe_volume if probe_volume > 0.0 else 0.0
        center_elevation = SUPPORT_TOTAL_DROP_MM - drop
        radius = WASHER_BEARING_LAND_OUTER_DIAMETER_MM / 2.0
        records.append(
            WasherLandEvidence(
                bore_drop_below_shelf_underside_mm=float(drop),
                bore_diameter_mm=WALL_BORE_DIAMETER_MM,
                outer_diameter_mm=WASHER_BEARING_LAND_OUTER_DIAMETER_MM,
                radial_land_mm=(
                    WASHER_BEARING_LAND_OUTER_DIAMETER_MM
                    - WALL_BORE_DIAMETER_MM
                )
                / 2.0,
                surface_thickness_checked_mm=WASHER_LAND_EVIDENCE_THICKNESS_MM,
                minimum_run_edge_margin_mm=(
                    SUPPORT_RUN_WIDTH_MM / 2.0 - radius
                ),
                minimum_vertical_edge_margin_mm=(
                    min(center_elevation, SUPPORT_TOTAL_DROP_MM - center_elevation)
                    - radius
                ),
                annulus_probe_volume_mm3=probe_volume,
                annulus_solid_volume_mm3=solid_volume,
                solid_volume_ratio=ratio,
                continuous_single_body=continuous,
                full_solid=continuous and ratio >= 1.0 - 1.0e-6,
            )
        )
    return tuple(records)


def print_envelope(mesh: trimesh.Trimesh) -> PrintEnvelope:
    raw = tuple(float(value) for value in mesh.extents)
    bed_allowance = 2.0 * (
        BRIM_MM + BRIM_OBJECT_GAP_MM + RESERVE_PER_BED_EDGE_MM
    )
    required = (raw[0] + bed_allowance, raw[1] + bed_allowance, raw[2])
    return PrintEnvelope(
        raw_part_mm=raw,
        required_build_volume_mm=required,
        available_build_volume_mm=A1_MINI_BUILD_VOLUME_MM,
        brim_mm=BRIM_MM,
        brim_object_gap_mm=BRIM_OBJECT_GAP_MM,
        reserve_per_bed_edge_mm=RESERVE_PER_BED_EDGE_MM,
        fits=all(
            need <= have + GEOMETRY_EPSILON
            for need, have in zip(required, A1_MINI_BUILD_VOLUME_MM)
        ),
    )


def print_envelopes() -> dict[str, PrintEnvelope]:
    parts = {**build_saved_one_bay_parts(), **build_saved_terminal_halves()}
    return {name: print_envelope(mesh) for name, mesh in parts.items()}


def joinery_clearance_evidence() -> JoineryClearanceEvidence:
    internal_height = SHELF_TOTAL_HEIGHT_MM - TOP_SKIN_MM - BOTTOM_SKIN_MM
    if not math.isclose(internal_height, CHANNEL_CLEAR_HEIGHT_MM, abs_tol=1.0e-9):
        raise AssertionError("Cassette skins no longer close the exact channel height")
    if not math.isclose(
        2.0 * LOG_ENGAGEMENT_PER_HALF_MM + MIDPOINT_SEAM_CLEARANCE_MM,
        LOG_LENGTH_MM,
        abs_tol=1.0e-9,
    ):
        raise AssertionError("Log length no longer preserves physical engagement")
    return JoineryClearanceEvidence(
        midpoint_seam_mm=MIDPOINT_SEAM_CLEARANCE_MM,
        support_line_seam_mm=SUPPORT_LINE_CLEARANCE_MM,
        wall_endpoint_mm=WALL_ENDPOINT_CLEARANCE_MM,
        channel_clearance_per_face_mm=JOINERY_CLEARANCE_PER_FACE_MM,
        channel_clear_height_mm=CHANNEL_CLEAR_HEIGHT_MM,
        cassette_internal_height_mm=internal_height,
        log_engagement_per_half_mm=LOG_ENGAGEMENT_PER_HALF_MM,
        physical_bearing_contact_per_half_mm=PHYSICAL_BEARING_CONTACT_PER_HALF_MM,
        independent_log_retainers_per_bay=LOG_RETAINER_COUNT_PER_BAY,
        bay_local_support_retainers_per_bay=SUPPORT_RETAINERS_PER_BAY,
    )


def build_one_bay_evidence() -> OneBayEvidence:
    installed = build_installed_one_bay_parts()
    saved = build_saved_one_bay_parts()
    orientation: dict[str, str] = {}
    for name in saved:
        if name.endswith("support"):
            orientation[name] = "wall_face_down_rotated_45_degrees"
        elif "cassette_half" in name:
            orientation[name] = "solid_support_end_diaphragm_on_plate"
        elif name.endswith("splice_log"):
            orientation[name] = "flat_dovetail_side_on_plate"
        else:
            orientation[name] = "largest_flat_face_on_plate"
    parts = tuple(
        OneBayPart(
            name=name,
            installed_mesh=installed[name],
            saved_print_mesh=saved[name],
            saved_orientation=orientation[name],
            support_required=False,
            capacity_credit=not name.endswith("retainer"),
        )
        for name in installed
    )
    target_intersection = installed_target_maximum_intersection_mm3()
    capture_intersection = right_half_capture_path_maximum_intersection_mm3()
    support_service_intersection = (
        support_retainer_service_path_maximum_intersection_mm3()
    )
    support_stop_intersection = support_retainer_walkout_stop_intersection_mm3()
    section = log_section_evidence()
    washer_lands = wall_washer_land_evidence()
    return OneBayEvidence(
        parts=parts,
        support_centers_mm=ONE_BAY_SUPPORT_CENTERS_MM,
        planning_bay_pitch_mm=SUPPORT_PITCH_MM,
        printed_regular_half_length_mm=PRINTED_REGULAR_HALF_LENGTH_MM,
        printed_terminal_half_length_mm=PRINTED_TERMINAL_HALF_LENGTH_MM,
        printed_log_length_mm=LOG_LENGTH_MM,
        joinery=joinery_clearance_evidence(),
        one_bay_part_count=len(parts),
        field_support_count=FIELD_SUPPORT_COUNT,
        field_bay_count=FIELD_BAY_COUNT,
        aesthetic_contract_id=AESTHETIC_CONTRACT_ID,
        positive_log_body_shoulders_authored=True,
        log_retainer_preassembly_path_authored=True,
        log_key_top_access_pockets_per_bay=LOG_KEY_TOP_ACCESS_POCKETS_PER_BAY,
        flush_log_key_access_closures_authored=True,
        target_pose_maximum_intersection_mm3=target_intersection,
        target_pose_collision_free=target_intersection <= 1.0e-5,
        right_half_capture_path_maximum_intersection_mm3=capture_intersection,
        right_half_capture_path_collision_free=capture_intersection <= 1.0e-5,
        support_retainer_positive_capture_authored=(
            support_service_intersection <= 1.0e-5
            and support_stop_intersection > 1.0e-5
        ),
        support_retainer_service_path_maximum_intersection_mm3=(
            support_service_intersection
        ),
        support_retainer_service_path_collision_free=(
            support_service_intersection <= 1.0e-5
        ),
        support_retainer_walkout_stop_intersection_mm3=(
            support_stop_intersection
        ),
        support_retainer_hand_grip_protrusion_mm=(
            SUPPORT_RETAINER_HAND_GRIP_PROTRUSION_MM
        ),
        log_section=section,
        washer_lands=washer_lands,
        midpoint_net_section_geometry_authored=(
            section.net_area_mm2 > 0.0
            and section.net_second_moment_about_y_mm4 > 0.0
            and section.net_governing_section_modulus_mm3 > 0.0
            and not section.material_capacity_claimed
        ),
        midpoint_notched_log_section_qualified=False,
        release_blockers=(),
        tabletop_assembly_order=(
            "off the supports, slide the three independent dovetail logs "
            "into the left cassette half",
            "with the right half absent, lower each independent retainer "
            "through the left-half top access into its exposed log notch",
            "slide the right half over the logs and retainer ends so its "
            "closed top captures all three keys",
            "place two printed supports at the 254 mm planning centers",
            "lower the joined cassette onto its two 15.70 mm physical support contacts",
            "at each cassette/support contact, insert its bay-local support "
            "retainer straight from the front and shift it 2.4 mm toward "
            "that bay to place its rear dog behind the positive shoulder; "
            "the integrated handle remains 4.0 mm proud for a hand grip",
            "for disassembly shift each support retainer 2.4 mm away from "
            "its bay, grasp the 4.0 mm handle and pull it straight forward, "
            "lift the cassette "
            "clear of both lugs, then reverse the off-support slide",
        ),
        no_load_boundary=(
            "Qualification geometry only: current rating is 0 kg / 0 lb. "
            "Printed bores are candidates, retainers receive zero gravity or "
            "bending credit, and no wall installation is authorized."
        ),
    )


__all__ = (
    "A1_MINI_BUILD_VOLUME_MM",
    "AESTHETIC_CONTRACT_ID",
    "FIELD_BAY_COUNT",
    "FIELD_LOG_KEY_TOP_ACCESS_POCKET_COUNT",
    "FIELD_SUPPORT_COUNT",
    "JoineryClearanceEvidence",
    "LogSectionEvidence",
    "LOG_ENGAGEMENT_PER_HALF_MM",
    "LOG_LENGTH_MM",
    "LOG_RETAINER_CAP_HEIGHT_MM",
    "LOG_RETAINER_CAP_RUN_MM",
    "LOG_RETAINER_COUNT_PER_BAY",
    "MIDPOINT_SEAM_CLEARANCE_MM",
    "OneBayEvidence",
    "OneBayPart",
    "PHYSICAL_BEARING_CONTACT_PER_HALF_MM",
    "PRINTED_REGULAR_HALF_LENGTH_MM",
    "PRINTED_TERMINAL_HALF_LENGTH_MM",
    "PrintEnvelope",
    "RATED_LOAD_KG",
    "RATED_LOAD_LB",
    "SHELF_TOTAL_HEIGHT_MM",
    "SUPPORT_LINE_CLEARANCE_MM",
    "SUPPORT_PITCH_MM",
    "SUPPORT_RETAINER_BAYONET_SHIFT_MM",
    "SUPPORT_RETAINER_HAND_GRIP_PROTRUSION_MM",
    "SUPPORT_RETAINERS_PER_BAY",
    "WASHER_BEARING_LAND_OUTER_DIAMETER_MM",
    "WasherLandEvidence",
    "WALL_ENDPOINT_CLEARANCE_MM",
    "build_installed_one_bay_parts",
    "build_log_retainer",
    "build_one_bay_evidence",
    "build_regular_cassette_half",
    "build_saved_one_bay_parts",
    "build_saved_terminal_halves",
    "build_splice_log",
    "build_support_candidate",
    "build_support_retainer",
    "build_terminal_cassette_half",
    "installed_target_maximum_intersection_mm3",
    "joinery_clearance_evidence",
    "log_section_evidence",
    "orient_cassette_for_print",
    "orient_log_for_print",
    "orient_support_for_print",
    "print_envelope",
    "print_envelopes",
    "right_half_capture_path_maximum_intersection_mm3",
    "support_retainer_service_path_maximum_intersection_mm3",
    "support_retainer_walkout_stop_intersection_mm3",
    "wall_washer_land_evidence",
)
