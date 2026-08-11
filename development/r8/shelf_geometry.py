#!/usr/bin/env python3
"""Qualification-only structural geometry for the R8 / 16B shelf direction.

This module intentionally emits no wall-fastener bores, accessory receivers,
load rating, or production authorization.  Coordinates are millimetres:

* ``x`` -- across the shelf run (the corbel's 32 mm thickness),
* ``q`` -- wall-to-front shelf projection, and
* ``e`` -- installed vertical elevation.

The corbel builders author their ``q/e`` profile in XY and extrude through X
as mesh Z.  That saved mesh orientation places a broad run-side face on the
build plate; callers may relabel axes when assembling an installed scene.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

import numpy as np
import trimesh


QUALIFICATION_ONLY = True
RATED_LOAD_KG = 0.0
RATED_LOAD_LB = 0.0

SHELF_DEPTH_MM = 152.4
CASSETTE_HEIGHT_MM = 30.0
CASSETTE_SKIN_MM = 3.2
CASSETTE_PERIMETER_MM = 4.8
CASSETTE_RIB_MM = 3.6
CASSETTE_MAX_CLEAR_SPAN_MM = 14.0
SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM = 6.4

CORBEL_PROJECTION_MM = 152.4
CORBEL_INSTALLED_HEIGHT_MM = 160.0
CORBEL_RUN_THICKNESS_MM = 32.0
CORBEL_WALL_CHORD_MM = 16.0
CORBEL_TOP_CHORD_MM = 16.0
CORBEL_ROOT_RADIUS_MM = 10.0
CORBEL_FRONT_NOSE_MM = 32.0
CORBEL_MINIMUM_CURVED_WEB_MM = 16.0

GEOMETRY_EPSILON = 1.0e-7


@dataclass(frozen=True)
class CofferMetrics:
    """Exact open-coffer dimensions used by one cassette seed."""

    module_length_mm: float
    depth_mm: float
    height_mm: float
    continuous_skin_mm: float
    perimeter_mm: float
    rib_mm: float
    cells_along_run: int
    cells_through_depth: int
    clear_span_along_run_mm: float
    clear_span_through_depth_mm: float
    maximum_clear_span_mm: float
    open_coffer_face: str


@dataclass(frozen=True)
class UBoxMetrics:
    """Exact dimensions of the lighter front-first cassette candidate."""

    module_length_mm: float
    depth_mm: float
    height_mm: float
    top_skin_mm: float
    bottom_skin_mm: float
    visible_front_wall_mm: float
    full_depth_end_land_mm: float
    internal_web_mm: float
    internal_web_count: int
    clear_panel_span_along_run_mm: float
    hidden_open_face: str


@dataclass(frozen=True)
class SeamBearingDatum:
    """A full-depth cassette-end land that can bear on a corbel cap."""

    side: str
    seam_plane_x_mm: float
    land_x_bounds_mm: tuple[float, float]
    depth_bounds_mm: tuple[float, float]
    underside_e_mm: float


@dataclass(frozen=True)
class PrintEnvelope:
    """An oriented mesh envelope including bed-edge process margins."""

    raw_part_mm: tuple[float, float, float]
    required_build_volume_mm: tuple[float, float, float]
    available_build_volume_mm: tuple[float, float, float]
    brim_mm: float
    brim_object_gap_mm: float
    reserve_per_bed_edge_mm: float
    fits: bool


@dataclass(frozen=True)
class LayerConnectivityReport:
    """Connectivity result for every nominal deposited corbel layer."""

    layer_height_mm: float
    sampled_layer_count: int
    failed_layer_indices: tuple[int, ...]
    all_layers_connected: bool


def _positive(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return result


def _clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Normalize topology after a primitive or Manifold boolean."""

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("Geometry operation produced an empty mesh")
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals(multibody=True)
    return mesh


def _box(
    size: tuple[float, float, float],
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> trimesh.Trimesh:
    extents = np.asarray([_positive(value, "box size") for value in size], dtype=float)
    mesh = trimesh.creation.box(extents=extents)
    mesh.apply_translation(np.asarray(origin, dtype=float) + extents / 2.0)
    return _clean_mesh(mesh)


def _boolean_difference(
    body: trimesh.Trimesh, cutters: Sequence[trimesh.Trimesh]
) -> trimesh.Trimesh:
    if not cutters:
        return body.copy()
    result = trimesh.boolean.difference(
        [body, *cutters], engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean_mesh(result)


def _boolean_union(meshes: Sequence[trimesh.Trimesh]) -> trimesh.Trimesh:
    if not meshes:
        raise ValueError("At least one mesh is required for union")
    result = trimesh.boolean.union(
        list(meshes), engine="manifold", check_volume=True
    )
    if isinstance(result, list):
        result = trimesh.util.concatenate(result)
    return _clean_mesh(result)


def _signed_polygon_area(points: np.ndarray) -> float:
    return 0.5 * float(
        np.dot(points[:, 0], np.roll(points[:, 1], -1))
        - np.dot(points[:, 1], np.roll(points[:, 0], -1))
    )


def _cross_2d(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ab = b - a
    ac = c - a
    return float(ab[0] * ac[1] - ab[1] * ac[0])


def _strictly_inside_triangle(
    point: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray
) -> bool:
    crosses = (
        _cross_2d(a, b, point),
        _cross_2d(b, c, point),
        _cross_2d(c, a, point),
    )
    return all(value > GEOMETRY_EPSILON for value in crosses)


def _ear_clip(points: np.ndarray) -> np.ndarray:
    """Triangulate one simple CCW polygon without optional 2D libraries."""

    if len(points) < 3:
        raise ValueError("A polygon needs at least three vertices")
    if _signed_polygon_area(points) < 0.0:
        points = points[::-1].copy()

    remaining = list(range(len(points)))
    triangles: list[tuple[int, int, int]] = []
    iteration_limit = len(points) * len(points)
    iterations = 0
    while len(remaining) > 3:
        ear_found = False
        for position, current in enumerate(remaining):
            previous = remaining[position - 1]
            following = remaining[(position + 1) % len(remaining)]
            a, b, c = points[[previous, current, following]]
            if _cross_2d(a, b, c) <= GEOMETRY_EPSILON:
                continue
            if any(
                _strictly_inside_triangle(points[index], a, b, c)
                for index in remaining
                if index not in (previous, current, following)
            ):
                continue
            triangles.append((previous, current, following))
            del remaining[position]
            ear_found = True
            break
        iterations += 1
        if not ear_found or iterations > iteration_limit:
            raise ValueError("Could not triangulate the supplied simple polygon")
    triangles.append(tuple(remaining))
    return np.asarray(triangles, dtype=np.int64)


def _polygon_prism(points_xy: Iterable[tuple[float, float]], height: float) -> trimesh.Trimesh:
    points = np.asarray(tuple(points_xy), dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("Polygon points must be an N by 2 array")
    if np.linalg.norm(points[0] - points[-1]) <= GEOMETRY_EPSILON:
        points = points[:-1]
    if _signed_polygon_area(points) < 0.0:
        points = points[::-1].copy()
    faces = _ear_clip(points)
    mesh = trimesh.creation.extrude_triangulation(
        points, faces, height=_positive(height, "prism height")
    )
    return _clean_mesh(mesh)


def _outer_corbel_profile() -> tuple[tuple[float, float], ...]:
    """The exact common outer envelope for both structural prototypes."""

    return (
        (0.0, 0.0),
        (CORBEL_WALL_CHORD_MM, 0.0),
        (CORBEL_PROJECTION_MM, CORBEL_INSTALLED_HEIGHT_MM - CORBEL_FRONT_NOSE_MM),
        (CORBEL_PROJECTION_MM, CORBEL_INSTALLED_HEIGHT_MM),
        (0.0, CORBEL_INSTALLED_HEIGHT_MM),
    )


def _cubic_bezier(
    p0: np.ndarray,
    p1: np.ndarray,
    p2: np.ndarray,
    p3: np.ndarray,
    samples: int,
) -> np.ndarray:
    t = np.linspace(0.0, 1.0, samples, dtype=float)[:, None]
    omt = 1.0 - t
    return (
        omt**3 * p0
        + 3.0 * omt**2 * t * p1
        + 3.0 * omt * t**2 * p2
        + t**3 * p3
    )


def _curved_corbel_cutout_profile() -> tuple[tuple[float, float], ...]:
    """Inner D opening with explicit R10 wall and top root transitions."""

    radius = CORBEL_ROOT_RADIUS_MM
    top_inner = CORBEL_INSTALLED_HEIGHT_MM - CORBEL_TOP_CHORD_MM
    front_inner = CORBEL_PROJECTION_MM - CORBEL_WALL_CHORD_MM

    # Begin at the wall/top inside corner, descend the wall, then turn through
    # a true R10 quarter-circle into the working curved web boundary.
    points: list[np.ndarray] = [np.asarray((CORBEL_WALL_CHORD_MM, top_inner))]
    curve_start_e = CORBEL_WALL_CHORD_MM + radius + 12.0
    wall_center = np.asarray(
        (CORBEL_WALL_CHORD_MM + radius, curve_start_e + radius)
    )
    for angle in np.linspace(math.pi, 1.5 * math.pi, 9):
        points.append(wall_center + radius * np.asarray((math.cos(angle), math.sin(angle))))

    curve_start = np.asarray((CORBEL_WALL_CHORD_MM + radius, curve_start_e))
    curve_end = np.asarray((front_inner - radius, top_inner - radius))
    curve = _cubic_bezier(
        curve_start,
        curve_start + np.asarray((22.0, 0.0)),
        curve_end - np.asarray((22.0, 0.0)),
        curve_end,
        41,
    )
    points.extend(curve[1:])

    top_center = np.asarray((front_inner - radius, top_inner))
    for angle in np.linspace(-0.5 * math.pi, 0.0, 9)[1:]:
        points.append(top_center + radius * np.asarray((math.cos(angle), math.sin(angle))))
    return tuple((float(point[0]), float(point[1])) for point in points)


def minimum_curved_web_thickness_mm() -> float:
    """Return the exact minimum normal gap between authored web boundaries.

    The working outer boundary is the straight load-path edge from the wall
    root to the 32 mm front nose.  The inner boundary is the sampled R10 /
    Bezier / R10 cutout polyline.  Distance to a straight line varies linearly
    along every polyline segment, so testing all authored vertices gives the
    exact minimum for this faceted CAD profile.
    """

    outer_start = np.asarray((CORBEL_WALL_CHORD_MM, 0.0), dtype=float)
    outer_end = np.asarray(
        (
            CORBEL_PROJECTION_MM,
            CORBEL_INSTALLED_HEIGHT_MM - CORBEL_FRONT_NOSE_MM,
        ),
        dtype=float,
    )
    direction = outer_end - outer_start
    length = float(np.linalg.norm(direction))
    inner = np.asarray(_curved_corbel_cutout_profile(), dtype=float)
    signed = (
        direction[0] * (inner[:, 1] - outer_start[1])
        - direction[1] * (inner[:, 0] - outer_start[0])
    ) / length
    if np.any(signed <= 0.0):
        raise AssertionError("The inner cutout crossed the working outer web edge")
    return float(np.min(signed))


def _corbel_from_cutout(cutout_profile: Sequence[tuple[float, float]]) -> trimesh.Trimesh:
    outer = _polygon_prism(_outer_corbel_profile(), CORBEL_RUN_THICKNESS_MM)
    # Oversize the cutter only through the extrusion axis.  Its q/e boundary
    # stays exact so the 16 mm wall and top chords remain dimensionally frozen.
    cutter = _polygon_prism(cutout_profile, CORBEL_RUN_THICKNESS_MM + 2.0)
    cutter.apply_translation((0.0, 0.0, -1.0))
    return _boolean_difference(outer, [cutter])


def build_d_frame_corbel() -> trimesh.Trimesh:
    """Build the one-piece 32 mm R8 D-frame qualification corbel.

    The mesh has no fastener bores and no accessory rail subtraction.  Its
    curved opening is not a capacity claim; it exists for controlled comparison
    against :func:`build_straight_diagonal_reference_corbel`.
    """

    return _corbel_from_cutout(_curved_corbel_cutout_profile())


def build_straight_diagonal_reference_corbel() -> trimesh.Trimesh:
    """Build a same-envelope, equal-volume straight-diagonal control corbel."""

    curved_cutout = np.asarray(_curved_corbel_cutout_profile(), dtype=float)
    target_cutout_area = abs(_signed_polygon_area(curved_cutout))
    top_inner = CORBEL_INSTALLED_HEIGHT_MM - CORBEL_TOP_CHORD_MM
    cutout_run = CORBEL_PROJECTION_MM - 2.0 * CORBEL_WALL_CHORD_MM
    wall_intercept = top_inner - 2.0 * target_cutout_area / cutout_run
    if not (0.0 < wall_intercept < top_inner):
        raise AssertionError("Equal-area straight reference has an invalid intercept")
    straight_cutout = (
        (CORBEL_WALL_CHORD_MM, top_inner),
        (CORBEL_WALL_CHORD_MM, wall_intercept),
        (CORBEL_PROJECTION_MM - CORBEL_WALL_CHORD_MM, top_inner),
    )
    return _corbel_from_cutout(straight_cutout)


def build_matched_corbel_pair() -> tuple[trimesh.Trimesh, trimesh.Trimesh]:
    """Return ``(curved_D_frame, straight_reference)`` qualification meshes."""

    return build_d_frame_corbel(), build_straight_diagonal_reference_corbel()


def _coffer_intervals(
    total_mm: float,
    *,
    perimeter_mm: float,
    rib_mm: float,
    maximum_clear_span_mm: float,
) -> tuple[tuple[tuple[float, float], ...], float]:
    inner = total_mm - 2.0 * perimeter_mm
    if inner <= 0.0:
        raise ValueError("Cassette perimeter consumes the coffer field")
    cells = max(1, math.ceil((inner + rib_mm) / (maximum_clear_span_mm + rib_mm)))
    clear = (inner - (cells - 1) * rib_mm) / cells
    if clear <= 0.0 or clear > maximum_clear_span_mm + GEOMETRY_EPSILON:
        raise ValueError("Could not satisfy the configured coffer clear span")
    intervals: list[tuple[float, float]] = []
    cursor = perimeter_mm
    for index in range(cells):
        start = cursor
        end = start + clear
        intervals.append((start, end))
        cursor = end + (rib_mm if index < cells - 1 else 0.0)
    if abs(intervals[-1][1] - (total_mm - perimeter_mm)) > 1.0e-6:
        raise AssertionError("Coffer intervals do not terminate at the perimeter")
    return tuple(intervals), clear


def build_coffered_cassette_seed(
    module_length_mm: float,
    *,
    depth_mm: float = SHELF_DEPTH_MM,
    height_mm: float = CASSETTE_HEIGHT_MM,
    skin_mm: float = CASSETTE_SKIN_MM,
    perimeter_mm: float = CASSETTE_PERIMETER_MM,
    rib_mm: float = CASSETTE_RIB_MM,
    maximum_clear_span_mm: float = CASSETTE_MAX_CLEAR_SPAN_MM,
) -> tuple[trimesh.Trimesh, CofferMetrics]:
    """Build one continuous-skin, open-coffer cassette qualification seed.

    Rectangular coffer cells are opened through the underside, leaving an exact
    3.2 mm continuous top skin, full-height 4.8 mm perimeter, and full-height
    3.6 mm internal ribs.  This deliberately inspectable seed does *not* claim
    the future closed two-skin production topology.
    """

    length = _positive(module_length_mm, "module length")
    depth = _positive(depth_mm, "cassette depth")
    height = _positive(height_mm, "cassette height")
    skin = _positive(skin_mm, "cassette skin")
    perimeter = _positive(perimeter_mm, "cassette perimeter")
    rib = _positive(rib_mm, "cassette rib")
    maximum_clear = _positive(maximum_clear_span_mm, "maximum clear span")
    if skin >= height:
        raise ValueError("Cassette skin must be thinner than total height")
    if not 3.2 - GEOMETRY_EPSILON <= rib <= 4.0 + GEOMETRY_EPSILON:
        raise ValueError("R8 cassette rib must stay within the 3.2-4.0 mm study band")

    x_cells, clear_x = _coffer_intervals(
        length,
        perimeter_mm=perimeter,
        rib_mm=rib,
        maximum_clear_span_mm=maximum_clear,
    )
    y_cells, clear_y = _coffer_intervals(
        depth,
        perimeter_mm=perimeter,
        rib_mm=rib,
        maximum_clear_span_mm=maximum_clear,
    )

    body = _box((length, depth, height))
    cutter_z0 = -0.5
    cutter_height = height - skin + 0.5
    cutters = [
        _box(
            (x1 - x0, y1 - y0, cutter_height),
            (x0, y0, cutter_z0),
        )
        for x0, x1 in x_cells
        for y0, y1 in y_cells
    ]
    mesh = _boolean_difference(body, cutters)
    metrics = CofferMetrics(
        module_length_mm=length,
        depth_mm=depth,
        height_mm=height,
        continuous_skin_mm=skin,
        perimeter_mm=perimeter,
        rib_mm=rib,
        cells_along_run=len(x_cells),
        cells_through_depth=len(y_cells),
        clear_span_along_run_mm=clear_x,
        clear_span_through_depth_mm=clear_y,
        maximum_clear_span_mm=max(clear_x, clear_y),
        open_coffer_face="underside",
    )
    return mesh, metrics


def build_front_first_u_box_cassette(
    module_length_mm: float,
    *,
    depth_mm: float = SHELF_DEPTH_MM,
    height_mm: float = CASSETTE_HEIGHT_MM,
    top_skin_mm: float = 3.2,
    bottom_skin_mm: float = 2.4,
    visible_front_wall_mm: float = 4.0,
    full_depth_end_land_mm: float = SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
    internal_web_mm: float = 2.4,
    internal_web_count: int = 3,
) -> tuple[trimesh.Trimesh, UBoxMetrics]:
    """Build the selected lighter, smooth-faced cassette study.

    The top, bottom, and visible front are continuous.  Both seam ends and
    three internal cross webs run the full shelf depth.  The rear face, hidden
    at the wall, remains open.  When the visible front is placed on the bed,
    every 0.2 mm build layer repeats one connected U-box section; no internal
    rib begins as a bridge above an empty cell.
    """

    length = _positive(module_length_mm, "module length")
    depth = _positive(depth_mm, "cassette depth")
    height = _positive(height_mm, "cassette height")
    top = _positive(top_skin_mm, "top skin")
    bottom = _positive(bottom_skin_mm, "bottom skin")
    front = _positive(visible_front_wall_mm, "front wall")
    end = _positive(full_depth_end_land_mm, "end land")
    web = _positive(internal_web_mm, "internal web")
    if isinstance(internal_web_count, bool) or internal_web_count < 1:
        raise ValueError("At least one internal U-box web is required")
    if top + bottom >= height:
        raise ValueError("U-box skins consume the full cassette height")
    if 2.0 * end + internal_web_count * web >= length:
        raise ValueError("U-box end lands and webs consume the module length")
    if front >= depth:
        raise ValueError("The visible front wall must be thinner than shelf depth")

    clear = (
        length - 2.0 * end - internal_web_count * web
    ) / (internal_web_count + 1)
    parts = [
        _box((length, depth, bottom)),
        _box((length, depth, top), (0.0, 0.0, height - top)),
        _box((length, front, height)),
        _box((end, depth, height)),
        _box((end, depth, height), (length - end, 0.0, 0.0)),
    ]
    cursor = end + clear
    for _ in range(internal_web_count):
        parts.append(_box((web, depth, height), (cursor, 0.0, 0.0)))
        cursor += web + clear
    if abs(cursor - (length - end)) > 1.0e-7:
        raise AssertionError("U-box web layout did not terminate at the right end land")
    mesh = _boolean_union(parts)
    return mesh, UBoxMetrics(
        module_length_mm=length,
        depth_mm=depth,
        height_mm=height,
        top_skin_mm=top,
        bottom_skin_mm=bottom,
        visible_front_wall_mm=front,
        full_depth_end_land_mm=end,
        internal_web_mm=web,
        internal_web_count=internal_web_count,
        clear_panel_span_along_run_mm=clear,
        hidden_open_face="rear wall face",
    )


def cassette_seam_bearing_datums(
    module_length_mm: float,
    *,
    depth_mm: float = SHELF_DEPTH_MM,
    end_land_mm: float = SELECTED_U_BOX_FULL_DEPTH_END_LAND_MM,
) -> tuple[SeamBearingDatum, SeamBearingDatum]:
    """Return the selected U-box's left/right full-depth bearing lands."""

    length = _positive(module_length_mm, "module length")
    depth = _positive(depth_mm, "cassette depth")
    end_land = _positive(end_land_mm, "selected cassette end land")
    if 2.0 * end_land >= length:
        raise ValueError("Cassette is too short for two end bearing lands")
    common = {
        "depth_bounds_mm": (0.0, depth),
        "underside_e_mm": 0.0,
    }
    return (
        SeamBearingDatum(
            side="left",
            seam_plane_x_mm=0.0,
            land_x_bounds_mm=(0.0, end_land),
            **common,
        ),
        SeamBearingDatum(
            side="right",
            seam_plane_x_mm=length,
            land_x_bounds_mm=(length - end_land, length),
            **common,
        ),
    )


def orient_cassette_on_long_edge(
    mesh: trimesh.Trimesh, *, yaw_degrees: float = 45.0
) -> trimesh.Trimesh:
    """Place a cassette on its long edge, yaw it, and normalize to +XYZ."""

    if not isinstance(mesh, trimesh.Trimesh) or mesh.is_empty:
        raise ValueError("A nonempty cassette mesh is required")
    oriented = mesh.copy()
    oriented.apply_transform(
        trimesh.transformations.rotation_matrix(math.pi / 2.0, (1.0, 0.0, 0.0))
    )
    oriented.apply_transform(
        trimesh.transformations.rotation_matrix(
            math.radians(float(yaw_degrees)), (0.0, 0.0, 1.0)
        )
    )
    oriented.apply_translation(-oriented.bounds[0])
    return _clean_mesh(oriented)


def print_envelope_with_margins(
    mesh: trimesh.Trimesh,
    *,
    brim_mm: float = 5.0,
    brim_object_gap_mm: float = 0.0,
    reserve_per_bed_edge_mm: float = 2.0,
    available_build_volume_mm: tuple[float, float, float] = (180.0, 180.0, 180.0),
) -> PrintEnvelope:
    """Measure an oriented part with brim plus an independent bed-edge reserve."""

    brim = _positive(brim_mm, "brim")
    brim_gap = float(brim_object_gap_mm)
    if not math.isfinite(brim_gap) or brim_gap < 0.0:
        raise ValueError("brim-object gap must be finite and nonnegative")
    reserve = _positive(reserve_per_bed_edge_mm, "bed-edge reserve")
    available = tuple(
        _positive(value, "available build-volume dimension")
        for value in available_build_volume_mm
    )
    raw = tuple(float(value) for value in mesh.extents)
    process_margin = 2.0 * (brim + brim_gap + reserve)
    required = (raw[0] + process_margin, raw[1] + process_margin, raw[2])
    return PrintEnvelope(
        raw_part_mm=raw,
        required_build_volume_mm=required,
        available_build_volume_mm=available,  # type: ignore[arg-type]
        brim_mm=brim,
        brim_object_gap_mm=brim_gap,
        reserve_per_bed_edge_mm=reserve,
        fits=all(
            needed <= allowed + GEOMETRY_EPSILON
            for needed, allowed in zip(required, available)
        ),
    )


def _point_in_polygon(point: np.ndarray, polygon: np.ndarray) -> bool:
    """Ray-casting containment for a point not expected on the boundary."""

    x, y = float(point[0]), float(point[1])
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y):
            intersection = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < intersection:
                inside = not inside
        previous = current
    return inside


def _section_has_one_material_component(section: trimesh.path.Path3D | None) -> bool:
    if section is None:
        return False
    loops: list[np.ndarray] = []
    for discrete in section.discrete:
        points = np.asarray(discrete, dtype=float)[:, :2]
        if len(points) < 4 or np.linalg.norm(points[0] - points[-1]) > 1.0e-5:
            return False
        polygon = points[:-1]
        if abs(_signed_polygon_area(polygon)) <= GEOMETRY_EPSILON:
            return False
        loops.append(polygon)
    if not loops:
        return False

    # A connected profile may have holes, but it must have exactly one outer
    # enclosure.  Every smaller boundary must sit within a larger boundary.
    loops.sort(key=lambda item: abs(_signed_polygon_area(item)), reverse=True)
    outer_components = 0
    for index, polygon in enumerate(loops):
        representative = np.mean(polygon, axis=0)
        contained = any(
            _point_in_polygon(representative, candidate)
            for candidate in loops[:index]
        )
        if not contained:
            outer_components += 1
    return outer_components == 1


def saved_layer_connectivity(
    mesh: trimesh.Trimesh, *, layer_height_mm: float = 0.2
) -> LayerConnectivityReport:
    """Check material connectivity at every nominal saved-orientation layer."""

    layer = _positive(layer_height_mm, "layer height")
    z_min, z_max = (float(mesh.bounds[0, 2]), float(mesh.bounds[1, 2]))
    thickness = z_max - z_min
    layer_count = int(round(thickness / layer))
    if layer_count < 1 or abs(layer_count * layer - thickness) > 1.0e-4:
        raise ValueError("Saved build height must be an integer number of layers")
    failed: list[int] = []
    for index in range(layer_count):
        z = z_min + (index + 0.5) * layer
        section = mesh.section(
            plane_origin=(0.0, 0.0, z), plane_normal=(0.0, 0.0, 1.0)
        )
        if not _section_has_one_material_component(section):
            failed.append(index)
    return LayerConnectivityReport(
        layer_height_mm=layer,
        sampled_layer_count=layer_count,
        failed_layer_indices=tuple(failed),
        all_layers_connected=not failed,
    )


def corbel_layer_connectivity(
    mesh: trimesh.Trimesh, *, layer_height_mm: float = 0.2
) -> LayerConnectivityReport:
    """Backward-compatible named wrapper for a saved corbel orientation."""

    return saved_layer_connectivity(mesh, layer_height_mm=layer_height_mm)
