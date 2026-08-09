#!/usr/bin/env python3
"""Focused consistency checks for the promotion-ready r6 documentation draft."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


R6 = Path(__file__).resolve().parents[1]
REPO = R6.parents[1]
DOCS = R6 / "docs"
sys.path.insert(0, str(R6))

from package_layout import (  # noqa: E402
    EXPECTED_EXACT_PACKAGE_COUNTS,
    PACKAGE_FILENAMES,
    PACKAGE_ORDER,
)
from publish_root import STAGED_TREE_MAP  # noqa: E402

REQUIRED_DOCS = (
    "README.md",
    "PRINT_ME_FIRST.md",
    "ENGINEERING_DESIGN.md",
    "SAFETY.md",
    "ASSEMBLY.md",
    "MEASUREMENT_WORKSHEET.md",
    "TEST_PROTOCOL.md",
    "CONTRIBUTING.md",
    "CHANGELOG_ENTRY.md",
)


class R6DocumentationDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents = {
            name: (DOCS / name).read_text(encoding="utf-8") for name in REQUIRED_DOCS
        }
        cls.corpus = "\n".join(cls.documents.values())
        cls.progress = (R6 / "PROGRESS.md").read_text(encoding="utf-8")

    def test_exact_document_set_exists_and_is_substantive(self) -> None:
        self.assertEqual(tuple(self.documents), REQUIRED_DOCS)
        self.assertTrue(all(len(payload.splitlines()) >= 25 for payload in self.documents.values()))

    def test_scope_status_counts_and_rights_are_consistent(self) -> None:
        required = (
            "experimental",
            "unrated",
            "no tested load rating",
            "black PETG",
            "only nonprinted",
            "metal structural screws",
            "verified wood studs",
            "two independent",
            "225",
            "33",
            "258",
            "516",
            "16.000337",
            "32.000674",
            "coupons and spares",
            "no G-code",
            "49 individual one-part model-only 3mfs",
            "generated/individual_model_only_3mf/",
            "generated/stl/",
            "production wall holes",
            "public visibility does not",
            "no `LICENSE`",
        )
        lowered = " ".join(self.corpus.lower().split())
        for phrase in required:
            self.assertIn(phrase.lower(), lowered, phrase)
        self.assertNotIn("plywood", lowered)
        self.assertNotIn("tested load rating: ", lowered)
        for stale in (
            "three accessible top wedges",
            "six top wedges",
            "three top tenons",
            "all four wedges per half",
            "two top wedges",
            "one spring wedge",
            "three wedges per half",
        ):
            self.assertNotIn(stale, lowered, stale)

    def test_geometry_mechanics_movement_and_installation_contract(self) -> None:
        required = (
            "3 / 6 / 9",
            "3 + 6 = 9",
            "6 in",
            "1514.475",
            "177.55",
            "733.675",
            "173.15",
            "173.95",
            "37.7825",
            "879.7925",
            "171.95",
            "18.8 mm structural clearance",
            "30.2325",
            "4.2325",
            "8.6325",
            "seven through",
            "four return",
            "final-X",
            "two top positive quarter-turn cross-keys",
            "one spring cross-key",
            "open-bottom receivers",
            "upward from below",
            "no whole-half longitudinal slide",
            "nine crown seams",
            "seven supported pier seams",
            "keeper strip",
            "single rear-bayonet tongue",
            "separate underside keeper-reach indexed quarter-turn pin",
            "indexed quarter-turn pin",
            "rail-free",
            "upper level first",
            "zero structural credit",
        )
        lowered = " ".join(self.corpus.lower().split())
        for phrase in required:
            self.assertIn(phrase.lower(), lowered, phrase)
        self.assertNotIn("42 stitch-rail segments, 76 rail pins", self.corpus)
        self.assertNotIn("167.15", self.corpus)
        self.assertNotIn("744.075", self.corpus)
        self.assertNotIn("8.4 mm structural arm clearance", lowered)
        self.assertNotIn("24.2325 mm nominal", lowered)
        self.assertNotIn("16.062", self.corpus)
        self.assertNotIn("32.124", self.corpus)
        self.assertNotIn("split-tail profile and round head in the bed plane", lowered)
        self.assertIn("split plane perpendicular to the plate", lowered)
        self.assertNotIn("fit saddles and front/rear rail trains", lowered)
        self.assertNotIn("install the sliding saddle", lowered)

    def test_measurement_and_physical_test_gates_are_explicit(self) -> None:
        required = (
            "printer model",
            "nozzle diameter",
            "build-plate",
            "black-PETG manufacturer",
            "target contents load",
            "loaded height",
            "corner angle",
            "wall bow",
            "stud/blocking",
            "head/washer outside diameter",
            "thread embedment",
            "utility-clearance method",
            "maximum driver",
            "straight-approach",
            "drying method",
            "lower level — 5 ft through wall",
            "upper level — 5 ft through wall",
            "lower level — 3 ft return wall",
            "upper level — 3 ft return wall",
            "1 hour",
            "24 hours",
            "7 days",
            "30 days",
            "90 days",
            "72 hours",
            "teardown",
        )
        lowered = self.corpus.lower()
        for phrase in required:
            self.assertIn(phrase.lower(), lowered, phrase)

    def test_required_load_cases_and_original_mechanism_reconciliation_are_explicit(self) -> None:
        protocol = " ".join(self.documents["TEST_PROTOCOL.md"].lower().split())
        for phrase in (
            "crown-point-load case",
            "asymmetric/torsional-load case",
            "whole-article thermal cycling",
            "coupon thermal cycling is useful screening but is not the whole-article substitute",
            "destructive load-to-failure, separate specimen",
            "separate matched destructive specimen",
        ):
            self.assertIn(phrase, protocol, phrase)

        engineering = self.documents["ENGINEERING_DESIGN.md"].lower()
        for phrase in (
            "original named-mechanism reconciliation",
            "integrated caps replace the sliding saddles/pins",
            "fixed-diaphragm/cap topology replaces floating front keys",
            "119 optional printed objects",
            "installed package count and structural credit are both zero",
        ):
            self.assertIn(phrase, engineering, phrase)

    def test_generated_status_mass_and_print_time_language_are_current(self) -> None:
        readme = self.documents["README.md"]
        changelog = self.documents["CHANGELOG_ENTRY.md"]
        self.assertIn("32.000674", readme)
        self.assertIn("No authoritative print-time estimate is available", readme)
        self.assertIn("has emitted all five canonical", readme)
        self.assertNotIn("Full-set integration must still create", readme)
        self.assertNotIn("### Not yet released", changelog)
        self.assertNotIn("must still pass before any named artifact", changelog)
        self.assertIn("119 optional printed", changelog)
        self.assertIn("32.000674", self.progress)
        self.assertIn("119 optional printed", self.progress)
        self.assertNotIn("122 pieces", self.progress)
        self.assertNotIn("remain in\n  progress", self.progress)

    def test_rendering_and_package_status_cannot_be_mistaken_for_release(self) -> None:
        self.assertIn("artist rendering is visual intent only", self.corpus.lower())
        self.assertIn("drawings govern", self.corpus.lower())
        readme = self.documents["README.md"]
        self.assertIn(
            "assets/artist_rendering_all_petg_two_level_exact_6_plus_3.png",
            readme,
        )
        self.assertIn("assets/artist_rendering_all_petg_two_level.png", readme)
        self.assertIn("assets/artist_rendering_all_petg_two_level.prompt.md", readme)
        self.assertIn("current visual-intent hero", readme)
        self.assertIn("preserved as visual-development history", readme)
        for document in ("README.md", "PRINT_ME_FIRST.md", "CHANGELOG_ENTRY.md"):
            payload = self.documents[document]
            for package_id in PACKAGE_ORDER:
                self.assertIn(package_id, payload, (document, package_id))
                self.assertIn(
                    PACKAGE_FILENAMES[package_id],
                    payload,
                    (document, package_id),
                )
        self.assertIn("frozen", self.documents["README.md"].lower())
        for count in EXPECTED_EXACT_PACKAGE_COUNTS.values():
            self.assertIn(f"| {count} |", self.documents["README.md"])
        self.assertIn("does not mean", self.documents["PRINT_ME_FIRST.md"].lower())
        self.assertIn("does not imply", self.documents["CHANGELOG_ENTRY.md"].lower())
        self.assertNotIn("ready to print", self.documents["README.md"].lower())

    def test_obsolete_keeper_orientation_and_package_phrases_are_absent(self) -> None:
        lowered = " ".join(self.corpus.lower().split())
        for obsolete in (
            "flat carrier back",
            "integral flex hooks",
            "integral catches",
            "purpose placeholders",
            "package-purpose placeholders",
            "release-generator placeholders",
            "not finalized filenames",
            "bundle names are not yet frozen",
        ):
            self.assertNotIn(obsolete, lowered, obsolete)
        self.assertIn("decorated `d=0` face", lowered)
        self.assertIn("receiver housings upward", lowered)
        self.assertIn("one rear-bayonet tongue", lowered)
        self.assertIn("separate keeper-reach indexed quarter-turn pin", lowered)

    def test_local_markdown_links_are_relative_and_resolve_when_not_fragments(self) -> None:
        link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for name, payload in self.documents.items():
            for target in link_pattern.findall(payload):
                self.assertFalse(target.startswith(("/", "file:", "~")), (name, target))
                if target.startswith(("http://", "https://", "#")):
                    continue
                path_text = target.split("#", 1)[0]
                if path_text.startswith("generated/"):
                    self.assertIn(("generated", "generated"), STAGED_TREE_MAP)
                    continue
                candidates = (DOCS / path_text, R6 / path_text, REPO / path_text)
                self.assertTrue(any(path.exists() for path in candidates), (name, target))

    def test_no_owner_absolute_paths_or_gcode_files_are_named(self) -> None:
        forbidden = (
            "/" + "Users/",
            "file://",
            ".gcode",
            "Bambu Lab A1 mini with a 0.4",
        )
        for token in forbidden:
            self.assertNotIn(token, self.corpus, token)


if __name__ == "__main__":
    unittest.main()
