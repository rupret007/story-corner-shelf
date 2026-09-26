from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_shelf_mini as mini  # noqa: E402


class ShelfMiniTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        mini.main()
        cls.report = json.loads((ROOT / "generated" / "mini" / "validation.json").read_text(encoding="utf-8"))
        cls.cfg = mini.load_mini_config()

    def test_stud_bay_matches_r12_measured_centers(self) -> None:
        centers = self.report["closet"]["stud_centers_from_inside_corner_in"]
        self.assertEqual(centers, [17.0, 32.5])
        self.assertAlmostEqual(self.report["closet"]["deck_clear_span_in"], 15.5, places=6)

    def test_part_inventory(self) -> None:
        names = {entry["name"] for entry in self.report["meshes"]}
        self.assertEqual(
            names,
            {
                "MINI_PETG_StudBracket",
                "MINI_PETG_DeckTile_Center",
                "MINI_PETG_DeckTile_End_Left",
                "MINI_PETG_DeckTile_End_Right",
            },
        )
        self.assertEqual(self.report["part_count_total"], 8)
        by_name = {entry["name"]: entry["repeat_count"] for entry in self.report["meshes"]}
        self.assertEqual(by_name["MINI_PETG_StudBracket"], 2)
        self.assertEqual(by_name["MINI_PETG_DeckTile_Center"], 2)
        self.assertEqual(by_name["MINI_PETG_DeckTile_End_Left"], 2)
        self.assertEqual(by_name["MINI_PETG_DeckTile_End_Right"], 2)

    def test_every_part_fits_effective_a1_mini_envelope_with_margin(self) -> None:
        build = np.asarray(self.report["printer"]["effective_build_envelope_mm"], dtype=float)
        self.assertEqual(build.tolist(), [170.0, 170.0, 170.0])
        for entry in self.report["meshes"]:
            with self.subTest(name=entry["name"]):
                self.assertTrue(entry["fits_effective_build_envelope_in_saved_orientation"])
                size = np.asarray(entry["size_mm"], dtype=float)
                self.assertTrue(np.all(size <= build + 1e-6))

    def test_meshes_are_watertight_single_bodies(self) -> None:
        for entry in self.report["meshes"]:
            with self.subTest(name=entry["name"]):
                self.assertTrue(entry["watertight"])
                self.assertTrue(entry["winding_consistent"])
                self.assertEqual(entry["body_count"], 1)

    def test_mini_mass_is_below_r12_when_r12_validation_present(self) -> None:
        comparison = self.report["comparison_to_r12"]
        r12_kg = comparison.get("r12_packaged_kg")
        if r12_kg is None:
            self.skipTest("R12 validation missing")
        mini_kg = float(self.report["estimated_packaged_petg_mass_kg"])
        self.assertLess(mini_kg, r12_kg)
        self.assertIn("unverified", comparison["print_time_estimate"])

    def test_outputs_exist_under_generated_mini(self) -> None:
        out = ROOT / "generated" / "mini"
        for entry in self.report["meshes"]:
            stl = out / f"{entry['name']}.stl"
            self.assertTrue(stl.exists(), stl)
            threemf = out / "model_only_3mf" / f"MODEL_ONLY_{entry['name']}.3mf"
            self.assertTrue(threemf.exists(), threemf)


if __name__ == "__main__":
    unittest.main()
