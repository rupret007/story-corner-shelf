#!/usr/bin/env python3
"""Qualification-only R8 integration for the D-frame, rail, and cable modules.

This module is deliberately an *interface wrapper*.  It imports the frozen
qualification seeds from :mod:`shelf_geometry` and :mod:`accessory_geometry`
without modifying either one:

* the D-frame structural core is copied unchanged and receives only four
  additive, external mushroom bosses;
* the separate rail receives rear keyhole channels in two outboard lanes,
  never in the accessory-socket back-web zone;
* every accessory receives a front-accessible, secondary PETG detent whose
  hook sits in an outboard rail recess after the gravity key has seated.

Coordinates in the installed assembly are ``x`` across the 36 mm rail,
``y`` out from the wall, and ``z`` upward.  Four external bosses mount the
rail 1 mm beyond the D-frame's 16 mm wall chord, leaving a clean debris and
root-transition gap.  Nothing here emits a wall bore, printed wall anchor,
load rating, or production authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal
import warnings

import numpy as np
from shapely.geometry import GeometryCollection, Polygon
import trimesh

import accessory_geometry as accessory
import shelf_geometry as shelf


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0
COLLISION_TOLERANCE_MM3 = 1.0e-5

# The source corbel spans 32 mm across the run; centring it within a 36 mm
# faceplate leaves a clean 2 mm reveal on each side.
DFRAME_RAIL_SIDE_REVEAL_MM = 2.0
DFRAME_BOSS_ROOT_Y_MM = shelf.CORBEL_WALL_CHORD_MM
RAIL_STANDOFF_MM = 1.0
RAIL_SEATED_Y_MM = DFRAME_BOSS_ROOT_Y_MM + RAIL_STANDOFF_MM
RAIL_SEATED_Z_MM = 48.0

# Mount bosses and rear keyhole channels.  The 160 mm D-frame provides a clean
# e=48..136 rail band.  A 4 mm rail lift and 8 mm accessory lift both remain
# below the top chord while the longer lower root preserves the true 16 mm web.
MOUNT_CLEARANCE_MM = 0.4
MOUNT_SERVICE_LIFT_MM = 4.0
MOUNT_APPROACH_MM = 2.4
# Keep each complete 4 mm mushroom head inside the D-frame's x=2..34 run
# faces.  The earlier 2.6/33.4 lanes left 1.4 mm head tips outside the core,
# creating isolated first/last layers in the required broad-face orientation.
MOUNT_BOSS_CENTER_X_MM = (4.0, 32.0)
# Both stems shift 1 mm toward the support centre.  The x=29.9 far-stem start
# therefore precedes its head's x=30.0 start, so the full head grows from
# deposited stem material without widening the retaining neck.  The 5/31 pair
# is invariant under the opposite-run x -> 36-x mirror.
MOUNT_STEM_CENTER_X_MM = (5.0, 31.0)
MOUNT_BOSS_CENTER_Z_MM = (12.0, 72.0)
MOUNT_STEM_WIDTH_MM = 2.2
MOUNT_STEM_HEIGHT_MM = 3.4
MOUNT_HEAD_WIDTH_MM = 4.0
MOUNT_HEAD_HEIGHT_MM = 5.0
MOUNT_HEAD_BACK_Y_MM = 1.2
MOUNT_HEAD_FRONT_Y_MM = 2.0
MOUNT_CAVITY_FRONT_Y_MM = accessory.UNINTERRUPTED_BACK_WEB_MM

# Accessory latch.  The flexure is deliberately outside the T-lug and its
# recess has 0.4 mm vertical clearance when seated, so it cannot carry the
# gravity reaction.  It only prevents an uncommanded upward service lift.
LATCH_CLEARANCE_MM = 0.4
LATCH_ANCHOR_X_BOUNDS_MM = (9.2, 12.4)
LATCH_ROOT_X_BOUNDS_MM = (10.4, 12.4)
LATCH_ROOT_Y_MM = 1.6
LATCH_ROOT_Z_MM = -7.4
LATCH_ARM_LENGTH_MM = 10.0
LATCH_ARM_THICKNESS_MM = 1.0
LATCH_SERVICE_DEFLECTION_MM = 1.6
LATCH_HOOK_X_BOUNDS_MM = (10.4, 12.4)
LATCH_HOOK_REAR_OFFSET_MM = 3.0
LATCH_HOOK_FRONT_OFFSET_MM = 0.4
LATCH_HOOK_HEIGHT_MM = 3.0
LATCH_RECESS_BACK_Y_MM = 7.0
LATCH_RECESS_FRONT_Y_MM = accessory.FACEPLATE_THICKNESS_MM + 0.05
MODULE_APPROACH_MM = 6.4
SERVICE_INCREMENT_MM = 0.4
FINAL_COIL_TIP_MAX_Z_MM = 13.0
RETAINED_MODULE_SAVED_ORIENTATION = "local_xy_bed_local_negative_z_build"
RETAINED_MODULE_PRINT_ROTATION_X_DEG = 180.0
BLANK_MINIMUM_FIRST_LAYER_BODY_CONTACT_MM2 = 64.0

# Frozen R8 reference counts.  Eligibility itself is topology-driven and also
# accepts later measured plans with at least one true interior support.
NOMINAL_SUPPORT_COUNTS = {"through": 9, "return": 5}
SupportRun = Literal["through", "return"]
LatchState = Literal["seated", "deflected"]


@dataclass(frozen=True)
class SupportEligibility:
    """Fail-closed decision for adding an accessory rail to one support."""

    run: str
    support_index: int
    support_count: int
    is_corner: bool
    eligible: bool
    reason: str


@dataclass(frozen=True)
class DFrameMountWrapper:
    """An untouched core plus its additive-boss, one-body wrapper."""

    eligibility: SupportEligibility
    source_core: trimesh.Trimesh
    installed_core: trimesh.Trimesh
    boss_parts: tuple[trimesh.Trimesh, ...]
    body: trimesh.Trimesh
    source_to_installed: np.ndarray
    mirrored: bool


@dataclass(frozen=True)
class CorePreservationReport:
    """Exact evidence that coordinate installation did not mutate the core."""

    source_volume_mm3: float
    installed_volume_mm3: float
    wrapper_volume_mm3: float
    volume_delta_mm3: float
    source_digest: str
    restored_digest: str
    vertex_face_bytes_identical: bool
    additive_only: bool


@dataclass(frozen=True)
class ServiceTransforms:
    """Deterministic install and exact reverse-removal transforms."""

    approach: tuple[np.ndarray, ...]
    insertion: np.ndarray
    drop: tuple[np.ndarray, ...]
    seated: np.ndarray
    removal_lift: tuple[np.ndarray, ...]
    removal_outward: tuple[np.ndarray, ...]
    increment_mm: float


@dataclass(frozen=True)
class LatchStrainProxy:
    """Small-deflection cantilever surface-strain comparison, not FEA."""

    arm_length_mm: float
    arm_thickness_mm: float
    tip_deflection_mm: float
    surface_strain: float
    below_three_percent: bool


@dataclass(frozen=True)
class LayerIslandReport:
    """Layer support classification for the declared retained-part build."""

    layer_height_mm: float
    sampled_layer_count: int
    first_layer_body_contact_area_mm2: float
    island_layer_indices: tuple[int, ...]
    all_layers_supported: bool
    support_required: bool
    support_classification: str
    support_evidence: str


class IneligibleSupportError(ValueError):
    """Raised when an endpoint, corner, or unknown support requests a rail."""


def _box(
    x_bounds: tuple[float, float],
    y_bounds: tuple[float, float],
    z_bounds: tuple[float, float],
) -> trimesh.Trimesh:
    bounds = (x_bounds, y_bounds, z_bounds)
    if any(high <= low for low, high in bounds):
        raise ValueError("Every box bound must have positive extent")
    extents = np.asarray([high - low for low, high in bounds], dtype=float)
    center = np.asarray([(low + high) / 2.0 for low, high in bounds], dtype=float)
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    return mesh


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("Geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    return mesh


def _union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    result = trimesh.boolean.union(meshes, engine="manifold", check_volume=True)
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _difference(body: trimesh.Trimesh, cutters: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    cutter = _union(cutters)
    result = trimesh.boolean.difference(
        [body, cutter], engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def transformed(mesh: trimesh.Trimesh, matrix: np.ndarray) -> trimesh.Trimesh:
    """Return a clean transformed copy without changing the caller's mesh."""

    if np.asarray(matrix).shape != (4, 4):
        raise ValueError("A 4 x 4 homogeneous transform is required")
    result = mesh.copy()
    result.apply_transform(np.asarray(matrix, dtype=float))
    return _clean(result)


def _translation(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> np.ndarray:
    matrix = np.eye(4, dtype=float)
    matrix[:3, 3] = (x, y, z)
    return matrix


def opposite_run_mirror() -> np.ndarray:
    """Mirror a complete local rail assembly about its x=18 mm centreline."""

    matrix = np.eye(4, dtype=float)
    matrix[0, 0] = -1.0
    matrix[0, 3] = accessory.FACEPLATE_WIDTH_MM
    return matrix


def mirror_for_opposite_run(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    return transformed(mesh, opposite_run_mirror())


def support_eligibility(
    run: str,
    support_index: int,
    support_count: int,
    *,
    is_corner: bool = False,
) -> SupportEligibility:
    """Allow interior supports in any valid measured run topology."""

    if run not in NOMINAL_SUPPORT_COUNTS:
        reason = "unknown run is excluded"
    elif isinstance(support_count, bool) or not isinstance(support_count, int):
        reason = "support count must be an integer"
    elif support_count < 3:
        reason = "a run needs at least three supports for one eligible interior"
    elif isinstance(support_index, bool) or not isinstance(support_index, int):
        reason = "support index must be an integer"
    elif support_index < 0 or support_index >= support_count:
        reason = "support index is outside the run"
    elif is_corner:
        reason = "corner supports remain clean"
    elif support_index in (0, support_count - 1):
        reason = "endpoint and corner-adjacent supports remain clean"
    else:
        return SupportEligibility(
            run=run,
            support_index=support_index,
            support_count=support_count,
            is_corner=False,
            eligible=True,
            reason="interior support is eligible for qualification hardware",
        )
    return SupportEligibility(
        run=run,
        support_index=(
            int(support_index)
            if isinstance(support_index, int) and not isinstance(support_index, bool)
            else -1
        ),
        support_count=(
            int(support_count)
            if isinstance(support_count, int) and not isinstance(support_count, bool)
            else -1
        ),
        is_corner=bool(is_corner),
        eligible=False,
        reason=reason,
    )


def _source_to_installed_transform(*, mirrored: bool) -> np.ndarray:
    """Map source ``(q,e,run)`` to installed ``(x,y,z)`` coordinates."""

    # Unmirrored: x=run+2, y=q, z=e.  Mirrored: x=34-run.
    matrix = np.asarray(
        (
            (0.0, 0.0, -1.0 if mirrored else 1.0, 34.0 if mirrored else 2.0),
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        dtype=float,
    )
    return matrix


def _mount_boss_parts(*, mirrored: bool = False) -> tuple[trimesh.Trimesh, ...]:
    parts: list[trimesh.Trimesh] = []
    for head_center_x, stem_center_x in zip(
        MOUNT_BOSS_CENTER_X_MM, MOUNT_STEM_CENTER_X_MM, strict=True
    ):
        for local_center_z in MOUNT_BOSS_CENTER_Z_MM:
            center_z = RAIL_SEATED_Z_MM + local_center_z
            stem = _box(
                (
                    stem_center_x - MOUNT_STEM_WIDTH_MM / 2.0,
                    stem_center_x + MOUNT_STEM_WIDTH_MM / 2.0,
                ),
                (DFRAME_BOSS_ROOT_Y_MM - 0.2, RAIL_SEATED_Y_MM + 1.4),
                (
                    center_z - MOUNT_STEM_HEIGHT_MM / 2.0,
                    center_z + MOUNT_STEM_HEIGHT_MM / 2.0,
                ),
            )
            head = _box(
                (
                    head_center_x - MOUNT_HEAD_WIDTH_MM / 2.0,
                    head_center_x + MOUNT_HEAD_WIDTH_MM / 2.0,
                ),
                (
                    RAIL_SEATED_Y_MM + MOUNT_HEAD_BACK_Y_MM,
                    RAIL_SEATED_Y_MM + MOUNT_HEAD_FRONT_Y_MM,
                ),
                (
                    center_z - MOUNT_HEAD_HEIGHT_MM / 2.0,
                    center_z + MOUNT_HEAD_HEIGHT_MM / 2.0,
                ),
            )
            part = _union([stem, head])
            parts.append(mirror_for_opposite_run(part) if mirrored else part)
    return tuple(parts)


def build_eligible_d_frame_wrapper(
    run: str,
    support_index: int,
    support_count: int,
    *,
    is_corner: bool = False,
    mirrored: bool = False,
) -> DFrameMountWrapper:
    """Wrap one eligible D-frame with external bosses and no subtraction."""

    eligibility = support_eligibility(
        run, support_index, support_count, is_corner=is_corner
    )
    if not eligibility.eligible:
        raise IneligibleSupportError(eligibility.reason)
    source_core = shelf.build_d_frame_corbel()
    source_to_installed = _source_to_installed_transform(mirrored=mirrored)
    installed_core = transformed(source_core, source_to_installed)
    boss_parts = _mount_boss_parts(mirrored=mirrored)
    body = _union([installed_core, *boss_parts])
    return DFrameMountWrapper(
        eligibility=eligibility,
        source_core=source_core,
        installed_core=installed_core,
        boss_parts=boss_parts,
        body=body,
        source_to_installed=source_to_installed,
        mirrored=mirrored,
    )


def core_preservation_report(wrapper: DFrameMountWrapper) -> CorePreservationReport:
    """Restore the installed copy and compare exact bytes, digest, and volume."""

    restored = transformed(wrapper.installed_core, np.linalg.inv(wrapper.source_to_installed))
    source_digest = accessory.mesh_geometry_digest(wrapper.source_core)
    restored_digest = accessory.mesh_geometry_digest(restored)
    byte_identical = bool(
        wrapper.source_core.vertices.tobytes() == restored.vertices.tobytes()
        and wrapper.source_core.faces.tobytes() == restored.faces.tobytes()
    )
    source_volume = float(wrapper.source_core.volume)
    installed_volume = float(wrapper.installed_core.volume)
    wrapper_volume = float(wrapper.body.volume)
    volume_delta = installed_volume - source_volume
    return CorePreservationReport(
        source_volume_mm3=source_volume,
        installed_volume_mm3=installed_volume,
        wrapper_volume_mm3=wrapper_volume,
        volume_delta_mm3=volume_delta,
        source_digest=source_digest,
        restored_digest=restored_digest,
        vertex_face_bytes_identical=byte_identical,
        additive_only=(
            abs(volume_delta) <= 1.0e-8
            and source_digest == restored_digest
            and byte_identical
            and wrapper_volume > installed_volume
        ),
    )


def _mount_cavity_cutters() -> tuple[trimesh.Trimesh, ...]:
    cutters: list[trimesh.Trimesh] = []
    head_half_x = MOUNT_HEAD_WIDTH_MM / 2.0 + MOUNT_CLEARANCE_MM
    head_half_z = MOUNT_HEAD_HEIGHT_MM / 2.0 + MOUNT_CLEARANCE_MM
    stem_half_x = MOUNT_STEM_WIDTH_MM / 2.0 + MOUNT_CLEARANCE_MM
    for head_center_x, stem_center_x in zip(
        MOUNT_BOSS_CENTER_X_MM, MOUNT_STEM_CENTER_X_MM, strict=True
    ):
        for seated_center_z in MOUNT_BOSS_CENTER_Z_MM:
            entry_center_z = seated_center_z - MOUNT_SERVICE_LIFT_MM
            travel_z = (
                entry_center_z - head_half_z,
                seated_center_z + head_half_z,
            )
            # Buried head channel; the 0.8 mm rear lip captures the 4 mm head.
            cutters.append(
                _box(
                    (
                        head_center_x - head_half_x,
                        head_center_x + head_half_x,
                    ),
                    (0.8, MOUNT_CAVITY_FRONT_Y_MM),
                    travel_z,
                )
            )
            # Only the narrow stem channel is open at the rear during travel.
            cutters.append(
                _box(
                    (
                        stem_center_x - stem_half_x,
                        stem_center_x + stem_half_x,
                    ),
                    (-0.05, 1.6),
                    travel_z,
                )
            )
            # At service lift the complete head can enter straight from rear.
            cutters.append(
                _box(
                    (
                        head_center_x - head_half_x,
                        head_center_x + head_half_x,
                    ),
                    (-0.05, MOUNT_CAVITY_FRONT_Y_MM),
                    (entry_center_z - head_half_z, entry_center_z + head_half_z),
                )
            )
    return tuple(cutters)


def _latch_arm_and_tip(
    state: LatchState,
) -> tuple[trimesh.Trimesh, tuple[float, float, float, float]]:
    if state not in ("seated", "deflected"):
        raise ValueError("latch state must be 'seated' or 'deflected'")
    deflection = 0.0 if state == "seated" else LATCH_SERVICE_DEFLECTION_MM
    angle = math.asin(deflection / LATCH_ARM_LENGTH_MM)

    arm = _box(
        LATCH_ROOT_X_BOUNDS_MM,
        (
            LATCH_ROOT_Y_MM - LATCH_ARM_THICKNESS_MM / 2.0,
            LATCH_ROOT_Y_MM + LATCH_ARM_THICKNESS_MM / 2.0,
        ),
        (LATCH_ROOT_Z_MM - LATCH_ARM_LENGTH_MM, LATCH_ROOT_Z_MM),
    )
    pivot = np.asarray((0.0, LATCH_ROOT_Y_MM, LATCH_ROOT_Z_MM), dtype=float)
    rotation = trimesh.transformations.rotation_matrix(angle, (1.0, 0.0, 0.0), pivot)
    arm.apply_transform(rotation)

    # A short outboard bridge overlaps the common module pad by 0.8 mm, then
    # carries the working flex arm entirely beyond x=+10.4.  That keeps a
    # fixed upper detent clear of the full 20 mm pad on the station below.
    anchor = _box(
        LATCH_ANCHOR_X_BOUNDS_MM,
        (
            LATCH_ROOT_Y_MM - LATCH_ARM_THICKNESS_MM / 2.0,
            LATCH_ROOT_Y_MM + LATCH_ARM_THICKNESS_MM / 2.0,
        ),
        (LATCH_ROOT_Z_MM - 0.5, LATCH_ROOT_Z_MM + 0.6),
    )

    free_y = LATCH_ROOT_Y_MM + deflection
    free_z = LATCH_ROOT_Z_MM - math.sqrt(
        LATCH_ARM_LENGTH_MM**2 - deflection**2
    )
    hook_y = (
        free_y - LATCH_HOOK_REAR_OFFSET_MM,
        free_y + LATCH_HOOK_FRONT_OFFSET_MM,
    )
    hook_z = (
        free_z - LATCH_HOOK_HEIGHT_MM / 2.0,
        free_z + LATCH_HOOK_HEIGHT_MM / 2.0,
    )
    hook = _box(LATCH_HOOK_X_BOUNDS_MM, hook_y, hook_z)
    finger_tab = _box(
        LATCH_HOOK_X_BOUNDS_MM,
        (free_y + 0.1, free_y + 4.1),
        (free_z - 2.0, free_z + 2.0),
    )
    return _union([anchor, arm, hook, finger_tab]), (
        hook_y[0], hook_y[1], hook_z[0], hook_z[1]
    )


def latch_strain_proxy() -> LatchStrainProxy:
    """Return the conservative 2.4% rectangular-cantilever strain proxy."""

    strain = (
        1.5
        * LATCH_ARM_THICKNESS_MM
        * LATCH_SERVICE_DEFLECTION_MM
        / LATCH_ARM_LENGTH_MM**2
    )
    return LatchStrainProxy(
        arm_length_mm=LATCH_ARM_LENGTH_MM,
        arm_thickness_mm=LATCH_ARM_THICKNESS_MM,
        tip_deflection_mm=LATCH_SERVICE_DEFLECTION_MM,
        surface_strain=strain,
        below_three_percent=strain < 0.03,
    )


def build_retained_accessory(
    kind: accessory.AccessoryKind,
    *,
    latch_state: LatchState = "seated",
) -> trimesh.Trimesh:
    """Add the common front-release detent to one real accessory mesh."""

    base = accessory.build_accessory(kind)
    if kind == "coil_j_hook":
        # The seed's z=+15 mm tip can touch an occupied adjacent station near
        # the end of the 8 mm service lift.  The integrated wrapper freezes the
        # physically equivalent 14 mm tip (centre +6, bounds -1..+13) by
        # trimming only the top 2 mm.  The root, elbow, key, and cable-bearing
        # geometry remain unchanged.
        margin = 1.0
        base = _difference(
            base,
            [
                _box(
                    (
                        float(base.bounds[0, 0]) - margin,
                        float(base.bounds[1, 0]) + margin,
                    ),
                    (
                        float(base.bounds[0, 1]) - margin,
                        float(base.bounds[1, 1]) + margin,
                    ),
                    (FINAL_COIL_TIP_MAX_Z_MM, float(base.bounds[1, 2]) + margin),
                )
            ],
        )
    latch, _ = _latch_arm_and_tip(latch_state)
    return _union([base, latch])


def _latch_recess_cutters() -> tuple[trimesh.Trimesh, ...]:
    _, (hook_y0, _hook_y1, hook_z0, hook_z1) = _latch_arm_and_tip("seated")
    x_bounds = (
        accessory.SOCKET_CENTER_X_MM + LATCH_HOOK_X_BOUNDS_MM[0] - LATCH_CLEARANCE_MM,
        accessory.SOCKET_CENTER_X_MM + LATCH_HOOK_X_BOUNDS_MM[1] + LATCH_CLEARANCE_MM,
    )
    # Only the part of the hook behind the rail's front face needs a recess.
    if accessory.FACEPLATE_THICKNESS_MM + hook_y0 >= accessory.FACEPLATE_THICKNESS_MM:
        raise AssertionError("Latch hook does not reach the front recess")
    return tuple(
        _box(
            x_bounds,
            (LATCH_RECESS_BACK_Y_MM, LATCH_RECESS_FRONT_Y_MM),
            (
                center_z + hook_z0 - LATCH_CLEARANCE_MM,
                center_z + hook_z1 + LATCH_CLEARANCE_MM,
            ),
        )
        for center_z in accessory.SOCKET_CENTER_Z_MM
    )


def build_mounted_retention_rail(
    *, clearance_mm: float = accessory.NOMINAL_CLEARANCE_MM
) -> trimesh.Trimesh:
    """Build the actual rail with mount channels and latch recesses."""

    if abs(clearance_mm - MOUNT_CLEARANCE_MM) > 1.0e-12:
        raise ValueError("The integrated interface is frozen to 0.4 mm clearance")
    base = accessory.build_faceplate_rail(clearance_mm=clearance_mm)
    return _difference(
        base,
        [*_mount_cavity_cutters(), *_latch_recess_cutters()],
    )


def _exact_offsets(start: float, stop: float, increment: float) -> tuple[float, ...]:
    distance = abs(stop - start)
    count = int(round(distance / increment))
    if abs(count * increment - distance) > 1.0e-9:
        raise ValueError("Service distance must be an integer number of increments")
    return tuple(start + (stop - start) * index / count for index in range(count + 1))


def rail_mount_service_transforms() -> ServiceTransforms:
    """Lift 4 mm, approach 2.4 mm, drop, and publish the exact reverse."""

    seated = _translation(y=RAIL_SEATED_Y_MM, z=RAIL_SEATED_Z_MM)
    insertion = _translation(
        y=RAIL_SEATED_Y_MM,
        z=RAIL_SEATED_Z_MM + MOUNT_SERVICE_LIFT_MM,
    )
    approach = tuple(
        _translation(
            y=RAIL_SEATED_Y_MM + offset,
            z=RAIL_SEATED_Z_MM + MOUNT_SERVICE_LIFT_MM,
        )
        for offset in _exact_offsets(
            MOUNT_APPROACH_MM, 0.0, SERVICE_INCREMENT_MM
        )
    )
    drop = tuple(
        _translation(y=RAIL_SEATED_Y_MM, z=RAIL_SEATED_Z_MM + lift)
        for lift in _exact_offsets(
            MOUNT_SERVICE_LIFT_MM, 0.0, SERVICE_INCREMENT_MM
        )
    )
    return ServiceTransforms(
        approach=approach,
        insertion=insertion,
        drop=drop,
        seated=seated,
        removal_lift=tuple(reversed(drop)),
        removal_outward=tuple(reversed(approach)),
        increment_mm=SERVICE_INCREMENT_MM,
    )


def module_service_transforms(station_index: int) -> ServiceTransforms:
    """Push a deflected module in, drop it 8 mm, and publish the reverse."""

    if isinstance(station_index, bool) or not isinstance(station_index, int):
        raise TypeError("station_index must be an exact integer")
    datum = accessory.seating_transforms(station_index)
    seated = datum.seated.copy()
    insertion = datum.insertion.copy()
    approach = tuple(
        _translation(y=offset) @ insertion
        for offset in _exact_offsets(MODULE_APPROACH_MM, 0.0, SERVICE_INCREMENT_MM)
    )
    drop = tuple(
        _translation(z=lift) @ seated
        for lift in _exact_offsets(
            accessory.SOCKET_SERVICE_LIFT_MM, 0.0, SERVICE_INCREMENT_MM
        )
    )
    return ServiceTransforms(
        approach=approach,
        insertion=insertion,
        drop=drop,
        seated=seated,
        removal_lift=tuple(reversed(drop)),
        removal_outward=tuple(reversed(approach)),
        increment_mm=SERVICE_INCREMENT_MM,
    )


def wrong_key_orientation(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Mirror only local x so the left tongue is wrong-handed on the right.

    Outward ``y`` and vertical ``z`` remain correct.  Rejection therefore
    proves the asymmetric key, rather than a trivially backwards module pad.
    """

    mirror = np.eye(4, dtype=float)
    mirror[0, 0] = -1.0
    return transformed(mesh, mirror)


def positive_overlap_volume(
    first: trimesh.Trimesh, second: trimesh.Trimesh
) -> float:
    """Return the actual Manifold positive intersection volume in mm^3."""

    # Coincident, zero-volume contact faces are a successful clearance result.
    # Trimesh may ask those degenerate result shells for a centre of mass; keep
    # that known divide-by-zero warning out of otherwise clean qualification logs.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, module=r"trimesh\.triangles"
        )
        result = trimesh.boolean.intersection(
            [first, second], engine="manifold", check_volume=True
        )
        if result is None:
            return 0.0
        if isinstance(result, list):
            if not result:
                return 0.0
            result = trimesh.util.concatenate(result)
        if result.is_empty:
            return 0.0
        volume = abs(float(result.volume))
        return 0.0 if volume <= 1.0e-12 else volume


def mesh_is_one_body(mesh: trimesh.Trimesh) -> bool:
    return bool(
        mesh.is_watertight
        and mesh.is_winding_consistent
        and mesh.volume > 0.0
        and len(mesh.split(only_watertight=False)) == 1
    )


def orient_retained_module_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Rotate 180 degrees about local X, then normalize onto the XY bed."""

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty retained module is required")
    result = mesh.copy()
    result.apply_transform(
        trimesh.transformations.rotation_matrix(
            math.radians(RETAINED_MODULE_PRINT_ROTATION_X_DEG),
            (1.0, 0.0, 0.0),
        )
    )
    result.apply_translation(-result.bounds[0])
    return _clean(result)


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


def _filled_components(region) -> tuple[Polygon, ...]:
    if region.is_empty:
        return ()
    if isinstance(region, Polygon):
        return (region,)
    components: list[Polygon] = []
    for geometry in region.geoms:
        if isinstance(geometry, Polygon):
            components.append(geometry)
        elif hasattr(geometry, "geoms"):
            components.extend(_filled_components(geometry))
    return tuple(components)


def saved_layer_island_report(
    mesh: trimesh.Trimesh, *, layer_height_mm: float = 0.2
) -> LayerIslandReport:
    """Apply the retained-module orientation, then classify layer islands."""

    return saved_oriented_layer_island_report(
        orient_retained_module_for_print(mesh),
        layer_height_mm=layer_height_mm,
    )


def saved_oriented_layer_island_report(
    oriented_mesh: trimesh.Trimesh, *, layer_height_mm: float = 0.2
) -> LayerIslandReport:
    """Parity-correct island scan for a mesh already oriented on its bed.

    Multiple supported branches in one layer are valid; a component is an
    island only when its filled section has no positive plan overlap with the
    immediately preceding deposited layer.
    """

    if not isinstance(oriented_mesh, trimesh.Trimesh) or oriented_mesh.is_empty:
        raise ValueError("A nonempty oriented print mesh is required")
    layer = float(layer_height_mm)
    if not math.isfinite(layer) or layer <= 0.0:
        raise ValueError("layer height must be positive and finite")
    oriented = oriented_mesh.copy()
    height = float(oriented.extents[2])
    count = int(math.ceil((height - 1.0e-9) / layer))
    if count < 1:
        raise ValueError("Saved build height must contain at least one layer")
    previous = None
    islands: list[int] = []
    first_layer_area = 0.0
    minimum_z = float(oriented.bounds[0, 2])
    for index in range(count):
        layer_bottom = index * layer
        deposited_height = min(layer, height - layer_bottom)
        region = _section_material_region(
            oriented, minimum_z + layer_bottom + 0.5 * deposited_height
        )
        components = _filled_components(region)
        if index == 0:
            first_layer_area = float(region.area)
        if not components:
            islands.append(index)
        elif previous is not None and any(
            component.intersection(previous).area <= 1.0e-8
            for component in components
        ):
            islands.append(index)
        previous = region
    support_required = bool(islands)
    if support_required:
        evidence = (
            "disconnected component begins at saved layer index "
            + ",".join(str(index) for index in islands)
        )
    else:
        evidence = "every saved-layer component overlaps deposited material below"
    return LayerIslandReport(
        layer_height_mm=layer,
        sampled_layer_count=count,
        first_layer_body_contact_area_mm2=first_layer_area,
        island_layer_indices=tuple(islands),
        all_layers_supported=not support_required,
        support_required=support_required,
        support_classification=(
            "support_required" if support_required else "support_free"
        ),
        support_evidence=evidence,
    )
