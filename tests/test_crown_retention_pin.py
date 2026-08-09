#!/usr/bin/env python3
"""Focused source-contract tests for keeper/tie quarter-turn pins."""

from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from crown_retention_pin import (  # noqa: E402
    crown_retention_pin_contract,
    pin_transform_e,
    pin_transform_q,
)


def load_config() -> dict:
    return json.loads((R6 / "config.json").read_text(encoding="utf-8"))


class CrownRetentionPinTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = load_config()
        cls.contract = crown_retention_pin_contract(cls.cfg)

    def test_one_shared_family_has_two_exact_reach_variants(self) -> None:
        contract = self.contract
        self.assertEqual(contract.family_id, "indexed_vertical_quarter_turn_pin")
        self.assertEqual(contract.shaft_diameter_mm, 3.2)
        self.assertEqual(contract.shaft_bore_diameter_mm, 4.0)
        self.assertEqual(contract.tail_long_short_axial_mm, (7.2, 3.2, 2.4))
        self.assertEqual(contract.entry_gate_long_short_mm, (8.0, 4.0))
        self.assertEqual(contract.chamber_u_q_axial_mm, (8.8, 8.8, 3.6))
        self.assertEqual(contract.flat_pull_bar_long_short_axial_mm, (8.0, 3.2, 3.2))
        self.assertEqual(contract.keeper.variant_id, "keeper_reach")
        self.assertEqual(contract.front_tie.variant_id, "front_tie_reach")

    def test_crown_bridge_pin_saved_orientation_is_explicitly_unqualified(self) -> None:
        saved = self.cfg["tied_arcade"]["rear_crown_bridge"][
            "retention_pin_positive_tail_contract"
        ]
        orientation = saved["saved_orientation"]
        self.assertIn("shaft axis parallel", orientation)
        self.assertIn("split plane perpendicular", orientation)
        self.assertIn("round head", orientation)
        self.assertFalse(saved["support_free_claim_allowed"])
        self.assertFalse(saved["production_orientation_allowed"])

    def test_tail_passes_entry_rotates_and_cannot_withdraw_when_locked(self) -> None:
        contract = self.contract
        self.assertAlmostEqual(contract.entry_clearance_each_face_mm, 0.4)
        self.assertAlmostEqual(contract.shaft_radial_clearance_mm, 0.4)
        self.assertAlmostEqual(contract.locked_capture_overlap_each_side_mm, 1.6)
        expected_half_extent = math.hypot(7.2 / 2.0, 3.2 / 2.0)
        self.assertAlmostEqual(contract.maximum_rotating_half_extent_mm, expected_half_extent)
        self.assertAlmostEqual(
            contract.minimum_rotation_chamber_clearance_mm,
            8.8 / 2.0 - expected_half_extent,
        )
        self.assertGreater(contract.minimum_rotation_chamber_clearance_mm, 0.4)

    def test_hard_index_has_exact_unlock_and_ceiling_reserve(self) -> None:
        contract = self.contract
        self.assertEqual(contract.unlock_push_e_mm, 0.8)
        self.assertEqual(contract.index_nub_height_mm, 0.6)
        self.assertEqual(contract.index_pocket_depth_mm, 0.8)
        self.assertAlmostEqual(contract.index_clearance_after_push_mm, 0.2)
        self.assertAlmostEqual(contract.tail_ceiling_clearance_during_rotation_mm, 0.4)
        rule = self.cfg["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "shared_pin_geometry"
        ]["single_index_nub"]["wrong_way_rule"]
        self.assertIn("only the positive locked long-axis position", rule)
        self.assertIn("visibly proud by 0.6 mm", rule)

    def test_keeper_uses_one_rear_tongue_and_one_pin_at_clear_gap(self) -> None:
        keeper = self.contract.keeper
        self.assertEqual(keeper.center_u_q_mm, (9.2, 95.45))
        self.assertEqual(keeper.entry_gate_u_q_mm, ((7.2, 11.2), (91.45, 99.45)))
        self.assertEqual(keeper.chamber_u_q_mm, ((4.8, 13.6), (91.05, 99.85)))
        self.assertAlmostEqual(keeper.minimum_external_collision_clearance_mm, 4.55)
        raw = self.cfg["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "keeper_reach_variant"
        ]
        self.assertTrue(raw["rear_bayonet_tongue_retained"])
        self.assertFalse(raw["front_tongue_emitted"])
        self.assertEqual(
            self.cfg["joinery"]["diaphragm_bowtie"]["positive_retention"]
            ["internal_upward_bayonet_track"]["front_track_status"].split(";", 1)[0],
            "RETIRED_AS_A_TONGUE",
        )

    def test_keeper_e_stack_preserves_floor_roof_and_handle_push(self) -> None:
        keeper = self.contract.keeper
        self.assertEqual(keeper.entry_throat_e_mm, (138.0, 142.0))
        self.assertEqual(keeper.index_pocket_e_mm, (141.2, 142.0))
        self.assertEqual(keeper.chamber_e_mm, (142.0, 145.6))
        self.assertEqual(keeper.roof_e_mm, (145.6, 148.8))
        self.assertEqual(keeper.tail_body_e_mm, (142.0, 144.4))
        self.assertEqual(keeper.index_nub_e_mm, (141.4, 142.0))
        self.assertEqual(keeper.handle_e_mm, (130.2, 133.4))
        self.assertEqual(keeper.shaft_e_mm, (133.0, 142.4))
        self.assertEqual(keeper.minimum_parent_floor_after_pocket_mm, 3.2)
        self.assertEqual(keeper.bare_saved_envelope_mm, (14.2, 8.0, 3.2))

    def test_front_tie_q_axis_clears_arch_ear_keyway_and_eye_walls(self) -> None:
        tie = self.contract.front_tie
        self.assertEqual(tie.center_u_e_mm, (14.0, 145.6))
        self.assertEqual(tie.entry_gate_u_e_mm, ((10.0, 18.0), (143.6, 147.6)))
        self.assertEqual(tie.chamber_u_e_mm, ((9.6, 18.4), (141.2, 150.0)))
        self.assertEqual(tie.chamber_q_mm, (140.0, 143.6))
        self.assertEqual(tie.tie_eye_u_e_mm, ((6.8, 21.2), (140.4, 150.8)))
        self.assertEqual(tie.receiver_eye_u_e_mm, ((6.6, 21.4), (140.2, 151.0)))
        self.assertAlmostEqual(tie.minimum_external_collision_clearance_mm, 0.4)
        raw = self.cfg["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "front_tie_reach_variant"
        ]
        self.assertAlmostEqual(raw["minimum_chamber_to_crown_ear_q_clearance_mm"], 0.4)
        self.assertAlmostEqual(raw["minimum_chamber_to_crown_keyway_u_clearance_mm"], 4.4)
        self.assertAlmostEqual(raw["minimum_chamber_bottom_to_arch_extrados_mm"], 3.2)
        self.assertAlmostEqual(raw["installed_head_to_shelf_front_gap_mm"], 0.8)

    def test_front_tie_q_stack_preserves_capture_and_visible_pull_bar(self) -> None:
        tie = self.contract.front_tie
        self.assertEqual(tie.rear_capture_wall_q_mm, (136.8, 140.0))
        self.assertEqual(tie.entry_throat_q_mm, (143.6, 152.4))
        self.assertEqual(
            tie.tail_body_u_e_q_mm,
            ((12.4, 15.6), (142.0, 149.2), (141.2, 143.6)),
        )
        self.assertEqual(
            tie.index_nub_u_e_q_mm,
            ((12.8, 15.2), (147.6, 149.2), (143.6, 144.2)),
        )
        self.assertEqual(
            tie.index_pocket_u_e_q_mm,
            ((12.6, 15.4), (147.4, 149.4), (143.6, 144.4)),
        )
        self.assertEqual(tie.shaft_q_mm, (143.2, 153.6))
        self.assertEqual(
            tie.pull_bar_u_e_q_mm,
            ((12.4, 15.6), (141.6, 149.6), (153.2, 156.4)),
        )
        self.assertEqual(tie.bare_saved_envelope_mm, (15.2, 8.0, 3.2))

    def test_exact_install_and_removal_transforms_are_inverses(self) -> None:
        keeper = self.contract.keeper
        self.assertEqual(keeper.clear_approach_translation_e_mm, -10.4)
        self.assertEqual(keeper.insertion_translation_e_mm, 11.2)
        matrices = keeper.kinematic_stage_matrices
        self.assertEqual(matrices["clear_approach_entry_index"], pin_transform_e(0.0, -10.4))
        self.assertEqual(matrices["inserted_unindexed"], pin_transform_e(0.0, 0.8))
        self.assertEqual(matrices["rotated_unseated"], pin_transform_e(90.0, 0.8))
        self.assertEqual(matrices["positively_indexed_locked"], pin_transform_e(90.0, 0.0))

        tie = self.contract.front_tie
        self.assertEqual(tie.clear_approach_translation_q_mm, 11.6)
        self.assertEqual(tie.insertion_to_rotation_translation_q_mm, -12.4)
        matrices = tie.kinematic_stage_matrices
        self.assertEqual(matrices["clear_approach_entry_index"], pin_transform_q(0.0, 11.6))
        self.assertEqual(matrices["inserted_unindexed"], pin_transform_q(0.0, -0.8))
        self.assertEqual(matrices["rotated_unseated"], pin_transform_q(-90.0, -0.8))
        self.assertEqual(matrices["positively_indexed_locked"], pin_transform_q(-90.0, 0.0))
        self.assertEqual(matrices["removal_entry_index"], pin_transform_q(0.0, -0.8))
        self.assertEqual(matrices["removed_clear"], pin_transform_q(0.0, 11.6))

    def test_rotation_matrix_maps_entry_q_axis_to_locked_u_axis(self) -> None:
        locked = pin_transform_e(90.0, 0.0)
        self.assertEqual(locked[0], (0.0, -1.0, 0.0, 0.0))
        self.assertEqual(locked[1], (1.0, 0.0, 0.0, 0.0))
        self.assertEqual(locked[2], (0.0, 0.0, 1.0, 0.0))

    def test_physical_gates_and_zero_credit_remain_explicit(self) -> None:
        contract = self.contract
        self.assertEqual(contract.physical_cycle_count_each_variant, 100)
        self.assertEqual(contract.migration_dwell_days, (30, 90))
        self.assertTrue(contract.software_model_mapping_contract_required)
        self.assertFalse(contract.physical_installation_mapping_qualified)
        self.assertFalse(contract.production_release_eligible)
        raw = self.cfg["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"]
        self.assertIn("zero vertical", raw["retention_credit"])
        self.assertIn("no numerical load rating", raw["retention_credit"])
        gate = raw["software_model_mapping_completion_gate"]
        self.assertIn("runtime generator", gate)
        self.assertIn("actual-parent", gate)
        self.assertIn("solid insertion/rotation/removal booleans", gate)
        self.assertIn("software_model_mapping_complete true", gate)
        self.assertEqual(len(raw["fixed_crown_interface_assembly_sequence"]), 7)
        self.assertIn("keeper-reach pin", raw["fixed_crown_interface_assembly_sequence"][2])
        self.assertIn("front-tie-reach pin", raw["fixed_crown_interface_assembly_sequence"][4])
        self.assertIn("fully unload", raw["fixed_crown_interface_disassembly_rule"])

    def test_object_count_impact_is_exact_and_logical_inventory_is_integrated(self) -> None:
        contract = self.contract
        self.assertEqual(contract.additional_objects_per_level, 18)
        self.assertEqual(contract.additional_objects_two_levels, 36)
        self.assertEqual(contract.projected_complete_objects_per_level, 258)
        self.assertEqual(contract.projected_complete_objects_two_levels, 516)
        status = self.cfg["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "object_count_impact_contract"
        ]["inventory_update_status"]
        self.assertTrue(status.startswith("LOGICAL_INVENTORY_AND_PACKAGE_PLANS_INTEGRATED"))
        self.assertIn("runtime generator proves", status)
        self.assertIn("physical installation and production remain unqualified", status)

    def test_original_4_8_mm_shaft_is_rejected_by_4_mm_gate(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "shared_pin_geometry"
        ]["shaft_diameter_mm"] = 4.8
        with self.assertRaisesRegex(ValueError, "cannot pass the entry gate"):
            crown_retention_pin_contract(bad)

    def test_too_small_rotation_chamber_is_rejected(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "shared_pin_geometry"
        ]["rotation_chamber_u_q_mm"] = [7.8, 7.8]
        with self.assertRaisesRegex(ValueError, "tail rotation clearance"):
            crown_retention_pin_contract(bad)

    def test_thinned_front_tie_eye_wall_is_rejected(self) -> None:
        bad = copy.deepcopy(self.cfg)
        bad["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "front_tie_reach_variant"
        ]["tie_integral_eye_u_e_envelopes_mm"] = [[7.0, 21.2], [140.4, 150.8]]
        bad["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "front_tie_reach_variant"
        ]["local_original_tie_body_trim_u_e_q_envelopes_mm"][0] = [7.0, 21.2]
        with self.assertRaisesRegex(ValueError, "local eye wall"):
            crown_retention_pin_contract(bad)

    def test_wrong_way_or_friction_only_contract_is_rejected(self) -> None:
        wrong_way = copy.deepcopy(self.cfg)
        wrong_way["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "shared_pin_geometry"
        ]["single_index_nub"]["wrong_way_rule"] = "either orientation may seat"
        with self.assertRaisesRegex(ValueError, "wrong-way orientation"):
            crown_retention_pin_contract(wrong_way)

        friction = copy.deepcopy(self.cfg)
        friction["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "exact_service_kinematics"
        ]["forbidden_access"].remove("friction-only retention")
        with self.assertRaisesRegex(ValueError, "friction retention"):
            crown_retention_pin_contract(friction)

    def test_mapping_state_split_cannot_be_weakened_from_source_metadata(self) -> None:
        mutations = (
            ("software_model_mapping_contract_required", False, "runtime software-model"),
            ("physical_installation_mapping_qualified", True, "not physically"),
            ("production_release_eligible", True, "not production-release"),
        )
        for field, value, error in mutations:
            with self.subTest(field=field):
                bad = copy.deepcopy(self.cfg)
                bad["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
                    field
                ] = value
                with self.assertRaisesRegex(ValueError, error):
                    crown_retention_pin_contract(bad)

    def test_coupon_cycles_and_migration_cannot_be_weakened(self) -> None:
        cycles = copy.deepcopy(self.cfg)
        cycles["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "qualification_gate"
        ]["minimum_full_insert_push_rotate_seat_release_cycles_each_variant"] = 99
        with self.assertRaisesRegex(ValueError, "at least 100"):
            crown_retention_pin_contract(cycles)

        migration = copy.deepcopy(self.cfg)
        migration["joinery"]["shared_keeper_and_front_tie_quarter_turn_pin"][
            "qualification_gate"
        ]["migration_dwell_days"] = [30]
        with self.assertRaisesRegex(ValueError, "30- and 90-day"):
            crown_retention_pin_contract(migration)


if __name__ == "__main__":
    unittest.main()
