from __future__ import annotations

from pathlib import Path
import sys
import unittest


R10_ROOT = Path(__file__).resolve().parents[1]
if str(R10_ROOT) not in sys.path:
    sys.path.insert(0, str(R10_ROOT))

import cable_bookend  # noqa: E402
import generate_one_bay_qualification as generator  # noqa: E402
import lincoln_geometry  # noqa: E402


class R10HandoffDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assembly = (R10_ROOT / "ASSEMBLY.md").read_text(encoding="utf-8")
        cls.print_first = (R10_ROOT / "PRINT_FIRST.md").read_text(
            encoding="utf-8"
        )
        cls.both = cls.assembly + "\n" + cls.print_first
        cls.normalized_assembly = " ".join(
            cls.assembly.replace("\n> ", " ").split()
        )
        cls.normalized_print_first = " ".join(
            cls.print_first.replace("\n> ", " ").split()
        )
        cls.normalized_both = " ".join(cls.both.replace("\n> ", " ").split())

    def test_every_generated_individual_model_has_an_exact_handoff_filename(self) -> None:
        for part_name in generator.PART_ORDER:
            filename = f"MODEL_ONLY_{part_name}.3mf"
            with self.subTest(filename=filename):
                self.assertIn(filename, self.assembly)
                self.assertIn(filename, self.print_first)

    def test_core_assembly_steps_are_the_exact_authored_sequence(self) -> None:
        evidence = lincoln_geometry.build_one_bay_evidence()
        self.assertEqual(len(evidence.tabletop_assembly_order), 7)
        positions = []
        for step in evidence.tabletop_assembly_order:
            self.assertIn(step, self.assembly)
            positions.append(self.assembly.index(step))
        self.assertEqual(positions, sorted(positions))

    def test_saved_core_orientations_and_support_off_are_explicit(self) -> None:
        evidence = lincoln_geometry.build_one_bay_evidence()
        for part in evidence.parts:
            with self.subTest(part=part.name):
                self.assertIn(part.saved_orientation, self.print_first)
                self.assertFalse(part.support_required)
        self.assertIn(
            "Support is Off for every article", self.normalized_print_first
        )
        self.assertIn("One named article per plate", self.print_first)

    def test_flush_caps_and_positive_support_retainer_motion_cannot_be_omitted(self) -> None:
        for phrase in (
            "integrated flush access caps",
            "there are no separate debris-cover pieces",
            "insert its bay-local support retainer straight from the front",
            "shift it 2.4 mm toward that bay",
            "shift each support retainer 2.4 mm away from its bay",
            "pull it straight forward",
            "positive reversible walk-out stops",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.normalized_assembly)

    def test_cable_bookend_api_inventory_and_service_contract_are_documented(self) -> None:
        for part_name in (
            cable_bookend.FIRST_WALL_BOOKEND_PART_NAME,
            cable_bookend.FIRST_WALL_BLANK_0_PART_NAME,
            cable_bookend.FIRST_WALL_BLANK_1_PART_NAME,
            cable_bookend.FIRST_WALL_COMB_PART_NAME,
        ):
            with self.subTest(part_name=part_name):
                self.assertIn(part_name, self.both)
        for phrase in (
            "only on first-wall support S0",
            "Both sockets face inward",
            "lower it exactly 8 mm",
            "ten cycles in each socket",
            "zero structural or shelf-load credit",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.normalized_both)

    def test_fail_fast_order_finishes_actual_one_bay_before_full_wall(self) -> None:
        for heading in (
            "Gate A — midpoint Lincoln-log interface",
            "Gate B — one support-capture interface",
            "Gate C — complete one actual shelf cell",
            "Gate D — separate far-left S0 cable candidate",
        ):
            self.assertIn(heading, self.print_first)
        self.assertLess(
            self.print_first.index("Gate A — midpoint Lincoln-log interface"),
            self.print_first.index("Gate B — one support-capture interface"),
        )
        self.assertLess(
            self.print_first.index("Gate B — one support-capture interface"),
            self.print_first.index("Gate C — complete one actual shelf cell"),
        )
        self.assertIn(
            "not a complete six-bay production set", self.normalized_print_first
        )

    def test_qualification_inventory_is_reconciled_with_exact_first_wall_count(self) -> None:
        for phrase in (
            "16-article qualification bundle",
            "12 core one-bay articles plus four S0 cable-gate articles",
            "seven supports",
            "12 cassette halves",
            "18 splice logs",
            "18 flush-capped log retainers",
            "12 bay-local support retainers",
            "two flush blanks",
            "one comb/hook",
            "70 printed articles",
            "not both installed at S0",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.normalized_assembly)
        self.assertIn("exactly 70 printed articles", self.normalized_print_first)

    def test_every_print_requires_new_human_permission(self) -> None:
        for phrase in (
            "fresh, explicit human",
            "Permission from an earlier job does not carry forward",
            "applies even when a retry appears unchanged",
            "stop at the final Send/Print control",
            "obtain fresh permission",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.normalized_print_first)

    def test_print_and_cycle_records_are_present(self) -> None:
        for phrase in (
            "First-article inspection record",
            "One-bay unloaded cycling record",
            "Cable-module cycling record",
            "Spool lot + dry record",
            "Cycles completed",
            "Photo ID",
            "Pass / fail",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.print_first)

    def test_material_hardware_and_fail_closed_boundaries_are_explicit(self) -> None:
        for phrase in (
            "SUNLU standard black PETG",
            "B0D1KC72YP",
            "GRK RSS Rugged Structural Screw",
            "1/4 in x 3-1/2 in",
            "part `90306`",
            "L.H. Dottie `FW14`",
            "21 candidates in one complete wall",
            "100 exact screws",
            "four support fixtures",
            "verified continuous solid-wood blocking",
            "no wall hardware",
            "Do not drill the closet wall",
            "0 kg / 0 lb",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.normalized_assembly)
        self.assertIn("No wall drilling", self.print_first)
        self.assertIn("No wall drilling", self.assembly)


if __name__ == "__main__":
    unittest.main()
