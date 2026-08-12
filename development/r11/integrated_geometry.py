#!/usr/bin/env python3
"""Fail-closed R11 integrated reciprocal Lincoln-log geometry.

This module is qualification geometry, not a released shelf, load rating, or
wall-installation instruction.  It replaces the R10 loose midpoint logs and
retainers with two handed, three-rib half-decks and one bay-local Palatine
keystone.  The half-decks are authored for a broad-face, top-face-down print
orientation on one A1-mini plate *per half-deck*.

Installed axes are X along the wall, Y from wall to shelf front, and Z upward.
Each half-deck is authored locally from its support end toward the bay
midpoint.  In an assembled bay the right article is mirrored in X.

The 55 mm reciprocal overlap uses side-by-side, full-height rib lanes.  This
avoids the section loss of a half-height lap: one 9.6 x 32 mm lane belongs to
each half, with a real 0.8 mm gap (0.4 mm per mating face).  The three lanes
are fixed at Y=16, 76.2, and 136.4 mm.  The small keystone receives no gravity
or material-capacity credit; it only prevents the two halves separating in X.

Support capture has a different and independent role.  A bay-owned mushroom
lug, fused into each support capital, enters an integral keyhole at Y=16 mm.
The already joined bay slides 32 mm toward the wall while held 2 mm above its
bearing pose, then settles 2 mm by gravity into a higher terminal pocket.  In
the settled pose a solid shoulder blocks reverse slide without friction.  The
exact reverse is lift, slide away from the wall, then lift clear.  Neighboring
bays use physically separate lugs on opposite support half-lands; there is no
shared release key.

The full support, wall bores, cable receiver, blanks, and comb/hook are outside
this geometry file.  Their required inventory and the S0 fused-receiver
provenance are recorded, but no absent mesh is fabricated.  All claims remain
zero-rated until exact printed articles, supports, wall construction, and the
complete assembly pass the physical gates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable, Mapping, Sequence
import warnings

import numpy as np
from shapely.geometry import GeometryCollection, Polygon
from shapely import affinity
import trimesh


class R11GeometryError(ValueError):
    """Raised when R11 geometry would otherwise require an assumption."""


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PHYSICAL_QUALIFICATION_COMPLETE = False
WALL_INSTALLATION_AUTHORIZED = False
PRINTED_MATERIAL = "SUNLU standard black PETG, ASIN B0D1KC72YP"
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0

A1_MINI_BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
BRIM_WIDTH_MM = 5.0
BRIM_OBJECT_GAP_MM = 0.1
RESERVE_PER_BED_EDGE_MM = 2.0
XY_PROCESS_ALLOWANCE_MM = 2.0 * (
    BRIM_WIDTH_MM + BRIM_OBJECT_GAP_MM + RESERVE_PER_BED_EDGE_MM
)
GEOMETRY_EPSILON_MM = 1.0e-7
COLLISION_TOLERANCE_MM3 = 1.0e-5

FIELD_SUPPORT_COUNT = 7
FIELD_BAY_COUNT = 6
FIELD_BAY_KINDS = (
    "terminal",
    "regular",
    "regular",
    "regular",
    "regular",
    "terminal",
)
FIELD_TERMINAL_HALF_DECK_COUNT = 4
FIELD_REGULAR_HALF_DECK_COUNT = 8
FIELD_HALF_DECK_COUNT = 12
FIELD_KEYSTONE_COUNT = 6
FIELD_CABLE_MODULE_COUNT = 3
FIELD_PRINTED_ARTICLE_COUNT = 28
FIELD_SAFE_UNBATCHED_PRINT_START_COUNT = 28
FIELD_TARGET_BATCHED_PRINT_START_COUNT = 21
FIELD_VERIFIED_PRODUCTION_PRINT_START_COUNT: int | None = None

SHELF_DEPTH_MM = 152.4
SHELF_TOTAL_HEIGHT_MM = 32.0
SUPPORT_RUN_WIDTH_MM = 31.75
TOP_SKIN_MM = 4.0
RIB_WIDTH_MM = 20.0
RIB_STATIONS_Y_MM = (16.0, 76.2, 136.4)

MIDPOINT_SEAM_MM = 0.35
SUPPORT_LINE_SEAM_MM = 0.35
INTEGRATED_OVERLAP_MM = 55.0
JOINT_CLEARANCE_PER_FACE_MM = 0.4
LAP_CENTER_GAP_MM = 2.0 * JOINT_CLEARANCE_PER_FACE_MM
LAP_LANE_WIDTH_MM = (RIB_WIDTH_MM - LAP_CENTER_GAP_MM) / 2.0

REGULAR_CLEAR_SPAN_MM = 253.65
REGULAR_CORE_LENGTH_MM = (REGULAR_CLEAR_SPAN_MM - MIDPOINT_SEAM_MM) / 2.0
REGULAR_MODULE_LENGTH_MM = 154.325
TERMINAL_CLEAR_SPAN_MM = 269.35
TERMINAL_CORE_LENGTH_MM = (TERMINAL_CLEAR_SPAN_MM - MIDPOINT_SEAM_MM) / 2.0
TERMINAL_MODULE_LENGTH_MM = 162.175
TERMINAL_EXTENSION_MM = 7.85
TONGUE_PROJECTION_MM = 27.675
INCOMING_ENGAGEMENT_MM = 27.325
AXIAL_BLIND_CLEARANCE_MM = 0.4
TONGUE_ROOT_OVERLAP_MM = 0.2

SUPPORT_BEARING_LENGTH_MM = 15.70
CAPTURE_BLOCK_Y_START_MM = 8.0
CAPTURE_BLOCK_Y_END_MM = 56.0
CAPTURE_ENTRY_Y_MM = 16.0
CAPTURE_FINAL_Y_MM = 48.0
CAPTURE_WALLWARD_SLIDE_MM = CAPTURE_FINAL_Y_MM - CAPTURE_ENTRY_Y_MM
CAPTURE_SLIDE_ELEVATION_MM = 2.0
CAPTURE_INITIAL_LIFT_MM = 14.0
CAPTURE_LUG_CENTER_X_MM = SUPPORT_BEARING_LENGTH_MM / 2.0
CAPTURE_LUG_NECK_XY_MM = 4.0
CAPTURE_LUG_NECK_HEIGHT_MM = 4.0
CAPTURE_LUG_HEAD_XY_MM = 8.0
CAPTURE_LUG_HEAD_HEIGHT_MM = 6.0
CAPTURE_LUG_TOTAL_HEIGHT_MM = 10.0
CAPTURE_REVERSE_SHOULDER_Z_MM = 8.4

KEYSTONE_CENTER_Y_MM = 110.0
KEYSTONE_BODY_HEIGHT_MM = 12.0
KEYSTONE_CAP_HEIGHT_MM = 2.0
KEYSTONE_INSTALLED_BOTTOM_Z_MM = 20.0
KEYSTONE_SLOT_CLEARANCE_PER_FACE_MM = 0.4
KEYSTONE_CAP_OVERHANG_MM = 1.0

NET_RIB_I_TARGET_MM4 = 8263.957
NET_RIB_Z_TARGET_MM3 = 949.016
AESTHETIC_CONTRACT_ID = "r11_palatine_reciprocal_keystone_v1"

S0_CABLE_RECEIVER_PROVENANCE: Mapping[str, object] = {
    "support_index": 0,
    "receiver_is_fused_into_support": True,
    "receiver_mesh_authored_in_this_module": False,
    "separate_cable_modules_required": 3,
    "separate_module_roles": ("flush_blank_0", "flush_blank_1", "comb_hook"),
    "capacity_credit": False,
}

OUTER_TERMINAL_BAY_PART_ORDER = (
    "r11_bay0_left_terminal_integrated_half_deck",
    "r11_bay0_right_terminal_integrated_half_deck",
    "r11_bay0_positive_keystone",
)


@dataclass(frozen=True)
class PrintEnvelope:
    raw_part_mm: tuple[float, float, float]
    required_build_volume_mm: tuple[float, float, float]
    available_build_volume_mm: tuple[float, float, float]
    xy_process_allowance_mm: float
    minimum_xy_spare_mm: float
    fits: bool


@dataclass(frozen=True)
class NetRibSectionEvidence:
    gross_width_mm: float
    net_lane_width_mm: float
    height_mm: float
    gross_second_moment_mm4: float
    gross_section_modulus_mm3: float
    net_second_moment_mm4: float
    net_section_modulus_mm3: float
    minimum_required_second_moment_mm4: float
    minimum_required_section_modulus_mm3: float
    geometry_targets_pass: bool
    material_capacity_claimed: bool


@dataclass(frozen=True)
class LayerConnectivityReport:
    layer_height_mm: float
    sampled_layer_count: int
    first_layer_contact_area_mm2: float
    island_layer_indices: tuple[int, ...]
    support_required: bool


@dataclass(frozen=True)
class AssemblyPathEvidence:
    target_maximum_intersection_mm3: float
    midpoint_join_maximum_intersection_mm3: float
    keystone_insert_maximum_intersection_mm3: float
    capture_drop_maximum_intersection_mm3: float
    capture_wallward_slide_maximum_intersection_mm3: float
    capture_settle_maximum_intersection_mm3: float
    exact_reverse_maximum_intersection_mm3: float
    blocked_reverse_slide_intersection_mm3: float
    all_authored_service_paths_collision_free: bool
    positive_no_friction_reverse_stop: bool
    midpoint_join_precedes_capture: bool
    keystone_role: str
    support_capture_role: str


@dataclass(frozen=True)
class FieldInventoryEvidence:
    supports: int
    terminal_half_decks: int
    regular_half_decks: int
    total_half_decks: int
    palatine_keystones: int
    cable_modules: int
    total_candidate_articles: int
    maximum_simultaneously_installed_articles: int
    interchangeable_cable_spare_articles: int
    safe_unbatched_print_starts: int
    target_batched_print_starts: int
    target_batched_plate_nesting_verified: bool
    verified_production_print_starts: int | None
    first_and_last_bays_use_two_terminal_halves_each: bool
    no_loose_logs: bool
    no_log_retainers: bool
    no_support_keys: bool


@dataclass(frozen=True)
class AdjacentCaptureEvidence:
    support_run_width_mm: float
    bay_owned_lug_centers_from_support_line_mm: tuple[float, float]
    lug_head_width_mm: float
    clear_gap_between_lug_heads_mm: float
    each_lug_inside_its_support_half_land: bool
    current_bay_service_motion_changes_x: bool
    shared_release_component_count: int
    adjacent_bay_release_independent: bool


@dataclass(frozen=True)
class IntegratedBayEvidence:
    kind: str
    clear_span_mm: float
    core_length_mm: float
    module_length_mm: float
    physical_overlap_mm: float
    midpoint_seam_mm: float
    rib_stations_y_mm: tuple[float, ...]
    joint_clearance_per_face_mm: float
    minimum_support_bearing_length_mm: float
    half_deck_count: int
    keystone_count: int
    target_body_count: int
    target_watertight: bool
    target_winding_consistent: bool
    print_envelopes: Mapping[str, PrintEnvelope]
    rib_section: NetRibSectionEvidence
    assembly: AssemblyPathEvidence
    aesthetic_contract_id: str
    qualification_only: bool
    rated_load_kg: float
    wall_installation_authorized: bool
    analytic_blockers: tuple[str, ...]
    physical_blockers: tuple[str, ...]


def _require_exact(value: float, expected: float, name: str) -> None:
    if not math.isclose(float(value), float(expected), rel_tol=0.0, abs_tol=1.0e-9):
        raise R11GeometryError(f"{name} drifted: {value!r} != {expected!r}")


_require_exact(REGULAR_CORE_LENGTH_MM, 126.65, "regular core length")
_require_exact(TERMINAL_CORE_LENGTH_MM, 134.5, "terminal core length")
_require_exact(TONGUE_PROJECTION_MM, 27.675, "tongue projection")
_require_exact(INCOMING_ENGAGEMENT_MM, 27.325, "incoming engagement")
_require_exact(
    REGULAR_MODULE_LENGTH_MM - REGULAR_CORE_LENGTH_MM,
    TONGUE_PROJECTION_MM,
    "derived regular tongue projection",
)
_require_exact(
    TERMINAL_MODULE_LENGTH_MM - TERMINAL_CORE_LENGTH_MM,
    TONGUE_PROJECTION_MM,
    "derived terminal tongue projection",
)
_require_exact(2.0 * REGULAR_MODULE_LENGTH_MM - REGULAR_CLEAR_SPAN_MM, 55.0, "regular overlap")
_require_exact(2.0 * TERMINAL_MODULE_LENGTH_MM - TERMINAL_CLEAR_SPAN_MM, 55.0, "terminal overlap")
_require_exact(XY_PROCESS_ALLOWANCE_MM, 14.2, "XY process allowance")
_require_exact(LAP_LANE_WIDTH_MM, 9.6, "net lap lane width")


def _positive(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise R11GeometryError(f"{name} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise R11GeometryError(f"{name} must be a positive finite number")
    return result


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise R11GeometryError("R11 geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    if not np.isfinite(mesh.vertices).all():
        raise R11GeometryError("R11 geometry contains non-finite coordinates")
    return mesh


def _copy(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    return _clean(mesh.copy())


def _box(
    extents: tuple[float, float, float],
    origin: tuple[float, float, float],
) -> trimesh.Trimesh:
    size = np.asarray([_positive(item, "box dimension") for item in extents])
    start = np.asarray(origin, dtype=float)
    if start.shape != (3,) or not np.isfinite(start).all():
        raise R11GeometryError("box origin must contain three finite coordinates")
    mesh = trimesh.creation.box(extents=size)
    mesh.apply_translation(start + size / 2.0)
    return _clean(mesh)


def _union(meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise R11GeometryError("at least one mesh is required for union")
    result = trimesh.boolean.union(
        [_copy(item) for item in meshes], engine="manifold", check_volume=True
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
        [_copy(body), *[_copy(item) for item in cutters]],
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
        raise R11GeometryError(f"{name} must be one watertight positive body")
    return result


def _kind_dimensions(kind: str) -> tuple[float, float, float]:
    if kind == "regular":
        return REGULAR_CLEAR_SPAN_MM, REGULAR_CORE_LENGTH_MM, REGULAR_MODULE_LENGTH_MM
    if kind == "terminal":
        return TERMINAL_CLEAR_SPAN_MM, TERMINAL_CORE_LENGTH_MM, TERMINAL_MODULE_LENGTH_MM
    raise R11GeometryError("half-deck kind must be 'regular' or 'terminal'")


def _lap_lane_bounds(hand: str, station: float) -> tuple[float, float]:
    if hand == "left":
        return station - RIB_WIDTH_MM / 2.0, station - JOINT_CLEARANCE_PER_FACE_MM
    if hand == "right":
        return station + JOINT_CLEARANCE_PER_FACE_MM, station + RIB_WIDTH_MM / 2.0
    raise R11GeometryError("half-deck hand must be 'left' or 'right'")


def _receiver_lane_bounds(hand: str, station: float) -> tuple[float, float]:
    if hand == "left":
        return station, station + RIB_WIDTH_MM / 2.0 + JOINT_CLEARANCE_PER_FACE_MM
    if hand == "right":
        return station - RIB_WIDTH_MM / 2.0 - JOINT_CLEARANCE_PER_FACE_MM, station
    raise R11GeometryError("half-deck hand must be 'left' or 'right'")


def _keystone_profile(center_x: float, center_y: float) -> Polygon:
    local = Polygon(
        (
            (-6.0, -8.0),
            (6.0, -8.0),
            (6.0, -4.0),
            (8.0, -4.0),
            (8.0, 2.0),
            (10.0, 2.0),
            (10.0, 8.0),
            (-10.0, 8.0),
            (-10.0, 2.0),
            (-8.0, 2.0),
            (-8.0, -4.0),
            (-6.0, -4.0),
        )
    )
    profile = affinity.translate(local, xoff=float(center_x), yoff=float(center_y))
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise R11GeometryError("Palatine keystone profile is invalid")
    return profile


def _extrude_xy(profile: Polygon, height: float, z_start: float) -> trimesh.Trimesh:
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise R11GeometryError("XY extrusion profile is invalid")
    result = trimesh.creation.extrude_polygon(
        profile, height=_positive(height, "extrusion height"), engine="earcut"
    )
    result.apply_translation((0.0, 0.0, float(z_start)))
    return _clean(result)


def _capture_cutters() -> tuple[trimesh.Trimesh, ...]:
    center_x = CAPTURE_LUG_CENTER_X_MM
    head_clear = CAPTURE_LUG_HEAD_XY_MM + 2.0 * JOINT_CLEARANCE_PER_FACE_MM
    neck_clear = CAPTURE_LUG_NECK_XY_MM + 2.0 * JOINT_CLEARANCE_PER_FACE_MM
    track_start = CAPTURE_ENTRY_Y_MM - head_clear / 2.0
    track_end = CAPTURE_FINAL_Y_MM + head_clear / 2.0
    return (
        # Through-entry for the initial vertical drop at +32 mm Y.
        _box(
            (head_clear, head_clear, 26.4),
            (
                center_x - head_clear / 2.0,
                CAPTURE_ENTRY_Y_MM - head_clear / 2.0,
                -16.0,
            ),
        ),
        # Narrow underside lane for the lug neck at both service elevations.
        _box(
            (neck_clear, track_end - track_start, 6.8),
            (center_x - neck_clear / 2.0, track_start, -2.4),
        ),
        # Low head gallery used while the bay is held 2 mm above bearing.
        _box(
            (head_clear, track_end - track_start, 6.8),
            (center_x - head_clear / 2.0, track_start, 1.6),
        ),
        # Higher terminal pocket. Gravity raises the fixed head in shelf-local
        # coordinates, placing its top behind the gallery's solid 8.4 mm roof.
        _box(
            (head_clear, head_clear, 6.8),
            (
                center_x - head_clear / 2.0,
                CAPTURE_FINAL_Y_MM - head_clear / 2.0,
                3.6,
            ),
        ),
    )


def _build_half_deck(*, kind: str, hand: str) -> trimesh.Trimesh:
    _, core, module = _kind_dimensions(kind)
    if hand not in ("left", "right"):
        raise R11GeometryError("half-deck hand must be 'left' or 'right'")

    parts: list[trimesh.Trimesh] = [
        _box(
            (core, SHELF_DEPTH_MM, TOP_SKIN_MM),
            (0.0, 0.0, SHELF_TOTAL_HEIGHT_MM - TOP_SKIN_MM),
        ),
        _box(
            (
                SUPPORT_BEARING_LENGTH_MM,
                CAPTURE_BLOCK_Y_END_MM - CAPTURE_BLOCK_Y_START_MM,
                SHELF_TOTAL_HEIGHT_MM,
            ),
            (0.0, CAPTURE_BLOCK_Y_START_MM, 0.0),
        ),
        # Local lock boss between the center and front load ribs.  Its pocket
        # is through-open, so the broad saved orientation creates no roof.
        _box((14.0, 20.0, 12.0), (core - 14.0, 100.0, 20.0)),
    ]
    for station in RIB_STATIONS_Y_MM:
        parts.append(
            _box(
                (core, RIB_WIDTH_MM, SHELF_TOTAL_HEIGHT_MM),
                (0.0, station - RIB_WIDTH_MM / 2.0, 0.0),
            )
        )
        lane_min, lane_max = _lap_lane_bounds(hand, station)
        parts.append(
            _box(
                (
                    module - core + TONGUE_ROOT_OVERLAP_MM,
                    lane_max - lane_min,
                    SHELF_TOTAL_HEIGHT_MM,
                ),
                (core - TONGUE_ROOT_OVERLAP_MM, lane_min, 0.0),
            )
        )

    body = _union(parts)
    socket_start = core - INCOMING_ENGAGEMENT_MM - AXIAL_BLIND_CLEARANCE_MM
    socket_length = core - socket_start + 0.2
    cutters: list[trimesh.Trimesh] = list(_capture_cutters())
    for station in RIB_STATIONS_Y_MM:
        lane_min, lane_max = _receiver_lane_bounds(hand, station)
        cutters.append(
            _box(
                (socket_length, lane_max - lane_min, SHELF_TOTAL_HEIGHT_MM + 0.8),
                (socket_start, lane_min, -0.4),
            )
        )

    # Each half owns one side of the symmetric pocket.  Mirroring the right
    # half in assembly puts both halves around the same bay-midpoint profile.
    seam_center_local = core + MIDPOINT_SEAM_MM / 2.0
    slot = _keystone_profile(seam_center_local, KEYSTONE_CENTER_Y_MM).buffer(
        KEYSTONE_SLOT_CLEARANCE_PER_FACE_MM, join_style="mitre"
    )
    cutters.append(_extrude_xy(slot, 12.8, 19.6))
    result = _one_body(
        _difference(body, cutters), f"R11 {kind} {hand} integrated half-deck"
    )
    expected = np.asarray((module, SHELF_DEPTH_MM, SHELF_TOTAL_HEIGHT_MM))
    # Manifold's float vertex round-trip is bounded to a few micrometres.
    if not np.allclose(result.extents, expected, rtol=0.0, atol=1.0e-5):
        raise R11GeometryError(
            f"{kind} {hand} half-deck envelope drifted: {result.extents}"
        )
    return result


def build_regular_half_deck(*, hand: str) -> trimesh.Trimesh:
    """Build one 154.325 mm interior-bay integrated half-deck."""

    return _build_half_deck(kind="regular", hand=hand)


def build_terminal_half_deck(*, hand: str) -> trimesh.Trimesh:
    """Build one 162.175 mm end-bay half; both end-bay halves use this size."""

    return _build_half_deck(kind="terminal", hand=hand)


def build_palatine_keystone() -> trimesh.Trimesh:
    """Build one gravity-seated, no-load-credit bay-local lock."""

    body_profile = _keystone_profile(0.0, 0.0)
    cap_profile = body_profile.buffer(KEYSTONE_CAP_OVERHANG_MM, join_style="mitre")
    body = _extrude_xy(body_profile, KEYSTONE_BODY_HEIGHT_MM, 0.0)
    cap = _extrude_xy(
        cap_profile,
        KEYSTONE_CAP_HEIGHT_MM,
        KEYSTONE_BODY_HEIGHT_MM,
    )
    return _one_body(_union((body, cap)), "R11 Palatine keystone")


def build_capture_lug_interface_fixture(
    *, center_x_mm: float, center_y_mm: float = CAPTURE_FINAL_Y_MM
) -> trimesh.Trimesh:
    """Build only the fused-support lug interface, never a field support mesh."""

    center_x = float(center_x_mm)
    center_y = float(center_y_mm)
    if not math.isfinite(center_x) or not math.isfinite(center_y):
        raise R11GeometryError("capture-lug center must be finite")
    neck = _box(
        (CAPTURE_LUG_NECK_XY_MM, CAPTURE_LUG_NECK_XY_MM, 4.1),
        (
            center_x - CAPTURE_LUG_NECK_XY_MM / 2.0,
            center_y - CAPTURE_LUG_NECK_XY_MM / 2.0,
            0.0,
        ),
    )
    head = _box(
        (
            CAPTURE_LUG_HEAD_XY_MM,
            CAPTURE_LUG_HEAD_XY_MM,
            CAPTURE_LUG_HEAD_HEIGHT_MM + 0.1,
        ),
        (
            center_x - CAPTURE_LUG_HEAD_XY_MM / 2.0,
            center_y - CAPTURE_LUG_HEAD_XY_MM / 2.0,
            CAPTURE_LUG_NECK_HEIGHT_MM - 0.1,
        ),
    )
    return _one_body(_union((neck, head)), "R11 capture-lug interface fixture")


def orient_half_deck_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Place the complete top datum on the plate; baseline is one per plate."""

    result = _copy(mesh)
    maximum = float(result.bounds[1, 2])
    result.vertices[:, 2] = maximum - result.vertices[:, 2]
    result.fix_normals(multibody=True)
    return _normalize(result)


def orient_keystone_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Put the broad decorative cap on the plate and grow the body upward."""

    result = _copy(mesh)
    maximum = float(result.bounds[1, 2])
    result.vertices[:, 2] = maximum - result.vertices[:, 2]
    result.fix_normals(multibody=True)
    return _normalize(result)


def _mirror_right_to_span(mesh: trimesh.Trimesh, span: float) -> trimesh.Trimesh:
    result = _copy(mesh)
    result.vertices[:, 0] = float(span) - result.vertices[:, 0]
    result.fix_normals(multibody=True)
    return _clean(result)


def _installed_bay_parts(kind: str) -> dict[str, trimesh.Trimesh]:
    span, _, _ = _kind_dimensions(kind)
    left = _build_half_deck(kind=kind, hand="left")
    right = _mirror_right_to_span(
        _build_half_deck(kind=kind, hand="right"), span
    )
    wedge = build_palatine_keystone()
    wedge.apply_translation(
        (
            span / 2.0,
            KEYSTONE_CENTER_Y_MM,
            KEYSTONE_INSTALLED_BOTTOM_Z_MM,
        )
    )
    return {
        f"r11_{kind}_bay_left_integrated_half_deck": _clean(left),
        f"r11_{kind}_bay_right_integrated_half_deck": _clean(right),
        f"r11_{kind}_bay_palatine_keystone": _clean(wedge),
    }


def build_installed_regular_bay_parts() -> dict[str, trimesh.Trimesh]:
    return _installed_bay_parts("regular")


def build_installed_terminal_bay_parts() -> dict[str, trimesh.Trimesh]:
    return _installed_bay_parts("terminal")


def _installed_capture_lugs(kind: str) -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    span, _, _ = _kind_dimensions(kind)
    return (
        build_capture_lug_interface_fixture(center_x_mm=CAPTURE_LUG_CENTER_X_MM),
        build_capture_lug_interface_fixture(
            center_x_mm=span - CAPTURE_LUG_CENTER_X_MM
        ),
    )


def _saved_bay_parts(kind: str) -> dict[str, trimesh.Trimesh]:
    left = orient_half_deck_for_print(_build_half_deck(kind=kind, hand="left"))
    right = orient_half_deck_for_print(_build_half_deck(kind=kind, hand="right"))
    wedge = orient_keystone_for_print(build_palatine_keystone())
    return {
        f"r11_{kind}_bay_left_integrated_half_deck": left,
        f"r11_{kind}_bay_right_integrated_half_deck": right,
        f"r11_{kind}_bay_palatine_keystone": wedge,
    }


def build_saved_regular_bay_parts() -> dict[str, trimesh.Trimesh]:
    return _saved_bay_parts("regular")


def build_saved_terminal_bay_parts() -> dict[str, trimesh.Trimesh]:
    return _saved_bay_parts("terminal")


def build_saved_outer_terminal_bay_parts() -> dict[str, trimesh.Trimesh]:
    """Return the geometry-authored three-part subset of an outer bay.

    Full supports and cable modules intentionally remain absent.  A bundle
    generator must append them from an explicit provider or fail closed.
    """

    source = build_saved_terminal_bay_parts()
    return {
        OUTER_TERMINAL_BAY_PART_ORDER[0]: source[
            "r11_terminal_bay_left_integrated_half_deck"
        ],
        OUTER_TERMINAL_BAY_PART_ORDER[1]: source[
            "r11_terminal_bay_right_integrated_half_deck"
        ],
        OUTER_TERMINAL_BAY_PART_ORDER[2]: source[
            "r11_terminal_bay_palatine_keystone"
        ],
    }


def print_envelope(mesh: trimesh.Trimesh) -> PrintEnvelope:
    references = (
        REGULAR_MODULE_LENGTH_MM,
        TERMINAL_MODULE_LENGTH_MM,
        SHELF_DEPTH_MM,
        SHELF_TOTAL_HEIGHT_MM,
        22.0,
        18.0,
        14.0,
    )

    def canonical(value: float) -> float:
        for reference in references:
            if math.isclose(value, reference, rel_tol=0.0, abs_tol=1.0e-4):
                return reference
        return round(value, 6)

    raw = tuple(canonical(float(item)) for item in mesh.extents)
    required = (
        round(raw[0] + XY_PROCESS_ALLOWANCE_MM, 6),
        round(raw[1] + XY_PROCESS_ALLOWANCE_MM, 6),
        raw[2],
    )
    fits = (
        required[2] <= A1_MINI_BUILD_VOLUME_MM[2] + GEOMETRY_EPSILON_MM
        and (
            (
                required[0] <= A1_MINI_BUILD_VOLUME_MM[0] + GEOMETRY_EPSILON_MM
                and required[1]
                <= A1_MINI_BUILD_VOLUME_MM[1] + GEOMETRY_EPSILON_MM
            )
            or (
                required[1] <= A1_MINI_BUILD_VOLUME_MM[0] + GEOMETRY_EPSILON_MM
                and required[0]
                <= A1_MINI_BUILD_VOLUME_MM[1] + GEOMETRY_EPSILON_MM
            )
        )
    )
    spare = min(
        A1_MINI_BUILD_VOLUME_MM[0] - required[0],
        A1_MINI_BUILD_VOLUME_MM[1] - required[1],
    )
    return PrintEnvelope(
        raw_part_mm=raw,
        required_build_volume_mm=required,
        available_build_volume_mm=A1_MINI_BUILD_VOLUME_MM,
        xy_process_allowance_mm=XY_PROCESS_ALLOWANCE_MM,
        minimum_xy_spare_mm=round(float(spare), 6),
        fits=bool(fits),
    )


def rib_section_evidence() -> NetRibSectionEvidence:
    height = SHELF_TOTAL_HEIGHT_MM
    gross_i = RIB_WIDTH_MM * height**3 / 12.0
    gross_z = gross_i / (height / 2.0)
    net_i = LAP_LANE_WIDTH_MM * height**3 / 12.0
    net_z = net_i / (height / 2.0)
    return NetRibSectionEvidence(
        gross_width_mm=RIB_WIDTH_MM,
        net_lane_width_mm=LAP_LANE_WIDTH_MM,
        height_mm=height,
        gross_second_moment_mm4=gross_i,
        gross_section_modulus_mm3=gross_z,
        net_second_moment_mm4=net_i,
        net_section_modulus_mm3=net_z,
        minimum_required_second_moment_mm4=NET_RIB_I_TARGET_MM4,
        minimum_required_section_modulus_mm3=NET_RIB_Z_TARGET_MM3,
        geometry_targets_pass=(
            net_i >= NET_RIB_I_TARGET_MM4 and net_z >= NET_RIB_Z_TARGET_MM3
        ),
        material_capacity_claimed=False,
    )


def _intersection_volume(first: trimesh.Trimesh, second: trimesh.Trimesh) -> float:
    if not (
        np.all(first.bounds[1] > second.bounds[0] + GEOMETRY_EPSILON_MM)
        and np.all(second.bounds[1] > first.bounds[0] + GEOMETRY_EPSILON_MM)
    ):
        return 0.0
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        overlap = trimesh.boolean.intersection(
            [_copy(first), _copy(second)], engine="manifold", check_volume=False
        )
    if overlap is None:
        return 0.0
    if isinstance(overlap, list):
        value = sum(abs(float(item.volume)) for item in overlap if not item.is_empty)
    elif overlap.is_empty:
        value = 0.0
    else:
        value = abs(float(overlap.volume))
    return 0.0 if value <= 1.0e-8 else float(value)


def _pairwise_maximum(meshes: Iterable[trimesh.Trimesh]) -> float:
    items = tuple(meshes)
    maximum = 0.0
    for index, first in enumerate(items):
        for second in items[index + 1 :]:
            maximum = max(maximum, _intersection_volume(first, second))
    return maximum


def _moving_fixed_maximum(
    moving: Iterable[trimesh.Trimesh], fixed: Iterable[trimesh.Trimesh]
) -> float:
    return max(
        (
            _intersection_volume(first, second)
            for first in moving
            for second in fixed
        ),
        default=0.0,
    )


def _translated_group(
    meshes: Iterable[trimesh.Trimesh], translation: tuple[float, float, float]
) -> tuple[trimesh.Trimesh, ...]:
    result: list[trimesh.Trimesh] = []
    for source in meshes:
        item = _copy(source)
        item.apply_translation(translation)
        result.append(_clean(item))
    return tuple(result)


def _path_maximum(
    moving: Sequence[trimesh.Trimesh],
    fixed: Sequence[trimesh.Trimesh],
    translations: Iterable[tuple[float, float, float]],
) -> float:
    maximum = 0.0
    for translation in translations:
        maximum = max(
            maximum,
            _moving_fixed_maximum(_translated_group(moving, translation), fixed),
        )
    return maximum


def build_assembly_path_evidence(kind: str = "regular") -> AssemblyPathEvidence:
    parts = _installed_bay_parts(kind)
    left = parts[f"r11_{kind}_bay_left_integrated_half_deck"]
    right = parts[f"r11_{kind}_bay_right_integrated_half_deck"]
    wedge = parts[f"r11_{kind}_bay_palatine_keystone"]
    lugs = _installed_capture_lugs(kind)

    target = _pairwise_maximum((left, right, wedge, *lugs))
    join = max(
        _intersection_volume(
            left,
            _translated_group((right,), (float(offset), 0.0, 0.0))[0],
        )
        for offset in np.linspace(60.0, 0.0, 25)
    )
    wedge_insert = max(
        _moving_fixed_maximum(
            _translated_group((wedge,), (0.0, 0.0, float(rise))),
            (left, right),
        )
        for rise in np.linspace(16.0, 0.0, 17)
    )

    joined = (left, right, wedge)
    drop_translations = (
        (0.0, CAPTURE_WALLWARD_SLIDE_MM, float(z))
        for z in np.linspace(CAPTURE_INITIAL_LIFT_MM, CAPTURE_SLIDE_ELEVATION_MM, 13)
    )
    drop_max = _path_maximum(joined, lugs, drop_translations)
    slide_translations = (
        (0.0, float(y), CAPTURE_SLIDE_ELEVATION_MM)
        for y in np.linspace(CAPTURE_WALLWARD_SLIDE_MM, 0.0, 17)
    )
    slide_max = _path_maximum(joined, lugs, slide_translations)
    settle_translations = (
        (0.0, 0.0, float(z))
        for z in np.linspace(CAPTURE_SLIDE_ELEVATION_MM, 0.0, 9)
    )
    settle_max = _path_maximum(joined, lugs, settle_translations)
    reverse_max = max(drop_max, slide_max, settle_max)

    attempted_reverse = _translated_group(joined, (0.0, 8.0, 0.0))
    reverse_stop = _moving_fixed_maximum(attempted_reverse, lugs)
    service_max = max(target, join, wedge_insert, drop_max, slide_max, settle_max)
    return AssemblyPathEvidence(
        target_maximum_intersection_mm3=target,
        midpoint_join_maximum_intersection_mm3=join,
        keystone_insert_maximum_intersection_mm3=wedge_insert,
        capture_drop_maximum_intersection_mm3=drop_max,
        capture_wallward_slide_maximum_intersection_mm3=slide_max,
        capture_settle_maximum_intersection_mm3=settle_max,
        exact_reverse_maximum_intersection_mm3=reverse_max,
        blocked_reverse_slide_intersection_mm3=reverse_stop,
        all_authored_service_paths_collision_free=(
            service_max <= COLLISION_TOLERANCE_MM3
        ),
        positive_no_friction_reverse_stop=(
            reverse_stop > COLLISION_TOLERANCE_MM3
        ),
        midpoint_join_precedes_capture=True,
        keystone_role=(
            "bay-local half-to-half separation lock only; no gravity, wall, "
            "material-capacity, friction, snap, or glue credit"
        ),
        support_capture_role=(
            "two remote bay-owned fused-support lugs provide anti-lift capture "
            "and gravity-settled positive reverse-slide shoulders"
        ),
    )


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


def _filled_components(region: object) -> tuple[Polygon, ...]:
    if getattr(region, "is_empty", True):
        return ()
    if isinstance(region, Polygon):
        return (region,)
    components: list[Polygon] = []
    for item in getattr(region, "geoms", ()):  # GeometryCollection/MultiPolygon
        if isinstance(item, Polygon):
            components.append(item)
        elif hasattr(item, "geoms"):
            components.extend(_filled_components(item))
    return tuple(components)


def saved_layer_connectivity_report(
    mesh: trimesh.Trimesh, *, layer_height_mm: float = 0.2
) -> LayerConnectivityReport:
    """Sample every saved layer and reject a component born in mid-air."""

    layer = _positive(layer_height_mm, "layer height")
    height = float(mesh.extents[2])
    count = int(math.ceil(height / layer - 1.0e-9))
    minimum_z = float(mesh.bounds[0, 2])
    previous = None
    islands: list[int] = []
    first_area = 0.0
    for index in range(count):
        bottom = index * layer
        deposited = min(layer, height - bottom)
        region = _section_material_region(
            mesh, minimum_z + bottom + deposited / 2.0
        )
        components = _filled_components(region)
        if index == 0:
            first_area = float(region.area)
        if not components:
            islands.append(index)
        elif previous is not None and any(
            component.intersection(previous).area <= 1.0e-8
            for component in components
        ):
            islands.append(index)
        previous = region
    return LayerConnectivityReport(
        layer_height_mm=layer,
        sampled_layer_count=count,
        first_layer_contact_area_mm2=first_area,
        island_layer_indices=tuple(islands),
        support_required=bool(islands),
    )


def field_inventory_evidence() -> FieldInventoryEvidence:
    terminal = 2 * sum(kind == "terminal" for kind in FIELD_BAY_KINDS)
    regular = 2 * sum(kind == "regular" for kind in FIELD_BAY_KINDS)
    total = (
        FIELD_SUPPORT_COUNT
        + terminal
        + regular
        + FIELD_KEYSTONE_COUNT
        + FIELD_CABLE_MODULE_COUNT
    )
    if (
        terminal != FIELD_TERMINAL_HALF_DECK_COUNT
        or regular != FIELD_REGULAR_HALF_DECK_COUNT
        or total != FIELD_PRINTED_ARTICLE_COUNT
    ):
        raise R11GeometryError("field inventory no longer closes exactly")
    return FieldInventoryEvidence(
        supports=FIELD_SUPPORT_COUNT,
        terminal_half_decks=terminal,
        regular_half_decks=regular,
        total_half_decks=terminal + regular,
        palatine_keystones=FIELD_KEYSTONE_COUNT,
        cable_modules=FIELD_CABLE_MODULE_COUNT,
        total_candidate_articles=total,
        maximum_simultaneously_installed_articles=total - 1,
        interchangeable_cable_spare_articles=1,
        safe_unbatched_print_starts=FIELD_SAFE_UNBATCHED_PRINT_START_COUNT,
        target_batched_print_starts=FIELD_TARGET_BATCHED_PRINT_START_COUNT,
        target_batched_plate_nesting_verified=False,
        verified_production_print_starts=(
            FIELD_VERIFIED_PRODUCTION_PRINT_START_COUNT
        ),
        first_and_last_bays_use_two_terminal_halves_each=(
            FIELD_BAY_KINDS[0] == FIELD_BAY_KINDS[-1] == "terminal"
            and terminal == 4
        ),
        no_loose_logs=True,
        no_log_retainers=True,
        no_support_keys=True,
    )


def adjacent_capture_evidence() -> AdjacentCaptureEvidence:
    """Prove the two lugs at one interior support are physically independent."""

    centers = (-CAPTURE_LUG_CENTER_X_MM, CAPTURE_LUG_CENTER_X_MM)
    left_head_max = centers[0] + CAPTURE_LUG_HEAD_XY_MM / 2.0
    right_head_min = centers[1] - CAPTURE_LUG_HEAD_XY_MM / 2.0
    gap = right_head_min - left_head_max
    support_half = SUPPORT_RUN_WIDTH_MM / 2.0
    inside = all(
        abs(center) + CAPTURE_LUG_HEAD_XY_MM / 2.0
        <= support_half + GEOMETRY_EPSILON_MM
        for center in centers
    )
    independent = gap > 0.0 and inside
    return AdjacentCaptureEvidence(
        support_run_width_mm=SUPPORT_RUN_WIDTH_MM,
        bay_owned_lug_centers_from_support_line_mm=centers,
        lug_head_width_mm=CAPTURE_LUG_HEAD_XY_MM,
        clear_gap_between_lug_heads_mm=gap,
        each_lug_inside_its_support_half_land=inside,
        current_bay_service_motion_changes_x=False,
        shared_release_component_count=0,
        adjacent_bay_release_independent=independent,
    )


def _bay_evidence(kind: str) -> IntegratedBayEvidence:
    span, core, module = _kind_dimensions(kind)
    saved = _saved_bay_parts(kind)
    envelopes = {name: print_envelope(mesh) for name, mesh in saved.items()}
    installed = _installed_bay_parts(kind)
    return IntegratedBayEvidence(
        kind=kind,
        clear_span_mm=span,
        core_length_mm=core,
        module_length_mm=module,
        physical_overlap_mm=INTEGRATED_OVERLAP_MM,
        midpoint_seam_mm=MIDPOINT_SEAM_MM,
        rib_stations_y_mm=RIB_STATIONS_Y_MM,
        joint_clearance_per_face_mm=JOINT_CLEARANCE_PER_FACE_MM,
        minimum_support_bearing_length_mm=SUPPORT_BEARING_LENGTH_MM,
        half_deck_count=2,
        keystone_count=1,
        target_body_count=sum(
            len(mesh.split(only_watertight=False)) for mesh in installed.values()
        ),
        target_watertight=all(mesh.is_watertight for mesh in installed.values()),
        target_winding_consistent=all(
            mesh.is_winding_consistent for mesh in installed.values()
        ),
        print_envelopes=envelopes,
        rib_section=rib_section_evidence(),
        assembly=build_assembly_path_evidence(kind),
        aesthetic_contract_id=AESTHETIC_CONTRACT_ID,
        qualification_only=True,
        rated_load_kg=0.0,
        wall_installation_authorized=False,
        analytic_blockers=(
            "full R11 support and S0 fused cable receiver meshes are outside this module",
            "wall keepouts, blocking, and exact fastener schedule remain unverified",
        ),
        physical_blockers=(
            "print both exact terminal and regular joint articles",
            "complete ten assembly/release cycles without force, fracture, or walkout",
            "qualify the support lugs, bearing surfaces, wall connection, creep, and proof loads",
        ),
    )


def build_regular_bay_evidence() -> IntegratedBayEvidence:
    return _bay_evidence("regular")


def build_terminal_bay_evidence() -> IntegratedBayEvidence:
    return _bay_evidence("terminal")


def build_outer_terminal_bay_evidence() -> dict[str, object]:
    """Return JSON-safe evidence for the geometry-authored outer-bay subset."""

    parts = build_saved_outer_terminal_bay_parts()
    per_part: dict[str, object] = {}
    for name, mesh in parts.items():
        layer = saved_layer_connectivity_report(mesh)
        envelope = print_envelope(mesh)
        per_part[name] = {
            "body_count": len(mesh.split(only_watertight=False)),
            "watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "support_required": layer.support_required,
            "saved_orientation": (
                "complete_top_datum_on_plate_one_half_deck_per_plate"
                if name.endswith("half_deck")
                else "keystone_decorative_cap_on_plate"
            ),
            "layer_connectivity": asdict(layer),
            "print_envelope": asdict(envelope),
        }
    bay = build_terminal_bay_evidence()
    analytic_blockers = (
        *bay.analytic_blockers,
        "outer-bay bundle also requires explicit S0 support, ordinary support, and three cable-module providers",
    )
    geometry_subset_passed = (
        bay.assembly.all_authored_service_paths_collision_free
        and bay.assembly.positive_no_friction_reverse_stop
        and all(not item["support_required"] for item in per_part.values())
        and all(item["print_envelope"]["fits"] for item in per_part.values())
    )
    return {
        "schema_version": "r11_outer_terminal_geometry_subset_v1",
        "part_order": OUTER_TERMINAL_BAY_PART_ORDER,
        "parts": per_part,
        "geometry_subset_passed": geometry_subset_passed,
        "subset_analytic_blockers": (),
        "subset_physical_and_field_blockers": bay.physical_blockers,
        "support_required_by_part": {
            name: item["support_required"] for name, item in per_part.items()
        },
        "all_saved_layer_islands_clear": all(
            not item["support_required"] for item in per_part.values()
        ),
        # Overall stays false while analytic and physical blockers remain.
        "passed": False,
        "analytic_blockers": analytic_blockers,
        "physical_blockers": bay.physical_blockers,
        "assembly_order": (
            "off-support, slide the two terminal half-decks together along X",
            "lower the one bay-local Palatine keystone vertically into its midpoint pocket",
            "hold the joined bay 32 mm forward and 14 mm above final pose",
            "lower to 2 mm above bearing with both lug heads in their entry pockets",
            "slide the rigid joined bay 32 mm toward the wall",
            "settle 2 mm by gravity behind both positive reverse-slide shoulders",
            "release by lifting 2 mm, sliding 32 mm away, lifting clear, removing the keystone, and separating the halves",
        ),
        "zero_rating": {
            "rated_load_kg": 0.0,
            "rated_load_lb": 0.0,
            "wall_installation_authorized": False,
        },
    }


def build_outer_terminal_bay_qualification_evidence() -> dict[str, object]:
    """Backward-compatible explicit qualification spelling."""

    return build_outer_terminal_bay_evidence()


__all__ = [
    "R11GeometryError",
    "build_regular_half_deck",
    "build_terminal_half_deck",
    "build_palatine_keystone",
    "build_capture_lug_interface_fixture",
    "build_installed_regular_bay_parts",
    "build_installed_terminal_bay_parts",
    "build_saved_regular_bay_parts",
    "build_saved_terminal_bay_parts",
    "build_saved_outer_terminal_bay_parts",
    "build_regular_bay_evidence",
    "build_terminal_bay_evidence",
    "build_outer_terminal_bay_evidence",
    "build_outer_terminal_bay_qualification_evidence",
    "build_assembly_path_evidence",
    "saved_layer_connectivity_report",
    "field_inventory_evidence",
    "adjacent_capture_evidence",
    "rib_section_evidence",
    "print_envelope",
]
