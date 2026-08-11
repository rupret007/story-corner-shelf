#!/usr/bin/env python3
"""Release-plan regressions for cassettes and the excluded rail study."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from design_math import calculate_plan  # noqa: E402
from release_plan import (  # noqa: E402
    enumerate_cassette_instances,
    group_cassette_variants,
    per_level_topology,
    plan_optional_stitch_rail_study,
)


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


class R6ReleasePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(
            (R6 / "config.json").read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
        cls.plan = calculate_plan(cls.cfg)
        cls.cassettes = enumerate_cassette_instances(cls.cfg, cls.plan)
        cls.optional_rails = plan_optional_stitch_rail_study(cls.cfg, cls.plan)

    def test_eight_cassette_variants_cover_exactly_eighteen_positions(self) -> None:
        groups = group_cassette_variants(self.cassettes)
        self.assertEqual(len(groups), 8)
        self.assertEqual(len(self.cassettes), 18)
        self.assertEqual(
            {key: len(value) for key, value in groups.items()},
            {
                "return_end_outer": 1,
                "return_internal_crown_to_pier": 2,
                "return_internal_pier_to_crown": 2,
                "return_start_outer": 1,
                "through_end_outer": 1,
                "through_internal_crown_to_pier": 5,
                "through_internal_pier_to_crown": 5,
                "through_start_outer": 1,
            },
        )
        widths = sorted({round(item.physical_width_mm, 4) for item in self.cassettes})
        self.assertEqual(
            widths,
            [112.185, 120.6175, 139.3925, 143.7925, 152.225],
        )

    def test_terminal_supports_are_inboard_and_internal_supports_touch_seams(self) -> None:
        for run_id in ("long_wall_5ft", "short_wall_3ft"):
            run_items = [item for item in self.cassettes if item.run_id == run_id]
            self.assertAlmostEqual(
                run_items[0].support_center_local_mm,
                (
                    self.plan.through.start_pier_inset_mm
                    if run_id == "long_wall_5ft"
                    else self.plan.return_run.start_pier_inset_mm
                ),
                places=6,
            )
            run_length = (
                self.plan.through.length_mm
                if run_id == "long_wall_5ft"
                else self.plan.return_run.length_mm
            )
            self.assertAlmostEqual(
                run_length - run_items[-1].support_center_local_mm,
                (
                    self.plan.through.end_pier_inset_mm
                    if run_id == "long_wall_5ft"
                    else self.plan.return_run.end_pier_inset_mm
                ),
                places=6,
            )
            for item in run_items[1:-1]:
                if item.spring_side == "left":
                    self.assertAlmostEqual(
                        item.support_center_local_mm - item.physical_start_local_mm,
                        -self.cfg["structure"]["cassette_between_module_seam_mm"] / 2.0,
                    )
                else:
                    self.assertAlmostEqual(
                        item.physical_end_local_mm - item.support_center_local_mm,
                        -self.cfg["structure"]["cassette_between_module_seam_mm"] / 2.0,
                    )

    def test_optional_rail_study_remains_reproducible_but_excluded(self) -> None:
        self.assertFalse(
            self.cfg["structure"]["stitch_rail_baseline_policy"][
                "installed_in_release_candidate"
            ]
        )
        self.assertEqual(sum(len(line.segments) for line in self.optional_rails), 41)
        self.assertEqual(sum(len(line.joints) for line in self.optional_rails), 37)
        floating = [
            joint
            for line in self.optional_rails
            for joint in line.joints
            if joint.joint_class == "floating_supported_pier"
        ]
        self.assertEqual(len(floating), 14)
        self.assertEqual(2 * sum(len(line.joints) for line in self.optional_rails), 74)
        for line in self.optional_rails:
            self.assertLessEqual(max(item.length_mm for item in line.segments), 165.0 + 1e-7)
            self.assertGreater(min(item.length_mm for item in line.segments), 0.0)

    def test_optional_study_joint_planes_preserve_the_research_contract(self) -> None:
        keepout = self.cfg["structure"]["stitch_rail_planner"][
            "minimum_overlap_plane_offset_from_cassette_seam_mm"
        ]
        stagger = self.cfg["structure"]["stitch_rail_planner"][
            "minimum_front_rear_joint_stagger_mm"
        ]
        for run in (self.plan.through, self.plan.return_run):
            seams = run.cassette_boundary_stations_local_mm[1:-1]
            for line in [item for item in self.optional_rails if item.run_id == run.run_id]:
                for joint in line.joints:
                    self.assertGreaterEqual(
                        min(abs(joint.center_local_mm - seam) for seam in seams),
                        keepout - 1e-7,
                    )
            front = next(
                item for item in self.optional_rails if item.run_id == run.run_id and item.line_role == "front"
            )
            rear = next(
                item for item in self.optional_rails if item.run_id == run.run_id and item.line_role == "rear"
            )
            front_float = [item for item in front.joints if item.related_pier_seam_local_mm is not None]
            rear_float = [item for item in rear.joints if item.related_pier_seam_local_mm is not None]
            for left, right in zip(front_float, rear_float):
                self.assertEqual(left.related_pier_seam_local_mm, right.related_pier_seam_local_mm)
                self.assertGreaterEqual(abs(left.center_local_mm - right.center_local_mm), stagger)

    def test_release_baseline_topology_contains_zero_rail_objects(self) -> None:
        one = self.cfg["structure"]["stitch_rail_planner"]["expected_per_level"]
        two = self.cfg["structure"]["stitch_rail_planner"]["expected_selected_two_levels"]
        for key in one:
            self.assertEqual(two[key], 2 * one[key], key)
        topology = per_level_topology(self.cfg, self.plan)
        self.assertEqual(topology["stitch_rail_segments"], 0)
        self.assertEqual(topology["stitch_rail_overlap_joints"], 0)
        self.assertEqual(topology["stitch_rail_joint_pins"], 0)
        self.assertEqual(topology["run_end_tie_blocks"], 0)
        snapshot = self.cfg["nominal_geometry_snapshot"]["selected_two_level_part_topology"]
        self.assertEqual(snapshot["stitch_rail_segments"], 0)
        self.assertEqual(snapshot["stitch_rail_overlap_joints"], 0)
        self.assertEqual(snapshot["stitch_rail_joint_pins"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
