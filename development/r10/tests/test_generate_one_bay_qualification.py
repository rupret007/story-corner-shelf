#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest


R10_ROOT = Path(__file__).resolve().parents[1]
if str(R10_ROOT) not in sys.path:
    sys.path.insert(0, str(R10_ROOT))

import generate_one_bay_qualification as generator  # noqa: E402


class R10QualificationBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.first = generator.build_bundle(cls.root / "first")
        cls.second = generator.build_bundle(cls.root / "second")
        cls.manifest = generator.validate_bundle(cls.first)
        cls.validation = json.loads(
            (cls.first / "validation.json").read_text(encoding="utf-8")
        )
        cls.status = json.loads(
            (cls.first / "release_status.json").read_text(encoding="utf-8")
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_two_complete_builds_are_byte_identical(self) -> None:
        self.assertEqual(
            generator.tree_evidence(self.first), generator.tree_evidence(self.second)
        )
        first_paths = sorted(
            path.relative_to(self.first)
            for path in self.first.rglob("*")
            if path.is_file()
        )
        for relative in first_paths:
            self.assertEqual(
                (self.first / relative).read_bytes(),
                (self.second / relative).read_bytes(),
            )

    def test_inventory_is_exact_one_bay_plus_first_wall_cable_set(self) -> None:
        order = tuple(self.manifest["object_names_in_order"])
        self.assertEqual(order, generator.PART_ORDER)
        self.assertEqual(
            tuple(self.manifest["core_one_bay_part_order"]),
            generator.CORE_PART_ORDER,
        )
        self.assertEqual(
            tuple(self.manifest["cable_bookend_part_order"]),
            generator.CABLE_PART_ORDER,
        )
        self.assertEqual(len(order), 16)
        self.assertEqual(len(set(order)), 16)
        self.assertEqual(self.validation["actual_lincoln_log_one_bay_article_count"], 12)
        self.assertEqual(self.validation["first_wall_s0_cable_candidate_article_count"], 4)
        for name in order:
            self.assertTrue(
                (self.first / "stl" / f"{name}.stl").is_file(), name
            )
            self.assertTrue(
                (
                    self.first
                    / "individual_model_only_3mf"
                    / f"MODEL_ONLY_{name}.3mf"
                ).is_file(),
                name,
            )

    def test_bundle_is_neutral_unsliced_and_catalog_is_off_plate(self) -> None:
        boundary = self.manifest["publication_boundary"]
        self.assertTrue(boundary["qualification_only"])
        self.assertTrue(boundary["model_only_neutral_3mf"])
        self.assertTrue(boundary["fresh_human_permission_required_before_every_print"])
        self.assertFalse(boundary["production_set"])
        self.assertFalse(boundary["slicer_profile_present"])
        self.assertFalse(boundary["gcode_or_toolpath_present"])
        self.assertFalse(boundary["installation_or_drilling_authorized"])
        self.assertFalse(boundary["load_rating_created"])
        self.assertTrue(self.validation["catalog"]["off_plate_inspection_only"])
        self.assertTrue(self.validation["catalog"]["do_not_print"])
        suffixes = {path.suffix.lower() for path in self.first.rglob("*") if path.is_file()}
        self.assertFalse({".gcode", ".bgcode", ".gco"}.intersection(suffixes))

    def test_manifest_binds_controlling_r10_documents_and_sources(self) -> None:
        source_paths = {record["path"] for record in self.manifest["source_records"]}
        self.assertIn("requirements.txt", source_paths)
        for relative in (
            "development/r10/ASSEMBLY.md",
            "development/r10/DESIGN_REQUIREMENTS.md",
            "development/r10/GUIDELINES.md",
            "development/r10/LOAD_QUALIFICATION.md",
            "development/r10/MATERIALS_AND_HARDWARE.md",
            "development/r10/PRINT_FIRST.md",
            "development/r10/README.md",
            "development/r10/cable_bookend.py",
            "development/r10/capacity_study.py",
            "development/r10/config.json",
            "development/r10/full_wall_plan.py",
            "development/r10/generate_one_bay_qualification.py",
            "development/r10/lincoln_geometry.py",
            "development/r10/model_io.py",
            "development/r10/release_status.py",
        ):
            self.assertIn(relative, source_paths)

    def test_bundle_carries_exact_handoff_documents_and_assembly_visual(self) -> None:
        self.assertEqual(
            tuple(self.validation["included_handoff_documents"]),
            generator.HANDOFF_DOCUMENTS,
        )
        for document in generator.HANDOFF_DOCUMENTS:
            self.assertEqual(
                (self.first / document).read_bytes(),
                (R10_ROOT / document).read_bytes(),
            )
        self.assertEqual(
            (self.first / generator.ASSEMBLY_VISUAL_FILENAME).read_bytes(),
            (
                R10_ROOT
                / "visuals"
                / "r10_one_bay_exploded_and_first_wall_topology.svg"
            ).read_bytes(),
        )
        self.assertEqual(
            (self.first / "requirements.txt").read_bytes(),
            (generator.PROJECT_ROOT / "requirements.txt").read_bytes(),
        )

    def test_aggregate_artifact_gate_passes_but_physical_print_and_install_do_not(self) -> None:
        self.assertTrue(self.status["artifact_gate"]["passed"])
        self.assertTrue(self.status["qualification_bundle_analytically_complete"])
        self.assertFalse(self.status["all_physical_gates_complete"])
        self.assertFalse(self.status["print_authorized"])
        self.assertFalse(self.status["wall_installation_authorized"])
        self.assertEqual((self.status["rated_load_kg"], self.status["rated_load_lb"]), (0.0, 0.0))

    def test_publication_is_no_replace(self) -> None:
        with self.assertRaises(FileExistsError):
            generator.build_bundle(self.first)

    def test_artifact_tampering_fails_the_strict_hash_audit(self) -> None:
        tampered = self.root / "tampered"
        shutil.copytree(self.first, tampered)
        readme = tampered / "README.md"
        readme.write_bytes(readme.read_bytes() + b"tampered\n")
        with self.assertRaises(ValueError):
            generator.validate_bundle(tampered)

    def test_print_first_is_actual_article_fail_fast_order(self) -> None:
        text = (self.first / "PRINT_FIRST.md").read_text(encoding="utf-8")
        for phrase in (
            "Gate A — midpoint Lincoln-log interface",
            "Gate B — one support-capture interface",
            "Gate C — complete one actual shelf cell",
            "Gate D — separate far-left S0 cable candidate",
            "fresh, explicit human",
            "fresh permission",
            "never auto-scale",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
