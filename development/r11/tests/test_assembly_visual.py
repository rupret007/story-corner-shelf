from __future__ import annotations

import math
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


R11 = Path(__file__).resolve().parents[1]
VISUAL = R11 / "visuals" / "r11_first_outer_bay_exploded_and_wall_topology.svg"
SVG_NS = "http://www.w3.org/2000/svg"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class TestR11AssemblyVisual(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = VISUAL.read_text(encoding="utf-8")
        cls.root = ET.fromstring(cls.source)
        cls.words = re.sub(r"\s+", " ", " ".join(cls.root.itertext())).strip()

    def test_is_accessible_deterministic_repo_native_svg(self) -> None:
        self.assertEqual(self.root.tag, f"{{{SVG_NS}}}svg")
        self.assertEqual(self.root.attrib["viewBox"], "0 0 1600 1100")
        self.assertEqual(self.root.attrib["role"], "img")
        self.assertEqual(self.root.attrib["aria-labelledby"], "r11-title r11-desc")

        title = self.root.find(f"{{{SVG_NS}}}title")
        desc = self.root.find(f"{{{SVG_NS}}}desc")
        self.assertIsNotNone(title)
        self.assertIsNotNone(desc)
        self.assertEqual(title.attrib["id"], "r11-title")
        self.assertEqual(desc.attrib["id"], "r11-desc")
        self.assertIn("first outer terminal bay", title.text.lower())
        self.assertIn("not authorized", desc.text.lower())

        forbidden = {"a", "animate", "foreignObject", "image", "script", "use"}
        self.assertFalse(
            {local_name(element.tag) for element in self.root.iter()} & forbidden
        )
        self.assertNotIn("http://", self.source.replace(f'xmlns="{SVG_NS}"', ""))
        self.assertNotIn("https://", self.source)

    def test_outer_terminal_bay_parts_and_dimensions_are_explicit(self) -> None:
        for token in (
            "S0 · fused two-socket outer support",
            "S1 · ordinary support",
            "LEFT TERMINAL HALF-DECK · 162.175 mm",
            "RIGHT TERMINAL HALF-DECK · 162.175 mm",
            "55 mm reciprocal overlap across all 3 lanes",
            "1 removable keystone",
            "blocks half-to-half X separation only",
        ):
            self.assertIn(token, self.words)

        ids = {element.attrib.get("id") for element in self.root.iter()}
        for expected in (
            "terminal-half-decks",
            "keystone-zero-credit",
            "supports-no-drilling-map",
        ):
            self.assertIn(expected, ids)

    def test_capture_and_reverse_motion_are_exact(self) -> None:
        for token in (
            "lower with 2 mm clearance",
            "slide 32 mm wallward",
            "settle 2 mm",
            "behind solid 8.4 mm roof / shoulder",
            "Exact reverse: lift 2 mm → slide 32 mm outward → lift clear.",
        ):
            self.assertIn(token, self.words)

    def test_cable_states_and_zero_credit_boundary_are_prominent(self) -> None:
        for token in (
            "S0 furniture states · 2 sockets",
            "lift 8 mm",
            "two flush blanks",
            "blank + comb/hook",
            "ALL CABLE MODULES: 0 SHELF-LOAD CREDIT",
            "0 VERTICAL-LOAD CREDIT",
        ):
            self.assertIn(token, self.words)

    def test_first_wall_topology_matches_exact_closure_and_counts(self) -> None:
        wall_length = 1555.75
        support_width = 31.75
        clearance = 0.35
        overlap = 55.0
        pitch = 254.0
        regular_span = pitch - clearance
        terminal_span = regular_span + support_width / 2.0 - clearance / 2.0
        closure = 2.0 * terminal_span + 4.0 * regular_span + 7.0 * clearance
        terminal_half = (terminal_span + overlap) / 2.0
        regular_half = (regular_span + overlap) / 2.0

        self.assertTrue(math.isclose(closure, wall_length))
        self.assertTrue(math.isclose(terminal_half, 162.175))
        self.assertTrue(math.isclose(regular_half, 154.325))

        for token in (
            "1555.75 mm first wall",
            "seven supports · six independent bays",
            "4 terminal halves × 162.175 mm (both halves of bays 0 and 5)",
            "8 regular halves × 154.325 mm",
            "28-kit · 27 active max · 28 safe starts · 21 unverified batched target",
        ):
            self.assertIn(token, self.words)

        support_group = self.root.find(f".//*[@id='first-wall-supports']")
        half_group = self.root.find(f".//*[@id='first-wall-half-decks']")
        self.assertIsNotNone(support_group)
        self.assertIsNotNone(half_group)
        self.assertEqual(len(support_group.findall(f"{{{SVG_NS}}}rect")), 7)
        halves = half_group.findall(f"{{{SVG_NS}}}rect")
        self.assertEqual(len(halves), 12)
        self.assertEqual(sum(item.attrib.get("class") == "terminal" for item in halves), 4)
        self.assertEqual(sum(item.attrib.get("class") == "regular" for item in halves), 8)

    def test_safety_banner_and_non_fabrication_boundary_are_unambiguous(self) -> None:
        normalized = self.words.upper()
        for token in (
            "QUALIFICATION-ONLY ENGINEERING SCHEMATIC",
            "NO PRINT",
            "NO DRILL",
            "NO INSTALL",
            "NO LOAD",
            "RATED LOAD 0 KG / 0 LB",
            "NOT A FABRICATION DRAWING",
        ):
            self.assertIn(token, normalized)

        self.assertIn("bore positions intentionally omitted", self.words)
        self.assertIn("drilling coordinates are not released", self.words)
        self.assertFalse(
            {local_name(element.tag) for element in self.root.iter()} & {"circle", "ellipse"}
        )

    def test_controlling_guides_link_the_visual(self) -> None:
        target = "visuals/r11_first_outer_bay_exploded_and_wall_topology.svg"
        for name in ("README.md", "ASSEMBLY.md", "PLAN.md"):
            text = (R11 / name).read_text(encoding="utf-8")
            self.assertIn(f"]({target})", text, name)
            self.assertIn("qualification-only", text.lower(), name)


if __name__ == "__main__":
    unittest.main()
