#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path
import unittest


R9_ROOT = Path(__file__).resolve().parents[1]
if str(R9_ROOT) not in sys.path:
    sys.path.insert(0, str(R9_ROOT))

import field_layout  # noqa: E402


class R9MeasuredFieldLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.layout = field_layout.build_even_field_layout()

    def test_measured_runs_receive_minimum_even_support_counts(self) -> None:
        through, return_run = self.layout.runs
        self.assertEqual((through.clear_length_mm, return_run.clear_length_mm), (1555.75, 933.45))
        self.assertEqual((len(through.stations), len(return_run.stations)), (6, 4))
        self.assertEqual(self.layout.supports_per_level, 10)
        self.assertEqual(self.layout.visible_supports_per_level, 8)
        self.assertEqual(self.layout.hidden_corner_halves_per_level, 2)

    def test_each_run_is_exactly_even_and_below_qualification_pitch(self) -> None:
        for run in self.layout.runs:
            differences = [
                right.center_from_run_datum_mm - left.center_from_run_datum_mm
                for left, right in zip(run.stations, run.stations[1:])
            ]
            self.assertTrue(differences)
            for difference in differences:
                self.assertAlmostEqual(difference, run.actual_pitch_mm, places=5)
            self.assertLessEqual(run.actual_pitch_mm, run.maximum_pitch_mm)
        self.assertAlmostEqual(self.layout.runs[0].actual_pitch_in, 11.998031, places=6)
        self.assertAlmostEqual(self.layout.runs[1].actual_pitch_in, 11.830052, places=6)

    def test_only_outer_ends_use_bookends_and_corner_halves_stay_hidden(self) -> None:
        through, return_run = self.layout.runs
        self.assertEqual(through.stations[0].role, "outer_bookend")
        self.assertEqual(through.stations[-1].role, "hidden_corner")
        self.assertEqual(return_run.stations[0].role, "hidden_corner")
        self.assertEqual(return_run.stations[-1].role, "outer_bookend")
        self.assertTrue(
            all(
                station.role == "compact"
                for station in (*through.stations[1:-1], *return_run.stations[1:-1])
            )
        )

    def test_every_support_has_three_bores_but_no_drilling_release(self) -> None:
        self.assertEqual(self.layout.mounting_bores_per_support, 3)
        self.assertTrue(
            all(
                station.mounting_bores == 3
                for run in self.layout.runs
                for station in run.stations
            )
        )
        self.assertFalse(self.layout.drilling_coordinates_released)
        self.assertFalse(self.layout.primary_hollow_wall_anchor_authorized)


if __name__ == "__main__":
    unittest.main()
