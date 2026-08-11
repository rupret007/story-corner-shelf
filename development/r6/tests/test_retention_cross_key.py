#!/usr/bin/env python3
"""Focused fail-closed tests for the universal r6 positive cross-key."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import sys
import unittest


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from retention_cross_key import (  # noqa: E402
    crossbar_corners_at_rotation,
    key_transform_q,
    positive_retention_cross_key_contract,
)


def load_config() -> dict:
    return json.loads((R6 / "config.json").read_text(encoding="utf-8"))


class PositiveRetentionCrossKeyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = load_config()

    def test_exact_contract_preserves_ligaments_counts_and_zero_credit(self) -> None:
        contract = positive_retention_cross_key_contract(self.cfg)
        self.assertEqual(contract.family_id, "positive_quarter_turn_cross_key")
        self.assertEqual(contract.top_tenon_ligament_run_y_mm, (7.0, 9.0))
        self.assertEqual(contract.spring_tenon_ligament_run_y_mm, (8.0, 9.0))
        self.assertAlmostEqual(contract.shaft_radial_clearance_mm, 0.4)
        self.assertEqual(contract.keys_per_level, 54)
        self.assertEqual(contract.keys_selected_two_levels, 108)
        self.assertIn("zero vertical", contract.load_credit)
        self.assertAlmostEqual(contract.exact_insertion_translation_mm, 27.2)
        self.assertEqual(contract.exact_locking_rotation_deg, 90.0)

    def test_exact_crossbar_corner_sweep_fits_the_rotation_chamber(self) -> None:
        contract = positive_retention_cross_key_contract(self.cfg)
        key = self.cfg["tied_arcade"]["retention_wedge"]
        crossbar = key["crossbar"]
        chamber_radius = key["front_bayonet_boss"]["rotation_chamber_diameter_mm"] / 2.0
        observed_radius = 0.0
        for step in range(901):
            angle = step / 10.0
            for u, y in crossbar_corners_at_rotation(
                crossbar["actual_long_span_mm"],
                crossbar["actual_short_span_mm"],
                angle,
            ):
                observed_radius = max(observed_radius, math.hypot(u, y))
                self.assertLessEqual(math.hypot(u, y), chamber_radius)
        self.assertAlmostEqual(observed_radius, contract.crossbar_corner_sweep_radius_mm)
        self.assertAlmostEqual(contract.chamber_radial_sweep_clearance_mm, 0.4565835097474311)

    def test_service_matrices_are_exact_inverse_entry_lock_and_withdrawal(self) -> None:
        contract = positive_retention_cross_key_contract(self.cfg)
        expected_locked = key_transform_q(90.0, 0.0)
        expected_withdrawn = key_transform_q(0.0, -27.2)
        self.assertEqual(contract.kinematic_stage_matrices["positively_indexed_locked"], expected_locked)
        for actual_row, expected_row in zip(
            contract.kinematic_stage_matrices["visible_front_withdrawn"],
            expected_withdrawn,
        ):
            for actual, expected in zip(actual_row, expected_row):
                self.assertAlmostEqual(actual, expected)
        self.assertAlmostEqual(expected_locked[0][1], -1.0)
        self.assertAlmostEqual(expected_locked[1][0], 1.0)

    def test_gate_capture_latch_and_print_orientation_are_positive_and_compact(self) -> None:
        contract = positive_retention_cross_key_contract(self.cfg)
        self.assertAlmostEqual(contract.gate_capture_overlap_each_lug_mm, 2.5)
        self.assertAlmostEqual(contract.locked_index_notch_residual_wall_mm, 3.2)
        self.assertAlmostEqual(contract.chamber_axial_clearance_mm, 0.8)
        self.assertAlmostEqual(contract.maximum_installed_outward_float_mm, 0.4)
        self.assertAlmostEqual(contract.minimum_latch_engagement_at_outward_float_mm, 0.8)
        self.assertAlmostEqual(contract.release_clearance_mm, 0.4)
        self.assertEqual(contract.conservative_flexure_strain_length_mm, 20.0)
        for actual, expected in zip(
            contract.authored_folded_u_centerline_segments_mm,
            (17.1, 1.6, 7.1),
        ):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(contract.authored_folded_u_centerline_length_mm, 25.8)
        self.assertLess(contract.nominal_flexure_outer_fiber_strain, 0.03)
        self.assertEqual(contract.saved_bare_envelope_mm, (27.2, 19.2, 3.2))
        self.assertEqual(contract.saved_brim_envelope_mm, (39.2, 31.2, 3.2))
        self.assertTrue(all(value <= 180.0 for value in contract.saved_brim_envelope_mm))

    def test_bore_growth_below_seven_mm_top_ligament_fails_closed(self) -> None:
        bad = copy.deepcopy(self.cfg)
        key = bad["tied_arcade"]["retention_wedge"]
        key["tenon_through_bore_diameter_mm"] = 4.2
        key["through_hole_run_y_mm"] = [4.2, 4.2]
        with self.assertRaisesRegex(ValueError, "below 7 mm"):
            positive_retention_cross_key_contract(bad)

    def test_pull_feature_and_conservative_flexure_path_fail_closed(self) -> None:
        bad_pull = copy.deepcopy(self.cfg)
        bad_pull["tied_arcade"]["retention_wedge"][
            "visible_handle_and_positive_index"
        ]["minimum_pull_feature_mm"] = 19.8
        with self.assertRaisesRegex(ValueError, "minimum pull feature span"):
            positive_retention_cross_key_contract(bad_pull)

        bad_path = copy.deepcopy(self.cfg)
        bad_path["tied_arcade"]["retention_wedge"][
            "visible_handle_and_positive_index"
        ]["integral_u_flexure_developed_length_mm"] = 25.9
        with self.assertRaisesRegex(ValueError, "exceeds the authored folded-U"):
            positive_retention_cross_key_contract(bad_path)

    def test_each_folded_u_authored_component_datum_is_enforced(self) -> None:
        fields = (
            "root_width_u_mm",
            "dog_width_u_mm",
            "dog_inset_from_handle_end_u_mm",
            "open_slot_q_mm",
            "shaft_spine_neck_width_u_mm",
            "neck_q_thickness_mm",
            "neck_shaft_positive_union_q_mm",
            "dog_front_beam_positive_union_q_mm",
            "dog_rear_latch_projection_q_mm",
            "dog_total_q_depth_mm",
        )
        for field in fields:
            with self.subTest(field=field):
                bad = copy.deepcopy(self.cfg)
                geometry = bad["tied_arcade"]["retention_wedge"][
                    "visible_handle_and_positive_index"
                ]["folded_u_authored_geometry"]
                geometry[field] = float(geometry[field]) + 0.1
                with self.assertRaises(ValueError):
                    positive_retention_cross_key_contract(bad)

    def test_undersized_rotation_chamber_fails_full_corner_sweep(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["tied_arcade"]["retention_wedge"]["front_bayonet_boss"]["rotation_chamber_diameter_mm"] = 10.2
        with self.assertRaisesRegex(ValueError, "clear every crossbar corner"):
            positive_retention_cross_key_contract(bad)

    def test_thin_boss_or_lost_gate_capture_fails_closed(self) -> None:
        thin = copy.deepcopy(self.cfg)
        thin["tied_arcade"]["retention_wedge"]["front_bayonet_boss"]["outer_run_y_mm"] = [16.6, 16.6]
        with self.assertRaisesRegex(ValueError, "minimum outer wall"):
            positive_retention_cross_key_contract(thin)

        notched_thin = copy.deepcopy(self.cfg)
        notched_thin["tied_arcade"]["retention_wedge"]["front_bayonet_boss"]["outer_run_y_mm"][0] = 18.8
        with self.assertRaisesRegex(ValueError, "notch"):
            positive_retention_cross_key_contract(notched_thin)

        uncaptured = copy.deepcopy(self.cfg)
        uncaptured["tied_arcade"]["retention_wedge"]["front_bayonet_boss"]["vertical_entry_slot_run_y_mm"][0] = 9.0
        with self.assertRaises(ValueError):
            positive_retention_cross_key_contract(uncaptured)

    def test_friction_only_or_inadequate_release_fails_closed(self) -> None:
        friction = copy.deepcopy(self.cfg)
        friction["tied_arcade"]["retention_wedge"]["visible_handle_and_positive_index"]["anti_rotation_rule"] = "friction detent"
        with self.assertRaisesRegex(ValueError, "unique positive"):
            positive_retention_cross_key_contract(friction)

        trapped = copy.deepcopy(self.cfg)
        trapped["tied_arcade"]["retention_wedge"]["visible_handle_and_positive_index"]["front_release_deflection_mm"] = 1.4
        with self.assertRaises(ValueError):
            positive_retention_cross_key_contract(trapped)

    def test_hidden_access_or_noninverse_removal_fails_closed(self) -> None:
        hidden = copy.deepcopy(self.cfg)
        hidden["tied_arcade"]["retention_wedge"]["exact_service_kinematics"]["forbidden_access"].remove("wall/rear")
        with self.assertRaisesRegex(ValueError, "hidden"):
            positive_retention_cross_key_contract(hidden)

        wrong_motion = copy.deepcopy(self.cfg)
        wrong_motion["tied_arcade"]["retention_wedge"]["exact_service_kinematics"]["removal_translation_q_mm"] = -20.4
        with self.assertRaisesRegex(ValueError, "removal translation"):
            positive_retention_cross_key_contract(wrong_motion)

    def test_unqualified_orientation_cycle_thermal_and_migration_fail_closed(self) -> None:
        production = copy.deepcopy(self.cfg)
        production["tied_arcade"]["retention_wedge"]["saved_print_orientation"]["production_orientation_allowed"] = True
        with self.assertRaisesRegex(ValueError, "may not be production-qualified"):
            positive_retention_cross_key_contract(production)

        cycles = copy.deepcopy(self.cfg)
        cycles["tied_arcade"]["retention_wedge"]["qualification_gate"]["minimum_full_insert_lock_release_remove_cycles"] = 99
        with self.assertRaisesRegex(ValueError, "below 100"):
            positive_retention_cross_key_contract(cycles)

        migration = copy.deepcopy(self.cfg)
        migration["tied_arcade"]["retention_wedge"]["qualification_gate"]["migration_dwell_days"] = [30]
        with self.assertRaisesRegex(ValueError, "90-day"):
            positive_retention_cross_key_contract(migration)

    def test_object_topology_must_remain_one_key_per_interface(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["tied_arcade"]["retention_wedge"]["object_count_contract"]["additional_keeper_objects"] = 54
        with self.assertRaisesRegex(ValueError, "54/108"):
            positive_retention_cross_key_contract(bad)


if __name__ == "__main__":
    unittest.main()
