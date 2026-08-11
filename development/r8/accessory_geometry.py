#!/usr/bin/env python3
"""Qualification-only CAD for the R8 removable cable-accessory rail.

The coordinate convention is intentionally explicit:

* ``x`` is across the 36 mm faceplate;
* ``y`` points out from the structural D-frame and wall;
* ``z`` is vertical in the installed shelf.

The rail is a separate, additive part.  Its socket cutters never extend behind
``y = 2.4`` mm, so an uninterrupted 2.4 mm PETG back web remains between every
receiver and the structural D-frame.  Nothing in this module emits a cut into
the D-frame itself.

These meshes and calculations carry *zero* load rating.  They exist only to
make fit, printability, and physical qualification coupons repeatable.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import math
from typing import Literal

import numpy as np
import trimesh


# Faceplate and socket geometry, millimetres.
FACEPLATE_WIDTH_MM = 36.0
FACEPLATE_HEIGHT_MM = 88.0
FACEPLATE_THICKNESS_MM = 8.8
UNINTERRUPTED_BACK_WEB_MM = 2.4
FRONT_RETAINER_SKIN_MM = 2.0
SOCKET_CENTER_Z_MM = (20.0, 46.0, 72.0)
SOCKET_CENTER_X_MM = FACEPLATE_WIDTH_MM / 2.0
SOCKET_SERVICE_LIFT_MM = 8.0
NOMINAL_CLEARANCE_MM = 0.4
CLEARANCE_LADDER_MM = (0.2, 0.3, 0.4, 0.5)

# One common, asymmetric gravity T-lug is used by every module.
LUG_STEM_WIDTH_MM = 6.0
LUG_STEM_DEPTH_MM = 2.5
LUG_HEAD_WIDTH_MM = 11.0
LUG_HEAD_DEPTH_MM = 3.6
LUG_HEIGHT_MM = 8.0
LUG_KEY_EXTENSION_MM = 1.5
MODULE_BASE_WIDTH_MM = 20.0
MODULE_BASE_HEIGHT_MM = 16.0
MODULE_BASE_THICKNESS_MM = 3.2

# Print and release state.  The zero values are deliberate fail-closed gates.
A1_MINI_VOLUME_MM = (180.0, 180.0, 180.0)
QUALIFICATION_ONLY = True
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0

AccessoryKind = Literal["blank", "single_peg", "three_cable_comb", "coil_j_hook"]


@dataclass(frozen=True)
class SocketSpec:
    """Analytic dimensions of one keyed, gravity-seated receiver."""

    clearance_mm: float
    center_x_mm: float
    center_z_mm: float
    cavity_back_y_mm: float
    undercut_front_y_mm: float
    front_y_mm: float
    main_pocket_width_mm: float
    keyed_pocket_width_mm: float
    neck_width_mm: float
    pocket_bottom_z_mm: float
    pocket_top_z_mm: float
    entry_bottom_z_mm: float
    entry_top_z_mm: float
    service_lift_mm: float


@dataclass(frozen=True)
class SeatingTransforms:
    """Installed and insertion transforms for a local accessory module."""

    station_index: int
    seated: np.ndarray
    insertion: np.ndarray
    service_lift_mm: float


@dataclass(frozen=True)
class PrintEnvelope:
    """A saved mesh orientation and its A1 mini fit result."""

    part_mm: tuple[float, float, float]
    with_brim_mm: tuple[float, float, float]
    printable_volume_mm: tuple[float, float, float]
    brim_object_gap_mm: float
    fits: bool


@dataclass(frozen=True)
class StrainProxy:
    """A comparison-only rectangular-root surface-strain estimate.

    This Euler-Bernoulli expression is useful for comparing prototype roots;
    it is not FEA, a PETG material allowables calculation, or a load rating.
    """

    force_n: float
    projection_mm: float
    root_width_mm: float
    root_height_mm: float
    assumed_modulus_mpa: float
    root_moment_n_mm: float
    second_moment_mm4: float
    surface_strain: float


@dataclass(frozen=True)
class ClearanceLadder:
    """One connected receiver bar and four individually printable common keys."""

    clearances_mm: tuple[float, ...]
    receiver: trimesh.Trimesh
    keys: tuple[trimesh.Trimesh, ...]
    station_centers_x_mm: tuple[float, ...]


def _box(
    x_bounds: tuple[float, float],
    y_bounds: tuple[float, float],
    z_bounds: tuple[float, float],
) -> trimesh.Trimesh:
    """Create an axis-aligned cuboid from exact minimum/maximum bounds."""

    bounds = (x_bounds, y_bounds, z_bounds)
    if any(high <= low for low, high in bounds):
        raise ValueError("Every box extent must be positive")
    extents = np.array([high - low for low, high in bounds], dtype=float)
    center = np.array([(low + high) / 2.0 for low, high in bounds], dtype=float)
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(center)
    return mesh


def _cylinder_y(
    *, radius_mm: float, length_mm: float, center: tuple[float, float, float]
) -> trimesh.Trimesh:
    """Create a deterministic 64-sided cylinder whose axis is global ``y``."""

    if radius_mm <= 0.0 or length_mm <= 0.0:
        raise ValueError("Cylinder radius and length must be positive")
    transform = trimesh.transformations.rotation_matrix(-math.pi / 2.0, (1.0, 0.0, 0.0))
    transform[:3, 3] = np.asarray(center, dtype=float)
    return trimesh.creation.cylinder(
        radius=radius_mm,
        height=length_mm,
        sections=64,
        transform=transform,
    )


def _cylinder_z(
    *, radius_mm: float, length_mm: float, center: tuple[float, float, float]
) -> trimesh.Trimesh:
    if radius_mm <= 0.0 or length_mm <= 0.0:
        raise ValueError("Cylinder radius and length must be positive")
    transform = trimesh.transformations.translation_matrix(center)
    return trimesh.creation.cylinder(
        radius=radius_mm,
        height=length_mm,
        sections=64,
        transform=transform,
    )


def _boolean_union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("At least one mesh is required")
    result = trimesh.boolean.union(meshes, engine="manifold", check_volume=True)
    if not isinstance(result, trimesh.Trimesh):
        raise RuntimeError("Manifold union did not return one mesh")
    result.merge_vertices()
    result.remove_unreferenced_vertices()
    result.fix_normals(multibody=True)
    return result


def _boolean_difference(
    body: trimesh.Trimesh, cutters: list[trimesh.Trimesh]
) -> trimesh.Trimesh:
    if not cutters:
        return body.copy()
    cutter = _boolean_union(cutters)
    result = trimesh.boolean.difference(
        [body, cutter], engine="manifold", check_volume=True
    )
    if not isinstance(result, trimesh.Trimesh):
        raise RuntimeError("Manifold difference did not return one mesh")
    result.merge_vertices()
    result.remove_unreferenced_vertices()
    result.fix_normals(multibody=True)
    return result


def socket_spec(
    *,
    center_x_mm: float = SOCKET_CENTER_X_MM,
    center_z_mm: float,
    clearance_mm: float = NOMINAL_CLEARANCE_MM,
) -> SocketSpec:
    """Return the exact cutter envelope for one socket.

    ``clearance_mm`` is radial/per-side clearance around the lug in the
    installed ``x-z`` plane.  The nominal lug depth is centered in the
    undercut and leaves the same 0.4 mm at its front and rear faces.
    """

    if clearance_mm <= 0.0 or clearance_mm > 1.0:
        raise ValueError("Prototype socket clearance must be in (0, 1.0] mm")
    half_head = LUG_HEAD_WIDTH_MM / 2.0
    half_stem = LUG_STEM_WIDTH_MM / 2.0
    half_height = LUG_HEIGHT_MM / 2.0
    pocket_bottom = center_z_mm - half_height - clearance_mm
    pocket_top = center_z_mm + SOCKET_SERVICE_LIFT_MM + half_height + clearance_mm
    entry_bottom = center_z_mm + SOCKET_SERVICE_LIFT_MM - half_height - clearance_mm
    return SocketSpec(
        clearance_mm=clearance_mm,
        center_x_mm=center_x_mm,
        center_z_mm=center_z_mm,
        cavity_back_y_mm=UNINTERRUPTED_BACK_WEB_MM,
        undercut_front_y_mm=FACEPLATE_THICKNESS_MM - FRONT_RETAINER_SKIN_MM,
        front_y_mm=FACEPLATE_THICKNESS_MM,
        main_pocket_width_mm=2.0 * (half_head + clearance_mm),
        keyed_pocket_width_mm=(
            LUG_HEAD_WIDTH_MM + LUG_KEY_EXTENSION_MM + 2.0 * clearance_mm
        ),
        neck_width_mm=2.0 * (half_stem + clearance_mm),
        pocket_bottom_z_mm=pocket_bottom,
        pocket_top_z_mm=pocket_top,
        entry_bottom_z_mm=entry_bottom,
        entry_top_z_mm=pocket_top,
        service_lift_mm=SOCKET_SERVICE_LIFT_MM,
    )


def socket_cutters(
    *,
    center_x_mm: float = SOCKET_CENTER_X_MM,
    center_z_mm: float,
    clearance_mm: float = NOMINAL_CLEARANCE_MM,
) -> tuple[trimesh.Trimesh, ...]:
    """Build the undercut, keyed tongue, neck, and insertion-window cutters."""

    spec = socket_spec(
        center_x_mm=center_x_mm,
        center_z_mm=center_z_mm,
        clearance_mm=clearance_mm,
    )
    half_head = spec.main_pocket_width_mm / 2.0
    half_stem = spec.neck_width_mm / 2.0
    # A 0.05 mm overshoot at the exposed face makes the Boolean reliably open.
    cutter_front = FACEPLATE_THICKNESS_MM + 0.05
    pocket_z = (spec.pocket_bottom_z_mm, spec.pocket_top_z_mm)
    entry_z = (spec.entry_bottom_z_mm, spec.entry_top_z_mm)
    main_pocket = _box(
        (center_x_mm - half_head, center_x_mm + half_head),
        (UNINTERRUPTED_BACK_WEB_MM, spec.undercut_front_y_mm),
        pocket_z,
    )
    # The left-only extension is the key.  A 180-degree rotated lug has its
    # tongue on the right and therefore cannot enter this cavity.
    keyed_extension = _box(
        (
            center_x_mm - LUG_HEAD_WIDTH_MM / 2.0 - LUG_KEY_EXTENSION_MM - clearance_mm,
            center_x_mm - LUG_HEAD_WIDTH_MM / 2.0 + 0.01,
        ),
        (UNINTERRUPTED_BACK_WEB_MM, spec.undercut_front_y_mm),
        pocket_z,
    )
    neck = _box(
        (center_x_mm - half_stem, center_x_mm + half_stem),
        (spec.undercut_front_y_mm - 0.2, cutter_front),
        pocket_z,
    )
    insertion_window = _box(
        (
            center_x_mm - LUG_HEAD_WIDTH_MM / 2.0 - LUG_KEY_EXTENSION_MM - clearance_mm,
            center_x_mm + half_head,
        ),
        (spec.undercut_front_y_mm - 0.2, cutter_front),
        entry_z,
    )
    return main_pocket, keyed_extension, neck, insertion_window


def build_faceplate_rail(
    *, clearance_mm: float = NOMINAL_CLEARANCE_MM
) -> trimesh.Trimesh:
    """Build the 36 x 88 x 8.8 mm additive three-station receiver rail."""

    plate = _box(
        (0.0, FACEPLATE_WIDTH_MM),
        (0.0, FACEPLATE_THICKNESS_MM),
        (0.0, FACEPLATE_HEIGHT_MM),
    )
    cutters: list[trimesh.Trimesh] = []
    for center_z in SOCKET_CENTER_Z_MM:
        cutters.extend(socket_cutters(center_z_mm=center_z, clearance_mm=clearance_mm))
    return _boolean_difference(plate, cutters)


def build_common_module_base(
    *, clearance_mm: float = NOMINAL_CLEARANCE_MM
) -> trimesh.Trimesh:
    """Build the keyed T-lug plus the common external module pad.

    ``clearance_mm`` changes the T-head depth as well as the ladder's x/z
    cutter allowance.  The four physical ladder keys therefore qualify the
    tight print axis instead of varying only two axes around one fixed head.
    """

    if clearance_mm <= 0.0 or clearance_mm > 1.0:
        raise ValueError("Prototype module clearance must be in (0, 1.0] mm")

    base = _box(
        (-MODULE_BASE_WIDTH_MM / 2.0, MODULE_BASE_WIDTH_MM / 2.0),
        (0.0, MODULE_BASE_THICKNESS_MM),
        (-MODULE_BASE_HEIGHT_MM / 2.0, MODULE_BASE_HEIGHT_MM / 2.0),
    )
    stem = _box(
        (-LUG_STEM_WIDTH_MM / 2.0, LUG_STEM_WIDTH_MM / 2.0),
        (-LUG_STEM_DEPTH_MM, 0.2),
        (-LUG_HEIGHT_MM / 2.0, LUG_HEIGHT_MM / 2.0),
    )
    cavity_depth = (
        FACEPLATE_THICKNESS_MM
        - FRONT_RETAINER_SKIN_MM
        - UNINTERRUPTED_BACK_WEB_MM
    )
    head_depth = cavity_depth - 2.0 * clearance_mm
    if head_depth <= 0.0:
        raise ValueError("Clearance consumes the full T-head cavity depth")
    head_center_local_y = (
        UNINTERRUPTED_BACK_WEB_MM
        + cavity_depth / 2.0
        - FACEPLATE_THICKNESS_MM
    )
    head_y_bounds = (
        head_center_local_y - head_depth / 2.0,
        head_center_local_y + head_depth / 2.0,
    )
    if abs(clearance_mm - NOMINAL_CLEARANCE_MM) <= 1.0e-12 and abs(
        head_depth - LUG_HEAD_DEPTH_MM
    ) > 1.0e-12:
        raise AssertionError("Nominal T-head depth drifted from its frozen value")
    head = _box(
        (-LUG_HEAD_WIDTH_MM / 2.0, LUG_HEAD_WIDTH_MM / 2.0),
        head_y_bounds,
        (-LUG_HEIGHT_MM / 2.0, LUG_HEIGHT_MM / 2.0),
    )
    key = _box(
        (
            -LUG_HEAD_WIDTH_MM / 2.0 - LUG_KEY_EXTENSION_MM,
            -LUG_HEAD_WIDTH_MM / 2.0 + 0.1,
        ),
        head_y_bounds,
        (-LUG_HEIGHT_MM / 2.0, LUG_HEIGHT_MM / 2.0),
    )
    return _boolean_union([base, stem, head, key])


def build_blank_cap() -> trimesh.Trimesh:
    """The common module base is itself the low-profile blank cap."""

    return build_common_module_base()


def build_single_peg() -> trimesh.Trimesh:
    """Build a 22 mm projection with a retained, rounded cable tip."""

    base = build_common_module_base()
    root = _box((-4.0, 4.0), (2.8, 7.0), (-4.0, 4.0))
    shaft = _cylinder_y(radius_mm=3.0, length_mm=20.0, center=(0.0, 15.0, 0.0))
    tip = _cylinder_z(radius_mm=3.0, length_mm=8.0, center=(0.0, 24.0, 3.0))
    return _boolean_union([base, root, shaft, tip])


def build_three_cable_comb() -> trimesh.Trimesh:
    """Build a three-position comb for lightweight individual cables."""

    base = build_common_module_base()
    crossbar = _box((-14.0, 14.0), (2.8, 8.0), (-4.0, 4.0))
    parts = [base, crossbar]
    for center_x in (-9.0, 0.0, 9.0):
        parts.append(
            _cylinder_y(
                radius_mm=2.5,
                length_mm=16.0,
                center=(center_x, 15.0, 0.0),
            )
        )
        parts.append(
            _cylinder_z(
                radius_mm=2.5,
                length_mm=7.0,
                center=(center_x, 22.0, 2.5),
            )
        )
    return _boolean_union(parts)


def build_coil_j_hook() -> trimesh.Trimesh:
    """Build a broad J-hook for a loose lightweight cable coil."""

    base = build_common_module_base()
    root = _box((-5.0, 5.0), (2.8, 8.0), (-5.0, 5.0))
    arm = _cylinder_y(radius_mm=4.0, length_mm=23.0, center=(0.0, 16.0, 0.0))
    elbow = trimesh.creation.icosphere(subdivisions=2, radius=4.0)
    elbow.apply_translation((0.0, 27.0, 0.0))
    tip = _cylinder_z(radius_mm=4.0, length_mm=16.0, center=(0.0, 27.0, 7.0))
    return _boolean_union([base, root, arm, elbow, tip])


def build_accessory(kind: AccessoryKind) -> trimesh.Trimesh:
    """Build one of the four common-key accessory modules."""

    builders = {
        "blank": build_blank_cap,
        "single_peg": build_single_peg,
        "three_cable_comb": build_three_cable_comb,
        "coil_j_hook": build_coil_j_hook,
    }
    try:
        builder = builders[kind]
    except KeyError as exc:
        raise ValueError(f"Unknown R8 accessory kind: {kind!r}") from exc
    return builder()


def seating_transforms(station_index: int) -> SeatingTransforms:
    """Return the seated transform and the straight-in insertion transform.

    A module is pushed through the widened entry window at ``z + 8`` mm and
    then dropped exactly 8 mm under gravity behind the narrow retainer neck.
    """

    if station_index not in range(len(SOCKET_CENTER_Z_MM)):
        raise IndexError("station_index must identify one of the three rail sockets")
    center_z = SOCKET_CENTER_Z_MM[station_index]
    seated = np.eye(4, dtype=float)
    seated[:3, 3] = (SOCKET_CENTER_X_MM, FACEPLATE_THICKNESS_MM, center_z)
    insertion = seated.copy()
    insertion[2, 3] += SOCKET_SERVICE_LIFT_MM
    return SeatingTransforms(
        station_index=station_index,
        seated=seated,
        insertion=insertion,
        service_lift_mm=SOCKET_SERVICE_LIFT_MM,
    )


def transformed_module(mesh: trimesh.Trimesh, station_index: int, *, insertion: bool) -> trimesh.Trimesh:
    """Place a local module at a rail's seated or insertion datum."""

    transforms = seating_transforms(station_index)
    result = mesh.copy()
    result.apply_transform(transforms.insertion if insertion else transforms.seated)
    return result


def build_clearance_ladder() -> ClearanceLadder:
    """Build the 0.2/0.3/0.4/0.5 mm physical fit ladder.

    The four sockets share one connected 132 x 32 mm receiver bar.  Each
    returned key is a separate one-body common module base.  The tuple order,
    left-to-right station order, and clearance order are identical.
    """

    width = 132.0
    height = 32.0
    centers = (18.0, 50.0, 82.0, 114.0)
    center_z = 12.0
    receiver = _box(
        (0.0, width),
        (0.0, FACEPLATE_THICKNESS_MM),
        (0.0, height),
    )
    cutters: list[trimesh.Trimesh] = []
    for center_x, clearance in zip(centers, CLEARANCE_LADDER_MM):
        cutters.extend(
            socket_cutters(
                center_x_mm=center_x,
                center_z_mm=center_z,
                clearance_mm=clearance,
            )
        )
    receiver = _boolean_difference(receiver, cutters)
    return ClearanceLadder(
        clearances_mm=CLEARANCE_LADDER_MM,
        receiver=receiver,
        keys=tuple(
            build_common_module_base(clearance_mm=clearance)
            for clearance in CLEARANCE_LADDER_MM
        ),
        station_centers_x_mm=centers,
    )


def rectangular_root_strain_proxy(
    *,
    force_n: float,
    projection_mm: float,
    root_width_mm: float,
    root_height_mm: float,
    assumed_modulus_mpa: float = 1800.0,
) -> StrainProxy:
    """Return a comparison-only fixed-end strain proxy for a root section."""

    values = (force_n, projection_mm, root_width_mm, root_height_mm, assumed_modulus_mpa)
    if force_n < 0.0 or any(value <= 0.0 for value in values[1:]):
        raise ValueError("Force cannot be negative and geometry/modulus must be positive")
    moment = force_n * projection_mm
    second_moment = root_width_mm * root_height_mm**3 / 12.0
    strain = moment * (root_height_mm / 2.0) / (assumed_modulus_mpa * second_moment)
    return StrainProxy(
        force_n=force_n,
        projection_mm=projection_mm,
        root_width_mm=root_width_mm,
        root_height_mm=root_height_mm,
        assumed_modulus_mpa=assumed_modulus_mpa,
        root_moment_n_mm=moment,
        second_moment_mm4=second_moment,
        surface_strain=strain,
    )


def mesh_is_one_body(mesh: trimesh.Trimesh) -> bool:
    """Return true only for one watertight, positive-volume connected body."""

    components = mesh.split(only_watertight=False)
    return bool(mesh.is_watertight and mesh.volume > 0.0 and len(components) == 1)


def mesh_geometry_digest(mesh: trimesh.Trimesh, *, quantum_mm: float = 1.0e-6) -> str:
    """Hash canonical, order-independent quantized triangles.

    Sorting vertices inside every triangle and sorting all triangle rows makes
    this digest insensitive to vertex and face indexing while still freezing
    the actual CAD surface.
    """

    if quantum_mm <= 0.0:
        raise ValueError("Digest quantum must be positive")
    quantized = np.rint(np.asarray(mesh.triangles) / quantum_mm).astype("<i8")
    canonical_rows: list[tuple[int, ...]] = []
    for triangle in quantized:
        vertices = sorted(tuple(int(value) for value in vertex) for vertex in triangle)
        canonical_rows.append(tuple(itertools.chain.from_iterable(vertices)))
    canonical_rows.sort()
    canonical = np.asarray(canonical_rows, dtype="<i8")
    header = f"r8-accessory-triangles-v1\0{quantum_mm:.12g}\0{len(canonical_rows)}\0".encode(
        "ascii"
    )
    return hashlib.sha256(header + canonical.tobytes(order="C")).hexdigest()


def saved_print_envelope(
    mesh: trimesh.Trimesh,
    *,
    brim_mm: float = 5.0,
    brim_object_gap_mm: float = 0.0,
    bed_axes: tuple[int, int] = (0, 2),
) -> PrintEnvelope:
    """Check a declared face-down orientation against the A1 mini envelope.

    By default global ``x`` and installed ``z`` are on the build plate, while
    outward ``y`` becomes print height.  This is the broad face orientation for
    both the receiver rail and the accessory modules.
    """

    if (
        brim_mm < 0.0
        or brim_object_gap_mm < 0.0
        or len(set(bed_axes)) != 2
        or any(axis not in (0, 1, 2) for axis in bed_axes)
    ):
        raise ValueError("bed_axes must name two distinct XYZ axes and brim cannot be negative")
    height_axis = next(axis for axis in (0, 1, 2) if axis not in bed_axes)
    extents = tuple(float(value) for value in mesh.extents)
    part = (extents[bed_axes[0]], extents[bed_axes[1]], extents[height_axis])
    radial_margin = float(brim_mm) + float(brim_object_gap_mm)
    with_brim = (
        part[0] + 2.0 * radial_margin,
        part[1] + 2.0 * radial_margin,
        part[2],
    )
    fits = all(
        needed <= available + 1.0e-9
        for needed, available in zip(with_brim, A1_MINI_VOLUME_MM)
    )
    return PrintEnvelope(
        part_mm=part,
        with_brim_mm=with_brim,
        printable_volume_mm=A1_MINI_VOLUME_MM,
        brim_object_gap_mm=float(brim_object_gap_mm),
        fits=fits,
    )
