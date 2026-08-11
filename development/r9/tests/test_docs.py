"""Regression checks for the novice R9 handoff documents."""

from __future__ import annotations

from pathlib import Path
import unittest


R9 = Path(__file__).resolve().parents[1]
DOCS = R9 / "docs"


class R9DocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.print_first = (DOCS / "PRINT_FIRST.md").read_text(encoding="utf-8")
        cls.assembly = (DOCS / "ASSEMBLY.md").read_text(encoding="utf-8")
        cls.worksheet = (DOCS / "MEASUREMENT_WORKSHEET.md").read_text(
            encoding="utf-8"
        )
        cls.protocol = (DOCS / "TEST_PROTOCOL.md").read_text(encoding="utf-8")
        cls.kickoff = (DOCS / "PRINTER_KICKOFF.md").read_text(encoding="utf-8")
        cls.materials = (DOCS / "MATERIALS_AND_HARDWARE.md").read_text(
            encoding="utf-8"
        )
        cls.design = (DOCS / "DESIGN_LANGUAGE.md").read_text(encoding="utf-8")
        cls.all_text = "\n".join(
            (
                cls.kickoff,
                cls.print_first,
                cls.assembly,
                cls.worksheet,
                cls.protocol,
                cls.materials,
                cls.design,
            )
        )

    def test_exact_bundle_and_catalog_warning_are_present(self) -> None:
        self.assertIn("development/r9/generated/qualification_v5/", self.print_first)
        self.assertIn("r9_compact_bookend_petg_qualification_v5", self.print_first)
        self.assertIn("MODEL_ONLY_R9_QUALIFICATION_CATALOG.3mf", self.print_first)
        self.assertIn("Never treat that combined catalog", self.print_first)

    def test_all_17_printable_ids_and_saved_support_rule_are_documented(self) -> None:
        ids = (
            "r9_shortened_outer_bookend_support",
            "r9_compact_support",
            "r9_concealed_corner_half_control",
            "r9_through_hidden_corner_half",
            "r9_return_hidden_corner_half",
            "r9_under_shelf_shear_key_coupon",
            "r9_cosmetic_corner_cover_coupon",
            "r9_90_degree_tabletop_angle_fixture",
            "r9_rear_ledger_male_coupon",
            "r9_rear_ledger_female_coupon",
            "r9_front_beam_lower_lap_coupon",
            "r9_front_beam_upper_lap_coupon",
            "r9_two_socket_outer_bookend_rail_fit_coupon",
            "r9_flush_blank_cable_module",
            "r9_multi_cable_comb_hook_module",
            "r9_through_outer_bookend_additive_two_socket_candidate",
            "r9_return_outer_bookend_additive_two_socket_candidate",
        )
        for mesh_id in ids:
            with self.subTest(mesh_id=mesh_id):
                self.assertIn(f"MODEL_ONLY_{mesh_id}.3mf", self.print_first)
        self.assertIn("All 17 R9 parts are authored **Support Off**", self.print_first)
        self.assertIn("Preview", self.print_first)

    def test_petg_and_a1_mini_settings_are_exact(self) -> None:
        for text in (
            "Bambu Lab A1 mini, 0.4 mm nozzle",
            "Textured PEI",
            "SUNLU PETG @BBL A1M 0.4 nozzle",
            "0.20mm Strength @BBL A1M",
            "250 C first layer; 245 C",
            "Flow ratio | 0.94",
            "25% grid",
            "Outer brim only, 5.0 mm wide, 0.1 mm object gap",
            "50 C for",
            "6–8 hours",
        ):
            with self.subTest(text=text):
                self.assertIn(text, self.print_first)
        self.assertIn("PLA is not authorized", self.print_first)
        self.assertIn("duplicate `Generic PETG`", self.print_first)
        self.assertIn("cool fully before removal", self.print_first)

    def test_run_local_datums_and_field_measurements_are_unambiguous(self) -> None:
        self.assertIn("zero is the far-left clear endpoint", self.worksheet)
        self.assertIn("zero is the inside corner", self.worksheet)
        self.assertIn("through far-left zero", self.worksheet)
        self.assertNotIn("outlet center from inside corner", self.all_text.lower())
        for text in (
            "61.25 in / 1555.75 mm",
            "36.75 in / 933.45 mm",
            "conservative working measurement",
        ):
            self.assertIn(text, self.worksheet)

    def test_v5_gate_language_and_required_controls_are_consistent(self) -> None:
        self.assertNotIn("final v1", self.protocol.lower())
        self.assertNotIn("v1 review", self.protocol.lower())
        self.assertIn("qualification-v5 review", self.protocol)
        self.assertIn("without any detectable rocking", self.protocol)
        for mesh_id in (
            "r9_compact_support",
            "r9_shortened_outer_bookend_support",
            "r9_concealed_corner_half_control",
        ):
            self.assertIn(mesh_id, self.protocol)

    def test_corrected_gate0_key_route_and_legacy_block_are_explicit(self) -> None:
        for text in (
            "stage0_individual_model_only_3mf",
            "MODEL_ONLY_r9_gate0_clearance_key_0p4_handle_down.3mf",
            "Do **not** print the legacy R8 v2",
            "floating-cantilever warning",
        ):
            self.assertIn(text, self.print_first)

    def test_one_bay_wall_work_and_load_remain_blocked(self) -> None:
        self.assertIn("software-blocked", self.print_first)
        self.assertIn("generated/one_bay_prototype_v3", self.assembly)
        self.assertIn("0 kg / 0 lb", self.all_text)
        self.assertIn("no drilling", self.assembly.lower())
        self.assertIn("wall installation remains blocked", self.assembly.lower())
        self.assertIn("printed wall anchors", self.all_text.lower())

    def test_exact_first_shelf_hardware_and_material_schedule_is_clear(self) -> None:
        for value in (
            "GRK RSS Rugged Structural Screw",
            "1/4 in x 3-1/2 in",
            "90306",
            "7/64 in / 2.778 mm",
            "18 installed screws",
            "Buy |",
            "24",
            "continuous",
            "64.0 mm",
            "59.944 mm",
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.materials)
        self.assertIn("generic hollow-wall anchor", self.materials)

    def test_palatine_moderne_contract_protects_the_load_path(self) -> None:
        for value in (
            "Palatine Moderne",
            "compressed Roman",
            "stepped keystone",
            "Art Deco",
            "additive-only",
            "load web",
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.design)


if __name__ == "__main__":
    unittest.main(verbosity=2)
