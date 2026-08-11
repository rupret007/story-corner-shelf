#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


R9_ROOT = Path(__file__).resolve().parents[1]
if str(R9_ROOT) not in sys.path:
    sys.path.insert(0, str(R9_ROOT))

import generate_one_bay_prototype as generator  # noqa: E402
import model_io  # noqa: E402


class R9OneBayPrototypeGeneratorTests(unittest.TestCase):
    def test_fresh_bundle_is_exact_neutral_five_part_prototype(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "one-bay"
            generator.build_bundle(destination)
            generator.validate_bundle(destination)
            validation = json.loads(
                (destination / "validation.json").read_text(encoding="utf-8")
            )
            self.assertTrue(validation["tabletop_one_bay_present"])
            self.assertFalse(validation["full_measured_shelf_set_present"])
            self.assertFalse(validation["production_ready"])
            self.assertEqual(validation["rated_load_kg"], 0.0)
            self.assertTrue(validation["wall_bores_emitted"])
            self.assertEqual(
                validation["wall_mounting_candidate"]["bores_per_support"], 3
            )
            self.assertEqual(
                validation["wall_mounting_candidate"]["bore_center_spacing_mm"],
                64.0,
            )
            self.assertTrue(
                validation["wall_mounting_candidate"]["geometry_spacing_passes"]
            )
            self.assertEqual(
                validation["aesthetic_contract"]["id"],
                "r9_palatine_moderne_v1",
            )
            self.assertFalse(
                validation["wall_mounting_candidate"]["wall_installation_authorized"]
            )
            self.assertEqual(
                [
                    run["support_count"]
                    for run in validation["measured_even_support_candidate"]["runs"]
                ],
                [6, 4],
            )
            first = validation["first_shelf_execution_phase"]
            self.assertEqual(
                (first["run_id"], first["shelf_top_elevation_in"], first["support_count"]),
                ("through", 68.0, 6),
            )
            self.assertTrue(first["upper_84_in_shelf_deferred"])
            self.assertTrue(first["return_wall_deferred"])
            self.assertFalse(first["wall_installation_authorized"])
            self.assertTrue(validation["installed_target"]["collision_free"])
            self.assertTrue(
                validation["installed_target"]["service_paths_collision_free"]
            )
            self.assertEqual(tuple(validation["part_order"]), generator.PART_ORDER)
            for name in generator.PART_ORDER:
                path = (
                    destination
                    / "individual_model_only_3mf"
                    / f"MODEL_ONLY_{name}.3mf"
                )
                inspection = model_io.inspect_model_only_3mf(path)
                self.assertEqual(tuple(inspection.objects), (name,))
                self.assertEqual(inspection.translations_mm[name], (0.0, 0.0, 0.0))
            svg = (destination / "R9_ONE_BAY_ASSEMBLY_REFERENCE.svg").read_text(
                encoding="utf-8"
            )
            self.assertIn('width="1200" height="1200"', svg)
            self.assertIn("lower into top-open sockets", svg)
            self.assertIn("three 7.0 mm bores at 16 / 80 / 144 mm drops", svg)
            self.assertIn("wall installation remain blocked", svg)

    def test_two_fresh_builds_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first"
            second = Path(temporary) / "second"
            generator.build_bundle(first)
            generator.build_bundle(second)
            first_files = {
                str(path.relative_to(first)): path.read_bytes()
                for path in first.rglob("*")
                if path.is_file()
            }
            second_files = {
                str(path.relative_to(second)): path.read_bytes()
                for path in second.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first_files, second_files)

    def test_existing_destination_is_refused_without_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "existing"
            destination.mkdir()
            sentinel = destination / "sentinel.txt"
            sentinel.write_text("untouched", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                generator.build_bundle(destination)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "untouched")

    def test_published_v1_is_byte_frozen_and_custom_repo_targets_fail(self) -> None:
        generator._validate_published_v1()
        generator._validate_published_v2()
        with self.assertRaisesRegex(ValueError, "inside the repository"):
            generator._validate_destination(R9_ROOT / "unsafe-new-output")


if __name__ == "__main__":
    unittest.main()
