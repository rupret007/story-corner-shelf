#!/usr/bin/env python3
"""Pure geometry and readiness calculations for Story Corner r6.

This module deliberately creates no meshes and writes no files.  It is the
single, testable source for the nominal L-plan, the 3/6 arcade stationing, the
grand tied-frame arc, and the 3:4:5 X-corbel node coordinates.

All dimensions returned by this module are millimetres unless a field name
explicitly says otherwise.  Calculations are geometry checks only; they are
not a load rating or a substitute for a qualified structural review.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import asin, atan, degrees, hypot, radians, tan
from typing import Any


MM_PER_INCH = 25.4
EPSILON = 1.0e-7


def mm(value_in: float) -> float:
    """Convert inches to millimetres."""

    return float(value_in) * MM_PER_INCH


def _run_by_role(cfg: dict[str, Any], role: str) -> dict[str, Any]:
    matches = [run for run in cfg["closet"]["runs"] if run["corner_role"] == role]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {role!r} run; found {len(matches)}")
    return matches[0]


def _verified_or_reference(run: dict[str, Any], verified: str, reference: str) -> float:
    value = run.get(verified)
    return float(run[reference] if value is None else value)


@dataclass(frozen=True)
class RunPlan:
    run_id: str
    role: str
    wall_width_mm: float
    start_from_corner_mm: float
    length_mm: float
    bay_count: int
    pier_count: int
    start_pier_inset_mm: float
    end_pier_inset_mm: float
    bay_span_mm: float
    support_centers_local_mm: tuple[float, ...]
    support_centers_absolute_mm: tuple[float, ...]
    cassette_boundary_stations_local_mm: tuple[float, ...]
    cassette_nominal_widths_mm: tuple[float, ...]
    cassette_physical_widths_mm: tuple[float, ...]
    crown_seam_stations_local_mm: tuple[float, ...]
    pier_seam_stations_local_mm: tuple[float, ...]


@dataclass(frozen=True)
class PlanGeometry:
    depth_mm: float
    corner_gap_mm: float
    integral_boss_projection_beyond_cassette_mm: float
    full_removable_facade_projection_beyond_cassette_mm: float
    visible_front_projection_beyond_cassette_mm: float
    ornament_axial_service_stroke_mm: float
    return_corner_cosmetic_overhang_back_mm: float
    structural_arm_clearance_mm: float
    through_back_clearance_mm: float
    return_back_clearance_mm: float
    through: RunPlan
    return_run: RunPlan
    corner_front_plane_absolute_mm: float
    corner_integral_boss_front_plane_absolute_mm: float
    corner_visible_front_plane_absolute_mm: float
    corner_service_swept_front_plane_absolute_mm: float
    return_corner_cosmetic_leading_plane_absolute_mm: float
    exact_crown_alignment_error_mm: float
    minimum_perpendicular_corbel_clearance_mm: float
    minimum_structural_front_to_perpendicular_corbel_plan_reserve_mm: float
    minimum_integral_boss_front_to_perpendicular_corbel_plan_reserve_mm: float
    minimum_visible_front_to_perpendicular_corbel_plan_reserve_mm: float
    minimum_service_swept_front_to_perpendicular_corbel_plan_reserve_mm: float
    maximum_part_axis_with_comb_mm: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArcGeometry:
    span_mm: float
    rise_mm: float
    radius_mm: float
    included_angle_deg: float
    horizontal_thrust_over_total_load_proxy: float


@dataclass(frozen=True)
class XCorbelGeometry:
    projection_mm: float
    vertical_leg_mm: float
    diagonal_mm: float
    wall_upper_node: tuple[float, float]
    front_spring_node: tuple[float, float]
    wall_lower_node: tuple[float, float]
    front_saddle_node: tuple[float, float]
    brace_crossing: tuple[float, float]


def _physical_module_widths(boundaries: list[float], gap_mm: float) -> list[float]:
    """Reserve half a seam on each side that meets another cassette."""

    widths: list[float] = []
    last_index = len(boundaries) - 2
    for index, (left, right) in enumerate(zip(boundaries, boundaries[1:])):
        nominal = right - left
        reserve = gap_mm
        if index == 0:
            reserve -= gap_mm / 2.0
        if index == last_index:
            reserve -= gap_mm / 2.0
        widths.append(nominal - reserve)
    return widths


def _build_run(
    *,
    run: dict[str, Any],
    start_mm: float,
    length_mm: float,
    start_inset_mm: float,
    end_inset_mm: float,
    seam_mm: float,
) -> RunPlan:
    bays = int(run["palatine_arcade_bays"])
    piers = int(run["nominal_structural_pier_count"])
    if bays < 1 or piers != bays + 1:
        raise ValueError(f"{run['id']}: a {bays}-bay arcade requires {bays + 1} piers")
    if (
        start_inset_mm <= 0.0
        or end_inset_mm <= 0.0
        or start_inset_mm + end_inset_mm >= length_mm
    ):
        raise ValueError(
            f"{run['id']}: invalid terminal pier insets "
            f"{start_inset_mm:.3f}/{end_inset_mm:.3f} mm"
        )

    span = (length_mm - start_inset_mm - end_inset_mm) / bays
    supports_local = tuple(start_inset_mm + index * span for index in range(piers))
    supports_absolute = tuple(start_mm + station for station in supports_local)
    crowns = tuple(
        start_inset_mm + (index + 0.5) * span for index in range(bays)
    )

    boundaries = [0.0]
    for index in range(bays):
        boundaries.append(crowns[index])
        if index < bays - 1:
            boundaries.append(supports_local[index + 1])
    boundaries.append(length_mm)

    if len(boundaries) != 2 * bays + 1:
        raise AssertionError("A half-bay cassette layout must have 2B modules")
    if any(right - left <= seam_mm for left, right in zip(boundaries, boundaries[1:])):
        raise ValueError(f"{run['id']}: a cassette is too narrow for the configured seam")

    physical = _physical_module_widths(boundaries, seam_mm)
    pier_seams = tuple(supports_local[1:-1])
    return RunPlan(
        run_id=str(run["id"]),
        role=str(run["corner_role"]),
        wall_width_mm=0.0,  # Filled by calculate_plan after field-width resolution.
        start_from_corner_mm=start_mm,
        length_mm=length_mm,
        bay_count=bays,
        pier_count=piers,
        start_pier_inset_mm=start_inset_mm,
        end_pier_inset_mm=end_inset_mm,
        bay_span_mm=span,
        support_centers_local_mm=supports_local,
        support_centers_absolute_mm=supports_absolute,
        cassette_boundary_stations_local_mm=tuple(boundaries),
        cassette_nominal_widths_mm=tuple(
            right - left for left, right in zip(boundaries, boundaries[1:])
        ),
        cassette_physical_widths_mm=tuple(physical),
        crown_seam_stations_local_mm=crowns,
        pier_seam_stations_local_mm=pier_seams,
    )


def calculate_plan(cfg: dict[str, Any]) -> PlanGeometry:
    """Calculate the fitted L plan and the exact 3/6 structural rhythm."""

    through_cfg = _run_by_role(cfg, "through")
    return_cfg = _run_by_role(cfg, "return")
    depth = mm(float(cfg["closet"]["shelf_depth_in"]))
    corner_cfg = cfg["closet"]["inside_corner"]
    nominal_gap = float(corner_cfg["visible_ornament_joint_gap_mm"])
    ornament = cfg["palatine"]["ornament_keyhole_contract"]
    parent_front_d = float(
        ornament["coordinate_contract"]["structural_parent_front_global_d_mm"]
    )
    boss_front_d = float(ornament["boss_full_head_block_depth_zone_mm"][0])
    full_facade_projection = parent_front_d
    integral_boss_projection = parent_front_d - boss_front_d
    if integral_boss_projection < -EPSILON:
        raise ValueError("Ornament front cannot be behind its structural parent datum")
    if full_facade_projection + EPSILON < integral_boss_projection:
        raise ValueError("Full removable facade cannot project less than its integral boss")
    service_stroke = float(
        ornament["strict_collision_gate"]["axial_insertion_sweep_total_mm"]
    )
    cosmetic_overhang = float(
        corner_cfg["return_corner_removable_cosmetic_overhang_back_mm"]
    )
    if abs(service_stroke - cosmetic_overhang) > EPSILON:
        raise ValueError(
            "Return-corner cosmetic overhang must equal the complete ornament axial stroke"
        )
    measured_angle = corner_cfg.get("field_verified_angle_deg")
    measured_bow = corner_cfg.get("field_verified_max_wall_bow_mm")
    datum_uncertainty = corner_cfg.get("field_verified_corner_datum_uncertainty_mm")
    if measured_angle is None or measured_bow is None or datum_uncertainty is None:
        # The checked-in plan is intentionally a square, zero-bow regression
        # fixture.  It is not a field-fit promise.
        gap = nominal_gap
    else:
        angle_error = abs(float(measured_angle) - 90.0)
        maximum_error = float(corner_cfg["maximum_square_corner_deviation_deg"])
        if angle_error > maximum_error + EPSILON:
            raise ValueError(
                f"Measured corner error {angle_error:.6f} deg exceeds the "
                f"{maximum_error:.6f} deg square-footprint gate"
            )
        gap = required_corner_gap_mm(
            depth_mm=depth + full_facade_projection,
            measured_angle_deg=float(measured_angle),
            minimum_gap_mm=float(
                corner_cfg["minimum_residual_visible_joint_clearance_mm"]
            ),
            wall_bow_mm=float(measured_bow),
            datum_uncertainty_mm=float(datum_uncertainty),
            manufacturing_installation_reserve_mm=float(
                corner_cfg["minimum_production_manufacturing_installation_reserve_mm"]
            ),
        )
    seam = float(cfg["structure"]["cassette_between_module_seam_mm"])

    through_wall = mm(
        _verified_or_reference(
            through_cfg, "field_verified_min_clear_wall_width_in", "nominal_clear_wall_width_in"
        )
    )
    return_wall = mm(
        _verified_or_reference(
            return_cfg, "field_verified_min_clear_wall_width_in", "nominal_clear_wall_width_in"
        )
    )
    through_back = mm(
        _verified_or_reference(
            through_cfg,
            "field_verified_installed_shelf_back_clearance_in",
            "reference_shelf_back_clearance_in",
        )
    )
    return_back = mm(
        _verified_or_reference(
            return_cfg,
            "field_verified_installed_shelf_back_clearance_in",
            "reference_shelf_back_clearance_in",
        )
    )
    through_outer = mm(float(through_cfg["target_outer_end_clearance_in"]))
    return_outer = mm(float(return_cfg["target_outer_end_clearance_in"]))

    # The perpendicular wall's installed back clearance controls each board's
    # station at the re-entrant corner.
    through_start = return_back
    through_length = through_wall - through_outer - through_start
    corner_front_plane = through_back + depth
    corner_integral_boss_front_plane = corner_front_plane + integral_boss_projection
    corner_visible_front_plane = corner_front_plane + full_facade_projection
    corner_service_swept_front_plane = corner_visible_front_plane + service_stroke
    return_cosmetic_leading_plane = corner_visible_front_plane + gap
    structural_arm_clearance = full_facade_projection + service_stroke + gap
    return_start = return_cosmetic_leading_plane + cosmetic_overhang
    return_length = return_wall - return_outer - return_start
    if min(through_length, return_length) <= 0.0:
        raise ValueError("Field clearances leave no positive shelf length")

    long_bays = int(through_cfg["palatine_arcade_bays"])
    local_corner_target = corner_front_plane - through_start
    inset = (2.0 * long_bays * local_corner_target - through_length) / (
        2.0 * (long_bays - 1)
    )

    through = _build_run(
        run=through_cfg,
        start_mm=through_start,
        length_mm=through_length,
        start_inset_mm=inset,
        end_inset_mm=inset,
        seam_mm=seam,
    )
    return_start_inset = inset - cosmetic_overhang
    return_run = _build_run(
        run=return_cfg,
        start_mm=return_start,
        length_mm=return_length,
        start_inset_mm=return_start_inset,
        end_inset_mm=inset,
        seam_mm=seam,
    )
    through = RunPlan(**{**asdict(through), "wall_width_mm": through_wall})
    return_run = RunPlan(**{**asdict(return_run), "wall_width_mm": return_wall})

    first_crown_absolute = through.start_from_corner_mm + through.crown_seam_stations_local_mm[0]
    crown_error = first_crown_absolute - corner_front_plane

    projection = float(cfg["corbel"]["shelf_arm_length_mm"])
    cap = cfg["corbel"]["integrated_bearing_cap"]
    if not cap.get("installed"):
        raise ValueError("The active plan requires the integrated bearing cap")
    cap_profile = cap.get("run_e_profile_polygon_mm")
    if not isinstance(cap_profile, list) or not cap_profile:
        raise ValueError("Integrated-cap run/e profile is required for corner clearance")
    cap_half_run = max(abs(float(point[0])) for point in cap_profile)
    through_nose = through_back + projection
    return_first_near_edge = return_run.support_centers_absolute_mm[0] - cap_half_run
    perpendicular_clearance = return_first_near_edge - through_nose
    visible_front_to_corbel_reserve = (
        return_first_near_edge - corner_visible_front_plane
    )
    structural_front_to_corbel_reserve = return_first_near_edge - corner_front_plane
    integral_boss_front_to_corbel_reserve = (
        return_first_near_edge - corner_integral_boss_front_plane
    )
    service_swept_front_to_corbel_reserve = (
        return_first_near_edge - corner_service_swept_front_plane
    )

    comb = float(cfg["nominal_geometry_snapshot"]["comb_finger_projection_mm"])
    maximum_part_axis = max(
        max(through.cassette_physical_widths_mm),
        max(return_run.cassette_physical_widths_mm),
    ) + comb

    return PlanGeometry(
        depth_mm=depth,
        corner_gap_mm=gap,
        integral_boss_projection_beyond_cassette_mm=integral_boss_projection,
        full_removable_facade_projection_beyond_cassette_mm=full_facade_projection,
        visible_front_projection_beyond_cassette_mm=full_facade_projection,
        ornament_axial_service_stroke_mm=service_stroke,
        return_corner_cosmetic_overhang_back_mm=cosmetic_overhang,
        structural_arm_clearance_mm=structural_arm_clearance,
        through_back_clearance_mm=through_back,
        return_back_clearance_mm=return_back,
        through=through,
        return_run=return_run,
        corner_front_plane_absolute_mm=corner_front_plane,
        corner_integral_boss_front_plane_absolute_mm=corner_integral_boss_front_plane,
        corner_visible_front_plane_absolute_mm=corner_visible_front_plane,
        corner_service_swept_front_plane_absolute_mm=corner_service_swept_front_plane,
        return_corner_cosmetic_leading_plane_absolute_mm=return_cosmetic_leading_plane,
        exact_crown_alignment_error_mm=crown_error,
        minimum_perpendicular_corbel_clearance_mm=perpendicular_clearance,
        minimum_structural_front_to_perpendicular_corbel_plan_reserve_mm=(
            structural_front_to_corbel_reserve
        ),
        minimum_integral_boss_front_to_perpendicular_corbel_plan_reserve_mm=(
            integral_boss_front_to_corbel_reserve
        ),
        minimum_visible_front_to_perpendicular_corbel_plan_reserve_mm=(
            visible_front_to_corbel_reserve
        ),
        minimum_service_swept_front_to_perpendicular_corbel_plan_reserve_mm=(
            service_swept_front_to_corbel_reserve
        ),
        maximum_part_axis_with_comb_mm=maximum_part_axis,
    )


def grand_arc(span_mm: float, rise_mm: float) -> ArcGeometry:
    """Return circular-segment geometry and a simple tied-arch thrust proxy."""

    span = float(span_mm)
    rise = float(rise_mm)
    if span <= 0.0 or not 0.0 < rise <= span / 2.0:
        raise ValueError("Circular-segment rise must be positive and at most half the span")
    radius = span * span / (8.0 * rise) + rise / 2.0
    included = degrees(2.0 * asin(span / (2.0 * radius)))
    # For a uniformly distributed load on a two-hinged idealized tied arch:
    # H / W = span / (8 rise). This is only a mechanics-development proxy.
    thrust_proxy = span / (8.0 * rise)
    return ArcGeometry(span, rise, radius, included, thrust_proxy)


def x_corbel_geometry(cfg: dict[str, Any]) -> XCorbelGeometry:
    """Resolve the two exact 3:4:5 load paths in the depth/elevation plane.

    Coordinates are ``(projection from wall, elevation from facade bottom)``.
    One diagonal connects the upper wall node directly to the arch springing;
    the other connects a lower wall node directly to the cassette underside.
    """

    corbel = cfg["corbel"]
    arcade = cfg["tied_arcade"]
    projection = float(corbel["triangle_horizontal_leg_mm"])
    vertical = float(corbel["triangle_vertical_leg_mm"])
    diagonal = float(corbel["triangle_hypotenuse_mm"])
    spring = float(arcade["arch_spring_extrados_y_mm"])
    cassette_underside = float(arcade["total_height_mm"]) - float(
        cfg["structure"]["cassette_total_height_mm"]
    )

    wall_upper = (0.0, spring + vertical)
    front_spring = (projection, spring)
    wall_lower = (0.0, cassette_underside - vertical)
    front_saddle = (projection, cassette_underside)

    configured_nodes = corbel.get("x_brace_nodes_mm")
    if configured_nodes:
        expected_nodes = {
            "wall_upper": wall_upper,
            "front_spring": front_spring,
            "wall_lower": wall_lower,
            "front_saddle_at_cassette_underside": front_saddle,
        }
        for name, expected in expected_nodes.items():
            actual = tuple(float(value) for value in configured_nodes.get(name, ()))
            if len(actual) != 2 or any(
                abs(actual[index] - expected[index]) > EPSILON for index in range(2)
            ):
                raise ValueError(
                    f"corbel.x_brace_nodes_mm.{name} must be {expected}, got {actual}"
                )
    actual_a = hypot(front_spring[0] - wall_upper[0], front_spring[1] - wall_upper[1])
    actual_b = hypot(front_saddle[0] - wall_lower[0], front_saddle[1] - wall_lower[1])
    if abs(actual_a - diagonal) > EPSILON or abs(actual_b - diagonal) > EPSILON:
        raise ValueError(
            f"Configured corbel is not an exact shared {projection:g}/{vertical:g}/{diagonal:g} triangle"
        )

    # Solve the intersection of z1 = upper - (vertical/projection)y and
    # z2 = lower + (vertical/projection)y.
    slope = vertical / projection
    cross_y = (wall_upper[1] - wall_lower[1]) / (2.0 * slope)
    cross_z = wall_upper[1] - slope * cross_y
    if not 0.0 < cross_y < projection:
        raise ValueError("The two X-corbel diagonals do not cross within the projection")

    return XCorbelGeometry(
        projection_mm=projection,
        vertical_leg_mm=vertical,
        diagonal_mm=diagonal,
        wall_upper_node=wall_upper,
        front_spring_node=front_spring,
        wall_lower_node=wall_lower,
        front_saddle_node=front_saddle,
        brace_crossing=(cross_y, cross_z),
    )


def required_corner_gap_mm(
    *,
    depth_mm: float,
    measured_angle_deg: float,
    minimum_gap_mm: float,
    wall_bow_mm: float,
    datum_uncertainty_mm: float = 0.0,
    manufacturing_installation_reserve_mm: float = 0.0,
) -> float:
    """Conservative field joint for angle, bow, datum, and fit reserve."""

    return (
        float(minimum_gap_mm)
        + float(depth_mm) * abs(tan(radians(float(measured_angle_deg) - 90.0)))
        + max(0.0, float(wall_bow_mm))
        + max(0.0, float(datum_uncertainty_mm))
        + max(0.0, float(manufacturing_installation_reserve_mm))
    )


def maximum_angle_error_deg(*, depth_mm: float, available_gap_mm: float) -> float:
    """Return the one-sided square-footprint angle limit for a known gap."""

    if depth_mm <= 0.0 or available_gap_mm < 0.0:
        raise ValueError("Depth must be positive and available gap nonnegative")
    return degrees(atan(available_gap_mm / depth_mm))


def production_blockers(cfg: dict[str, Any]) -> tuple[str, ...]:
    """List unresolved inputs that intentionally block production artifacts."""

    blockers: list[str] = []
    printer = cfg["printer"]
    support = cfg["support"]
    material = cfg["material"]
    closet = cfg["closet"]
    if printer.get("model") in (None, "", "UNCONFIRMED"):
        blockers.append("printer.model")
    if printer.get("nozzle_mm") is None:
        blockers.append("printer.nozzle_mm")
    if printer.get("build_plate") in (None, "", "UNCONFIRMED"):
        blockers.append("printer.build_plate")
    if material.get("brand_and_product") in (None, "", "UNCONFIRMED"):
        blockers.append("material.brand_and_product")
    if material.get("filament_drying_method") in (None, "", "UNCONFIRMED"):
        blockers.append("material.filament_drying_method")
    if closet.get("common_shelf_top_elevation_from_finished_floor_in") is None:
        blockers.append("closet.common_shelf_top_elevation_from_finished_floor_in")
    if closet["inside_corner"].get("field_verified_angle_deg") is None:
        blockers.append("closet.inside_corner.field_verified_angle_deg")
    if closet["inside_corner"].get("field_verified_max_wall_bow_mm") is None:
        blockers.append("closet.inside_corner.field_verified_max_wall_bow_mm")
    if closet["inside_corner"].get("field_verified_corner_datum_uncertainty_mm") is None:
        blockers.append(
            "closet.inside_corner.field_verified_corner_datum_uncertainty_mm"
        )
    vertical = closet["vertical_layout"]
    if not vertical.get("field_verified_shelf_top_offsets_above_outlet_top_in"):
        blockers.append(
            "closet.vertical_layout.field_verified_shelf_top_offsets_above_outlet_top_in"
        )
    if vertical.get("field_verified_outlet_service_clearance_in") is None:
        blockers.append("closet.vertical_layout.field_verified_outlet_service_clearance_in")
    for run in closet["runs"]:
        prefix = f"closet.runs[{run['id']}]"
        for key in (
            "field_verified_min_clear_wall_width_in",
            "field_verified_installed_shelf_back_clearance_in",
            "field_verified_corbel_centers_in",
            "field_verified_stud_or_blocking_material",
            "field_verified_wall_fastener",
            "target_contents_load_lb",
        ):
            value = run.get(key)
            if value is None or value == "" or value == []:
                blockers.append(f"{prefix}.{key}")
        support_records = run.get("field_verified_support_records_by_level")
        expected_centers = int(run["nominal_corbel_count"])
        for level_id in ("lower", "upper"):
            record_prefix = (
                f"{prefix}.field_verified_support_records_by_level[{level_id}]"
            )
            if not isinstance(support_records, dict) or not isinstance(
                support_records.get(level_id), dict
            ):
                blockers.append(record_prefix)
                continue
            record = support_records[level_id]
            width = record.get("clear_wall_width_in")
            if not isinstance(width, (int, float)) or isinstance(width, bool) or width <= 0:
                blockers.append(f"{record_prefix}.clear_wall_width_in")
            centers = record.get("corbel_centers_in")
            if (
                not isinstance(centers, list)
                or len(centers) != expected_centers
                or any(
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    for value in centers
                )
            ):
                blockers.append(f"{record_prefix}.corbel_centers_in")
            for key in ("stud_or_blocking_material", "framing_verification_method"):
                if record.get(key) in (None, "", "UNCONFIRMED"):
                    blockers.append(f"{record_prefix}.{key}")
    for key in (
        "field_verified_screw_shank_diameter_mm",
        "field_verified_screw_head_or_washer_od_mm",
        "field_verified_screw_length_in",
        "field_verified_thread_embedment_in",
        "field_verified_wall_finish_type",
        "field_verified_wall_finish_thickness_in",
        "field_verified_utility_clearance_method",
        "field_verified_driver_maximum_od_mm",
        "field_verified_driver_straight_approach_mm",
    ):
        if support.get(key) is None:
            blockers.append(f"support.{key}")
    storage = closet["storage_contents"]
    for key in (
        "largest_bin_or_item_width_in",
        "largest_bin_or_item_depth_in",
        "largest_bin_or_item_height_in",
        "largest_loaded_bin_or_item_weight_lb",
        "quantity_per_shelf",
    ):
        if storage.get(key) is None:
            blockers.append(f"closet.storage_contents.{key}")
    protocol = cfg["test_protocol"]
    required_load_cases = protocol.get("required_nondestructive_load_cases", [])
    completed_load_cases = protocol.get("nondestructive_load_case_completion", {})
    for load_case in required_load_cases:
        if completed_load_cases.get(load_case) is not True:
            blockers.append(
                f"test_protocol.nondestructive_load_case_completion[{load_case}]"
            )
    thermal = protocol.get("whole_article_thermal_cycling", {})
    for key in (
        "planned_cycle_count",
        "minimum_service_temperature_c",
        "maximum_service_temperature_c",
    ):
        if thermal.get(key) is None:
            blockers.append(f"test_protocol.whole_article_thermal_cycling.{key}")
    if thermal.get("completed") is not True:
        blockers.append("test_protocol.whole_article_thermal_cycling.completed")
    destructive = protocol.get("destructive_load_to_failure", {})
    if destructive.get("separate_specimen_id") in (None, ""):
        blockers.append(
            "test_protocol.destructive_load_to_failure.separate_specimen_id"
        )
    if destructive.get("completed") is not True:
        blockers.append("test_protocol.destructive_load_to_failure.completed")
    return tuple(blockers)
