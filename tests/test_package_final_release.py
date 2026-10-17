from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageFinalReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)
        self.root = self.workspace / "repo"
        (self.root / "scripts").mkdir(parents=True)
        self.script = self.root / "scripts" / "package_final_release.py"
        shutil.copy2(ROOT / "scripts" / self.script.name, self.script)
        shutil.copy2(ROOT / "config.json", self.root / "config.json")
        self.generated = self.root / "generated"
        self.source = self.generated / "model_only_3mf"
        self.destination = self.generated / "final_release_r12"

    def seed_package(self) -> Path:
        self.destination.mkdir(parents=True)
        sentinel = self.destination / "existing-package.txt"
        sentinel.write_bytes(b"keep this package\n")
        return sentinel

    def run_packager(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.script)], capture_output=True, text=True
        )

    def assert_preserved(self, message: str, sentinel: Path) -> None:
        result = self.run_packager()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertEqual(sentinel.read_bytes(), b"keep this package\n")
        self.assertEqual(list(self.destination.iterdir()), [sentinel])

    def test_missing_model_directory_preserves_existing_package(self) -> None:
        sentinel = self.seed_package()
        self.assert_preserved("No generated model-only 3MF", sentinel)

    def test_empty_model_directory_preserves_existing_package(self) -> None:
        sentinel = self.seed_package()
        self.source.mkdir()
        self.assert_preserved("No generated model-only 3MF", sentinel)

    def test_non_file_model_entries_preserve_existing_package(self) -> None:
        sentinel = self.seed_package()
        self.source.mkdir()
        (self.source / "valid.3mf").write_bytes(b"model")
        for kind in ("directory", "dangling_symlink"):
            with self.subTest(kind=kind):
                invalid = self.source / "invalid.3mf"
                if kind == "directory":
                    invalid.mkdir()
                else:
                    invalid.symlink_to(self.workspace / "missing.3mf")
                self.assert_preserved("must be an existing file", sentinel)
                if kind == "directory":
                    invalid.rmdir()
                else:
                    invalid.unlink()

    def test_symlinked_generated_directory_preserves_external_package(self) -> None:
        external = self.workspace / "external"
        external.mkdir()
        self.generated.symlink_to(external, target_is_directory=True)
        sentinel = self.seed_package()
        self.source.mkdir()
        (self.source / "valid.3mf").write_bytes(b"model")
        self.assert_preserved("symlinked generated directory", sentinel)
        self.assertTrue(self.generated.is_symlink())
        self.assertEqual((self.source / "valid.3mf").read_bytes(), b"model")

    def test_dangling_generated_symlink_is_refused(self) -> None:
        missing = self.workspace / "missing"
        self.generated.symlink_to(missing, target_is_directory=True)
        result = self.run_packager()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlinked generated directory", result.stderr)
        self.assertFalse(missing.exists())
        self.assertTrue(self.generated.is_symlink())

    def test_valid_inputs_replace_package_and_copy_models_and_profiles(self) -> None:
        sentinel = self.seed_package()
        self.source.mkdir()
        (self.source / "valid.3mf").write_bytes(b"model payload")
        profiles = self.root / "profiles"
        profiles.mkdir()
        (profiles / "preset.json").write_bytes(b'{"name": "preset"}\n')
        result = self.run_packager()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(sentinel.exists())
        self.assertEqual(
            (self.destination / "models" / "valid.3mf").read_bytes(), b"model payload"
        )
        self.assertEqual(
            (self.destination / "profiles" / "preset.json").read_bytes(),
            (profiles / "preset.json").read_bytes(),
        )
        for name in ("README_FIRST.md", "START_PRINTING_NOW.md", "SETTINGS_LOCK.md", "PRINT_ORDER.md"):
            self.assertTrue((self.destination / name).is_file(), name)
