"""Contracts for the controlled R9 Stage 0 printer kickoff handoff."""

from __future__ import annotations

from pathlib import Path
import unittest


R9 = Path(__file__).resolve().parents[1]
GUIDE = R9 / "docs" / "PRINTER_KICKOFF.md"


class R9PrinterKickoffDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = GUIDE.read_text(encoding="utf-8")
        cls.flat = " ".join(cls.text.split())

    def test_exact_material_identity_is_bound(self) -> None:
        for value in (
            "SUNLU PETG",
            "B0D1KC72YP",
            "4 kg / 2 Black + 2 Black",
            "four black 1 kg spools",
            "1.75 mm +/-0.02 mm",
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.flat)
        self.assertIn("not PLA, PETG+, high-speed PETG, matte PETG", self.flat)

    def test_exact_stage0_route_and_manifest_verification_are_present(self) -> None:
        self.assertIn(
            "development/r9/generated/qualification_v5/"
            "stage0_individual_model_only_3mf/"
            "MODEL_ONLY_r8_clearance_ladder_receiver.3mf",
            self.text,
        )
        self.assertIn("live v5 `manifest.json`", self.text)
        self.assertIn("Do not open the combined R9 catalog", self.text)
        self.assertIn(
            "MODEL_ONLY_r9_gate0_clearance_key_0p4_handle_down.3mf",
            self.text,
        )

    def test_kickoff_and_physical_print_authorizations_are_separate(self) -> None:
        self.assertIn("PETG loaded—start Stage 0", self.text)
        self.assertIn("software preparation only", self.flat)
        self.assertIn("not** authorization to send", self.flat)
        self.assertIn("explicit authorization before Send/Print", self.flat)
        self.assertIn("corrected Stage 0 key is a separate physical job", self.flat)

    def test_exact_a1_mini_petg_recipe_and_fallback_are_present(self) -> None:
        for value in (
            "Bambu Lab A1 mini 0.4 nozzle",
            "Textured PEI Plate",
            "SUNLU PETG @BBL A1M 0.4 nozzle",
            "0.20mm Strength @BBL A1M",
            "0.20 mm",
            "250 C",
            "245 C",
            "60 C",
            "0.94",
            "9 mm^3/s",
            "10% minimum / 30% maximum",
            "90%",
            "6",
            "5",
            "3",
            "25% grid",
            "Outer brim only",
            "5.0 mm / 0.1 mm",
            "At least 2.0 mm beyond the brim",
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.flat)
        self.assertIn("Manage Presets", self.text)
        self.assertIn("enable `SUNLU`", self.text)
        self.assertIn("duplicate `Generic PETG`", self.text)

    def test_preview_human_handoff_and_release_limits_are_explicit(self) -> None:
        self.assertIn("## Preview gates after slicing", self.text)
        self.assertIn("macOS Accessibility access", self.text)
        self.assertIn("Bed Leveling On", self.text)
        self.assertIn("Timelapse Off", self.text)
        self.assertIn("Flow Dynamics Calibration On", self.text)
        self.assertIn("Stay with the machine through the complete first layer", self.text)
        self.assertIn("let the plate and PETG part cool fully", self.text)
        self.assertIn("0 kg / 0 lb", self.text)
        for forbidden_release in (
            "full shelf",
            "wall drilling",
            "installation",
            "stored load",
        ):
            with self.subTest(forbidden_release=forbidden_release):
                self.assertIn(forbidden_release, self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
