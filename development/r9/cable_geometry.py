#!/usr/bin/env python3
"""Additive-only R9 cable-rail qualification geometry.

The R9 user direction keeps cable organization only on the two outer
bookends per shelf level.  This module therefore authors one separate,
two-socket rail fit coupon plus two common-key modules: a low-profile blank
and a three-position cable comb/hook.  It deliberately does *not* modify,
subtract from, or claim attachment to :mod:`support_geometry`.

The 0.4 mm keyed gravity interface is the conservative R8 fit-study geometry
reused at two stations instead of three.  Endpoint rail attachment, doorway
clearance, cable-loop clearance, retention under snagging, and load capacity
remain unqualified.  Every emitted part is PETG-only and zero-rated.

Installed coordinates are X across the rail, Y outward from the support, and
Z upward.  Saved meshes use ordinary XYZ print coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import warnings

import numpy as np
from shapely.geometry import GeometryCollection, Polygon
import trimesh

try:  # Package import and direct unittest discovery are both supported.
    from . import design_math, support_geometry
except ImportError:  # pragma: no cover - direct unittest discovery path
    import design_math  # type: ignore[no-redef]
    import support_geometry  # type: ignore[no-redef]


QUALIFICATION_ONLY = True
PRODUCTION_READY = False
PHYSICAL_QUALIFICATION_COMPLETE = False
PRINTED_MATERIAL = "PETG"
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0
STRUCTURAL_OR_SHELF_LOAD_CREDIT = False
SUPPORT_GEOMETRY_SUBTRACTION_ALLOWED = False
ENDPOINT_INSTALLED_CLEARANCE_QUALIFIED = False
ENDPOINT_ATTACHMENT_AUTHORED = False

NOMINAL_CLEARANCE_PER_FACE_MM = 0.4
RAIL_WIDTH_MM = 36.0
RAIL_HEIGHT_MM = 62.0
RAIL_THICKNESS_MM = 8.8
UNINTERRUPTED_BACK_WEB_MM = 2.4
FRONT_RETAINER_SKIN_MM = 2.0
SOCKET_CENTER_X_MM = RAIL_WIDTH_MM / 2.0
SOCKET_CENTER_Z_MM = (18.0, 44.0)
SOCKET_SERVICE_LIFT_MM = 8.0

# Exact R8 common-key datums retained for interface continuity.
LUG_STEM_WIDTH_MM = 6.0
LUG_STEM_DEPTH_MM = 2.5
LUG_HEAD_WIDTH_MM = 11.0
LUG_HEAD_DEPTH_MM = 3.6
LUG_HEIGHT_MM = 8.0
LUG_KEY_EXTENSION_MM = 1.5
MODULE_BASE_WIDTH_MM = 20.0
MODULE_BASE_HEIGHT_MM = 16.0
MODULE_BASE_THICKNESS_MM = 3.2

LAYER_HEIGHT_MM = 0.2
GEOMETRY_EPSILON = 1.0e-7


_CONFIG = design_math.load_config()
design_math.validate_config(_CONFIG)
_ACCESSORY_CONFIG = _CONFIG["accessory_system"]
if _ACCESSORY_CONFIG["rails_allowed_on_outer_feature_columns_only"] is not True:
    raise ValueError("R9 cable rails must remain limited to outer bookends")
if _ACCESSORY_CONFIG["rails_or_pegs_on_compact_supports_allowed"] is not False:
    raise ValueError("R9 compact supports must remain cable-hardware free")
if _ACCESSORY_CONFIG["rails_or_pegs_at_inside_corner_allowed"] is not False:
    raise ValueError("R9 inside-corner supports must remain cable-hardware free")
if _ACCESSORY_CONFIG["sockets_per_rail"] != 2:
    raise ValueError("R9 outer-bookend rail must have exactly two sockets")
if _ACCESSORY_CONFIG["rails_per_level"] != 2:
    raise ValueError("R9 must retain exactly two outer-bookend rails per level")


@dataclass(frozen=True)
class SocketSpec:
    clearance_per_face_mm: float
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
    station_index: int
    seated: np.ndarray
    insertion: np.ndarray
    service_lift_mm: float


@dataclass(frozen=True)
class ServicePath:
    station_index: int
    insertion_approach: tuple[np.ndarray, ...]
    gravity_drop: tuple[np.ndarray, ...]
    removal_lift: tuple[np.ndarray, ...]
    removal_outward: tuple[np.ndarray, ...]
    increment_mm: float


@dataclass(frozen=True)
class LayerIslandReport:
    layer_height_mm: float
    sampled_layer_count: int
    first_layer_contact_area_mm2: float
    island_layer_indices: tuple[int, ...]
    support_required: bool
    support_classification: str
    support_evidence: str


@dataclass(frozen=True)
class SavedCablePartEvidence:
    part_name: str
    orientation_id: str
    support_required: bool
    support_classification: str
    support_evidence: str
    body_count: int
    watertight: bool
    winding_consistent: bool
    envelope: support_geometry.PrintEnvelope


def _positive(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return result


def _clearance(value: float) -> float:
    result = _positive(value, "socket clearance per face")
    if result > 1.0:
        raise ValueError("Socket clearance must not exceed 1.0 mm per face")
    return result


def _clean(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("Geometry operation produced no mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    if not np.isfinite(mesh.vertices).all():
        raise ValueError("Geometry operation produced non-finite vertices")
    return mesh


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


def _cylinder_y(
    *, radius_mm: float, length_mm: float, center: tuple[float, float, float]
) -> trimesh.Trimesh:
    radius = _positive(radius_mm, "cylinder radius")
    length = _positive(length_mm, "cylinder length")
    transform = trimesh.transformations.rotation_matrix(
        -math.pi / 2.0, (1.0, 0.0, 0.0)
    )
    transform[:3, 3] = np.asarray(center, dtype=float)
    return _clean(
        trimesh.creation.cylinder(
            radius=radius,
            height=length,
            sections=64,
            transform=transform,
        )
    )


def _cylinder_z(
    *, radius_mm: float, length_mm: float, center: tuple[float, float, float]
) -> trimesh.Trimesh:
    radius = _positive(radius_mm, "cylinder radius")
    length = _positive(length_mm, "cylinder length")
    transform = trimesh.transformations.translation_matrix(center)
    return _clean(
        trimesh.creation.cylinder(
            radius=radius,
            height=length,
            sections=64,
            transform=transform,
        )
    )


def _union(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("At least one mesh is required for union")
    result = trimesh.boolean.union(meshes, engine="manifold", check_volume=True)
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def _difference(body: trimesh.Trimesh, cutters: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not cutters:
        return _clean(body.copy())
    cutter = _union(cutters)
    result = trimesh.boolean.difference(
        [body, cutter], engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean(result)


def socket_spec(
    *,
    center_z_mm: float,
    center_x_mm: float = SOCKET_CENTER_X_MM,
    clearance_per_face_mm: float = NOMINAL_CLEARANCE_PER_FACE_MM,
) -> SocketSpec:
    clearance = _clearance(clearance_per_face_mm)
    center_x = float(center_x_mm)
    center_z = float(center_z_mm)
    if not math.isfinite(center_x) or not math.isfinite(center_z):
        raise ValueError("Socket center coordinates must be finite")
    half_head = LUG_HEAD_WIDTH_MM / 2.0
    half_stem = LUG_STEM_WIDTH_MM / 2.0
    half_height = LUG_HEIGHT_MM / 2.0
    pocket_bottom = center_z - half_height - clearance
    pocket_top = center_z + SOCKET_SERVICE_LIFT_MM + half_height + clearance
    entry_bottom = center_z + SOCKET_SERVICE_LIFT_MM - half_height - clearance
    return SocketSpec(
        clearance_per_face_mm=clearance,
        center_x_mm=center_x,
        center_z_mm=center_z,
        cavity_back_y_mm=UNINTERRUPTED_BACK_WEB_MM,
        undercut_front_y_mm=RAIL_THICKNESS_MM - FRONT_RETAINER_SKIN_MM,
        front_y_mm=RAIL_THICKNESS_MM,
        main_pocket_width_mm=LUG_HEAD_WIDTH_MM + 2.0 * clearance,
        keyed_pocket_width_mm=(
            LUG_HEAD_WIDTH_MM + LUG_KEY_EXTENSION_MM + 2.0 * clearance
        ),
        neck_width_mm=LUG_STEM_WIDTH_MM + 2.0 * clearance,
        pocket_bottom_z_mm=pocket_bottom,
        pocket_top_z_mm=pocket_top,
        entry_bottom_z_mm=entry_bottom,
        entry_top_z_mm=pocket_top,
        service_lift_mm=SOCKET_SERVICE_LIFT_MM,
    )


def socket_cutters(
    *,
    center_z_mm: float,
    center_x_mm: float = SOCKET_CENTER_X_MM,
    clearance_per_face_mm: float = NOMINAL_CLEARANCE_PER_FACE_MM,
) -> tuple[trimesh.Trimesh, ...]:
    spec = socket_spec(
        center_z_mm=center_z_mm,
        center_x_mm=center_x_mm,
        clearance_per_face_mm=clearance_per_face_mm,
    )
    half_head = spec.main_pocket_width_mm / 2.0
    half_stem = spec.neck_width_mm / 2.0
    cutter_front = RAIL_THICKNESS_MM + 0.05
    pocket_z = (spec.pocket_bottom_z_mm, spec.pocket_top_z_mm)
    entry_z = (spec.entry_bottom_z_mm, spec.entry_top_z_mm)
    main_pocket = _box(
        (spec.center_x_mm - half_head, spec.center_x_mm + half_head),
        (UNINTERRUPTED_BACK_WEB_MM, spec.undercut_front_y_mm),
        pocket_z,
    )
    keyed_extension = _box(
        (
            spec.center_x_mm
            - LUG_HEAD_WIDTH_MM / 2.0
            - LUG_KEY_EXTENSION_MM
            - spec.clearance_per_face_mm,
            spec.center_x_mm - LUG_HEAD_WIDTH_MM / 2.0 + 0.01,
        ),
        (UNINTERRUPTED_BACK_WEB_MM, spec.undercut_front_y_mm),
        pocket_z,
    )
    neck = _box(
        (spec.center_x_mm - half_stem, spec.center_x_mm + half_stem),
        (spec.undercut_front_y_mm - 0.2, cutter_front),
        pocket_z,
    )
    insertion_window = _box(
        (
            spec.center_x_mm
            - LUG_HEAD_WIDTH_MM / 2.0
            - LUG_KEY_EXTENSION_MM
            - spec.clearance_per_face_mm,
            spec.center_x_mm + half_head,
        ),
        (spec.undercut_front_y_mm - 0.2, cutter_front),
        entry_z,
    )
    return main_pocket, keyed_extension, neck, insertion_window


def build_two_socket_outer_bookend_rail_fit_coupon(
    *, clearance_per_face_mm: float = NOMINAL_CLEARANCE_PER_FACE_MM
) -> trimesh.Trimesh:
    """Build the separate 36 x 62 x 8.8 mm additive rail fit coupon."""

    clearance = _clearance(clearance_per_face_mm)
    rail = _box(
        (0.0, RAIL_WIDTH_MM),
        (0.0, RAIL_THICKNESS_MM),
        (0.0, RAIL_HEIGHT_MM),
    )
    cutters: list[trimesh.Trimesh] = []
    for center_z in SOCKET_CENTER_Z_MM:
        cutters.extend(
            socket_cutters(
                center_z_mm=center_z,
                clearance_per_face_mm=clearance,
            )
        )
    return _difference(rail, cutters)


def build_two_socket_additive_rail_fit_coupon(
    *, clearance_per_face_mm: float = NOMINAL_CLEARANCE_PER_FACE_MM
) -> trimesh.Trimesh:
    """Short alias for the outer-bookend rail coupon builder."""

    return build_two_socket_outer_bookend_rail_fit_coupon(
        clearance_per_face_mm=clearance_per_face_mm
    )


def build_common_module_base(
    *, clearance_per_face_mm: float = NOMINAL_CLEARANCE_PER_FACE_MM
) -> trimesh.Trimesh:
    """Build the low-profile pad and common keyed gravity T-lug."""

    clearance = _clearance(clearance_per_face_mm)
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
        RAIL_THICKNESS_MM - FRONT_RETAINER_SKIN_MM - UNINTERRUPTED_BACK_WEB_MM
    )
    head_depth = cavity_depth - 2.0 * clearance
    if head_depth <= 0.0:
        raise ValueError("Clearance consumes the T-head cavity depth")
    head_center_y = (
        UNINTERRUPTED_BACK_WEB_MM + cavity_depth / 2.0 - RAIL_THICKNESS_MM
    )
    head_y = (head_center_y - head_depth / 2.0, head_center_y + head_depth / 2.0)
    if math.isclose(clearance, 0.4, abs_tol=1.0e-12) and not math.isclose(
        head_depth, LUG_HEAD_DEPTH_MM, abs_tol=1.0e-12
    ):
        raise AssertionError("Nominal R8 T-head depth drifted")
    head = _box(
        (-LUG_HEAD_WIDTH_MM / 2.0, LUG_HEAD_WIDTH_MM / 2.0),
        head_y,
        (-LUG_HEIGHT_MM / 2.0, LUG_HEIGHT_MM / 2.0),
    )
    key = _box(
        (
            -LUG_HEAD_WIDTH_MM / 2.0 - LUG_KEY_EXTENSION_MM,
            -LUG_HEAD_WIDTH_MM / 2.0 + 0.1,
        ),
        head_y,
        (-LUG_HEIGHT_MM / 2.0, LUG_HEIGHT_MM / 2.0),
    )
    return _union([base, stem, head, key])


def build_flush_blank_module() -> trimesh.Trimesh:
    """Build the low-profile common pad with no projecting organizer."""

    return build_common_module_base()


def build_multi_cable_organizer_hook_module() -> trimesh.Trimesh:
    """Build a three-position comb/hook for lightweight cable organization."""

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
    return _union(parts)


def seating_transforms(station_index: int) -> SeatingTransforms:
    if station_index not in range(len(SOCKET_CENTER_Z_MM)):
        raise IndexError("station_index must identify one of the two sockets")
    seated = np.eye(4, dtype=float)
    seated[:3, 3] = (
        SOCKET_CENTER_X_MM,
        RAIL_THICKNESS_MM,
        SOCKET_CENTER_Z_MM[station_index],
    )
    insertion = seated.copy()
    insertion[2, 3] += SOCKET_SERVICE_LIFT_MM
    return SeatingTransforms(
        station_index=station_index,
        seated=seated,
        insertion=insertion,
        service_lift_mm=SOCKET_SERVICE_LIFT_MM,
    )


def service_path_transforms(
    station_index: int, *, increment_mm: float = 1.0, outward_approach_mm: float = 6.0
) -> ServicePath:
    """Return a sampled straight-in / gravity-drop path and its exact reverse."""

    transforms = seating_transforms(station_index)
    increment = _positive(increment_mm, "service-path increment")
    approach = _positive(outward_approach_mm, "outward approach")
    if not math.isclose(
        approach / increment, round(approach / increment), abs_tol=1.0e-9
    ) or not math.isclose(
        SOCKET_SERVICE_LIFT_MM / increment,
        round(SOCKET_SERVICE_LIFT_MM / increment),
        abs_tol=1.0e-9,
    ):
        raise ValueError("Service distances must be integer multiples of increment")

    insertion_approach: list[np.ndarray] = []
    for outward in np.linspace(approach, 0.0, int(round(approach / increment)) + 1):
        matrix = transforms.insertion.copy()
        matrix[1, 3] += float(outward)
        insertion_approach.append(matrix)
    gravity_drop: list[np.ndarray] = []
    for lift in np.linspace(
        SOCKET_SERVICE_LIFT_MM,
        0.0,
        int(round(SOCKET_SERVICE_LIFT_MM / increment)) + 1,
    ):
        matrix = transforms.seated.copy()
        matrix[2, 3] += float(lift)
        gravity_drop.append(matrix)
    return ServicePath(
        station_index=station_index,
        insertion_approach=tuple(insertion_approach),
        gravity_drop=tuple(gravity_drop),
        removal_lift=tuple(reversed(gravity_drop)),
        removal_outward=tuple(reversed(insertion_approach)),
        increment_mm=increment,
    )


def transformed_module(
    mesh: trimesh.Trimesh, station_index: int, *, insertion: bool
) -> trimesh.Trimesh:
    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty module mesh is required")
    transforms = seating_transforms(station_index)
    result = mesh.copy()
    result.apply_transform(transforms.insertion if insertion else transforms.seated)
    return _clean(result)


def positive_intersection_volume(
    first: trimesh.Trimesh, second: trimesh.Trimesh
) -> float:
    """Return Manifold intersection volume, treating contact faces as zero."""

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", category=RuntimeWarning, module=r"trimesh\.triangles"
        )
        result = trimesh.boolean.intersection(
            [first, second], engine="manifold", check_volume=True
        )
        if result is None or (isinstance(result, list) and not result):
            return 0.0
        if isinstance(result, list):
            result = trimesh.util.concatenate(result)
        if result.is_empty:
            return 0.0
        volume = abs(float(result.volume))
        return 0.0 if volume <= 1.0e-10 else volume


def _normalize(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    result = _clean(mesh.copy())
    result.apply_translation(-result.bounds[0])
    return _clean(result)


def orient_rail_back_web_on_plate(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Place installed X/Z on the plate and grow outward from the solid web."""

    result = _clean(mesh.copy())
    source = np.asarray(result.vertices, dtype=float).copy()
    result.vertices = source[:, (0, 2, 1)]
    return _normalize(result)


def orient_module_broad_side_on_plate(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Place local minimum Z on the plate for the blank and comb modules."""

    return _normalize(mesh)


def build_all_cable_qualification_parts() -> dict[str, trimesh.Trimesh]:
    return {
        "r9_two_socket_outer_bookend_rail_fit_coupon": (
            build_two_socket_outer_bookend_rail_fit_coupon()
        ),
        "r9_flush_blank_cable_module": build_flush_blank_module(),
        "r9_multi_cable_comb_hook_module": (
            build_multi_cable_organizer_hook_module()
        ),
    }


def build_saved_cable_qualification_parts() -> dict[str, trimesh.Trimesh]:
    installed = build_all_cable_qualification_parts()
    return {
        "r9_two_socket_outer_bookend_rail_fit_coupon": orient_rail_back_web_on_plate(
            installed["r9_two_socket_outer_bookend_rail_fit_coupon"]
        ),
        "r9_flush_blank_cable_module": orient_module_broad_side_on_plate(
            installed["r9_flush_blank_cable_module"]
        ),
        "r9_multi_cable_comb_hook_module": orient_module_broad_side_on_plate(
            installed["r9_multi_cable_comb_hook_module"]
        ),
    }


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
    oriented_mesh: trimesh.Trimesh, *, layer_height_mm: float = LAYER_HEIGHT_MM
) -> LayerIslandReport:
    """Detect any layer component with no positive overlap below it."""

    if not isinstance(oriented_mesh, trimesh.Trimesh) or oriented_mesh.is_empty:
        raise ValueError("A nonempty saved mesh is required")
    layer = _positive(layer_height_mm, "layer height")
    height = float(oriented_mesh.extents[2])
    ratio = height / layer
    nearest = round(ratio)
    count = (
        int(nearest)
        if math.isclose(ratio, nearest, rel_tol=0.0, abs_tol=1.0e-5)
        else int(math.ceil(ratio))
    )
    if count < 1:
        raise ValueError("Saved mesh must contain at least one layer")
    previous = None
    islands: list[int] = []
    first_layer_area = 0.0
    minimum_z = float(oriented_mesh.bounds[0, 2])
    for index in range(count):
        bottom = index * layer
        deposited = min(layer, height - bottom)
        region = _section_material_region(
            oriented_mesh, minimum_z + bottom + 0.5 * deposited
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
    evidence = (
        "disconnected component begins at saved layer index "
        + ",".join(str(index) for index in islands)
        if support_required
        else "every saved-layer component overlaps deposited material below"
    )
    return LayerIslandReport(
        layer_height_mm=layer,
        sampled_layer_count=count,
        first_layer_contact_area_mm2=first_layer_area,
        island_layer_indices=tuple(islands),
        support_required=support_required,
        support_classification=(
            "support_required" if support_required else "support_free"
        ),
        support_evidence=evidence,
    )


def saved_cable_print_evidence() -> tuple[SavedCablePartEvidence, ...]:
    saved = build_saved_cable_qualification_parts()
    orientations = {
        "r9_two_socket_outer_bookend_rail_fit_coupon": (
            "solid_back_web_on_plate_installed_xz_bed"
        ),
        "r9_flush_blank_cable_module": "local_minimum_z_broad_side_on_plate",
        "r9_multi_cable_comb_hook_module": "local_minimum_z_broad_side_on_plate",
    }
    evidence: list[SavedCablePartEvidence] = []
    for name, mesh in saved.items():
        report = saved_layer_island_report(mesh)
        evidence.append(
            SavedCablePartEvidence(
                part_name=name,
                orientation_id=orientations[name],
                support_required=report.support_required,
                support_classification=report.support_classification,
                support_evidence=report.support_evidence,
                body_count=len(mesh.split(only_watertight=False)),
                watertight=bool(mesh.is_watertight),
                winding_consistent=bool(mesh.is_winding_consistent),
                envelope=support_geometry.print_envelope_with_margins(mesh),
            )
        )
    return tuple(evidence)
