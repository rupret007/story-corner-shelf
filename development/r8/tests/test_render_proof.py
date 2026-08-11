#!/usr/bin/env python3
"""Contract tests for the staged deterministic R8 / 16B proof renderer."""

from __future__ import annotations

import copy
import os
from pathlib import Path
import re
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET


R8_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = R8_DIR.parent.parent
if str(R8_DIR) not in sys.path:
    sys.path.insert(0, str(R8_DIR))
import render_proof as proof


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class RenderProofContract(unittest.TestCase):
    """Render into temporary storage so checked assets stay frozen until release."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="r8-proof-test-")
        cls.root_dir = Path(cls.temporary.name)
        cls.output_dir = cls.root_dir / "outputs"
        drawing_python = Path("/usr/bin/python3")
        if not drawing_python.is_file():
            drawing_python = Path(sys.executable)
        environment = os.environ.copy()
        environment["MPLCONFIGDIR"] = str(cls.root_dir / "matplotlib-cache")
        cls.completed = subprocess.run(
            [
                str(drawing_python),
                str(R8_DIR / "render_proof.py"),
                "--output-dir",
                str(cls.output_dir),
            ],
            cwd=REPO_DIR,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        cls.paths = proof.proof_paths(cls.output_dir)
        cls.manifest = proof.strict_json_file(cls.paths.manifest)
        cls.svg_text = cls.paths.svg.read_text(encoding="utf-8")
        cls.root = ET.fromstring(cls.svg_text)
        matches = [
            element
            for element in cls.root.iter()
            if local_name(element.tag) == "metadata"
            and element.attrib.get("id") == "r8-proof-metadata"
        ]
        if len(matches) != 1:
            raise AssertionError(
                f"Expected one exact-proof metadata block, got {len(matches)}"
            )
        cls.svg_metadata = proof.strict_json_loads(
            matches[0].text or "", source_name="test SVG metadata"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_canvas_and_png_are_exactly_1800_by_1200(self) -> None:
        self.assertEqual(self.root.attrib["width"], "1800")
        self.assertEqual(self.root.attrib["height"], "1200")
        self.assertEqual(self.root.attrib["viewBox"], "0 0 1800 1200")
        with self.paths.png.open("rb") as stream:
            self.assertEqual(stream.read(8), b"\x89PNG\r\n\x1a\n")
            length = struct.unpack(">I", stream.read(4))[0]
            self.assertEqual(stream.read(4), b"IHDR")
            ihdr = stream.read(length)
        self.assertEqual(struct.unpack(">II", ihdr[:8]), (1800, 1200))
        self.assertEqual(
            self.manifest["outputs"]["png"]["dimensions_px"], [1800, 1200]
        )

    def test_manifest_and_svg_track_every_live_source_hash(self) -> None:
        expected = proof.source_hashes()
        self.assertEqual(self.manifest["source_hashes"], expected)
        self.assertEqual(self.svg_metadata["source_hashes"], expected)
        self.assertEqual(
            self.root.attrib["data-config-sha256"],
            expected["development/r8/config.json"],
        )
        source_names = set(expected)
        self.assertTrue(
            {
                "requirements.txt",
                "development/r8/config.json",
                "development/r8/design_math.py",
                "development/r8/shelf_geometry.py",
                "development/r8/accessory_geometry.py",
                "development/r8/interface_geometry.py",
                "development/r8/assembly_geometry.py",
                "development/r8/production_plan.py",
                "development/r8/render_proof.py",
            }.issubset(source_names)
        )
        self.assertEqual(len(proof.SOURCE_PATHS), len(set(proof.SOURCE_PATHS)))

    def test_output_hashes_sizes_and_embedded_payload_are_exact(self) -> None:
        for kind, path in (("svg", self.paths.svg), ("png", self.paths.png)):
            self.assertEqual(
                self.manifest["outputs"][kind]["sha256"], proof.sha256_file(path)
            )
            self.assertEqual(
                self.manifest["outputs"][kind]["bytes"], path.stat().st_size
            )
        self.assertGreater(self.paths.png.stat().st_size, 50_000)
        self.assertGreater(self.paths.svg.stat().st_size, 50_000)
        for key, value in self.svg_metadata.items():
            self.assertEqual(self.manifest[key], value)
        self.assertEqual(self.manifest["schema_version"], 2)

    def test_exact_geometry_topology_and_service_metadata(self) -> None:
        exact = self.manifest["exact"]
        self.assertEqual(exact["levels"], 2)
        self.assertEqual(exact["through_supports_per_level"], 9)
        self.assertEqual(exact["return_supports_per_level"], 5)
        self.assertEqual(exact["terminal_support_center_inset_mm"], 16.0)
        self.assertEqual(exact["cassette_internal_web_count"], 3)
        self.assertEqual(exact["shelf_depth_mm"], 152.4)
        self.assertEqual(exact["d_frame_downleg_mm"], 160.0)
        self.assertEqual(exact["d_frame_cap_mm"], 32.0)
        self.assertAlmostEqual(
            exact["d_frame_measured_minimum_web_mm"],
            16.66628590450866,
            places=10,
        )
        self.assertEqual(exact["rail_envelope_mm"], [36.0, 88.0, 8.8])
        self.assertEqual(exact["rail_socket_count"], 3)
        self.assertEqual(exact["through_default_rail_indices"], [1, 3, 5, 7])
        self.assertEqual(exact["return_default_rail_indices"], [1, 3])
        self.assertEqual(exact["module_count"], 4)
        self.assertEqual(exact["module_service_lift_mm"], 8.0)
        self.assertEqual(exact["rail_service_lift_mm"], 4.0)
        self.assertTrue(exact["rail_service_requires_module_removal"])
        self.assertEqual(
            exact["layout_representation"],
            "frozen_nominal_two_run_topology_schematic_not_to_scale",
        )
        self.assertFalse(exact["return_and_corner_field_verified"])
        self.assertFalse(exact["exact_full_l_placement"])
        self.assertEqual(self.svg_metadata["exact"], exact)

    def test_svg_has_fourteen_distinct_supports_per_level(self) -> None:
        ids = [element.attrib.get("id", "") for element in self.root.iter()]

        def count(prefix: str) -> int:
            return sum(value.startswith(prefix) for value in ids)

        expected = self.manifest["counts"]
        self.assertEqual(count("panel-"), expected["panels"])
        self.assertEqual(
            count("through-support-L"), expected["through_support_markers"]
        )
        self.assertEqual(
            count("return-support-L"), expected["return_support_markers"]
        )
        self.assertEqual(count("terminal-marker-"), 8)
        self.assertEqual(expected["clean_terminal_markers"], 8)
        self.assertEqual(expected["distinct_support_markers"], 28)
        self.assertEqual(count("default-rail-L"), expected["default_rail_markers"])
        self.assertEqual(count("rail-socket-"), expected["exploded_rail_sockets"])
        self.assertEqual(count("module-"), expected["accessory_modules"])
        self.assertEqual(count("positive-latch-"), 4)
        self.assertEqual(count("external-boss-"), 4)
        self.assertEqual(count("exact-d-frame-outer-profile"), 1)
        self.assertEqual(count("exact-d-frame-inner-profile"), 1)
        self.assertEqual(count("selected-u-box-section-"), 3)
        self.assertEqual(count("heavy-coffer-control"), 1)

        elements_by_id = {
            element.attrib["id"]: element
            for element in self.root.iter()
            if element.attrib.get("id")
        }
        for level in (1, 2):
            support_ids = [
                *[f"through-support-L{level}-{index}" for index in range(9)],
                *[f"return-support-L{level}-{index}" for index in range(5)],
            ]
            paths = []
            for support_id in support_ids:
                group = elements_by_id[support_id]
                path_nodes = [
                    node
                    for node in group.iter()
                    if local_name(node.tag) == "path" and node.attrib.get("d")
                ]
                self.assertTrue(path_nodes, support_id)
                paths.append(path_nodes[0].attrib["d"])
            self.assertEqual(len(paths), 14)
            self.assertEqual(len(set(paths)), 14)

    def test_required_warnings_and_scope_labels_are_legible(self) -> None:
        visible_text = " ".join(" ".join(self.root.itertext()).split()).casefold()
        for statement in self.manifest["required_statements"]:
            self.assertIn(statement.casefold(), visible_text)
        for phrase in (
            "measured cad min web",
            "36 × 88 × 8.8 mm",
            "positive release latch",
            "selected u-box",
            "matched heavy coffer control",
            "default rails 1 / 3 / 5 / 7",
            "default rails 1 / 3",
            "frozen nominal two-run topology",
            "schematic · not to scale",
            "corner transition unauthored",
            "3 full-depth internal webs",
        ):
            self.assertIn(phrase.casefold(), visible_text)
        self.assertNotIn("matte", visible_text)
        font_sizes = [
            float(explicit or shorthand)
            for explicit, shorthand in re.findall(
                r"font-size:\s*([0-9.]+)px|font:\s*(?:[0-9]+\s+)?([0-9.]+)px",
                self.svg_text,
            )
        ]
        self.assertTrue(font_sizes)
        self.assertGreaterEqual(min(font_sizes), 12.0)
        layout = self.manifest["layout_validation"]
        self.assertGreaterEqual(layout["minimum_font_size_px"], 12.0)
        self.assertTrue(layout["all_text_contained"])
        self.assertTrue(layout["all_heading_text_clear"])
        self.assertEqual(layout["heading_text_overlap_pairs"], [])

    def test_renderer_provenance_is_complete_and_verifiable(self) -> None:
        provenance = self.manifest["renderer_provenance"]
        self.assertEqual(self.svg_metadata["renderer_provenance"], provenance)
        cad = provenance["cad"]
        self.assertTrue(cad["resolved_interpreter"])
        self.assertRegex(cad["python_version"], r"^\d+\.\d+\.\d+")
        self.assertEqual(set(cad["packages"]), set(proof.CAD_PACKAGE_NAMES))
        self.assertTrue(all(cad["packages"].values()))
        drawing = provenance["drawing"]
        self.assertTrue(drawing["resolved_interpreter"])
        self.assertEqual(drawing["matplotlib_backend"].casefold(), "agg")
        self.assertIn("matplotlib", drawing["packages"])
        font = drawing["font"]
        self.assertEqual(font["requested_family"], "Arial")
        self.assertEqual(font["resolved_family"], "Arial")
        font_path = Path(font["resolved_path"])
        self.assertTrue(font_path.is_file())
        self.assertEqual(font["sha256"], proof.sha256_file(font_path))
        self.assertEqual(font["bytes"], font_path.stat().st_size)

    def test_authored_panel_and_footer_bounds_stay_inside_canvas(self) -> None:
        width, height = self.manifest["canvas_px"]
        bounds = list(
            self.manifest["layout_validation"]["panel_bounds_px"].values()
        )
        bounds.append(self.manifest["layout_validation"]["footer_bounds_px"])
        for x, y, item_width, item_height in bounds:
            with self.subTest(bounds=(x, y, item_width, item_height)):
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertGreater(item_width, 0)
                self.assertGreater(item_height, 0)
                self.assertLessEqual(x + item_width, width)
                self.assertLessEqual(y + item_height, height)

    def test_visual_remains_fail_closed_and_uses_public_scope_gate(self) -> None:
        self.assertTrue(self.manifest["qualification_only"])
        self.assertEqual(self.manifest["rated_load_kg"], 0.0)
        self.assertEqual(self.manifest["rated_load_lb"], 0.0)
        self.assertFalse(self.manifest["render"]["generative_ai_used"])
        publication = self.manifest["render"]["publication"]
        self.assertTrue(publication["staged_and_validated_before_replacement"])
        self.assertEqual(publication["individual_replacement_primitive"], "os.replace")
        self.assertEqual(publication["commit_marker"], "manifest replaced last")

        cfg = proof.load_config()
        proof.validate_project_scope(cfg)
        unsafe = copy.deepcopy(cfg)
        unsafe["project"]["qualification_only"] = False
        with self.assertRaises(Exception):
            proof.validate_project_scope(unsafe)


class RenderProofHardeningUnitTests(unittest.TestCase):
    def test_strict_json_rejects_duplicates_constants_and_overflow(self) -> None:
        for source in (
            '{"duplicate":1,"duplicate":2}',
            '{"value":NaN}',
            '{"value":Infinity}',
            '{"value":-Infinity}',
            '{"value":1e999}',
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                proof.strict_json_loads(source)

    def test_publication_rolls_back_when_post_publish_source_hash_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r8-proof-rollback-") as root_name:
            root = Path(root_name)
            staged = proof.proof_paths(root / "staged")
            target = proof.proof_paths(root / "target")
            staged.directory.mkdir()
            target.directory.mkdir()
            for path in (staged.svg, staged.png, staged.manifest):
                path.write_text(f"new-{path.name}", encoding="utf-8")
            for path in (target.svg, target.png, target.manifest):
                path.write_text(f"old-{path.name}", encoding="utf-8")
            with mock.patch.object(
                proof, "source_hashes", return_value={"source": "changed"}
            ):
                with self.assertRaises(RuntimeError):
                    proof.publish_output_set(
                        staged,
                        target,
                        expected_source_hashes={"source": "original"},
                    )
            for path in (target.svg, target.png, target.manifest):
                self.assertEqual(
                    path.read_text(encoding="utf-8"), f"old-{path.name}"
                )

    def test_output_validator_rejects_a_corrupt_atomic_set(self) -> None:
        with tempfile.TemporaryDirectory(prefix="r8-proof-invalid-") as root_name:
            paths = proof.proof_paths(Path(root_name))
            paths.svg.write_text("<svg/>", encoding="utf-8")
            paths.png.write_bytes(b"not png")
            paths.manifest.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                proof.validate_output_set(paths)


if __name__ == "__main__":
    unittest.main()
