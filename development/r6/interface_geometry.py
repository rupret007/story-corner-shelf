#!/usr/bin/env python3
"""Pure cross-part interface contracts for Story Corner r6.

This module deliberately creates no meshes.  It defines the exact coordinate,
clearance, thermal-slip, and corner-fit relationships that the generator must
prove before it may emit complete shelf packages.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from design_math import EPSILON, required_corner_gap_mm


@dataclass(frozen=True)
class StructuralElevationContract:
    cassette_underside_y_mm: float
    structural_crown_extrados_y_mm: float
    structural_spring_extrados_y_mm: float
    structural_rise_mm: float
    structural_rib_mm: float
    structural_crown_intrados_y_mm: float
    visual_crown_extrados_y_mm: float
    wall_upper_node: tuple[float, float]
    front_spring_node: tuple[float, float]
    wall_lower_node: tuple[float, float]
    front_saddle_node: tuple[float, float]
    x_crossing: tuple[float, float]
    upper_x_cradle_q_max_mm: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SaddleThermalContract:
    ridge_width_mm: float
    terminal_pocket_width_mm: float
    floating_pocket_width_mm: float
    ridge_depth_mm: float
    pocket_depth_mm: float
    q_centers_mm: tuple[float, float]
    minimum_q_ligament_mm: float
    ridge_bearing_area_mm2: float
    ridge_height_mm: float
    integrated_cap_installed: bool
    cap_wall_projection_x_mm: tuple[float, float]
    cap_e_mm: tuple[float, float]
    cap_base_run_mm: tuple[float, float]
    cap_top_run_mm: tuple[float, float]
    total_axial_travel_mm: float
    fixed_side: str
    floating_side: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CrownBridgeContract:
    body_u_mm: tuple[float, float]
    body_e_mm: tuple[float, float]
    body_q_mm: tuple[float, float]
    rail_centers_u_mm: tuple[float, float]
    rail_u_envelopes_mm: tuple[tuple[float, float], ...]
    rail_q_mm: tuple[float, float]
    keyway_q_mm: tuple[float, float]
    keyway_open_e_mm: tuple[float, float]
    rail_e_mm: tuple[float, float]
    swept_lug_e_mm: tuple[float, float]
    hard_stop_roof_e_mm: tuple[float, float]
    swept_body_e_mm: tuple[float, float]
    cassette_underside_e_mm: float
    body_to_cassette_vertical_clearance_mm: float
    top_receiver_u_clearance_mm: float
    top_receiver_q_clearance_mm: float
    pin_center_u_e_mm: tuple[float, float]
    front_ear_q_mm: tuple[float, float]
    rear_ear_q_mm: tuple[float, float]
    rear_ear_parent_spine_q_mm: tuple[float, float]
    rear_ear_parent_union_e_mm: tuple[float, float]
    rear_ear_parent_spine_e_mm: tuple[float, float]
    common_parent_rib_e_mm: tuple[float, float]
    worst_case_roof_mm: float
    pin_boss_to_keyway_clearance_mm: float
    pin_split_zone_q_mm: tuple[float, float]
    pin_unsplit_shaft_q_mm: tuple[float, float]
    pin_barb_q_mm: tuple[float, float]
    pin_head_q_mm: tuple[float, float]
    pin_release_window_u_q_e_mm: tuple[tuple[float, float], tuple[float, float], tuple[float, float]]
    pin_saved_bare_envelope_mm: tuple[float, float, float]
    pin_proxy_strain_fraction: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OrnamentInterfaceContract:
    visual_crown_e_mm: float
    visual_spring_e_mm: float
    visual_rise_mm: float
    visual_seam_mm: float
    through_carrier_width_mm: float
    return_carrier_width_mm: float
    fixed_keyholes: int
    elongated_keyholes: int
    elongated_travel_mm: float
    parent_union_overlap_mm: float
    global_depth_offset_mm: float
    boss_count_per_level: int
    parent_boss_union_volume_mm3: float
    gravity_sweep_step_mm: float
    family_map_keys: tuple[str, ...]
    connector_placement_complete: bool
    software_model_mapping_contract_required: bool
    physical_installation_mapping_qualified: bool
    production_release_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def structural_elevation_contract(cfg: dict[str, Any]) -> StructuralElevationContract:
    arcade = cfg["tied_arcade"]
    corbel = cfg["corbel"]
    underside = float(arcade["cassette_entablature_bottom_y_mm"])
    crown = float(arcade["arch_crown_extrados_y_mm"])
    spring = float(arcade["arch_spring_extrados_y_mm"])
    rise = float(arcade["arch_extrados_rise_mm"])
    rib = float(arcade["arch_radial_rib_mm"])
    if abs(crown - underside) > EPSILON:
        raise ValueError("The separate structural rib must touch, not overlap, the cassette underside")
    if abs((crown - spring) - rise) > EPSILON:
        raise ValueError("Structural crown, spring, and rise are inconsistent")
    if abs(float(arcade["arch_to_cassette_entablature_overlap_mm"])) > EPSILON:
        raise ValueError("Separate printed arch and cassette may not have solid-volume overlap")

    nodes = corbel["x_brace_nodes_mm"]
    wall_upper = tuple(float(value) for value in nodes["wall_upper"])
    front_spring = tuple(float(value) for value in nodes["front_spring"])
    wall_lower = tuple(float(value) for value in nodes["wall_lower"])
    front_saddle = tuple(float(value) for value in nodes["front_saddle_at_cassette_underside"])
    crossing = tuple(float(value) for value in corbel["x_brace_crossing_mm"])
    for wall, front in ((wall_upper, front_spring), (wall_lower, front_saddle)):
        if abs((front[0] - wall[0]) - 144.0) > EPSILON:
            raise ValueError("Each X path must retain the exact 144 mm horizontal leg")
        if abs(abs(front[1] - wall[1]) - 108.0) > EPSILON:
            raise ValueError("Each X path must retain the exact 108 mm vertical leg")
    if front_spring[1] != spring or front_saddle[1] != underside:
        raise ValueError("X front nodes must meet the structural spring and cassette underside")
    cradle = corbel["upper_diagonal_cassette_union_segment_mm"]
    centerline_q = float(cradle["centerline_local_q_at_e_133_2_mm"])
    outer_q = float(cradle["outer_solid_maximum_local_q_at_cassette_underside_mm"])
    cutter_q = float(cradle["maximum_local_q_from_rear_mm"])
    fit = float(cradle["cradle_fit_clearance_mm"])
    if abs(centerline_q - 21.383333) > EPSILON or abs(outer_q - 24.983333) > EPSILON:
        raise ValueError("Upper-X centerline and 12 mm outer envelope are not the audited geometry")
    if abs(cutter_q - outer_q - fit) > EPSILON:
        raise ValueError("Upper-X cradle cutter omits the configured fit clearance")
    return StructuralElevationContract(
        cassette_underside_y_mm=underside,
        structural_crown_extrados_y_mm=crown,
        structural_spring_extrados_y_mm=spring,
        structural_rise_mm=rise,
        structural_rib_mm=rib,
        structural_crown_intrados_y_mm=crown - rib,
        visual_crown_extrados_y_mm=float(arcade["visual_facade_crown_extrados_y_mm"]),
        wall_upper_node=wall_upper,
        front_spring_node=front_spring,
        wall_lower_node=wall_lower,
        front_saddle_node=front_saddle,
        x_crossing=crossing,
        upper_x_cradle_q_max_mm=cutter_q,
    )


def saddle_thermal_contract(cfg: dict[str, Any]) -> SaddleThermalContract:
    corbel = cfg["corbel"]
    ridge = float(corbel["saddle_locator_ridge_run_width_mm"])
    terminal = float(corbel["terminal_saddle_locator_pocket_run_width_mm"])
    floating = float(corbel["floating_pier_saddle_locator_pocket_run_width_mm"])
    ridge_depth = float(corbel["saddle_locator_ridge_depth_along_shelf_mm"])
    pocket_depth = float(corbel["saddle_locator_pocket_depth_along_shelf_mm"])
    q_centers = tuple(float(value) for value in corbel["saddle_locator_centers_from_rear_mm"])
    travel = float(corbel["floating_pier_total_axial_travel_mm"])
    nominal_fit_total = 0.4
    if floating + EPSILON < ridge + nominal_fit_total + travel:
        raise ValueError("Floating saddle pocket does not preserve fit clearance plus travel")
    if abs(terminal - (ridge + nominal_fit_total)) > EPSILON:
        raise ValueError("Terminal saddle pocket must remain the tight reference fit")
    if abs(pocket_depth - (ridge_depth + nominal_fit_total)) > EPSILON:
        raise ValueError("Saddle locator pocket depth must preserve the qualified 0.4 mm total fit")
    if abs(float(corbel["floating_pier_lock_slot_total_axial_travel_mm"]) - travel) > EPSILON:
        raise ValueError("Cassette locks must preserve the same axial travel as the locator pocket")
    bowtie = cfg["joinery"]["diaphragm_bowtie"]
    mouth_depth = float(bowtie["depth_mm"])
    mouths = tuple(
        (float(center) - mouth_depth / 2.0, float(center) + mouth_depth / 2.0)
        for center in bowtie["centers_from_rear_mm"]
    )
    if len(q_centers) != len(mouths) - 1:
        raise ValueError("There must be one saddle locator band between each diaphragm mouth")
    ligaments: list[float] = []
    for index, center in enumerate(q_centers):
        expected_center = (mouths[index][1] + mouths[index + 1][0]) / 2.0
        if abs(center - expected_center) > EPSILON:
            raise ValueError("Saddle locator is not centered in its diaphragm-mouth clear band")
        pocket = (center - pocket_depth / 2.0, center + pocket_depth / 2.0)
        ligaments.extend((pocket[0] - mouths[index][1], mouths[index + 1][0] - pocket[1]))
    minimum_ligament = min(ligaments)
    required_wall = float(cfg["joinery"]["minimum_wall_mm"])
    if minimum_ligament < required_wall - EPSILON:
        raise ValueError("Saddle locator pocket leaves less than the minimum q ligament")
    if abs(minimum_ligament - float(corbel["saddle_locator_minimum_q_ligament_mm"])) > EPSILON:
        raise ValueError("Configured saddle locator q ligament does not match exact geometry")
    bearing_area = ridge * ridge_depth
    if bearing_area < 112.0 - EPSILON:
        raise ValueError("Rotated locator footprint silently loses the prior 112 mm2 bearing area")
    ridge_height = float(corbel["saddle_locator_ridge_height_mm"])
    cap = corbel["integrated_bearing_cap"]
    if not cap["installed"] or corbel["separate_sliding_saddle_installed"] or corbel["separate_saddle_pin_installed"]:
        raise ValueError("The release candidate must use the integral cap with no separate saddle or pin")
    cap_x = tuple(float(value) for value in cap["wall_projection_x_mm"])
    cap_e = tuple(float(value) for value in cap["vertical_envelope_mm"])
    cap_base = tuple(float(value) for value in cap["base_run_envelope_at_e_128_mm"])
    cap_top = tuple(float(value) for value in cap["top_run_envelope_at_e_138_mm"])
    if cap_x != (0.0, 144.0) or cap_e != (128.0, 138.0):
        raise ValueError("Integrated cap does not span the exact wall-to-shelf bearing path")
    if cap_base != (-24.0, 24.0) or cap_top != (-24.0, 24.0):
        raise ValueError("Integrated cap is not the exact full-width lock-clearing 48 mm bearing cap")
    hold_e = float(cap["base_constant_run_envelope_to_e_mm"])
    if abs(hold_e - 138.0) > EPSILON or abs(float(cap["side_flare_angle_deg"])) > EPSILON:
        raise ValueError("Integrated cap may not taper around the outboard lock service paths")
    if "75 mm" not in cap["full_width_cap_reason"] or "unioned directly" not in cap["rising_x_endpoint_union_rule"]:
        raise ValueError("Integrated cap lacks its exact service-sweep or X-end union contract")
    return SaddleThermalContract(
        ridge, terminal, floating, ridge_depth, pocket_depth, q_centers,
        minimum_ligament, bearing_area, ridge_height, True, cap_x, cap_e,
        cap_base, cap_top, travel, "right/outboard/next", "left/cornerward/previous",
    )


def spring_socket_contract(cfg: dict[str, Any]) -> dict[str, Any]:
    """Validate the one global spring-tenon/socket datum in run/depth/elevation."""

    spring = cfg["tied_arcade"]["spring_final_x_vertical_joint"]
    support_offset = float(spring["tenon_center_crownward_from_support_mm"])
    tenon_run = tuple(float(value) for value in spring["tenon_run_envelope_from_support_toward_crown_mm"])
    if abs(sum(tenon_run) / 2.0 - support_offset) > EPSILON:
        raise ValueError("Spring tenon run envelope is not centered on the support offset")
    if tuple(float(value) for value in spring["interior_socket_centers_from_support_mm"]) != (-support_offset, support_offset):
        raise ValueError("Interior spring sockets must be a true handed pair")
    q_cassette = float(spring["tenon_center_q_from_cassette_rear_mm"])
    back = float(cfg["closet"]["runs"][0]["reference_shelf_back_clearance_in"]) * 25.4
    q_wall = float(spring["tenon_center_q_from_finished_wall_mm"])
    if abs(q_cassette + back - q_wall) > EPSILON:
        raise ValueError("Spring q datum does not include the configured shelf-back clearance")
    tenon_depth = float(spring["tenon_depth_mm"])
    receiver_depth = float(spring["receiver_depth_mm"])
    receiver_q = tuple(float(value) for value in spring["receiver_q_envelope_from_finished_wall_mm"])
    housing_q = tuple(float(value) for value in spring["receiver_housing_q_envelope_from_finished_wall_mm"])
    if abs(receiver_q[1] - receiver_q[0] - receiver_depth) > EPSILON:
        raise ValueError("Spring receiver q envelope does not equal receiver depth")
    tenon_q = (q_wall - tenon_depth / 2.0, q_wall + tenon_depth / 2.0)
    if receiver_q[0] > tenon_q[0] + EPSILON or receiver_q[1] < tenon_q[1] - EPSILON:
        raise ValueError("Spring receiver does not contain the tenon in q")
    if not (housing_q[0] <= receiver_q[0] and housing_q[1] >= receiver_q[1]):
        raise ValueError("Spring housing does not contain its receiver")
    upper_x = cfg["corbel"]["upper_diagonal_cassette_union_segment_mm"]
    nonhousing_clip = float(upper_x["nonhousing_descending_x_max_wall_projection_mm"])
    moving_shoulder_min = float(upper_x["moving_arch_shoulder_min_wall_projection_mm"])
    moving_clearance = float(upper_x["nonhousing_to_moving_arch_minimum_clearance_mm"])
    if abs(moving_shoulder_min - housing_q[0]) > EPSILON:
        raise ValueError("Moving-arch shoulder datum disagrees with the spring housing front datum")
    if abs(moving_shoulder_min - nonhousing_clip - moving_clearance) > EPSILON or moving_clearance < 0.4 - EPSILON:
        raise ValueError("Nonhousing descending X does not preserve the exact 0.4 mm arch-lift clearance")
    capital = tuple(float(value) for value in spring["capital_clevis_footprint_from_support_toward_crown_mm"])
    shoulder_run = tuple(float(value) for value in spring["capital_shoulder_run_envelope_from_support_toward_crown_mm"])
    shoulder_e = tuple(float(value) for value in spring["capital_shoulder_y_envelope_mm"])
    housing_e = tuple(float(value) for value in spring["receiver_housing_y_envelope_mm"])
    arc_root = tuple(float(value) for value in spring["structural_arc_root_from_support_toward_crown_mm"])
    if capital != (0.0, 28.0) or shoulder_run != capital or shoulder_e != (42.8, 46.0):
        raise ValueError("Spring capital/shoulder is not the audited compact clevis")
    if housing_e != (46.0, 68.0) or float(spring["receiver_housing_bottom_y_mm"]) != 46.0:
        raise ValueError("Spring receiver housing must begin at the e=46 hard stop")
    housing_runs = cfg["corbel"]["integrated_bearing_cap"][
        "interior_spring_housing_run_envelopes_mm"
    ]
    physical_housing_end = max(abs(float(value)) for pair in housing_runs for value in pair)
    if arc_root != (28.8, 46.0) or abs(
        arc_root[0]
        - physical_housing_end
        - float(spring["structural_arc_root_clearance_from_clevis_mm"])
    ) > EPSILON:
        raise ValueError(
            "Structural arc root does not clear the physical compact-clevis housing by 0.4 mm"
        )
    seam_half = physical_crown_face_shift_mm(cfg)
    through_half = float(cfg["nominal_geometry_snapshot"]["through_arch_span_mm"]) / 2.0
    return_half = float(cfg["nominal_geometry_snapshot"]["return_arch_span_mm"]) / 2.0
    through_clear = through_half - seam_half - arc_root[0]
    return_clear = return_half - seam_half - arc_root[0]
    if abs(through_clear - float(spring["through_clear_half_run_root_to_physical_crown_mm"])) > EPSILON or abs(return_clear - float(spring["return_clear_half_run_root_to_physical_crown_mm"])) > EPSILON:
        raise ValueError("Regenerated spring-to-physical-crown half-runs are inconsistent")
    rise = float(cfg["tied_arcade"]["arch_extrados_rise_mm"])
    through_radius = (through_clear * through_clear + rise * rise) / (2.0 * rise)
    return_radius = (return_clear * return_clear + rise * rise) / (2.0 * rise)
    crown_e = float(cfg["tied_arcade"]["arch_crown_extrados_y_mm"])
    through_center_e = crown_e - through_radius
    return_center_e = crown_e - return_radius
    for actual, key in (
        (through_radius, "through_regenerated_arc_radius_mm"),
        (through_center_e, "through_regenerated_arc_center_y_mm"),
        (return_radius, "return_regenerated_arc_radius_mm"),
        (return_center_e, "return_regenerated_arc_center_y_mm"),
    ):
        if abs(actual - float(spring[key])) > 1.0e-9:
            raise ValueError("Regenerated structural arc circle math is inconsistent")
    if spring["full_height_structural_pier_solid_allowed"]:
        raise ValueError("The colliding redundant full-height structural pier is prohibited")
    if float(spring["minimum_root_transition_web_mm"]) < float(cfg["tied_arcade"]["minimum_haunch_web_mm"]):
        raise ValueError("Regenerated arc root transition is thinner than the haunch minimum")
    return {
        "support_offset_mm": support_offset,
        "run_start_socket_center_mm": support_offset,
        "run_end_socket_center_mm": -support_offset,
        "interior_socket_centers_mm": [-support_offset, support_offset],
        "tenon_q_wall_mm": list(tenon_q),
        "receiver_q_wall_mm": list(receiver_q),
        "housing_q_wall_mm": list(housing_q),
        "nonhousing_descending_xwall_clip_mm": nonhousing_clip,
        "nonhousing_to_moving_arch_clearance_mm": moving_clearance,
        "tenon_e_mm": [float(value) for value in spring["tenon_final_y_envelope_mm"]],
        "capital_clevis_u_mm": list(capital),
        "capital_shoulder_e_mm": list(shoulder_e),
        "receiver_housing_e_mm": list(housing_e),
        "structural_arc_root_u_e_mm": list(arc_root),
        "through_clear_half_run_mm": through_clear,
        "return_clear_half_run_mm": return_clear,
        "through_arc_radius_mm": through_radius,
        "through_arc_center_e_mm": through_center_e,
        "return_arc_radius_mm": return_radius,
        "return_arc_center_e_mm": return_center_e,
        "full_height_structural_pier_allowed": False,
        "installation_motion": "+e at final s and q",
    }


def crown_bridge_contract(cfg: dict[str, Any]) -> CrownBridgeContract:
    """Fail closed unless the bridge, keyways, stop, and one pin form one exact joint."""

    arcade = cfg["tied_arcade"]
    bridge = arcade["rear_crown_bridge"]
    minimum_wall = float(cfg["joinery"]["minimum_wall_mm"])
    body_u = tuple(float(value) for value in bridge["final_u_envelope_from_crown_mm"])
    body_e = tuple(float(value) for value in bridge["final_y_envelope_mm"])
    body_q = tuple(float(value) for value in bridge["bridge_body_q_envelope_mm"])
    if abs(body_u[1] - body_u[0] - float(bridge["width_mm"])) > EPSILON:
        raise ValueError("Crown bridge body is not exactly 72 mm wide")
    if abs(body_e[1] - body_e[0] - float(bridge["height_mm"])) > EPSILON:
        raise ValueError("Crown bridge body is not exactly 48 mm high")
    if abs(body_q[1] - body_q[0] - float(bridge["thickness_mm"])) > EPSILON:
        raise ValueError("Crown bridge body is not exactly 6.4 mm thick")
    if bridge["bridge_body_has_downward_tab"]:
        raise ValueError("A downward crown-bridge tab is prohibited")
    cassette_underside = float(bridge["cassette_underside_y_mm"])
    if abs(cassette_underside - float(arcade["cassette_entablature_bottom_y_mm"])) > EPSILON:
        raise ValueError("Crown bridge and cassette use different underside datums")
    body_to_cassette = cassette_underside - body_e[1]
    if body_to_cassette < -EPSILON or bridge["cassette_overlap_volume_allowed"]:
        raise ValueError("Crown bridge body overlaps the continuous cassette volume")
    if bridge["body_top_is_cassette_underside_hard_stop"] and abs(body_to_cassette) > EPSILON:
        raise ValueError("Crown bridge body top must stop exactly at the cassette underside")

    rails = bridge["dovetail_rails"]
    centers = tuple(float(value) for value in rails["u_centers_from_crown_mm"])
    lug_width = float(rails["lug_width_along_u_mm"])
    envelopes = tuple(tuple(float(value) for value in pair) for pair in rails["lug_u_envelopes_mm"])
    expected = tuple((center - lug_width / 2.0, center + lug_width / 2.0) for center in centers)
    if any(abs(a - b) > EPSILON for pair, exp in zip(envelopes, expected) for a, b in zip(pair, exp)):
        raise ValueError("Crown rail U envelopes do not match their centers and widths")
    if min(pair[0] - body_u[0] for pair in envelopes) < minimum_wall - EPSILON or min(body_u[1] - pair[1] for pair in envelopes) < minimum_wall - EPSILON:
        raise ValueError("Depth-projecting crown lugs do not preserve the bridge edge wall")
    rail_q = tuple(float(value) for value in rails["lug_q_envelope_mm"])
    keyway_q = tuple(float(value) for value in rails["keyway_q_envelope_mm"])
    if abs(rail_q[1] - rail_q[0] - float(rails["lug_projection_in_q_mm"])) > EPSILON:
        raise ValueError("Crown lugs must project 4.8 mm in q, not in u")
    if rail_q[0] != body_q[1] or keyway_q[0] != body_q[1] or keyway_q[1] < rail_q[1]:
        raise ValueError("Crown rail/keyway q stack is discontinuous")
    union_overlap_q = float(rails["lug_body_union_overlap_q_mm"])
    if abs(union_overlap_q - 0.02) > EPSILON:
        raise ValueError("Crown lugs require the exact 0.02 mm positive body union")
    if abs(float(rails["keyway_head_width_along_u_mm"]) - lug_width - 0.8) > EPSILON:
        raise ValueError("Crown keyway does not preserve 0.4 mm clearance per U face")

    rail_e = tuple(float(value) for value in rails["final_y_envelope_mm"])
    if abs(rail_e[1] - rail_e[0] - float(rails["minimum_engagement_height_mm"])) > EPSILON:
        raise ValueError("Crown lug engagement height does not match its audited contract")
    keyway_open_e = tuple(float(value) for value in rails["keyway_open_bottom_y_envelope_mm"])
    delta = tuple(float(value) for value in bridge["upward_insertion_delta_y_mm"])
    if delta[1] != 0.0 or delta[0] >= 0.0 or abs(delta[0]) + EPSILON < float(bridge["minimum_clear_upward_approach_mm"]):
        raise ValueError("Crown bridge lacks its full straight upward approach path")
    swept_lug_e = (rail_e[0] + delta[0], rail_e[1] + delta[1])
    if keyway_open_e[0] > swept_lug_e[0] + EPSILON or keyway_open_e[1] < swept_lug_e[1] - EPSILON:
        raise ValueError("Open-bottom keyway does not contain the complete upward lug sweep")
    roof = tuple(float(value) for value in rails["hard_stop_roof_y_envelope_mm"])
    if abs(roof[0] - rail_e[1]) > EPSILON or roof[1] - roof[0] < minimum_wall - EPSILON:
        raise ValueError("Crown hard-stop roof is absent or too thin")
    if roof[1] > cassette_underside + EPSILON:
        raise ValueError("Crown keyway roof breaches the continuous cassette")
    common_parent = tuple(float(value) for value in rails["common_guaranteed_parent_rib_y_envelope_mm"])
    long_parent = tuple(float(value) for value in rails["long_arch_guaranteed_parent_rib_y_envelope_mm"])
    return_parent = tuple(float(value) for value in rails["return_arch_guaranteed_parent_rib_y_envelope_mm"])
    if abs(common_parent[0] - max(long_parent[0], return_parent[0])) > EPSILON or abs(common_parent[1] - min(long_parent[1], return_parent[1])) > EPSILON:
        raise ValueError("Common crown parent band is not the long/return intersection")
    if common_parent[0] > rail_e[0] + EPSILON or common_parent[1] < roof[1] - EPSILON:
        raise ValueError("Short crown lug/keyway/roof leaves the guaranteed arch-rib material")
    keyway_half = float(rails["keyway_head_width_along_u_mm"]) / 2.0
    keyway_u_inner = abs(centers[1]) - keyway_half
    keyway_u_outer = abs(centers[1]) + keyway_half
    installed_keyway_centers = tuple(
        float(value) for value in rails["installed_keyway_u_centers_from_nominal_seam_mm"]
    )
    face_offset = float(rails["physical_crown_face_offset_each_side_mm"])
    source_center = float(rails["keyway_source_center_inward_from_physical_crown_face_mm"])
    if installed_keyway_centers != centers or abs(face_offset - physical_crown_face_shift_mm(cfg)) > EPSILON:
        raise ValueError("Crown keyway nominal-seam and physical-face datums disagree")
    if abs(source_center + face_offset - abs(centers[1])) > EPSILON:
        raise ValueError("Handed crown keyway source does not compensate the physical half-seam offset")
    source_keyway_u_inner = source_center - keyway_half
    source_keyway_u_outer = source_center + keyway_half
    spring = arcade["spring_final_x_vertical_joint"]
    rib = float(arcade["arch_radial_rib_mm"])
    derived_parents: list[tuple[float, float]] = []
    for radius_key, center_key in (
        ("through_regenerated_arc_radius_mm", "through_regenerated_arc_center_y_mm"),
        ("return_regenerated_arc_radius_mm", "return_regenerated_arc_center_y_mm"),
    ):
        radius = float(spring[radius_key])
        center_e = float(spring[center_key])
        derived_parents.append(
            (
                center_e + math.sqrt((radius - rib) ** 2 - source_keyway_u_inner**2),
                center_e + math.sqrt(radius**2 - source_keyway_u_outer**2),
            )
        )
    for configured, derived in zip((long_parent, return_parent), derived_parents):
        if any(abs(a - b) > 1.0e-9 for a, b in zip(configured, derived)):
            raise ValueError("Crown parent-rib envelope is not derived from the exact keyway width and regenerated radius")
    worst_roof = common_parent[1] - rail_e[1]
    if worst_roof < minimum_wall - EPSILON or abs(worst_roof - float(rails["minimum_worst_case_parent_roof_mm"])) > EPSILON:
        raise ValueError("Worst-case long/return crown roof is below its exact audited thickness")
    swept_body = tuple(float(value) for value in bridge["upward_swept_body_y_envelope_mm"])
    if abs(swept_body[0] - (body_e[0] + delta[0])) > EPSILON or abs(swept_body[1] - body_e[1]) > EPSILON:
        raise ValueError("Crown body swept envelope is inconsistent")

    nearest_u = float(bridge["nearest_top_receiver_u_edge_mm"])
    u_clearance = nearest_u - (centers[1] + float(rails["keyway_head_width_along_u_mm"]) / 2.0)
    nearest_q = tuple(float(value) for value in bridge["nearest_top_receiver_q_envelope_mm"])
    q_clearance = nearest_q[0] - body_q[1]
    if u_clearance < minimum_wall - EPSILON or q_clearance < minimum_wall - EPSILON:
        raise ValueError("Crown bridge/keyway collides with the nearest top receiver")
    if abs(u_clearance - float(bridge["minimum_keyway_to_top_receiver_u_clearance_mm"])) > EPSILON or abs(q_clearance - float(bridge["minimum_body_to_top_receiver_q_clearance_mm"])) > EPSILON:
        raise ValueError("Configured crown/top-receiver clearances do not match exact envelopes")

    pin_center = tuple(float(value) for value in bridge["retention_pin_center_u_y_mm"])
    hole = float(bridge["retention_pin_hole_diameter_mm"])
    ligament = float(bridge["retention_pin_clear_ligament_mm"])
    boss = tuple(float(value) for value in bridge["retention_pin_minimum_boss_u_y_mm"])
    if any(abs(value - (hole + 2.0 * ligament)) > EPSILON for value in boss):
        raise ValueError("Crown pin boss does not preserve the configured 7 mm ligament")
    right_keyway_inner = centers[1] - float(rails["keyway_head_width_along_u_mm"]) / 2.0
    pin_boss_right = pin_center[0] + boss[0] / 2.0
    pin_boss_top = pin_center[1] + boss[1] / 2.0
    u_separation = right_keyway_inner - pin_boss_right
    e_separation = common_parent[0] - pin_boss_top
    pin_keyway_clearance = max(u_separation, e_separation)
    if pin_keyway_clearance < minimum_wall - EPSILON:
        raise ValueError("Fixed-right crown pin boss crowds the right keyway in both u and e")
    boss_u = tuple(float(value) for value in bridge["retention_pin_boss_u_envelope_mm"])
    boss_e = tuple(float(value) for value in bridge["retention_pin_boss_y_envelope_mm"])
    expected_boss_u = (pin_center[0] - boss[0] / 2.0, pin_center[0] + boss[0] / 2.0)
    expected_boss_e = (pin_center[1] - boss[1] / 2.0, pin_center[1] + boss[1] / 2.0)
    if any(abs(a - b) > EPSILON for a, b in zip(boss_u, expected_boss_u)) or any(abs(a - b) > EPSILON for a, b in zip(boss_e, expected_boss_e)):
        raise ValueError("Crown pin boss envelope does not match its exact center and 7 mm ligaments")
    if body_e[1] - (pin_center[1] + hole / 2.0) < ligament - EPSILON:
        raise ValueError("Crown pin bore lacks its top ligament")
    if pin_center[1] - hole / 2.0 - body_e[0] < ligament - EPSILON:
        raise ValueError("Crown pin bore lacks its bottom ligament")
    front_ear = tuple(float(value) for value in bridge["front_shear_ear_q_envelope_mm"])
    rear_ear = tuple(float(value) for value in bridge["rear_shear_ear_q_envelope_mm"])
    ear_gap = float(bridge["ear_to_bridge_clearance_mm"])
    if abs(front_ear[0] - body_q[1] - ear_gap) > EPSILON or abs(body_q[0] - rear_ear[1] - ear_gap) > EPSILON:
        raise ValueError("Double-shear ears do not flank the bridge with the exact clearance")
    if front_ear[1] - front_ear[0] < minimum_wall - EPSILON or rear_ear[1] - rear_ear[0] < minimum_wall - EPSILON:
        raise ValueError("Crown double-shear ears are thinner than the minimum wall")
    rear_union_e = tuple(float(value) for value in bridge["rear_shear_ear_parent_union_y_envelope_mm"])
    rear_spine_q = tuple(float(value) for value in bridge["rear_shear_ear_parent_spine_q_envelope_mm"])
    rear_spine_e = tuple(float(value) for value in bridge["rear_shear_ear_parent_spine_y_envelope_mm"])
    rear_spine_min = tuple(float(value) for value in bridge["rear_shear_ear_parent_spine_minimum_cross_section_mm"])
    diaphragm = cfg["joinery"]["diaphragm_bowtie"]
    third_mouth_end = float(diaphragm["centers_from_rear_mm"][-1]) + float(diaphragm["depth_mm"]) / 2.0
    if abs(rear_union_e[0] - (cassette_underside - 0.02)) > EPSILON or abs(rear_union_e[1] - (cassette_underside + minimum_wall)) > EPSILON:
        raise ValueError("Rear crown ear lacks its 0.02 mm overlap plus 3.2 mm cassette-parent union")
    if rear_spine_q != (third_mouth_end, rear_ear[1]) or rear_spine_e != (cassette_underside, cassette_underside + minimum_wall):
        raise ValueError("Rear crown ear parent spine is not the exact uncut 3.2 x 3.2 mm band beyond the third diaphragm mouth")
    if abs(rear_spine_q[1] - rear_spine_q[0] - rear_spine_min[0]) > EPSILON or abs(rear_spine_e[1] - rear_spine_e[0] - rear_spine_min[1]) > EPSILON or min(rear_spine_min) < minimum_wall - EPSILON:
        raise ValueError("Rear crown ear parent spine falls below the minimum printed cross-section")
    if abs(float(bridge["rear_shear_ear_parent_spine_to_third_diaphragm_q_clearance_mm"])) > EPSILON:
        raise ValueError("Rear crown ear spine must begin exactly at, but never overlap, the third diaphragm receiver boundary")
    transition_rule = str(bridge["rear_shear_ear_parent_transition_rule"])
    if not all(token in transition_rule for token in ("<=45 degree", "one connected body", "top-skin-down")):
        raise ValueError("Rear crown ear lacks its printable connected transition contract")
    if not bridge["front_shear_ear_owner"].startswith("right structural arch half only") or not bridge["rear_shear_ear_owner"].startswith("right fixed-crown cassette only"):
        raise ValueError("Crown double-shear ears do not have one exact stationary parent each")
    if abs(float(bridge["front_tie_minimum_vertical_clearance_mm"]) - 0.2) > EPSILON or boss_e[1] + 0.2 > 138.2 + EPSILON:
        raise ValueError("Crown front ear crowds the visible-front tie")
    if bridge["retention_pin_axis"] != "from the visible front toward the wall along -q":
        raise ValueError("Crown pin is not accessible on the declared straight service axis")
    if "split tail" not in bridge["positive_keeper_rule"] or float(bridge["minimum_straight_service_access_mm"]) < 75.0:
        raise ValueError("Crown pin lacks a positive accessible tail keeper")
    tail = bridge["retention_pin_positive_tail_contract"]
    split_q = tuple(float(value) for value in tail["split_zone_q_envelope_mm"])
    shaft_q = tuple(float(value) for value in tail["unsplit_shaft_q_envelope_mm"])
    ramp_q = tuple(float(value) for value in tail["rear_lead_ramp_q_envelope_mm"])
    barb_q = tuple(float(value) for value in tail["barb_max_q_envelope_mm"])
    head_q = tuple(float(value) for value in tail["head_q_envelope_mm"])
    release_window = tuple(
        tuple(float(value) for value in envelope)
        for envelope in tail["free_space_release_window_u_q_e_envelopes_mm"]
    )
    saved_pin = tuple(float(value) for value in tail["saved_bare_envelope_mm"])
    if float(tail["uncompressed_shaft_diameter_mm"]) != float(bridge["retention_pin_diameter_mm"]) or float(tail["parent_bore_diameter_mm"]) != hole:
        raise ValueError("Crown split-tail pin diameter/bore drifted from the parent joint")
    slot = float(tail["split_slot_width_u_mm"])
    shaft_radius = float(tail["shaft_outer_radius_after_shoulder_mm"])
    radial_thickness = shaft_radius - slot / 2.0
    if abs(radial_thickness - float(tail["conservative_arm_radial_thickness_mm"])) > EPSILON:
        raise ValueError("Crown split-tail circular-segment arm thickness drifted")
    split_union = split_q[1] - shaft_q[0]
    if abs(split_union - float(tail["split_to_unsplit_positive_union_q_mm"])) > EPSILON:
        raise ValueError("Crown split tail lacks its exact unsplit-shaft union")
    if abs(ramp_q[1] - barb_q[0]) > EPSILON or abs(barb_q[1] - float(tail["barb_front_shoulder_q_mm"])) > EPSILON:
        raise ValueError("Crown split-tail lead/barb/shoulder q stack is discontinuous")
    ear_approach = rear_ear[0] - barb_q[1]
    if abs(ear_approach - float(tail["barb_axial_catch_approach_mm"])) > EPSILON:
        raise ValueError("Crown split-tail barb lacks its 0.8 mm ear approach")
    radial_capture = float(tail["barb_expanded_outer_radius_mm"]) - hole / 2.0
    if abs(radial_capture - float(tail["barb_radial_capture_each_side_mm"])) > EPSILON:
        raise ValueError("Crown split-tail expanded barb capture drifted")
    flex_length = shaft_q[0] - barb_q[0]
    if abs(flex_length - float(tail["effective_flex_length_mm"])) > EPSILON:
        raise ValueError("Crown split-tail effective flex length is false")
    deflection = float(tail["qualification_deflection_each_arm_mm"])
    proxy_strain = 1.5 * radial_thickness * deflection / flex_length**2
    if abs(proxy_strain - float(tail["conservative_beam_proxy_strain_fraction"])) > EPSILON or proxy_strain >= 0.03:
        raise ValueError("Crown split-tail provisional strain proxy is not the frozen sub-3-percent value")
    head_union = shaft_q[1] - head_q[0]
    if abs(head_union - float(tail["shaft_to_head_positive_union_q_mm"])) > EPSILON:
        raise ValueError("Crown split-tail head lacks its exact shaft union")
    expected_saved_pin = (
        head_q[1] - split_q[0],
        float(tail["head_diameter_mm"]),
        float(tail["head_diameter_mm"]),
    )
    if any(abs(actual - expected) > EPSILON for actual, expected in zip(saved_pin, expected_saved_pin)):
        raise ValueError("Crown split-tail saved envelope does not include its full head and split shaft")
    saved_brim = tuple(float(value) for value in tail["saved_with_6_mm_brim_envelope_mm"])
    expected_saved_brim = (saved_pin[0] + 12.0, saved_pin[1] + 12.0, saved_pin[2])
    if any(abs(actual - expected) > EPSILON for actual, expected in zip(saved_brim, expected_saved_brim)):
        raise ValueError("Crown split-tail six-millimetre brim envelope drifted")
    if float(tail["compressed_release_max_outer_radius_mm"]) > hole / 2.0 + EPSILON:
        raise ValueError("Compressed crown split tail cannot pass the parent bore")
    if release_window[1][1] != rear_ear[0] or release_window[1][0] > split_q[0] + EPSILON:
        raise ValueError("Crown split-tail release window does not expose the barb from below")
    if tail["support_free_claim_allowed"] or tail["production_orientation_allowed"]:
        raise ValueError("Unqualified crown split-tail print mapping was enabled")
    return CrownBridgeContract(
        body_u, body_e, body_q, centers, envelopes, rail_q, keyway_q,
        keyway_open_e, rail_e, swept_lug_e, roof, swept_body,
        cassette_underside, body_to_cassette, u_clearance, q_clearance,
        pin_center, front_ear, rear_ear, rear_spine_q, rear_union_e,
        rear_spine_e, common_parent, worst_roof,
        pin_keyway_clearance, split_q, shaft_q, barb_q, head_q,
        release_window, saved_pin, proxy_strain,
    )


def integrated_cap_lock_contract(cfg: dict[str, Any]) -> dict[str, Any]:
    """Validate the two zero-credit underside locks in the integral corbel cap."""

    corbel = cfg["corbel"]
    lock = corbel["integrated_cap_cassette_lock"]
    cap = corbel["integrated_bearing_cap"]
    minimum = float(cfg["joinery"]["minimum_wall_mm"])
    cornerward = tuple(float(value) for value in lock["cornerward_lock_center_s_q_mm"])
    outboard = tuple(float(value) for value in lock["outboard_lock_center_s_q_mm"])
    q_centers = tuple(float(value) for value in corbel["saddle_locator_centers_from_rear_mm"])
    if (cornerward[1], outboard[1]) != q_centers or cornerward[0] != -18.9 or outboard[0] != 18.9:
        raise ValueError("Integral-cap locks do not use the exact handed s/q stations")
    shank = tuple(float(value) for value in lock["square_shank_run_q_mm"])
    cap_bore = tuple(float(value) for value in lock["cap_bore_run_q_mm"])
    tight = tuple(float(value) for value in lock["tight_cassette_receiver_run_q_mm"])
    floating = tuple(float(value) for value in lock["floating_cassette_receiver_run_q_mm"])
    pull_head = tuple(float(value) for value in lock["pull_head_run_q_mm"])
    if pull_head != (8.0, 8.0):
        raise ValueError("Cassette-lock pull head must retain its exact 8 x 8 mm service envelope")
    if any(abs(bore - shank_value - 0.4) > EPSILON for bore, shank_value in zip(cap_bore, shank)):
        raise ValueError("Cassette-lock cap bore lacks its 0.4 mm total fit")
    if tight != cap_bore or abs(floating[0] - tight[0] - float(corbel["floating_pier_lock_slot_total_axial_travel_mm"])) > EPSILON or floating[1] != tight[1]:
        raise ValueError("Floating cassette-lock receiver does not preserve 1.2 mm run travel")
    cap_base = tuple(float(value) for value in cap["base_run_envelope_at_e_128_mm"])
    run_half = cap_bore[0] / 2.0
    ligaments = (
        cornerward[0] - run_half - cap_base[0],
        cap_base[1] - (outboard[0] + run_half),
    )
    if min(ligaments) < minimum - EPSILON or abs(min(ligaments) - float(lock["minimum_cap_run_ligament_mm"])) > EPSILON:
        raise ValueError("Vertical cassette locks crowd the narrow e=128 cap base")
    tight_pocket_half = float(corbel["terminal_saddle_locator_pocket_run_width_mm"]) / 2.0
    floating_pocket_half = float(corbel["floating_pier_saddle_locator_pocket_run_width_mm"]) / 2.0
    tight_gap = abs(outboard[0]) - tight_pocket_half - tight[0] / 2.0
    floating_gap = abs(cornerward[0]) - floating_pocket_half - floating[0] / 2.0
    required_lock_gap = float(lock["minimum_lock_to_locator_pocket_run_ligament_mm"])
    if min(tight_gap, floating_gap) < required_lock_gap - EPSILON:
        raise ValueError("Cassette lock receiver crowds its locator pocket")
    if (
        "both" not in lock["run_start_terminal_receiver_policy"]
        or "tight" not in lock["run_start_terminal_receiver_policy"]
        or "previous/cornerward" not in lock["internal_support_receiver_policy"]
        or "floating" not in lock["internal_support_receiver_policy"]
        or "both" not in lock["run_end_terminal_receiver_policy"]
        or "floating" not in lock["run_end_terminal_receiver_policy"]
    ):
        raise ValueError("Per-bay cassette lock ownership is not explicit")
    cap_e = tuple(float(value) for value in lock["cap_bore_y_envelope_mm"])
    receiver_e = tuple(float(value) for value in lock["cassette_receiver_y_envelope_mm"])
    shoulder_e = tuple(float(value) for value in lock["tail_capture_shoulder_y_envelope_mm"])
    if cap_e != (128.0, 138.0) or receiver_e[0] != cap_e[1]:
        raise ValueError("Cassette-lock path is discontinuous across the cap/cassette interface")
    if receiver_e[1] - shoulder_e[1] > EPSILON or shoulder_e[1] - shoulder_e[0] < minimum - EPSILON:
        raise ValueError("Cassette lock lacks its 3.2 mm positive tail-capture shoulder")
    if lock["insertion_axis"] != "upward +e from the open underside" or float(lock["minimum_straight_underside_service_access_mm"]) < 75.0:
        raise ValueError("Cassette locks lack straight underside service access")
    if not str(lock.get("service_sweep_status", "")).startswith("GEOMETRY_CLOSED"):
        raise ValueError("Cassette-lock service sweep is not closed against the real X-corbel solids")
    if "friction alone is prohibited" not in lock["positive_keeper_rule"] or not lock["retention_credit"].startswith("zero"):
        raise ValueError("Cassette lock is not a positive zero-credit retainer")
    one = cfg["nominal_geometry_snapshot"]["nominal_part_topology"]
    two = cfg["nominal_geometry_snapshot"]["selected_two_level_part_topology"]
    if int(lock["count_per_support"]) != 2 or (int(one["cassette_locks"]), int(two["cassette_locks"])) != (22, 44):
        raise ValueError("Integral-cap cassette-lock counts are not 22/44")
    if any(int(item["sliding_saddles"]) != 0 or int(item["saddle_pins"]) != 0 for item in (one, two)):
        raise ValueError("Deleted separate saddles or saddle pins remain in topology")
    return {
        "cornerward_center_s_q_mm": list(cornerward),
        "outboard_center_s_q_mm": list(outboard),
        "tight_receiver_run_q_mm": list(tight),
        "floating_receiver_run_q_mm": list(floating),
        "pull_head_run_q_mm": list(pull_head),
        "minimum_cap_run_ligament_mm": min(ligaments),
        "straight_service_sweep_mm": float(lock["minimum_straight_underside_service_access_mm"]),
        "compressed_tail_service_sweep_collision_free": True,
        "expanded_tail_flex_coupon_required": True,
        "count_per_level": 22,
        "separate_saddles_per_level": 0,
        "separate_saddle_pins_per_level": 0,
        "retention_credit": "zero",
        "run_start_terminal_modes": ["tight", "tight"],
        "internal_support_modes": ["floating_previous", "tight_next"],
        "run_end_terminal_modes": ["floating", "floating"],
    }


def corbel_print_contract(cfg: dict[str, Any]) -> dict[str, Any]:
    """Record the real common build face and keep support claims fail-closed."""

    contract = cfg["corbel"]["print_connectivity_contract"]
    bed = tuple(float(value) for value in contract["saved_bed_envelope_with_6_mm_brim_mm"])
    height = float(contract["maximum_build_height_mm"])
    if max((*bed, height)) > 180.0 + EPSILON:
        raise ValueError("Integral-cap corbel print envelope exceeds 180 mm")
    advance = float(contract["maximum_x_path_lateral_advance_per_build_height_mm"])
    angle = float(contract["maximum_support_free_transition_angle_from_build_vertical_deg"])
    if advance > 1.0 + EPSILON or abs(angle - 36.869898) > 1.0e-6:
        raise ValueError("X paths exceed the frozen <=45-degree layer transition")
    if not contract["per_layer_connectivity_required"] or contract["detached_island_allowed"]:
        raise ValueError("Corbel print contract permits a detached per-layer island")
    if contract["support_free_claim_allowed"] or contract["production_print_mapping_allowed"]:
        raise ValueError("Unqualified spring-receiver closure is incorrectly claimed printable")
    exception = str(contract["named_exception"])
    if not all(token in exception for token in ("clevis", "locator", "lock", "coupon")):
        raise ValueError("Corbel print blockers are not tied to all exact support/coupon zones")
    return {
        "common_build_face": contract["common_build_face"],
        "bed_envelope_with_brim_mm": list(bed),
        "build_height_mm": height,
        "per_layer_mesh_gate_required": True,
        "support_free": False,
        "production_mapping_allowed": False,
        "remaining_blocker": contract["named_exception"],
    }


def rail_baseline_contract(cfg: dict[str, Any]) -> dict[str, Any]:
    """The RC deliberately omits the geometry-current 119-object stitch-rail loop."""

    structure = cfg["structure"]
    policy = structure["stitch_rail_baseline_policy"]
    one = cfg["nominal_geometry_snapshot"]["nominal_part_topology"]
    two = cfg["nominal_geometry_snapshot"]["selected_two_level_part_topology"]
    keys = ("stitch_rail_segments", "stitch_rail_overlap_joints", "stitch_rail_joint_pins", "run_end_tie_blocks")
    if policy["installed_in_release_candidate"] or int(structure["rail_lines_per_run"]) != 0:
        raise ValueError("Stitch rails are not allowed in the installed RC baseline")
    if any(int(one[key]) != 0 or int(two[key]) != 0 for key in keys):
        raise ValueError("Rail/tie objects remain in the baseline topology")
    optional = structure["optional_research_rail_interface_contract"]
    if float(optional["required_total_axial_motion_mm"]) < 1.2:
        raise ValueError("Optional rail research contract loses pier-seam travel")
    return {
        "installed": False,
        "per_level_removed": int(policy["baseline_part_count_reduction_per_level"]),
        "two_level_removed": int(policy["baseline_part_count_reduction_two_levels"]),
        "baseline_counts": {key: int(one[key]) for key in keys},
        "future_reentry_gate": policy["future_reentry_gate"],
    }


def diaphragm_retention_contract(cfg: dict[str, Any]) -> dict[str, Any]:
    """Prove gravity retention without reintroducing the deleted rail loop."""

    bowtie = cfg["joinery"]["diaphragm_bowtie"]
    retain = bowtie["positive_retention"]
    centers = tuple(float(value) for value in bowtie["centers_from_rear_mm"])
    depth = float(bowtie["depth_mm"])
    mouths = tuple((center - depth / 2.0, center + depth / 2.0) for center in centers)
    keeper_q = tuple(float(value) for value in retain["fixed_crown_keeper_q_envelope_mm"])
    rear_coverage = mouths[0][0] - keeper_q[0]
    front_coverage = keeper_q[1] - mouths[-1][1]
    required_coverage = float(retain["required_q_coverage_reserve_each_end_mm"])
    if rear_coverage < required_coverage - EPSILON or front_coverage < required_coverage - EPSILON:
        raise ValueError("Fixed-crown keeper lacks its q mouth-coverage reserve")
    if required_coverage < 0.4 - EPSILON:
        raise ValueError("Fixed-crown keeper coverage reserve is below the qualified tolerance")
    if abs(rear_coverage - float(retain["fixed_crown_rear_q_coverage_reserve_mm"])) > EPSILON or abs(front_coverage - float(retain["fixed_crown_front_q_coverage_reserve_mm"])) > EPSILON:
        raise ValueError("Configured crown-keeper reserves do not match the exact mouth envelopes")
    minimum = float(retain["minimum_plan_clearance_mm"])
    x_cradle_q_max = float(cfg["corbel"]["upper_diagonal_cassette_union_segment_mm"]["maximum_local_q_from_rear_mm"])
    x_cradle_clearance = mouths[0][0] - x_cradle_q_max
    if x_cradle_clearance < minimum - EPSILON:
        raise ValueError("First diaphragm mouth collides with the upper-X cassette cradle")
    bridge_q = tuple(float(value) for value in retain["nearest_crown_bridge_q_envelope_mm"])
    tie_q = tuple(float(value) for value in retain["nearest_fixed_front_tie_q_envelope_mm"])
    solid_front_q = keeper_q[1]
    if bridge_q[0] - solid_front_q < minimum - EPSILON or tie_q[0] - solid_front_q < minimum - EPSILON:
        raise ValueError("Fixed-crown keeper crowds the bridge or front tie")
    keeper_e = tuple(float(value) for value in retain["fixed_crown_keeper_installed_e_envelope_mm"])
    keeper_thickness = float(retain["fixed_crown_keeper_thickness_mm"])
    if abs(keeper_e[1] - keeper_e[0] - keeper_thickness) > EPSILON:
        raise ValueError("Fixed-crown keeper e envelope does not match its thickness")
    if keeper_thickness < float(cfg["joinery"]["minimum_wall_mm"]):
        raise ValueError("Fixed-crown keeper is thinner than the minimum printed wall")
    underside = float(cfg["tied_arcade"]["cassette_entablature_bottom_y_mm"])
    vertical_clearance = underside - keeper_e[1]
    if abs(vertical_clearance - float(retain["fixed_crown_vertical_clearance_mm"])) > EPSILON:
        raise ValueError("Fixed-crown keeper does not preserve its exact no-preload clearance")
    if "friction alone is prohibited" not in retain["fixed_crown_integral_anti_reverse_rule"]:
        raise ValueError("Fixed-crown keeper lacks positive anti-reverse retention")
    if not retain["fixed_crown_guide_owner"].startswith("left crown cassette only, opposite the right crown-pin ear"):
        raise ValueError("Keeper track must be left-owned and opposite the right crown-pin ear")
    if retain["fixed_crown_preload_allowed"] or float(retain["fixed_crown_vertical_clearance_mm"]) <= 0.0:
        raise ValueError("Crown keeper must retain with clearance and no preload")
    keeper_run = tuple(float(value) for value in retain["fixed_crown_keeper_run_envelope_inward_from_left_physical_face_mm"])
    if abs(keeper_run[1] - keeper_run[0] - float(retain["fixed_crown_keeper_run_width_mm"])) > EPSILON:
        raise ValueError("Keeper width disagrees with its fixed-left run envelope")
    track = retain["internal_upward_bayonet_track"]
    if retain["cassette_external_downward_guide_allowed"] or abs(float(retain["cassette_local_downward_projection_mm"])) > EPSILON:
        raise ValueError("Keeper receiver may not enlarge the 30 mm cassette below e=138")
    shank_u = tuple(float(value) for value in track["rear_tongue_shank_run_envelope_inward_from_left_physical_face_mm"])
    head_u = tuple(float(value) for value in track["rear_tongue_head_run_envelope_inward_from_left_physical_face_mm"])
    chamber_u = tuple(float(value) for value in track["rear_head_chamber_run_envelope_inward_from_left_physical_face_mm"])
    throat_u = tuple(float(value) for value in track["rear_final_shank_throat_run_envelope_inward_from_left_physical_face_mm"])
    head_fit = min(head_u[0] - chamber_u[0], chamber_u[1] - head_u[1])
    shank_fit = min(shank_u[0] - throat_u[0], throat_u[1] - shank_u[1])
    head_capture = min(throat_u[0] - head_u[0], head_u[1] - throat_u[1])
    parent_ledge = min(throat_u[0] - chamber_u[0], chamber_u[1] - throat_u[1])
    if min(chamber_u) < minimum - EPSILON:
        raise ValueError("Left-owned keeper chamber loses its seam-side wall")
    if abs(head_fit - float(track["moving_fit_clearance_each_run_side_mm"])) > EPSILON or abs(shank_fit - float(track["moving_fit_clearance_each_run_side_mm"])) > EPSILON:
        raise ValueError("Keeper rear head/shank moving fit is not 0.4 mm per run side")
    if abs(head_capture - float(track["head_capture_overlap_each_run_side_mm"])) > EPSILON or head_capture < minimum - EPSILON:
        raise ValueError("Keeper rear head lacks 3.2 mm capture per run side")
    if abs(parent_ledge - float(track["parent_capture_ledge_each_run_side_mm"])) > EPSILON or parent_ledge < minimum - EPSILON:
        raise ValueError("Keeper receiver ledges fall below the minimum wall")
    entry_head_q = tuple(float(value) for value in track["rear_tongue_entry_head_q_envelope_mm"])
    final_head_q = tuple(float(value) for value in track["rear_tongue_final_head_q_envelope_mm"])
    chamber_q = tuple(float(value) for value in track["rear_head_chamber_q_envelope_mm"])
    entry_window_q = tuple(float(value) for value in track["rear_bottom_entry_window_q_envelope_mm"])
    final_throat_q = tuple(float(value) for value in track["rear_final_shank_throat_q_envelope_mm"])
    slide = float(track["rearward_locking_slide_mm"])
    if any(abs((entry_head_q[index] - final_head_q[index]) - slide) > EPSILON for index in range(2)):
        raise ValueError("Keeper tongue entry-to-final motion is not the exact rearward slide")
    for cutter, moving, label in (
        (entry_window_q, entry_head_q, "entry"),
        (final_throat_q, final_head_q, "final"),
    ):
        if abs(moving[0] - cutter[0] - 0.4) > EPSILON or abs(cutter[1] - moving[1] - 0.4) > EPSILON:
            raise ValueError(f"Keeper rear tongue {label} q fit is not 0.4 mm")
    if chamber_q != (final_throat_q[0], entry_window_q[1]):
        raise ValueError("Keeper rear head chamber does not contain the complete 4 mm slide")
    q_ledge = entry_window_q[0] - final_head_q[0]
    if abs(q_ledge - float(track["final_head_q_ledge_coverage_mm"])) > EPSILON:
        raise ValueError("Keeper final head lacks its exact q ledge coverage")
    track_clearances = (chamber_q[0] - mouths[0][1], mouths[1][0] - chamber_q[1])
    if min(track_clearances) < minimum - EPSILON or abs(min(track_clearances) - float(track["minimum_q_ligament_to_adjacent_diaphragm_mouth_mm"])) > EPSILON:
        raise ValueError("Internal keeper track crowds a diaphragm mouth")
    shank_e = tuple(float(value) for value in track["rear_tongue_shank_y_envelope_mm"])
    head_e = tuple(float(value) for value in track["rear_tongue_head_y_envelope_mm"])
    chamber_e = tuple(float(value) for value in track["rear_head_chamber_y_envelope_mm"])
    throat_e = tuple(float(value) for value in track["rear_bottom_entry_and_final_throat_y_envelope_mm"])
    roof_e = tuple(float(value) for value in track["capture_roof_y_envelope_mm"])
    if abs(keeper_e[1] - shank_e[0] - float(track["tongue_to_keeper_strip_positive_union_mm"])) > EPSILON:
        raise ValueError("Keeper rear tongue has no positive-volume strip union")
    if abs(shank_e[1] - head_e[0] - 0.4) > EPSILON:
        raise ValueError("Keeper rear shank/head union is not positive")
    if head_e[0] != chamber_e[0] or abs(chamber_e[1] - head_e[1] - 0.4) > EPSILON:
        raise ValueError("Keeper rear head lacks its exact vertical chamber fit")
    if throat_e[1] != chamber_e[0] or roof_e[0] != chamber_e[1] or abs(roof_e[1] - roof_e[0] - minimum) > EPSILON:
        raise ValueError("Keeper internal receiver loses its throat/chamber/roof stack")
    approach_delta = float(track["clear_approach_translation_y_mm"])
    approach_head = tuple(float(value) for value in track["clear_approach_head_y_envelope_mm"])
    if any(abs(approach_head[index] - (head_e[index] + approach_delta)) > EPSILON for index in range(2)):
        raise ValueError("Keeper clear-approach head envelope is not its rigid lift transform")
    if abs(underside - approach_head[1] - float(track["clear_approach_to_cassette_vertical_gap_mm"])) > EPSILON:
        raise ValueError("Keeper rear head lacks 0.4 mm clear approach below the cassette")
    if track["support_free_claim_allowed"] or track["production_orientation_allowed"]:
        raise ValueError("Unqualified keeper tongue print mapping was enabled")
    shelf_depth = float(cfg["closet"]["shelf_depth_in"]) * 25.4
    internal_path = shelf_depth - float(retain["fixed_crown_front_access_q_mm"])
    if abs(internal_path - float(retain["fixed_crown_internal_front_service_path_mm"])) > EPSILON:
        raise ValueError("Keeper internal front service path is inconsistent")
    if float(retain["minimum_external_straight_service_path_mm"]) < 75.0:
        raise ValueError("Keeper pull feature lacks the required external service path")
    if retain["assembly_sequence"] != ["diaphragm keys", "keeper strip", "fixed front crown tie", "arch halves", "crown bridge"]:
        raise ValueError("Crown interface assembly order is not explicit and collision-free")
    if "12.0 mm" not in retain["floating_pier_trap_rule"] or "1.2 mm" not in retain["floating_pier_trap_rule"]:
        raise ValueError("Floating pier trap does not preserve the full axial travel")
    saddle_thermal_contract(cfg)
    one = cfg["nominal_geometry_snapshot"]["nominal_part_topology"]
    two = cfg["nominal_geometry_snapshot"]["selected_two_level_part_topology"]
    if int(one["fixed_crown_diaphragm_keeper_strips"]) != 9 or int(two["fixed_crown_diaphragm_keeper_strips"]) != 18:
        raise ValueError("Crown keeper physical-object counts are not exact")
    front = cfg["joinery"]["front_entablature_joint"]["fixed_crown_tie_key"]
    receiver_q = tuple(float(value) for value in front["front_open_receiver_q_envelope_mm"])
    key_q = tuple(float(value) for value in front["key_q_envelope_at_hard_stop_mm"])
    if receiver_q[1] != 152.4 or key_q[1] != 152.4 or key_q[0] < receiver_q[0]:
        raise ValueError("Fixed crown tie is not a valid visible-front insertion")
    if abs(float(front["bridge_clearance_mm"]) - (key_q[0] - float(front["crown_bridge_body_ends_q_mm"]))) > EPSILON:
        raise ValueError("Fixed crown tie hard stop loses bridge clearance")
    receiver_e = tuple(float(value) for value in front["receiver_y_envelope_mm"])
    key_e = tuple(float(value) for value in front["key_y_envelope_at_hard_stop_mm"])
    vertical_face_fit = float(front["vertical_clearance_per_face_mm"])
    if abs(key_e[0] - receiver_e[0] - vertical_face_fit) > EPSILON or abs(receiver_e[1] - key_e[1] - vertical_face_fit) > EPSILON:
        raise ValueError("Fixed front tie lacks its exact vertical fit clearance")
    true_bridge_clearance = receiver_e[0] - float(front["nearest_bridge_keyway_roof_y_max_mm"])
    if true_bridge_clearance < float(front["minimum_true_3d_bridge_clearance_mm"]) - EPSILON or abs(true_bridge_clearance - float(front["actual_true_3d_bridge_clearance_mm"])) > EPSILON:
        raise ValueError("Fixed front tie and crown keyway lack true 3D separation")
    if float(front["nearest_top_receiver_run_clearance_mm"]) < minimum - EPSILON:
        raise ValueError("Fixed crown tie crowds a top receiver")
    if "incidental arch contact is prohibited" not in front["positive_catch_rule"] or front["preload_allowed"]:
        raise ValueError("Fixed crown tie lacks an independent positive catch")
    totals = cfg["nominal_geometry_snapshot"]["baseline_complete_physical_object_counts"]
    expected_per_level = (
        int(totals["structural_and_joinery_per_level"])
        + int(totals["removable_ornament_per_level"])
    )
    if (
        int(totals["complete_per_level"]) != expected_per_level
        or int(totals["complete_selected_two_levels"]) != 2 * expected_per_level
    ):
        raise ValueError("Integral-cap rail-free baseline totals do not reconcile")
    return {
        "mouth_q_envelopes_mm": [[round(value, 7) for value in item] for item in mouths],
        "keeper_q_envelope_mm": list(keeper_q),
        "keeper_q_coverage_reserve_mm": min(rear_coverage, front_coverage),
        "keeper_vertical_clearance_mm": vertical_clearance,
        "keeper_run_envelope_inward_from_left_physical_face_mm": list(keeper_run),
        "bridge_clearance_mm": bridge_q[0] - solid_front_q,
        "front_tie_clearance_mm": tie_q[0] - solid_front_q,
        "x_cradle_to_first_mouth_clearance_mm": x_cradle_clearance,
        "internal_front_service_path_mm": internal_path,
        "per_level_keeper_count": 9,
        "two_level_keeper_count": 18,
        "pier_keeper_objects": 0,
        "pier_trap_total_axial_travel_mm": 1.2,
        "fixed_front_tie_q_envelope_mm": list(key_q),
        "fixed_front_tie_e_envelope_mm": list(key_e),
        "front_tie_to_bridge_vertical_clearance_mm": true_bridge_clearance,
        "minimum_internal_track_q_ligament_mm": min(track_clearances),
        "complete_objects_per_level": int(totals["complete_per_level"]),
        "complete_objects_two_levels": int(totals["complete_selected_two_levels"]),
    }


def ornament_interface_contract(cfg: dict[str, Any]) -> OrnamentInterfaceContract:
    """Validate visual seams and zero-credit, orientation-qualified keyholes."""

    arcade = cfg["tied_arcade"]
    palatine = cfg["palatine"]
    visual = palatine["visual_carrier_contract"]
    keyholes = palatine["ornament_keyhole_contract"]
    isolation = cfg["ornament_isolation"]
    crown = float(visual["visual_crown_extrados_y_mm"])
    spring = float(visual["visual_spring_extrados_y_mm"])
    rise = float(visual["visual_arch_rise_mm"])
    if abs(crown - spring - rise) > EPSILON or abs(float(visual["visual_carrier_height_mm"]) - (168.0 - spring)) > EPSILON:
        raise ValueError("Visual facade spring/crown/rise is not the independent 60/152/92 geometry")
    if abs(crown - float(arcade["visual_facade_crown_extrados_y_mm"])) > EPSILON or abs(spring - float(arcade["visual_facade_spring_extrados_y_mm"])) > EPSILON:
        raise ValueError("Palatine and tied-arcade visual geometry disagree")
    seam = float(visual["visual_seam_mm"])
    inset = float(visual["inset_each_nominal_end_mm"])
    if abs(seam - 2.0 * inset) > EPSILON:
        raise ValueError("Visual seam must be two centered end insets")
    through_width = float(visual["through_physical_carrier_width_mm"])
    return_width = float(visual["return_physical_carrier_width_mm"])
    if abs(through_width - (float(visual["through_nominal_half_span_mm"]) - seam)) > EPSILON or abs(return_width - (float(visual["return_nominal_half_span_mm"]) - seam)) > EPSILON:
        raise ValueError("Carrier widths do not reserve the 0.6 mm visual seam")
    fixed = 1
    elongated = len(keyholes["elongated_run_axis_connector_indices"])
    if int(keyholes["connectors_per_carrier"]) != fixed + elongated or int(keyholes["fixed_connector_index"]) in keyholes["elongated_run_axis_connector_indices"]:
        raise ValueError("Each carrier must have one fixed and two elongated keyholes")
    boss_head = tuple(float(value) for value in keyholes["boss_head_run_y_mm"])
    receiver_head = tuple(float(value) for value in keyholes["receiver_head_run_y_mm"])
    clearance = float(keyholes["clearance_per_face_mm"])
    if any(abs(receiver - boss - 2.0 * clearance) > EPSILON for boss, receiver in zip(boss_head, receiver_head)):
        raise ValueError("Ornament head receiver does not preserve per-face clearance")
    travel = float(keyholes["elongated_total_run_travel_mm"])
    if abs(float(keyholes["elongated_receiver_head_run_mm"]) - (receiver_head[0] + travel)) > EPSILON:
        raise ValueError("Elongated ornament head receiver omits the full run travel")
    if abs(float(keyholes["elongated_receiver_neck_run_mm"]) - (float(keyholes["receiver_neck_run_mm"]) + travel)) > EPSILON:
        raise ValueError("Elongated ornament neck receiver omits the full run travel")
    overlap = float(keyholes["parent_union_overlap_mm"])
    if abs(overlap - 0.02) > EPSILON or "actual-parent" not in keyholes["coupon_gate"]:
        raise ValueError("Ornament boss must use only the 0.02 mm parent union and actual-orientation coupon")
    no_go = tuple(float(value) for value in isolation["unloaded_no_go_gap_depth_zone_mm"])
    structure = tuple(float(value) for value in isolation["structural_chassis_depth_zone_mm"])
    if abs(no_go[1] - structure[0]) > EPSILON or float(isolation["minimum_unloaded_clearance_from_structure_mm"]) < 3.0:
        raise ValueError("Ornament-to-structure isolation is less than 3 mm")
    if keyholes["structural_credit"]:
        raise ValueError("Removable ornament connectors may receive no structural credit")
    datum = keyholes["coordinate_contract"]
    parent_z = tuple(float(value) for value in datum["structural_parent_source_z_envelope_mm"])
    offset = float(datum["structural_parent_front_global_d_mm"])
    parent_d = tuple(float(value) for value in datum["structural_parent_global_d_envelope_mm"])
    if parent_z != (0.0, 18.0) or any(abs(actual - (offset + local)) > EPSILON for actual, local in zip(parent_d, parent_z)):
        raise ValueError("Ornament global d datum does not map the unchanged structural source z")
    if datum["structural_parent_translation_for_ornament_allowed"]:
        raise ValueError("Ornament datum may not translate the structural parent")
    spring_z = float(datum["spring_tenon_source_z_center_mm"])
    spring_q = float(datum["spring_tenon_installed_q_center_mm"])
    shelf_depth = float(cfg["closet"]["shelf_depth_in"]) * 25.4
    if abs(shelf_depth - spring_z - spring_q) > EPSILON or abs(offset + shelf_depth - 165.6) > EPSILON:
        raise ValueError("Ornament d/q datum breaks the structural spring alignment")
    boss_neck_d = tuple(float(value) for value in keyholes["boss_neck_depth_zone_mm"])
    parent_overlap_z = tuple(float(value) for value in datum["boss_parent_overlap_local_z_envelope_mm"])
    if parent_overlap_z != (0.0, overlap) or abs(boss_neck_d[1] - offset - overlap) > EPSILON:
        raise ValueError("Sacrificial boss overlap is not exactly 0.02 mm in parent-local z")
    boss_local_z = tuple(float(value) for value in isolation["integral_boss_parent_local_z_envelope_mm"])
    if boss_local_z != (-7.2, overlap):
        raise ValueError("Integral ornament boss does not span the exact -7.2..+0.02 parent-local depth")
    neck = tuple(float(value) for value in keyholes["boss_neck_run_y_mm"])
    union_volume = neck[0] * neck[1] * overlap
    if abs(union_volume - float(isolation["minimum_boss_neck_parent_union_volume_mm3"])) > EPSILON:
        raise ValueError("Configured ornament-boss union volume does not match its exact neck overlap")
    required_families = tuple(str(value) for value in keyholes["required_ornament_family_boss_maps"])
    mapping = keyholes["per_parent_boss_placement_map"]
    mapping_complete = isinstance(mapping, dict) and set(mapping) == set(required_families)
    if len(required_families) != 8 or len(set(required_families)) != 8:
        raise ValueError("Ornament attachment contract must enumerate exactly eight installed families")
    if not mapping_complete and keyholes["installed_interface_complete"]:
        raise ValueError("Ornament connector release is claimed without eight exact parent maps")
    if mapping_complete != bool(keyholes["installed_interface_complete"]):
        raise ValueError("Ornament installed-interface status disagrees with its parent map")
    if not mapping_complete:
        family_keys: tuple[str, ...] = ()
    else:
        family_keys = tuple(sorted(mapping))
        expected_counts = {
            "through_carrier_left": 6,
            "through_carrier_right": 6,
            "return_carrier_left": 3,
            "return_carrier_right": 3,
            "pier_overlay": 11,
            "ordinary_endcap": 2,
            "corner_fixed_rosette": 1,
            "corner_floating_return": 1,
        }
        if {
            family: int(mapping[family]["installed_count_per_level"])
            for family in family_keys
        } != dict(sorted(expected_counts.items())):
            raise ValueError("Ornament parent-map repeat counts do not equal the 33-piece facade")
        for family in family_keys:
            centers = mapping[family]["carrier_local_receiver_centers_x_y_mm"]
            if len(centers) != 3 or len({tuple(float(value) for value in center) for center in centers}) != 3:
                raise ValueError(f"{family}: parent map needs three unique receiver centers")
            if "same" not in str(mapping[family]["parent_ownership"]).lower() and family not in {
                "pier_overlay",
                "corner_fixed_rosette",
                "corner_floating_return",
            }:
                raise ValueError(f"{family}: ornament ownership is not restricted to one parent")
            if "actual_parent_coupon" not in mapping[family] or "orientation" not in str(mapping[family]["actual_parent_coupon"]):
                raise ValueError(f"{family}: actual-parent-orientation coupon is absent")

        from ornament_access import (
            derived_carrier_receiver_centers,
            ornament_access_contract,
        )

        carrier_families = (
            "through_carrier_left",
            "through_carrier_right",
            "return_carrier_left",
            "return_carrier_right",
        )
        for family in carrier_families:
            expected_centers = [
                list(center)
                for center in derived_carrier_receiver_centers(cfg, family)
            ]
            if mapping[family]["carrier_local_receiver_centers_x_y_mm"] != expected_centers:
                raise ValueError(
                    f"{family}: physical-local receiver map no longer derives from its parent bosses"
                )

        pier = mapping["pier_overlay"]
        if pier["carrier_local_receiver_centers_x_y_mm"] != [[8.8, 9.4], [25.6, 9.4], [17.2, 26.8]]:
            raise ValueError("Pier two-keyhole/one-locator receiver map drift")
        if pier["attachment_feature_types"] != ["compact_gravity_keyhole", "compact_gravity_keyhole", "noncapturing_loose_locator"]:
            raise ValueError("Pier overlay must retain two gravity keyholes and one loose locator")
        if pier["parent_interface_plate_run_e_source_z_envelopes_mm"] != [[-17.2, 17.2], [0.0, 60.0], [0.0, 1.6]]:
            raise ValueError("Pier ornament interface plate envelope drift")
        spring_joint = arcade["spring_final_x_vertical_joint"]
        shoulder_z = tuple(float(value) for value in spring_joint["hard_stop_shoulder_source_z_envelope_mm"])
        transition_z = tuple(float(value) for value in spring_joint["below_housing_transition_source_z_envelope_mm"])
        plate_z = tuple(float(value) for value in spring_joint["ornament_interface_plate_source_z_envelope_mm"])
        arch_clearance = shoulder_z[0] - plate_z[1]
        if shoulder_z != (2.0, 18.0) or transition_z != shoulder_z or plate_z != (0.0, 1.6):
            raise ValueError("Pier plate and moving spring shoulder do not use the frozen depth bands")
        if abs(arch_clearance - 0.4) > EPSILON or abs(arch_clearance - float(pier["moving_arch_clearance_mm"])) > EPSILON:
            raise ValueError("Pier ornament plate lacks 0.4 mm moving-arch clearance")

        overhang = keyholes["overhang_finish_contract"]
        standard_width = float(overhang["standard_physical_finish_width_mm"])
        standard_inset = float(overhang["standard_terminal_pier_inset_mm"])
        return_inset = float(overhang["return_corner_terminal_pier_inset_mm"])
        return_parent_width = float(overhang["return_corner_parent_panel_width_mm"])
        cantilever = float(overhang["return_corner_cosmetic_cantilever_back_mm"])
        if (
            abs(standard_width - (standard_inset - seam)) > EPSILON
            or abs(standard_width - 30.8325) > EPSILON
            or abs(return_parent_width - (return_inset - seam)) > EPSILON
            or abs(return_parent_width - 26.4325) > EPSILON
            or abs(cantilever - 4.4) > EPSILON
        ):
            raise ValueError("Terminal ornament widths no longer derive from their exact asymmetric insets")
        for family in ("ordinary_endcap", "corner_fixed_rosette"):
            if abs(float(mapping[family]["physical_width_height_mm"][0]) - standard_width) > EPSILON:
                raise ValueError(f"{family}: standard overhang width drift")

        floating = mapping["corner_floating_return"]
        source_solid = tuple(float(value) for value in floating["source_solid_x_envelope_mm"])
        visible_base = tuple(float(value) for value in floating["visible_base_x_envelope_mm"])
        piece_origin = float(floating["piece_run_start_mm"])
        panel_run = tuple(float(value) for value in floating["parent_panel_run_envelope_mm"])
        if (
            source_solid != (0.0, 31.1325)
            or visible_base != (0.8, 31.1325)
            or abs(piece_origin + cantilever) > EPSILON
            or panel_run != (0.3, 26.7325)
            or abs(panel_run[1] - panel_run[0] - return_parent_width) > EPSILON
            or abs(float(floating["parent_panel_width_mm"]) - return_parent_width) > EPSILON
            or tuple(float(value) for value in floating["physical_width_height_mm"]) != (31.1325, 60.0)
        ):
            raise ValueError("Floating return-corner finish no longer preserves its offset source/panel envelopes")
        piece_centers = [
            tuple(float(value) for value in center)
            for center in floating["locked_boss_centers_piece_local_x_e_mm"]
        ]
        panel_centers = [
            tuple(float(value) for value in center)
            for center in floating["locked_boss_centers_parent_panel_local_x_e_mm"]
        ]
        installed_centers = [
            tuple(float(value) for value in center)
            for center in floating["locked_boss_centers_run_s_e_mm"]
        ]
        if not (
            len(piece_centers) == len(panel_centers) == len(installed_centers) == 3
        ):
            raise ValueError("Floating return-corner finish needs three boss datums in every coordinate system")
        for piece, panel, installed in zip(piece_centers, panel_centers, installed_centers):
            if (
                abs(piece_origin + piece[0] - installed[0]) > EPSILON
                or abs(panel_run[0] + panel[0] - installed[0]) > EPSILON
                or abs(piece[1] - installed[1]) > EPSILON
                or abs(panel[1] - installed[1]) > EPSILON
            ):
                raise ValueError("Floating return-corner boss piece/panel/run datums disagree")
        installed_solid = (piece_origin + source_solid[0], piece_origin + source_solid[1])
        installed_visible = (piece_origin + visible_base[0], piece_origin + visible_base[1])
        adjacent_carrier_start = return_inset + float(visual["inset_each_nominal_end_mm"])
        if (
            any(
                abs(actual - expected) > EPSILON
                for actual, expected in zip(installed_solid, (-4.4, 26.7325))
            )
            or any(
                abs(actual - expected) > EPSILON
                for actual, expected in zip(installed_visible, (-3.6, 26.7325))
            )
            or abs(adjacent_carrier_start - installed_solid[1] - seam) > EPSILON
        ):
            raise ValueError("Floating return-corner cantilever loses its locked leading edge or trailing seam")

        boss_count = sum(expected_counts.values()) * int(keyholes["boss_count_per_installed_piece"])
        if boss_count != 99 or boss_count != int(keyholes["boss_count_per_level"]) or boss_count != int(isolation["parent_boss_feature_count_per_level"]):
            raise ValueError("Ornament parent-boss feature count must remain 99 per level")
        sweep = keyholes["strict_collision_gate"]
        if abs(float(sweep["axial_insertion_sweep_step_mm"]) - 0.4) > EPSILON or abs(float(sweep["axial_insertion_sweep_total_mm"]) - 4.4) > EPSILON:
            raise ValueError("Ornament strict collision sweep must sample the full axial insertion every 0.4 mm")
        if abs(float(sweep["gravity_sweep_step_mm"]) - 0.4) > EPSILON or abs(float(sweep["gravity_sweep_total_mm"]) - 6.0) > EPSILON:
            raise ValueError("Ornament strict collision sweep must sample the full drop every 0.4 mm")
        if tuple(float(value) for value in sweep["elongated_receiver_extremes_mm"]) != (-0.6, 0.6):
            raise ValueError("Ornament strict collision sweep omits the two run-travel extremes")
        # The access helper independently proves that all 54 structural keys
        # remain visible through true d=0..10.2 swept oculi and that the
        # repacked attachment housings retain their minimum planar separation.
        ornament_access_contract(cfg)
    boss_count = int(keyholes["boss_count_per_level"])
    sweep_step = float(keyholes["strict_collision_gate"]["gravity_sweep_step_mm"])
    if not bool(keyholes["software_model_mapping_contract_required"]):
        raise ValueError("Ornament source omits the software model-mapping contract")
    if bool(keyholes["physical_installation_mapping_qualified"]):
        raise ValueError("Ornament source claims unperformed physical qualification")
    if bool(keyholes["production_release_eligible"]):
        raise ValueError("Ornament source claims unearned production eligibility")
    return OrnamentInterfaceContract(
        crown, spring, rise, seam, through_width, return_width, fixed,
        elongated, travel, overlap, offset, boss_count, union_volume,
        sweep_step, family_keys, mapping_complete,
        True, False, False,
    )


def required_field_corner_gap_mm(cfg: dict[str, Any]) -> float:
    corner = cfg["closet"]["inside_corner"]
    ornament = cfg["palatine"]["ornament_keyhole_contract"]
    parent_front_d = float(
        ornament["coordinate_contract"]["structural_parent_front_global_d_mm"]
    )
    actual_visible_depth = (
        float(cfg["closet"]["shelf_depth_in"]) * 25.4
        + parent_front_d
    )
    missing = [
        key
        for key in (
            "field_verified_angle_deg",
            "field_verified_max_wall_bow_mm",
            "field_verified_corner_datum_uncertainty_mm",
        )
        if corner.get(key) is None
    ]
    if missing:
        raise ValueError(f"Field corner gap is blocked until measured: {', '.join(missing)}")
    error = abs(float(corner["field_verified_angle_deg"]) - 90.0)
    maximum = float(corner["maximum_square_corner_deviation_deg"])
    if error > maximum + EPSILON:
        raise ValueError("Measured corner is outside the square-footprint angle gate")
    return required_corner_gap_mm(
        depth_mm=actual_visible_depth,
        measured_angle_deg=float(corner["field_verified_angle_deg"]),
        minimum_gap_mm=float(
            corner["minimum_residual_visible_joint_clearance_mm"]
        ),
        wall_bow_mm=float(corner["field_verified_max_wall_bow_mm"]),
        datum_uncertainty_mm=float(corner["field_verified_corner_datum_uncertainty_mm"]),
        manufacturing_installation_reserve_mm=float(
            corner["minimum_production_manufacturing_installation_reserve_mm"]
        ),
    )


def physical_crown_face_shift_mm(cfg: dict[str, Any]) -> float:
    return float(cfg["structure"]["cassette_between_module_seam_mm"]) / 2.0


def top_feature_x_from_spring_mm(
    cfg: dict[str, Any], *, nominal_half_span_mm: float, u_from_physical_crown_mm: float
) -> float:
    """Place a top feature from the physical—not nominal—crown face."""

    return (
        float(nominal_half_span_mm)
        - physical_crown_face_shift_mm(cfg)
        - float(u_from_physical_crown_mm)
    )


def arch_saved_to_run_matrix(
    *,
    spring_s_mm: float,
    handedness: str,
    shelf_depth_mm: float,
    saved_y_min_installed_mm: float,
) -> np.ndarray:
    """Map a normalized arch STL into run coordinates ``(s,q,e)``."""

    if handedness not in {"left", "right"}:
        raise ValueError("handedness must be left or right")
    sign = 1.0 if handedness == "left" else -1.0
    return np.asarray(
        [
            [sign, 0.0, 0.0, float(spring_s_mm)],
            [0.0, 0.0, -1.0, float(shelf_depth_mm)],
            [0.0, 1.0, 0.0, float(saved_y_min_installed_mm)],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def cassette_saved_to_run_matrix(
    *,
    physical_start_s_mm: float,
    shelf_depth_mm: float,
    cassette_height_mm: float,
    cassette_underside_e_mm: float,
) -> np.ndarray:
    """Map the top-skin-down cassette STL into run coordinates ``(s,q,e)``."""

    return np.asarray(
        [
            [1.0, 0.0, 0.0, float(physical_start_s_mm)],
            [0.0, -1.0, 0.0, float(shelf_depth_mm)],
            [0.0, 0.0, -1.0, float(cassette_underside_e_mm + cassette_height_mm)],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def run_to_world_matrix(
    *,
    run_role: str,
    run_start_from_corner_mm: float,
    back_clearance_mm: float,
    level_top_world_mm: float,
    total_height_mm: float,
) -> np.ndarray:
    """Map run coordinates into the common inside-corner world datum."""

    z_offset = float(level_top_world_mm) - float(total_height_mm)
    if run_role == "through":
        rows = [
            [1.0, 0.0, 0.0, float(run_start_from_corner_mm)],
            [0.0, 1.0, 0.0, float(back_clearance_mm)],
            [0.0, 0.0, 1.0, z_offset],
            [0.0, 0.0, 0.0, 1.0],
        ]
    elif run_role == "return":
        rows = [
            [0.0, 1.0, 0.0, float(back_clearance_mm)],
            [1.0, 0.0, 0.0, float(run_start_from_corner_mm)],
            [0.0, 0.0, 1.0, z_offset],
            [0.0, 0.0, 0.0, 1.0],
        ]
    else:
        raise ValueError("run_role must be through or return")
    return np.asarray(rows, dtype=float)
