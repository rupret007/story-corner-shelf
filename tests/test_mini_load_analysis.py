from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import mini_load_analysis as analysis  # noqa: E402


class MiniLoadAnalysisTests(unittest.TestCase):
    def test_official_rating_stays_zero(self) -> None:
        report = analysis.build_report()
        self.assertTrue(report.qualification_only)
        self.assertEqual(report.official_rated_load_lb, 0.0)

    def test_provisional_load_is_minimum_mode(self) -> None:
        report = analysis.build_report()
        rated_modes = [
            mode
            for mode in report.modes
            if mode.name != "deck_tile_full_bay_span_interlayer_ultraconservative"
        ]
        limits = [mode.limit_total_load_lb for mode in rated_modes]
        self.assertAlmostEqual(report.provisional_contents_load_lb, min(limits), places=1)
        self.assertEqual(
            report.governing_failure_mode,
            min(rated_modes, key=lambda mode: mode.limit_total_load_lb).name,
        )
        mode_names = {mode.name for mode in report.modes}
        self.assertIn("deck_tile_interlock_shear", mode_names)
        self.assertIn("deck_tile_segment_span_interlayer", mode_names)
        self.assertIn("bracket_root_stress_concentration", mode_names)

    def test_deck_segment_span_matches_validation_layout(self) -> None:
        inputs = analysis.load_structural_inputs()
        segment = analysis.max_deck_tile_segment_span_mm(inputs["deck_layout"])
        self.assertAlmostEqual(segment, 151.8, places=1)
        segment_lb, detail = analysis.deck_span_limit_lb(
            span_mm=segment,
            deck_depth_mm=152.4,
            thickness_mm=8.0,
            interlayer_governed=True,
        )
        full_lb, _ = analysis.deck_span_limit_lb(
            span_mm=393.7,
            deck_depth_mm=152.4,
            thickness_mm=8.0,
            interlayer_governed=True,
        )
        self.assertGreater(segment_lb, full_lb)

    def test_layer_adhesion_factor_is_four(self) -> None:
        self.assertEqual(analysis.LAYER_ADHESION_SAFETY_FACTOR, 4.0)
        self.assertAlmostEqual(analysis.allowable_interlayer_mpa(), 15.0 / 4.0)

    def test_section_modulus_and_deck_bending(self) -> None:
        s = analysis.rectangular_section_modulus_mm3(152.4, 8.0)
        self.assertAlmostEqual(s, 152.4 * 8.0 * 8.0 / 6.0)
        deck_lb, detail = analysis.deck_span_limit_lb(
            span_mm=393.7,
            deck_depth_mm=152.4,
            thickness_mm=8.0,
            interlayer_governed=True,
        )
        self.assertGreater(deck_lb, 0.0)
        self.assertEqual(detail["model"], "simply_supported_uniform_load_between_two_bracket_arms")

    def test_bracket_cantilever_scales_with_section(self) -> None:
        small, _ = analysis.bracket_arm_cantilever_limit_lb(
            arm_length_mm=152.4,
            arm_width_mm=12.0,
            arm_height_mm=12.0,
            allowable_mpa=10.0,
            use_half_bracket_reaction=True,
        )
        large, _ = analysis.bracket_arm_cantilever_limit_lb(
            arm_length_mm=152.4,
            arm_width_mm=16.0,
            arm_height_mm=16.0,
            allowable_mpa=10.0,
            use_half_bracket_reaction=True,
        )
        self.assertGreater(large, small)

    def test_deck_interlock_shear_uses_generator_geometry(self) -> None:
        geom = analysis.deck_interlock_geometry_mm(
            deck_depth_mm=152.4,
            deck_thickness_mm=8.0,
            interlock_tongue_depth_mm=3.0,
        )
        self.assertAlmostEqual(geom["tongue_contact_length_mm"], 152.4 * 0.7)
        self.assertAlmostEqual(geom["tongue_thickness_mm"], 4.0)
        self.assertAlmostEqual(geom["shear_plan_area_mm2"], 3.0 * 152.4 * 0.7)
        limit_lb, detail = analysis.deck_interlock_shear_limit_lb(
            deck_depth_mm=152.4,
            deck_thickness_mm=8.0,
            interlock_tongue_depth_mm=3.0,
            spanwise_joint_count=2,
        )
        self.assertGreater(limit_lb, 0.0)
        self.assertEqual(detail["spanwise_joint_count"], 2)

    def test_bracket_root_stress_concentration_factor(self) -> None:
        self.assertEqual(analysis.BRACKET_ROOT_STRESS_CONCENTRATION_FACTOR, 1.5)

    def test_arm_along_depth_raises_root_limit_above_legacy_interlayer(self) -> None:
        legacy, _ = analysis.bracket_root_interlayer_limit_lb(
            arm_length_mm=152.4,
            strap_width_mm=72.0,
            arm_width_mm=12.0,
            arm_height_mm=12.0,
            arm_layers_along_depth=False,
        )
        improved, _ = analysis.bracket_root_interlayer_limit_lb(
            arm_length_mm=152.4,
            strap_width_mm=72.0,
            arm_width_mm=12.0,
            arm_height_mm=12.0,
            arm_layers_along_depth=True,
        )
        self.assertGreater(improved, legacy)

    def test_cli_json_is_deterministic(self) -> None:
        command = [sys.executable, "-B", str(ROOT / "scripts" / "mini_load_analysis.py")]
        first = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        second = subprocess.run(command, check=True, capture_output=True, text=True).stdout
        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertIn("provisional_contents_load_lb_analysis_only", payload)
        self.assertEqual(payload["official_rated_load_lb"], 0.0)


if __name__ == "__main__":
    unittest.main()
