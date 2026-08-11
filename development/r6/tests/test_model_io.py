#!/usr/bin/env python3
"""Determinism and neutral-package checks for the project-owned 3MF writer."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from model_io import (  # noqa: E402
    NS_3MF,
    cuboid,
    write_instanced_model_3mf,
    write_model_3mf,
)


class R6ModelIoTests(unittest.TestCase):
    def test_model_only_3mf_is_deterministic_and_references_every_object_once(self) -> None:
        objects = [
            ("FIRST", cuboid((10.0, 20.0, 3.2)), (0.0, 0.0, 0.0)),
            ("SECOND", cuboid((12.0, 8.0, 4.8)), (20.0, 0.0, 0.0)),
        ]
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-model-io-") as directory:
            root = Path(directory)
            first = root / "first.3mf"
            second = root / "second.3mf"
            for path in (first, second):
                write_model_3mf(
                    path,
                    "Story Corner r6 test",
                    "MODEL-ONLY; EXPERIMENTAL; UNRATED; NO G-CODE",
                    objects,
                )
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                self.assertEqual(
                    names,
                    ["[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"],
                )
                self.assertFalse(any("gcode" in name.lower() for name in names))
                model = ET.fromstring(archive.read("3D/3dmodel.model"))
            namespace = {"m": NS_3MF}
            resources = model.findall("m:resources/m:object", namespace)
            build_items = model.findall("m:build/m:item", namespace)
            object_ids = [node.attrib["id"] for node in resources]
            referenced_ids = [node.attrib["objectid"] for node in build_items]
            self.assertEqual(len(object_ids), len(set(object_ids)))
            self.assertEqual(sorted(object_ids), sorted(referenced_ids))
            self.assertEqual(len(build_items), len(objects))
            self.assertEqual(
                [node.attrib["name"] for node in resources],
                ["FIRST", "SECOND"],
            )

    def test_writer_rejects_duplicate_or_empty_object_names(self) -> None:
        mesh = cuboid((1.0, 1.0, 1.0))
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-model-io-") as directory:
            output = Path(directory) / "bad.3mf"
            with self.assertRaises(ValueError):
                write_model_3mf(
                    output,
                    "bad",
                    "bad",
                    [("SAME", mesh, (0.0, 0.0, 0.0)), ("SAME", mesh, (2.0, 0.0, 0.0))],
                )
            with self.assertRaises(ValueError):
                write_model_3mf(output, "bad", "bad", [("", mesh, (0.0, 0.0, 0.0))])

    def test_instanced_writer_shares_meshes_but_builds_each_physical_object_once(self) -> None:
        families = [
            ("PIN", cuboid((4.8, 4.8, 20.4))),
            ("KEY", cuboid((48.35, 14.0, 20.0))),
        ]
        instances = [
            ("LEVEL_01_PIN_001", "PIN", (0.0, 0.0, 0.0)),
            ("LEVEL_01_PIN_002", "PIN", (10.0, 0.0, 0.0)),
            ("LEVEL_01_KEY_001", "KEY", (20.0, 0.0, 0.0)),
        ]
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-instanced-") as directory:
            root = Path(directory)
            first = root / "first.3mf"
            second = root / "second.3mf"
            for path in (first, second):
                write_instanced_model_3mf(
                    path,
                    "Story Corner r6 exact set",
                    "MODEL-ONLY; EXPERIMENTAL; UNRATED; NO G-CODE",
                    families,
                    instances,
                )
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                model = ET.fromstring(archive.read("3D/3dmodel.model"))
                self.assertFalse(any("gcode" in name.lower() for name in archive.namelist()))
            namespace = {"m": NS_3MF}
            objects = model.findall("m:resources/m:object", namespace)
            mesh_objects = [node for node in objects if node.find("m:mesh", namespace) is not None]
            component_objects = [
                node for node in objects if node.find("m:components", namespace) is not None
            ]
            build_items = model.findall("m:build/m:item", namespace)
            self.assertEqual(len(mesh_objects), 2)
            self.assertEqual(len(component_objects), len(instances))
            self.assertEqual(len(build_items), len(instances))
            component_ids = [node.attrib["id"] for node in component_objects]
            build_ids = [node.attrib["objectid"] for node in build_items]
            self.assertEqual(sorted(component_ids), sorted(build_ids))
            self.assertEqual(
                [node.attrib["name"] for node in component_objects],
                [name for name, _family, _translation in instances],
            )
            mesh_ids = {node.attrib["id"] for node in mesh_objects}
            referenced_sources = {
                node.attrib["objectid"]
                for parent in component_objects
                for node in parent.findall("m:components/m:component", namespace)
            }
            self.assertEqual(mesh_ids, referenced_sources)


if __name__ == "__main__":
    unittest.main(verbosity=2)
