#!/usr/bin/env python3
"""Exact cross-part interface tests for the r6 release candidate."""

from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path

import numpy as np


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from ornament_access import derived_carrier_receiver_centers  # noqa: E402

from interface_geometry import (  # noqa: E402
    arch_saved_to_run_matrix,
    cassette_saved_to_run_matrix,
    corbel_print_contract,
    crown_bridge_contract,
    diaphragm_retention_contract,
    integrated_cap_lock_contract,
    ornament_interface_contract,
    physical_crown_face_shift_mm,
    rail_baseline_contract,
    required_field_corner_gap_mm,
    run_to_world_matrix,
    saddle_thermal_contract,
    spring_socket_contract,
    structural_elevation_contract,
    top_feature_x_from_spring_mm,
)


def load_config() -> dict:
    return json.loads((R6 / "config.json").read_text(encoding="utf-8"))


class InterfaceGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = load_config()

    def test_lowered_structural_rib_and_exact_x_paths(self) -> None:
        contract = structural_elevation_contract(self.cfg)
        self.assertEqual(contract.structural_crown_extrados_y_mm, 138.0)
        self.assertEqual(contract.structural_crown_intrados_y_mm, 124.0)
        self.assertEqual(contract.structural_spring_extrados_y_mm, 46.0)
        self.assertEqual(contract.structural_rise_mm, 92.0)
        self.assertEqual(contract.visual_crown_extrados_y_mm, 152.0)
        self.assertEqual(contract.wall_upper_node, (0.0, 154.0))
        self.assertEqual(contract.front_spring_node, (144.0, 46.0))
        self.assertEqual(contract.wall_lower_node, (0.0, 30.0))
        self.assertEqual(contract.front_saddle_node, (144.0, 138.0))
        self.assertAlmostEqual(math.dist(contract.wall_upper_node, contract.front_spring_node), 180.0)
        self.assertAlmostEqual(math.dist(contract.wall_lower_node, contract.front_saddle_node), 180.0)
        self.assertAlmostEqual(contract.x_crossing[0], 82.666667, places=6)
        self.assertAlmostEqual(contract.x_crossing[1], 92.0, places=7)
        self.assertAlmostEqual(contract.upper_x_cradle_q_max_mm, 25.383333, places=6)

    def test_spring_joint_moved_as_one_coherent_interface(self) -> None:
        joint = self.cfg["tied_arcade"]["spring_final_x_vertical_joint"]
        self.assertEqual(joint["tenon_final_y_envelope_mm"], [46.0, 68.0])
        self.assertEqual(joint["hard_stop_shoulder_y_envelope_mm"], [42.8, 46.0])
        self.assertEqual(joint["retention_wedge_center_y_mm"], 57.0)
        self.assertEqual(self.cfg["tied_arcade"]["cassette_final_x_vertical_tenon_joint"]["tenon_final_y_envelope_mm"], [138.0, 160.0])
        socket = spring_socket_contract(self.cfg)
        self.assertEqual(socket["interior_socket_centers_mm"], [-14.4, 14.4])
        self.assertEqual(socket["tenon_q_wall_mm"], [145.75, 153.75])
        self.assertEqual(socket["receiver_q_wall_mm"], [145.35, 154.15])
        self.assertEqual(socket["housing_q_wall_mm"], [140.75, 158.75])
        self.assertEqual(socket["nonhousing_descending_xwall_clip_mm"], 140.35)
        self.assertAlmostEqual(socket["nonhousing_to_moving_arch_clearance_mm"], 0.4)
        self.assertEqual(socket["capital_clevis_u_mm"], [0.0, 28.0])
        self.assertEqual(socket["capital_shoulder_e_mm"], [42.8, 46.0])
        self.assertEqual(socket["receiver_housing_e_mm"], [46.0, 68.0])
        self.assertEqual(socket["structural_arc_root_u_e_mm"], [28.8, 46.0])
        housing_end = max(
            abs(value)
            for pair in self.cfg["corbel"]["integrated_bearing_cap"][
                "interior_spring_housing_run_envelopes_mm"
            ]
            for value in pair
        )
        self.assertAlmostEqual(socket["structural_arc_root_u_e_mm"][0] - housing_end, 0.4)
        self.assertAlmostEqual(socket["through_clear_half_run_mm"], 91.9925)
        self.assertAlmostEqual(socket["return_clear_half_run_mm"], 83.56)
        self.assertAlmostEqual(socket["through_arc_radius_mm"], 91.9925003057, places=9)
        self.assertAlmostEqual(socket["through_arc_center_e_mm"], 46.0074996943, places=9)
        self.assertAlmostEqual(socket["return_arc_radius_mm"], 83.9471391304, places=9)
        self.assertAlmostEqual(socket["return_arc_center_e_mm"], 54.0528608696, places=9)
        self.assertFalse(socket["full_height_structural_pier_allowed"])

    def test_redundant_colliding_pier_front_keys_are_deleted(self) -> None:
        joint = self.cfg["joinery"]["front_entablature_joint"]
        self.assertEqual(joint["fixed_crown_tie_key"]["count_full_l"], 9)
        self.assertEqual(joint["floating_pier_seam_alignment_key"]["count_full_l"], 0)
        self.assertEqual(self.cfg["joinery"]["diaphragm_bowtie"]["floating_pier_seam_key_count"], 21)
        self.assertEqual(self.cfg["nominal_geometry_snapshot"]["nominal_part_topology"]["floating_pier_entablature_alignment_keys"], 0)

    def test_saddle_and_lock_preserve_real_axial_travel(self) -> None:
        contract = saddle_thermal_contract(self.cfg)
        self.assertEqual(contract.ridge_width_mm, 10.4)
        self.assertEqual(contract.terminal_pocket_width_mm, 10.8)
        self.assertEqual(contract.floating_pocket_width_mm, 12.0)
        self.assertEqual(contract.ridge_depth_mm, 10.9)
        self.assertEqual(contract.pocket_depth_mm, 11.3)
        self.assertEqual(contract.q_centers_mm, (57.55, 95.45))
        self.assertAlmostEqual(contract.minimum_q_ligament_mm, 3.3)
        self.assertAlmostEqual(contract.ridge_bearing_area_mm2, 113.36)
        self.assertTrue(contract.integrated_cap_installed)
        self.assertEqual(contract.cap_wall_projection_x_mm, (0.0, 144.0))
        self.assertEqual(contract.cap_e_mm, (128.0, 138.0))
        self.assertEqual(contract.cap_base_run_mm, (-24.0, 24.0))
        self.assertEqual(contract.cap_top_run_mm, (-24.0, 24.0))
        self.assertEqual(contract.total_axial_travel_mm, 1.2)
        self.assertEqual(
            (contract.fixed_side, contract.floating_side),
            ("right/outboard/next", "left/cornerward/previous"),
        )

        locks = integrated_cap_lock_contract(self.cfg)
        self.assertEqual(locks["cornerward_center_s_q_mm"], [-18.9, 57.55])
        self.assertEqual(locks["outboard_center_s_q_mm"], [18.9, 95.45])
        self.assertEqual(locks["tight_receiver_run_q_mm"], [3.8, 3.8])
        self.assertEqual(locks["floating_receiver_run_q_mm"], [5.0, 3.8])
        self.assertEqual(locks["pull_head_run_q_mm"], [8.0, 8.0])
        self.assertAlmostEqual(locks["minimum_cap_run_ligament_mm"], 3.2)
        self.assertEqual(locks["straight_service_sweep_mm"], 75.0)
        self.assertTrue(locks["compressed_tail_service_sweep_collision_free"])
        self.assertTrue(locks["expanded_tail_flex_coupon_required"])
        self.assertEqual((locks["count_per_level"], locks["separate_saddles_per_level"], locks["separate_saddle_pins_per_level"]), (22, 0, 0))
        self.assertEqual(locks["run_start_terminal_modes"], ["tight", "tight"])
        self.assertEqual(locks["internal_support_modes"], ["floating_previous", "tight_next"])
        self.assertEqual(locks["run_end_terminal_modes"], ["floating", "floating"])

    def test_crown_bridge_is_one_upward_depth_projecting_joint(self) -> None:
        crown = crown_bridge_contract(self.cfg)
        self.assertEqual(crown.body_u_mm, (-36.0, 36.0))
        self.assertEqual(crown.body_e_mm, (90.0, 138.0))
        self.assertEqual(crown.body_q_mm, (128.0, 134.4))
        self.assertEqual(crown.rail_centers_u_mm, (-28.0, 28.0))
        self.assertEqual(crown.rail_u_envelopes_mm, ((-32.8, -23.2), (23.2, 32.8)))
        self.assertEqual(crown.rail_q_mm, (134.4, 139.2))
        self.assertEqual(crown.keyway_q_mm, (134.4, 139.8))
        self.assertEqual(crown.rail_e_mm, (120.9, 127.9))
        self.assertEqual(crown.keyway_open_e_mm, (72.9, 127.9))
        self.assertEqual(crown.swept_lug_e_mm, (72.9, 127.9))
        self.assertEqual(crown.hard_stop_roof_e_mm, (127.9, 131.231041356))
        self.assertEqual(crown.swept_body_e_mm, (42.0, 138.0))
        self.assertEqual(crown.cassette_underside_e_mm, 138.0)
        self.assertEqual(crown.body_to_cassette_vertical_clearance_mm, 0.0)
        self.assertAlmostEqual(crown.top_receiver_u_clearance_mm, 7.0)
        self.assertAlmostEqual(crown.top_receiver_q_clearance_mm, 4.6)
        self.assertEqual(crown.pin_center_u_e_mm, (9.7, 128.3))
        self.assertEqual(crown.front_ear_q_mm, (134.8, 139.6))
        self.assertEqual(crown.rear_ear_q_mm, (122.8, 127.6))
        self.assertEqual(crown.rear_ear_parent_spine_q_mm, (124.4, 127.6))
        self.assertEqual(crown.rear_ear_parent_union_e_mm, (137.98, 141.2))
        self.assertEqual(crown.rear_ear_parent_spine_e_mm, (138.0, 141.2))
        self.assertEqual(crown.common_parent_rib_e_mm, (120.646226096, 131.231041356))
        self.assertAlmostEqual(crown.worst_case_roof_mm, 3.331041356)
        self.assertAlmostEqual(crown.pin_boss_to_keyway_clearance_mm, 3.4)
        self.assertEqual(crown.pin_split_zone_q_mm, (120.8, 131.0))
        self.assertEqual(crown.pin_unsplit_shaft_q_mm, (130.6, 140.0))
        self.assertEqual(crown.pin_barb_q_mm, (121.6, 122.0))
        self.assertEqual(crown.pin_head_q_mm, (139.6, 142.0))
        self.assertEqual(
            crown.pin_release_window_u_q_e_mm,
            ((5.6, 13.8), (120.4, 122.8), (118.6, 126.3)),
        )
        self.assertEqual(crown.pin_saved_bare_envelope_mm, (21.2, 8.0, 8.0))
        self.assertLess(crown.pin_proxy_strain_fraction, 0.03)
        self.assertEqual(self.cfg["tied_arcade"]["rear_crown_bridge"]["retention_pin_boss_u_envelope_mm"], [0.0, 19.4])
        self.assertEqual(self.cfg["tied_arcade"]["rear_crown_bridge"]["retention_pin_boss_y_envelope_mm"], [118.6, 138.0])
        self.assertFalse(self.cfg["tied_arcade"]["rear_crown_bridge"]["bridge_body_has_downward_tab"])
        rails = self.cfg["tied_arcade"]["rear_crown_bridge"]["dovetail_rails"]
        self.assertEqual(rails["installed_keyway_u_centers_from_nominal_seam_mm"], [-28.0, 28.0])
        self.assertEqual(rails["keyway_source_center_inward_from_physical_crown_face_mm"], 27.825)

    def test_unproven_rail_loop_is_absent_from_baseline(self) -> None:
        rail = rail_baseline_contract(self.cfg)
        self.assertFalse(rail["installed"])
        self.assertEqual(rail["per_level_removed"], 119)
        self.assertEqual(rail["two_level_removed"], 238)
        self.assertTrue(all(value == 0 for value in rail["baseline_counts"].values()))

    def test_diaphragm_keys_and_front_tie_have_positive_retention(self) -> None:
        retained = diaphragm_retention_contract(self.cfg)
        self.assertEqual(retained["mouth_q_envelopes_mm"], [[28.6, 48.6], [66.5, 86.5], [104.4, 124.4]])
        self.assertEqual(retained["keeper_q_envelope_mm"], [28.2, 124.8])
        self.assertAlmostEqual(retained["keeper_q_coverage_reserve_mm"], 0.4)
        self.assertAlmostEqual(retained["keeper_vertical_clearance_mm"], 0.4)
        self.assertEqual(retained["keeper_run_envelope_inward_from_left_physical_face_mm"], [3.2, 15.2])
        self.assertAlmostEqual(retained["x_cradle_to_first_mouth_clearance_mm"], 3.216667, places=6)
        self.assertAlmostEqual(retained["bridge_clearance_mm"], 3.2)
        self.assertAlmostEqual(retained["front_tie_clearance_mm"], 9.6)
        self.assertAlmostEqual(retained["internal_front_service_path_mm"], 27.6)
        self.assertAlmostEqual(retained["minimum_internal_track_q_ligament_mm"], 4.55)
        self.assertEqual(retained["per_level_keeper_count"], 9)
        self.assertEqual(retained["pier_keeper_objects"], 0)
        self.assertEqual(retained["fixed_front_tie_q_envelope_mm"], [134.8, 152.4])
        self.assertEqual(retained["fixed_front_tie_e_envelope_mm"], [138.2, 150.2])
        self.assertEqual(retained["front_tie_to_bridge_vertical_clearance_mm"], 4.0)
        self.assertEqual(retained["complete_objects_per_level"], 258)

    def test_visual_ornament_is_seamed_floating_and_zero_credit(self) -> None:
        ornament = ornament_interface_contract(self.cfg)
        self.assertEqual((ornament.visual_spring_e_mm, ornament.visual_crown_e_mm, ornament.visual_rise_mm), (60.0, 152.0, 92.0))
        self.assertEqual(ornament.visual_seam_mm, 0.6)
        self.assertAlmostEqual(ornament.through_carrier_width_mm, 120.3675)
        self.assertAlmostEqual(ornament.return_carrier_width_mm, 111.935)
        self.assertEqual((ornament.fixed_keyholes, ornament.elongated_keyholes), (1, 2))
        self.assertEqual(ornament.elongated_travel_mm, 1.2)
        self.assertEqual(ornament.parent_union_overlap_mm, 0.02)
        self.assertEqual(ornament.global_depth_offset_mm, 13.2)
        self.assertEqual(ornament.boss_count_per_level, 99)
        self.assertAlmostEqual(ornament.parent_boss_union_volume_mm3, 1.0368)
        self.assertEqual(ornament.gravity_sweep_step_mm, 0.4)
        self.assertEqual(
            ornament.family_map_keys,
            (
                "corner_fixed_rosette",
                "corner_floating_return",
                "ordinary_endcap",
                "pier_overlay",
                "return_carrier_left",
                "return_carrier_right",
                "through_carrier_left",
                "through_carrier_right",
            ),
        )
        self.assertTrue(ornament.connector_placement_complete)
        self.assertTrue(ornament.software_model_mapping_contract_required)
        self.assertFalse(ornament.physical_installation_mapping_qualified)
        self.assertFalse(ornament.production_release_eligible)

    def test_ornament_parent_maps_freeze_exact_haunch_panel_and_sweep_geometry(self) -> None:
        keyholes = self.cfg["palatine"]["ornament_keyhole_contract"]
        mapping = keyholes["per_parent_boss_placement_map"]
        self.assertEqual(keyholes["elongated_receiver_head_run_mm"], 14.0)
        self.assertEqual(keyholes["elongated_receiver_neck_run_mm"], 9.2)
        self.assertEqual(keyholes["boss_count_per_level"], 99)
        self.assertEqual(
            mapping["through_carrier_left"]["locked_boss_centers_parent_local_u_e_mm"],
            [[70.7925, 117.2], [40.2, 117.2], [40.2, 96.4]],
        )
        self.assertEqual(
            mapping["return_carrier_left"]["locked_boss_centers_parent_local_u_e_mm"],
            [[62.76, 117.2], [40.2, 117.2], [40.2, 96.4]],
        )
        floating = mapping["corner_floating_return"]
        self.assertEqual(floating["source_solid_x_envelope_mm"], [0.0, 31.1325])
        self.assertEqual(floating["visible_base_x_envelope_mm"], [0.8, 31.1325])
        self.assertEqual(floating["locked_piece_origin_run_s_mm"], -4.4)
        self.assertEqual(floating["parent_panel_run_envelope_mm"], [0.3, 26.7325])
        self.assertEqual(
            floating["locked_boss_centers_run_s_e_mm"],
            [[6.4, 122.6], [15.9325, 141.0], [6.4, 159.4]],
        )
        for family_id in (
            "through_carrier_left",
            "through_carrier_right",
            "return_carrier_left",
            "return_carrier_right",
        ):
            self.assertEqual(
                mapping[family_id]["carrier_local_receiver_centers_x_y_mm"],
                [
                    list(center)
                    for center in derived_carrier_receiver_centers(
                        self.cfg, family_id
                    )
                ],
            )
        self.assertEqual(
            mapping["pier_overlay"]["carrier_local_receiver_centers_x_y_mm"],
            [[8.8, 9.4], [25.6, 9.4], [17.2, 26.8]],
        )
        self.assertEqual(
            mapping["pier_overlay"]["locked_locator_center_parent_local_run_e_mm"],
            [0.0, 29.8],
        )
        self.assertEqual(
            mapping["pier_overlay"]["parent_interface_plate_q_envelope_mm"],
            [150.8, 152.4],
        )
        self.assertEqual(
            self.cfg["tied_arcade"]["spring_final_x_vertical_joint"]
            ["hard_stop_shoulder_source_z_envelope_mm"],
            [2.0, 18.0],
        )
        self.assertEqual(
            keyholes["overhang_finish_contract"]["standard_physical_finish_width_mm"],
            30.8325,
        )
        self.assertEqual(
            keyholes["strict_collision_gate"]["required_states"],
            [
                "axial_entry_clear",
                "every_0.4_mm_axial_insertion_step",
                "gravity_entry",
                "every_0.4_mm_drop_step",
                "locked",
                "both_run_travel_extremes",
            ],
        )

        stale_nominal_local = copy.deepcopy(self.cfg)
        stale_nominal_local["palatine"]["ornament_keyhole_contract"][
            "per_parent_boss_placement_map"
        ]["through_carrier_left"]["carrier_local_receiver_centers_x_y_mm"][0][0] += 0.3
        with self.assertRaisesRegex(ValueError, "physical-local receiver"):
            ornament_interface_contract(stale_nominal_local)

    def test_corbel_print_path_is_common_face_but_fail_closed(self) -> None:
        printed = corbel_print_contract(self.cfg)
        self.assertEqual(printed["bed_envelope_with_brim_mm"], [180.0, 68.8])
        self.assertEqual(printed["build_height_mm"], 165.95)
        self.assertTrue(printed["per_layer_mesh_gate_required"])
        self.assertFalse(printed["support_free"])
        self.assertFalse(printed["production_mapping_allowed"])

    def test_config_has_no_duplicate_json_keys(self) -> None:
        def reject(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise AssertionError(f"duplicate JSON key: {key}")
                result[key] = value
            return result

        json.loads((R6 / "config.json").read_text(encoding="utf-8"), object_pairs_hook=reject)

    def test_field_corner_gap_accounts_for_every_uncertainty_term(self) -> None:
        cfg = copy.deepcopy(self.cfg)
        with self.assertRaisesRegex(ValueError, "blocked until measured"):
            required_field_corner_gap_mm(cfg)
        corner = cfg["closet"]["inside_corner"]
        corner["field_verified_angle_deg"] = 90.2
        corner["field_verified_max_wall_bow_mm"] = 0.8
        corner["field_verified_corner_datum_uncertainty_mm"] = 0.4
        expected = 0.65 + 165.6 * math.tan(math.radians(0.2)) + 0.8 + 0.4 + 0.6
        self.assertAlmostEqual(required_field_corner_gap_mm(cfg), expected, places=8)
        corner["field_verified_angle_deg"] = 90.2001
        with self.assertRaisesRegex(ValueError, "outside"):
            required_field_corner_gap_mm(cfg)

    def test_physical_crown_face_is_the_feature_datum(self) -> None:
        shift = physical_crown_face_shift_mm(self.cfg)
        self.assertEqual(shift, 0.175)
        x = top_feature_x_from_spring_mm(
            self.cfg,
            nominal_half_span_mm=120.9675,
            u_from_physical_crown_mm=50.0,
        )
        self.assertAlmostEqual(x, 70.7925, places=7)
        # The old nominal-crown expression would miss every receiver by 0.175.
        self.assertAlmostEqual((120.9675 - 50.0) - x, shift, places=7)

    def test_authoritative_saved_to_world_matrix_chain(self) -> None:
        cassette = cassette_saved_to_run_matrix(
            physical_start_s_mm=0.175,
            shelf_depth_mm=152.4,
            cassette_height_mm=30.0,
            cassette_underside_e_mm=138.0,
        )
        # Saved cassette top skin z=0 maps to installed shelf top e=168.
        self.assertTrue(np.allclose(cassette @ np.array([0.0, 0.0, 0.0, 1.0]), [0.175, 152.4, 168.0, 1.0]))
        left = arch_saved_to_run_matrix(
            spring_s_mm=31.4325,
            handedness="left",
            shelf_depth_mm=152.4,
            saved_y_min_installed_mm=42.8,
        )
        right = arch_saved_to_run_matrix(
            spring_s_mm=273.3675,
            handedness="right",
            shelf_depth_mm=152.4,
            saved_y_min_installed_mm=42.8,
        )
        self.assertEqual(left[0, 0], 1.0)
        self.assertEqual(right[0, 0], -1.0)
        world = run_to_world_matrix(
            run_role="through",
            run_start_from_corner_mm=6.35,
            back_clearance_mm=6.35,
            level_top_world_mm=1000.0,
            total_height_mm=168.0,
        )
        spring_world = world @ left @ np.array([0.0, 0.0, 3.0, 1.0])
        self.assertAlmostEqual(spring_world[0], 37.7825, places=7)
        self.assertAlmostEqual(spring_world[1], 155.75, places=7)
        self.assertAlmostEqual(spring_world[2], 874.8, places=7)


if __name__ == "__main__":
    unittest.main()
