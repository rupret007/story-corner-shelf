#!/usr/bin/env python3
"""Geometry regressions for the excluded r6 rail-on research specimen."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from design_math import calculate_plan  # noqa: E402
from rail_geometry import (  # noqa: E402
    run_end_tie_block_mesh,
    stitch_rail_pin_mesh,
    stitch_rail_segment_mesh,
)
from release_plan import plan_optional_stitch_rail_study  # noqa: E402


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


class R6OptionalRailStudyGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(
            (R6 / "config.json").read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
        cls.lines = plan_optional_stitch_rail_study(cls.cfg, calculate_plan(cls.cfg))
        cls.results = [
            (segment, stitch_rail_segment_mesh(cls.cfg, segment))
            for line in cls.lines
            for segment in line.segments
        ]

    def test_all_optional_segments_are_closed_single_bodies_in_the_nominal_envelope(self) -> None:
        self.assertFalse(
            self.cfg["structure"]["stitch_rail_baseline_policy"][
                "installed_in_release_candidate"
            ]
        )
        self.assertEqual(
            len(self.results),
            self.cfg["structure"]["stitch_rail_planner"]["expected_per_level"][
                "rail_segments"
            ],
        )
        limit = float(self.cfg["printer"]["minimum_model_build_envelope_mm"][0])
        for segment, result in self.results:
            mesh = result.mesh
            self.assertTrue(mesh.is_watertight, segment.logical_id)
            self.assertGreater(mesh.volume, 0.0, segment.logical_id)
            self.assertEqual(len(mesh.split(only_watertight=False)), 1, segment.logical_id)
            self.assertTrue(np.all(mesh.bounds[0] >= -1e-7), segment.logical_id)
            self.assertTrue(np.all(mesh.extents <= limit + 1e-7), segment.logical_id)
            self.assertAlmostEqual(mesh.extents[0], segment.length_mm, delta=1.0e-5)

    def test_half_laps_and_floating_holes_match_the_release_plan(self) -> None:
        round_holes = 0
        elongated_holes = 0
        for segment, result in self.results:
            self.assertEqual(
                result.left_half_lap,
                segment.left_joint_class != "free_run_start",
            )
            self.assertEqual(
                result.right_half_lap,
                segment.right_joint_class != "free_run_end",
            )
            if segment.left_joint_class == "floating_supported_pier":
                self.assertEqual(result.elongated_hole_count, 2)
            else:
                self.assertEqual(result.elongated_hole_count, 0)
            round_holes += result.round_hole_count
            elongated_holes += result.elongated_hole_count
        self.assertEqual(elongated_holes, 28)
        expected = self.cfg["structure"]["stitch_rail_planner"]["expected_per_level"]
        self.assertEqual(
            round_holes,
            4 * expected["fixed_overlap_joints"]
            + 2 * expected["floating_pier_overlap_joints"],
        )

    def test_shared_pin_and_run_end_tie_are_printable_closed_bodies(self) -> None:
        for name, mesh in (
            ("stitch_rail_pin", stitch_rail_pin_mesh(self.cfg)),
            ("run_end_tie", run_end_tie_block_mesh(self.cfg)),
        ):
            self.assertTrue(mesh.is_watertight, name)
            self.assertGreater(mesh.volume, 0.0, name)
            self.assertEqual(len(mesh.split(only_watertight=False)), 1, name)
            self.assertTrue(np.all(mesh.bounds[0] >= -1e-7), name)
            self.assertTrue(np.all(mesh.extents <= 180.0 + 1e-7), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
