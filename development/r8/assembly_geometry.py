#!/usr/bin/env python3
"""Qualification-only one-bay assembly geometry for the R8 shelf.

This module closes only the cassette-to-corbel interface.  It does not add
wall-fastener bores, authorize a printer profile, or make a load claim.  The
installed coordinate convention is deliberately explicit:

* ``x`` runs along the shelf;
* ``y`` runs from the wall toward the visible front; and
* ``z`` points up.

The selected U-box cassette is reflected through its depth so its authored
open rear faces the wall.  Two unmodified D-frame cores carry the cassette at
its end seams.  Their shallow locator keys and the right-hand flex keeper are
additive, nonstructural fit features.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Literal, Sequence
import warnings

import numpy as np
import trimesh

import accessory_geometry as accessory
import design_math
import interface_geometry as interface
import shelf_geometry as shelf


_R8_CONFIG = json.loads(
    Path(__file__).with_name("config.json").read_text(encoding="utf-8")
)
THROUGH_RUN_LAYOUT = design_math.calculate_plan(_R8_CONFIG).through


# Fail-closed release gates.  These values are intentionally not production
# claims; they keep this interface proof from being mistaken for a rated set.
QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PRINT_PROFILE_RELEASED = False
WALL_FASTENER_BORES_EMITTED = False
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0
REQUIRED_PRINT_MATERIAL = "PETG"
A1_MINI_BUILD_VOLUME_MM = (180.0, 180.0, 180.0)
REGISTRATION_STRUCTURAL_CREDIT = False
KEEPER_STRUCTURAL_CREDIT = False
NOMINAL_PRINTED_PART_COUNT = 5

# One internal through bay from the frozen R8 layout.  The 0.35 mm seam gap
# puts each 32 mm corbel centre 0.175 mm outside its cassette seam.
NOMINAL_BAY_LENGTH_MM = THROUGH_RUN_LAYOUT.physical_module_widths_mm[1]
SEAM_GAP_MM = 0.35
SEAM_HALF_GAP_MM = SEAM_GAP_MM / 2.0
LEFT_SUPPORT_CENTER_X_MM = -SEAM_HALF_GAP_MM
RIGHT_SUPPORT_CENTER_X_MM = NOMINAL_BAY_LENGTH_MM + SEAM_HALF_GAP_MM
CAP_BEARING_WIDTH_MM = (shelf.CORBEL_RUN_THICKNESS_MM - SEAM_GAP_MM) / 2.0

# The left support is one known interior station in the frozen through-run
# topology.  The existing interface contract authors a 36 mm rail about local
# x=18; this translation centres it on the one-bay left support.
RAIL_SUPPORT_RUN = "through"
RAIL_SUPPORT_INDEX = 1
RAIL_SUPPORT_COUNT = len(THROUGH_RUN_LAYOUT.corbel_centers_mm)
DEFAULT_RAIL_SUPPORT_INDICES = tuple(
    _R8_CONFIG["accessory_system"]["default_equipped_station_indices"][
        RAIL_SUPPORT_RUN
    ]
)
if any(
    isinstance(index, bool) or not isinstance(index, int)
    for index in DEFAULT_RAIL_SUPPORT_INDICES
):
    raise ValueError("default rail support indices must be exact integers")
DEFAULT_RAIL_STATION_INDEX = 1
RAIL_LOCAL_TO_ASSEMBLY_X_MM = (
    LEFT_SUPPORT_CENTER_X_MM - accessory.FACEPLATE_WIDTH_MM / 2.0
)
RAIL_SERVICE_REQUIRES_MODULE_REMOVAL = True
TILED_BAY_PITCH_MM = THROUGH_RUN_LAYOUT.equal_corbel_pitch_mm
INTERIOR_KEY_OFFSET_FROM_SUPPORT_MM = 3.2 + SEAM_HALF_GAP_MM
TERMINAL_KEY_OFFSET_FROM_SUPPORT_MM = 12.8
INTERIOR_PRIOR_KEEPER_OFFSET_MM = -8.175
INTERIOR_NEXT_KEEPER_OFFSET_MM = 8.175
TERMINAL_CAP_BEARING_WIDTH_MM = shelf.CORBEL_RUN_THICKNESS_MM
TERMINAL_START_SUPPORT_CENTER_X_MM = THROUGH_RUN_LAYOUT.corbel_centers_mm[0]
TERMINAL_END_SUPPORT_CENTER_X_MM = THROUGH_RUN_LAYOUT.corbel_centers_mm[-1]

# Shallow, additive cap registration.  A 0.4 mm clearance is provided on each
# pocket side and above the key; 1.0 mm of the 2.4 mm bottom skin remains.
REGISTRATION_CLEARANCE_PER_FACE_MM = 0.4
REGISTRATION_KEY_X_MM = 3.2
REGISTRATION_KEY_Y_MM = 12.0
REGISTRATION_KEY_PROJECTION_MM = 1.0
REGISTRATION_KEY_ROOT_OVERLAP_MM = 0.2
REGISTRATION_POCKET_X_MM = 4.0
REGISTRATION_POCKET_Y_MM = 12.8
REGISTRATION_POCKET_DEPTH_MM = 1.4
REGISTRATION_REMAINING_BOTTOM_SKIN_MM = 1.0
REGISTRATION_KEY_CENTER_Y_MM = shelf.SHELF_DEPTH_MM / 2.0
REGISTRATION_KEY_CENTERS_X_MM = (3.2, NOMINAL_BAY_LENGTH_MM - 3.2)

# A small open slot in the visible fascia accepts one flex keeper on the
# selected support side.  It blocks an uncommanded lift but presses toward the
# wall for service.
KEEPER_SLOT_CENTER_X_MM = NOMINAL_BAY_LENGTH_MM - 8.0
KEEPER_SLOT_X_MM = 4.8
KEEPER_SLOT_SOURCE_Y_BOUNDS_MM = (-0.05, 1.2)
KEEPER_SLOT_SOURCE_Z_BOUNDS_MM = (1.2, 3.2)
KEEPER_HOOK_X_MM = 4.0
KEEPER_HOOK_INSTALLED_Y_BOUNDS_MM = (151.6, 154.4)
KEEPER_HOOK_INSTALLED_Z_BOUNDS_MM = (161.6, 162.8)
KEEPER_FLEX_LENGTH_MM = 10.0
KEEPER_FLEX_THICKNESS_MM = 1.0
KEEPER_RELEASE_DEFLECTION_MM = 1.8
KEEPER_RELEASE_ANGLE_RAD = -math.asin(
    KEEPER_RELEASE_DEFLECTION_MM / KEEPER_FLEX_LENGTH_MM
)
KEEPER_BLOCKING_LIFT_MM = 0.8
KEEPER_CONTACT_LIFT_MM = 0.4

SERVICE_LIFT_MM = 2.0
SERVICE_INCREMENT_MM = 0.2
# Manifold exchanges float32 meshes; exact face contact can report a residual
# below 3e-5 mm^3 on these 150+ mm coordinates.  This is a numeric tolerance,
# not additional authored clearance.
COLLISION_TOLERANCE_MM3 = 3.0e-5

KeeperState = Literal["seated", "deflected"]
SupportRole = Literal["terminal_start", "interior", "terminal_end"]
RegistrationEnd = Literal["seam", "terminal"]
KeeperSide = Literal["left", "right"]


@dataclass(frozen=True)
class BearingContact:
    """Analytic contact contract at one cassette seam."""

    side: str
    support_center_x_mm: float
    cap_x_bounds_mm: tuple[float, float]
    cassette_overlap_x_bounds_mm: tuple[float, float]
    cap_overlap_width_mm: float
    selected_end_land_width_mm: float
    pocket_plan_area_mm2: float
    net_cap_contact_area_mm2: float
    net_selected_land_contact_area_mm2: float
    contact_z_mm: float


@dataclass(frozen=True)
class TerminalBearingContact:
    """Full-cap contact contract at one terminal cassette end."""

    side: str
    support_center_x_mm: float
    cap_x_bounds_mm: tuple[float, float]
    cassette_overlap_x_bounds_mm: tuple[float, float]
    cap_overlap_width_mm: float
    key_offset_from_support_center_mm: float
    selected_end_land_width_mm: float
    pocket_plan_area_mm2: float
    net_cap_contact_area_mm2: float
    net_selected_land_contact_area_mm2: float
    contact_z_mm: float


@dataclass(frozen=True)
class InstalledCassette:
    """Selected U-box before and after the registration cuts and placement."""

    source_seed: trimesh.Trimesh
    source_registered: trimesh.Trimesh
    installed: trimesh.Trimesh
    source_to_installed: np.ndarray
    metrics: shelf.UBoxMetrics
    registration_pockets_source: tuple[trimesh.Trimesh, trimesh.Trimesh]
    keeper_slot_source: trimesh.Trimesh
    origin_x_mm: float
    left_registration: RegistrationEnd
    right_registration: RegistrationEnd
    keeper_side: KeeperSide


@dataclass(frozen=True)
class InstalledSupport:
    """One untouched D-frame core plus additive interface features."""

    side: SupportRole
    support_index: int
    support_count: int
    center_x_mm: float
    keeper_state: KeeperState | None
    next_keeper_state: KeeperState | None
    source_core: trimesh.Trimesh
    installed_core: trimesh.Trimesh
    source_to_installed: np.ndarray
    registration_keys: tuple[trimesh.Trimesh, ...]
    rail_eligibility: interface.SupportEligibility | None
    rail_mount_bosses: tuple[trimesh.Trimesh, ...]
    keeper: trimesh.Trimesh | None
    next_keeper: trimesh.Trimesh | None
    body: trimesh.Trimesh

    @property
    def keepers(self) -> tuple[trimesh.Trimesh, ...]:
        return tuple(
            item for item in (self.keeper, self.next_keeper) if item is not None
        )


@dataclass(frozen=True)
class OneBayAssembly:
    """One internal cassette between topology-real shared supports."""

    cassette: InstalledCassette
    left_support: InstalledSupport
    right_support: InstalledSupport
    mounted_rail: trimesh.Trimesh
    seated_retained_blank: trimesh.Trimesh
    rail_support_index: int
    rail_station_index: int
    bearing_contacts: tuple[BearingContact, BearingContact]


@dataclass(frozen=True)
class TiledRunAssembly:
    """Full nine-support through run with eight physically tiled cassettes."""

    cassettes: tuple[InstalledCassette, ...]
    supports: tuple[InstalledSupport, ...]
    mounted_rails: tuple[trimesh.Trimesh, ...]
    seated_retained_blanks: tuple[trimesh.Trimesh, ...]
    rail_support_indices: tuple[int, ...]
    rail_station_indices: tuple[int, ...]
    bearing_contacts: tuple[
        tuple[BearingContact | TerminalBearingContact, BearingContact | TerminalBearingContact],
        ...,
    ]


@dataclass(frozen=True)
class ServiceTransforms:
    """Exact vertical install and reverse-removal stations."""

    installation: tuple[np.ndarray, ...]
    removal: tuple[np.ndarray, ...]
    lift_mm: float
    increment_mm: float


@dataclass(frozen=True)
class KeeperStrainProxy:
    """Small-deflection comparison only; not FEA or a material allowable."""

    arm_length_mm: float
    arm_thickness_mm: float
    tip_deflection_mm: float
    surface_strain: float
    below_three_percent: bool


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
    return _clean(mesh)


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("Geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    return mesh


def _union(meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("At least one mesh is required")
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, module=r"trimesh\.triangles"
        )
        result = trimesh.boolean.union(
            list(meshes), engine="manifold", check_volume=True
        )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _difference(
    body: trimesh.Trimesh, cutters: Sequence[trimesh.Trimesh]
) -> trimesh.Trimesh:
    if not cutters:
        return body.copy()
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, module=r"trimesh\.triangles"
        )
        result = trimesh.boolean.difference(
            [body, *cutters], engine="manifold", check_volume=True
        )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def transformed(mesh: trimesh.Trimesh, matrix: np.ndarray) -> trimesh.Trimesh:
    """Return a cleaned transformed copy without changing the input mesh."""

    transform = np.asarray(matrix, dtype=float)
    if transform.shape != (4, 4):
        raise ValueError("A 4 x 4 homogeneous transform is required")
    result = mesh.copy()
    result.apply_transform(transform)
    return _clean(result)


def translation(*, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> np.ndarray:
    matrix = np.eye(4, dtype=float)
    matrix[:3, 3] = (float(x), float(y), float(z))
    return matrix


def cassette_source_to_installed_transform(origin_x_mm: float = 0.0) -> np.ndarray:
    """Map source ``(run, front->rear, up)`` to installed wall coordinates."""

    return np.asarray(
        (
            (1.0, 0.0, 0.0, float(origin_x_mm)),
            (0.0, -1.0, 0.0, shelf.SHELF_DEPTH_MM),
            (0.0, 0.0, 1.0, shelf.CORBEL_INSTALLED_HEIGHT_MM),
            (0.0, 0.0, 0.0, 1.0),
        ),
        dtype=float,
    )


def support_source_to_installed_transform(center_x_mm: float) -> np.ndarray:
    """Map D-frame source ``(q, e, run)`` to installed ``(x, y, z)``."""

    return np.asarray(
        (
            (0.0, 0.0, 1.0, float(center_x_mm) - shelf.CORBEL_RUN_THICKNESS_MM / 2.0),
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        dtype=float,
    )


def _registration_pocket_source(center_x_mm: float) -> trimesh.Trimesh:
    return _box(
        (
            center_x_mm - REGISTRATION_POCKET_X_MM / 2.0,
            center_x_mm + REGISTRATION_POCKET_X_MM / 2.0,
        ),
        (
            REGISTRATION_KEY_CENTER_Y_MM - REGISTRATION_POCKET_Y_MM / 2.0,
            REGISTRATION_KEY_CENTER_Y_MM + REGISTRATION_POCKET_Y_MM / 2.0,
        ),
        (-0.05, REGISTRATION_POCKET_DEPTH_MM),
    )


def _keeper_slot_source(
    length_mm: float, keeper_side: KeeperSide
) -> trimesh.Trimesh:
    if keeper_side == "left":
        center_x = 8.0
    elif keeper_side == "right":
        center_x = float(length_mm) - 8.0
    else:
        raise ValueError("keeper_side must be 'left' or 'right'")
    return _box(
        (
            center_x - KEEPER_SLOT_X_MM / 2.0,
            center_x + KEEPER_SLOT_X_MM / 2.0,
        ),
        KEEPER_SLOT_SOURCE_Y_BOUNDS_MM,
        KEEPER_SLOT_SOURCE_Z_BOUNDS_MM,
    )


def _cassette_registration_centers(
    length_mm: float, left: RegistrationEnd, right: RegistrationEnd
) -> tuple[float, float]:
    if left not in ("seam", "terminal") or right not in ("seam", "terminal"):
        raise ValueError("cassette registration ends must be 'seam' or 'terminal'")
    # Both seam and terminal pockets remain 3.2 mm from the physical end.
    # Terminal support centres move 16 mm inward; their key sign reverses.
    left_center = 3.2
    right_center = float(length_mm) - 3.2
    return (left_center, right_center)


def build_registered_cassette(
    *,
    length_mm: float = NOMINAL_BAY_LENGTH_MM,
    origin_x_mm: float = 0.0,
    left_registration: RegistrationEnd = "seam",
    right_registration: RegistrationEnd = "seam",
    keeper_side: KeeperSide = "right",
) -> InstalledCassette:
    """Cut two shallow locator pockets and one open keeper slot."""

    length = float(length_mm)
    seed, metrics = shelf.build_front_first_u_box_cassette(length)
    pocket_centers = _cassette_registration_centers(
        length, left_registration, right_registration
    )
    pockets = tuple(_registration_pocket_source(center) for center in pocket_centers)
    slot = _keeper_slot_source(length, keeper_side)
    registered = _difference(seed, (*pockets, slot))
    transform = cassette_source_to_installed_transform(origin_x_mm)
    return InstalledCassette(
        source_seed=seed,
        source_registered=registered,
        installed=transformed(registered, transform),
        source_to_installed=transform,
        metrics=metrics,
        registration_pockets_source=(pockets[0], pockets[1]),
        keeper_slot_source=slot,
        origin_x_mm=float(origin_x_mm),
        left_registration=left_registration,
        right_registration=right_registration,
        keeper_side=keeper_side,
    )


def _registration_key_installed(center_x_mm: float) -> trimesh.Trimesh:
    contact_z = shelf.CORBEL_INSTALLED_HEIGHT_MM
    return _box(
        (
            center_x_mm - REGISTRATION_KEY_X_MM / 2.0,
            center_x_mm + REGISTRATION_KEY_X_MM / 2.0,
        ),
        (
            REGISTRATION_KEY_CENTER_Y_MM - REGISTRATION_KEY_Y_MM / 2.0,
            REGISTRATION_KEY_CENTER_Y_MM + REGISTRATION_KEY_Y_MM / 2.0,
        ),
        (
            contact_z - REGISTRATION_KEY_ROOT_OVERLAP_MM,
            contact_z + REGISTRATION_KEY_PROJECTION_MM,
        ),
    )


def _keeper_flex_member(
    state: KeeperState, center_x_mm: float
) -> trimesh.Trimesh:
    center_x = float(center_x_mm)
    half_hook_x = KEEPER_HOOK_X_MM / 2.0
    parts = (
        _box(
            (center_x - half_hook_x, center_x + half_hook_x),
            (153.4, 154.4),
            (151.8, 162.4),
        ),
        _box(
            (center_x - half_hook_x, center_x + half_hook_x),
            KEEPER_HOOK_INSTALLED_Y_BOUNDS_MM,
            KEEPER_HOOK_INSTALLED_Z_BOUNDS_MM,
        ),
        _box(
            (center_x - half_hook_x, center_x + half_hook_x),
            (154.0, 157.6),
            (160.8, 163.4),
        ),
    )
    member = _union(parts)
    if state == "seated":
        return member
    if state != "deflected":
        raise ValueError(f"Unknown keeper state: {state!r}")
    rotation = trimesh.transformations.rotation_matrix(
        KEEPER_RELEASE_ANGLE_RAD,
        (1.0, 0.0, 0.0),
        (0.0, 153.9, 152.0),
    )
    return transformed(member, rotation)


def _keeper_installed(
    state: KeeperState, center_x_mm: float
) -> trimesh.Trimesh:
    center_x = float(center_x_mm)
    anchor = _box(
        (center_x - 3.0, center_x + 3.0),
        (151.6, 154.5),
        (149.5, 153.2),
    )
    return _union((anchor, _keeper_flex_member(state, center_x)))


def rail_local_to_assembly_transform(
    support_center_x_mm: float = LEFT_SUPPORT_CENTER_X_MM,
) -> np.ndarray:
    """Translate the existing 36 mm rail contract onto one support centre."""

    return translation(
        x=float(support_center_x_mm) - accessory.FACEPLATE_WIDTH_MM / 2.0
    )


def _validate_support_topology(
    role: SupportRole,
    run: str,
    support_index: int,
    support_count: int,
) -> None:
    if run not in interface.NOMINAL_SUPPORT_COUNTS:
        raise ValueError("support run must be 'through' or 'return'")
    if (
        isinstance(support_count, bool)
        or not isinstance(support_count, int)
        or support_count < 3
    ):
        raise ValueError("support count must be an integer of at least three")
    if (
        isinstance(support_index, bool)
        or not isinstance(support_index, int)
        or support_index not in range(support_count)
    ):
        raise ValueError("support index is outside the run topology")
    expected_role: SupportRole
    if support_index == 0:
        expected_role = "terminal_start"
    elif support_index == support_count - 1:
        expected_role = "terminal_end"
    else:
        expected_role = "interior"
    if role != expected_role:
        raise ValueError(
            f"support {support_index} requires role {expected_role!r}, not {role!r}"
        )


def _support_key_centers(
    role: SupportRole, center_x_mm: float
) -> tuple[float, ...]:
    center = float(center_x_mm)
    if role == "terminal_start":
        return (center - TERMINAL_KEY_OFFSET_FROM_SUPPORT_MM,)
    if role == "terminal_end":
        return (center + TERMINAL_KEY_OFFSET_FROM_SUPPORT_MM,)
    if role == "interior":
        return (
            center - INTERIOR_KEY_OFFSET_FROM_SUPPORT_MM,
            center + INTERIOR_KEY_OFFSET_FROM_SUPPORT_MM,
        )
    raise ValueError(f"Unknown support role: {role!r}")


def _support_keeper_center(role: SupportRole, center_x_mm: float) -> float | None:
    if role in ("terminal_start", "terminal_end"):
        return None
    if role == "interior":
        return float(center_x_mm) + INTERIOR_PRIOR_KEEPER_OFFSET_MM
    raise ValueError(f"Unknown support role: {role!r}")


def build_support_variant(
    role: SupportRole,
    center_x_mm: float,
    support_index: int,
    *,
    keeper_state: KeeperState = "seated",
    next_keeper_state: KeeperState | None = None,
    rail_ready: bool = False,
    run: str = RAIL_SUPPORT_RUN,
    support_count: int = RAIL_SUPPORT_COUNT,
    is_corner: bool = False,
) -> InstalledSupport:
    """Build a topology-real terminal or shared-interior support family.

    Terminals stay key-only.  Every interior carries the prior cassette's
    keeper; the penultimate interior must also carry the final cassette's
    mirrored keeper, while every other interior forbids that second keeper.
    """

    if keeper_state not in ("seated", "deflected"):
        raise ValueError("keeper_state must be 'seated' or 'deflected'")
    if next_keeper_state not in (None, "seated", "deflected"):
        raise ValueError(
            "next_keeper_state must be None, 'seated', or 'deflected'"
        )
    _validate_support_topology(role, run, support_index, support_count)
    if role != "interior" and keeper_state != "seated":
        raise ValueError("terminal supports are clean and cannot carry a keeper")
    is_penultimate = (
        role == "interior" and support_index == support_count - 2
    )
    if (next_keeper_state is not None) != is_penultimate:
        raise ValueError(
            "the penultimate interior requires exactly one final-cassette keeper"
        )
    center = float(center_x_mm)
    eligibility: interface.SupportEligibility | None = None
    bosses: tuple[trimesh.Trimesh, ...] = ()
    if rail_ready:
        local = interface.build_eligible_d_frame_wrapper(
            run,
            support_index,
            support_count,
            is_corner=is_corner,
            mirrored=False,
        )
        placement = rail_local_to_assembly_transform(center)
        source_core = local.source_core
        installed_core = transformed(local.installed_core, placement)
        source_to_installed = placement @ local.source_to_installed
        bosses = tuple(transformed(part, placement) for part in local.boss_parts)
        base_body = transformed(local.body, placement)
        eligibility = local.eligibility
    else:
        if is_corner:
            raise ValueError("corner supports require a separate corner topology")
        source_core = shelf.build_d_frame_corbel()
        source_to_installed = support_source_to_installed_transform(center)
        installed_core = transformed(source_core, source_to_installed)
        base_body = installed_core

    keys = tuple(
        _registration_key_installed(key_center)
        for key_center in _support_key_centers(role, center)
    )
    keeper_center = _support_keeper_center(role, center)
    keeper = (
        None
        if keeper_center is None
        else _keeper_installed(keeper_state, keeper_center)
    )
    next_keeper = (
        None
        if next_keeper_state is None
        else _keeper_installed(
            next_keeper_state,
            center + INTERIOR_NEXT_KEEPER_OFFSET_MM,
        )
    )
    keepers = tuple(
        item for item in (keeper, next_keeper) if item is not None
    )
    return InstalledSupport(
        side=role,
        support_index=support_index,
        support_count=support_count,
        center_x_mm=center,
        keeper_state=None if keeper is None else keeper_state,
        next_keeper_state=next_keeper_state,
        source_core=source_core,
        installed_core=installed_core,
        source_to_installed=source_to_installed,
        registration_keys=keys,
        rail_eligibility=eligibility,
        rail_mount_bosses=bosses,
        keeper=keeper,
        next_keeper=next_keeper,
        body=_union((base_body, *keys, *keepers)),
    )


def build_terminal_start_support(
    center_x_mm: float = TERMINAL_START_SUPPORT_CENTER_X_MM,
    *,
    run: str = RAIL_SUPPORT_RUN,
    support_count: int = RAIL_SUPPORT_COUNT,
) -> InstalledSupport:
    return build_support_variant(
        "terminal_start",
        center_x_mm,
        0,
        run=run,
        support_count=support_count,
    )


def build_terminal_end_support(
    center_x_mm: float = TERMINAL_END_SUPPORT_CENTER_X_MM,
    *,
    run: str = RAIL_SUPPORT_RUN,
    support_count: int = RAIL_SUPPORT_COUNT,
) -> InstalledSupport:
    return build_support_variant(
        "terminal_end",
        center_x_mm,
        support_count - 1,
        run=run,
        support_count=support_count,
    )


def build_smooth_interior_support(
    center_x_mm: float = RIGHT_SUPPORT_CENTER_X_MM,
    *,
    support_index: int = 2,
    keeper_state: KeeperState = "seated",
    next_keeper_state: KeeperState | None = None,
    run: str = RAIL_SUPPORT_RUN,
    support_count: int = RAIL_SUPPORT_COUNT,
) -> InstalledSupport:
    return build_support_variant(
        "interior",
        center_x_mm,
        support_index,
        keeper_state=keeper_state,
        next_keeper_state=next_keeper_state,
        run=run,
        support_count=support_count,
    )


def build_rail_interior_support(
    center_x_mm: float = LEFT_SUPPORT_CENTER_X_MM,
    *,
    support_index: int = RAIL_SUPPORT_INDEX,
    keeper_state: KeeperState = "seated",
    next_keeper_state: KeeperState | None = None,
    run: str = RAIL_SUPPORT_RUN,
    support_count: int = RAIL_SUPPORT_COUNT,
) -> InstalledSupport:
    return build_support_variant(
        "interior",
        center_x_mm,
        support_index,
        keeper_state=keeper_state,
        next_keeper_state=next_keeper_state,
        rail_ready=True,
        run=run,
        support_count=support_count,
    )


def build_rail_ready_left_support(
    *,
    run: str = RAIL_SUPPORT_RUN,
    support_index: int = RAIL_SUPPORT_INDEX,
    support_count: int = RAIL_SUPPORT_COUNT,
    is_corner: bool = False,
    next_keeper_state: KeeperState | None = None,
) -> InstalledSupport:
    """Compatibility wrapper for the internal-seam rail support."""

    return build_support_variant(
        "interior",
        LEFT_SUPPORT_CENTER_X_MM,
        support_index,
        rail_ready=True,
        run=run,
        support_count=support_count,
        is_corner=is_corner,
        next_keeper_state=next_keeper_state,
    )


def build_installed_support(
    side: Literal["left", "right"], *, keeper_state: KeeperState = "seated"
) -> InstalledSupport:
    """Build the two shared supports used by the internal one-bay fixture."""

    if side == "left":
        return build_rail_interior_support(keeper_state=keeper_state)
    if side == "right":
        return build_smooth_interior_support(keeper_state=keeper_state)
    raise ValueError("side must be 'left' or 'right'")


def bearing_contacts(
    origin_x_mm: float = 0.0,
    length_mm: float = NOMINAL_BAY_LENGTH_MM,
) -> tuple[BearingContact, BearingContact]:
    """Publish exact cap and selected-end-land contact areas."""

    pocket_area = REGISTRATION_POCKET_X_MM * REGISTRATION_POCKET_Y_MM
    net_cap = CAP_BEARING_WIDTH_MM * shelf.SHELF_DEPTH_MM - pocket_area
    net_land = (
        shelf.SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM * shelf.SHELF_DEPTH_MM
        - pocket_area
    )
    origin = float(origin_x_mm)
    length = float(length_mm)
    left_center = origin - SEAM_HALF_GAP_MM
    right_center = origin + length + SEAM_HALF_GAP_MM
    left_cap = (
        left_center - shelf.CORBEL_RUN_THICKNESS_MM / 2.0,
        left_center + shelf.CORBEL_RUN_THICKNESS_MM / 2.0,
    )
    right_cap = (
        right_center - shelf.CORBEL_RUN_THICKNESS_MM / 2.0,
        right_center + shelf.CORBEL_RUN_THICKNESS_MM / 2.0,
    )
    common = {
        "cap_overlap_width_mm": CAP_BEARING_WIDTH_MM,
        "selected_end_land_width_mm": shelf.SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
        "pocket_plan_area_mm2": pocket_area,
        "net_cap_contact_area_mm2": net_cap,
        "net_selected_land_contact_area_mm2": net_land,
        "contact_z_mm": shelf.CORBEL_INSTALLED_HEIGHT_MM,
    }
    return (
        BearingContact(
            side="left",
            support_center_x_mm=left_center,
            cap_x_bounds_mm=left_cap,
            cassette_overlap_x_bounds_mm=(
                origin,
                origin + CAP_BEARING_WIDTH_MM,
            ),
            **common,
        ),
        BearingContact(
            side="right",
            support_center_x_mm=right_center,
            cap_x_bounds_mm=right_cap,
            cassette_overlap_x_bounds_mm=(
                origin + length - CAP_BEARING_WIDTH_MM,
                origin + length,
            ),
            **common,
        ),
    )


def terminal_bearing_contact(
    side: Literal["left", "right"], origin_x_mm: float, length_mm: float
) -> TerminalBearingContact:
    """Publish the exact full-cap terminal bearing contract."""

    origin = float(origin_x_mm)
    cassette_end = origin + float(length_mm)
    if side == "left":
        center = origin + shelf.CORBEL_RUN_THICKNESS_MM / 2.0
        cap_bounds = (origin, origin + TERMINAL_CAP_BEARING_WIDTH_MM)
    elif side == "right":
        center = cassette_end - shelf.CORBEL_RUN_THICKNESS_MM / 2.0
        cap_bounds = (
            cassette_end - TERMINAL_CAP_BEARING_WIDTH_MM,
            cassette_end,
        )
    else:
        raise ValueError("terminal side must be 'left' or 'right'")
    pocket_area = REGISTRATION_POCKET_X_MM * REGISTRATION_POCKET_Y_MM
    return TerminalBearingContact(
        side=side,
        support_center_x_mm=center,
        cap_x_bounds_mm=cap_bounds,
        cassette_overlap_x_bounds_mm=cap_bounds,
        cap_overlap_width_mm=TERMINAL_CAP_BEARING_WIDTH_MM,
        key_offset_from_support_center_mm=(
            -TERMINAL_KEY_OFFSET_FROM_SUPPORT_MM
            if side == "left"
            else TERMINAL_KEY_OFFSET_FROM_SUPPORT_MM
        ),
        selected_end_land_width_mm=shelf.SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
        pocket_plan_area_mm2=pocket_area,
        net_cap_contact_area_mm2=(
            TERMINAL_CAP_BEARING_WIDTH_MM * shelf.SHELF_DEPTH_MM - pocket_area
        ),
        net_selected_land_contact_area_mm2=(
            shelf.SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM
            * shelf.SHELF_DEPTH_MM
            - pocket_area
        ),
        contact_z_mm=shelf.CORBEL_INSTALLED_HEIGHT_MM,
    )


def _map_interface_service(
    sequence: interface.ServiceTransforms, prefix: np.ndarray
) -> interface.ServiceTransforms:
    """Map an existing absolute local service sequence into this one bay."""

    def mapped(items: tuple[np.ndarray, ...]) -> tuple[np.ndarray, ...]:
        return tuple(prefix @ matrix for matrix in items)

    return interface.ServiceTransforms(
        approach=mapped(sequence.approach),
        insertion=prefix @ sequence.insertion,
        drop=mapped(sequence.drop),
        seated=prefix @ sequence.seated,
        removal_lift=mapped(sequence.removal_lift),
        removal_outward=mapped(sequence.removal_outward),
        increment_mm=sequence.increment_mm,
    )


def rail_mount_service_transforms(
    support_center_x_mm: float = LEFT_SUPPORT_CENTER_X_MM,
) -> interface.ServiceTransforms:
    """Return the exact existing rail sequence translated to the left support."""

    return _map_interface_service(
        interface.rail_mount_service_transforms(),
        rail_local_to_assembly_transform(support_center_x_mm),
    )


def blank_module_service_transforms(
    station_index: int = DEFAULT_RAIL_STATION_INDEX,
    *,
    support_center_x_mm: float = LEFT_SUPPORT_CENTER_X_MM,
) -> interface.ServiceTransforms:
    """Return an exact retained-blank sequence on the mounted one-bay rail."""

    rail_seated = rail_mount_service_transforms(support_center_x_mm).seated
    return _map_interface_service(
        interface.module_service_transforms(station_index), rail_seated
    )


def build_mounted_rail(
    support_center_x_mm: float = LEFT_SUPPORT_CENTER_X_MM,
) -> trimesh.Trimesh:
    """Build the separate retention rail at its seated boss datum."""

    return transformed(
        interface.build_mounted_retention_rail(),
        rail_mount_service_transforms(support_center_x_mm).seated,
    )


def build_installed_retained_blank(
    *,
    latch_state: interface.LatchState = "seated",
    station_index: int = DEFAULT_RAIL_STATION_INDEX,
    support_center_x_mm: float = LEFT_SUPPORT_CENTER_X_MM,
) -> trimesh.Trimesh:
    """Build the separate retained blank at one valid rail socket."""

    blank = interface.build_retained_accessory(
        "blank", latch_state=latch_state
    )
    return transformed(
        blank,
        blank_module_service_transforms(
            station_index, support_center_x_mm=support_center_x_mm
        ).seated,
    )


def orient_one_bay_blank_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Use the retained-module 180-degree-X saved orientation for the blank."""

    report = interface.saved_layer_island_report(mesh, layer_height_mm=0.2)
    if (
        report.support_required
        or report.first_layer_body_contact_area_mm2
        < interface.BLANK_MINIMUM_FIRST_LAYER_BODY_CONTACT_MM2
    ):
        raise ValueError("one-bay blank must satisfy the support-free print gate")
    return interface.orient_retained_module_for_print(mesh)


def build_one_bay(*, keeper_state: KeeperState = "seated") -> OneBayAssembly:
    """Build one internal seam-to-seam bay using support indices 1 and 2."""

    return OneBayAssembly(
        cassette=build_registered_cassette(),
        left_support=build_installed_support(
            "left", keeper_state="seated"
        ),
        right_support=build_installed_support(
            "right", keeper_state=keeper_state
        ),
        mounted_rail=build_mounted_rail(),
        seated_retained_blank=build_installed_retained_blank(),
        rail_support_index=RAIL_SUPPORT_INDEX,
        rail_station_index=DEFAULT_RAIL_STATION_INDEX,
        bearing_contacts=bearing_contacts(),
    )


def build_tiled_through_run(
    *, release_cassette_index: int | None = None
) -> TiledRunAssembly:
    """Build the complete design-math through run and its default rail kit."""

    bounds = THROUGH_RUN_LAYOUT.physical_module_bounds_mm
    bay_count = len(bounds)
    if release_cassette_index is not None:
        if isinstance(release_cassette_index, bool) or not isinstance(
            release_cassette_index, int
        ):
            raise TypeError("release_cassette_index must be an exact integer")
        if release_cassette_index not in range(bay_count):
            raise IndexError(
                "release_cassette_index must identify one through cassette"
            )
    cassettes = tuple(
        build_registered_cassette(
            length_mm=right - left,
            origin_x_mm=left,
            left_registration="terminal" if index == 0 else "seam",
            right_registration=(
                "terminal" if index == bay_count - 1 else "seam"
            ),
            keeper_side="left" if index == bay_count - 1 else "right",
        )
        for index, (left, right) in enumerate(bounds)
    )
    supports: list[InstalledSupport] = [build_terminal_start_support()]
    for support_index in range(1, RAIL_SUPPORT_COUNT - 1):
        state: KeeperState = (
            "deflected"
            if (
                release_cassette_index != bay_count - 1
                and release_cassette_index == support_index - 1
            )
            else "seated"
        )
        next_state: KeeperState | None = (
            (
                "deflected"
                if release_cassette_index == bay_count - 1
                else "seated"
            )
            if support_index == RAIL_SUPPORT_COUNT - 2
            else None
        )
        center = THROUGH_RUN_LAYOUT.corbel_centers_mm[support_index]
        if support_index in DEFAULT_RAIL_SUPPORT_INDICES:
            support = build_rail_interior_support(
                center,
                support_index=support_index,
                keeper_state=state,
                next_keeper_state=next_state,
            )
        else:
            support = build_smooth_interior_support(
                center,
                support_index=support_index,
                keeper_state=state,
                next_keeper_state=next_state,
            )
        supports.append(support)
    supports.append(build_terminal_end_support())

    contacts: list[
        tuple[
            BearingContact | TerminalBearingContact,
            BearingContact | TerminalBearingContact,
        ]
    ] = []
    for index, cassette in enumerate(cassettes):
        origin = cassette.origin_x_mm
        length = cassette.metrics.module_length_mm
        seams = bearing_contacts(origin, length)
        left: BearingContact | TerminalBearingContact = (
            terminal_bearing_contact("left", origin, length)
            if index == 0
            else seams[0]
        )
        right: BearingContact | TerminalBearingContact = (
            terminal_bearing_contact("right", origin, length)
            if index == bay_count - 1
            else seams[1]
        )
        contacts.append((left, right))

    rails: list[trimesh.Trimesh] = []
    blanks: list[trimesh.Trimesh] = []
    blank_stations: list[int] = []
    for support_index in DEFAULT_RAIL_SUPPORT_INDICES:
        center = supports[support_index].center_x_mm
        rails.append(build_mounted_rail(center))
        for station_index in range(len(accessory.SOCKET_CENTER_Z_MM)):
            blanks.append(
                build_installed_retained_blank(
                    station_index=station_index,
                    support_center_x_mm=center,
                )
            )
            blank_stations.append(station_index)
    return TiledRunAssembly(
        cassettes=cassettes,
        supports=tuple(supports),
        mounted_rails=tuple(rails),
        seated_retained_blanks=tuple(blanks),
        rail_support_indices=DEFAULT_RAIL_SUPPORT_INDICES,
        rail_station_indices=tuple(blank_stations),
        bearing_contacts=tuple(contacts),
    )


def service_transforms() -> ServiceTransforms:
    """Return 0.2 mm vertical stations from clear approach to seated."""

    count = int(round(SERVICE_LIFT_MM / SERVICE_INCREMENT_MM))
    if abs(count * SERVICE_INCREMENT_MM - SERVICE_LIFT_MM) > 1.0e-9:
        raise AssertionError("Service lift must be an exact increment multiple")
    lifts = tuple(
        SERVICE_LIFT_MM - index * SERVICE_INCREMENT_MM
        for index in range(count + 1)
    )
    installation = tuple(translation(z=lift) for lift in lifts)
    return ServiceTransforms(
        installation=installation,
        removal=tuple(reversed(installation)),
        lift_mm=SERVICE_LIFT_MM,
        increment_mm=SERVICE_INCREMENT_MM,
    )


def keeper_strain_proxy() -> KeeperStrainProxy:
    """Return a geometry-only cantilever strain comparison for PETG trials."""

    strain = (
        1.5
        * KEEPER_FLEX_THICKNESS_MM
        * KEEPER_RELEASE_DEFLECTION_MM
        / KEEPER_FLEX_LENGTH_MM**2
    )
    return KeeperStrainProxy(
        arm_length_mm=KEEPER_FLEX_LENGTH_MM,
        arm_thickness_mm=KEEPER_FLEX_THICKNESS_MM,
        tip_deflection_mm=KEEPER_RELEASE_DEFLECTION_MM,
        surface_strain=strain,
        below_three_percent=strain < 0.03,
    )


def orient_installed_support_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Put installed ``(y, z)`` on the bed and the run axis in height."""

    matrix = np.asarray(
        (
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        dtype=float,
    )
    result = transformed(mesh, matrix)
    result.apply_translation(-result.bounds[0])
    return _clean(result)


def positive_overlap_volume(
    first: trimesh.Trimesh, second: trimesh.Trimesh
) -> float:
    """Return actual positive Manifold intersection volume in cubic mm."""

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
    """Return true only for one watertight positive-volume component."""

    return bool(
        mesh.is_watertight
        and mesh.is_winding_consistent
        and mesh.volume > 0.0
        and len(mesh.split(only_watertight=False)) == 1
    )
