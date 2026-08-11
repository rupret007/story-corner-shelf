#!/usr/bin/env python3
"""Additive, inward-facing cable receiver for the R10 far-left bookend.

The candidate starts with :func:`lincoln_geometry.build_support_candidate` and
never cuts that source mesh.  A frozen-R9-compatible two-socket receiver is
rigidly mapped to the positive run face (the inward face of support S0), joined
with positive overlap, and supported in the saved wall-face-down orientation by
an additive 45-degree print ramp.  The ramp starts beyond every wall-bore
cutter and ends below the cassette/support-retainer service plane.

Installed source axes are ``q/e/run``: wall-to-front projection, elevation,
and wall run.  Positive run is inward from the first wall's far-left outer
bookend.  Receiver-local axes remain the R9 convention: X across the receiver,
Y outward from its face, and Z upward.  Therefore receiver-local positive Y
maps to source positive run.

This module emits qualification articles only.  It creates no load rating,
wall-installation authorization, drilling schedule, field-clearance claim, or
structural credit for the cable system.  Saved-mesh and analytic checks are not
a substitute for slicer Preview, printed fit tests, cable snag tests, or field
door/trim/outlet measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import sys
from typing import Iterable
import warnings

import numpy as np
from shapely.geometry import Polygon
import trimesh


R10_ROOT = Path(__file__).resolve().parent
R9_ROOT = R10_ROOT.parent / "r9"
if str(R9_ROOT) not in sys.path:
    sys.path.insert(0, str(R9_ROOT))

try:  # Package import and direct unittest discovery are both supported.
    from . import capacity_study, lincoln_geometry
except ImportError:  # pragma: no cover - direct unittest discovery path
    import capacity_study  # type: ignore[no-redef]
    import lincoln_geometry  # type: ignore[no-redef]

import cable_geometry  # type: ignore[import-not-found]  # noqa: E402


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PHYSICAL_QUALIFICATION_COMPLETE = False
WALL_INSTALLATION_AUTHORIZED = False
FIELD_CLEARANCE_QUALIFIED = False
DOOR_TRIM_OUTLET_AND_CABLE_LOOP_CLEARANCE_QUALIFIED = False
STRUCTURAL_OR_SHELF_LOAD_CREDIT = False
SUPPORT_CORE_SUBTRACTION_ALLOWED = False
PRINTED_MATERIAL = lincoln_geometry.PRINTED_MATERIAL
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0

EXPECTED_R9_CABLE_GEOMETRY_SHA256 = (
    "e414b7bdeff0c0140f6621957f7d807ac291ce433d75a65e02ac6f5b5dd6a864"
)
EXPECTED_R9_BOOKEND_ATTACHMENT_SHA256 = (
    "66f8ae974fd5fc6ab21a1b95f31b7550ab691c3969a179d69b2e53525741ee7e"
)

FIRST_WALL_ACTIVE_SUPPORT_INDICES = (0,)
FIRST_WALL_SUPPORT_COUNT = 7
FIRST_WALL_BAY_COUNT = 6
SOCKETS_PER_BOOKEND = 2
INWARD_FACING = True
INTERMEDIATE_SUPPORT_CABLE_HARDWARE_ALLOWED = False
CORNER_CABLE_HARDWARE_ALLOWED = False

SUPPORT_RUN_WIDTH_MM = 31.75
SUPPORT_WALL_CHORD_MM = 19.05
SUPPORT_TOTAL_DROP_MM = 158.75
OUTER_BOOKEND_VISIBLE_CORBEL_DROP_MM = 120.65
OUTER_EMPHASIS_LOW_E_MM = (
    SUPPORT_TOTAL_DROP_MM - OUTER_BOOKEND_VISIBLE_CORBEL_DROP_MM
)
OUTER_EMPHASIS_RUN_INSET_MM = 0.4
OUTER_EMPHASIS_STRUCTURAL_CREDIT = False

SOCKET_CLEARANCE_PER_FACE_MM = 0.4
SOCKET_SERVICE_LIFT_MM = 8.0
SERVICE_PATH_INCREMENT_MM = 1.0
SERVICE_OUTWARD_APPROACH_MM = 6.0

# The 36 x 62 x 8.8 mm R9 receiver is placed on S0's positive-run face.
# q=32 keeps every addition at least 11.95 mm beyond the 19.05 mm wall chord.
# e=90..152 leaves 6.75 mm below the shelf underside and 10.75 mm below the
# bay-local support-retainer service plane.
RECEIVER_Q_MIN_MM = 32.0
RECEIVER_E_MIN_MM = 90.0
RECEIVER_RUN_OVERLAP_MM = 0.4
RECEIVER_RUN_BACK_MM = SUPPORT_RUN_WIDTH_MM - RECEIVER_RUN_OVERLAP_MM
RECEIVER_Q_MAX_MM = RECEIVER_Q_MIN_MM + cable_geometry.RAIL_WIDTH_MM
RECEIVER_E_MAX_MM = RECEIVER_E_MIN_MM + cable_geometry.RAIL_HEIGHT_MM
RECEIVER_RUN_FRONT_MM = RECEIVER_RUN_BACK_MM + cable_geometry.RAIL_THICKNESS_MM
SOCKET_CAVITY_NEAREST_CORE_RUN_MM = (
    RECEIVER_RUN_BACK_MM + cable_geometry.UNINTERRUPTED_BACK_WEB_MM
)

# In the saved orientation source q is print Z.  The ramp grows the exact
# 8.4 mm receiver reveal over 8.4 mm of print height (45 degrees), then overlaps
# the receiver for 0.4 mm.  Its inner 0.4 mm remains fused to the source side.
INWARD_REVEAL_BEYOND_SOURCE_MM = (
    RECEIVER_RUN_FRONT_MM - SUPPORT_RUN_WIDTH_MM
)
PRINT_RAMP_Q_START_MM = RECEIVER_Q_MIN_MM - INWARD_REVEAL_BEYOND_SOURCE_MM
PRINT_RAMP_Q_OVERLAP_MM = 0.4
PRINT_RAMP_Q_END_MM = RECEIVER_Q_MIN_MM + PRINT_RAMP_Q_OVERLAP_MM
PRINT_RAMP_MAX_NEW_REVEAL_PER_02_LAYER_MM = 0.2

FIRST_WALL_BOOKEND_PART_NAME = (
    "r10_first_wall_s0_inward_two_socket_additive_bookend_candidate"
)
FIRST_WALL_BLANK_0_PART_NAME = "r10_first_wall_socket_0_flush_blank"
FIRST_WALL_BLANK_1_PART_NAME = "r10_first_wall_socket_1_flush_blank"
FIRST_WALL_COMB_PART_NAME = "r10_first_wall_multi_cable_comb_hook"

GEOMETRY_EPSILON = 1.0e-7
CORE_CONTAINMENT_NUMERICAL_TOLERANCE_MM3 = 1.0e-5


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if _sha256(Path(cable_geometry.__file__).resolve()) != EXPECTED_R9_CABLE_GEOMETRY_SHA256:
    raise RuntimeError("Frozen R9 cable geometry changed before R10 port")
if _sha256(R9_ROOT / "bookend_attachment.py") != EXPECTED_R9_BOOKEND_ATTACHMENT_SHA256:
    raise RuntimeError("Frozen R9 bookend attachment changed before R10 port")

_CONFIG = capacity_study.load_config()
capacity_study.validate_config(_CONFIG)
_CABLE_CONFIG = _CONFIG["printed_arcade"]["cable_system"]
_ROLES = tuple(_CONFIG["field_reference"]["support_roles_left_to_right"])
if tuple(_CABLE_CONFIG["active_first_wall_support_indices"]) != (
    FIRST_WALL_ACTIVE_SUPPORT_INDICES
):
    raise ValueError("R10 first-wall cable receiver must remain S0-only")
if _CABLE_CONFIG["sockets_per_bookend"] != SOCKETS_PER_BOOKEND:
    raise ValueError("R10 outer bookend must retain exactly two sockets")
if _CABLE_CONFIG["inward_facing"] is not INWARD_FACING:
    raise ValueError("R10 S0 cable sockets must face inward")
if _CABLE_CONFIG["allowed_on_intermediate_supports"] is not False:
    raise ValueError("R10 intermediate supports must remain cable-hardware free")
if _CABLE_CONFIG["allowed_at_inside_corner"] is not False:
    raise ValueError("R10 inside-corner hardware must remain forbidden")
if _ROLES[0] != "outer_bookend_with_cable_receiver":
    raise ValueError("R10 S0 role no longer identifies the cable bookend")
if len(_ROLES) != FIRST_WALL_SUPPORT_COUNT:
    raise ValueError("R10 first-wall support count drifted")

for actual, expected, name in (
    (lincoln_geometry.SUPPORT_RUN_WIDTH_MM, SUPPORT_RUN_WIDTH_MM, "run width"),
    (lincoln_geometry.SUPPORT_WALL_CHORD_MM, SUPPORT_WALL_CHORD_MM, "wall chord"),
    (lincoln_geometry.SUPPORT_TOTAL_DROP_MM, SUPPORT_TOTAL_DROP_MM, "strap drop"),
    (
        float(_CONFIG["printed_arcade"]["outer_bookend_visible_corbel_drop_mm"]),
        OUTER_BOOKEND_VISIBLE_CORBEL_DROP_MM,
        "outer-bookend visible drop",
    ),
):
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1.0e-9):
        raise ValueError(f"R10 support {name} drifted from the cable port")


@dataclass(frozen=True)
class CableBookendCandidate:
    support_index: int
    part_name: str
    source_support: trimesh.Trimesh
    additive_outer_emphasis: trimesh.Trimesh
    mapped_receiver: trimesh.Trimesh
    additive_print_ramp: trimesh.Trimesh
    fused_body: trimesh.Trimesh
    receiver_to_support: np.ndarray
    inward_axis: str


@dataclass(frozen=True)
class CorePreservationEvidence:
    source_digest_before: str
    source_digest_after: str
    source_volume_mm3: float
    containment_numerical_tolerance_mm3: float
    outer_emphasis_source_overlap_mm3: float
    receiver_source_overlap_mm3: float
    ramp_source_overlap_mm3: float
    receiver_ramp_overlap_mm3: float
    missing_source_core_volume_mm3: float
    source_core_preserved: bool
    additive_only: bool


@dataclass(frozen=True)
class ServiceClearanceEvidence:
    bore_addition_intersection_mm3: tuple[float, ...]
    retainer_service_intersection_mm3: tuple[float, ...]
    minimum_bore_q_gap_mm: float
    minimum_retainer_e_gap_mm: float
    wall_bores_clear: bool
    both_support_retainer_service_lanes_clear: bool


@dataclass(frozen=True)
class MappedServicePath:
    module_name: str
    station_index: int
    insertion_approach: tuple[trimesh.Trimesh, ...]
    gravity_drop: tuple[trimesh.Trimesh, ...]
    removal_lift: tuple[trimesh.Trimesh, ...]
    removal_outward: tuple[trimesh.Trimesh, ...]
    increment_mm: float


@dataclass(frozen=True)
class ModuleServiceEvidence:
    module_name: str
    station_index: int
    increment_mm: float
    insertion_sample_count: int
    drop_sample_count: int
    lift_sample_count: int
    outward_sample_count: int
    insertion_maximum_intersection_mm3: float
    drop_maximum_intersection_mm3: float
    lift_maximum_intersection_mm3: float
    outward_maximum_intersection_mm3: float
    removal_is_exact_reverse: bool
    collision_free: bool


@dataclass(frozen=True)
class SavedBookendPrintEvidence:
    part_name: str
    orientation_id: str
    support_required: bool
    sampled_layer_height_mm: float
    disconnected_layer_indices: tuple[int, ...]
    first_layer_contact_area_mm2: float
    maximum_new_reveal_per_02_layer_mm: float
    body_count: int
    watertight: bool
    winding_consistent: bool
    envelope: lincoln_geometry.PrintEnvelope


@dataclass(frozen=True)
class CableBookendEvidence:
    core: CorePreservationEvidence
    clearance: ServiceClearanceEvidence
    module_service: tuple[ModuleServiceEvidence, ...]
    saved_print: SavedBookendPrintEvidence
    active_first_wall_support_indices: tuple[int, ...]
    sockets_per_bookend: int
    inward_facing: bool
    intermediate_support_hardware_allowed: bool
    corner_hardware_allowed: bool
    field_clearance_qualified: bool
    outer_visible_corbel_emphasis_mm: float
    outer_emphasis_structural_credit: bool
    rated_load_kg: float
    rated_load_lb: float
    wall_installation_authorized: bool
    release_blockers: tuple[str, ...]


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("Cable-bookend geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("Cable-bookend geometry contains non-finite vertices")
    return mesh


def _copy(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty Trimesh is required")
    return _clean(mesh.copy())


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


def _union(meshes: Iterable[trimesh.Trimesh]) -> trimesh.Trimesh:
    sources = tuple(_copy(mesh) for mesh in meshes)
    if not sources:
        raise ValueError("At least one mesh is required for union")
    result = trimesh.boolean.union(
        list(sources), engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _mesh_fingerprint(mesh: trimesh.Trimesh) -> str:
    source = _copy(mesh)
    digest = hashlib.sha256()
    digest.update(np.asarray(source.vertices, dtype="<f8").tobytes())
    digest.update(np.asarray(source.faces, dtype="<i8").tobytes())
    return digest.hexdigest()


def _positive_intersection_volume(
    first: trimesh.Trimesh, second: trimesh.Trimesh
) -> float:
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
    return 0.0 if volume <= 1.0e-10 else volume


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
    return (
        0.0
        if volume <= CORE_CONTAINMENT_NUMERICAL_TOLERANCE_MM3
        else volume
    )


def _box(
    bounds: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
) -> trimesh.Trimesh:
    if any(high <= low for low, high in bounds):
        raise ValueError("Every box bound must have positive extent")
    extents = np.asarray([high - low for low, high in bounds], dtype=float)
    center = np.asarray([(low + high) / 2.0 for low, high in bounds], dtype=float)
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    return _clean(mesh)


def _transformed(mesh: trimesh.Trimesh, matrix: np.ndarray) -> trimesh.Trimesh:
    transform = np.asarray(matrix, dtype=float)
    if transform.shape != (4, 4) or not np.isfinite(transform).all():
        raise ValueError("A finite 4 x 4 transform is required")
    result = _copy(mesh)
    result.apply_transform(transform)
    return _clean(result)


def receiver_allowed_on_first_wall_support(support_index: int) -> bool:
    if isinstance(support_index, bool) or not isinstance(support_index, int):
        raise ValueError("support_index must be an integer")
    if support_index < 0 or support_index >= FIRST_WALL_SUPPORT_COUNT:
        raise IndexError("support_index lies outside the seven-support first wall")
    return support_index in FIRST_WALL_ACTIVE_SUPPORT_INDICES


def receiver_to_support_transform() -> np.ndarray:
    """Map R9 receiver local XYZ to R10 support q/e/run.

    Local +Y (the module approach/removal direction) becomes source +run, so
    both sockets face inward from far-left support S0.
    """

    matrix = np.zeros((4, 4), dtype=float)
    matrix[0, 0] = 1.0  # receiver X -> support q
    matrix[1, 2] = 1.0  # receiver Z -> support e
    matrix[2, 1] = 1.0  # receiver outward Y -> inward support run
    matrix[0, 3] = RECEIVER_Q_MIN_MM
    matrix[1, 3] = RECEIVER_E_MIN_MM
    matrix[2, 3] = RECEIVER_RUN_BACK_MM
    matrix[3, 3] = 1.0
    return matrix


def map_receiver_to_support(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    return _transformed(mesh, receiver_to_support_transform())


def _build_additive_print_ramp() -> trimesh.Trimesh:
    """Build the 45-degree side reveal under the inward receiver."""

    profile = Polygon(
        (
            (PRINT_RAMP_Q_START_MM, RECEIVER_RUN_BACK_MM),
            (PRINT_RAMP_Q_START_MM, SUPPORT_RUN_WIDTH_MM),
            (RECEIVER_Q_MIN_MM, RECEIVER_RUN_FRONT_MM),
            (PRINT_RAMP_Q_END_MM, RECEIVER_RUN_FRONT_MM),
            (PRINT_RAMP_Q_END_MM, RECEIVER_RUN_BACK_MM),
        )
    )
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise ValueError("Cable-bookend print ramp profile is invalid")
    ramp = trimesh.creation.extrude_polygon(
        profile, height=cable_geometry.RAIL_HEIGHT_MM, engine="earcut"
    )
    old = np.asarray(ramp.vertices, dtype=float).copy()
    # Extrusion source axes are q/run/e; installed support axes are q/e/run.
    ramp.vertices = old[:, (0, 2, 1)]
    ramp.fix_normals(multibody=True)
    ramp.apply_translation((0.0, RECEIVER_E_MIN_MM, 0.0))
    return _clean(ramp)


def _build_additive_outer_emphasis() -> trimesh.Trimesh:
    """Add the stepped 120.65 mm S0 silhouette without thinning its core.

    The profile overlaps the untouched wall strap only below e=72 mm, leaving
    3.875 mm to the nearest middle-bore edge.  Its upper return grows at 45
    degrees in the wall-face-down print orientation.
    """

    profile = Polygon(
        (
            (15.05, OUTER_EMPHASIS_LOW_E_MM),
            (24.0, OUTER_EMPHASIS_LOW_E_MM),
            (24.0, 46.0),
            (28.0, 46.0),
            (28.0, 56.0),
            (32.0, 56.0),
            (32.0, 68.0),
            (38.1, 82.55),
            (30.95, 82.55),
            (20.4, 72.0),
            (15.05, 72.0),
        )
    )
    if not profile.is_valid or profile.is_empty or profile.area <= 0.0:
        raise ValueError("R10 outer-bookend emphasis profile is invalid")
    emphasis = trimesh.creation.extrude_polygon(
        profile,
        height=SUPPORT_RUN_WIDTH_MM - 2.0 * OUTER_EMPHASIS_RUN_INSET_MM,
        engine="earcut",
    )
    emphasis.apply_translation((0.0, 0.0, OUTER_EMPHASIS_RUN_INSET_MM))
    return _clean(emphasis)


def build_first_wall_left_cable_bookend() -> CableBookendCandidate:
    """Fuse one additive two-socket receiver to structural source support S0."""

    source = lincoln_geometry.build_support_candidate()
    before = _mesh_fingerprint(source)
    emphasis = _build_additive_outer_emphasis()
    receiver = map_receiver_to_support(
        cable_geometry.build_two_socket_outer_bookend_rail_fit_coupon(
            clearance_per_face_mm=SOCKET_CLEARANCE_PER_FACE_MM
        )
    )
    ramp = _build_additive_print_ramp()
    body = _one_body(
        _union((source, emphasis, receiver, ramp)), "R10 S0 cable bookend"
    )
    if _mesh_fingerprint(source) != before:
        raise AssertionError("Cable-bookend union mutated its R10 source support")
    return CableBookendCandidate(
        support_index=0,
        part_name=FIRST_WALL_BOOKEND_PART_NAME,
        source_support=source,
        additive_outer_emphasis=emphasis,
        mapped_receiver=receiver,
        additive_print_ramp=ramp,
        fused_body=body,
        receiver_to_support=receiver_to_support_transform(),
        inward_axis="+support_run",
    )


def build_flush_blank_module() -> trimesh.Trimesh:
    """Return an exact-geometry R9-compatible flush blank."""

    return _copy(cable_geometry.build_flush_blank_module())


def build_multi_cable_comb_hook_module() -> trimesh.Trimesh:
    """Return an exact-geometry R9-compatible three-position comb/hook."""

    return _copy(cable_geometry.build_multi_cable_organizer_hook_module())


def core_preservation_evidence(
    candidate: CableBookendCandidate | None = None,
) -> CorePreservationEvidence:
    item = build_first_wall_left_cable_bookend() if candidate is None else candidate
    before = _mesh_fingerprint(item.source_support)
    emphasis_source = _positive_intersection_volume(
        item.additive_outer_emphasis, item.source_support
    )
    receiver_source = _positive_intersection_volume(
        item.mapped_receiver, item.source_support
    )
    ramp_source = _positive_intersection_volume(
        item.additive_print_ramp, item.source_support
    )
    receiver_ramp = _positive_intersection_volume(
        item.mapped_receiver, item.additive_print_ramp
    )
    missing = _missing_volume(item.source_support, item.fused_body)
    after = _mesh_fingerprint(item.source_support)
    preserved = bool(before == after and missing <= GEOMETRY_EPSILON)
    additive = bool(
        preserved
        and emphasis_source > GEOMETRY_EPSILON
        and receiver_source > GEOMETRY_EPSILON
        and ramp_source > GEOMETRY_EPSILON
        and receiver_ramp > GEOMETRY_EPSILON
    )
    return CorePreservationEvidence(
        source_digest_before=before,
        source_digest_after=after,
        source_volume_mm3=float(item.source_support.volume),
        containment_numerical_tolerance_mm3=(
            CORE_CONTAINMENT_NUMERICAL_TOLERANCE_MM3
        ),
        outer_emphasis_source_overlap_mm3=emphasis_source,
        receiver_source_overlap_mm3=receiver_source,
        ramp_source_overlap_mm3=ramp_source,
        receiver_ramp_overlap_mm3=receiver_ramp,
        missing_source_core_volume_mm3=missing,
        source_core_preserved=preserved,
        additive_only=additive,
    )


def _support_retainer_service_envelopes() -> tuple[trimesh.Trimesh, ...]:
    q_start = lincoln_geometry.SHELF_DEPTH_MM - lincoln_geometry.SUPPORT_RETAINER_DEPTH_MM
    # A full 136 mm removal translation puts the retainer completely beyond
    # the original 152.4 mm front edge.  One swept box conservatively covers
    # every intermediate front-insert / front-remove pose.
    q_end = lincoln_geometry.SHELF_DEPTH_MM + lincoln_geometry.SUPPORT_RETAINER_DEPTH_MM
    e_start = (
        lincoln_geometry.SUPPORT_TOTAL_DROP_MM
        + lincoln_geometry.CAPTURE_KEY_BASE_ABOVE_SHELF_UNDERSIDE_MM
    )
    e_end = e_start + lincoln_geometry.SUPPORT_RETAINER_HEIGHT_MM
    result: list[trimesh.Trimesh] = []
    for center in lincoln_geometry.CAPTURE_LUG_CENTERS_SOURCE_RUN_MM:
        result.append(
            _box(
                (
                    (q_start, q_end),
                    (e_start, e_end),
                    (
                        center - lincoln_geometry.SUPPORT_RETAINER_RUN_MM / 2.0,
                        center + lincoln_geometry.SUPPORT_RETAINER_RUN_MM / 2.0,
                    ),
                )
            )
        )
    return tuple(result)


def service_clearance_evidence(
    candidate: CableBookendCandidate | None = None,
) -> ServiceClearanceEvidence:
    item = build_first_wall_left_cable_bookend() if candidate is None else candidate
    additions = _union(
        (
            item.additive_outer_emphasis,
            item.mapped_receiver,
            item.additive_print_ramp,
        )
    )
    cutters = lincoln_geometry._wall_bore_cutters()
    bore_intersections = tuple(
        _positive_intersection_volume(additions, cutter) for cutter in cutters
    )
    retainer_envelopes = _support_retainer_service_envelopes()
    retainer_intersections = tuple(
        _positive_intersection_volume(additions, envelope)
        for envelope in retainer_envelopes
    )
    minimum_bore_gap = float(
        min(item.mapped_receiver.bounds[0, 0], item.additive_print_ramp.bounds[0, 0])
        - max(cutter.bounds[1, 0] for cutter in cutters)
    )
    minimum_retainer_gap = float(
        min(envelope.bounds[0, 1] for envelope in retainer_envelopes)
        - additions.bounds[1, 1]
    )
    return ServiceClearanceEvidence(
        bore_addition_intersection_mm3=bore_intersections,
        retainer_service_intersection_mm3=retainer_intersections,
        minimum_bore_q_gap_mm=minimum_bore_gap,
        minimum_retainer_e_gap_mm=minimum_retainer_gap,
        wall_bores_clear=(
            minimum_bore_gap > 0.0
            and all(volume <= GEOMETRY_EPSILON for volume in bore_intersections)
        ),
        both_support_retainer_service_lanes_clear=(
            minimum_retainer_gap > 0.0
            and all(
                volume <= GEOMETRY_EPSILON for volume in retainer_intersections
            )
        ),
    )


def _map_local_pose_to_support(
    module: trimesh.Trimesh, local_pose: np.ndarray
) -> trimesh.Trimesh:
    return map_receiver_to_support(_transformed(module, local_pose))


def mapped_module_service_path(
    module: trimesh.Trimesh,
    *,
    module_name: str,
    station_index: int,
    increment_mm: float = SERVICE_PATH_INCREMENT_MM,
) -> MappedServicePath:
    if module_name not in ("flush_blank", "multi_cable_comb_hook"):
        raise ValueError("module_name must identify the blank or comb/hook")
    path = cable_geometry.service_path_transforms(
        station_index,
        increment_mm=increment_mm,
        outward_approach_mm=SERVICE_OUTWARD_APPROACH_MM,
    )

    def map_all(transforms: tuple[np.ndarray, ...]) -> tuple[trimesh.Trimesh, ...]:
        return tuple(_map_local_pose_to_support(module, pose) for pose in transforms)

    return MappedServicePath(
        module_name=module_name,
        station_index=station_index,
        insertion_approach=map_all(path.insertion_approach),
        gravity_drop=map_all(path.gravity_drop),
        removal_lift=map_all(path.removal_lift),
        removal_outward=map_all(path.removal_outward),
        increment_mm=path.increment_mm,
    )


def _maximum_collision(
    body: trimesh.Trimesh, poses: tuple[trimesh.Trimesh, ...]
) -> float:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return max(
            (_positive_intersection_volume(body, pose) for pose in poses),
            default=0.0,
        )


def module_service_evidence(
    candidate: CableBookendCandidate | None = None,
) -> tuple[ModuleServiceEvidence, ...]:
    item = build_first_wall_left_cable_bookend() if candidate is None else candidate
    modules = (
        ("flush_blank", build_flush_blank_module()),
        ("multi_cable_comb_hook", build_multi_cable_comb_hook_module()),
    )
    result: list[ModuleServiceEvidence] = []
    for module_name, module in modules:
        for station_index in range(SOCKETS_PER_BOOKEND):
            path = mapped_module_service_path(
                module,
                module_name=module_name,
                station_index=station_index,
                increment_mm=SERVICE_PATH_INCREMENT_MM,
            )
            insertion_maximum = _maximum_collision(
                item.fused_body, path.insertion_approach
            )
            drop_maximum = _maximum_collision(item.fused_body, path.gravity_drop)
            # Removal is the exact reverse of the two collision-free forward
            # paths, so its maxima are identical without repeating 64 booleans.
            removal_is_reverse = bool(
                tuple(_mesh_fingerprint(mesh) for mesh in path.gravity_drop)
                == tuple(
                    _mesh_fingerprint(mesh) for mesh in reversed(path.removal_lift)
                )
                and tuple(
                    _mesh_fingerprint(mesh) for mesh in path.insertion_approach
                )
                == tuple(
                    _mesh_fingerprint(mesh)
                    for mesh in reversed(path.removal_outward)
                )
            )
            collision_free = bool(
                insertion_maximum <= GEOMETRY_EPSILON
                and drop_maximum <= GEOMETRY_EPSILON
                and removal_is_reverse
            )
            result.append(
                ModuleServiceEvidence(
                    module_name=module_name,
                    station_index=station_index,
                    increment_mm=path.increment_mm,
                    insertion_sample_count=len(path.insertion_approach),
                    drop_sample_count=len(path.gravity_drop),
                    lift_sample_count=len(path.removal_lift),
                    outward_sample_count=len(path.removal_outward),
                    insertion_maximum_intersection_mm3=insertion_maximum,
                    drop_maximum_intersection_mm3=drop_maximum,
                    lift_maximum_intersection_mm3=drop_maximum,
                    outward_maximum_intersection_mm3=insertion_maximum,
                    removal_is_exact_reverse=removal_is_reverse,
                    collision_free=collision_free,
                )
            )
    return tuple(result)


def orient_first_wall_bookend_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Use R10's wall-face-down A1 orientation; the ramp supports the rail."""

    return lincoln_geometry.orient_support_for_print(mesh)


def build_saved_cable_bookend_parts() -> dict[str, trimesh.Trimesh]:
    candidate = build_first_wall_left_cable_bookend()
    blank = cable_geometry.orient_module_broad_side_on_plate(
        build_flush_blank_module()
    )
    comb = cable_geometry.orient_module_broad_side_on_plate(
        build_multi_cable_comb_hook_module()
    )
    return {
        FIRST_WALL_BOOKEND_PART_NAME: orient_first_wall_bookend_for_print(
            candidate.fused_body
        ),
        FIRST_WALL_BLANK_0_PART_NAME: _copy(blank),
        FIRST_WALL_BLANK_1_PART_NAME: _copy(blank),
        FIRST_WALL_COMB_PART_NAME: _copy(comb),
    }


def saved_bookend_print_evidence(
    candidate: CableBookendCandidate | None = None,
    *,
    sampled_layer_height_mm: float = 0.2,
) -> SavedBookendPrintEvidence:
    item = build_first_wall_left_cable_bookend() if candidate is None else candidate
    saved = orient_first_wall_bookend_for_print(item.fused_body)
    report = cable_geometry.saved_layer_island_report(
        saved, layer_height_mm=sampled_layer_height_mm
    )
    return SavedBookendPrintEvidence(
        part_name=FIRST_WALL_BOOKEND_PART_NAME,
        orientation_id="wall_face_down_45deg_with_additive_inward_reveal_ramp",
        support_required=report.support_required,
        sampled_layer_height_mm=report.layer_height_mm,
        disconnected_layer_indices=report.island_layer_indices,
        first_layer_contact_area_mm2=report.first_layer_contact_area_mm2,
        maximum_new_reveal_per_02_layer_mm=(
            PRINT_RAMP_MAX_NEW_REVEAL_PER_02_LAYER_MM
        ),
        body_count=len(saved.split(only_watertight=False)),
        watertight=bool(saved.is_watertight),
        winding_consistent=bool(saved.is_winding_consistent),
        envelope=lincoln_geometry.print_envelope(saved),
    )


def build_evidence() -> CableBookendEvidence:
    candidate = build_first_wall_left_cable_bookend()
    core = core_preservation_evidence(candidate)
    clearance = service_clearance_evidence(candidate)
    service = module_service_evidence(candidate)
    saved = saved_bookend_print_evidence(candidate)
    return CableBookendEvidence(
        core=core,
        clearance=clearance,
        module_service=service,
        saved_print=saved,
        active_first_wall_support_indices=FIRST_WALL_ACTIVE_SUPPORT_INDICES,
        sockets_per_bookend=SOCKETS_PER_BOOKEND,
        inward_facing=INWARD_FACING,
        intermediate_support_hardware_allowed=(
            INTERMEDIATE_SUPPORT_CABLE_HARDWARE_ALLOWED
        ),
        corner_hardware_allowed=CORNER_CABLE_HARDWARE_ALLOWED,
        field_clearance_qualified=FIELD_CLEARANCE_QUALIFIED,
        outer_visible_corbel_emphasis_mm=OUTER_BOOKEND_VISIBLE_CORBEL_DROP_MM,
        outer_emphasis_structural_credit=OUTER_EMPHASIS_STRUCTURAL_CREDIT,
        rated_load_kg=RATED_LOAD_KG,
        rated_load_lb=RATED_LOAD_LB,
        wall_installation_authorized=WALL_INSTALLATION_AUTHORIZED,
        release_blockers=(
            "saved slicer Preview and first-article inspection remain open",
            "both printed sockets and both module types require ten physical service cycles",
            "door, trim, outlet, plug, cord-loop, snag, and human-access envelopes are unmeasured",
            "cable accessories carry zero shelf-load or structural credit",
        ),
    )


def build_cable_bookend_evidence() -> CableBookendEvidence:
    """Stable release-aggregator name for the complete fail-closed evidence."""

    return build_evidence()


__all__ = (
    "CableBookendCandidate",
    "CableBookendEvidence",
    "CorePreservationEvidence",
    "MappedServicePath",
    "ModuleServiceEvidence",
    "SavedBookendPrintEvidence",
    "ServiceClearanceEvidence",
    "build_evidence",
    "build_cable_bookend_evidence",
    "build_first_wall_left_cable_bookend",
    "build_flush_blank_module",
    "build_multi_cable_comb_hook_module",
    "build_saved_cable_bookend_parts",
    "core_preservation_evidence",
    "map_receiver_to_support",
    "mapped_module_service_path",
    "module_service_evidence",
    "orient_first_wall_bookend_for_print",
    "receiver_allowed_on_first_wall_support",
    "receiver_to_support_transform",
    "saved_bookend_print_evidence",
    "service_clearance_evidence",
)
