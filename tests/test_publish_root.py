#!/usr/bin/env python3
"""Focused source-only tests for the exclusive r6 root-publication tool."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


R6 = Path(__file__).resolve().parents[1]


def _single_existing_layout(label: str, candidates: tuple[Path, ...]) -> Path:
    matches = tuple(candidate for candidate in candidates if candidate.is_dir())
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {label} layout, found {matches}")
    return matches[0]


# These tests are copied into the assembled repository and are run there before
# publication commits.  Resolve the preserved fallback and GitHub templates in
# either their development-source or intentional assembled-root locations.
HYBRID_R5 = _single_existing_layout(
    "hybrid r5",
    (R6 / "reference" / "hybrid_r5", R6.parents[1] / "reference" / "hybrid_r5"),
)
REPOSITORY = HYBRID_R5.parents[1]
GITHUB_TEMPLATE_ROOT = _single_existing_layout(
    "GitHub template",
    (R6 / "publication" / ".github", R6 / ".github"),
)
sys.path.insert(0, str(R6))

import publish_root  # noqa: E402


class PublicationBlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = publish_root.publication_copy_rules(R6, REPOSITORY)
        cls.by_destination = {rule.destination: rule for rule in cls.rules}

    def test_root_docs_are_canonical_mirrors_and_reference_docs_publish(self) -> None:
        for docs_name, root_name in publish_root.ROOT_DOCUMENT_MAP:
            self.assertEqual(
                self.by_destination[root_name].source_relative,
                f"docs/{docs_name}",
            )
            self.assertEqual(
                self.by_destination[f"docs/{docs_name}"].source_relative,
                f"docs/{docs_name}",
            )
        for name in publish_root.REFERENCE_DOCUMENTS:
            self.assertIn(name, self.by_destination)

    def test_exact_hero_and_preserved_rendering_history_are_published(self) -> None:
        exact = f"assets/{publish_root.EXACT_HERO}"
        preserved = f"assets/{publish_root.PRESERVED_RENDERING}"
        self.assertIn(exact, self.by_destination)
        self.assertIn(preserved, self.by_destination)
        self.assertIn(f"assets/{publish_root.HERO_PROMPT}", self.by_destination)
        self.assertNotEqual(exact, preserved)
        self.assertNotEqual(
            hashlib.sha256((R6 / exact).read_bytes()).hexdigest(),
            hashlib.sha256((R6 / preserved).read_bytes()).hexdigest(),
        )
        self.assertEqual(
            hashlib.sha256((R6 / preserved).read_bytes()).hexdigest(),
            publish_root.PRESERVED_RENDERING_SHA256,
        )
        digest = publish_root._validate_exact_hero(R6)
        self.assertEqual(
            digest,
            hashlib.sha256((R6 / exact).read_bytes()).hexdigest(),
        )

    def test_sources_tests_artifacts_github_and_hybrid_are_mapped(self) -> None:
        destinations = set(self.by_destination)
        self.assertTrue(publish_root.REQUIRED_ROOT_MODULES <= destinations)
        self.assertIn("config.json", destinations)
        self.assertTrue(any(name.startswith("tests/test_") for name in destinations))
        self.assertIn(("generated", "generated"), publish_root.STAGED_TREE_MAP)
        self.assertIn(("tests", "tests"), publish_root.STAGED_TREE_MAP)
        self.assertTrue(
            set(publish_root.PUBLICATION_TEMPLATE_FILES) <= destinations
        )
        self.assertTrue(
            {
                "reference/hybrid_r5/README.md",
                "reference/hybrid_r5/SOURCE_MANIFEST.json",
                "reference/hybrid_r5/config.hybrid.json",
                "reference/hybrid_r5/scripts/generate_hybrid_r5.py",
            }
            <= destinations
        )
        self.assertFalse(any("__pycache__" in name for name in destinations))
        self.assertFalse(any(".visual_check" in name for name in destinations))
        self.assertIn("PROGRESS.md", destinations)
        self.assertEqual(len(destinations), len(self.rules))

    def test_template_sources_match_the_active_layout(self) -> None:
        expected_prefix = (
            "publication/" if GITHUB_TEMPLATE_ROOT.parent.name == "publication" else ""
        )
        for name in publish_root.PUBLICATION_TEMPLATE_FILES:
            self.assertEqual(
                self.by_destination[name].source_relative,
                f"{expected_prefix}{name}",
            )

    def test_hybrid_r5_manifest_remains_byte_verified(self) -> None:
        manifest = publish_root._validate_hybrid_reference(REPOSITORY)
        self.assertEqual(manifest["status"], "verified fallback source snapshot")
        self.assertEqual(
            manifest["revision"], "triadic_palatine_fitted_l_corner_r5"
        )


class DerivedEvidenceTests(unittest.TestCase):
    def _synthetic_release(self, root: Path) -> dict[str, object]:
        revision = "synthetic_revision_from_config"
        edition = "Synthetic Experimental Edition"
        config = {
            "project": {
                "name": "Synthetic Corner",
                "revision": revision,
                "edition": edition,
                "production_release_allowed": False,
                "embedded_gcode_allowed": False,
            },
            "test_protocol": {"tested_load_rating_exists": False},
        }
        package_id = "derived_package_id"
        filename = "MODEL_ONLY_DERIVED_PACKAGE.3mf"
        plan = {
            "package_id": package_id,
            "filename": filename,
            "physical_object_count": 73,
        }
        validation = {
            "production_ready": False,
            "tested_load_rating_exists": False,
            "embedded_gcode_allowed": False,
            "software_model_package_eligible": True,
            "physical_installation_qualified": False,
            "production_release_eligible": False,
            "physical_qualification_blockers": ["synthetic physical coupon"],
            "reports": [
                {"package_id": package_id, "all_checks_pass": True}
            ],
        }
        manifest = {
            "production_ready": False,
            "tested_load_rating_exists": False,
            "software_model_package_eligible": True,
            "physical_installation_qualified": False,
            "production_release_eligible": False,
            "physical_qualification_blockers": ["synthetic physical coupon"],
            "release": {"plans": [plan]},
        }
        (root / "generated" / "model_only_3mf").mkdir(parents=True)
        (root / "generated" / "drawings").mkdir()
        (root / "generated" / "model_only_3mf" / filename).write_bytes(b"model")
        (root / "generated" / "drawings" / "derived.svg").write_text(
            "<svg/>", encoding="utf-8"
        )
        (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
        (root / "generated" / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        (root / "generated" / "validation.json").write_text(
            json.dumps(validation), encoding="utf-8"
        )
        return {
            "passed": True,
            "mode": "full-release",
            "derived": {
                "project_name": "Synthetic Corner",
                "revision": revision,
                "edition": edition,
                "one_level_physical_object_count": 431,
                "selected_levels_physical_object_count": 862,
                "package_filenames": {package_id: filename},
                "package_counts": {package_id: 73},
            },
        }

    def test_revision_counts_and_package_records_are_derived(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = self._synthetic_release(root)
            evidence = publish_root._derive_release_evidence(root, report)
        self.assertEqual(
            evidence["project"]["revision"], "synthetic_revision_from_config"
        )
        self.assertEqual(
            evidence["derived_inventory"]["one_level_physical_object_count"],
            431,
        )
        self.assertEqual(
            evidence["canonical_packages"],
            [
                {
                    "package_id": "derived_package_id",
                    "filename": "MODEL_ONLY_DERIVED_PACKAGE.3mf",
                    "physical_object_count": 73,
                    "validation_passed": True,
                }
            ],
        )

    def test_missing_explicit_physical_gate_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = self._synthetic_release(root)
            validation_path = root / "generated" / "validation.json"
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            del validation["physical_installation_qualified"]
            validation_path.write_text(json.dumps(validation), encoding="utf-8")
            with self.assertRaisesRegex(
                publish_root.PublicationError, "physical_installation_qualified false"
            ):
                publish_root._derive_release_evidence(root, report)


class ExactManifestTests(unittest.TestCase):
    def _manifest_for(self, root: Path, relative: str) -> dict[str, object]:
        path = root / relative
        record = {
            "destination": relative,
            "source_scope": "test",
            "source": relative,
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mode": f"{publish_root._file_mode(path):04o}",
        }
        return {
            "file_count_excluding_manifest": 1,
            "total_bytes_excluding_manifest": path.stat().st_size,
            "files": [record],
        }

    def test_exact_allowlist_rejects_extra_file_and_digest_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = root / "proof.txt"
            payload.write_text("checked", encoding="utf-8")
            manifest = self._manifest_for(root, "proof.txt")
            (root / publish_root.PUBLICATION_MANIFEST).write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            publish_root._audit_manifest_file_set(root, manifest)
            extra = root / "unlisted.txt"
            extra.write_text("extra", encoding="utf-8")
            with self.assertRaisesRegex(
                publish_root.PublicationError, "missing/unlisted files"
            ):
                publish_root._audit_manifest_file_set(root, manifest)
            extra.unlink()
            payload.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(
                publish_root.PublicationError, "byte/hash drift"
            ):
                publish_root._audit_manifest_file_set(root, manifest)

    def test_personal_absolute_path_and_forbidden_cache_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / "private.txt"
            private.write_text(
                "source: /" + "Users/alice/private/model.stl",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                publish_root.PublicationError, "personal absolute path"
            ):
                publish_root._reject_host_paths(private)
        with self.assertRaisesRegex(publish_root.PublicationError, "forbidden"):
            publish_root._reject_forbidden_destination("tests/__pycache__/x.pyc")

    def test_credentials_are_rejected_in_plain_files_and_3mf_members(self) -> None:
        token = "gh" + "p_" + "A" * 32
        key_marker = "-----BEGIN " + "PRIVATE KEY-----"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plain = root / "plain.txt"
            plain.write_text(f"credential={token}\n", encoding="utf-8")
            with self.assertRaisesRegex(
                publish_root.PublicationError, "GitHub token signature"
            ):
                publish_root._reject_credentials(plain)

            package = root / "model.3mf"
            with zipfile.ZipFile(
                package, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                archive.writestr("Metadata/private.txt", key_marker)
            with self.assertRaisesRegex(
                publish_root.PublicationError, "private key signature.*archive member"
            ):
                publish_root._reject_credentials(package)

    def test_nested_repository_and_credential_files_are_forbidden(self) -> None:
        for relative in (
            "generated/.git/config",
            "generated/.env.production",
            "generated/credentials.json",
            "generated/credentials.prod.yml",
            "generated/id_ed25519",
            "generated/private.pem",
        ):
            with self.subTest(relative=relative), self.assertRaisesRegex(
                publish_root.PublicationError, "forbidden"
            ):
                publish_root._reject_forbidden_destination(relative)

    def test_every_mapped_source_passes_host_path_and_credential_preflight(self) -> None:
        publish_root._audit_copy_rule_sources(
            publish_root.publication_copy_rules(R6, REPOSITORY)
        )

    def test_publication_template_relocation_is_exact_and_unambiguous(self) -> None:
        name = publish_root.PUBLICATION_TEMPLATE_FILES[0]
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            source_root = parent / "source"
            assembled_root = parent / "assembled"
            ambiguous_root = parent / "ambiguous"
            for root, relative in (
                (source_root, f"publication/{name}"),
                (assembled_root, name),
                (ambiguous_root, f"publication/{name}"),
                (ambiguous_root, name),
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("checked\n", encoding="utf-8")
            self.assertEqual(
                publish_root._publication_template_source(source_root, name),
                f"publication/{name}",
            )
            self.assertEqual(
                publish_root._publication_template_source(assembled_root, name),
                name,
            )
            with self.assertRaisesRegex(
                publish_root.PublicationError, "exactly one source or assembled"
            ):
                publish_root._publication_template_source(ambiguous_root, name)

    def test_license_marker_cannot_claim_an_unmapped_license(self) -> None:
        records = [
            {
                "destination": "README.md",
                "source_scope": "test",
                "source": "README.md",
                "bytes": 1,
                "sha256": "0" * 64,
                "mode": "0644",
            }
        ]
        manifest = {
            "files": records,
            "license": publish_root._license_status(records),
        }
        publish_root._audit_license_marker(manifest)
        manifest["license"] = {
            "status": "owner_selected_file_preserved",
            "file": "LICENSE",
        }
        with self.assertRaisesRegex(
            publish_root.PublicationError, "license marker differs"
        ):
            publish_root._audit_license_marker(manifest)

    def test_publication_payload_separates_software_and_physical_status(self) -> None:
        payload = publish_root._publication_manifest_payload(
            [],
            {
                "project": {"name": "X", "revision": "derived", "edition": "E"},
                "derived_inventory": {"package_counts": {}},
                "canonical_packages": [],
                "governing_drawings": ["drawings/derived.svg"],
                "physical_qualification_blockers": ["physical coupon"],
            },
            "0" * 64,
            {"revision": "fallback", "status": "preserved"},
        )
        self.assertIs(payload["software_model_publication_eligible"], True)
        self.assertIs(payload["physical_installation_qualified"], False)
        self.assertIs(payload["production_release_eligible"], False)
        self.assertTrue(payload["physical_qualification_blockers"])

    def test_copy_is_byte_and_executable_mode_preserving(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root = root / "source"
            destination = root / "destination"
            source_root.mkdir()
            destination.mkdir()
            source = source_root / "tool.py"
            source.write_bytes(b"#!/usr/bin/env python3\n")
            source.chmod(0o754)
            rule = publish_root.CopyRule(
                "test", source_root, "tool.py", "scripts/tool.py"
            )
            records = publish_root._copy_rules([rule], destination)
            copied = destination / "scripts" / "tool.py"
            self.assertEqual(source.read_bytes(), copied.read_bytes())
            self.assertEqual(publish_root._file_mode(source), publish_root._file_mode(copied))
            self.assertEqual(records[0]["sha256"], hashlib.sha256(source.read_bytes()).hexdigest())


class FailClosedLifecycleTests(unittest.TestCase):
    def test_full_release_failure_happens_before_staging_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            repository = parent / "repository"
            staged = parent / "checked-input"
            destination = parent / "new-publication"
            repository.mkdir()
            staged.mkdir()
            calls: list[bool] = []

            def fail_full(_python: Path, _root: Path, source_only: bool) -> dict[str, object]:
                calls.append(source_only)
                if source_only:
                    return {"passed": True, "mode": "source-only", "derived": {}}
                raise publish_root.PublicationError("full release refused")

            with mock.patch.object(publish_root.tempfile, "mkdtemp") as make_stage:
                with self.assertRaisesRegex(
                    publish_root.PublicationError, "full release refused"
                ):
                    publish_root.publish_checked_release(
                        staged_release=staged,
                        repository_root=repository,
                        destination=destination,
                        python=Path(sys.executable),
                        check_runner=fail_full,
                    )
            self.assertEqual(calls, [True, False])
            make_stage.assert_not_called()
            self.assertFalse(os.path.lexists(destination))

    def test_existing_destination_or_broken_symlink_is_refused_without_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            repository = parent / "repository"
            staged = parent / "staged"
            repository.mkdir()
            staged.mkdir()
            checker = mock.Mock()
            existing = parent / "existing"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                publish_root.publish_checked_release(
                    staged_release=staged,
                    repository_root=repository,
                    destination=existing,
                    python=Path(sys.executable),
                    check_runner=checker,
                )
            broken = parent / "broken"
            broken.symlink_to(parent / "absent")
            with self.assertRaises(FileExistsError):
                publish_root.publish_checked_release(
                    staged_release=staged,
                    repository_root=repository,
                    destination=broken,
                    python=Path(sys.executable),
                    check_runner=checker,
                )
            checker.assert_not_called()

    def test_atomic_commit_has_no_replace_fallback_and_preserves_existing(self) -> None:
        source_text = (R6 / "publish_root.py").read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        calls = {
            f"{node.func.value.id}.{node.func.attr}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
        }
        self.assertNotIn("os.replace", calls)
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            source = parent / "unpublished"
            destination = parent / "existing"
            source.mkdir()
            destination.mkdir()
            (destination / "user.txt").write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                publish_root._exclusive_atomic_rename(source, destination)
            self.assertEqual((destination / "user.txt").read_text(), "preserve")
            self.assertTrue(source.is_dir())

    def test_owned_stage_cleanup_rejects_any_broad_or_unowned_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            unowned = parent / "user-tree"
            unowned.mkdir()
            with self.assertRaisesRegex(publish_root.PublicationError, "unsafe"):
                publish_root._remove_owned_unpublished_stage(
                    unowned, parent, ".release.unpublished-"
                )
            self.assertTrue(unowned.is_dir())


class GithubPublicationTemplateTests(unittest.TestCase):
    def test_workflow_runs_audit_source_full_and_complete_tests(self) -> None:
        workflow = (GITHUB_TEMPLATE_ROOT / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )
        for required in (
            'Path(os.environ["RUNNER_TEMP"]) / "r6-publication"',
            'manifest["files"]',
            "unsafe publication destination",
            "--audit-publication",
            '"$RUNNER_TEMP/r6-publication"',
            "release_check.py --root . --source-only",
            "release_check.py --root .",
            "unittest discover -s tests",
            "git diff --exit-code",
            "git status --porcelain=v1 --untracked-files=all",
        ):
            self.assertIn(required, workflow)
        self.assertNotIn("--audit-publication .", workflow)
        self.assertNotIn("scripts/build_all.sh", workflow)

    def test_templates_do_not_reintroduce_obsolete_hybrid_release_language(self) -> None:
        corpus = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(GITHUB_TEMPLATE_ROOT.rglob("*"))
            if path.is_file()
        ).lower()
        for obsolete in (
            "untested hybrid prototype",
            "plywood and steel remain the permanent load path",
            "101 objects",
            "r5 configuration",
            "artist_rendering_triadic_palatine_order.png",
            "structurally all-petg shelf is outside this project",
        ):
            self.assertNotIn(obsolete, corpus)
        self.assertIn("physical_installation_qualified", corpus)
        self.assertIn("production_release_eligible", corpus)
        self.assertIn("no tested load rating", corpus)


if __name__ == "__main__":
    unittest.main()
