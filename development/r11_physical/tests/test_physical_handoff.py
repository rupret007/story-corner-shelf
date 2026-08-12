from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import re
import sys
import unittest
import xml.etree.ElementTree as ET


PHYSICAL = Path(__file__).resolve().parents[1]
PROJECT_ROOT = PHYSICAL.parents[1]
R11 = PROJECT_ROOT / "development" / "r11"


def read(relative: str) -> str:
    return (PHYSICAL / relative).read_text(encoding="utf-8")


class PhysicalHandoffTests(unittest.TestCase):
    def test_beginner_guide_keeps_the_tabletop_boundary(self) -> None:
        text = read("README.md")
        normalized = " ".join(text.split())
        for token in (
            "0 kg / 0 lb",
            "No sanding",
            "No sanding, file, lubricant, heat, glue, tools, force",
            "cycle 1",
            "cycle 5",
            "cycle 10",
            "does **not** authorize more printing",
        ):
            self.assertIn(token, normalized)

    def test_physical_record_binds_exact_articles_without_overclaim(self) -> None:
        text = read("PHYSICAL_RECORD.md")
        for token in (
            "r11_bay0_left_terminal_integrated_half_deck",
            "ff6793255147413b9845dbc771a5b2e5581c1dcbbdcfe5e39b2a7cdb8e6bcbfc",
            "5fe65ebfda9f1d3df77f3db99485983b6313e829a202b536b89b15d2eaea12d1",
            "r11_bay0_right_terminal_integrated_half_deck",
            "354dfb1e3ef4ca88aff30333d3154f7f3de1618f90f3e00a37d1aa5c49b30598",
            "b714da3ad19d553b74389d9ffb1abbc9903a34662f3fba3f2b79397d13e6ceea",
            "PRINT IN PROGRESS / OUTCOME NOT RECORDED",
            "not established",
            "0 kg / 0 lb",
        ):
            self.assertIn(token, text)

    def test_visuals_are_static_accessible_and_safety_labeled(self) -> None:
        requirements = {
            "visuals/one_bay_dry_fit_steps.svg": (
                "WALL SIDE",
                "FRONT EDGE",
                "LEFT HALF",
                "RIGHT HALF",
                "MAKE THE FIRST GENTLE FIT",
                "INSPECT THE JOINED PAIR",
                "REVERSE • CHECK 1 / 5 / 10",
                "CYCLE 1",
                "CYCLE 5",
                "CYCLE 10",
                "No sanding",
            ),
            "visuals/joint_closeups.svg": (
                "THREE RECIPROCAL LAP ROWS",
                "OUTWARD (away from wall)",
                "KEYSTONE LOCKS SEPARATION ONLY",
                "Keystone carries no gravity load",
                "no sanding, force, tools, glue, wall mounting, or load",
            ),
        }
        for relative, tokens in requirements.items():
            payload = (PHYSICAL / relative).read_bytes()
            root = ET.fromstring(payload)
            self.assertTrue(root.findall("{http://www.w3.org/2000/svg}title"))
            self.assertTrue(root.findall("{http://www.w3.org/2000/svg}desc"))
            lowered = payload.lower()
            for forbidden in (b"<script", b"javascript:", b"<image", b"href="):
                self.assertNotIn(forbidden, lowered, relative)
            text = payload.decode("utf-8")
            for token in tokens:
                self.assertIn(token, text, relative)

    def test_cleaned_photo_is_bound_and_declared_non_evidence(self) -> None:
        image = PHYSICAL / "photos" / "left-half-clean-reference.png"
        payload = image.read_bytes()
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "a8d6ae08c5cc06fe8967a1790233a1adceac7dd102651eadc38584cd67bccbd4",
        )
        provenance = read("photos/README.md")
        normalized = " ".join(provenance.replace("**", "").split())
        self.assertIn("not a measurement image", normalized)
        self.assertIn("generative editing is\n  not pixel-preserving", provenance)
        self.assertNotIn("/tmp/codex-remote-attachments", provenance)
        self.assertNotRegex(provenance, r"(?i)placeholder|todo|fill me")
        guide = read("README.md")
        self.assertIn("photos/left-half-clean-reference.png", guide)
        self.assertIn("Do not use the\ncleaned image for dimensions", guide)

    def test_private_source_photo_references_are_exact_and_path_private(self) -> None:
        provenance = read("photos/README.md")
        expected = (
            "646c31b35bb67188e77abfd92c3c09e2c420d675fdaab9f34cffaf3cc2e8583c",
            "631b42988708b731505988ef9e332e2ae5fa77266d86bb25008347c0b089ddac",
            "e8334c57ccf887436a1bdffefe264ca654a92a457f584e462b8a34316656d03d",
            "917b03245b5172897cb30f4c11e0f384d5a3abc514988e67968b74a1104fb8ae",
            "96b0d66046600eb1dbbf3e7494eed748a388058abdfeb445df750eaa8fd37016",
            "cb4d2d05cf6f2a443a67ef170cbc41339ac437c3c163f4d98e6c07a6b36faef9",
            "c5673ec24bef7b7bd1cad602716335ee2f3bdfb6fc85e955b5dc6f59d4367483",
            "87546c71d436c587fe3f742a41212e9cd5d60cb642de905d059456c0ed6b68a9",
            "6636e852ba4d0e40dd4f7dcdac8304c59b4267f397bee0f5a03f3d9f9ca37fe2",
        )
        for digest in expected:
            self.assertEqual(provenance.count(digest), 1)
        self.assertNotIn("codex-remote-attachments", provenance)

    def test_local_document_links_resolve_or_are_documented_frozen_errata(self) -> None:
        markdown_files = sorted(PHYSICAL.rglob("*.md"))
        pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        for document in markdown_files:
            for target in pattern.findall(document.read_text(encoding="utf-8")):
                if target.startswith(("https://", "http://", "#")):
                    continue
                clean = target.split("#", 1)[0]
                self.assertTrue((document.parent / clean).resolve().exists(), f"{document}: {target}")
        errata = read("FROZEN_ARTIFACT_ERRATA.md")
        self.assertEqual(errata.count("`../r10/README.md`"), 2)
        self.assertIn("artifact bytes remain unchanged", read("README.md"))

    def test_layout_and_geometry_agree_on_four_terminal_halves(self) -> None:
        sys.path.insert(0, str(R11))
        try:
            layout = importlib.import_module("layout")
            geometry = importlib.import_module("integrated_geometry")
            plan = layout.build_plan()
            bays = plan["layout"]["bay_stations"]
            self.assertEqual(
                [(bay["left_half_kind"], bay["right_half_kind"]) for bay in bays],
                [
                    ("terminal", "terminal"),
                    ("regular", "regular"),
                    ("regular", "regular"),
                    ("regular", "regular"),
                    ("regular", "regular"),
                    ("terminal", "terminal"),
                ],
            )
            self.assertEqual(
                plan["printed_piece_counts"]["terminal_integrated_half_decks"], 4
            )
            self.assertEqual(
                plan["printed_piece_counts"]["regular_integrated_half_decks"], 8
            )
            evidence = geometry.field_inventory_evidence()
            self.assertEqual(evidence.terminal_half_decks, 4)
            self.assertEqual(evidence.regular_half_decks, 8)
            self.assertTrue(evidence.first_and_last_bays_use_two_terminal_halves_each)
        finally:
            sys.path.remove(str(R11))

    def test_public_routers_are_mirrored_and_point_to_physical_handoff(self) -> None:
        self.assertEqual(
            (PROJECT_ROOT / "README.md").read_bytes(),
            (PROJECT_ROOT / "docs" / "README.md").read_bytes(),
        )
        self.assertEqual(
            (PROJECT_ROOT / "PRINT_ME_FIRST.md").read_bytes(),
            (PROJECT_ROOT / "docs" / "PRINT_ME_FIRST.md").read_bytes(),
        )
        for relative in ("README.md", "PRINT_ME_FIRST.md", "PROGRESS.md"):
            text = (PROJECT_ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("development/r11_physical/README.md", text)
            self.assertIn("0 kg / 0 lb", text)

    def test_publication_manifest_identifies_current_router_sources_truthfully(self) -> None:
        manifest = json.loads(
            (PROJECT_ROOT / "PUBLICATION_MANIFEST.json").read_text(encoding="utf-8")
        )
        by_destination = {record["destination"]: record for record in manifest["files"]}
        expected_sources = {
            "README.md": "docs/README.md",
            "docs/README.md": "docs/README.md",
            "PRINT_ME_FIRST.md": "docs/PRINT_ME_FIRST.md",
            "docs/PRINT_ME_FIRST.md": "docs/PRINT_ME_FIRST.md",
            "PROGRESS.md": "PROGRESS.md",
        }
        for destination, source in expected_sources.items():
            record = by_destination[destination]
            self.assertEqual(record["source_scope"], "current_router_overlay")
            self.assertEqual(record["source"], source)
            self.assertEqual(
                hashlib.sha256((PROJECT_ROOT / source).read_bytes()).hexdigest(),
                record["sha256"],
            )

    def test_public_device_binding_tradeoff_is_explicit(self) -> None:
        text = read("PRIVACY_NOTE.md")
        normalized = " ".join(text.split())
        for token in (
            "does **not** publish the raw printer serial",
            "stable device fingerprint",
            "fail closed",
            "identifier, not a credential",
            "explicit review and authorization",
        ):
            self.assertIn(token, normalized)

    def test_next_engineer_prompt_is_complete_and_fail_closed(self) -> None:
        text = read("NEXT_ENGINEER_PROMPT.md")
        normalized = " ".join(text.split())
        for token in (
            "0 kg / 0 lb",
            "PRINT IN PROGRESS / OUTCOME NOT RECORDED",
            "No sanding",
            "cycles 1, 5, and 10",
            "never use git add . or git add -A",
            "full root unittest discovery suite",
            "R6 source-only and full release checks",
            "run all R7, R8, R9, and R10 tests",
            "zero skips and zero failures",
            "two fresh builds",
            "Monitor every new GitHub Actions run to completion",
            "fresh, explicit authorization",
        ):
            self.assertIn(token, normalized)
        self.assertIn("NEXT_ENGINEER_PROMPT.md", read("README.md"))
        self.assertNotIn("/Users/", text)
        self.assertNotIn("/private/tmp/", text)
        self.assertNotRegex(text, r"(?i)print_authorized\s*[:=]\s*true")


if __name__ == "__main__":
    unittest.main()
