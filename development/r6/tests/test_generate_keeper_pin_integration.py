#!/usr/bin/env python3
"""Actual-parent mesh regressions for the fixed-crown keeper pin."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

import generate_all_petg_r6 as generator  # noqa: E402
from design_math import calculate_plan  # noqa: E402


class R6GeneratorKeeperPinIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads((R6 / "config.json").read_text(encoding="utf-8"))
        cls.cassettes, _report = generator.cassette_chassis_family(
            cls.cfg,
            plan=calculate_plan(cls.cfg),
        )
        cls.pins = generator.indexed_crown_retention_pin_parts(
            cls.cfg, selected_levels=2
        )
        cls.pin = next(
            part for part in cls.pins if part.design_metrics["variant_id"] == "keeper_reach"
        )
        cls.front_tie_pin = next(
            part
            for part in cls.pins
            if part.design_metrics["variant_id"] == "front_tie_reach"
        )
        cls.keeper_strip = generator.fixed_crown_diaphragm_keeper_strip(
            cls.cfg, selected_levels=2
        )
        cls.front_tie = next(
            part
            for part in generator.seam_keys(cls.cfg)
            if part.design_metrics.get("positive_q_axis_pin_eye_generated")
        )

    def test_keeper_reach_pin_has_real_parent_receiver_and_complete_reversible_sweep(self) -> None:
        pin = self.pin
        self.assertTrue(pin.mesh.is_watertight)
        self.assertEqual(pin.mesh.body_count, 1)
        self.assertTrue(
            np.allclose(pin.mesh.extents, [14.2, 8.0, 3.2], atol=1.0e-5)
        )
        self.assertEqual(pin.design_metrics["variant_id"], "keeper_reach")
        self.assertFalse(
            pin.design_metrics["prohibited_front_tie_vertical_variant_emitted"]
        )

        self.assertEqual(
            [part.design_metrics["variant_id"] for part in self.pins],
            ["keeper_reach", "front_tie_reach"],
        )
        front_tie = self.pins[1]
        self.assertTrue(front_tie.mesh.is_watertight)
        self.assertEqual(front_tie.mesh.body_count, 1)
        self.assertTrue(
            np.allclose(front_tie.mesh.extents, [15.2, 8.0, 3.2], atol=1.0e-5)
        )
        self.assertFalse(front_tie.design_metrics["prohibited_vertical_variant_emitted"])

        owners = [
            part
            for part in self.cassettes
            if part.design_metrics["fixed_crown_keeper_pin_receiver_generated"]
        ]
        self.assertEqual(len(owners), 9)
        for cassette in owners:
            receiver = cassette.design_metrics["fixed_crown_keeper_pin_receiver"]
            self.assertEqual(
                receiver["rotation_chamber_residual_solid_volume_mm3"], 0.0
            )
            self.assertGreater(
                receiver["capture_roof_probe_occupied_volume_mm3"], 0.0
            )
            self.assertGreater(
                receiver["parent_floor_probe_occupied_volume_mm3"], 0.0
            )

        report = generator.validate_keeper_pin_parent_sweeps(
            self.cfg,
            cassettes=self.cassettes,
            keeper_pin=pin,
        )
        self.assertEqual(report["owning_cassette_count"], 9)
        self.assertEqual(report["entry_or_withdraw_translation_station_count"], 29)
        self.assertEqual(report["quarter_turn_or_inverse_angle_station_count"], 91)
        self.assertEqual(report["index_seat_or_release_station_count"], 5)
        self.assertEqual(
            report["real_parent_collision_free_boolean_pair_count"],
            9 * (29 + 91 + 5),
        )
        self.assertEqual(report["wrong_way_hard_index_collision_count"], 9)
        self.assertGreater(
            report["minimum_wrong_way_index_collision_volume_mm3"], 1.0e-3
        )
        self.assertTrue(report["inverse_removal_uses_exact_reversed_states"])
        self.assertFalse(report["front_tie_vertical_variant_included"])

    def test_keeper_rear_bayonet_strip_and_real_track_complete_the_inverse_path(self) -> None:
        strip = self.keeper_strip
        self.assertTrue(strip.mesh.is_watertight)
        self.assertEqual(strip.mesh.body_count, 1)
        self.assertTrue(
            np.allclose(strip.mesh.extents, [96.6, 12.0, 10.0], atol=1.0e-5)
        )
        owners = [
            part
            for part in self.cassettes
            if part.design_metrics["fixed_crown_keeper_pin_receiver_generated"]
        ]
        self.assertEqual(len(owners), 9)
        for cassette in owners:
            receiver = cassette.design_metrics["fixed_crown_keeper_pin_receiver"]
            self.assertTrue(receiver["rear_bayonet_strip_receiver_embodied"])
            self.assertFalse(receiver["rear_bayonet_front_tongue_emitted"])
            self.assertEqual(
                receiver[
                    "rear_bayonet_head_chamber_residual_solid_volume_mm3"
                ],
                0.0,
            )
            self.assertGreater(
                receiver[
                    "rear_bayonet_capture_roof_probe_occupied_volume_mm3"
                ],
                0.0,
            )

        report = generator.validate_keeper_strip_parent_sweeps(
            self.cfg,
            cassettes=self.cassettes,
            keeper_strip=strip,
            keeper_pin=self.pin,
        )
        self.assertEqual(report["owning_cassette_count"], 9)
        self.assertEqual(report["lift_station_count"], 18)
        self.assertEqual(report["rearward_slide_station_count"], 11)
        self.assertEqual(
            report["real_parent_collision_free_boolean_pair_count"],
            9 * 2 * (18 + 11),
        )
        self.assertEqual(report["pin_blocked_full_forward_slide_count"], 9)
        self.assertGreater(
            report["minimum_pin_blocking_overlap_volume_mm3"], 1.0e-3
        )
        self.assertTrue(report["inverse_removal_uses_exact_reversed_states"])
        self.assertFalse(report["front_tongue_emitted"])

    def test_visible_front_tie_and_q_axis_pin_have_exact_real_parent_sweeps(self) -> None:
        owners = [
            part
            for part in self.cassettes
            if part.design_metrics[
                "fixed_crown_front_tie_pin_receiver_generated"
            ]
        ]
        self.assertEqual(len(owners), 9)
        for cassette in owners:
            receiver = cassette.design_metrics[
                "fixed_crown_front_tie_pin_receiver"
            ]
            self.assertEqual(
                receiver["rotation_chamber_residual_solid_volume_mm3"], 0.0
            )
            self.assertGreater(
                receiver["rear_capture_wall_probe_occupied_volume_mm3"], 0.0
            )
            self.assertTrue(
                receiver["receiver_boss_protected_in_original_blank"]
            )

        report = generator.validate_front_tie_pin_parent_sweeps(
            self.cfg,
            cassettes=self.cassettes,
            front_tie=self.front_tie,
            front_tie_pin=self.front_tie_pin,
        )
        self.assertEqual(report["owning_cassette_count"], 9)
        self.assertEqual(report["front_tie_translation_station_count"], 46)
        self.assertEqual(report["pin_translation_station_count"], 32)
        self.assertEqual(report["pin_rotation_station_count"], 91)
        self.assertEqual(report["pin_seating_station_count"], 3)
        self.assertEqual(
            report["real_parent_tie_collision_free_boolean_pair_count"],
            9 * 46 * 2,
        )
        self.assertEqual(
            report["real_parent_pin_collision_free_boolean_pair_count"],
            9 * (32 + 91 + 3) * 3,
        )
        self.assertEqual(report["wrong_way_hard_index_collision_count"], 9)
        self.assertFalse(report["prohibited_vertical_front_tie_variant_included"])


if __name__ == "__main__":
    unittest.main()
