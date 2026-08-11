from __future__ import annotations

from pathlib import Path
import hashlib
import unittest


R10_ROOT = Path(__file__).resolve().parents[1]


class R10DocumentationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.docs = {
            name: (R10_ROOT / name).read_text(encoding="utf-8")
            for name in (
                "README.md",
                "DESIGN_REQUIREMENTS.md",
                "GUIDELINES.md",
                "MATERIALS_AND_HARDWARE.md",
                "LOAD_QUALIFICATION.md",
            )
        }
        cls.all_text = "\n".join(cls.docs.values())

    def test_obsolete_metal_chassis_is_not_reintroduced(self) -> None:
        for forbidden in (
            "6061-T6",
            "continuous front and rear aluminum",
            "aluminum bearing strap",
            "hybrid one-bay fixture",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.all_text)
        self.assertIn("no aluminum or steel shelf chassis", self.all_text)

    def test_exact_printed_arcade_and_fastener_counts_are_documented(self) -> None:
        materials = self.docs["MATERIALS_AND_HARDWARE.md"]
        for phrase in (
            "exact 10 in",
            "six independent bays",
            "| Palatine PETG support, 31.75 mm across the run | 7 |",
            "| Regular cassette half, 126.65 mm printed / 127 mm nominal | 10 |",
            "| Terminal cassette half, 142.35 mm printed / 142.875 mm nominal | 2 |",
            "| PETG splice log, 159.1 x 20 x 24 mm | 18 |",
            "12 x 28 x 6 mm body; 12.4 x 28 x 10.8 mm saved envelope",
            "| Bay-local support retainer, 8 x 136 x 6 mm | 12 |",
            "All 30 keys are retention-only",
            "67 printed structural-assembly articles",
            "70 first-wall printed",
            "32.0 mm total height",
            "zero-gap assembly is forbidden",
            "part `90306`",
            "21 installed candidates",
            "verified continuous",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.all_text)

    def test_compact_corbels_and_cable_memory_are_explicit(self) -> None:
        guidelines = self.docs["GUIDELINES.md"]
        for phrase in (
            "76.2 mm",
            "158.75 mm",
            "120.65 mm",
            "exactly **two outer cable bookends**",
            "two-socket",
            "0.4 mm clearance per face",
            "8 mm service lift/drop",
            "flush blank",
            "two flush blanks",
            "multi-cable comb/hook",
            "through-side terminal/corner placeholder",
            "R9 attachment mesh",
            "zero structural credit",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, guidelines)

    def test_wall_bore_and_creep_contract_match_engineering_source(self) -> None:
        for phrase in (
            "7.0 mm",
            "19.05 / 79.375 / 139.7 mm",
            "27.025 mm",
            "no counterbores",
            "not a drilling schedule",
            "1000-hour creep",
            "measured maximum plus 5 degrees C",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.all_text)

    def test_every_major_document_fails_closed(self) -> None:
        for name in (
            "README.md",
            "DESIGN_REQUIREMENTS.md",
            "GUIDELINES.md",
            "MATERIALS_AND_HARDWARE.md",
            "LOAD_QUALIFICATION.md",
        ):
            with self.subTest(name=name):
                text = self.docs[name]
                self.assertIn("0 kg / 0 lb", text)
        self.assertIn("No wall drilling", self.docs["GUIDELINES.md"])
        self.assertIn("Generic hollow-wall anchors", self.all_text)

    def test_fail_fast_print_and_dry_assembly_are_documented(self) -> None:
        readme = self.docs["README.md"]
        qualification = self.docs["LOAD_QUALIFICATION.md"]
        for phrase in (
            "Actual midpoint interface",
            "Complete one actual structural bay",
            "One cable bookend set",
            "Complete tabletop set",
            "Framed-wall mockup",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, readme)
        self.assertIn("Assemble dry on a flat table", qualification)
        self.assertIn("Never hammer", qualification)
        self.assertIn("one part per plate", qualification)

    def test_exact_material_and_process_are_preserved(self) -> None:
        for phrase in (
            "SUNLU standard black PETG",
            "B0D1KC72YP",
            "SUNLU PETG @BBL A1M 0.4 nozzle",
            "0.20mm Strength @BBL A1M",
            "Support Off",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.all_text)

    def test_primary_sources_do_not_overclaim_petg_connection_capacity(self) -> None:
        materials = self.docs["MATERIALS_AND_HARDWARE.md"]
        for phrase in (
            "grkfasteners.com/grk-products",
            "ESR-2442.pdf",
            "SUNLU standard PETG product data",
            "does **not**",
            "not long-term design allowables",
            "L.H. Dottie FW14 product page",
            "standard 100-pack",
            "outside ESR-2442",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, materials)

    def test_hardware_allocation_is_complete_before_retests(self) -> None:
        materials = self.docs["MATERIALS_AND_HARDWARE.md"]
        for phrase in (
            "100 exact GRK 90306 screws",
            "100-pack of Dottie FW14 washers",
            "four sacrificial three-fastener support groups",
            "Initial unallocated spares",
            "minimum full-size printed demand",
            "284 articles",
            "19 measurement stations",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, materials)

    def test_assembly_diagram_is_linked_hash_pinned_and_fail_closed(self) -> None:
        name = "r10_one_bay_exploded_and_first_wall_topology.svg"
        svg_path = R10_ROOT / "visuals" / name
        payload = svg_path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        visuals_readme = (R10_ROOT / "visuals" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(name, self.docs["README.md"])
        self.assertIn(name, visuals_readme)
        self.assertIn(digest, visuals_readme)
        self.assertIn("NOT A DRILLING OR INSTALLATION DIAGRAM", payload.decode())
        self.assertIn("3 independent flush-cap keys", payload.decode())
        self.assertIn("grip +4.0", payload.decode())


if __name__ == "__main__":
    unittest.main()
