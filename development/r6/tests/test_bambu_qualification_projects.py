#!/usr/bin/env python3
"""Focused fail-closed tests for the unsliced Bambu qualification builder."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

import build_bambu_qualification_projects as bambu  # noqa: E402


class BambuQualificationBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifacts = bambu._manifest_artifacts(R6 / "generated" / "manifest.json")
        cls.source_dir = R6 / "generated" / "individual_model_only_3mf"

    def test_identity_transform_regression_accepts_explicit_and_omitted_identity(self) -> None:
        expected = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
        self.assertEqual(bambu._parse_transform(None), expected)
        self.assertEqual(bambu._parse_transform("1 0 0 0 1 0 0 0 1 0 0 0"), expected)
        self.assertTrue(bambu._identity_linear(expected))
        self.assertFalse(
            bambu._identity_linear((1.0, 0.0, 0.0, -1.0, 0.0, 1.0, 0.0, 0.0, 1.0))
        )
        with self.assertRaises(bambu.BambuQualificationError):
            bambu._parse_transform("1 0 0 0 1 0 0 0 1 nan 0 0")

    def test_fixed_projects_are_qualification_only_and_exclude_solid_screw_placeholder(self) -> None:
        self.assertEqual(len(bambu.PROJECT_SPECS), 4)
        sources = [name for spec in bambu.PROJECT_SPECS for name in spec.sources]
        self.assertEqual(len(sources), 7)
        self.assertEqual(len(sources), len(set(sources)))
        self.assertNotIn(bambu.EXCLUDED_SOURCE, sources)
        self.assertIn("solid", bambu.EXCLUDED_REASON.lower())
        self.assertIn("no screw bore", bambu.EXCLUDED_REASON.lower())
        crown = next(
            spec
            for spec in bambu.PROJECT_SPECS
            if spec.project_id == "crown_pin_support_brim_candidate"
        )
        self.assertEqual(crown.overrides["brim_type"], "outer_only")
        self.assertEqual(crown.overrides["brim_width"], "6")
        self.assertEqual(crown.overrides["enable_support"], "1")
        common = bambu._common_settings_expected()
        self.assertEqual(common["filament_vendor"], ["SUNLU"])
        self.assertEqual(common["sparse_infill_pattern"], "grid")
        self.assertEqual(common["top_shell_layers"], "5")
        self.assertEqual(common["bottom_shell_layers"], "3")
        self.assertEqual(common["fan_min_speed"], ["10"])
        self.assertEqual(common["fan_max_speed"], ["30"])
        self.assertEqual(common["overhang_fan_speed"], ["90"])

    def test_profile_catalog_recursively_flattens_inheritance_and_untyped_include(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r6-bambu-profile-") as directory:
            root = Path(directory)
            machine = root / "machine"
            machine.mkdir()
            (machine / "base.json").write_text(
                json.dumps(
                    {
                        "name": "base",
                        "type": "machine",
                        "from": "system",
                        "alpha": "base",
                        "shared": "base",
                    }
                ),
                encoding="utf-8",
            )
            (machine / "snippet.json").write_text(
                json.dumps({"name": "snippet", "machine_start_gcode": "G28"}),
                encoding="utf-8",
            )
            (machine / "child.json").write_text(
                json.dumps(
                    {
                        "name": "child",
                        "type": "machine",
                        "inherits": "base",
                        "include": ["snippet"],
                        "shared": "child",
                    }
                ),
                encoding="utf-8",
            )
            flattened, chain = bambu.ProfileCatalog(root).flatten("child", "machine")
        self.assertEqual(flattened["alpha"], "base")
        self.assertEqual(flattened["machine_start_gcode"], "G28")
        self.assertEqual(flattened["shared"], "child")
        self.assertEqual(flattened["inherits"], "")
        self.assertNotIn("include", flattened)
        self.assertEqual([node.name for node in chain], ["child", "base", "snippet"])

    def test_profile_catalog_rejects_cycles(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r6-bambu-profile-cycle-") as directory:
            root = Path(directory)
            machine = root / "machine"
            machine.mkdir()
            for name, parent in (("a", "b"), ("b", "a")):
                (machine / f"{name}.json").write_text(
                    json.dumps(
                        {"name": name, "type": "machine", "inherits": parent}
                    ),
                    encoding="utf-8",
                )
            catalog = bambu.ProfileCatalog(root)
            with self.assertRaises(bambu.BambuQualificationError):
                catalog.flatten("a", "machine")

    def test_all_seven_sources_are_exact_manifest_hashed_individual_3mfs(self) -> None:
        for spec in bambu.PROJECT_SPECS:
            for source_name in spec.sources:
                audit = bambu.audit_individual_source(
                    self.source_dir, source_name, self.artifacts
                )
                self.assertEqual(audit.source_name, source_name)
                self.assertGreater(audit.vertex_count, 0)
                self.assertGreater(audit.triangle_count, 0)
                self.assertEqual(len(audit.geometry_sha256_0p0001mm), 64)
                self.assertLessEqual(audit.bounds_mm[1][0], 180.0)
                self.assertLessEqual(audit.bounds_mm[1][1], 180.0)
                self.assertLessEqual(audit.bounds_mm[1][2], 180.0)

    def test_exact_source_assemblies_preserve_orientation_and_fit_a1_mini(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r6-bambu-source-assembly-") as directory:
            root = Path(directory)
            for spec in bambu.PROJECT_SPECS:
                audits = [
                    bambu.audit_individual_source(self.source_dir, name, self.artifacts)
                    for name in spec.sources
                ]
                path = root / spec.filename
                report = bambu.write_qualification_source_3mf(path, spec, audits)
                self.assertEqual(len(report["placed_bounds"]), len(audits))
                for record in report["placed_bounds"]:
                    self.assertTrue(
                        all(
                            0.0 <= record["bounds_mm"][0][axis]
                            <= record["bounds_mm"][1][axis]
                            <= 180.0 + 1.0e-6
                            for axis in range(3)
                        )
                    )

    def test_cli_command_is_unsliced_and_cannot_rotate_or_scale(self) -> None:
        command = bambu.build_bambu_command(
            Path("/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"),
            Path("source.3mf"),
            Path("output.3mf"),
            Path("machine.json"),
            Path("process.json"),
            Path("filament.json"),
        )
        self.assertIn("--export-3mf", command)
        self.assertEqual(command[command.index("--arrange") + 1], "0")
        for forbidden in ("--slice", "--orient", "--scale", "--rotate"):
            self.assertNotIn(forbidden, command)
        self.assertIn("--filament-colour=#000000", command)

    def test_geometry_digest_tolerates_bambu_recentering_drift_only_at_0p0001mm(self) -> None:
        def mesh(vertices: list[tuple[float, float, float]]) -> ET.Element:
            node = ET.Element(f"{{{bambu.NS_3MF}}}mesh")
            vertices_node = ET.SubElement(node, f"{{{bambu.NS_3MF}}}vertices")
            for x, y, z in vertices:
                ET.SubElement(
                    vertices_node,
                    f"{{{bambu.NS_3MF}}}vertex",
                    {"x": str(x), "y": str(y), "z": str(z)},
                )
            triangles = ET.SubElement(node, f"{{{bambu.NS_3MF}}}triangles")
            ET.SubElement(
                triangles,
                f"{{{bambu.NS_3MF}}}triangle",
                {"v1": "0", "v2": "1", "v3": "2"},
            )
            return node

        source = mesh(
            [(0.0, 0.0, 0.0), (152.2250061, 0.0, 0.0), (0.0, 159.6000061, 60.0)]
        )
        recentered = mesh(
            [
                (-76.1125, -79.8, -30.0),
                (76.1125099, -79.8, -30.0),
                (-76.1125, 79.8000092, 30.0000010),
            ]
        )
        self.assertEqual(bambu._mesh_evidence(source)[3], bambu._mesh_evidence(recentered)[3])

    def test_root_discovery_supports_development_and_flattened_publication_layouts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r6-bambu-roots-") as directory:
            base = Path(directory)
            development = base / "repo" / "development" / "r6"
            flattened = base / "publication"
            for root in (development, flattened):
                (root / "generated" / "individual_model_only_3mf").mkdir(parents=True)
                (root / "generated" / "manifest.json").write_text("{}", encoding="utf-8")
                (root / "build_bambu_qualification_projects.py").write_text(
                    "# relocated fixture\n", encoding="utf-8"
                )
            self.assertEqual(
                bambu.discover_r6_root(development / "build_bambu_qualification_projects.py"),
                development.resolve(),
            )
            self.assertEqual(
                bambu.discover_r6_root(flattened / "build_bambu_qualification_projects.py"),
                flattened.resolve(),
            )
            self.assertEqual(bambu.repository_anchor(development), (base / "repo").resolve())
            self.assertEqual(bambu.repository_anchor(flattened), flattened.resolve())

    def test_documented_parent_sibling_output_is_allowed_but_existing_is_refused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r6-bambu-output-") as directory:
            base = Path(directory)
            r6 = base / "repo" / "development" / "r6"
            r6.mkdir(parents=True)
            desired = base / "story-corner-r6-bambu-a1mini-sunlu-petg-qualification"
            self.assertEqual(bambu.validate_output_path(r6, desired), desired.resolve())
            desired.mkdir()
            with self.assertRaises(FileExistsError):
                bambu.validate_output_path(r6, desired)
            with self.assertRaises(bambu.BambuQualificationError):
                bambu.validate_output_path(r6, base / "repo" / "inside-repo")

    def _write_synthetic_native_project(
        self,
        destination: Path,
        source_assembly: Path,
        spec: bambu.ProjectSpec,
    ) -> None:
        with zipfile.ZipFile(source_assembly) as source_archive:
            entries = {
                name: source_archive.read(name) for name in source_archive.namelist()
            }
        model = ET.fromstring(entries["3D/3dmodel.model"])
        namespace = {"m": bambu.NS_3MF}
        application = model.find("m:metadata[@name='Application']", namespace)
        self.assertIsNotNone(application)
        application.text = "BambuStudio-TEST"
        entries["3D/3dmodel.model"] = ET.tostring(
            model, encoding="utf-8", xml_declaration=True
        )
        model_settings = ET.Element("config")
        for index, source_name in enumerate(spec.sources, start=2):
            obj = ET.SubElement(model_settings, "object", {"id": str(index)})
            ET.SubElement(
                obj, "metadata", {"key": "name", "value": source_name}
            )
        plate = ET.SubElement(model_settings, "plate")
        ET.SubElement(plate, "metadata", {"key": "gcode_file", "value": ""})
        entries["Metadata/model_settings.config"] = ET.tostring(
            model_settings, encoding="utf-8", xml_declaration=True
        )
        entries["Metadata/project_settings.config"] = json.dumps(
            bambu._settings_expected(spec), sort_keys=True
        ).encode("utf-8")
        entries["Metadata/slice_info.config"] = b"<config><header/></config>"
        with zipfile.ZipFile(destination, "w") as archive:
            for name, payload in entries.items():
                archive.writestr(name, payload)

    def test_native_project_audit_enforces_settings_geometry_envelope_and_no_gcode(self) -> None:
        spec = bambu.PROJECT_SPECS[2]
        audits = [
            bambu.audit_individual_source(self.source_dir, name, self.artifacts)
            for name in spec.sources
        ]
        with tempfile.TemporaryDirectory(prefix="r6-bambu-native-audit-") as directory:
            root = Path(directory)
            source = root / "source.3mf"
            project = root / spec.filename
            bambu.write_qualification_source_3mf(source, spec, audits)
            self._write_synthetic_native_project(project, source, spec)
            bambu.canonicalize_3mf_zip(project)
            report = bambu.validate_bambu_project(project, spec, audits)
            self.assertTrue(report["bambu_native"])
            self.assertTrue(report["unsliced"])
            self.assertEqual(report["embedded_toolpath_file_count"], 0)
            self.assertEqual(report["settings"]["brim_width"], "6")

            with zipfile.ZipFile(project, "a") as archive:
                archive.writestr("Metadata/plate_1.gcode", "G1 X0 Y0\n")
            with self.assertRaises(bambu.BambuQualificationError):
                bambu.validate_bambu_project(project, spec, audits)

    def test_zip_canonicalization_removes_header_nondeterminism_only(self) -> None:
        entries = {
            "b/payload.bin": b"\x00\x01\x02exact payload\xff",
            "a/readme.txt": b"same bytes in both archives\n",
        }

        def write_variant(
            path: Path,
            order: tuple[str, ...],
            timestamp: tuple[int, int, int, int, int, int],
            compression: int,
        ) -> None:
            with zipfile.ZipFile(path, "w") as archive:
                archive.comment = repr(timestamp).encode("ascii")
                for name in order:
                    info = zipfile.ZipInfo(name, date_time=timestamp)
                    info.create_system = 3
                    info.external_attr = 0o100600 << 16
                    info.comment = b"noncanonical header"
                    info.compress_type = compression
                    archive.writestr(info, entries[name])

        with tempfile.TemporaryDirectory(prefix="r6-bambu-canonical-zip-") as directory:
            root = Path(directory)
            first = root / "first.3mf"
            second = root / "second.3mf"
            write_variant(
                first,
                ("b/payload.bin", "a/readme.txt"),
                (2024, 2, 3, 4, 5, 6),
                zipfile.ZIP_STORED,
            )
            write_variant(
                second,
                ("a/readme.txt", "b/payload.bin"),
                (2026, 7, 8, 9, 10, 12),
                zipfile.ZIP_DEFLATED,
            )
            self.assertNotEqual(first.read_bytes(), second.read_bytes())

            first_report = bambu.canonicalize_3mf_zip(first)
            second_report = bambu.canonicalize_3mf_zip(second)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first_report, second_report)
            self.assertTrue(first_report["payloads_preserved_exactly"])
            with zipfile.ZipFile(first) as archive:
                bambu._audit_canonical_zip_container(archive, first.name)
                self.assertEqual(archive.namelist(), sorted(entries))
                self.assertEqual(
                    {name: archive.read(name) for name in archive.namelist()}, entries
                )

    def test_generated_readme_has_required_local_only_warnings(self) -> None:
        records = [
            {"filename": spec.filename, "title": spec.title}
            for spec in bambu.PROJECT_SPECS
        ]
        text = bambu._readme_text(records)
        for phrase in (
            "qualification-only",
            "no generated G-code",
            "Open each `.3mf` **as a project**",
            "use 100% scale",
            "Do not substitute PLA",
            "Slice locally",
            "solid/no-hole wall-screw placeholder is deliberately absent",
            "60–65 °C for 6 hours",
            "avoid acetone",
            "coarse and fine passes",
        ):
            self.assertIn(phrase, text)

    def test_zip_and_privacy_audit_rejects_unsafe_members_paths_and_secrets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r6-bambu-privacy-") as directory:
            root = Path(directory)
            unsafe = root / "unsafe.3mf"
            with zipfile.ZipFile(unsafe, "w") as archive:
                archive.writestr("../escape", b"x")
            with zipfile.ZipFile(unsafe) as archive:
                with self.assertRaises(bambu.BambuQualificationError):
                    bambu._audit_zip_container(archive, unsafe.name)
            with self.assertRaises(bambu.BambuQualificationError):
                bambu._privacy_scan_bytes(
                    "fixture", b"source=/" + b"Users" + b"/private/model.3mf"
                )
            with self.assertRaises(bambu.BambuQualificationError):
                bambu._privacy_scan_bytes("fixture", b"api_key=abcdefghijk")


if __name__ == "__main__":
    unittest.main(verbosity=2)
