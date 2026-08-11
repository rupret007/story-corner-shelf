#!/usr/bin/env python3
"""Regression and safety-contract tests for the experimental r6 geometry."""

from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from design_math import (  # noqa: E402
    calculate_plan,
    grand_arc,
    maximum_angle_error_deg,
    production_blockers,
    required_corner_gap_mm,
    x_corbel_geometry,
)


CONFIG_PATH = R6 / "config.json"


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_config() -> dict:
    return json.loads(
        CONFIG_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


class R6DesignMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = load_config()
        cls.plan = calculate_plan(cls.cfg)

    def test_all_petg_scope_is_explicit_and_unrated(self) -> None:
        project = self.cfg["project"]
        material = self.cfg["material"]
        protocol = self.cfg["test_protocol"]
        self.assertFalse(project["embedded_gcode_allowed"])
        self.assertEqual(material["printed_material"], "black PETG only")
        self.assertEqual(
            material["nonprinted_boundary"], "wall screws and compatible heads/washers only"
        )
        self.assertFalse(protocol["tested_load_rating_exists"])
        self.assertFalse(self.cfg["support"]["printed_wall_anchors_allowed"])
        self.assertFalse(self.cfg["support"]["hollow_wall_anchors_allowed_in_primary_load_path"])

    def test_exact_nominal_l_plan(self) -> None:
        plan = self.plan
        self.assertAlmostEqual(plan.through.length_mm, 1514.475, places=6)
        self.assertAlmostEqual(plan.return_run.start_from_corner_mm, 177.55, places=6)
        self.assertAlmostEqual(plan.return_run.length_mm, 733.675, places=6)
        self.assertAlmostEqual(plan.through.start_pier_inset_mm, 31.4325, places=6)
        self.assertAlmostEqual(plan.through.end_pier_inset_mm, 31.4325, places=6)
        self.assertAlmostEqual(plan.return_run.start_pier_inset_mm, 27.0325, places=6)
        self.assertAlmostEqual(plan.return_run.end_pier_inset_mm, 31.4325, places=6)
        self.assertAlmostEqual(plan.through.bay_span_mm, 241.935, places=6)
        self.assertAlmostEqual(plan.return_run.bay_span_mm, 225.07, places=6)
        self.assertAlmostEqual(plan.integral_boss_projection_beyond_cassette_mm, 7.2, places=6)
        self.assertAlmostEqual(plan.full_removable_facade_projection_beyond_cassette_mm, 13.2, places=6)
        self.assertAlmostEqual(plan.visible_front_projection_beyond_cassette_mm, 13.2, places=6)
        self.assertAlmostEqual(plan.ornament_axial_service_stroke_mm, 4.4, places=6)
        self.assertAlmostEqual(plan.return_corner_cosmetic_overhang_back_mm, 4.4, places=6)
        self.assertAlmostEqual(plan.structural_arm_clearance_mm, 18.8, places=6)
        self.assertAlmostEqual(plan.corner_integral_boss_front_plane_absolute_mm, 165.95, places=6)
        self.assertAlmostEqual(plan.corner_visible_front_plane_absolute_mm, 171.95, places=6)
        self.assertAlmostEqual(plan.corner_service_swept_front_plane_absolute_mm, 176.35, places=6)
        self.assertAlmostEqual(plan.return_corner_cosmetic_leading_plane_absolute_mm, 173.15, places=6)
        self.assertAlmostEqual(plan.exact_crown_alignment_error_mm, 0.0, places=7)
        self.assertAlmostEqual(plan.minimum_perpendicular_corbel_clearance_mm, 30.2325, places=6)
        self.assertAlmostEqual(plan.minimum_structural_front_to_perpendicular_corbel_plan_reserve_mm, 21.8325, places=6)
        self.assertAlmostEqual(plan.minimum_integral_boss_front_to_perpendicular_corbel_plan_reserve_mm, 14.6325, places=6)
        self.assertAlmostEqual(
            plan.minimum_visible_front_to_perpendicular_corbel_plan_reserve_mm,
            8.6325,
            places=6,
        )
        self.assertAlmostEqual(plan.minimum_service_swept_front_to_perpendicular_corbel_plan_reserve_mm, 4.2325, places=6)
        self.assertAlmostEqual(plan.maximum_part_axis_with_comb_mm, 162.225, places=6)

    def test_three_six_nine_stationing(self) -> None:
        plan = self.plan
        self.assertEqual((plan.return_run.bay_count, plan.through.bay_count), (3, 6))
        self.assertEqual(plan.return_run.bay_count + plan.through.bay_count, 9)
        self.assertEqual((plan.return_run.pier_count, plan.through.pier_count), (4, 7))
        self.assertEqual(plan.return_run.pier_count + plan.through.pier_count, 11)
        self.assertEqual(len(plan.return_run.cassette_nominal_widths_mm), 6)
        self.assertEqual(len(plan.through.cassette_nominal_widths_mm), 12)
        self.assertEqual(
            tuple(round(value, 4) for value in plan.through.support_centers_absolute_mm),
            (37.7825, 279.7175, 521.6525, 763.5875, 1005.5225, 1247.4575, 1489.3925),
        )
        self.assertEqual(
            tuple(round(value, 4) for value in plan.return_run.support_centers_absolute_mm),
            (204.5825, 429.6525, 654.7225, 879.7925),
        )

    def test_two_independent_levels_fit_the_reported_vertical_zone(self) -> None:
        closet = self.cfg["closet"]
        vertical = closet["vertical_layout"]
        drop = self.cfg["tied_arcade"]["total_height_mm"] / 25.4
        lower = vertical["reference_lower_shelf_top_above_outlet_top_in"]
        upper = vertical["reference_upper_shelf_top_above_outlet_top_in"]
        zone = closet["measured_vertical_zone_from_outlet_top_to_ceiling_in"]
        self.assertEqual(vertical["minimum_shelf_levels"], 2)
        self.assertEqual(vertical["selected_shelf_levels"], 2)
        self.assertAlmostEqual(drop, vertical["grand_frame_drop_below_shelf_top_in"], places=6)
        self.assertAlmostEqual(upper - lower, vertical["reference_top_to_top_spacing_in"])
        self.assertAlmostEqual(
            upper - drop - lower,
            vertical["reference_clear_opening_between_levels_in"],
            places=6,
        )
        self.assertAlmostEqual(
            zone - upper,
            vertical["reference_clearance_above_upper_shelf_in"],
            places=6,
        )
        self.assertAlmostEqual(
            lower - drop,
            vertical["reference_lower_frame_bottom_above_outlet_top_in"],
            places=6,
        )
        self.assertIn("no printed column", vertical["level_independence_rule"])

        one = self.cfg["nominal_geometry_snapshot"]["nominal_part_topology"]
        two = self.cfg["nominal_geometry_snapshot"]["selected_two_level_part_topology"]
        for key in (
            "deck_cassettes",
            "arcade_halves",
            "structural_pier_x_corbels",
            "sliding_saddles",
            "saddle_pins",
            "cassette_locks",
            "cassette_top_retention_wedges",
            "total_run_seams",
            "diaphragm_bowtie_keys",
            "fixed_crown_entablature_tie_keys",
            "floating_pier_entablature_alignment_keys",
            "crown_bridges",
            "crown_bridge_retention_pins",
            "spring_retention_wedges",
            "stitch_rail_segments",
            "stitch_rail_overlap_joints",
            "stitch_rail_joint_pins",
            "run_end_tie_blocks",
        ):
            self.assertEqual(two[key], 2 * one[key], key)
        top_interfaces = self.cfg["tied_arcade"]["cassette_vertical_tenon_count_per_half"]
        self.assertEqual(one["cassette_top_retention_wedges"], top_interfaces * one["arcade_halves"])
        self.assertEqual(one["spring_retention_wedges"], one["arcade_halves"])
        features = self.cfg["nominal_geometry_snapshot"]["integral_feature_topology"]
        self.assertEqual(features["per_level_cassette_vertical_tenons"], top_interfaces * one["arcade_halves"])
        self.assertEqual(features["per_level_spring_vertical_tenons"], one["arcade_halves"])
        self.assertEqual(
            features["selected_two_level_cassette_vertical_tenons"],
            2 * features["per_level_cassette_vertical_tenons"],
        )
        self.assertEqual(
            features["selected_two_level_spring_vertical_tenons"],
            2 * features["per_level_spring_vertical_tenons"],
        )

        minimum_access = vertical["minimum_straight_wedge_and_pin_service_access_mm"]
        clear_opening_mm = vertical["reference_clear_opening_between_levels_in"] * 25.4
        self.assertGreater(clear_opening_mm, minimum_access)
        self.assertGreaterEqual(minimum_access, 75.0)
        self.assertIn("upper level first", vertical["installation_order"])
        self.assertIn("independently removable", vertical["installation_order"])

    def test_cassette_widths_and_seam_reserve(self) -> None:
        through = self.plan.through
        return_run = self.plan.return_run
        self.assertAlmostEqual(max(through.cassette_nominal_widths_mm), 152.4, places=6)
        self.assertAlmostEqual(max(through.cassette_physical_widths_mm), 152.225, places=6)
        self.assertAlmostEqual(min(through.cassette_physical_widths_mm), 120.6175, places=6)
        self.assertAlmostEqual(max(return_run.cassette_physical_widths_mm), 143.7925, places=6)
        self.assertAlmostEqual(min(return_run.cassette_physical_widths_mm), 112.185, places=6)
        self.assertAlmostEqual(return_run.cassette_physical_widths_mm[0], 139.3925, places=6)
        self.assertLess(self.plan.maximum_part_axis_with_comb_mm, 168.0)

    def test_grand_arc_geometry_matches_snapshot(self) -> None:
        rise = self.cfg["tied_arcade"]["arch_extrados_rise_mm"]
        long_arc = grand_arc(self.plan.through.bay_span_mm, rise)
        short_arc = grand_arc(self.plan.return_run.bay_span_mm, rise)
        snapshot = self.cfg["nominal_geometry_snapshot"]["grand_main_arch_geometry"]
        self.assertAlmostEqual(long_arc.radius_mm, snapshot["through_extrados_radius_mm"], places=6)
        self.assertAlmostEqual(
            long_arc.included_angle_deg,
            snapshot["through_extrados_included_angle_deg"],
            places=6,
        )
        self.assertAlmostEqual(short_arc.radius_mm, snapshot["return_extrados_radius_mm"], places=6)
        self.assertAlmostEqual(
            short_arc.included_angle_deg,
            snapshot["return_extrados_included_angle_deg"],
            places=6,
        )
        self.assertLess(long_arc.horizontal_thrust_over_total_load_proxy, 0.34)
        self.assertLess(short_arc.horizontal_thrust_over_total_load_proxy, 0.32)

    def test_x_corbel_has_two_exact_345_paths_and_explicit_cassette_union(self) -> None:
        x = x_corbel_geometry(self.cfg)
        self.assertEqual(x.wall_upper_node, (0.0, 154.0))
        self.assertEqual(x.front_spring_node, (144.0, 46.0))
        self.assertEqual(x.wall_lower_node, (0.0, 30.0))
        self.assertEqual(x.front_saddle_node, (144.0, 138.0))
        self.assertAlmostEqual(x.diagonal_mm, 180.0, places=7)
        self.assertAlmostEqual(x.brace_crossing[0], 82.6666666667, places=7)
        self.assertAlmostEqual(x.brace_crossing[1], 92.0, places=7)
        cassette_bottom = (
            self.cfg["tied_arcade"]["total_height_mm"]
            - self.cfg["structure"]["cassette_total_height_mm"]
        )
        self.assertEqual(x.front_saddle_node[1], cassette_bottom)
        corbel = self.cfg["corbel"]
        self.assertAlmostEqual(corbel["x_brace_crossing_mm"][0], x.brace_crossing[0], places=6)
        self.assertAlmostEqual(corbel["x_brace_crossing_mm"][1], x.brace_crossing[1], places=7)
        self.assertGreaterEqual(
            corbel["minimum_crossing_boss_diameter_mm"],
            2.0 * corbel["x_brace_chord_mm"],
        )
        union = corbel["upper_diagonal_cassette_union_segment_mm"]
        self.assertEqual(tuple(union["from"]), x.wall_upper_node)
        # This is the buffered outer cradle envelope, not the diagonal
        # centerline endpoint. Receiver packing must clear the full solid.
        self.assertAlmostEqual(union["maximum_local_q_from_rear_mm"], 25.383333, places=6)
        self.assertIn("open-bottom cradle cutter", union["rule"])
        self.assertAlmostEqual(
            (
                corbel["body_thickness_mm"]
                - corbel["provisional_maximum_driver_tunnel_width_mm"]
            )
            / 2.0,
            corbel["minimum_continuous_side_web_each_side_mm"],
        )
        self.assertIn("crosses at least one X diagonal", corbel["driver_tunnel_x_brace_rule"])

    def test_corner_angle_gate_preserves_residual_gap(self) -> None:
        corner = self.cfg["closet"]["inside_corner"]
        visible_depth = (
            self.plan.depth_mm
            + self.plan.visible_front_projection_beyond_cassette_mm
        )
        max_error = corner["maximum_square_corner_deviation_deg"]
        shift = visible_depth * abs(math.tan(math.radians(max_error)))
        required = required_corner_gap_mm(
            depth_mm=visible_depth,
            measured_angle_deg=90.0 + max_error,
            minimum_gap_mm=corner["minimum_residual_visible_joint_clearance_mm"],
            wall_bow_mm=0.0,
            datum_uncertainty_mm=0.0,
            manufacturing_installation_reserve_mm=corner[
                "minimum_production_manufacturing_installation_reserve_mm"
            ],
        )
        self.assertGreater(required, corner["visible_ornament_joint_gap_mm"])
        self.assertAlmostEqual(
            required
            - shift
            - corner["minimum_production_manufacturing_installation_reserve_mm"],
            corner["minimum_residual_visible_joint_clearance_mm"],
            places=7,
        )
        allowable = maximum_angle_error_deg(
            depth_mm=visible_depth,
            available_gap_mm=(
                corner["visible_ornament_joint_gap_mm"]
                - corner["minimum_residual_visible_joint_clearance_mm"]
            ),
        )
        self.assertLess(allowable, max_error)

    def test_seam_classes_allow_thermal_movement(self) -> None:
        topology = self.cfg["joinery"]["run_seam_topology"]
        self.assertEqual(topology["total_run_seams"], 16)
        self.assertEqual(topology["fixed_crown_seams"], 9)
        self.assertEqual(topology["thermally_floating_pier_seams"], 7)
        self.assertEqual(
            topology["fixed_crown_seams"] + topology["thermally_floating_pier_seams"],
            topology["total_run_seams"],
        )
        self.assertIn("neither rail may bypass", self.cfg["structure"]["stitch_rail_movement_policy"])

    def test_front_joint_families_do_not_overlap_in_plan(self) -> None:
        structure = self.cfg["structure"]
        bowtie = self.cfg["joinery"]["diaphragm_bowtie"]
        front = self.cfg["joinery"]["front_entablature_joint"]
        zone_start, zone_end = structure["front_entablature_tie_zone_from_rear_mm"]
        bowtie_front_edge = bowtie["centers_from_rear_mm"][-1] + bowtie["head_width_mm"] / 2.0
        self.assertGreaterEqual(
            zone_start - bowtie_front_edge,
            bowtie["minimum_plan_ligament_to_front_entablature_joint_mm"],
        )
        self.assertAlmostEqual(front["center_from_rear_mm"], (zone_start + zone_end) / 2.0)
        self.assertEqual(front["fixed_crown_tie_key"]["count_full_l"], 9)
        self.assertEqual(front["floating_pier_seam_alignment_key"]["count_full_l"], 0)
        self.assertIn("collision", front["floating_pier_seam_alignment_key"]["status"])

    def test_crown_bridge_has_real_insertion_and_depth_reserve(self) -> None:
        bridge = self.cfg["tied_arcade"]["rear_crown_bridge"]
        isolation = self.cfg["ornament_isolation"]
        self.assertIn("upward from below", bridge["insertion_path"])
        self.assertIn("downward", bridge["removal_path"])
        self.assertEqual(bridge["retention_pin_joint"], "accessible double shear")
        self.assertIn("anti-drop", bridge["retention_pin_role"])
        self.assertLessEqual(
            isolation["rear_crown_bridge_depth_zone_mm"][1],
            isolation["overall_crown_swept_depth_envelope_mm"],
        )
        self.assertAlmostEqual(
            isolation["structural_chassis_depth_zone_mm"][1]
            + bridge["thickness_mm"],
            isolation["rear_crown_bridge_depth_zone_mm"][1],
        )
        self.assertEqual(bridge["final_u_envelope_from_crown_mm"], [-36.0, 36.0])
        self.assertEqual(bridge["final_y_envelope_mm"], [90.0, 138.0])
        rails = bridge["dovetail_rails"]
        self.assertEqual(rails["u_centers_from_crown_mm"], [-28.0, 28.0])
        self.assertEqual(rails["final_y_envelope_mm"], [120.9, 127.9])
        self.assertEqual(bridge["retention_pin_fixed_half"], "right")
        self.assertEqual(
            bridge["retention_pin_axis"],
            "from the visible front toward the wall along -q",
        )
        self.assertEqual(bridge["retention_pin_center_u_y_mm"], [9.7, 128.3])
        expected_boss = (
            bridge["retention_pin_hole_diameter_mm"]
            + 2.0 * bridge["retention_pin_clear_ligament_mm"]
        )
        self.assertEqual(bridge["retention_pin_minimum_boss_u_y_mm"], [expected_boss] * 2)
        pin_u, pin_y = bridge["retention_pin_center_u_y_mm"]
        pin_radius = bridge["retention_pin_hole_diameter_mm"] / 2.0
        boss_u, boss_y = bridge["retention_pin_minimum_boss_u_y_mm"]
        self.assertAlmostEqual(boss_u / 2.0 - pin_radius, 7.0, places=7)
        self.assertAlmostEqual(boss_y / 2.0 - pin_radius, 7.0, places=7)
        self.assertGreaterEqual(
            pin_y - pin_radius - bridge["final_y_envelope_mm"][0],
            7.0,
        )
        self.assertAlmostEqual(
            bridge["final_y_envelope_mm"][1] - pin_y - pin_radius,
            7.0,
            places=7,
        )
        self.assertEqual(
            bridge["rear_return_ear_global_depth_zone_mm"],
            isolation["crown_pin_rear_return_ear_depth_zone_mm"],
        )
        self.assertEqual(
            bridge["rear_return_ear_global_depth_zone_mm"][1],
            isolation["overall_crown_swept_depth_envelope_mm"],
        )
        self.assertGreaterEqual(bridge["minimum_straight_service_access_mm"], 75.0)

    def test_final_x_cassette_tenons_have_no_slide_or_crown_collision(self) -> None:
        arcade = self.cfg["tied_arcade"]
        joint = arcade["cassette_final_x_vertical_tenon_joint"]
        bridge = arcade["rear_crown_bridge"]
        self.assertEqual(arcade["cassette_vertical_tenon_count_per_half"], 2)
        self.assertEqual(joint["whole_half_longitudinal_travel_mm"], 0.0)
        self.assertIn("straight upward", joint["installation_motion"])
        self.assertTrue(joint["open_bottom_receivers"])
        expected_receiver_width = (
            joint["tenon_run_width_mm"] + 2.0 * joint["receiver_clearance_per_side_mm"]
        )
        expected_receiver_depth = (
            joint["tenon_depth_mm"] + 2.0 * joint["receiver_clearance_per_side_mm"]
        )
        self.assertAlmostEqual(joint["receiver_run_width_mm"], expected_receiver_width)
        self.assertAlmostEqual(joint["receiver_depth_mm"], expected_receiver_depth)
        self.assertAlmostEqual(
            2.0 * joint["receiver_front_and_rear_cheek_each_mm"]
            + joint["receiver_depth_mm"],
            arcade["chassis_depth_mm"],
        )

        bridge_half_width = bridge["width_mm"] / 2.0
        minimum_wall = self.cfg["joinery"]["minimum_wall_mm"]
        for run_id, values in joint["run_centers_mm"].items():
            final = values["final_u_centers_mm"]
            entry = values["entry_u_centers_mm"]
            self.assertEqual(final, entry, run_id)
            self.assertEqual(len(final), 2)
            self.assertEqual(final, sorted(final))
            half_width = values["governing_clear_half_width_mm"]
            expected_outer = (
                half_width
                - joint["receiver_run_width_mm"] / 2.0
                - values["minimum_pier_side_end_ligament_mm"]
            )
            self.assertAlmostEqual(final[-1], expected_outer, places=7)
            minimum_web = min(b - a for a, b in zip(final, final[1:])) - joint[
                "receiver_run_width_mm"
            ]
            self.assertAlmostEqual(minimum_web, values["minimum_receiver_web_between_mm"])
            self.assertGreaterEqual(minimum_web, minimum_wall)
            crown_clearance = final[0] - joint["receiver_run_width_mm"] / 2.0 - bridge_half_width
            self.assertGreaterEqual(crown_clearance, arcade["minimum_crown_ligament_mm"])

        self.assertEqual(
            joint["run_centers_mm"]["long_wall_5ft"]["final_u_centers_mm"],
            [50.0, 80.5925],
        )
        self.assertEqual(
            joint["run_centers_mm"]["short_wall_3ft"]["final_u_centers_mm"],
            [49.6, 72.16],
        )
        self.assertEqual(arcade["cassette_vertical_tenon_count_per_half"], 2)
        self.assertEqual(arcade["cassette_compression_pad_count_per_half"], 2)

        hole_run, hole_y = arcade["retention_wedge"]["through_hole_run_y_mm"]
        self.assertAlmostEqual(
            (joint["tenon_run_width_mm"] - hole_run) / 2.0,
            joint["minimum_tenon_clear_ligament_run_mm"],
        )
        self.assertAlmostEqual(
            (joint["tenon_engagement_height_mm"] - hole_y) / 2.0,
            joint["minimum_tenon_clear_ligament_y_mm"],
        )
        self.assertIn("zero vertical capacity credit", joint["load_path_rule"])
        self.assertTrue(any("whole-half 12 mm" in item for item in arcade["kinematic_no_go_conditions"]))

    def test_spring_tenon_uses_broad_bearing_and_accessible_wedge(self) -> None:
        arcade = self.cfg["tied_arcade"]
        spring = arcade["spring_final_x_vertical_joint"]
        wedge = arcade["retention_wedge"]
        self.assertIn("straight upward", spring["installation_motion"])
        self.assertTrue(spring["open_bottom_receiver"])
        self.assertNotIn("spring_tongue_engagement_mm", arcade)
        self.assertNotIn("cassette_retention_t_lug_mm", arcade)
        self.assertAlmostEqual(
            spring["tenon_run_width_mm"]
            + 2.0 * spring["receiver_clearance_per_side_mm"],
            spring["receiver_run_width_mm"],
        )
        self.assertAlmostEqual(
            spring["tenon_depth_mm"]
            + 2.0 * spring["receiver_clearance_per_side_mm"],
            spring["receiver_depth_mm"],
        )
        self.assertAlmostEqual(
            2.0 * spring["receiver_front_and_rear_cheek_each_mm"]
            + spring["receiver_depth_mm"],
            arcade["chassis_depth_mm"],
        )
        hole_run, hole_y = spring["retention_wedge_hole_run_y_mm"]
        self.assertAlmostEqual(
            (spring["tenon_run_width_mm"] - hole_run) / 2.0,
            spring["minimum_tenon_clear_ligament_run_mm"],
        )
        self.assertAlmostEqual(
            (spring["tenon_engagement_height_mm"] - hole_y) / 2.0,
            spring["minimum_tenon_clear_ligament_y_mm"],
        )
        self.assertGreaterEqual(spring["receiver_side_wall_each_mm"], self.cfg["joinery"]["minimum_wall_mm"])
        self.assertGreaterEqual(spring["minimum_straight_service_access_mm"], 75.0)
        self.assertEqual(
            wedge["insertion_axis"],
            "front to rear along +q at the vertical entry index, followed by a visible-front quarter-turn",
        )
        self.assertEqual(wedge["family_id"], "positive_quarter_turn_cross_key")
        self.assertFalse(wedge["legacy_straight_wedge_allowed"])
        self.assertIn("zero vertical", wedge["retention_role"])
        self.assertLessEqual(wedge["maximum_rear_tip_protrusion_mm"], 0.4)

    def test_assembly_sequence_never_requires_hidden_or_longitudinal_access(self) -> None:
        arcade = self.cfg["tied_arcade"]
        sequence = " ".join(arcade["assembly_kinematics"])
        self.assertIn("final run coordinate", sequence)
        self.assertIn("do not translate", sequence)
        self.assertIn("visible front", sequence)
        self.assertIn("upward from below", sequence)
        self.assertIn("no step may require a whole-half longitudinal slide", arcade["disassembly_kinematics"])
        self.assertTrue(any("wall-side-only" in item for item in arcade["kinematic_no_go_conditions"]))

    def test_production_is_intentionally_blocked(self) -> None:
        blockers = production_blockers(self.cfg)
        required = {
            "printer.model",
            "printer.nozzle_mm",
            "printer.build_plate",
            "material.brand_and_product",
            "material.filament_drying_method",
            "closet.inside_corner.field_verified_angle_deg",
            "closet.inside_corner.field_verified_max_wall_bow_mm",
            "closet.inside_corner.field_verified_corner_datum_uncertainty_mm",
            "support.field_verified_screw_shank_diameter_mm",
            "support.field_verified_wall_finish_thickness_in",
            "support.field_verified_driver_maximum_od_mm",
            "support.field_verified_driver_straight_approach_mm",
            "closet.storage_contents.largest_bin_or_item_depth_in",
            "closet.vertical_layout.field_verified_shelf_top_offsets_above_outlet_top_in",
            "closet.vertical_layout.field_verified_outlet_service_clearance_in",
            "test_protocol.whole_article_thermal_cycling.planned_cycle_count",
            "test_protocol.whole_article_thermal_cycling.completed",
            "test_protocol.destructive_load_to_failure.separate_specimen_id",
            "test_protocol.destructive_load_to_failure.completed",
        }
        for run in self.cfg["closet"]["runs"]:
            prefix = (
                f"closet.runs[{run['id']}].field_verified_support_records_by_level"
            )
            for level_id in ("lower", "upper"):
                required.update(
                    {
                        f"{prefix}[{level_id}].clear_wall_width_in",
                        f"{prefix}[{level_id}].corbel_centers_in",
                        f"{prefix}[{level_id}].stud_or_blocking_material",
                        f"{prefix}[{level_id}].framing_verification_method",
                    }
                )
        for load_case in self.cfg["test_protocol"][
            "required_nondestructive_load_cases"
        ]:
            required.add(
                f"test_protocol.nondestructive_load_case_completion[{load_case}]"
            )
        self.assertTrue(required.issubset(set(blockers)))
        self.assertGreaterEqual(len(blockers), 20)
        self.assertFalse(self.cfg["corbel"]["production_fastener_geometry_allowed"])
        self.assertTrue(self.cfg["support"]["requires_sacrificial_wall_mockup"])
        self.assertTrue(self.cfg["support"]["requires_full_bay_test_before_overhead_install"])

    def test_physical_test_protocol_names_every_required_distinct_case(self) -> None:
        protocol = self.cfg["test_protocol"]
        self.assertEqual(
            protocol["required_nondestructive_load_cases"],
            ["distributed", "front_edge", "crown_point", "asymmetric_torsional"],
        )
        self.assertEqual(
            protocol["nondestructive_load_case_completion"],
            {
                "distributed": False,
                "front_edge": False,
                "crown_point": False,
                "asymmetric_torsional": False,
            },
        )
        sequence = " ".join(protocol["prototype_sequence"]).lower()
        for phrase in (
            "crown-point",
            "asymmetric/torsional",
            "whole-article thermal cycling",
            "destructive load-to-failure",
            "separately printed matched specimen",
        ):
            self.assertIn(phrase, sequence)
        thermal = protocol["whole_article_thermal_cycling"]
        self.assertFalse(thermal["coupon_substitution_allowed"])
        self.assertFalse(thermal["completed"])
        destructive = protocol["destructive_load_to_failure"]
        self.assertTrue(destructive["separate_matched_specimen_required"])
        self.assertFalse(destructive["reuse_for_creep_or_installation_allowed"])
        self.assertFalse(destructive["completed"])

    def test_each_run_has_distinct_lower_and_upper_support_records(self) -> None:
        for run in self.cfg["closet"]["runs"]:
            records = run["field_verified_support_records_by_level"]
            self.assertEqual(set(records), {"lower", "upper"})
            self.assertIsNot(records["lower"], records["upper"])
            for record in records.values():
                self.assertEqual(
                    set(record),
                    {
                        "clear_wall_width_in",
                        "corbel_centers_in",
                        "stud_or_blocking_material",
                        "framing_verification_method",
                    },
                )
                self.assertIsNone(record["clear_wall_width_in"])
                self.assertEqual(record["corbel_centers_in"], [])
                self.assertIsNone(record["stud_or_blocking_material"])
                self.assertIsNone(record["framing_verification_method"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
