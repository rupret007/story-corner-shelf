#!/usr/bin/env python3
"""Focused determinism and safety-contract tests for the r6 SVG sheets."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from generate_drawings import (  # noqa: E402
    DISPLAY_NOTICE,
    DRAWING_FILENAMES,
    STATUS_LINE,
    generate_drawings,
    load_config,
)


CONFIG_PATH = R6 / "config.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R6DrawingTests(unittest.TestCase):
    def test_config_reader_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            duplicate = Path(temp) / "duplicate.json"
            duplicate.write_text('{"project": {"name": "one", "name": "two"}}\n')
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key 'name'"):
                load_config(duplicate)

    def test_all_required_drawings_are_valid_svg_and_repeat_safety_labels(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            paths = generate_drawings(config_path=CONFIG_PATH, out_dir=Path(temp))
            self.assertEqual(tuple(path.name for path in paths), DRAWING_FILENAMES)
            for path in paths:
                payload = path.read_text(encoding="utf-8")
                root = ET.fromstring(payload)
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg", path.name)
                self.assertEqual(root.attrib["data-revision"], "r6", path.name)
                self.assertEqual(
                    root.attrib["data-status"],
                    "experimental-unrated-nominal-unverified-model-only-no-wall-bores",
                    path.name,
                )
                self.assertIn(STATUS_LINE, payload, path.name)
                self.assertIn(DISPLAY_NOTICE, payload, path.name)
                for phrase in (
                    "EXPERIMENTAL / UNRATED",
                    "NOMINAL / UNVERIFIED",
                    "MODEL-ONLY",
                    "NO WALL BORES",
                    "SCHEMATIC DISPLAY PATHS ONLY",
                    "no load rating is claimed",
                ):
                    self.assertIn(phrase, payload, f"{path.name}: {phrase}")

    def test_exact_nominal_geometry_and_mechanics_appear_on_governing_sheets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            generate_drawings(config_path=CONFIG_PATH, out_dir=out)
            expected_fragments = {
                "plan_layout.svg": (
                    'data-through-length-mm="1514.475"',
                    'data-return-length-mm="733.675"',
                    'data-support-count="11"',
                    'data-half-cassette-count="18"',
                    "37.7825, 279.7175, 521.6525, 763.5875, 1005.5225, 1247.4575, 1489.3925",
                    "204.5825, 429.6525, 654.7225, 879.7925",
                    "16 seams: 9 fixed crowns + 7 floating piers",
                ),
                "palatine_3_6_elevation.svg": (
                    'data-long-bays="6"',
                    'data-return-bays="3"',
                    'data-total-bays="9"',
                    'data-long-radius-mm="125.527913"',
                    'data-return-radius-mm="114.826773"',
                    "241.935 mm",
                    "225.07 mm",
                    "3 + 6 = 9 visible bays",
                ),
                "two_level_vertical_layout.svg": (
                    'data-zone-in="43.5"',
                    'data-lower-offset-in="12"',
                    'data-upper-offset-in="33"',
                    'data-top-spacing-in="21"',
                    'data-clear-opening-in="14.385827"',
                    "NO VERTICAL STRUCTURAL TIE",
                    "upper level first",
                    "≥ 75 mm",
                ),
                "exploded_joinery.svg": (
                    'data-cassette-tenons-per-half="2"',
                    'data-spring-tenons-per-half="1"',
                    'data-long-tenon-centers-mm="50,80.5925"',
                    'data-short-tenon-centers-mm="49.6,72.16"',
                    "0.0 mm whole-half run travel",
                    "3 indexed quarter-turn cross-keys per half",
                    "upward from below",
                    "to positive hard stop",
                ),
                "crown_assembly_sequence.svg": (
                    'data-bridge-width-mm="72"',
                    'data-bridge-height-mm="48"',
                    'data-bridge-thickness-mm="6.4"',
                    'data-pin-diameter-mm="5"',
                    'data-pin-hole-mm="5.4"',
                    "RIGHT / fixed half only",
                    "anti-drop / reverse-slide",
                    "FULLY UNLOAD",
                ),
                "x_corbel_load_path.svg": (
                    'data-horizontal-leg-mm="144"',
                    'data-vertical-leg-mm="108"',
                    'data-diagonal-mm="180"',
                    'data-crossing-mm="82.666667,92"',
                    "√(144² + 108²) = 180 mm",
                    "(0,154) → (27.733333,133.2)",
                    "y = 42 / 84 / 126 mm",
                ),
                "corner_ownership_clearance.svg": (
                    'data-corner-gap-mm="1.2"',
                    'data-corner-front-plane-mm="158.75"',
                    'data-first-through-crown-mm="158.75"',
                    'data-perpendicular-corbel-clearance-mm="30.2325"',
                    'data-visible-front-corbel-plan-reserve-mm="8.6325"',
                    'data-integral-boss-projection-mm="7.2"',
                    'data-full-removable-facade-projection-mm="13.2"',
                    'data-ornament-axial-service-stroke-mm="4.4"',
                    'data-return-cosmetic-leading-plane-mm="173.15"',
                    'data-return-visible-base-leading-plane-mm="173.95"',
                    'data-locked-all-solid-gap-mm="1.2"',
                    'data-visible-base-relief-gap-mm="2"',
                    'data-structural-arm-clearance-mm="18.8"',
                    "Return structural arm start: 177.55 mm",
                    "Minimum residual solid gap: 0.65 mm",
                    "Maximum nominal square deviation: ±0.2°",
                ),
            }
            self.assertEqual(tuple(expected_fragments), DRAWING_FILENAMES)
            for filename, fragments in expected_fragments.items():
                payload = (out / filename).read_text(encoding="utf-8")
                for fragment in fragments:
                    self.assertIn(fragment, payload, f"{filename}: {fragment}")

            plan_payload = (out / "plan_layout.svg").read_text(encoding="utf-8")
            self.assertIn(
                'class="inverse" text-anchor="middle" fill="#f7f0de">DEPTH 152.4 mm / 6 in</text>',
                plan_payload,
            )
            self.assertNotIn(
                'rotate(-90 271.445 270.785)',
                plan_payload,
            )
            self.assertNotIn(
                "y = 42 / 96 / 150 mm",
                (out / "x_corbel_load_path.svg").read_text(encoding="utf-8"),
            )
            corner_payload = (out / "corner_ownership_clearance.svg").read_text(
                encoding="utf-8"
            )
            for label in (
                "structural front 158.75 mm",
                "full locked facade front 171.95 mm",
                "max 4.4 mm service face 176.35 mm",
                "return structure starts 177.55 mm",
            ):
                self.assertIn(
                    f'class="inverse" fill="#f7f0de">{label}</text>',
                    corner_payload,
                )
            self.assertIn(
                'class="tiny">relieved visible base starts 173.95 mm</text>',
                corner_payload,
            )
            self.assertNotIn(
                'class="tiny" fill="#f7f0de">relieved visible base starts',
                corner_payload,
            )
            self.assertIn(
                'class="inverse-callout" fill="#f7f0de">NOMINAL 90°',
                corner_payload,
            )
            corbel_payload = (out / "x_corbel_load_path.svg").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                'class="inverse-label" text-anchor="start" fill="#f7f0de">Wᵤ',
                corbel_payload,
            )
            self.assertNotIn('class="label" text-anchor="start" fill="#f7f0de">Wᵤ', corbel_payload)

    def test_generation_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_paths = generate_drawings(config_path=CONFIG_PATH, out_dir=Path(first))
            second_paths = generate_drawings(config_path=CONFIG_PATH, out_dir=Path(second))
            self.assertEqual(tuple(path.name for path in first_paths), DRAWING_FILENAMES)
            self.assertEqual(tuple(path.name for path in second_paths), DRAWING_FILENAMES)
            self.assertEqual(
                {path.name: digest(path) for path in first_paths},
                {path.name: digest(path) for path in second_paths},
            )


if __name__ == "__main__":
    unittest.main()
