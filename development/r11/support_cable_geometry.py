#!/usr/bin/env python3
"""R11 support, capture-lug, and S0 cable qualification geometry.

This module authors the five articles that complete the R11 first-outer-bay
neutral qualification set.  It does not release a print, wall drilling,
installation, load test, or load rating.

Installed axes are X along the wall, Y from wall to shelf front, and Z upward.
The shelf bearing plane is Z=0.  The ordinary support is a new R11 body: a
31.75 mm wide, 152.4 mm deep corbel with a 158.75 mm wall strap, three exact
7 mm wall bores, full annular washer lands, an uninterrupted diagonal load
path, and additive Palatine side mouldings.  Two independent mushroom lugs
are built by the same R11 interface builder used by the half-deck galleries.
The lugs extend 10 mm above the bearing plane, so the complete installed Z
envelope is 168.75 mm; that envelope is not the structural-strap height.

S0 starts with that complete support and only adds material.  Its two inward
facing cable sockets are outside the structural core and clear the wall bores,
lug service region, and shelf bearing plane.  A module approaches a socket
from +X while raised 8 mm, moves inward, and gravity-drops 8 mm.  Removal is
the exact reverse.  The two blanks and comb/hook carry zero shelf-load credit.

Saved supports place the wall face on the plate and rotate their long bed
envelope 45 degrees.  Saved cable modules place a continuous Y side on the
plate.  These are authored support-off intentions only; slicer Preview and a
fresh human print decision remain mandatory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable, Mapping, Sequence
import warnings

import numpy as np
from shapely.geometry import LineString, Polygon
import trimesh

try:
    from . import integrated_geometry
except ImportError:  # pragma: no cover - direct unittest discovery
    import integrated_geometry  # type: ignore[no-redef]


class R11SupportCableGeometryError(ValueError):
    """Raised when an R11 support/cable datum would require an assumption."""


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PRINT_AUTHORIZED = False
WALL_INSTALLATION_AUTHORIZED = False
DRILLING_COORDINATES_RELEASED = False
TEST_LOAD_AUTHORIZED = False
PHYSICAL_QUALIFICATION_COMPLETE = False
STRUCTURAL_OR_SHELF_LOAD_CREDIT = False
SUPPORT_CORE_SUBTRACTION_FOR_CABLE_ALLOWED = False
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0
PRINTED_MATERIAL = "SUNLU standard black PETG, ASIN B0D1KC72YP"

SUPPORT_RUN_WIDTH_MM = 31.75
SUPPORT_X_BOUNDS_MM = (-SUPPORT_RUN_WIDTH_MM / 2.0, SUPPORT_RUN_WIDTH_MM / 2.0)
SUPPORT_PROJECTION_MM = 152.4
STRUCTURAL_STRAP_HEIGHT_MM = 158.75
WALL_STRAP_DEPTH_MM = 12.0
SHELF_ARM_HEIGHT_MM = 12.0
WALL_BORE_DIAMETER_MM = 7.0
WASHER_LAND_OUTER_DIAMETER_MM = 27.025
WALL_BORE_X_MM = 0.0
WALL_BORE_Z_MM = (-19.05, -79.375, -139.7)

CAPTURE_LUG_CENTER_X_MM = integrated_geometry.CAPTURE_LUG_CENTER_X_MM
CAPTURE_LUG_CENTERS_X_MM = (
    -CAPTURE_LUG_CENTER_X_MM,
    CAPTURE_LUG_CENTER_X_MM,
)
CAPTURE_LUG_CENTER_Y_MM = integrated_geometry.CAPTURE_FINAL_Y_MM
CAPTURE_WALLWARD_SLIDE_MM = integrated_geometry.CAPTURE_WALLWARD_SLIDE_MM
CAPTURE_SERVICE_ELEVATION_MM = integrated_geometry.CAPTURE_SLIDE_ELEVATION_MM
CAPTURE_SETTLE_MM = 2.0

SOCKET_CLEARANCE_PER_FACE_MM = 0.4
SOCKET_SERVICE_LIFT_MM = 8.0
SOCKET_COUNT = 2
SOCKET_CENTER_Y_MM = 48.0
SOCKET_CENTER_Z_MM = (-57.0, -31.0)
RECEIVER_X_BOUNDS_MM = (
    SUPPORT_X_BOUNDS_MM[1] - 0.4,
    SUPPORT_X_BOUNDS_MM[1] - 0.4 + 8.8,
)
RECEIVER_Y_BOUNDS_MM = (0.0, 36.0)
RECEIVER_Z_BOUNDS_MM = (-74.0, -12.0)
RECEIVER_BACK_WEB_MM = 1.3
RECEIVER_CORE_OVERLAP_MM = SUPPORT_X_BOUNDS_MM[1] - RECEIVER_X_BOUNDS_MM[0]
RECEIVER_TO_LUG_SERVICE_GAP_MM = (
    CAPTURE_LUG_CENTER_Y_MM
    - integrated_geometry.CAPTURE_LUG_HEAD_XY_MM / 2.0
    - RECEIVER_Y_BOUNDS_MM[1]
)

MODULE_HEAD_WIDTH_MM = 11.0
MODULE_HEAD_DEPTH_MM = 3.6
MODULE_STEM_WIDTH_MM = 6.0
MODULE_STEM_DEPTH_MM = 3.6
MODULE_LUG_HEIGHT_MM = 8.0
MODULE_BASE_WIDTH_MM = 20.0
MODULE_BASE_HEIGHT_MM = 16.0
MODULE_BASE_THICKNESS_MM = 3.2
MODULE_BASE_X_BOUNDS_MM = (
    RECEIVER_X_BOUNDS_MM[1],
    RECEIVER_X_BOUNDS_MM[1] + MODULE_BASE_THICKNESS_MM,
)
MODULE_STEM_X_BOUNDS_MM = (
    RECEIVER_X_BOUNDS_MM[1] - 3.5,
    RECEIVER_X_BOUNDS_MM[1] + 0.1,
)
MODULE_HEAD_X_BOUNDS_MM = (
    RECEIVER_X_BOUNDS_MM[1] - 7.1,
    RECEIVER_X_BOUNDS_MM[1] - 3.4,
)

A1_MINI_BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
BRIM_WIDTH_MM = 5.0
BRIM_OBJECT_GAP_MM = 0.1
RESERVE_PER_BED_EDGE_MM = 2.0
XY_PROCESS_ALLOWANCE_MM = 2.0 * (
    BRIM_WIDTH_MM + BRIM_OBJECT_GAP_MM + RESERVE_PER_BED_EDGE_MM
)
LAYER_SAMPLE_HEIGHT_MM = 0.4
GEOMETRY_EPSILON_MM = 1.0e-7
COLLISION_TOLERANCE_MM3 = 1.0e-5
CORE_CONTAINMENT_TOLERANCE_MM3 = 1.0e-4

S0_SUPPORT_PART = "r11_first_wall_s0_fused_two_socket_support"
S1_SUPPORT_PART = "r11_first_wall_s1_ordinary_support"
BLANK_0_PART = "r11_first_wall_socket_0_flush_blank"
BLANK_1_PART = "r11_first_wall_socket_1_flush_blank"
COMB_PART = "r11_first_wall_multi_cable_comb_hook"
OUTER_BAY_SUPPORT_CABLE_PART_ORDER = (
    S0_SUPPORT_PART,
    S1_SUPPORT_PART,
    BLANK_0_PART,
    BLANK_1_PART,
    COMB_PART,
)


@dataclass(frozen=True)
class PrintEnvelope:
    raw_part_mm: tuple[float, float, float]
    required_build_volume_mm: tuple[float, float, float]
    available_build_volume_mm: tuple[float, float, float]
    fits: bool


@dataclass(frozen=True)
class LayerConnectivityReport:
    layer_height_mm: float
    sampled_layer_count: int
    first_layer_contact_area_mm2: float
    island_layer_indices: tuple[int, ...]
    support_required: bool


def _require_exact(value: float, expected: float, name: str) -> None:
    if not math.isclose(float(value), float(expected), rel_tol=0.0, abs_tol=1e-9):
        raise R11SupportCableGeometryError(
            f"{name} drifted: {value!r} != {expected!r}"
        )


_require_exact(SUPPORT_RUN_WIDTH_MM, integrated_geometry.SUPPORT_RUN_WIDTH_MM, "support run width")
_require_exact(CAPTURE_LUG_CENTER_X_MM, 7.85, "capture lug half-land center")
_require_exact(CAPTURE_WALLWARD_SLIDE_MM, 32.0, "capture slide")
_require_exact(CAPTURE_SERVICE_ELEVATION_MM, 2.0, "capture service elevation")
_require_exact(SOCKET_CLEARANCE_PER_FACE_MM, 0.4, "socket clearance")
_require_exact(SOCKET_SERVICE_LIFT_MM, 8.0, "socket service lift")
_require_exact(XY_PROCESS_ALLOWANCE_MM, 14.2, "print-process XY allowance")
_require_exact(RECEIVER_CORE_OVERLAP_MM, 0.4, "receiver/core additive overlap")
_require_exact(RECEIVER_TO_LUG_SERVICE_GAP_MM, 8.0, "receiver/lug service gap")


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise R11SupportCableGeometryError("geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    if not np.isfinite(mesh.vertices).all():
        raise R11SupportCableGeometryError("geometry contains non-finite vertices")
    return mesh


def _copy(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    return _clean(mesh.copy())


def _box(
    x_bounds: tuple[float, float],
    y_bounds: tuple[float, float],
    z_bounds: tuple[float, float],
) -> trimesh.Trimesh:
    bounds = (x_bounds, y_bounds, z_bounds)
    if any(not math.isfinite(item) for pair in bounds for item in pair):
        raise R11SupportCableGeometryError("box bounds must be finite")
    if any(high <= low for low, high in bounds):
        raise R11SupportCableGeometryError("box bounds must have positive extent")
    extents = np.asarray([high - low for low, high in bounds], dtype=float)
    center = np.asarray([(low + high) / 2.0 for low, high in bounds], dtype=float)
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    return _clean(mesh)


def _cylinder_y(
    *, diameter_mm: float, y_bounds: tuple[float, float], center_xz: tuple[float, float]
) -> trimesh.Trimesh:
    low, high = y_bounds
    if high <= low or diameter_mm <= 0.0:
        raise R11SupportCableGeometryError("cylinder dimensions must be positive")
    transform = trimesh.transformations.rotation_matrix(
        -math.pi / 2.0, (1.0, 0.0, 0.0)
    )
    transform[:3, 3] = (
        float(center_xz[0]),
        (low + high) / 2.0,
        float(center_xz[1]),
    )
    return _clean(
        trimesh.creation.cylinder(
            radius=diameter_mm / 2.0,
            height=high - low,
            sections=64,
            transform=transform,
        )
    )


def _extrude_yz_profile(
    profile: Polygon, *, x_bounds: tuple[float, float]
) -> trimesh.Trimesh:
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise R11SupportCableGeometryError("YZ profile must be valid and positive")
    low, high = x_bounds
    source = trimesh.creation.extrude_polygon(
        profile, height=high - low, engine="earcut"
    )
    old = np.asarray(source.vertices, dtype=float).copy()
    # Source profile XY is installed YZ; source extrusion Z is installed X.
    source.vertices = np.column_stack((old[:, 2] + low, old[:, 0], old[:, 1]))
    source.fix_normals(multibody=True)
    return _clean(source)


def _union(meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise R11SupportCableGeometryError("union needs at least one mesh")
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


def _one_body(mesh: trimesh.Trimesh, name: str) -> trimesh.Trimesh:
    result = _clean(mesh)
    if (
        len(result.split(only_watertight=False)) != 1
        or not result.is_watertight
        or not result.is_winding_consistent
        or float(result.volume) <= 0.0
    ):
        raise R11SupportCableGeometryError(
            f"{name} must be one watertight positive body"
        )
    return result


def _intersection_volume(first: trimesh.Trimesh, second: trimesh.Trimesh) -> float:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = trimesh.boolean.intersection(
            [_copy(first), _copy(second)], engine="manifold", check_volume=True
        )
    if result is None or (isinstance(result, list) and not result):
        return 0.0
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    if result.is_empty:
        return 0.0
    volume = abs(float(result.volume))
    return 0.0 if volume <= 1.0e-8 else volume


def _missing_volume(body: trimesh.Trimesh, container: trimesh.Trimesh) -> float:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = trimesh.boolean.difference(
            [_copy(body), _copy(container)], engine="manifold", check_volume=True
        )
    if result is None or (isinstance(result, list) and not result):
        return 0.0
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    if result.is_empty:
        return 0.0
    volume = abs(float(result.volume))
    return 0.0 if volume <= CORE_CONTAINMENT_TOLERANCE_MM3 else volume


def _palatine_mouldings() -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """Add zero-credit classical side mouldings outside the central load web."""

    centerline = LineString(
        (
            (5.0, -150.0),
            (30.0, -143.0),
            (58.0, -121.0),
            (85.0, -90.0),
            (109.0, -56.0),
            (130.0, -27.0),
            (145.0, -10.0),
        )
    )
    profile = centerline.buffer(3.0, cap_style="square", join_style="mitre")
    if not isinstance(profile, Polygon):
        raise R11SupportCableGeometryError("Palatine moulding became multi-body")
    return (
        _extrude_yz_profile(
            profile,
            x_bounds=(SUPPORT_X_BOUNDS_MM[0], SUPPORT_X_BOUNDS_MM[0] + 4.0),
        ),
        _extrude_yz_profile(
            profile,
            x_bounds=(SUPPORT_X_BOUNDS_MM[1] - 4.0, SUPPORT_X_BOUNDS_MM[1]),
        ),
    )


def _wall_bore_cutters() -> tuple[trimesh.Trimesh, ...]:
    return tuple(
        _cylinder_y(
            diameter_mm=WALL_BORE_DIAMETER_MM,
            y_bounds=(-1.0, WALL_STRAP_DEPTH_MM + 1.0),
            center_xz=(WALL_BORE_X_MM, center_z),
        )
        for center_z in WALL_BORE_Z_MM
    )


def build_ordinary_support() -> trimesh.Trimesh:
    """Build the actual R11 support with two independent capture lugs."""

    wall_strap = _box(
        SUPPORT_X_BOUNDS_MM,
        (0.0, WALL_STRAP_DEPTH_MM),
        (-STRUCTURAL_STRAP_HEIGHT_MM, 0.0),
    )
    shelf_arm = _box(
        SUPPORT_X_BOUNDS_MM,
        (0.0, SUPPORT_PROJECTION_MM),
        (-SHELF_ARM_HEIGHT_MM, 0.0),
    )
    diagonal_profile = Polygon(
        ((0.0, -150.0), (18.0, -150.0), (146.0, -12.0), (124.0, -12.0))
    )
    diagonal = _extrude_yz_profile(
        diagonal_profile, x_bounds=(-10.0, 10.0)
    )
    lower_tie = _box(
        (-10.0, 10.0),
        (0.0, 24.0),
        (-152.0, -138.0),
    )
    lugs: list[trimesh.Trimesh] = []
    fusion_pads: list[trimesh.Trimesh] = []
    lug_print_ramps: list[trimesh.Trimesh] = []
    for center_x in CAPTURE_LUG_CENTERS_X_MM:
        lugs.append(
            integrated_geometry.build_capture_lug_interface_fixture(
                center_x_mm=center_x, center_y_mm=CAPTURE_LUG_CENTER_Y_MM
            )
        )
        fusion_pads.append(
            _box(
                (center_x - 1.9, center_x + 1.9),
                (CAPTURE_LUG_CENTER_Y_MM - 1.9, CAPTURE_LUG_CENTER_Y_MM + 1.9),
                (-0.2, 0.1),
            )
        )
        # In the wall-face-down saved orientation the head begins 2 mm before
        # the neck.  This narrow permanent 45-degree-under ramp reaches the
        # head's 3.9 mm underside from the already printed shelf arm.  It stays
        # inside the half-deck's 4.8 mm neck-clear service lane, so it changes
        # neither the exact lug head nor the lower/slide/settle interface.
        ramp_profile = Polygon(
            (
                (43.6, -0.1),
                (44.8, -0.1),
                (44.8, 4.3),
                (44.0, 4.3),
            )
        )
        lug_print_ramps.append(
            _extrude_yz_profile(
                ramp_profile, x_bounds=(center_x - 1.9, center_x + 1.9)
            )
        )
    unbored = _union(
        (
            wall_strap,
            shelf_arm,
            diagonal,
            lower_tie,
            *_palatine_mouldings(),
            *fusion_pads,
            *lug_print_ramps,
            *lugs,
        )
    )
    support = _one_body(
        _difference(unbored, _wall_bore_cutters()), "R11 ordinary support"
    )
    expected = (
        SUPPORT_RUN_WIDTH_MM,
        SUPPORT_PROJECTION_MM,
        STRUCTURAL_STRAP_HEIGHT_MM
        + integrated_geometry.CAPTURE_LUG_TOTAL_HEIGHT_MM,
    )
    if not np.allclose(support.extents, expected, rtol=0.0, atol=1e-5):
        raise R11SupportCableGeometryError(
            f"ordinary support envelope drifted: {tuple(support.extents)}"
        )
    return support


def _socket_cutters(center_z_mm: float) -> tuple[trimesh.Trimesh, ...]:
    clearance = SOCKET_CLEARANCE_PER_FACE_MM
    head_y = (
        SOCKET_CENTER_Y_MM - MODULE_HEAD_WIDTH_MM / 2.0 - clearance,
        SOCKET_CENTER_Y_MM + MODULE_HEAD_WIDTH_MM / 2.0 + clearance,
    )
    stem_y = (
        SOCKET_CENTER_Y_MM - MODULE_STEM_WIDTH_MM / 2.0 - clearance,
        SOCKET_CENTER_Y_MM + MODULE_STEM_WIDTH_MM / 2.0 + clearance,
    )
    full_z = (
        center_z_mm - MODULE_LUG_HEIGHT_MM / 2.0 - clearance,
        center_z_mm
        + SOCKET_SERVICE_LIFT_MM
        + MODULE_LUG_HEIGHT_MM / 2.0
        + clearance,
    )
    raised_entry_z = (
        center_z_mm
        + SOCKET_SERVICE_LIFT_MM
        - MODULE_LUG_HEIGHT_MM / 2.0
        - clearance,
        center_z_mm
        + SOCKET_SERVICE_LIFT_MM
        + MODULE_LUG_HEIGHT_MM / 2.0
        + clearance,
    )
    return (
        _box(
            (
                RECEIVER_X_BOUNDS_MM[1] - 7.5,
                RECEIVER_X_BOUNDS_MM[1] - 3.0,
            ),
            head_y,
            full_z,
        ),
        _box(
            (
                RECEIVER_X_BOUNDS_MM[1] - 3.9,
                RECEIVER_X_BOUNDS_MM[1] + 0.4,
            ),
            stem_y,
            full_z,
        ),
        _box(
            (
                RECEIVER_X_BOUNDS_MM[1] - 3.0,
                RECEIVER_X_BOUNDS_MM[1] + 0.4,
            ),
            head_y,
            raised_entry_z,
        ),
    )


def build_two_socket_receiver() -> trimesh.Trimesh:
    """Build the additive-only, two-socket rail before fusion to S0."""

    body = _box(
        RECEIVER_X_BOUNDS_MM, RECEIVER_Y_BOUNDS_MM, RECEIVER_Z_BOUNDS_MM
    )
    cutters = tuple(
        cutter
        for center_z in SOCKET_CENTER_Z_MM
        for cutter in _socket_cutters(center_z)
    )
    receiver = _one_body(
        _difference(body, cutters), "R11 S0 two-socket receiver"
    )
    if len(SOCKET_CENTER_Z_MM) != SOCKET_COUNT:
        raise R11SupportCableGeometryError("receiver must have exactly two sockets")
    return receiver


def build_s0_fused_two_socket_support() -> trimesh.Trimesh:
    """Fuse the additive receiver to a complete, uncut ordinary support."""

    core = build_ordinary_support()
    receiver = build_two_socket_receiver()
    result = _one_body(_union((core, receiver)), "R11 S0 fused cable support")
    if _missing_volume(core, result) > CORE_CONTAINMENT_TOLERANCE_MM3:
        raise R11SupportCableGeometryError("S0 cable fusion removed structural core")
    return result


def _build_module(*, comb_hook: bool, center_z_mm: float = 0.0) -> trimesh.Trimesh:
    center_z = float(center_z_mm)
    base = _box(
        MODULE_BASE_X_BOUNDS_MM,
        (
            SOCKET_CENTER_Y_MM - MODULE_BASE_WIDTH_MM / 2.0,
            SOCKET_CENTER_Y_MM + MODULE_BASE_WIDTH_MM / 2.0,
        ),
        (center_z - MODULE_BASE_HEIGHT_MM / 2.0, center_z + MODULE_BASE_HEIGHT_MM / 2.0),
    )
    stem = _box(
        MODULE_STEM_X_BOUNDS_MM,
        (
            SOCKET_CENTER_Y_MM - MODULE_STEM_WIDTH_MM / 2.0,
            SOCKET_CENTER_Y_MM + MODULE_STEM_WIDTH_MM / 2.0,
        ),
        (center_z - MODULE_LUG_HEIGHT_MM / 2.0, center_z + MODULE_LUG_HEIGHT_MM / 2.0),
    )
    head = _box(
        MODULE_HEAD_X_BOUNDS_MM,
        (
            SOCKET_CENTER_Y_MM - MODULE_HEAD_WIDTH_MM / 2.0,
            SOCKET_CENTER_Y_MM + MODULE_HEAD_WIDTH_MM / 2.0,
        ),
        (center_z - MODULE_LUG_HEIGHT_MM / 2.0, center_z + MODULE_LUG_HEIGHT_MM / 2.0),
    )
    additions: list[trimesh.Trimesh] = [base, stem, head]
    if comb_hook:
        base_front = MODULE_BASE_X_BOUNDS_MM[1]
        additions.append(
            _box(
                (base_front - 0.2, base_front + 4.85),
                (SOCKET_CENTER_Y_MM - 9.0, SOCKET_CENTER_Y_MM + 9.0),
                (center_z - 7.0, center_z - 3.0),
            )
        )
        for offset_y in (-7.0, 0.0, 7.0):
            additions.extend(
                (
                    _box(
                        (base_front + 4.45, base_front + 12.65),
                        (
                            SOCKET_CENTER_Y_MM + offset_y - 1.2,
                            SOCKET_CENTER_Y_MM + offset_y + 1.2,
                        ),
                        (center_z - 7.0, center_z - 3.0),
                    ),
                    _box(
                        (base_front + 9.65, base_front + 12.65),
                        (
                            SOCKET_CENTER_Y_MM + offset_y - 1.2,
                            SOCKET_CENTER_Y_MM + offset_y + 1.2,
                        ),
                        (center_z - 7.0, center_z + 3.0),
                    ),
                )
            )
    return _one_body(
        _union(tuple(additions)),
        "R11 multi-cable comb/hook" if comb_hook else "R11 flush blank",
    )


def build_flush_blank_module() -> trimesh.Trimesh:
    return _build_module(comb_hook=False)


def build_multi_cable_comb_hook_module() -> trimesh.Trimesh:
    return _build_module(comb_hook=True)


def _normalize(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    result = _copy(mesh)
    result.apply_translation(-np.asarray(result.bounds[0], dtype=float))
    return _clean(result)


def orient_support_wall_face_down(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Map installed Y to print Z and rotate the X/Z bed footprint 45 degrees."""

    result = _copy(mesh)
    old = np.asarray(result.vertices, dtype=float).copy()
    unrotated_x = old[:, 0]
    unrotated_y = old[:, 2]
    cosine = math.sqrt(0.5)
    result.vertices = np.column_stack(
        (
            cosine * (unrotated_x - unrotated_y),
            cosine * (unrotated_x + unrotated_y),
            old[:, 1],
        )
    )
    result.fix_normals(multibody=True)
    return _normalize(result)


def orient_module_y_side_on_plate(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Build from head to stem, base, and hook along installed +X.

    The historical function spelling remains intentionally stable for the
    bundle API.  The actual R11 orientation puts the lug-head YZ face on the
    plate, which is the only ordering that continuously anchors both the
    flush blank and the outward-projecting comb/hook without supports.
    """

    result = _copy(mesh)
    old = np.asarray(result.vertices, dtype=float).copy()
    result.vertices = np.column_stack((old[:, 1], old[:, 2], old[:, 0]))
    result.fix_normals(multibody=True)
    return _normalize(result)


def print_envelope(mesh: trimesh.Trimesh) -> PrintEnvelope:
    raw = tuple(round(float(value), 6) for value in mesh.extents)
    required = (
        round(raw[0] + XY_PROCESS_ALLOWANCE_MM, 6),
        round(raw[1] + XY_PROCESS_ALLOWANCE_MM, 6),
        raw[2],
    )
    fits = bool(
        required[0] <= A1_MINI_BUILD_VOLUME_MM[0] + GEOMETRY_EPSILON_MM
        and required[1] <= A1_MINI_BUILD_VOLUME_MM[1] + GEOMETRY_EPSILON_MM
        and required[2] <= A1_MINI_BUILD_VOLUME_MM[2] + GEOMETRY_EPSILON_MM
    )
    return PrintEnvelope(
        raw_part_mm=raw,
        required_build_volume_mm=required,
        available_build_volume_mm=A1_MINI_BUILD_VOLUME_MM,
        fits=fits,
    )


def saved_layer_connectivity_report(
    mesh: trimesh.Trimesh, *, layer_height_mm: float = LAYER_SAMPLE_HEIGHT_MM
) -> LayerConnectivityReport:
    """Use R11's common all-layer filled-region connectivity scanner.

    The common scanner reconstructs holes with symmetric differences before
    testing component ancestry.  Treating every section loop as filled would
    incorrectly classify the wall-bore loops as new printed islands.
    """

    shared = integrated_geometry.saved_layer_connectivity_report(
        mesh, layer_height_mm=layer_height_mm
    )
    return LayerConnectivityReport(
        layer_height_mm=shared.layer_height_mm,
        sampled_layer_count=shared.sampled_layer_count,
        first_layer_contact_area_mm2=shared.first_layer_contact_area_mm2,
        island_layer_indices=shared.island_layer_indices,
        support_required=shared.support_required,
    )


def _translated(
    mesh: trimesh.Trimesh, translation: tuple[float, float, float]
) -> trimesh.Trimesh:
    result = _copy(mesh)
    result.apply_translation(np.asarray(translation, dtype=float))
    return _clean(result)


def _installed_module(
    *, comb_hook: bool, station_index: int, rise_mm: float = 0.0, outward_mm: float = 0.0
) -> trimesh.Trimesh:
    if station_index not in (0, 1):
        raise R11SupportCableGeometryError("socket station must be 0 or 1")
    source = _build_module(
        comb_hook=comb_hook, center_z_mm=SOCKET_CENTER_Z_MM[station_index]
    )
    return _translated(source, (float(outward_mm), 0.0, float(rise_mm)))


def _module_service_evidence(
    receiver: trimesh.Trimesh, *, comb_hook: bool, station_index: int
) -> dict[str, object]:
    approaches = tuple(np.linspace(8.0, 0.0, 9))
    drops = tuple(np.linspace(SOCKET_SERVICE_LIFT_MM, 0.0, 9))
    approach_volumes = tuple(
        _intersection_volume(
            _installed_module(
                comb_hook=comb_hook,
                station_index=station_index,
                rise_mm=SOCKET_SERVICE_LIFT_MM,
                outward_mm=float(outward),
            ),
            receiver,
        )
        for outward in approaches
    )
    drop_volumes = tuple(
        _intersection_volume(
            _installed_module(
                comb_hook=comb_hook,
                station_index=station_index,
                rise_mm=float(rise),
            ),
            receiver,
        )
        for rise in drops
    )
    maximum = max((*approach_volumes, *drop_volumes))
    return {
        "module": "comb_hook" if comb_hook else "flush_blank",
        "station_index": station_index,
        "socket_clearance_per_face_mm": SOCKET_CLEARANCE_PER_FACE_MM,
        "service_lift_mm": SOCKET_SERVICE_LIFT_MM,
        "approach_sample_count": len(approach_volumes),
        "drop_sample_count": len(drop_volumes),
        "removal_is_exact_reverse": True,
        "maximum_intersection_mm3": maximum,
        "collision_free": maximum <= COLLISION_TOLERANCE_MM3,
    }


def _outer_bay_capture_service_evidence() -> dict[str, object]:
    """Exercise the exact full supports, not interface-only stand-ins."""

    bay = integrated_geometry.build_installed_terminal_bay_parts()
    moving = tuple(bay.values())
    span = integrated_geometry.TERMINAL_CLEAR_SPAN_MM
    fixed = (
        build_s0_fused_two_socket_support(),
        _translated(build_ordinary_support(), (span, 0.0, 0.0)),
    )

    def maximum_at(translation: tuple[float, float, float]) -> float:
        return max(
            _intersection_volume(_translated(part, translation), support)
            for part in moving
            for support in fixed
        )

    target = maximum_at((0.0, 0.0, 0.0))
    drop = max(
        maximum_at((0.0, CAPTURE_WALLWARD_SLIDE_MM, float(z)))
        for z in np.linspace(
            integrated_geometry.CAPTURE_INITIAL_LIFT_MM,
            CAPTURE_SERVICE_ELEVATION_MM,
            13,
        )
    )
    slide = max(
        maximum_at((0.0, float(y), CAPTURE_SERVICE_ELEVATION_MM))
        for y in np.linspace(CAPTURE_WALLWARD_SLIDE_MM, 0.0, 17)
    )
    settle = max(
        maximum_at((0.0, 0.0, float(z)))
        for z in np.linspace(CAPTURE_SERVICE_ELEVATION_MM, 0.0, 9)
    )
    blocked = maximum_at((0.0, 8.0, 0.0))
    maximum_service = max(target, drop, slide, settle)
    return {
        "target_maximum_intersection_mm3": target,
        "lower_maximum_intersection_mm3": drop,
        "wallward_slide_maximum_intersection_mm3": slide,
        "gravity_settle_maximum_intersection_mm3": settle,
        "exact_reverse_maximum_intersection_mm3": maximum_service,
        "forbidden_horizontal_reverse_intersection_mm3": blocked,
        "all_service_samples_collision_free": maximum_service
        <= COLLISION_TOLERANCE_MM3,
        "positive_reverse_stop": blocked > COLLISION_TOLERANCE_MM3,
        "full_s0_and_s1_support_meshes_exercised": True,
    }


def _washer_land_missing_volumes(support: trimesh.Trimesh) -> tuple[float, ...]:
    """Return material missing from each exact 27.025/7 mm annular land."""

    values: list[float] = []
    for center_z in WALL_BORE_Z_MM:
        outer = _cylinder_y(
            diameter_mm=WASHER_LAND_OUTER_DIAMETER_MM,
            y_bounds=(0.1, WALL_STRAP_DEPTH_MM - 0.1),
            center_xz=(WALL_BORE_X_MM, center_z),
        )
        bore = _cylinder_y(
            diameter_mm=WALL_BORE_DIAMETER_MM,
            y_bounds=(0.0, WALL_STRAP_DEPTH_MM),
            center_xz=(WALL_BORE_X_MM, center_z),
        )
        land = _one_body(_difference(outer, (bore,)), "R11 washer-land probe")
        values.append(_missing_volume(land, support))
    return tuple(values)


def build_saved_outer_bay_support_cable_parts() -> dict[str, trimesh.Trimesh]:
    """Return the exact ordered five-article support/cable provider."""

    blank = orient_module_y_side_on_plate(build_flush_blank_module())
    return {
        S0_SUPPORT_PART: orient_support_wall_face_down(
            build_s0_fused_two_socket_support()
        ),
        S1_SUPPORT_PART: orient_support_wall_face_down(build_ordinary_support()),
        BLANK_0_PART: _copy(blank),
        BLANK_1_PART: _copy(blank),
        COMB_PART: orient_module_y_side_on_plate(
            build_multi_cable_comb_hook_module()
        ),
    }


def build_outer_bay_support_cable_evidence() -> dict[str, object]:
    """Return JSON-safe analytic evidence while every external gate stays shut."""

    core = build_ordinary_support()
    receiver = build_two_socket_receiver()
    fused = build_s0_fused_two_socket_support()
    missing_core = _missing_volume(core, fused)
    receiver_bore_intersections = tuple(
        _intersection_volume(receiver, cutter) for cutter in _wall_bore_cutters()
    )
    washer_land_missing = _washer_land_missing_volumes(core)
    service = tuple(
        _module_service_evidence(
            receiver, comb_hook=comb_hook, station_index=station_index
        )
        for comb_hook in (False, True)
        for station_index in (0, 1)
    )
    parts = build_saved_outer_bay_support_cable_parts()
    part_evidence: dict[str, object] = {}
    support_map: dict[str, bool] = {}
    for name, mesh in parts.items():
        layer = saved_layer_connectivity_report(mesh)
        envelope = print_envelope(mesh)
        support_map[name] = layer.support_required
        part_evidence[name] = {
            "body_count": len(mesh.split(only_watertight=False)),
            "watertight": bool(mesh.is_watertight),
            "winding_consistent": bool(mesh.is_winding_consistent),
            "support_required": layer.support_required,
            "saved_orientation": (
                "wall_face_on_plate_long_envelope_rotated_45_degrees"
                if name in (S0_SUPPORT_PART, S1_SUPPORT_PART)
                else "lug_head_face_on_plate_then_stem_base_and_hook"
            ),
            "layer_connectivity": asdict(layer),
            "print_envelope": asdict(envelope),
        }

    adjacent = integrated_geometry.adjacent_capture_evidence()
    interface_path = integrated_geometry.build_assembly_path_evidence("terminal")
    full_support_path = _outer_bay_capture_service_evidence()
    exact_meshes = all(
        item["body_count"] == 1
        and item["watertight"] is True
        and item["winding_consistent"] is True
        and item["support_required"] is False
        and item["print_envelope"]["fits"] is True
        for item in part_evidence.values()
    )
    analytic_checks = {
        "exact_ordered_five_article_provider": tuple(parts)
        == OUTER_BAY_SUPPORT_CABLE_PART_ORDER,
        "new_r11_support_datums_exact": (
            SUPPORT_RUN_WIDTH_MM == 31.75
            and SUPPORT_PROJECTION_MM == 152.4
            and STRUCTURAL_STRAP_HEIGHT_MM == 158.75
        ),
        "three_exact_7mm_bores_and_full_washer_lands": (
            len(WALL_BORE_Z_MM) == 3
            and WALL_BORE_DIAMETER_MM == 7.0
            and WASHER_LAND_OUTER_DIAMETER_MM == 27.025
            and all(
                WALL_BORE_X_MM - WASHER_LAND_OUTER_DIAMETER_MM / 2.0
                >= SUPPORT_X_BOUNDS_MM[0]
                and WALL_BORE_X_MM + WASHER_LAND_OUTER_DIAMETER_MM / 2.0
                <= SUPPORT_X_BOUNDS_MM[1]
                for _ in WALL_BORE_Z_MM
            )
            and all(
                value <= CORE_CONTAINMENT_TOLERANCE_MM3
                for value in washer_land_missing
            )
        ),
        "support_core_preserved_additive_only": missing_core
        <= CORE_CONTAINMENT_TOLERANCE_MM3,
        "receiver_clears_all_wall_bores": all(
            value <= COLLISION_TOLERANCE_MM3
            for value in receiver_bore_intersections
        ),
        "exact_two_inward_sockets": SOCKET_COUNT == 2
        and len(SOCKET_CENTER_Z_MM) == 2,
        "receiver_clears_lug_service_region": RECEIVER_TO_LUG_SERVICE_GAP_MM
        == 8.0,
        "module_service_paths_clear": all(item["collision_free"] for item in service),
        "capture_interface_exact_and_independent": (
            CAPTURE_LUG_CENTERS_X_MM == (-7.85, 7.85)
            and adjacent.adjacent_bay_release_independent
            and adjacent.shared_release_component_count == 0
            and interface_path.all_authored_service_paths_collision_free
            and interface_path.positive_no_friction_reverse_stop
            and full_support_path["all_service_samples_collision_free"] is True
            and full_support_path["positive_reverse_stop"] is True
        ),
        "all_saved_meshes_closed_support_off_and_a1_fit": exact_meshes,
        "cable_accessories_receive_zero_structural_credit": (
            STRUCTURAL_OR_SHELF_LOAD_CREDIT is False
            and RATED_LOAD_KG == 0.0
            and RATED_LOAD_LB == 0.0
        ),
    }
    subset_passed = all(analytic_checks.values())
    physical_blockers = (
        "inspect all five exact saved articles in slicer Preview before any print decision",
        "print and cycle both support captures at least ten times without force or damage",
        "print and cycle each cable module in both sockets, including snag and removal checks",
        "field-verify wall construction, utilities, trim, door, cable-loop, and screw-axis clearances",
        "complete independent structural review, creep conditioning, proof load, and destructive qualification",
    )
    return {
        "schema_version": "r11_outer_bay_support_cable_geometry_subset_v1",
        "part_order": OUTER_BAY_SUPPORT_CABLE_PART_ORDER,
        "parts": part_evidence,
        "geometry_subset_passed": subset_passed,
        "subset_analytic_blockers": (),
        "subset_physical_and_field_blockers": physical_blockers,
        "support_required_by_part": support_map,
        "all_saved_layer_islands_clear": all(not value for value in support_map.values()),
        "analytic_checks": analytic_checks,
        "structural_contract": {
            "support_station_line_x_mm": 0.0,
            "support_x_bounds_mm": SUPPORT_X_BOUNDS_MM,
            "run_width_mm": SUPPORT_RUN_WIDTH_MM,
            "projection_mm": SUPPORT_PROJECTION_MM,
            "structural_strap_height_mm": STRUCTURAL_STRAP_HEIGHT_MM,
            "central_diagonal_web_x_bounds_mm": (-10.0, 10.0),
            "palatine_side_moulding_count": 2,
            "palatine_mouldings_are_additive": True,
            "palatine_mouldings_structural_credit": False,
            "cable_receiver_structural_credit": False,
        },
        "core_preservation": {
            "support_core_subtraction_for_cable_allowed": False,
            "missing_structural_core_volume_mm3": missing_core,
            "preserved": missing_core <= CORE_CONTAINMENT_TOLERANCE_MM3,
        },
        "wall_connection_geometry": {
            "structural_strap_height_mm": STRUCTURAL_STRAP_HEIGHT_MM,
            "capture_lug_height_above_bearing_mm": integrated_geometry.CAPTURE_LUG_TOTAL_HEIGHT_MM,
            "complete_installed_z_envelope_mm": STRUCTURAL_STRAP_HEIGHT_MM
            + integrated_geometry.CAPTURE_LUG_TOTAL_HEIGHT_MM,
            "wall_bore_count": 3,
            "wall_bore_diameter_mm": WALL_BORE_DIAMETER_MM,
            "wall_bore_centers_installed_xz_mm": tuple(
                (WALL_BORE_X_MM, z) for z in WALL_BORE_Z_MM
            ),
            "washer_land_outer_diameter_mm": WASHER_LAND_OUTER_DIAMETER_MM,
            "receiver_bore_intersection_mm3": receiver_bore_intersections,
            "washer_land_missing_material_mm3": washer_land_missing,
            "drilling_coordinates_released": False,
        },
        "independent_capture_contract": {
            "lug_centers_x_mm": CAPTURE_LUG_CENTERS_X_MM,
            "lug_center_y_mm": CAPTURE_LUG_CENTER_Y_MM,
            "lower_to_service_elevation_mm": CAPTURE_SERVICE_ELEVATION_MM,
            "wallward_slide_mm": CAPTURE_WALLWARD_SLIDE_MM,
            "gravity_settle_mm": CAPTURE_SETTLE_MM,
            "release_is_exact_reverse": True,
            "shared_release_component_count": 0,
            "adjacent_bay_release_independent": adjacent.adjacent_bay_release_independent,
            "keystone_receives_capture_credit": False,
            "full_support_service_path": full_support_path,
        },
        "cable_contract": {
            "support_index": 0,
            "receiver_fused_additive_only": True,
            "socket_count": SOCKET_COUNT,
            "inward_axis": "+X along first-wall run",
            "socket_clearance_per_face_mm": SOCKET_CLEARANCE_PER_FACE_MM,
            "service_lift_drop_mm": SOCKET_SERVICE_LIFT_MM,
            "flush_blank_quantity": 2,
            "comb_hook_quantity": 1,
            "installed_socket_capacity": 2,
            "interchangeable_spare_articles": 1,
            "service_samples": service,
            "structural_credit": False,
        },
        "zero_rating_and_authorization": {
            "rated_load_kg": 0.0,
            "rated_load_lb": 0.0,
            "print_authorized": False,
            "wall_installation_authorized": False,
            "drilling_coordinates_released": False,
            "test_load_authorized": False,
            "production_ready": False,
        },
        # Overall remains false until the listed physical/field gates pass.
        "passed": False,
        "analytic_blockers": (),
        "physical_and_field_blockers": physical_blockers,
    }


__all__ = [
    "OUTER_BAY_SUPPORT_CABLE_PART_ORDER",
    "build_flush_blank_module",
    "build_multi_cable_comb_hook_module",
    "build_ordinary_support",
    "build_outer_bay_support_cable_evidence",
    "build_s0_fused_two_socket_support",
    "build_saved_outer_bay_support_cable_parts",
    "build_two_socket_receiver",
    "orient_module_y_side_on_plate",
    "orient_support_wall_face_down",
    "print_envelope",
    "saved_layer_connectivity_report",
]
