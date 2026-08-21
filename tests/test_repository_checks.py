from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_repository as checker  # noqa: E402


class RepositoryCheckTests(unittest.TestCase):
    def test_committed_all_petg_shelf_directory_is_present(self) -> None:
        all_petg_shelf = checker.GENERATED / "all_petg_shelf"
        self.assertTrue(
            all_petg_shelf.is_dir(),
            "generated/all_petg_shelf is a committed deliverable directory",
        )

    def test_generated_tree_accepts_known_directories(self) -> None:
        errors: list[str] = []
        checker.check_generated_tree(errors)
        self.assertEqual(
            errors,
            [],
            f"check_generated_tree flagged the committed generated tree: {errors}",
        )

    def test_full_repository_check_passes_on_committed_tree(self) -> None:
        try:
            checker.main()
        except SystemExit as exc:  # pragma: no cover - failure detail is the message
            self.fail(f"check_repository.main() reported failures: {exc}")


if __name__ == "__main__":
    unittest.main()
