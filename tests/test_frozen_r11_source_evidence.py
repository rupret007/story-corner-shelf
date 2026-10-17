from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V2_ROOT = ROOT / "development" / "r11_print_v2"
if str(V2_ROOT) not in sys.path:
    sys.path.insert(0, str(V2_ROOT))

import control_contract as control  # noqa: E402


class FrozenR11SourceEvidenceTests(unittest.TestCase):
    def test_canonical_repository_pins_verify_frozen_v1_source_closure(self) -> None:
        live_sha = control.sha256_file(ROOT / control.REPOSITORY_REQUIREMENTS_RELATIVE)
        self.assertEqual(live_sha, control.CANONICAL_REPOSITORY_REQUIREMENTS_SHA256)
        evidence = control.verify_frozen_v1()
        self.assertTrue(evidence["verified"])
        self.assertEqual(
            evidence["source_tree"]["source_tree_sha256"],
            control.FROZEN_V1_SOURCE_TREE_SHA256,
        )

    def test_non_canonical_requirements_are_rejected(self) -> None:
        manifest = control.strict_json(control.V1_ROOT / "manifest.json")
        records = manifest["source_records"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for record in records:
                source = control.PROJECT_ROOT / record["path"]
                destination = root / record["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            self.assertEqual(
                control.verify_live_source_records(
                    records, manifest["source_tree_evidence"], project_root=root
                ),
                manifest["source_tree_evidence"],
            )
            requirements = root / control.REPOSITORY_REQUIREMENTS_RELATIVE
            requirements.write_bytes(requirements.read_bytes() + b"# non-canonical\n")
            with self.assertRaisesRegex(
                control.ContractError,
                r"repository requirements\.txt changed without matching the frozen publication "
                "or the canonical Dependabot-pinned repository lock",
            ):
                control.verify_live_source_records(
                    records, manifest["source_tree_evidence"], project_root=root
                )

    def test_non_requirements_source_tampering_is_rejected(self) -> None:
        manifest = control.strict_json(control.V1_ROOT / "manifest.json")
        records = manifest["source_records"]
        victim_path = next(
            record["path"]
            for record in records
            if record["path"] != control.REPOSITORY_REQUIREMENTS_RELATIVE
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for record in records:
                source = control.PROJECT_ROOT / record["path"]
                destination = root / record["path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
            tampered = root / victim_path
            tampered.write_bytes(tampered.read_bytes() + b"tamper")
            with self.assertRaisesRegex(control.ContractError, "live source bytes changed"):
                control.verify_live_source_records(
                    records,
                    manifest["source_tree_evidence"],
                    project_root=root,
                )


if __name__ == "__main__":
    unittest.main()
