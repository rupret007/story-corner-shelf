from __future__ import annotations

import math
from pathlib import Path
import re
import unittest


R11 = Path(__file__).resolve().parents[1]
PROJECT_ROOT = R11.parents[1]

DOCS = {
    "README.md",
    "PLAN.md",
    "DESIGN_REQUIREMENTS.md",
    "GUIDELINES.md",
    "CUSTOMIZATION.md",
    "MATERIALS_AND_HARDWARE.md",
    "PRINT_FIRST.md",
    "ASSEMBLY.md",
    "LOAD_QUALIFICATION.md",
}


def read(name: str) -> str:
    return (R11 / name).read_text(encoding="utf-8")


class TestR11Documentation(unittest.TestCase):
    def test_public_entrypoints_route_to_current_r11_without_releasing_it(self) -> None:
        root_readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        root_print = (PROJECT_ROOT / "PRINT_ME_FIRST.md").read_text(
            encoding="utf-8"
        )
        progress = (PROJECT_ROOT / "PROGRESS.md").read_text(encoding="utf-8")

        self.assertEqual(
            (PROJECT_ROOT / "README.md").read_bytes(),
            (PROJECT_ROOT / "docs" / "README.md").read_bytes(),
        )
        self.assertEqual(
            (PROJECT_ROOT / "PRINT_ME_FIRST.md").read_bytes(),
            (PROJECT_ROOT / "docs" / "PRINT_ME_FIRST.md").read_bytes(),
        )
        for name, opening in (
            ("README.md", root_readme[:2500]),
            ("PRINT_ME_FIRST.md", root_print[:2500]),
            ("PROGRESS.md", progress[:2500]),
        ):
            normalized = " ".join(opening.lower().split())
            for token in (
                "r11",
                "1555.75 mm",
                "28",
                "27",
                "unverified 21-start batched target",
                "0 kg / 0 lb",
                "historical/frozen",
            ):
                self.assertIn(token, normalized, f"{name}: {token}")
            self.assertRegex(normalized, r"no (?:authorized r11 )?print")
            self.assertIn("development/r11/README.md", opening)
            self.assertIn("development/r11/PRINT_FIRST.md", opening)

    def test_required_r11_documents_exist(self) -> None:
        self.assertLessEqual(DOCS, {path.name for path in R11.glob("*.md")})

    def test_kit_installed_and_start_counts_are_distinct(self) -> None:
        readme = read("README.md")
        materials = read("MATERIALS_AND_HARDWARE.md")
        guidelines = read("GUIDELINES.md")

        kit_articles = 7 + 12 + 6 + 2 + 1
        installed_articles = 7 + 12 + 6 + 2
        safe_unbatched_starts = kit_articles
        target_batched_starts = 7 + 12 + 1 + 1
        self.assertEqual(kit_articles, 28)
        self.assertEqual(installed_articles, 27)
        self.assertEqual(safe_unbatched_starts, 28)
        self.assertEqual(target_batched_starts, 21)

        for text in (readme, materials, guidelines):
            self.assertIn("28", text)
            self.assertIn("27", text)
            self.assertIn("21", text)
            self.assertIn("unbatched", text.lower())
            self.assertIn("batch", text.lower())
        self.assertIn("**Supplied-kit target** | **28**", materials)
        self.assertIn("**Maximum simultaneously installed** | **27**", materials)
        self.assertIn("**Total** | **28** | **21**", materials)

    def test_batching_changes_starts_only(self) -> None:
        for name in (
            "README.md",
            "DESIGN_REQUIREMENTS.md",
            "GUIDELINES.md",
            "CUSTOMIZATION.md",
            "MATERIALS_AND_HARDWARE.md",
            "PRINT_FIRST.md",
            "PLAN.md",
        ):
            text = re.sub(r"\s+", " ", read(name).lower())
            self.assertRegex(text, r"batch(?:ing| nesting).*changes? starts only")

    def test_first_wall_solver_math(self) -> None:
        wall_length = 1555.75
        support_width = 31.75
        maximum_pitch = 254.0

        bays = math.ceil((wall_length - support_width) / maximum_pitch)
        supports = bays + 1
        pitch = (wall_length - support_width) / bays
        centers = [support_width / 2 + index * pitch for index in range(supports)]

        self.assertEqual(bays, 6)
        self.assertEqual(supports, 7)
        self.assertEqual(pitch, 254.0)
        self.assertEqual(3 * supports, 21)
        self.assertEqual(
            centers,
            [
                15.875,
                269.875,
                523.875,
                777.875,
                1031.875,
                1285.875,
                1539.875,
            ],
        )

        customization = read("CUSTOMIZATION.md")
        for token in (
            "n_bays     = ceil((L - w) / p_max)",
            "n_supports = n_bays + 1",
            "pitch p    = (L - w) / n_bays",
            "screws     = 3 * n_supports",
        ):
            self.assertIn(token, customization)

    def test_terminal_identity_closure_and_bed_budget(self) -> None:
        pitch = 254.0
        overlap = 55.0
        clearance = 0.35
        support_width = 31.75
        depth = 152.4
        brim = 5.0
        brim_gap = 0.1
        reserve = 2.0

        regular_span = pitch - clearance
        terminal_span = regular_span + support_width / 2 - clearance / 2
        closure = 2 * terminal_span + 4 * regular_span + 7 * clearance
        regular = (regular_span + overlap) / 2
        terminal = (terminal_span + overlap) / 2
        padded_x = terminal + 2 * (brim + brim_gap + reserve)
        padded_y = depth + 2 * (brim + brim_gap + reserve)

        self.assertTrue(math.isclose(regular, 154.325))
        self.assertTrue(math.isclose(terminal, 162.175))
        self.assertTrue(math.isclose(closure, 1555.75))
        self.assertTrue(math.isclose(padded_x, 176.375))
        self.assertTrue(math.isclose(padded_y, 166.6))
        self.assertLess(padded_x, 180.0)
        self.assertLess(padded_y, 180.0)

        for name in (
            "README.md",
            "DESIGN_REQUIREMENTS.md",
            "GUIDELINES.md",
            "CUSTOMIZATION.md",
            "MATERIALS_AND_HARDWARE.md",
            "ASSEMBLY.md",
            "PLAN.md",
        ):
            text = re.sub(r"\s+", " ", read(name).lower())
            self.assertIn("four terminal", text, name)
            self.assertIn("eight regular", text, name)
            self.assertIn("162.175", text, name)
            self.assertIn("154.325", text, name)

    def test_v1_refuses_single_bay_layout(self) -> None:
        for name in (
            "README.md",
            "DESIGN_REQUIREMENTS.md",
            "GUIDELINES.md",
            "CUSTOMIZATION.md",
            "PLAN.md",
        ):
            text = re.sub(r"\s+", " ", read(name).lower())
            self.assertRegex(text, r"refus(?:e|es).*?(?:one|single)-bay", name)
        self.assertIn("bay count is less than two", read("CUSTOMIZATION.md"))

    def test_v1_authorizations_are_hard_forced_false(self) -> None:
        controlling = "\n".join(
            read(name)
            for name in (
                "README.md",
                "DESIGN_REQUIREMENTS.md",
                "GUIDELINES.md",
                "CUSTOMIZATION.md",
                "PRINT_FIRST.md",
            )
        )
        for token in (
            "print_authorized: false",
            "drilling_coordinates_released: false",
            "wall_installation_authorized: false",
            "test_load_authorized: false",
            "rated_load_kg: 0.0",
        ):
            self.assertIn(token, controlling)

        for name in DOCS:
            text = read(name)
            self.assertIn("0 kg / 0 lb", text, name)
            self.assertIsNone(
                re.search(r"(?:print_authorized|drilling_coordinates_released|"
                          r"wall_installation_authorized|test_load_authorized)"
                          r"\s*:\s*true", text, re.IGNORECASE),
                name,
            )

    def test_capture_motion_and_keystone_credit_are_exact(self) -> None:
        for name in (
            "README.md",
            "DESIGN_REQUIREMENTS.md",
            "GUIDELINES.md",
            "CUSTOMIZATION.md",
            "PRINT_FIRST.md",
            "ASSEMBLY.md",
            "LOAD_QUALIFICATION.md",
            "PLAN.md",
        ):
            text = re.sub(r"\s+", " ", read(name).lower())
            self.assertRegex(text, r"2(?:\.0)? mm", name)
            self.assertRegex(text, r"32(?:\.0)? mm", name)
            self.assertIn("wallward", text, name)
            self.assertIn("gravity-settle", text, name)
            self.assertIn("8.4 mm", text, name)
            self.assertIn("x separation", text.replace("x-separation", "x separation"), name)
            self.assertIn("support-capture", text, name)

    def test_required_field_and_environment_inputs_are_explicit(self) -> None:
        customization = read("CUSTOMIZATION.md").lower()
        for token in (
            "instrument/resolution",
            "uncertainty",
            "datum",
            "bow/taper",
            "corner angle",
            "pipes",
            "wiring",
            "substrate layer",
            "blocking location",
            "verification method",
            "printer serial/firmware",
            "filament product/lot/spool/drying",
            "minimum/maximum service temperature",
            "humidity range",
            "sunlight",
            "heat sources",
            "contents/load envelope",
            "cable loop/bend/snag/service",
        ):
            self.assertIn(token, customization)

    def test_print_handoff_records_exact_profiles_and_fresh_permission_rule(self) -> None:
        print_first = re.sub(r"\s+", " ", read("PRINT_FIRST.md"))
        self.assertIn("fresh explicit human permission", print_first)
        self.assertIn("Earlier permission never carries", print_first)
        self.assertIn("SUNLU PETG @BBL A1M 0.4 nozzle", print_first)
        self.assertIn("0.20mm Strength @BBL A1M", print_first)
        self.assertIn("Support | Off", print_first)
        self.assertIn("Outer only, 5 mm; 0.1 mm brim-object gap", print_first)
        self.assertIn("exactly the eight first-outer-bay qualification", print_first)
        self.assertIn("bay-0 terminal left half-deck", print_first)
        self.assertIn("bay-0 terminal right mate", print_first)
        self.assertIn("already-passing S0 fused support", print_first)
        self.assertNotIn("regular left half-deck from bays 1-4", print_first)

    def test_hardware_and_cable_invariants_are_not_omitted(self) -> None:
        requirements = read("DESIGN_REQUIREMENTS.md")
        materials = read("MATERIALS_AND_HARDWARE.md")
        guidelines = read("GUIDELINES.md")

        for text in (requirements, materials, guidelines):
            self.assertIn("90306", text)
            self.assertIn("FW14", text)
            self.assertIn("21", text)
            self.assertIn("blocking", text.lower())

        for text in (requirements, guidelines):
            self.assertIn("two flush blanks", text.lower())
            self.assertIn("comb/hook", text)
            self.assertIn("0.4 mm", text)
            self.assertIn("8 mm", text)
            self.assertIn("zero shelf-load credit", text)

    def test_r10_is_history_not_a_silent_geometry_source(self) -> None:
        for text in (read("README.md"), read("DESIGN_REQUIREMENTS.md")):
            self.assertIn("../r10/README.md", text)
            self.assertIn("immutable", text.lower())
            self.assertIn("R10", text)

    def test_local_markdown_links_resolve(self) -> None:
        link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")

        for name in DOCS:
            source = R11 / name
            for target in link_pattern.findall(source.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                path_text = target.split("#", 1)[0]
                self.assertTrue(
                    (source.parent / path_text).resolve().exists(),
                    f"broken link in {name}: {target}",
                )


if __name__ == "__main__":
    unittest.main()
