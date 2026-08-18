from __future__ import annotations

from pathlib import Path
import unittest


R10_ROOT = Path(__file__).resolve().parents[1]


class DesignRequirementsTests(unittest.TestCase):
    def test_nonnegotiable_scope_and_cable_memory_are_present(self) -> None:
        text = (R10_ROOT / "DESIGN_REQUIREMENTS.md").read_text(encoding="utf-8")
        required = (
            "lower shelf only",
            "61.25 in",
            "top at 68 in",
            "predominantly 3D",
            "0 kg / 0 lb",
            "Lincoln-log",
            "captured dovetail channels",
            "three authored wall bores",
            "GRK 90306",
            "Roman aqueduct / Art-Deco arcade",
            "only on the two outer bookends",
            "exactly one fused two-socket receiver",
            "0.4 mm-per-face",
            "8 mm service lift/drop",
            "flush blank",
            "multi-cable comb/hook",
            "No cable rail, peg, receiver, or module",
            "Bambu Lab A1 mini",
            "SUNLU standard black PETG",
            "Support Off",
            "auto-scale",
            "independent-review gates",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_metal_chassis_and_generic_anchor_are_not_active_architecture(self) -> None:
        text = (R10_ROOT / "DESIGN_REQUIREMENTS.md").read_text(encoding="utf-8")
        self.assertIn("contains no aluminum or steel shelf", text)
        self.assertIn("generic drywall or hollow-wall anchor receives no", text)
        self.assertIn("Metal is limited to the exact wall screws", text)


if __name__ == "__main__":
    unittest.main()
