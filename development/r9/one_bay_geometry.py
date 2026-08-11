#!/usr/bin/env python3
"""Printable, no-load R9 tabletop one-bay shelf prototype.

This module is the first R9 geometry that is meant to assemble into a shelf
section rather than act as a loose coupon.  It deliberately stays small enough
for the Bambu Lab A1 mini: one 160 mm-wide bay at the full 152.4 mm shelf
projection.  The five printed articles are two handed compact supports, a rear
ledger, a front beam, and an open-bottom shelf cassette.

The prototype proves printability, the two member-to-support interfaces, deck
registration, appearance, and reversible tabletop assembly.  Its two supports
also carry an exact three-bore wall-mount *candidate* pattern so a successful
prototype can be evaluated against real hardware without drilling PETG after
printing.  The bores do not identify framing, approve an anchor, establish a
structural load path, or carry a load rating; those boundaries remain closed.

Installed axes in this file are X along the bay, Y from wall to shelf front,
and Z upward.  Support source meshes retain R9's q/e/run convention and are
mapped to installed X/Y/Z only for assembly evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
from shapely.geometry import Polygon
import trimesh

try:
    from . import support_geometry as support
except ImportError:  # pragma: no cover - direct unittest discovery
    import support_geometry as support  # type: ignore[no-redef]


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PHYSICAL_QUALIFICATION_COMPLETE = False
PRINTED_MATERIAL = "PETG"
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0
WALL_BORES_EMITTED = True

BAY_WIDTH_MM = 160.0
SHELF_DEPTH_MM = 152.4
SHELF_HEIGHT_MM = 30.0
SUPPORT_WIDTH_MM = 32.0
INNER_MEMBER_LENGTH_MM = BAY_WIDTH_MM - 2.0 * SUPPORT_WIDTH_MM

MEMBER_DEPTH_MM = 16.0
MEMBER_HEIGHT_MM = 30.0
MEMBER_TONGUE_LENGTH_MM = 8.0
MEMBER_TONGUE_DEPTH_MM = 8.0
MEMBER_TONGUE_HEIGHT_MM = MEMBER_HEIGHT_MM
INTERFACE_CLEARANCE_PER_FACE_MM = 0.4

REAR_MEMBER_Y_MM = 0.0
FRONT_MEMBER_Y_MM = SHELF_DEPTH_MM - MEMBER_DEPTH_MM
MEMBER_Z_MM = support.WALL_STRAP_TOTAL_DROP_MM - MEMBER_HEIGHT_MM

LOCATOR_BOSS_X_LOCAL_MM = 12.0
LOCATOR_BOSS_RUN_MM = 8.0
LOCATOR_BOSS_Y_MM = (24.0, 124.4)
LOCATOR_BOSS_DEPTH_MM = 4.0
LOCATOR_BOSS_PROTRUSION_MM = 1.4
LOCATOR_POCKET_DEPTH_MM = 2.0

CASSETTE_SKIN_MM = 2.4
CASSETTE_WEB_COUNT = 3
COLLISION_TOLERANCE_MM3 = 1.0e-5

# Three exact wall-mount candidates are printed into each 16 mm-deep strap.
# A diamond circumscribed around a 7 mm circle clears a nominal 1/4 in / M6-
# class metal fastener and grows continuously in either handed broad-face print
# orientation.  A washer stays on the uninterrupted front face; there is no
# counterbore and no printed fastener.  Hardware still has to be selected
# against the actual wall.
MOUNTING_BORE_DIAMETER_MM = 7.0
MOUNTING_BORE_DIAMOND_HALF_DIAGONAL_MM = 5.0
# The 64 mm pitch is intentional. It exceeds the 10D = 59.944 mm
# predrilled, parallel-to-grain spacing derived from the selected 0.236 in
# outside-thread-diameter GRK RSS candidate. This is geometric compatibility,
# not a released wall connection: framing, substrate, washer behavior against
# PETG, and the complete connection still require physical qualification.
MOUNTING_BORE_DROPS_BELOW_UNDERSIDE_MM = (16.0, 80.0, 144.0)
MOUNTING_BORE_CENTER_RUN_MM = SUPPORT_WIDTH_MM / 2.0
MOUNTING_BORE_Q_OVERRUN_MM = 1.0
MAXIMUM_FLAT_WASHER_OUTER_DIAMETER_MM = 20.0

FASTENER_CANDIDATE_PRODUCT = "GRK RSS 1/4 in x 3-1/2 in Climatek, part 90306"
FASTENER_CANDIDATE_OUTSIDE_THREAD_DIAMETER_MM = 0.236 * 25.4
FASTENER_CANDIDATE_PREDRILLED_SPACING_MULTIPLE = 10.0
FASTENER_CANDIDATE_MINIMUM_SPACING_MM = (
    FASTENER_CANDIDATE_OUTSIDE_THREAD_DIAMETER_MM
    * FASTENER_CANDIDATE_PREDRILLED_SPACING_MULTIPLE
)
FASTENER_CANDIDATE_PILOT_DIAMETER_MM = 7.0 / 64.0 * 25.4

# Palatine Moderne is a restrained Roman/Art-Deco language: the existing
# compressed D-arch remains the structural silhouette, while additive-only
# stepped keystones provide the visual hierarchy. They never cut a strap,
# bore, socket, locator, member, or cassette interface.
AESTHETIC_CONTRACT_ID = "r9_palatine_moderne_v1"
SUPPORT_KEYSTONE_TOP_WIDTH_MM = 24.0
SUPPORT_KEYSTONE_MIDDLE_WIDTH_MM = 16.0
SUPPORT_KEYSTONE_LOWER_WIDTH_MM = 10.0
SUPPORT_KEYSTONE_STEP_HEIGHT_MM = 4.0
FRONT_BEAM_RELIEF_OUTER_WIDTH_MM = 24.0
FRONT_BEAM_RELIEF_INNER_WIDTH_MM = 12.0
FRONT_BEAM_RELIEF_STEP_PROJECTION_MM = 1.0


@dataclass(frozen=True)
class OneBayPart:
    name: str
    installed_mesh: trimesh.Trimesh
    saved_print_mesh: trimesh.Trimesh
    installed_translation_mm: tuple[float, float, float]
    saved_orientation: str
    support_required: bool


@dataclass(frozen=True)
class PairIntersection:
    first_name: str
    second_name: str
    volume_mm3: float


@dataclass(frozen=True)
class OneBayEvidence:
    parts: tuple[OneBayPart, ...]
    pair_intersections: tuple[PairIntersection, ...]
    maximum_intersection_volume_mm3: float
    target_pose_collision_free: bool
    service_path_maximum_intersection_volume_mm3: float
    service_paths_collision_free: bool
    member_socket_clearance_per_face_mm: float
    deck_locator_clearance_per_face_mm: float
    bay_width_mm: float
    shelf_depth_mm: float
    shelf_height_mm: float
    mounting_bores_per_support: int
    mounting_bore_diameter_mm: float
    mounting_bore_drops_below_underside_mm: tuple[float, ...]
    maximum_flat_washer_outer_diameter_mm: float
    mounting_bores_clear_member_sockets: bool
    mounting_bore_center_spacing_mm: float
    fastener_candidate_product: str
    fastener_candidate_minimum_spacing_mm: float
    fastener_candidate_geometry_spacing_passes: bool
    aesthetic_contract_id: str
    tabletop_assembly_order: tuple[str, ...]
    no_load_boundary: str


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("One-bay geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("One-bay mesh contains non-finite coordinates")
    return mesh


def _copy(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    return _clean(mesh.copy())


def _box(
    extents: tuple[float, float, float],
    origin: tuple[float, float, float],
) -> trimesh.Trimesh:
    if any(
        isinstance(value, bool) or not math.isfinite(float(value)) or value <= 0.0
        for value in extents
    ):
        raise ValueError("Box extents must be positive finite numbers")
    result = trimesh.creation.box(extents=extents)
    result.apply_translation(np.asarray(origin) + np.asarray(extents) / 2.0)
    return _clean(result)


def _union(meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    result = trimesh.boolean.union(
        [_copy(mesh) for mesh in meshes], engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _difference(
    body: trimesh.Trimesh, cutters: Sequence[trimesh.Trimesh]
) -> trimesh.Trimesh:
    result = trimesh.boolean.difference(
        [_copy(body), *[_copy(cutter) for cutter in cutters]],
        engine="manifold",
        check_volume=True,
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _mounting_bore_profile() -> Polygon:
    """Return one support-free diamond containing the round screw envelope."""

    radius = MOUNTING_BORE_DIAMETER_MM / 2.0
    half = MOUNTING_BORE_DIAMOND_HALF_DIAGONAL_MM
    if half < radius * math.sqrt(2.0):
        raise ValueError("Mounting diamond does not contain the round clearance")
    profile = Polygon(((-half, 0.0), (0.0, half), (half, 0.0), (0.0, -half)))
    if not isinstance(profile, Polygon) or not profile.is_valid or profile.is_empty:
        raise ValueError("Mounting-bore profile is invalid")
    return profile


def _mounting_bore_cutters() -> tuple[trimesh.Trimesh, ...]:
    """Cut three wall-normal bores through one complete support strap."""

    q_length = support.WALL_STRAP_PROJECTION_MM + 2.0 * MOUNTING_BORE_Q_OVERRUN_MM
    cutters: list[trimesh.Trimesh] = []
    for drop in MOUNTING_BORE_DROPS_BELOW_UNDERSIDE_MM:
        source = trimesh.creation.extrude_polygon(
            _mounting_bore_profile(),
            height=q_length,
            engine="earcut",
        )
        # extrude_polygon emits (e, across-run, extrusion).  Relabel to the
        # support convention (q, e, across-run), then place the bore center.
        source.vertices = np.asarray(source.vertices, dtype=float)[:, (2, 0, 1)]
        source.vertices[:, 0] -= MOUNTING_BORE_Q_OVERRUN_MM
        source.vertices[:, 1] += support.WALL_STRAP_TOTAL_DROP_MM - drop
        source.vertices[:, 2] += MOUNTING_BORE_CENTER_RUN_MM
        cutters.append(_clean(source))
    return tuple(cutters)


def _support_socket_cutters(*, hand: str) -> tuple[trimesh.Trimesh, ...]:
    if hand not in ("left", "right"):
        raise ValueError("Support hand must be left or right")
    depth = MEMBER_TONGUE_LENGTH_MM + INTERFACE_CLEARANCE_PER_FACE_MM
    run_start = SUPPORT_WIDTH_MM - depth if hand == "left" else 0.0
    run_start += -INTERFACE_CLEARANCE_PER_FACE_MM if hand == "right" else 0.0
    run_depth = depth + INTERFACE_CLEARANCE_PER_FACE_MM
    q_size = MEMBER_TONGUE_DEPTH_MM + 2.0 * INTERFACE_CLEARANCE_PER_FACE_MM
    e_size = MEMBER_TONGUE_HEIGHT_MM + 2.0 * INTERFACE_CLEARANCE_PER_FACE_MM
    e_start = (
        support.WALL_STRAP_TOTAL_DROP_MM
        - MEMBER_HEIGHT_MM
        + (MEMBER_HEIGHT_MM - MEMBER_TONGUE_HEIGHT_MM) / 2.0
        - INTERFACE_CLEARANCE_PER_FACE_MM
    )
    rear_q = (
        (MEMBER_DEPTH_MM - MEMBER_TONGUE_DEPTH_MM) / 2.0
        - INTERFACE_CLEARANCE_PER_FACE_MM
    )
    front_q = (
        SHELF_DEPTH_MM
        - MEMBER_DEPTH_MM
        + (MEMBER_DEPTH_MM - MEMBER_TONGUE_DEPTH_MM) / 2.0
        - INTERFACE_CLEARANCE_PER_FACE_MM
    )
    return (
        _box((q_size, e_size, run_depth), (rear_q, e_start, run_start)),
        _box((q_size, e_size, run_depth), (front_q, e_start, run_start)),
    )


def _locator_bosses() -> tuple[trimesh.Trimesh, ...]:
    bosses: list[trimesh.Trimesh] = []
    for q_start in LOCATOR_BOSS_Y_MM:
        bosses.append(
            _box(
                (
                    LOCATOR_BOSS_DEPTH_MM,
                    LOCATOR_BOSS_PROTRUSION_MM + 0.4,
                    LOCATOR_BOSS_RUN_MM,
                ),
                (
                    q_start,
                    support.WALL_STRAP_TOTAL_DROP_MM - 0.4,
                    LOCATOR_BOSS_X_LOCAL_MM,
                ),
            )
        )
    return tuple(bosses)


def _support_keystone_insert() -> trimesh.Trimesh:
    """Return one additive, full-thickness stepped Roman keystone."""

    center_q = SHELF_DEPTH_MM / 2.0
    top_e = support.WALL_STRAP_TOTAL_DROP_MM - support.TOP_CHORD_MM
    step = SUPPORT_KEYSTONE_STEP_HEIGHT_MM
    profile = Polygon(
        (
            (center_q - SUPPORT_KEYSTONE_TOP_WIDTH_MM / 2.0, top_e + step),
            (center_q + SUPPORT_KEYSTONE_TOP_WIDTH_MM / 2.0, top_e + step),
            (center_q + SUPPORT_KEYSTONE_TOP_WIDTH_MM / 2.0, top_e),
            (center_q + SUPPORT_KEYSTONE_MIDDLE_WIDTH_MM / 2.0, top_e),
            (center_q + SUPPORT_KEYSTONE_MIDDLE_WIDTH_MM / 2.0, top_e - step),
            (center_q + SUPPORT_KEYSTONE_LOWER_WIDTH_MM / 2.0, top_e - step),
            (
                center_q + SUPPORT_KEYSTONE_LOWER_WIDTH_MM / 2.0,
                top_e - 2.0 * step,
            ),
            (
                center_q - SUPPORT_KEYSTONE_LOWER_WIDTH_MM / 2.0,
                top_e - 2.0 * step,
            ),
            (center_q - SUPPORT_KEYSTONE_LOWER_WIDTH_MM / 2.0, top_e - step),
            (center_q - SUPPORT_KEYSTONE_MIDDLE_WIDTH_MM / 2.0, top_e - step),
            (center_q - SUPPORT_KEYSTONE_MIDDLE_WIDTH_MM / 2.0, top_e),
            (center_q - SUPPORT_KEYSTONE_TOP_WIDTH_MM / 2.0, top_e),
        )
    )
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise ValueError("Palatine Moderne support keystone is invalid")
    mesh = trimesh.creation.extrude_polygon(
        profile,
        height=SUPPORT_WIDTH_MM,
        engine="earcut",
    )
    return _clean(mesh)


def build_compact_support_with_interfaces(*, hand: str) -> trimesh.Trimesh:
    """Build a handed support with sockets, bosses, and three printed bores."""

    core = support.build_compact_support_candidate()
    cut = _difference(
        core,
        (*_support_socket_cutters(hand=hand), *_mounting_bore_cutters()),
    )
    result = _union((cut, *_locator_bosses(), _support_keystone_insert()))
    if len(result.split(only_watertight=False)) != 1:
        raise ValueError("One-bay support must remain one connected body")
    return result


def build_left_compact_support() -> trimesh.Trimesh:
    return build_compact_support_with_interfaces(hand="left")


def build_right_compact_support() -> trimesh.Trimesh:
    return build_compact_support_with_interfaces(hand="right")


def _build_member() -> trimesh.Trimesh:
    body_start = MEMBER_TONGUE_LENGTH_MM
    body = _box(
        (INNER_MEMBER_LENGTH_MM, MEMBER_DEPTH_MM, MEMBER_HEIGHT_MM),
        (body_start, 0.0, 0.0),
    )
    tongue_y = (MEMBER_DEPTH_MM - MEMBER_TONGUE_DEPTH_MM) / 2.0
    tongue_z = (MEMBER_HEIGHT_MM - MEMBER_TONGUE_HEIGHT_MM) / 2.0
    left = _box(
        (MEMBER_TONGUE_LENGTH_MM + 0.4, MEMBER_TONGUE_DEPTH_MM, MEMBER_TONGUE_HEIGHT_MM),
        (0.0, tongue_y, tongue_z),
    )
    right = _box(
        (MEMBER_TONGUE_LENGTH_MM + 0.4, MEMBER_TONGUE_DEPTH_MM, MEMBER_TONGUE_HEIGHT_MM),
        (
            body_start + INNER_MEMBER_LENGTH_MM - 0.4,
            tongue_y,
            tongue_z,
        ),
    )
    return _union((body, left, right))


def build_rear_ledger() -> trimesh.Trimesh:
    return _build_member()


def build_front_beam() -> trimesh.Trimesh:
    body = _build_member()
    center_x = (MEMBER_TONGUE_LENGTH_MM + INNER_MEMBER_LENGTH_MM) / 2.0
    outer = _box(
        (
            FRONT_BEAM_RELIEF_OUTER_WIDTH_MM,
            FRONT_BEAM_RELIEF_STEP_PROJECTION_MM,
            MEMBER_HEIGHT_MM,
        ),
        (
            center_x - FRONT_BEAM_RELIEF_OUTER_WIDTH_MM / 2.0,
            MEMBER_DEPTH_MM,
            0.0,
        ),
    )
    inner = _box(
        (
            FRONT_BEAM_RELIEF_INNER_WIDTH_MM,
            FRONT_BEAM_RELIEF_STEP_PROJECTION_MM,
            MEMBER_HEIGHT_MM,
        ),
        (
            center_x - FRONT_BEAM_RELIEF_INNER_WIDTH_MM / 2.0,
            MEMBER_DEPTH_MM + FRONT_BEAM_RELIEF_STEP_PROJECTION_MM,
            0.0,
        ),
    )
    return _union((body, outer, inner))


def _cassette_towers() -> tuple[trimesh.Trimesh, ...]:
    towers: list[trimesh.Trimesh] = []
    x_starts = (LOCATOR_BOSS_X_LOCAL_MM - 2.0, BAY_WIDTH_MM - 20.0 - 2.0)
    for x_start in x_starts:
        for y_start in LOCATOR_BOSS_Y_MM:
            towers.append(
                _box(
                    (12.0, 8.0, SHELF_HEIGHT_MM - CASSETTE_SKIN_MM + 0.2),
                    (x_start, y_start - 2.0, 0.0),
                )
            )
    return tuple(towers)


def _cassette_pocket_cutters() -> tuple[trimesh.Trimesh, ...]:
    cutters: list[trimesh.Trimesh] = []
    x_starts = (
        LOCATOR_BOSS_X_LOCAL_MM - INTERFACE_CLEARANCE_PER_FACE_MM,
        BAY_WIDTH_MM
        - SUPPORT_WIDTH_MM
        + LOCATOR_BOSS_X_LOCAL_MM
        - INTERFACE_CLEARANCE_PER_FACE_MM,
    )
    for x_start in x_starts:
        for y_start in LOCATOR_BOSS_Y_MM:
            cutters.append(
                _box(
                    (
                        LOCATOR_BOSS_RUN_MM + 2.0 * INTERFACE_CLEARANCE_PER_FACE_MM,
                        LOCATOR_BOSS_DEPTH_MM
                        + 2.0 * INTERFACE_CLEARANCE_PER_FACE_MM,
                        LOCATOR_POCKET_DEPTH_MM + 0.2,
                    ),
                    (
                        x_start,
                        y_start - INTERFACE_CLEARANCE_PER_FACE_MM,
                        -0.2,
                    ),
                )
            )
    return tuple(cutters)


def build_shelf_cassette() -> trimesh.Trimesh:
    """Build one full-depth, open-bottom, three-web 160 mm cassette."""

    height_to_skin = SHELF_HEIGHT_MM - CASSETTE_SKIN_MM
    parts: list[trimesh.Trimesh] = [
        _box((BAY_WIDTH_MM, SHELF_DEPTH_MM, CASSETTE_SKIN_MM), (0.0, 0.0, height_to_skin)),
        _box((BAY_WIDTH_MM, CASSETTE_SKIN_MM, height_to_skin + 0.2), (0.0, 0.0, 0.0)),
        _box(
            (BAY_WIDTH_MM, CASSETTE_SKIN_MM, height_to_skin + 0.2),
            (0.0, SHELF_DEPTH_MM - CASSETTE_SKIN_MM, 0.0),
        ),
        _box((CASSETTE_SKIN_MM, SHELF_DEPTH_MM, height_to_skin + 0.2), (0.0, 0.0, 0.0)),
        _box(
            (CASSETTE_SKIN_MM, SHELF_DEPTH_MM, height_to_skin + 0.2),
            (BAY_WIDTH_MM - CASSETTE_SKIN_MM, 0.0, 0.0),
        ),
    ]
    web_pitch = BAY_WIDTH_MM / (CASSETTE_WEB_COUNT + 1)
    for index in range(1, CASSETTE_WEB_COUNT + 1):
        parts.append(
            _box(
                (CASSETTE_SKIN_MM, SHELF_DEPTH_MM, height_to_skin + 0.2),
                (index * web_pitch - CASSETTE_SKIN_MM / 2.0, 0.0, 0.0),
            )
        )
    body = _union((*parts, *_cassette_towers()))
    result = _difference(body, _cassette_pocket_cutters())
    if len(result.split(only_watertight=False)) != 1:
        raise ValueError("One-bay cassette must remain one connected body")
    return result


def _normalize(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    result = _copy(mesh)
    result.apply_translation(-result.bounds[0])
    return _clean(result)


def orient_support_for_print(
    mesh: trimesh.Trimesh, *, hand: str
) -> trimesh.Trimesh:
    """Keep each handed side socket open toward later layers, never bridged."""

    if hand == "left":
        return support.orient_broad_face_on_plate(mesh, face="minimum_z")
    if hand == "right":
        return support.orient_broad_face_on_plate(mesh, face="maximum_z")
    raise ValueError("Support hand must be left or right")


def orient_member_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Put the complete 112 x 16 mm footprint on the plate from layer one."""

    return _normalize(mesh)


def orient_cassette_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Put the finished shelf top on the plate; walls/webs then grow upward."""

    result = _copy(mesh)
    maximum = float(result.bounds[1, 2])
    result.vertices[:, 2] = maximum - result.vertices[:, 2]
    return _normalize(result)


def build_saved_one_bay_parts() -> dict[str, trimesh.Trimesh]:
    installed = {
        "r9_one_bay_left_compact_support": build_left_compact_support(),
        "r9_one_bay_right_compact_support": build_right_compact_support(),
        "r9_one_bay_rear_ledger": build_rear_ledger(),
        "r9_one_bay_front_beam": build_front_beam(),
        "r9_one_bay_shelf_cassette": build_shelf_cassette(),
    }
    return {
        name: (
            orient_support_for_print(mesh, hand="left")
            if name == "r9_one_bay_left_compact_support"
            else orient_support_for_print(mesh, hand="right")
            if name == "r9_one_bay_right_compact_support"
            else orient_member_for_print(mesh)
            if name.endswith(("rear_ledger", "front_beam"))
            else orient_cassette_for_print(mesh)
        )
        for name, mesh in installed.items()
    }


def _support_to_installed(mesh: trimesh.Trimesh, x_offset: float) -> trimesh.Trimesh:
    result = _copy(mesh)
    source = np.asarray(result.vertices, dtype=float).copy()
    result.vertices = source[:, (2, 0, 1)]
    result.apply_translation((x_offset, 0.0, 0.0))
    return _clean(result)


def build_installed_one_bay_parts() -> dict[str, trimesh.Trimesh]:
    rear = build_rear_ledger()
    rear.apply_translation(
        (SUPPORT_WIDTH_MM - MEMBER_TONGUE_LENGTH_MM, REAR_MEMBER_Y_MM, MEMBER_Z_MM)
    )
    front = build_front_beam()
    front.apply_translation(
        (SUPPORT_WIDTH_MM - MEMBER_TONGUE_LENGTH_MM, FRONT_MEMBER_Y_MM, MEMBER_Z_MM)
    )
    deck = build_shelf_cassette()
    deck.apply_translation((0.0, 0.0, support.WALL_STRAP_TOTAL_DROP_MM))
    return {
        "r9_one_bay_left_compact_support": _support_to_installed(build_left_compact_support(), 0.0),
        "r9_one_bay_right_compact_support": _support_to_installed(
            build_right_compact_support(), BAY_WIDTH_MM - SUPPORT_WIDTH_MM
        ),
        "r9_one_bay_rear_ledger": _clean(rear),
        "r9_one_bay_front_beam": _clean(front),
        "r9_one_bay_shelf_cassette": _clean(deck),
    }


def _intersection_volume(first: trimesh.Trimesh, second: trimesh.Trimesh) -> float:
    overlap = trimesh.boolean.intersection(
        [_copy(first), _copy(second)], engine="manifold", check_volume=False
    )
    if overlap is None:
        return 0.0
    if isinstance(overlap, list):
        return float(sum(abs(item.volume) for item in overlap if not item.is_empty))
    if overlap.is_empty:
        return 0.0
    return float(abs(overlap.volume))


def _service_path_maximum(installed: dict[str, trimesh.Trimesh]) -> float:
    """Sample vertical installation/removal for both members and the cassette."""

    maximum = 0.0
    support_names = (
        "r9_one_bay_left_compact_support",
        "r9_one_bay_right_compact_support",
    )
    member_names = ("r9_one_bay_rear_ledger", "r9_one_bay_front_beam")
    for moving_name in member_names:
        for lift in np.linspace(12.0, 0.0, 13):
            moving = _copy(installed[moving_name])
            moving.apply_translation((0.0, 0.0, float(lift)))
            for fixed_name in support_names:
                maximum = max(
                    maximum,
                    _intersection_volume(moving, installed[fixed_name]),
                )
    for lift in np.linspace(12.0, 0.0, 13):
        moving = _copy(installed["r9_one_bay_shelf_cassette"])
        moving.apply_translation((0.0, 0.0, float(lift)))
        for fixed_name in (*support_names, *member_names):
            maximum = max(
                maximum,
                _intersection_volume(moving, installed[fixed_name]),
            )
    return float(maximum)


def build_one_bay_evidence() -> OneBayEvidence:
    installed = build_installed_one_bay_parts()
    saved = build_saved_one_bay_parts()
    translations = {
        "r9_one_bay_left_compact_support": (0.0, 0.0, 0.0),
        "r9_one_bay_right_compact_support": (BAY_WIDTH_MM - SUPPORT_WIDTH_MM, 0.0, 0.0),
        "r9_one_bay_rear_ledger": (
            SUPPORT_WIDTH_MM - MEMBER_TONGUE_LENGTH_MM,
            REAR_MEMBER_Y_MM,
            MEMBER_Z_MM,
        ),
        "r9_one_bay_front_beam": (
            SUPPORT_WIDTH_MM - MEMBER_TONGUE_LENGTH_MM,
            FRONT_MEMBER_Y_MM,
            MEMBER_Z_MM,
        ),
        "r9_one_bay_shelf_cassette": (0.0, 0.0, support.WALL_STRAP_TOTAL_DROP_MM),
    }
    orientation = {
        "r9_one_bay_left_compact_support": "broad_minimum_run_face_on_plate",
        "r9_one_bay_right_compact_support": "broad_maximum_run_face_on_plate",
        "r9_one_bay_rear_ledger": "complete_112x16_member_footprint_on_plate",
        "r9_one_bay_front_beam": "complete_112x16_member_footprint_on_plate",
        "r9_one_bay_shelf_cassette": "finished_top_face_on_plate",
    }
    parts = tuple(
        OneBayPart(
            name=name,
            installed_mesh=installed[name],
            saved_print_mesh=saved[name],
            installed_translation_mm=translations[name],
            saved_orientation=orientation[name],
            support_required=False,
        )
        for name in installed
    )
    intersections: list[PairIntersection] = []
    names = tuple(installed)
    for first_index, first_name in enumerate(names):
        for second_name in names[first_index + 1 :]:
            intersections.append(
                PairIntersection(
                    first_name=first_name,
                    second_name=second_name,
                    volume_mm3=_intersection_volume(
                        installed[first_name], installed[second_name]
                    ),
                )
            )
    maximum = max((item.volume_mm3 for item in intersections), default=0.0)
    service_maximum = _service_path_maximum(installed)
    socket_bore_maximum = max(
        (
            _intersection_volume(socket, bore)
            for hand in ("left", "right")
            for socket in _support_socket_cutters(hand=hand)
            for bore in _mounting_bore_cutters()
        ),
        default=0.0,
    )
    bore_spacings = tuple(
        right - left
        for left, right in zip(
            MOUNTING_BORE_DROPS_BELOW_UNDERSIDE_MM,
            MOUNTING_BORE_DROPS_BELOW_UNDERSIDE_MM[1:],
        )
    )
    minimum_bore_spacing = min(bore_spacings)
    return OneBayEvidence(
        parts=parts,
        pair_intersections=tuple(intersections),
        maximum_intersection_volume_mm3=maximum,
        target_pose_collision_free=maximum <= COLLISION_TOLERANCE_MM3,
        service_path_maximum_intersection_volume_mm3=service_maximum,
        service_paths_collision_free=(
            service_maximum <= COLLISION_TOLERANCE_MM3
        ),
        member_socket_clearance_per_face_mm=INTERFACE_CLEARANCE_PER_FACE_MM,
        deck_locator_clearance_per_face_mm=INTERFACE_CLEARANCE_PER_FACE_MM,
        bay_width_mm=BAY_WIDTH_MM,
        shelf_depth_mm=SHELF_DEPTH_MM,
        shelf_height_mm=SHELF_HEIGHT_MM,
        mounting_bores_per_support=len(MOUNTING_BORE_DROPS_BELOW_UNDERSIDE_MM),
        mounting_bore_diameter_mm=MOUNTING_BORE_DIAMETER_MM,
        mounting_bore_drops_below_underside_mm=(
            MOUNTING_BORE_DROPS_BELOW_UNDERSIDE_MM
        ),
        maximum_flat_washer_outer_diameter_mm=(
            MAXIMUM_FLAT_WASHER_OUTER_DIAMETER_MM
        ),
        mounting_bores_clear_member_sockets=(
            socket_bore_maximum <= COLLISION_TOLERANCE_MM3
        ),
        mounting_bore_center_spacing_mm=minimum_bore_spacing,
        fastener_candidate_product=FASTENER_CANDIDATE_PRODUCT,
        fastener_candidate_minimum_spacing_mm=(
            FASTENER_CANDIDATE_MINIMUM_SPACING_MM
        ),
        fastener_candidate_geometry_spacing_passes=(
            minimum_bore_spacing
            >= FASTENER_CANDIDATE_MINIMUM_SPACING_MM - 1.0e-9
        ),
        aesthetic_contract_id=AESTHETIC_CONTRACT_ID,
        tabletop_assembly_order=(
            "place both handed compact supports upright on a padded table",
            "lower the rear ledger vertically into both rear top-open sockets",
            "lower the front beam vertically into both front top-open sockets",
            "lower the shelf cassette vertically onto all four locator bosses",
            "inspect the assembled bay unloaded; reverse these steps to remove",
        ),
        no_load_boundary=(
            "tabletop fit-and-appearance prototype with candidate printed wall "
            "bores only; no wall-install authorization, approved anchor, stored "
            "load, structural rating, or production authorization"
        ),
    )


def print_envelopes() -> dict[str, support.PrintEnvelope]:
    return {
        name: support.print_envelope_with_margins(mesh)
        for name, mesh in build_saved_one_bay_parts().items()
    }
