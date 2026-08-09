#!/usr/bin/env python3
"""Pure analytic contract for the r6 visible-front positive retention key.

The generator owns meshes.  This module owns the dimensions and fail-closed
proofs that make a quarter-turn key mechanically positive rather than a loose
friction wedge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any


EPSILON = 1.0e-7


@dataclass(frozen=True)
class PositiveCrossKeyContract:
    family_id: str
    shaft_diameter_mm: float
    bore_diameter_mm: float
    shaft_radial_clearance_mm: float
    top_tenon_ligament_run_y_mm: tuple[float, float]
    spring_tenon_ligament_run_y_mm: tuple[float, float]
    entry_clearance_run_y_mm: tuple[float, float]
    crossbar_corner_sweep_radius_mm: float
    chamber_radial_sweep_clearance_mm: float
    boss_minimum_outer_wall_mm: float
    locked_index_notch_residual_wall_mm: float
    gate_capture_overlap_each_lug_mm: float
    chamber_axial_clearance_mm: float
    maximum_installed_outward_float_mm: float
    minimum_latch_engagement_at_outward_float_mm: float
    release_clearance_mm: float
    conservative_flexure_strain_length_mm: float
    authored_folded_u_centerline_segments_mm: tuple[float, float, float]
    authored_folded_u_centerline_length_mm: float
    nominal_flexure_outer_fiber_strain: float
    minimum_external_service_access_mm: float
    exact_insertion_translation_mm: float
    exact_locking_rotation_deg: float
    saved_bare_envelope_mm: tuple[float, float, float]
    saved_brim_envelope_mm: tuple[float, float, float]
    keys_per_level: int
    keys_selected_two_levels: int
    load_credit: str
    kinematic_stage_matrices: dict[str, tuple[tuple[float, ...], ...]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _span(envelope: list[float] | tuple[float, float], label: str) -> float:
    low, high = (float(value) for value in envelope)
    if high <= low:
        raise ValueError(f"{label} is not an increasing envelope")
    return high - low


def _require_close(actual: float, expected: float, label: str) -> None:
    if abs(actual - expected) > EPSILON:
        raise ValueError(f"{label}: {actual:.9f} != {expected:.9f}")


def key_transform_q(rotation_deg: float, translation_q_mm: float = 0.0) -> tuple[tuple[float, ...], ...]:
    """Return the exact installed-coordinate transform about the q axis.

    Coordinates are ordered ``(u, y, q, 1)``.  Positive rotation is the
    configured clockwise motion as viewed from the visible front.
    """

    angle = math.radians(float(rotation_deg))
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return (
        (cosine, -sine, 0.0, 0.0),
        (sine, cosine, 0.0, 0.0),
        (0.0, 0.0, 1.0, float(translation_q_mm)),
        (0.0, 0.0, 0.0, 1.0),
    )


def crossbar_corners_at_rotation(
    long_span_mm: float,
    short_span_mm: float,
    rotation_deg: float,
) -> tuple[tuple[float, float], ...]:
    """Return all four exact u/y corners during the quarter-turn.

    At zero degrees the long crossbar axis is vertical.  This helper is useful
    to the mesh-level swept-solid gate without importing a geometry kernel.
    """

    half_short = float(short_span_mm) / 2.0
    half_long = float(long_span_mm) / 2.0
    angle = math.radians(float(rotation_deg))
    cosine = math.cos(angle)
    sine = math.sin(angle)
    corners: list[tuple[float, float]] = []
    for u_entry in (-half_short, half_short):
        for y_entry in (-half_long, half_long):
            corners.append(
                (
                    cosine * u_entry - sine * y_entry,
                    sine * u_entry + cosine * y_entry,
                )
            )
    return tuple(corners)


def positive_retention_cross_key_contract(cfg: dict[str, Any]) -> PositiveCrossKeyContract:
    """Validate and report the complete positive cross-key interface."""

    arcade = cfg["tied_arcade"]
    key = arcade["retention_wedge"]
    if key["family_id"] != "positive_quarter_turn_cross_key":
        raise ValueError("Universal retention family is not the positive quarter-turn cross-key")
    if key["legacy_straight_wedge_allowed"]:
        raise ValueError("A loose straight retention wedge is explicitly prohibited")
    if "captive-bayonet" not in key["mechanism"] or "positively indexed" not in key["mechanism"]:
        raise ValueError("Cross-key mechanism lacks captive bayonet geometry or a positive index")

    minimum_wall = float(cfg["joinery"]["minimum_wall_mm"])
    nominal_fit = float(cfg["joinery"]["nominal_fit_clearance_mm"])
    bore = float(key["tenon_through_bore_diameter_mm"])
    hole_u, hole_y = (float(value) for value in key["through_hole_run_y_mm"])
    _require_close(hole_u, bore, "through-hole run bound")
    _require_close(hole_y, bore, "through-hole vertical bound")
    shaft = float(key["shaft_diameter_mm"])
    nominal_shank = tuple(float(value) for value in key["nominal_shank_run_y_mm"])
    if nominal_shank != (shaft, shaft) or key["through_hole_shape"] != "circular cutter through both receiver cheeks and the captured tenon":
        raise ValueError("Shaft and circular through-bore declarations disagree")
    shaft_radial_clearance = (bore - shaft) / 2.0
    if shaft_radial_clearance < nominal_fit - EPSILON:
        raise ValueError("Cross-key shaft lacks the nominal PETG radial fit clearance")

    def tenon_ligaments(joint: dict[str, Any], label: str) -> tuple[float, float]:
        run = (float(joint["tenon_run_width_mm"]) - bore) / 2.0
        vertical = (float(joint["tenon_engagement_height_mm"]) - bore) / 2.0
        if run < 7.0 - EPSILON or vertical < 7.0 - EPSILON:
            raise ValueError(f"{label} cross-key bore reduces a tenon ligament below 7 mm")
        _require_close(run, float(joint["minimum_tenon_clear_ligament_run_mm"]), f"{label} run ligament")
        _require_close(vertical, float(joint["minimum_tenon_clear_ligament_y_mm"]), f"{label} vertical ligament")
        return (run, vertical)

    top = arcade["cassette_final_x_vertical_tenon_joint"]
    spring = arcade["spring_final_x_vertical_joint"]
    top_ligaments = tenon_ligaments(top, "cassette-top")
    spring_ligaments = tenon_ligaments(spring, "spring")
    for label, joint in (("cassette-top", top), ("spring", spring)):
        stack = 2.0 * float(joint["receiver_front_and_rear_cheek_each_mm"]) + float(joint["receiver_depth_mm"])
        _require_close(stack, float(arcade["chassis_depth_mm"]), f"{label} receiver depth stack")

    receiver_q = tuple(float(value) for value in key["receiver_primary_q_envelope_mm"])
    _require_close(_span(receiver_q, "primary receiver q"), float(arcade["chassis_depth_mm"]), "primary receiver q depth")
    shaft_q = tuple(float(value) for value in key["shaft_installed_q_envelope_mm"])
    rear_tip_clearance = receiver_q[1] - shaft_q[1]
    _require_close(rear_tip_clearance, float(key["rear_tip_clearance_mm"]), "rear-tip clearance")
    if shaft_q[1] > receiver_q[1] + float(key["maximum_rear_tip_protrusion_mm"]) + EPSILON:
        raise ValueError("Cross-key protrudes beyond the rear receiver face")

    boss = key["front_bayonet_boss"]
    crossbar = key["crossbar"]
    outer_u, outer_y = (float(value) for value in boss["outer_run_y_mm"])
    gate_thickness = _span(boss["front_gate_q_envelope_mm"], "front gate q")
    _require_close(gate_thickness, float(boss["front_gate_thickness_mm"]), "front gate thickness")
    if gate_thickness < minimum_wall - EPSILON:
        raise ValueError("Front bayonet gate is below the minimum printed wall")
    union_overlap = _span(boss["parent_positive_union_overlap_q_mm"], "boss parent overlap")
    if union_overlap < nominal_fit - EPSILON:
        raise ValueError("Front bayonet boss lacks a robust positive-volume parent union")

    slot_u, slot_y = (float(value) for value in boss["vertical_entry_slot_run_y_mm"])
    cross_long = float(crossbar["actual_long_span_mm"])
    cross_short = float(crossbar["actual_short_span_mm"])
    entry_clearances = ((slot_u - cross_short) / 2.0, (slot_y - cross_long) / 2.0)
    if min(entry_clearances) < nominal_fit - EPSILON:
        raise ValueError("Vertical crossbar entry sweep lacks nominal clearance")

    chamber_depth = _span(boss["rotation_chamber_q_envelope_mm"], "rotation chamber q")
    _require_close(chamber_depth, float(boss["rotation_chamber_depth_mm"]), "rotation chamber depth")
    crossbar_q = tuple(float(value) for value in crossbar["installed_q_envelope_mm"])
    crossbar_axial = _span(crossbar_q, "crossbar q")
    _require_close(crossbar_axial, float(crossbar["actual_axial_thickness_mm"]), "crossbar axial thickness")
    chamber_q = tuple(float(value) for value in boss["rotation_chamber_q_envelope_mm"])
    front_axial_clearance = crossbar_q[0] - chamber_q[0]
    rear_axial_clearance = chamber_q[1] - crossbar_q[1]
    if min(front_axial_clearance, rear_axial_clearance) < nominal_fit - EPSILON:
        raise ValueError("Crossbar lacks axial clearance through its full rotation")
    chamber_axial_clearance = chamber_depth - crossbar_axial
    _require_close(chamber_axial_clearance, float(crossbar["total_chamber_axial_clearance_mm"]), "total chamber axial clearance")
    _require_close(front_axial_clearance, float(crossbar["maximum_installed_outward_float_mm"]), "installed outward float")

    swept_radius = math.hypot(cross_long / 2.0, cross_short / 2.0)
    chamber_radius = float(boss["rotation_chamber_diameter_mm"]) / 2.0
    chamber_sweep_clearance = chamber_radius - swept_radius
    if chamber_sweep_clearance < 0.4 - EPSILON:
        raise ValueError("Circular chamber does not clear every crossbar corner through the 90 degree sweep")
    outer_wall = min(
        (outer_u - float(boss["rotation_chamber_diameter_mm"])) / 2.0,
        (outer_y - float(boss["rotation_chamber_diameter_mm"])) / 2.0,
        (outer_u - slot_u) / 2.0,
        (outer_y - slot_y) / 2.0,
    )
    _require_close(outer_wall, float(boss["minimum_outer_wall_mm"]), "bayonet boss minimum outer wall")
    if outer_wall < minimum_wall - EPSILON:
        raise ValueError("Bayonet boss loses the minimum wall around its swept cutter")
    notch_depth = float(boss["locked_index_notch_depth_mm"])
    notch_parent_wall = (outer_u - float(boss["rotation_chamber_diameter_mm"])) / 2.0
    notch_residual_wall = notch_parent_wall - notch_depth
    _require_close(notch_parent_wall, float(boss["locked_index_notch_parent_wall_mm"]), "locked-index notch parent wall")
    _require_close(notch_residual_wall, float(boss["locked_index_notch_residual_wall_mm"]), "locked-index notch residual wall")
    if notch_residual_wall < minimum_wall - EPSILON:
        raise ValueError("Locked-index notch cuts the bayonet boss below the minimum printed wall")
    capture_overlap = (cross_long - slot_u) / 2.0
    _require_close(capture_overlap, float(crossbar["minimum_gate_capture_overlap_each_lug_mm"]), "gate capture overlap")
    if capture_overlap <= 0.0:
        raise ValueError("Locked crossbar has no positive axial capture")

    if float(crossbar["entry_orientation_deg"]) != 0.0 or float(crossbar["locked_orientation_deg"]) != 90.0:
        raise ValueError("Cross-key must use the exact vertical-entry, horizontal-locked quarter-turn")
    for angle in range(0, 91):
        for u, y in crossbar_corners_at_rotation(cross_long, cross_short, angle):
            if math.hypot(u, y) > chamber_radius + EPSILON:
                raise ValueError("Sampled crossbar corner escapes the analytic rotation chamber")

    handle = key["visible_handle_and_positive_index"]
    handle_q = tuple(float(value) for value in handle["handle_installed_q_envelope_mm"])
    handle_long_span = float(handle["handle_long_span_mm"])
    dog_nominal = float(handle["latch_dog_nominal_positive_engagement_mm"])
    _require_close(
        float(handle["minimum_pull_feature_mm"]),
        handle_long_span,
        "minimum pull feature span",
    )
    flexure_developed_length = float(
        handle["integral_u_flexure_developed_length_mm"]
    )
    # The compact handle contains a folded U, not a fictitious straight beam.
    # Independently reproduce the generator's authored centerline from its
    # frozen root, dog, slot, and shaft-neck geometry.
    folded = handle["folded_u_authored_geometry"]
    root_width = float(folded["root_width_u_mm"])
    dog_width = float(folded["dog_width_u_mm"])
    dog_inset_from_handle_end = float(
        folded["dog_inset_from_handle_end_u_mm"]
    )
    open_slot_q = float(folded["open_slot_q_mm"])
    neck_width = float(folded["shaft_spine_neck_width_u_mm"])
    neck_q_thickness = float(folded["neck_q_thickness_mm"])
    neck_shaft_union = float(folded["neck_shaft_positive_union_q_mm"])
    dog_front_union = float(folded["dog_front_beam_positive_union_q_mm"])
    dog_rear_projection = float(folded["dog_rear_latch_projection_q_mm"])
    dog_total_q_depth = float(folded["dog_total_q_depth_mm"])
    if (
        min(
            root_width,
            dog_width,
            dog_inset_from_handle_end,
            open_slot_q,
            neck_width,
            neck_q_thickness,
            neck_shaft_union,
            dog_front_union,
            dog_rear_projection,
            dog_total_q_depth,
        )
        <= 0.0
    ):
        raise ValueError("Folded-U authored component datums must all be positive")
    _require_close(neck_width, float(handle["handle_short_span_mm"]), "folded-U neck width")
    _require_close(neck_q_thickness, open_slot_q, "folded-U neck q thickness")
    _require_close(neck_shaft_union, neck_q_thickness / 2.0, "folded-U neck/shaft union")
    _require_close(dog_rear_projection, dog_nominal, "folded-U rear latch projection")
    _require_close(
        dog_total_q_depth,
        dog_rear_projection
        + float(handle["flexure_thickness_mm"])
        + dog_front_union
        + open_slot_q,
        "folded-U dog total q depth",
    )
    dog_center_u = (
        handle_long_span / 2.0
        - dog_inset_from_handle_end
        + dog_width / 2.0
    )
    left_root_center_u = -handle_long_span / 2.0 + root_width / 2.0
    fixed_neck_left_u = -neck_width / 2.0
    spine_q0 = handle_q[0] + float(handle["flexure_thickness_mm"]) + open_slot_q
    authored_segments = (
        dog_center_u - left_root_center_u,
        spine_q0 - handle_q[0],
        fixed_neck_left_u - left_root_center_u,
    )
    configured_segments = tuple(
        float(value)
        for value in handle["authored_folded_u_centerline_segment_lengths_mm"]
    )
    if len(configured_segments) != 3 or any(
        abs(actual - expected) > EPSILON
        for actual, expected in zip(authored_segments, configured_segments)
    ):
        raise ValueError("Folded-U flexure segments do not match the authored root/dog/neck path")
    authored_length = sum(authored_segments)
    _require_close(
        authored_length,
        float(handle["authored_folded_u_centerline_length_mm"]),
        "authored folded-U centerline length",
    )
    if flexure_developed_length > authored_length + EPSILON:
        raise ValueError("Conservative flexure strain length exceeds the authored folded-U path")
    _require_close(_span(handle_q, "visible handle q"), float(handle["handle_axial_thickness_mm"]), "handle thickness")
    overall_q = shaft_q[1] - handle_q[0]
    service = key["exact_service_kinematics"]
    _require_close(overall_q, float(service["installed_key_overall_q_length_mm"]), "installed key overall length")
    _require_close(float(service["insertion_translation_q_mm"]), overall_q, "insertion translation")
    if tuple(float(value) for value in service["locking_rotation_deg"]) != (0.0, 90.0):
        raise ValueError("Locking motion is not an exact positive quarter-turn")
    if tuple(float(value) for value in service["removal_rotation_deg"]) != (90.0, 0.0):
        raise ValueError("Removal is not the exact inverse quarter-turn and visible-front translation")
    _require_close(float(service["removal_translation_q_mm"]), -overall_q, "removal translation")
    forbidden = {str(value) for value in service["forbidden_access"]}
    if {"wall/rear", "above cassette", "concealed keeper", "second loose tool-side part"} - forbidden:
        raise ValueError("Cross-key service contract permits hidden or extra-part access")
    external_access = float(service["minimum_external_straight_service_access_mm"])
    if external_access < 75.0 - EPSILON:
        raise ValueError("Cross-key lacks 75 mm of visible-front service access")

    if int(boss["unique_locked_index_notch_count"]) != 1 or "friction" not in handle["anti_rotation_rule"] or "prohibited" not in handle["anti_rotation_rule"]:
        raise ValueError("Cross-key anti-rotation is not a unique positive, non-friction index")
    outward_float = float(crossbar["maximum_installed_outward_float_mm"])
    minimum_dog = dog_nominal - outward_float
    _require_close(minimum_dog, float(handle["minimum_latch_engagement_at_outward_float_mm"]), "minimum latch engagement")
    if minimum_dog < 0.8 - EPSILON:
        raise ValueError("Latch dog loses positive engagement at maximum outward float")
    release = float(handle["front_release_deflection_mm"])
    release_clearance = release - dog_nominal
    _require_close(release_clearance, float(handle["post_release_dog_clearance_mm"]), "post-release dog clearance")
    if release_clearance < nominal_fit - EPSILON:
        raise ValueError("Visible latch release does not clear the hard notch")
    flexure_strain = (
        6.0
        * release
        * float(handle["flexure_thickness_mm"])
        / flexure_developed_length**2
    )
    _require_close(flexure_strain, float(handle["nominal_outer_fiber_strain"]), "nominal flexure strain")
    if flexure_strain > 0.03 + EPSILON:
        raise ValueError("Unqualified PETG latch flexure exceeds the provisional 3 percent geometry screen")

    minimum_pitch = min(
        values["final_u_centers_mm"][1] - values["final_u_centers_mm"][0]
        for values in top["run_centers_mm"].values()
    )
    if minimum_pitch - outer_u < minimum_wall - EPSILON:
        raise ValueError("Adjacent top-receiver bayonet bosses do not retain a minimum-wall gap")
    if minimum_pitch - handle_long_span < minimum_wall - EPSILON:
        raise ValueError("Adjacent locked visible handles collide or crowd their service gaps")
    nearest_top_center = min(
        min(float(value) for value in values["final_u_centers_mm"])
        for values in top["run_centers_mm"].values()
    )
    crown_half_width = float(arcade["rear_crown_bridge"]["width_mm"]) / 2.0
    handle_to_crown = nearest_top_center - handle_long_span / 2.0 - crown_half_width
    if handle_to_crown < float(arcade["minimum_crown_ligament_mm"]) - EPSILON:
        raise ValueError("Locked top-key handle crowds the crown bridge plan envelope")

    saved = key["saved_print_orientation"]
    bare = tuple(float(value) for value in saved["bare_key_envelope_mm"])
    brim = tuple(float(value) for value in saved["envelope_with_brim_mm"])
    brim_each = float(saved["brim_each_side_mm"])
    _require_close(bare[0], overall_q, "saved key q length")
    _require_close(bare[1], handle_long_span, "saved key handle span")
    _require_close(bare[2], max(shaft, float(handle["handle_short_span_mm"])), "saved key height")
    _require_close(brim[0], bare[0] + 2.0 * brim_each, "saved brim x")
    _require_close(brim[1], bare[1] + 2.0 * brim_each, "saved brim y")
    _require_close(brim[2], bare[2], "saved brim z")
    build_limit = tuple(float(value) for value in saved["maximum_required_build_envelope_mm"])
    if any(actual > limit + EPSILON for actual, limit in zip(brim, build_limit)):
        raise ValueError("Cross-key saved orientation exceeds the 180 mm-class build envelope")
    if saved["support_free_claim_allowed"] or saved["production_orientation_allowed"]:
        raise ValueError("Unprinted cross-key orientation may not be production-qualified")

    gate = key["qualification_gate"]
    if gate["status"] != "BLOCKED_PENDING_CONFIRMED_PRINTER_NOZZLE_PETG_AND_PHYSICAL_TESTS":
        raise ValueError("Cross-key must fail closed before printer, PETG, and physical qualification")
    if not gate["same_actual_petg_required"] or not gate["actual_parent_receiver_coupon_required"]:
        raise ValueError("Cross-key gate omits same-PETG or actual-parent coupon qualification")
    if int(gate["minimum_full_insert_lock_release_remove_cycles"]) < 100:
        raise ValueError("Cross-key cycle gate is below 100 complete service cycles")
    if int(gate["thermal_cycle_count"]) < 20 or float(gate["thermal_cycle_low_c"]) >= float(gate["thermal_cycle_high_c"]):
        raise ValueError("Cross-key thermal qualification gate is incomplete")
    migration_days = [int(value) for value in gate["migration_dwell_days"]]
    if migration_days != [30, 90] or int(gate["screening_migration_gate_days"]) != 30 or int(gate["release_migration_gate_days"]) != 90:
        raise ValueError("Cross-key lacks exact 30-day screening and 90-day release migration gates")
    if "blocks all complete-shelf packages" not in gate["failure_rule"]:
        raise ValueError("Cross-key failure does not fail the complete package closed")

    counts = key["object_count_contract"]
    per_level = int(counts["cassette_top_keys_per_level"]) + int(counts["spring_keys_per_level"])
    _require_close(float(per_level), float(counts["total_keys_per_level"]), "per-level key total")
    if per_level != 54 or int(counts["total_keys_selected_two_levels"]) != 108 or int(counts["additional_keeper_objects"]) != 0:
        raise ValueError("Positive cross-key must preserve the exact 54/108 object topology")
    one = cfg["nominal_geometry_snapshot"]["nominal_part_topology"]
    two = cfg["nominal_geometry_snapshot"]["selected_two_level_part_topology"]
    if int(one["cassette_top_retention_wedges"]) != int(counts["cassette_top_keys_per_level"]) or int(one["spring_retention_wedges"]) != int(counts["spring_keys_per_level"]):
        raise ValueError("One-level release inventory does not map one-for-one to positive cross-keys")
    if int(two["cassette_top_retention_wedges"]) + int(two["spring_retention_wedges"]) != 108:
        raise ValueError("Two-level release inventory does not contain exactly 108 positive cross-keys")
    if "zero vertical" not in key["retention_role"] or "no numerical load rating" not in key["retention_role"]:
        raise ValueError("Retention cross-key was assigned structural capacity credit")

    return PositiveCrossKeyContract(
        family_id=str(key["family_id"]),
        shaft_diameter_mm=shaft,
        bore_diameter_mm=bore,
        shaft_radial_clearance_mm=shaft_radial_clearance,
        top_tenon_ligament_run_y_mm=top_ligaments,
        spring_tenon_ligament_run_y_mm=spring_ligaments,
        entry_clearance_run_y_mm=entry_clearances,
        crossbar_corner_sweep_radius_mm=swept_radius,
        chamber_radial_sweep_clearance_mm=chamber_sweep_clearance,
        boss_minimum_outer_wall_mm=outer_wall,
        locked_index_notch_residual_wall_mm=notch_residual_wall,
        gate_capture_overlap_each_lug_mm=capture_overlap,
        chamber_axial_clearance_mm=chamber_axial_clearance,
        maximum_installed_outward_float_mm=outward_float,
        minimum_latch_engagement_at_outward_float_mm=minimum_dog,
        release_clearance_mm=release_clearance,
        conservative_flexure_strain_length_mm=flexure_developed_length,
        authored_folded_u_centerline_segments_mm=authored_segments,
        authored_folded_u_centerline_length_mm=authored_length,
        nominal_flexure_outer_fiber_strain=flexure_strain,
        minimum_external_service_access_mm=external_access,
        exact_insertion_translation_mm=overall_q,
        exact_locking_rotation_deg=90.0,
        saved_bare_envelope_mm=bare,
        saved_brim_envelope_mm=brim,
        keys_per_level=per_level,
        keys_selected_two_levels=int(counts["total_keys_selected_two_levels"]),
        load_credit="zero vertical, bearing, longitudinal-tension, or shelf-load capacity credit",
        kinematic_stage_matrices={
            "visible_front_approach": key_transform_q(0.0, -overall_q),
            "fully_inserted_entry_index": key_transform_q(0.0, 0.0),
            "positively_indexed_locked": key_transform_q(90.0, 0.0),
            "released_entry_index": key_transform_q(0.0, 0.0),
            "visible_front_withdrawn": key_transform_q(0.0, -overall_q),
        },
    )
