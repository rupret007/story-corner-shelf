from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


R11_ROOT = Path(__file__).resolve().parents[1]
if str(R11_ROOT) not in sys.path:
    sys.path.insert(0, str(R11_ROOT))

import generate_qualification as generator  # noqa: E402
import release_status  # noqa: E402


class R11QualificationBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.geometry_gate = release_status.geometry_gate_report()
        cls.first: Path | None = None
        cls.second: Path | None = None
        if cls.geometry_gate["passed"] is True:
            cls.first = generator.build_bundle(cls.root / "first")
            cls.second = generator.build_bundle(cls.root / "second")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_incomplete_geometry_fails_before_creating_any_output(self) -> None:
        target = self.root / "missing-provider-parent" / "must_not_exist"
        with mock.patch.object(
            release_status, "_support_cable_module", return_value=None
        ):
            with self.assertRaises(generator.QualificationGeometryIncomplete):
                generator.build_bundle(target)
        self.assertFalse(target.exists())
        self.assertFalse(target.parent.exists())

    def test_two_complete_builds_are_byte_identical_when_geometry_is_complete(self) -> None:
        if self.geometry_gate["passed"] is not True:
            self.skipTest("waiting for exact R11 support/cable saved-mesh provider")
        assert self.first is not None and self.second is not None
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

    def test_completed_bundle_has_exact_inventory_allowlist_and_neutral_boundary(self) -> None:
        if self.geometry_gate["passed"] is not True:
            self.skipTest("waiting for exact R11 support/cable saved-mesh provider")
        assert self.first is not None
        manifest = generator.validate_bundle(self.first)
        validation = json.loads(
            (self.first / "validation.json").read_text(encoding="utf-8")
        )
        layout_report = json.loads(
            (self.first / "layout_report.json").read_text(encoding="utf-8")
        )
        self.assertTrue(
            layout_report["release"][
                "checked_neutral_qualification_artifact_generation_allowed"
            ]
        )
        self.assertEqual(tuple(manifest["object_names_in_order"]), generator.PART_ORDER)
        self.assertEqual(len(manifest["object_names_in_order"]), 8)
        self.assertEqual(
            sorted(manifest["exact_file_allowlist"]),
            release_status._expected_bundle_paths(),
        )
        self.assertEqual(
            manifest["publication_boundary"], release_status.PUBLICATION_BOUNDARY
        )
        bundled_visual = self.first / generator.ASSEMBLY_VISUAL_RELATIVE_PATH
        source_visual = R11_ROOT / generator.ASSEMBLY_VISUAL_RELATIVE_PATH
        visual_report = release_status.inspect_assembly_visual(bundled_visual)
        self.assertEqual(bundled_visual.read_bytes(), source_visual.read_bytes())
        self.assertEqual(manifest["assembly_visual"], visual_report)
        self.assertEqual(validation["assembly_visual"], visual_report)
        self.assertTrue(validation["both_bay0_half_decks_are_terminal_length"])
        self.assertFalse(validation["full_wall_set"])
        self.assertFalse(validation["print_authorized"])
        self.assertFalse(validation["wall_installation_authorized"])
        self.assertFalse(validation["drilling_schedule_released"])
        self.assertFalse(validation["drilling_coordinates_released"])
        self.assertFalse(validation["test_load_authorized"])
        self.assertEqual(
            (validation["rated_load_kg"], validation["rated_load_lb"]),
            (0.0, 0.0),
        )
        filenames = [
            path.name.lower() for path in self.first.rglob("*") if path.is_file()
        ]
        self.assertFalse(
            any(
                name.endswith((".gcode", ".bgcode", ".gco"))
                or "slicer_profile" in name
                or "toolpath" in name
                for name in filenames
            )
        )

    def test_completed_bundle_tampering_and_replacement_are_rejected(self) -> None:
        if self.geometry_gate["passed"] is not True:
            self.skipTest("waiting for exact R11 support/cable saved-mesh provider")
        assert self.first is not None
        with self.assertRaises(FileExistsError):
            generator.build_bundle(self.first)
        tampered = self.root / "tampered"
        shutil.copytree(self.first, tampered)
        readme = tampered / "README.md"
        readme.write_bytes(readme.read_bytes() + b"tampered\n")
        with self.assertRaises(ValueError):
            generator.validate_bundle(tampered)

    def test_manifest_safety_boundary_tampering_is_rejected(self) -> None:
        if self.geometry_gate["passed"] is not True:
            self.skipTest("waiting for exact R11 support/cable saved-mesh provider")
        assert self.first is not None
        tampered = self.root / "tampered-manifest-boundary"
        shutil.copytree(self.first, tampered)
        manifest_path = tampered / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["publication_boundary"]["print_authorized"] = True
        manifest_path.write_text(
            json.dumps(manifest, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            generator.validate_bundle(tampered)

    def test_unexpected_artifact_injection_is_rejected(self) -> None:
        if self.geometry_gate["passed"] is not True:
            self.skipTest("waiting for exact R11 support/cable saved-mesh provider")
        assert self.first is not None
        tampered = self.root / "tampered-extra-file"
        shutil.copytree(self.first, tampered)
        (tampered / "unexpected.txt").write_text("not allowlisted\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            generator.validate_bundle(tampered)


if __name__ == "__main__":
    unittest.main()
