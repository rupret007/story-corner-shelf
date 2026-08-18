from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

import trimesh


R11_ROOT = Path(__file__).resolve().parents[1]
if str(R11_ROOT) not in sys.path:
    sys.path.insert(0, str(R11_ROOT))

import model_io  # noqa: E402


class R11ModelIoTests(unittest.TestCase):
    def test_frozen_r10_writer_is_hashed_before_execution(self) -> None:
        self.assertEqual(
            hashlib.sha256(model_io.R10_MODEL_IO.read_bytes()).hexdigest(),
            model_io.EXPECTED_R10_MODEL_IO_SHA256,
        )
        source = (R11_ROOT / "model_io.py").read_text(encoding="utf-8")
        self.assertLess(
            source.index("hashlib.sha256(_R10_MODEL_IO_BYTES).hexdigest()"),
            source.index("exec("),
        )

    def test_neutral_outputs_are_deterministic_and_geometry_identical(self) -> None:
        mesh = trimesh.creation.box(extents=(13.0, 17.0, 19.0))
        frozen = model_io.canonicalize_mesh(mesh)
        objects = (model_io.ModelObject("r11_test_box", frozen),)
        first = model_io.model_only_3mf_bytes("R11 test", "neutral model", objects)
        second = model_io.model_only_3mf_bytes("R11 test", "neutral model", objects)
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model_path = root / "box.3mf"
            stl_path = root / "box.stl"
            model_io.write_bytes_exclusive(model_path, first)
            model_io.write_binary_stl(stl_path, frozen)
            with zipfile.ZipFile(model_path) as archive:
                self.assertEqual(
                    tuple(archive.namelist()),
                    ("[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"),
                )
            inspection = model_io.inspect_model_only_3mf(model_path)
            digest = model_io.canonical_triangle_digest(frozen)
            self.assertTrue(inspection.passed)
            self.assertEqual(tuple(inspection.objects), ("r11_test_box",))
            self.assertEqual(
                model_io.canonical_triangle_digest(inspection.objects["r11_test_box"]),
                digest,
            )
            self.assertEqual(
                model_io.canonical_triangle_digest(model_io.read_binary_stl(stl_path)),
                digest,
            )

    def test_exclusive_writer_refuses_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact.bin"
            model_io.write_bytes_exclusive(target, b"first")
            with self.assertRaises(FileExistsError):
                model_io.write_bytes_exclusive(target, b"replacement")
            self.assertEqual(target.read_bytes(), b"first")


if __name__ == "__main__":
    unittest.main()
