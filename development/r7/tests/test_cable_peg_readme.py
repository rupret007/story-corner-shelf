#!/usr/bin/env python3
"""Focused regression checks for the novice R7 Bambu/PETG handoff."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


R7_ROOT = Path(__file__).resolve().parents[1]
README = R7_ROOT / "README.md"
EXACT_PROOF_PNG = R7_ROOT / "assets" / "cable_hook_location_proof_exact.png"
EXACT_PROOF_MANIFEST = (
    R7_ROOT / "assets" / "cable_hook_location_proof_exact.manifest.json"
)
CAD_PROOF_PNG = R7_ROOT / "assets" / "cable_hook_cad_proof_v4.png"


class R7CablePegReadmeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = README.read_text(encoding="utf-8")
        cls.compact = " ".join(cls.text.split())
        cls.lowered = cls.compact.lower()
        cls.plain = " ".join(
            cls.lowered.translate(
                {ord(character): None for character in "`*_>"}
            ).split()
        )

    def test_v4_is_active_and_v1_through_v3_are_superseded(self) -> None:
        self.assertIn("cable_peg_qualification_v4", self.text)
        self.assertIn("MODEL_ONLY_R7_CABLE_PEG_COLUMN_QUALIFICATION.3mf", self.text)
        self.assertIn(
            "`cable_peg_qualification_v1`, `cable_peg_qualification_v2`, and "
            "`cable_peg_qualification_v3` are superseded",
            self.compact,
        )
        self.assertNotIn(
            "--output development/r7/generated/cable_peg_qualification_v3",
            self.text,
        )
        self.assertNotIn(
            "cable_peg_qualification_v3/model_only_3mf/",
            self.text,
        )
        self.assertIn(
            "cable_peg_qualification_v4_pre_serialization_fix_SUPERSEDED",
            self.text,
        )
        self.assertIn(
            "STL/individual-3MF/canonical-package geometry bijection",
            self.text,
        )

    def test_visual_is_prominently_non_governing(self) -> None:
        for phrase in (
            "ai visual-intent image only",
            "v2 rendering",
            "not a build diagram",
            "exact hook count and permitted locations",
            "governed by the generated cad, configuration, and schematic",
            "not by the ai rendering",
        ):
            self.assertIn(phrase, self.plain, phrase)
        self.assertIn(
            "assets/artist_rendering_all_petg_two_level_cable_pegs_concept_v2.png",
            self.text,
        )
        self.assertIn(
            "assets/artist_rendering_all_petg_two_level_cable_pegs_concept_v2.prompt.md",
            self.text,
        )

    def test_exact_schematic_is_the_count_and_location_authority(self) -> None:
        for path in (
            "assets/cable_hook_location_proof_exact.png",
            "assets/cable_hook_location_proof_exact.svg",
            "assets/cable_hook_location_proof_exact.manifest.json",
            "assets/cable_hook_location_proof_exact.NOTES.md",
        ):
            self.assertIn(path, self.text, path)
            self.assertTrue((R7_ROOT / path).is_file(), path)
        for phrase in (
            "deterministic schematic above is the placement-and-count authority",
            "l2–l7",
            "r2–r4",
            "nine authorized hook stations on each shelf level",
            "l1 and r1",
            "exactly 18 authorized hook locations",
            "four excluded stations",
            "station spacing in this schematic is diagrammatic",
        ):
            self.assertIn(phrase, self.plain, phrase)

        self.assertEqual(
            hashlib.sha256(EXACT_PROOF_PNG.read_bytes()).hexdigest(),
            "a14410d8b629a5a9fd864ae009e18662c6ee4f3d27e39dffd8c863d705aeda29",
        )
        manifest = json.loads(EXACT_PROOF_MANIFEST.read_text(encoding="utf-8"))
        placement = manifest["placement_contract"]
        self.assertEqual(placement["authorized_hooks_per_level"], 9)
        self.assertEqual(placement["authorized_hooks_total"], 18)
        self.assertEqual(placement["excluded_hooks_per_level"], 2)
        self.assertEqual(placement["excluded_hooks_total"], 4)

    def test_neutral_model_warning_and_geometry_lock_are_explicit(self) -> None:
        for phrase in (
            "neutral model-only 3mf",
            "contains no g-code or toolpath",
            "does not embed or select the printer",
            "never reuse, copy, or edit a pla profile",
            "100% on x, y, and z",
            "do not use auto arrange, auto orient",
            "lay on face",
            "repair operation that changes geometry",
            "keep the v4 saved positions and orientations",
            "left tapered run-side jaw face flat on the plate",
        ):
            self.assertIn(phrase, self.plain, phrase)

    def test_exact_v4_cad_proof_is_linked_and_fail_closed(self) -> None:
        for path in (
            "assets/cable_hook_cad_proof_v4.png",
            "assets/cable_hook_cad_proof_v4.svg",
            "assets/cable_hook_cad_proof_v4.manifest.json",
            "assets/render_cable_hook_cad_proof_v4.py",
        ):
            self.assertIn(path, self.text, path)
            self.assertTrue((R7_ROOT / path).is_file(), path)
        self.assertEqual(
            hashlib.sha256(CAD_PROOF_PNG.read_bytes()).hexdigest(),
            "d68b40b9fb3129f85629a0d265d64c0220016f075e4628d03ba6b710c658dab4",
        )
        for phrase in (
            "rendered from the frozen v4 hook stl",
            "18 mm cable seat",
            "maximum 5 mm cable envelope",
            "manual 1.6 mm per-jaw pre-spread",
            "not evidence of printed fit, fatigue, creep, load capacity, or production readiness",
        ):
            self.assertIn(phrase, self.plain, phrase)

    def test_exact_bambu_and_sunlu_profile_is_frozen(self) -> None:
        for phrase in (
            "bambu studio 2.7.1.62",
            "bambu lab a1 mini 0.4 nozzle",
            "textured pei plate",
            "sunlu petg @bbl a1m 0.4 nozzle",
            "0.20mm strength @bbl a1m",
            "250 °c",
            "245 °c",
            "60 °c",
            "flow ratio",
            "0.94",
            "maximum volumetric speed",
            "9 mm³/s",
            "wall loops",
            "top / bottom shell layers",
            "5 / 3",
            "25%",
            "grid",
        ):
            self.assertIn(phrase, self.plain, phrase)

    def test_petg_preparation_and_cool_removal_are_beginner_explicit(self) -> None:
        for phrase in (
            "60–65 °c for 6–8 hours",
            "dishwashing detergent and water",
            "do not use acetone",
            "do not touch the cleaned print area",
            "petg—not pla",
            "35 °c or below",
            "do not pry hot petg",
        ):
            self.assertIn(phrase, self.plain, phrase)

    def test_brim_and_support_ui_fields_are_exact(self) -> None:
        for phrase in (
            "`brim type` to `outer brim only`",
            "`brim width` to `5 mm`",
            "inherited `brim-object gap` of `0.1 mm`",
            "`enable support` off",
            "`enable support` on",
            "`type` to `normal(auto)`",
            "`on build plate only`",
        ):
            self.assertIn(phrase, self.lowered, phrase)

    def test_two_job_order_preview_and_stop_contract_are_explicit(self) -> None:
        ladder_heading = self.text.index("## Print job 1 — clearance ladder first")
        pair_heading = self.text.index("## Print job 2 — parent coupon plus collar-hook")
        self.assertLess(ladder_heading, pair_heading)
        self.assertIn("/individual_model_only_3mf/", self.text)
        self.assertIn(
            "v4 includes the plate-edge translation required by the 5 mm outer brim",
            self.plain,
        )
        for phrase in (
            "set selection unprintable",
            "move the layer slider through every layer",
            "do not dismiss a warning",
            "inside the a1 mini printable boundary",
            "stop the print immediately",
            "lifting or curling",
            "nozzle contact or scraping",
            "missing or intermittent extrusion",
            "clicking or popping from wet petg",
            "severe stringing",
            "layer separation",
        ):
            self.assertIn(phrase, self.plain, phrase)

    def test_zero_load_and_qualification_only_status_cannot_be_missed(self) -> None:
        for phrase in (
            "qualification-only, zero-rated-load",
            "present rated load is zero",
            "a printed part is still a test specimen",
            "not an approved cable hanger",
            "hook loads never contribute to the shelf rating",
        ):
            self.assertIn(phrase, self.plain, phrase)

    def test_manual_insertion_and_real_assembly_load_fixture_are_explicit(self) -> None:
        for phrase in (
            "square rear lips have no automatic insertion cam",
            "manually pre-spread each jaw by at least 1.6 mm",
            "never force insertion by pushing, pulling, or levering on the hook tip",
            "three-object coupon plate qualifies only clearance, fit, and snap behavior",
            "cannot qualify the hook load path",
            "every proof, cycle, creep, and migration load gate",
            "exact printed overlay installed on its real relevant r6 x-corbel/full assembly",
            "cable seat exactly 18.0 mm from the overlay visible face",
            "tip-applied load is prohibited",
            "maximum qualified cable or bundle outside diameter is 5 mm",
        ):
            self.assertIn(phrase, self.plain, phrase)


if __name__ == "__main__":
    unittest.main()
