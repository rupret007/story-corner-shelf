#!/usr/bin/env python3
"""Removable zero-credit ornament for the Story Corner r6 arcade.

The structural chassis begins at installed depth ``z = 13.2 mm``.  Every
installed ornament mesh stops at ``z = 10.2 mm`` except for the deliberately
separate additive attachment helpers, leaving the required 3 mm unloaded
isolation gap.  The 88 gravity-boss and 11 straight-locator helpers are
*integral features* of sacrificial chassis pads; they are never counted as
separate printed objects and never receive structural credit.

Eight installed mesh families make 33 removable pieces per shelf level:
18 handed half-bay carriers, 11 pier overlays, two far-end caps, and the two
non-interlocking corner finish pieces.  Two additional PRINT_FIRST coupon
ladders qualify the connector fit and are outside the installed inventory.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import cos, pi, sin, sqrt
from typing import Any

import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry import box as shapely_box
from shapely.ops import unary_union

from design_math import calculate_plan, grand_arc
from model_io import boolean_difference, boolean_union, cuboid
from ornament_access import (
    carrier_coordinate_contract,
    connector_types_for_family,
    ornament_access_contract,
    swept_oculi_for_family,
)
from release_plan import enumerate_cassette_instances


EPSILON = 1.0e-7


@dataclass(frozen=True)
class KeyholeSpecification:
    boss_head_run_mm: float = 12.0
    boss_head_y_mm: float = 9.6
    boss_head_z_mm: tuple[float, float] = (6.0, 8.0)
    boss_neck_run_y_mm: float = 7.2
    boss_neck_z_mm: tuple[float, float] = (8.0, 13.22)
    head_transition_mm: float = 1.6
    clearance_per_face_mm: float = 0.4
    receiver_head_run_mm: float = 12.8
    receiver_head_y_mm: float = 10.4
    receiver_neck_run_mm: float = 8.0
    downward_travel_mm: float = 6.0
    internal_chase_run_y_mm: tuple[float, float] = (16.8, 18.4)
    internal_chase_z_mm: tuple[float, float] = (4.8, 8.6)
    housing_wall_mm: float = 2.4
    housing_run_y_mm: tuple[float, float] = (21.6, 23.2)
    rear_lip_mm: float = 1.6
    lip_aperture_z_mm: tuple[float, float] = (8.4, 10.4)


KEYHOLE = KeyholeSpecification()


def _keyhole_contract(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg["palatine"]["ornament_keyhole_contract"]


def _family_boss_map(cfg: dict[str, Any], family_id: str) -> dict[str, Any]:
    mapping = _keyhole_contract(cfg)["per_parent_boss_placement_map"]
    if not isinstance(mapping, dict) or family_id not in mapping:
        raise ValueError(f"{family_id}: exact parent-boss map is absent")
    record = mapping[family_id]
    centers = record.get("carrier_local_receiver_centers_x_y_mm")
    if not isinstance(centers, list) or len(centers) != 3:
        raise ValueError(f"{family_id}: exactly three receiver centers are required")
    return record


def _receiver_centers(
    cfg: dict[str, Any], family_id: str
) -> tuple[tuple[float, float], ...]:
    record = _family_boss_map(cfg, family_id)
    centers = tuple(
        (float(center[0]), float(center[1]))
        for center in record["carrier_local_receiver_centers_x_y_mm"]
    )
    if len(centers) != 3 or len(set(centers)) != 3:
        raise ValueError(f"{family_id}: receiver centers must be three unique points")
    return centers


def _receiver_run_travel_mm(cfg: dict[str, Any], connector_index: int) -> float:
    contract = _keyhole_contract(cfg)
    elongated = {int(value) for value in contract["elongated_run_axis_connector_indices"]}
    fixed = int(contract["fixed_connector_index"])
    if connector_index == fixed:
        return 0.0
    if connector_index in elongated:
        return float(contract["elongated_total_run_travel_mm"])
    raise ValueError(f"Connector index {connector_index} has no fixed/elongated class")


@dataclass(frozen=True)
class OrnamentInstance:
    logical_id: str
    family_id: str
    run_id: str | None
    placement_role: str
    structural_credit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrnamentFamily:
    family_id: str
    mesh: trimesh.Trimesh
    installed: bool
    print_first_coupon: bool
    structural_credit: bool
    notes: tuple[str, ...]
    design_metrics: dict[str, Any]


def _finish(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.fix_normals()
    if float(mesh.volume) < 0.0:
        mesh.invert()
    return mesh


def _extrude(shape: Any, z0: float, height: float) -> trimesh.Trimesh:
    if shape.is_empty or height <= 0.0:
        raise ValueError("An ornament extrusion needs a nonempty positive profile")
    if shape.geom_type == "MultiPolygon":
        meshes = [_extrude(component, z0, height) for component in shape.geoms]
        return _finish(trimesh.util.concatenate(meshes))
    mesh = trimesh.creation.extrude_polygon(shape, height=height, engine="earcut")
    mesh.apply_translation((0.0, 0.0, z0))
    return mesh


def _mirror_x(shape: Any, width: float) -> Any:
    return affinity.scale(shape, xfact=-1.0, yfact=1.0, origin=(width / 2.0, 0.0))


def _rectangular_frustum(
    center_x: float,
    center_y: float,
    bottom_run: float,
    bottom_y: float,
    top_run: float,
    top_y: float,
    z0: float,
    z1: float,
) -> trimesh.Trimesh:
    if z1 <= z0:
        raise ValueError("A connector transition needs positive depth")
    vertices: list[tuple[float, float, float]] = []
    for z, run, height in (
        (z0, bottom_run, bottom_y),
        (z1, top_run, top_y),
    ):
        vertices.extend(
            [
                (center_x - run / 2.0, center_y - height / 2.0, z),
                (center_x + run / 2.0, center_y - height / 2.0, z),
                (center_x + run / 2.0, center_y + height / 2.0, z),
                (center_x - run / 2.0, center_y + height / 2.0, z),
            ]
        )
    faces = np.asarray(
        [
            (0, 2, 1), (0, 3, 2),
            (4, 5, 6), (4, 6, 7),
            (0, 1, 5), (0, 5, 4),
            (1, 2, 6), (1, 6, 5),
            (2, 3, 7), (2, 7, 6),
            (3, 0, 4), (3, 4, 7),
        ],
        dtype=np.int64,
    )
    return trimesh.Trimesh(vertices=np.asarray(vertices), faces=faces, process=True)


def gravity_keyhole_boss_mesh(
    center_x: float = 0.0,
    center_y: float = 0.0,
) -> trimesh.Trimesh:
    """Integral sacrificial boss feature; not an independent installed part."""

    spec = KEYHOLE
    head_z0, head_z1 = spec.boss_head_z_mm
    neck_z0, neck_z1 = spec.boss_neck_z_mm
    transition_z0 = head_z1 - spec.head_transition_mm
    head = cuboid(
        (spec.boss_head_run_mm, spec.boss_head_y_mm, transition_z0 - head_z0 + 0.02),
        origin=(
            center_x - spec.boss_head_run_mm / 2.0,
            center_y - spec.boss_head_y_mm / 2.0,
            head_z0,
        ),
    )
    transition = _rectangular_frustum(
        center_x,
        center_y,
        spec.boss_head_run_mm,
        spec.boss_head_y_mm,
        spec.boss_neck_run_y_mm,
        spec.boss_neck_run_y_mm,
        transition_z0,
        head_z1,
    )
    neck = cuboid(
        (spec.boss_neck_run_y_mm, spec.boss_neck_run_y_mm, neck_z1 - neck_z0 + 0.02),
        origin=(
            center_x - spec.boss_neck_run_y_mm / 2.0,
            center_y - spec.boss_neck_run_y_mm / 2.0,
            neck_z0 - 0.02,
        ),
    )
    return _finish(boolean_union([head, transition, neck]))


def compact_pier_gravity_keyhole_boss_mesh(
    cfg: dict[str, Any],
    center_x: float = 0.0,
    center_y: float = 0.0,
) -> trimesh.Trimesh:
    """Integral compact pier boss; distinct from the standard facade boss."""

    compact = _keyhole_contract(cfg)["compact_pier_gravity_keyhole_contract"]
    head_run, head_y = (
        float(value) for value in compact["boss_head_run_y_mm"]
    )
    head_z0, head_z1 = (
        float(value) for value in compact["boss_head_depth_zone_mm"]
    )
    neck_run, neck_y = (
        float(value) for value in compact["boss_neck_run_y_mm"]
    )
    neck_z0, neck_z1 = (
        float(value) for value in compact["boss_neck_depth_zone_mm"]
    )
    transition_z0 = head_z1 - KEYHOLE.head_transition_mm
    head = cuboid(
        (head_run, head_y, transition_z0 - head_z0 + 0.02),
        origin=(center_x - head_run / 2.0, center_y - head_y / 2.0, head_z0),
    )
    transition = _rectangular_frustum(
        center_x,
        center_y,
        head_run,
        head_y,
        neck_run,
        neck_y,
        transition_z0,
        head_z1,
    )
    neck = cuboid(
        (neck_run, neck_y, neck_z1 - neck_z0 + 0.02),
        origin=(
            center_x - neck_run / 2.0,
            center_y - neck_y / 2.0,
            neck_z0 - 0.02,
        ),
    )
    return _finish(boolean_union([head, transition, neck]))


def noncapturing_loose_locator_post_mesh(
    cfg: dict[str, Any],
    center_x: float = 0.0,
    center_y: float = 0.0,
) -> trimesh.Trimesh:
    """Integral pier locator; a straight post with no retaining geometry."""

    locator = _keyhole_contract(cfg)["noncapturing_loose_locator_contract"]
    run, height = (
        float(value) for value in locator["structural_parent_post_run_y_mm"]
    )
    z0, z1 = (float(value) for value in locator["post_global_depth_zone_mm"])
    if (run, height, z0, z1) != (7.2, 7.2, 8.0, 13.22):
        raise ValueError("The noncapturing pier locator envelope drifted")
    return _finish(
        cuboid(
            (run, height, z1 - z0),
            origin=(center_x - run / 2.0, center_y - height / 2.0, z0),
        )
    )


def _gravity_aperture(
    center_x: float,
    center_y: float,
    boss_head_run_mm: float,
    boss_head_y_mm: float,
    boss_neck_run_mm: float,
    boss_neck_y_mm: float,
    downward_travel_mm: float,
    clearance_per_face_mm: float,
    run_travel_mm: float = 0.0,
) -> Any:
    if run_travel_mm < 0.0:
        raise ValueError("Receiver run travel may not be negative")
    head_w = (
        boss_head_run_mm
        + 2.0 * clearance_per_face_mm
        + run_travel_mm
    )
    head_h = boss_head_y_mm + 2.0 * clearance_per_face_mm
    neck_w = (
        boss_neck_run_mm
        + 2.0 * clearance_per_face_mm
        + run_travel_mm
    )
    neck_h = boss_neck_y_mm + 2.0 * clearance_per_face_mm
    entry_y = center_y - downward_travel_mm / 2.0
    final_y = center_y + downward_travel_mm / 2.0
    head = shapely_box(
        center_x - head_w / 2.0,
        entry_y - head_h / 2.0,
        center_x + head_w / 2.0,
        entry_y + head_h / 2.0,
    )
    travel = shapely_box(
        center_x - neck_w / 2.0,
        entry_y - neck_h / 2.0,
        center_x + neck_w / 2.0,
        final_y + neck_h / 2.0,
    )
    return unary_union([head, travel])


def _keyhole_aperture(
    center_x: float,
    center_y: float,
    clearance_per_face_mm: float,
    run_travel_mm: float = 0.0,
) -> Any:
    spec = KEYHOLE
    return _gravity_aperture(
        center_x,
        center_y,
        spec.boss_head_run_mm,
        spec.boss_head_y_mm,
        spec.boss_neck_run_y_mm,
        spec.boss_neck_run_y_mm,
        spec.downward_travel_mm,
        clearance_per_face_mm,
        run_travel_mm,
    )


def _receiver_housing_and_cutters(
    center_x: float,
    center_y: float,
    clearance_per_face_mm: float = KEYHOLE.clearance_per_face_mm,
    run_travel_mm: float = 0.0,
) -> tuple[trimesh.Trimesh, tuple[trimesh.Trimesh, ...]]:
    spec = KEYHOLE
    outer_w, outer_h = spec.housing_run_y_mm
    chase_w, chase_h = spec.internal_chase_run_y_mm
    required_head_run = spec.receiver_head_run_mm + run_travel_mm
    if chase_w + EPSILON < required_head_run:
        raise ValueError("Keyhole chase does not contain elongated head travel")
    if abs(outer_w - (chase_w + 2.0 * spec.housing_wall_mm)) > EPSILON:
        raise ValueError("Keyhole housing run walls are not truly 2.4 mm")
    if abs(outer_h - (chase_h + 2.0 * spec.housing_wall_mm)) > EPSILON:
        raise ValueError("Keyhole housing vertical walls are not truly 2.4 mm")
    housing = cuboid(
        (outer_w, outer_h, 7.1),
        origin=(center_x - outer_w / 2.0, center_y - outer_h / 2.0, 3.1),
    )
    # The clear swept chase is behind a 1.6 mm carrier-side wall and in front
    # of a 1.6 mm rear keyhole lip.  The lip aperture supplies the gravity
    # travel; the large internal chase never weakens the 2.4 mm perimeter.
    chase_z0, chase_z1 = spec.internal_chase_z_mm
    lip_z0, lip_z1 = spec.lip_aperture_z_mm
    chase = cuboid(
        (chase_w, chase_h, chase_z1 - chase_z0),
        origin=(center_x - chase_w / 2.0, center_y - chase_h / 2.0, chase_z0),
    )
    aperture = _extrude(
        _keyhole_aperture(
            center_x,
            center_y,
            clearance_per_face_mm,
            run_travel_mm,
        ),
        lip_z0,
        lip_z1 - lip_z0,
    )
    return housing, (chase, aperture)


def _compact_pier_receiver_housing_and_cutters(
    cfg: dict[str, Any],
    center_x: float,
    center_y: float,
) -> tuple[trimesh.Trimesh, tuple[trimesh.Trimesh, ...]]:
    """Independent compact gravity receiver used only by pier overlays."""

    compact = _keyhole_contract(cfg)["compact_pier_gravity_keyhole_contract"]
    head_run, head_y = (
        float(value) for value in compact["boss_head_run_y_mm"]
    )
    neck_run, _neck_y = (
        float(value) for value in compact["boss_neck_run_y_mm"]
    )
    chase_run, chase_y = (
        float(value) for value in compact["internal_chase_run_y_mm"]
    )
    outer_run, outer_y = (
        float(value) for value in compact["receiver_housing_outer_run_y_mm"]
    )
    housing_z0, housing_z1 = (
        float(value) for value in compact["receiver_housing_depth_zone_mm"]
    )
    chase_z0, chase_z1 = (
        float(value) for value in compact["internal_chase_depth_zone_mm"]
    )
    lip_z0, lip_z1 = (
        float(value) for value in compact["lip_aperture_depth_zone_mm"]
    )
    clearance = float(compact["clearance_per_face_mm"])
    run_travel = float(compact["elongated_total_run_travel_mm"])
    drop = float(compact["gravity_drop_mm"])
    wall = float(compact["minimum_receiver_wall_mm"])
    required_head_run = head_run + 2.0 * clearance + run_travel
    required_head_y = head_y + 2.0 * clearance
    if (
        abs(outer_run - chase_run - 2.0 * wall) > EPSILON
        or abs(outer_y - chase_y - 2.0 * wall) > EPSILON
        or chase_run + EPSILON < required_head_run
        or chase_y + EPSILON < required_head_y + drop
    ):
        raise ValueError("Compact pier keyhole loses its 2.4 mm walls or full sweep")
    housing = cuboid(
        (outer_run, outer_y, housing_z1 - housing_z0),
        origin=(
            center_x - outer_run / 2.0,
            center_y - outer_y / 2.0,
            housing_z0,
        ),
    )
    chase = cuboid(
        (chase_run, chase_y, chase_z1 - chase_z0),
        origin=(center_x - chase_run / 2.0, center_y - chase_y / 2.0, chase_z0),
    )
    aperture = _extrude(
        _gravity_aperture(
            center_x,
            center_y,
            head_run,
            head_y,
            neck_run,
            _neck_y,
            drop,
            clearance,
            run_travel,
        ),
        lip_z0,
        lip_z1 - lip_z0,
    )
    return housing, (chase, aperture)


def _loose_locator_housing_and_cutters(
    cfg: dict[str, Any],
    center_x: float,
    center_y: float,
) -> tuple[trimesh.Trimesh, tuple[trimesh.Trimesh, ...]]:
    """Return the straight, noncapturing receiver for the pier locator."""

    locator = _keyhole_contract(cfg)["noncapturing_loose_locator_contract"]
    outer_run, outer_y = (
        float(value) for value in locator["receiver_housing_outer_run_y_mm"]
    )
    slot_run, slot_y = (
        float(value) for value in locator["receiver_slot_run_y_mm"]
    )
    housing_z0, housing_z1 = (
        float(value) for value in locator["receiver_housing_depth_zone_mm"]
    )
    slot_z0, slot_z1 = (
        float(value) for value in locator["receiver_slot_depth_zone_mm"]
    )
    wall = float(locator["minimum_receiver_wall_mm"])
    if (
        abs(outer_run - slot_run - 2.0 * wall) > EPSILON
        or abs(outer_y - slot_y - 2.0 * wall) > EPSILON
    ):
        raise ValueError("Loose-locator receiver does not retain 2.4 mm walls")
    housing = cuboid(
        (outer_run, outer_y, housing_z1 - housing_z0),
        origin=(
            center_x - outer_run / 2.0,
            center_y - outer_y / 2.0,
            housing_z0,
        ),
    )
    # The rear-open straight slot contains the post at both ends of the full
    # gravity motion.  It has no head pocket or hidden undercut.
    slot = cuboid(
        (slot_run, slot_y, slot_z1 - slot_z0 + 0.2),
        origin=(
            center_x - slot_run / 2.0,
            center_y - slot_y / 2.0,
            slot_z0,
        ),
    )
    return housing, (slot,)


def _oculus_cutters(
    cfg: dict[str, Any], family_id: str
) -> tuple[trimesh.Trimesh, ...]:
    """Cut every service oculus through all removable carrier/chase solid."""

    cutters: list[trimesh.Trimesh] = []
    for oculus in swept_oculi_for_family(cfg, family_id):
        d0, d1 = oculus.depth_zone_mm
        cutters.append(_extrude(oculus.profile(), d0 - 0.1, d1 - d0 + 0.2))
    return tuple(cutters)


def _arch_opening_profile(
    width: float,
    span: float,
    rise: float,
    rib: float,
    nominal_x_offset_mm: float = 0.0,
) -> Any:
    arc = grand_arc(span, rise)
    center_y = rise - arc.radius_mm
    if (
        nominal_x_offset_mm < -EPSILON
        or nominal_x_offset_mm + width > span / 2.0 + EPSILON
    ):
        raise ValueError("Physical arch crop must remain inside its nominal half span")
    samples: list[tuple[float, float]] = []
    for index in range(49):
        local_x = width * index / 48.0
        distance = nominal_x_offset_mm + local_x
        outer_y = center_y + sqrt(max(0.0, arc.radius_mm**2 - distance**2))
        inner_y = max(0.0, outer_y * (rise - rib) / rise)
        samples.append((local_x, inner_y))
    return Polygon([(0.0, 0.0), (width, 0.0), *reversed(samples)])


def _three_ray_shape(width: float) -> Any:
    cx, cy = 0.27 * width, 94.0
    rays = []
    for angle_deg in (210.0, 270.0, 330.0):
        angle = angle_deg * pi / 180.0
        rays.append(
            LineString(
                [
                    (cx, cy),
                    (cx + 10.5 * cos(angle), cy + 10.5 * sin(angle)),
                ]
            ).buffer(1.0, cap_style=1, quad_segs=6)
        )
    return unary_union([Point(cx, cy).buffer(2.4, quad_segs=10), *rays])


def _three_chevrons_shape(width: float) -> Any:
    shapes = []
    center = 0.68 * width
    for index in range(3):
        half = 4.0 + 3.2 * index
        low = 90.0 + 4.5 * index
        high = low + 4.0
        shapes.append(
            LineString([(center - half, low), (center, high), (center + half, low)]).buffer(
                0.75, cap_style=1, join_style=2, quad_segs=4
            )
        )
    return unary_union(shapes)


def _carrier_mesh(cfg: dict[str, Any], run_role: str, hand: str) -> OrnamentFamily:
    if run_role not in {"through", "return"} or hand not in {"left", "right"}:
        raise ValueError("Carrier role/hand must be through|return and left|right")
    visual = cfg["palatine"]["visual_carrier_contract"]
    family_id = f"{run_role}_carrier_{hand}"
    coordinate = carrier_coordinate_contract(cfg, family_id)
    nominal_half_span = coordinate.nominal_half_span_mm
    width = coordinate.physical_width_mm
    inset = coordinate.inset_each_nominal_end_mm
    rise = float(visual["visual_arch_rise_mm"])
    rib = float(cfg["tied_arcade"]["arch_radial_rib_mm"])
    height = float(visual["visual_carrier_height_mm"])
    thickness = float(cfg["palatine"]["ornament_carrier_thickness_mm"])
    if abs(height - 108.0) > EPSILON or abs(thickness - 3.2) > EPSILON:
        raise ValueError("The frozen r6 carrier is 108 mm high and 3.2 mm thick")

    outline = shapely_box(0.0, 0.0, width, height).difference(
        _arch_opening_profile(
            width,
            2.0 * nominal_half_span,
            rise,
            rib,
            nominal_x_offset_mm=inset,
        )
    )
    if hand == "left":
        outline = _mirror_x(outline, width)
    base = _extrude(outline, 0.0, thickness)

    # Exact 6/9/15 mm entablature strata (global y 138..144..153..168)
    # receive shallow separator grooves.  Nine dentils are restored above a
    # recessed bed, so their count is visible without thinning the load path.
    cutters: list[trimesh.Trimesh] = [
        cuboid((width + 0.2, 0.8, 0.9), origin=(-0.1, 83.6, -0.1)),
        cuboid((width + 0.2, 0.8, 0.9), origin=(-0.1, 92.6, -0.1)),
        cuboid((width - 4.0, 6.0, 0.9), origin=(2.0, 80.0, -0.1)),
    ]
    reliefs: list[trimesh.Trimesh] = []
    dentil_gap = 2.4
    dentil_width = (width - 8.0 - 8.0 * dentil_gap) / 9.0
    for index in range(9):
        x0 = 4.0 + index * (dentil_width + dentil_gap)
        reliefs.append(cuboid((dentil_width, 6.0, 0.92), origin=(x0, 80.0, 0.0)))

    canonical_ray = _three_ray_shape(width)
    canonical_chevrons = _three_chevrons_shape(width)
    ray_panel = shapely_box(0.12 * width, 82.0, 0.42 * width, 107.0)
    chevron_panel = shapely_box(0.48 * width, 87.0, 0.88 * width, 107.0)
    if hand == "left":
        canonical_ray = _mirror_x(canonical_ray, width)
        canonical_chevrons = _mirror_x(canonical_chevrons, width)
        ray_panel = _mirror_x(ray_panel, width)
        chevron_panel = _mirror_x(chevron_panel, width)
    cutters.extend([_extrude(ray_panel, -0.1, 1.0), _extrude(chevron_panel, -0.1, 1.0)])
    reliefs.extend(
        [_extrude(canonical_ray, 0.0, 0.92), _extrude(canonical_chevrons, 0.0, 0.92)]
    )

    # The right half owns a stepped visible keystone.  The left half receives
    # only a shallow matching visual relief; neither bridges the thermal seam.
    keystone = Polygon([(0.0, 70.0), (7.0, 73.0), (12.0, 84.0), (10.0, 101.0), (0.0, 104.0)])
    if hand == "right":
        reliefs.append(_extrude(keystone, 0.0, thickness))
    else:
        cutters.append(_extrude(_mirror_x(keystone, width), -0.1, 1.0))

    body = boolean_difference(base, cutters)
    # Three rear gravity receivers form a non-collinear removable carrier
    # attachment.  Their housings never enter the z=10.2..13.2 isolation gap.
    centers = _receiver_centers(cfg, family_id)
    housings: list[trimesh.Trimesh] = []
    receiver_cutters: list[trimesh.Trimesh] = []
    for connector_index, (center_x, center_y) in enumerate(centers, start=1):
        housing, local_cutters = _receiver_housing_and_cutters(
            center_x,
            center_y,
            run_travel_mm=_receiver_run_travel_mm(cfg, connector_index),
        )
        housings.append(housing)
        receiver_cutters.extend(local_cutters)
    body = boolean_union([body, *reliefs, *housings])
    body = boolean_difference(body, receiver_cutters)
    # These are real service portals, not shallow decorative recesses.  The
    # cutter follows both +/-0.6 mm run extremes and all 6 mm of carrier
    # release travel, then crosses the complete d=0..10.2 removable depth.
    body = _finish(
        boolean_difference(body, list(_oculus_cutters(cfg, family_id)))
    )
    access = swept_oculi_for_family(cfg, family_id)
    return OrnamentFamily(
        family_id=family_id,
        mesh=body,
        installed=True,
        print_first_coupon=False,
        structural_credit=False,
        notes=(
            "Removable black-PETG fine ornament; zero structural credit.",
            "Right carrier owns the visible keystone; no ornament bridges a seam.",
        ),
        design_metrics={
            "width_mm": width,
            "nominal_half_span_mm": nominal_half_span,
            "centered_inset_each_nominal_end_mm": inset,
            "nominal_x_from_local_offset_mm": inset,
            "height_mm": height,
            "carrier_zone_mm": [0.0, thickness],
            "connector_chase_max_z_mm": 10.2,
            "gravity_receivers": 3,
            "receiver_centers_local_x_y_mm": [list(center) for center in centers],
            "attachment_feature_types": list(
                connector_types_for_family(cfg, family_id)
            ),
            "elongated_connector_indices": [1, 2],
            "fixed_connector_index": 3,
            "parent_boss_map": dict(_family_boss_map(cfg, family_id)),
            "cross_key_service_oculi": [item.to_dict() for item in access],
            "oculus_cutter_depth_zone_mm": [0.0, 10.2],
            "minimum_remaining_planar_web_mm": 2.4,
            "dentils": 9,
            "sunburst_rays": 3,
            "nested_chevrons": 3,
            "entablature_layer_heights_mm": [6.0, 9.0, 15.0],
            "keystone_owner": hand == "right",
        },
    )


def _piece_with_receivers(
    cfg: dict[str, Any],
    family_id: str,
    base_shape: Any,
    relief_shapes: tuple[Any, ...] = (),
    recess_shapes: tuple[Any, ...] = (),
) -> trimesh.Trimesh:
    receiver_centers = _receiver_centers(cfg, family_id)
    base = _extrude(base_shape, 0.0, 3.2)
    if recess_shapes:
        base = boolean_difference(base, [_extrude(shape, -0.1, 1.0) for shape in recess_shapes])
    reliefs = [_extrude(shape, 0.0, 0.92) for shape in relief_shapes]
    housings: list[trimesh.Trimesh] = []
    cutters: list[trimesh.Trimesh] = []
    connector_types = connector_types_for_family(cfg, family_id)
    for connector_index, (center_x, center_y) in enumerate(
        receiver_centers, start=1
    ):
        connector_type = connector_types[connector_index - 1]
        if connector_type == "gravity_keyhole":
            housing, local_cutters = _receiver_housing_and_cutters(
                center_x,
                center_y,
                run_travel_mm=_receiver_run_travel_mm(cfg, connector_index),
            )
        elif connector_type == "compact_gravity_keyhole":
            housing, local_cutters = _compact_pier_receiver_housing_and_cutters(
                cfg,
                center_x,
                center_y,
            )
        elif connector_type == "noncapturing_loose_locator":
            housing, local_cutters = _loose_locator_housing_and_cutters(
                cfg,
                center_x,
                center_y,
            )
        else:
            raise ValueError(
                f"{family_id}: unsupported attachment feature {connector_type!r}"
            )
        housings.append(housing)
        cutters.extend(local_cutters)
    body = boolean_difference(boolean_union([base, *reliefs, *housings]), cutters)
    return _finish(boolean_difference(body, list(_oculus_cutters(cfg, family_id))))


def _pier_overlay_family(cfg: dict[str, Any]) -> OrnamentFamily:
    family_id = "pier_overlay"
    width, height = 34.4, 59.6
    base_shape = Polygon([(0.0, 0.0), (width, 0.0), (31.2, height), (3.2, height)])
    flute_centers = np.linspace(6.2, width - 6.2, int(cfg["palatine"]["pier_flute_count"]))
    flutes = tuple(
        LineString([(float(x), 9.0), (float(x), 51.0)]).buffer(
            1.0, cap_style=1, quad_segs=8
        )
        for x in flute_centers
    )
    grooves = (
        shapely_box(2.0, 7.0, width - 2.0, 8.0),
        shapely_box(3.0, 52.0, width - 3.0, 53.0),
        *flutes,
    )
    centers = _receiver_centers(cfg, family_id)
    mesh = _piece_with_receivers(
        cfg,
        family_id,
        base_shape,
        recess_shapes=grooves,
    )
    return OrnamentFamily(
        family_id,
        mesh,
        True,
        False,
        False,
        ("Six-flute removable Greek pier face; zero structural credit.",),
        {
            "width_mm": width,
            "height_mm": height,
            "flutes": 6,
            "gravity_receivers": 2,
            "standard_gravity_receivers": 0,
            "compact_gravity_receivers": 2,
            "noncapturing_loose_locators": 1,
            "connector_chase_max_z_mm": 10.2,
            "receiver_centers_local_x_y_mm": [list(center) for center in centers],
            "elongated_connector_indices": [1, 2],
            "fixed_connector_index": None,
            "attachment_feature_types": list(
                connector_types_for_family(cfg, family_id)
            ),
            "parent_boss_map": dict(_family_boss_map(cfg, family_id)),
            "cross_key_service_oculi": [
                item.to_dict() for item in swept_oculi_for_family(cfg, family_id)
            ],
            "oculus_cutter_depth_zone_mm": [0.0, 10.2],
            "minimum_remaining_planar_web_mm": 3.2,
        },
    )


def _ordinary_endcap_family(cfg: dict[str, Any]) -> OrnamentFamily:
    family_id = "ordinary_endcap"
    parent_map = _family_boss_map(cfg, family_id)
    width, height = (
        float(value) for value in parent_map["physical_width_height_mm"]
    )
    base = Polygon([(0.0, 0.0), (width, 3.0), (width, 105.0), (0.0, height)])
    chevrons = tuple(
        LineString([(7.0 - i, 44.0 + i * 5.0), (16.0, 50.0 + i * 5.0), (25.0 + i, 44.0 + i * 5.0)]).buffer(
            0.8, cap_style=1, join_style=2, quad_segs=4
        )
        for i in range(3)
    )
    panel = shapely_box(3.0, 38.0, width - 3.0, 70.0)
    mesh = _piece_with_receivers(
        cfg,
        family_id,
        base,
        relief_shapes=chevrons,
        recess_shapes=(panel,),
    )
    centers = _receiver_centers(cfg, family_id)
    return OrnamentFamily(
        family_id,
        mesh,
        True,
        False,
        False,
        ("Far-run removable end closure; does not restrain rail movement.",),
        {
            "width_mm": width,
            "height_mm": height,
            "nested_chevrons": 3,
            "gravity_receivers": 3,
            "receiver_centers_local_x_y_mm": [list(center) for center in centers],
            "elongated_connector_indices": [1, 2],
            "fixed_connector_index": 3,
            "parent_boss_map": dict(parent_map),
        },
    )


def _nine_petal_rosette(center_x: float, center_y: float) -> Any:
    petals = []
    seed = affinity.scale(Point(0.0, 0.0).buffer(1.0, quad_segs=10), 3.1, 8.3)
    for index in range(9):
        angle = index * 360.0 / 9.0
        petal = affinity.translate(seed, yoff=9.0)
        petal = affinity.rotate(petal, -angle, origin=(0.0, 0.0))
        petals.append(affinity.translate(petal, xoff=center_x, yoff=center_y))
    return unary_union([Point(center_x, center_y).buffer(4.8, quad_segs=12), *petals])


def _corner_fixed_rosette_family(cfg: dict[str, Any]) -> OrnamentFamily:
    family_id = "corner_fixed_rosette"
    parent_map = _family_boss_map(cfg, family_id)
    width, height = (
        float(value) for value in parent_map["physical_width_height_mm"]
    )
    center_x, center_y = width / 2.0, height / 2.0
    base = shapely_box(0.0, 0.0, width, height)
    rosette = affinity.scale(
        _nine_petal_rosette(center_x, center_y),
        xfact=0.55,
        yfact=1.0,
        origin=(center_x, center_y),
    )
    panel = affinity.scale(
        Point(center_x, center_y).buffer(21.5, quad_segs=16),
        xfact=0.58,
        yfact=1.0,
        origin=(center_x, center_y),
    )
    mesh = _piece_with_receivers(
        cfg,
        family_id,
        base,
        relief_shapes=(rosette,),
        recess_shapes=(panel,),
    )
    centers = _receiver_centers(cfg, family_id)
    return OrnamentFamily(
        family_id,
        mesh,
        True,
        False,
        False,
        (
            "Nine-petal rosette fixes cosmetically to the through arm only.",
            "It has no mechanical engagement with the floating return piece.",
        ),
        {
            "width_mm": width,
            "height_mm": height,
            "rosette_petals": 9,
            "gravity_receivers": 3,
            "receiver_centers_local_x_y_mm": [list(center) for center in centers],
            "elongated_connector_indices": [1, 2],
            "fixed_connector_index": 3,
            "parent_boss_map": dict(parent_map),
        },
    )


def _corner_floating_return_family(cfg: dict[str, Any]) -> OrnamentFamily:
    family_id = "corner_floating_return"
    parent_map = _family_boss_map(cfg, family_id)
    width, height = (
        float(value) for value in parent_map["physical_width_height_mm"]
    )
    float_mm = float(cfg["palatine"]["facade_seam_key_axial_float_mm"])
    source_solid = tuple(
        float(value) for value in parent_map["source_solid_x_envelope_mm"]
    )
    visible_base = tuple(
        float(value) for value in parent_map["visible_base_x_envelope_mm"]
    )
    if source_solid != (0.0, width) or visible_base != (float_mm, width):
        raise ValueError("Floating return finish source/visible envelopes drifted")
    base = Polygon(
        [
            (visible_base[0], 0.0),
            (visible_base[1], 0.0),
            (visible_base[1], height),
            (visible_base[0], height),
        ]
    )
    steps = tuple(
        shapely_box(
            visible_base[0] + 3.0 + i * 3.0,
            8.0 + i * 5.0,
            visible_base[1] - 3.0 - i * 3.0,
            10.0 + i * 5.0,
        )
        for i in range(3)
    )
    mesh = _piece_with_receivers(
        cfg,
        family_id,
        base,
        recess_shapes=steps,
    )
    centers = _receiver_centers(cfg, family_id)
    return OrnamentFamily(
        family_id,
        mesh,
        True,
        False,
        False,
        ("Return-side corner finish reserves axial float and never locks the L corner.",),
        {
            "width_mm": width,
            "height_mm": height,
            "axial_float_mm": float_mm,
            "source_solid_x_envelope_mm": list(source_solid),
            "visible_base_x_envelope_mm": list(visible_base),
            "locked_piece_origin_run_s_mm": float(
                parent_map["locked_piece_origin_run_s_mm"]
            ),
            "parent_panel_run_envelope_mm": list(
                parent_map["parent_panel_run_envelope_mm"]
            ),
            "remove_before_through_rosette_service": True,
            "gravity_receivers": 3,
            "receiver_centers_local_x_y_mm": [list(center) for center in centers],
            "elongated_connector_indices": [1, 2],
            "fixed_connector_index": 3,
            "parent_boss_map": dict(parent_map),
        },
    )


def male_keyhole_coupon_ladder_mesh() -> trimesh.Trimesh:
    """Four repeat bosses on one <=180 mm PRINT_FIRST identification ladder."""

    base = cuboid((150.0, 35.0, 3.2), origin=(0.0, 0.0, 13.2))
    bosses = [gravity_keyhole_boss_mesh(x, 17.5) for x in (20.0, 55.0, 90.0, 125.0)]
    # Raised 1/2/3/4-dot groups identify the mating clearance station without
    # relying on tiny embossed text.
    dots: list[trimesh.Trimesh] = []
    for station, count in zip((20.0, 55.0, 90.0, 125.0), range(1, 5)):
        for index in range(count):
            dots.append(
                cuboid(
                    (2.0, 2.0, 1.2),
                    origin=(station - count + 2.0 * index, 2.5, 16.3),
                )
            )
    return _finish(boolean_union([base, *bosses, *dots]))


def female_keyhole_coupon_ladder_mesh(cfg: dict[str, Any]) -> trimesh.Trimesh:
    """Four qualified-clearance receivers matching the male coupon stations."""

    clearances = tuple(float(value) for value in cfg["joinery"]["coupon_clearance_matrix_mm"])
    if clearances != (0.2, 0.3, 0.4, 0.5):
        raise ValueError("The frozen ornament coupon ladder requires 0.2/0.3/0.4/0.5 mm")
    base = cuboid((150.0, 35.0, 3.2), origin=(0.0, 0.0, 0.0))
    housings: list[trimesh.Trimesh] = []
    cutters: list[trimesh.Trimesh] = []
    for station, clearance in zip((20.0, 55.0, 90.0, 125.0), clearances):
        housing, local_cutters = _receiver_housing_and_cutters(station, 17.5, clearance)
        housings.append(housing)
        cutters.extend(local_cutters)
    return _finish(boolean_difference(boolean_union([base, *housings]), cutters))


def ornament_instances_per_level(cfg: dict[str, Any]) -> tuple[OrnamentInstance, ...]:
    """Enumerate the exact 33 removable pieces for one independent level."""

    plan = calculate_plan(cfg)
    cassettes = enumerate_cassette_instances(cfg, plan)
    instances: list[OrnamentInstance] = []
    for cassette in cassettes:
        run_role = "through" if cassette.run_role == "through" else "return"
        hand = "left" if cassette.index % 2 == 0 else "right"
        instances.append(
            OrnamentInstance(
                logical_id=f"{cassette.run_id}_bay_{cassette.index // 2 + 1:02d}_{hand}_carrier",
                family_id=f"{run_role}_carrier_{hand}",
                run_id=cassette.run_id,
                placement_role="removable_half_bay_facade",
            )
        )
    for run in (plan.through, plan.return_run):
        for index in range(run.pier_count):
            instances.append(
                OrnamentInstance(
                    logical_id=f"{run.run_id}_pier_{index + 1:02d}_overlay",
                    family_id="pier_overlay",
                    run_id=run.run_id,
                    placement_role="removable_pier_face",
                )
            )
        instances.append(
            OrnamentInstance(
                logical_id=f"{run.run_id}_far_endcap",
                family_id="ordinary_endcap",
                run_id=run.run_id,
                placement_role="removable_far_run_end_finish",
            )
        )
    instances.extend(
        [
            OrnamentInstance(
                "inside_corner_through_fixed_rosette",
                "corner_fixed_rosette",
                plan.through.run_id,
                "fixed_through_cosmetic_corner",
            ),
            OrnamentInstance(
                "inside_corner_return_floating_finish",
                "corner_floating_return",
                plan.return_run.run_id,
                "floating_return_cosmetic_corner",
            ),
        ]
    )
    if len(instances) != 33 or any(item.structural_credit for item in instances):
        raise AssertionError("One level must contain exactly 33 zero-credit ornament pieces")
    return tuple(instances)


def ornament_topology(cfg: dict[str, Any]) -> dict[str, Any]:
    instances = ornament_instances_per_level(cfg)
    per_family = {
        family: sum(item.family_id == family for item in instances)
        for family in sorted({item.family_id for item in instances})
    }
    expected = {
        "corner_fixed_rosette": 1,
        "corner_floating_return": 1,
        "ordinary_endcap": 2,
        "pier_overlay": 11,
        "return_carrier_left": 3,
        "return_carrier_right": 3,
        "through_carrier_left": 6,
        "through_carrier_right": 6,
    }
    if per_family != expected:
        raise AssertionError(f"Ornament topology drift: {per_family!r}")
    return {
        "installed_family_count": 8,
        "installed_per_level": 33,
        "installed_selected_two_levels": 66,
        "print_first_coupon_family_count": 2,
        "per_level_by_family": per_family,
        "fine_ornament_structural_credit": False,
    }


def build_ornament_families(cfg: dict[str, Any]) -> dict[str, OrnamentFamily]:
    """Build eight installed families and two non-installed fit coupons."""

    ornament_access_contract(cfg)
    families = {
        "through_carrier_left": _carrier_mesh(cfg, "through", "left"),
        "through_carrier_right": _carrier_mesh(cfg, "through", "right"),
        "return_carrier_left": _carrier_mesh(cfg, "return", "left"),
        "return_carrier_right": _carrier_mesh(cfg, "return", "right"),
        "pier_overlay": _pier_overlay_family(cfg),
        "ordinary_endcap": _ordinary_endcap_family(cfg),
        "corner_fixed_rosette": _corner_fixed_rosette_family(cfg),
        "corner_floating_return": _corner_floating_return_family(cfg),
        "print_first_keyhole_male_ladder": OrnamentFamily(
            "print_first_keyhole_male_ladder",
            male_keyhole_coupon_ladder_mesh(),
            False,
            True,
            False,
            ("PRINT FIRST; connector-fit coupon only; zero structural credit.",),
            {"bosses": 4, "maximum_axis_mm": 150.0},
        ),
        "print_first_keyhole_female_ladder": OrnamentFamily(
            "print_first_keyhole_female_ladder",
            female_keyhole_coupon_ladder_mesh(cfg),
            False,
            True,
            False,
            ("PRINT FIRST; 0.2/0.3/0.4/0.5 mm per-face receiver ladder.",),
            {"receivers": 4, "clearance_per_face_mm": [0.2, 0.3, 0.4, 0.5], "maximum_axis_mm": 150.0},
        ),
    }
    installed = [family for family in families.values() if family.installed]
    coupons = [family for family in families.values() if family.print_first_coupon]
    if len(installed) != 8 or len(coupons) != 2 or any(family.structural_credit for family in families.values()):
        raise AssertionError("Ornament catalog must remain 8 installed + 2 zero-credit coupons")
    return families
