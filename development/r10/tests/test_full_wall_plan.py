from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


R10_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R10_ROOT))

import capacity_study  # noqa: E402
import full_wall_plan  # noqa: E402


class FullWallPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = capacity_study.load_config()
        cls.plan = full_wall_plan.build_plan(cls.config)

    def test_support_roles_and_short_visible_corbels_are_exact(self) -> None:
        stations = self.plan["support_stations"]
        self.assertEqual(len(stations), 7)
        self.assertEqual([item["center_mm"] for item in stations], [
            15.875, 269.875, 523.875, 777.875, 1031.875, 1285.875, 1539.875
        ])
        self.assertTrue(stations[0]["cable_receiver_present"])
        self.assertEqual(stations[0]["visible_corbel_drop_mm"], 120.65)
        self.assertEqual(stations[-1]["visible_corbel_drop_mm"], 0.0)
        self.assertEqual(
            stations[-1]["role"], "through_side_terminal_corner_placeholder"
        )
        self.assertEqual(
            [item["visible_corbel_drop_mm"] for item in stations[1:6]], [76.2] * 5
        )
        self.assertTrue(all(item["full_structural_strap_drop_mm"] == 158.75 for item in stations))

    def test_six_independent_bays_close_the_measured_wall(self) -> None:
        bays = self.plan["bay_stations"]
        self.assertEqual(len(bays), 6)
        self.assertEqual([item["midpoint_seam_mm"] for item in bays], [
            142.875, 396.875, 650.875, 904.875, 1158.875, 1412.875
        ])
        self.assertEqual(bays[0]["left_half_length_mm"], 142.35)
        self.assertEqual(bays[-1]["right_half_length_mm"], 142.35)
        for bay in bays:
            self.assertEqual(bay["splice_log_count"], 3)
            self.assertEqual(bay["midpoint_retention_key_count"], 3)
            self.assertEqual(bay["midpoint_seam_gap_mm"], 0.35)
            self.assertGreater(bay["splice_log_span_mm"][0], bay["left_support_center_mm"])
            self.assertLess(bay["splice_log_span_mm"][1], bay["right_support_center_mm"])

    def test_counts_include_all_keys_and_cable_modules(self) -> None:
        self.assertEqual(self.plan["printed_part_counts"], {
            "load_bearing_supports": 7,
            "cassette_halves": 12,
            "splice_logs": 18,
            "independent_log_retainers": 18,
            "bay_local_support_retainers": 12,
            "first_wall_cable_modules": 3,
            "total_first_wall_articles_including_cable_modules": 70,
        })
        self.assertEqual(self.plan["hardware_candidate_counts"]["grk_90306_installed"], 21)
        self.assertEqual(
            self.plan["hardware_candidate_counts"]["dottie_fw14_installed"], 21
        )
        self.assertEqual(
            self.plan["hardware_candidate_counts"][
                "grk_90306_initial_controlled_lot_buy"
            ],
            100,
        )
        self.assertEqual(
            self.plan["hardware_candidate_counts"][
                "dottie_fw14_initial_controlled_lot_buy"
            ],
            100,
        )
        self.assertEqual(
            self.plan["hardware_candidate_counts"]["minimum_reserved_before_retests"],
            96,
        )
        self.assertEqual(
            self.plan["qualification_scale_counts"],
            {
                "measurement_stations": 19,
                "measurement_station_formula": "2 * 6 bay midpoints + 7 supports",
                "minimum_full_size_articles_before_coupons_retests_or_spares": 284,
                "minimum_full_size_article_formula": "70 + 4 + 3 * 70",
            },
        )

    def test_target_demand_is_incomplete_and_never_a_capacity(self) -> None:
        demand = self.plan["target_demand_not_capacity"]
        self.assertEqual(demand["distributed_contents_force_n"], 441.29925)
        self.assertEqual(demand["front_edge_point_force_n"], 88.25985)
        self.assertEqual(demand["conservative_support_reaction_n_excluding_dead_mass"], 161.809725)
        self.assertEqual(demand["conservative_wall_moment_n_mm_excluding_dead_mass"], 19055.301615)
        self.assertFalse(demand["dead_mass_measured"])
        self.assertFalse(demand["capacity_comparison_permitted"])
        self.assertIn(
            "0.5 * measured shelf dead mass",
            demand["external_point_proof_ballast_formula"],
        )
        self.assertEqual((self.plan["rating_kg"], self.plan["rating_lb"]), (0.0, 0.0))
        self.assertFalse(self.plan["drilling_authorized"])

    def test_cli_is_deterministic(self) -> None:
        command = [sys.executable, "-B", str(R10_ROOT / "full_wall_plan.py")]
        first = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        second = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first), json.loads(json.dumps(self.plan)))


if __name__ == "__main__":
    unittest.main()
