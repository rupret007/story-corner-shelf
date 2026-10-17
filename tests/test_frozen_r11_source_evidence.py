from __future__ import annotations

import copy
import hashlib
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

# Byte-pinned publication of requirements.txt bound by the frozen R11 v1 manifest.
_FROZEN_PUBLISHED_REQUIREMENTS_TXT = b"""numpy==2.5.1
shapely==2.1.2
trimesh==5.0.0
manifold3d==3.5.2
mapbox-earcut==1.0.3
scipy==1.18.0
networkx==3.5
"""


def _populate_v1_source_tree(root: Path, *, requirements_bytes: bytes | None = None) -> None:
    manifest = control.strict_json(control.V1_ROOT / "manifest.json")
    for record in manifest["source_records"]:
        source = control.PROJECT_ROOT / record["path"]
        destination = root / record["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        if (
            requirements_bytes is not None
            and record["path"] == control.REPOSITORY_REQUIREMENTS_RELATIVE
        ):
            destination.write_bytes(requirements_bytes)
        else:
            shutil.copyfile(source, destination)


class FrozenR11SourceEvidenceTests(unittest.TestCase):
    def test_frozen_publication_requirements_bytes_are_pinned(self) -> None:
        digest = hashlib.sha256(_FROZEN_PUBLISHED_REQUIREMENTS_TXT).hexdigest()
        self.assertEqual(digest, control.FROZEN_PUBLISHED_REQUIREMENTS_SHA256)

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

    def test_requirements_upgrade_keeps_non_requirements_drift_guard(self) -> None:
        text = (V2_ROOT / "control_contract.py").read_text(encoding="utf-8")
        self.assertIn(
            "if live_non_requirements != frozen_non_requirements:",
            text,
        )
        self.assertIn(
            'raise ContractError("v1 live source bytes changed outside requirements.txt")',
            text,
        )

    def test_tampered_frozen_source_tree_sha256_is_rejected(self) -> None:
        manifest = control.strict_json(control.V1_ROOT / "manifest.json")
        records = manifest["source_records"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _populate_v1_source_tree(root)
            tampered_evidence = copy.deepcopy(manifest["source_tree_evidence"])
            tampered_evidence["source_tree_sha256"] = "0" * 64
            with self.assertRaisesRegex(
                control.ContractError,
                "v1 frozen source-tree evidence is no longer recognized",
            ):
                control.verify_live_source_records(
                    records,
                    tampered_evidence,
                    project_root=root,
                )

    def test_tampered_live_source_tree_evidence_is_rejected(self) -> None:
        manifest = control.strict_json(control.V1_ROOT / "manifest.json")
        records = manifest["source_records"]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            _populate_v1_source_tree(
                root, requirements_bytes=_FROZEN_PUBLISHED_REQUIREMENTS_TXT
            )
            live_evidence = control.verify_live_source_records(
                records,
                manifest["source_tree_evidence"],
                project_root=root,
            )
            self.assertEqual(live_evidence, manifest["source_tree_evidence"])
            tampered_evidence = copy.deepcopy(manifest["source_tree_evidence"])
            tampered_evidence["source_bytes"] += 1
            with self.assertRaisesRegex(
                control.ContractError,
                "v1 live source-tree evidence changed",
            ):
                control.verify_live_source_records(
                    records,
                    tampered_evidence,
                    project_root=root,
                )


if __name__ == "__main__":
    unittest.main()
