#!/usr/bin/env python3
"""Focused fail-closed release-check and atomic-build-wrapper tests."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

import build_release  # noqa: E402
import release_check  # noqa: E402


class StrictJsonTests(unittest.TestCase):
    def test_rejects_duplicate_keys_at_any_depth(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"outer":{"safe":1,"safe":2}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key 'safe'"):
                release_check.load_json_strict(path)

    def test_accepts_normal_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ok.json"
            path.write_text('{"outer":{"safe":1}}', encoding="utf-8")
            self.assertEqual(release_check.load_json_strict(path), {"outer": {"safe": 1}})


class ArtifactAllowListTests(unittest.TestCase):
    def _record(self, path: Path, relative: str) -> dict[str, object]:
        payload = path.read_bytes()
        return {"path": relative, "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}

    def test_rejects_extra_printable_and_stale_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            models = root / "generated" / "model_only_3mf"
            models.mkdir(parents=True)
            declared = models / "declared.3mf"
            declared.write_bytes(b"changed")
            (models / "extra.3mf").write_bytes(b"extra")
            manifest = {
                "generated_artifact_count_excluding_manifest": 1,
                "artifacts": [{"path": "model_only_3mf/declared.3mf", "bytes": 3, "sha256": hashlib.sha256(b"old").hexdigest()}],
            }
            issues: list[release_check.Issue] = []
            release_check._check_artifact_allowlist(root, manifest, issues)
        self.assertIn("generated.extra_printable", {item.code for item in issues})
        self.assertIn("manifest.stale_artifact", {item.code for item in issues})
        self.assertIn("manifest.artifact_size", {item.code for item in issues})

    def test_exact_printable_allowlist_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            models = root / "generated" / "model_only_3mf"
            models.mkdir(parents=True)
            artifact = models / "declared.3mf"
            artifact.write_bytes(b"payload")
            manifest = {"generated_artifact_count_excluding_manifest": 1, "artifacts": [self._record(artifact, "model_only_3mf/declared.3mf")]}
            (root / "generated" / "manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            issues: list[release_check.Issue] = []
            release_check._check_artifact_allowlist(root, manifest, issues)
        self.assertEqual(issues, [])

    def test_rejects_extra_and_missing_nonprintable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = root / "generated"
            generated.mkdir()
            declared = generated / "declared.csv"
            declared.write_text("part,count\nkey,1\n", encoding="utf-8")
            manifest = {
                "generated_artifact_count_excluding_manifest": 1,
                "artifacts": [self._record(declared, "declared.csv")],
            }
            (generated / "stale_report.json").write_text("{}\n", encoding="utf-8")
            issues: list[release_check.Issue] = []
            release_check._check_artifact_allowlist(root, manifest, issues)
            self.assertIn("generated.extra_artifact", {item.code for item in issues})

            (generated / "stale_report.json").unlink()
            declared.unlink()
            issues = []
            release_check._check_artifact_allowlist(root, manifest, issues)
        self.assertIn("generated.missing_artifact", {item.code for item in issues})


class CanonicalPackageSourceGeometryTests(unittest.TestCase):
    def test_checked_tree_has_exact_canonical_to_individual_source_bijection(self) -> None:
        manifest = release_check.load_json_strict(R6 / "generated" / "manifest.json")
        validation = release_check.load_json_strict(
            R6 / "generated" / "validation.json"
        )
        issues: list[release_check.Issue] = []
        release_check._check_canonical_package_source_bijection(
            R6,
            manifest,
            validation,
            issues,
        )
        self.assertEqual(issues, [])

        mutated = json.loads(json.dumps(validation))
        mutated["release_package_planning"][
            "canonical_package_source_geometry_bijection"
        ]["packages"][0][
            "all_sources_equal_named_individual_exports"
        ] = False
        issues = []
        release_check._check_canonical_package_source_bijection(
            R6,
            manifest,
            mutated,
            issues,
        )
        self.assertIn(
            "validation.canonical_package_source_geometry_bijection",
            {item.code for item in issues},
        )


class GenerationSourceBundleTests(unittest.TestCase):
    def _write_source_fixture(self, root: Path) -> dict[str, object]:
        aggregate = hashlib.sha256()
        records: list[dict[str, object]] = []
        for index, relative in enumerate(release_check.GENERATION_SOURCE_FILES):
            payload = f"# deterministic source {index}: {relative}\n".encode("utf-8")
            (root / relative).write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            record = {
                "path": relative,
                "size_bytes": len(payload),
                "sha256": digest,
            }
            records.append(record)
            aggregate.update(relative.encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(str(len(payload)).encode("ascii"))
            aggregate.update(b"\0")
            aggregate.update(digest.encode("ascii"))
            aggregate.update(b"\n")
        return {
            "schema_version": 1,
            "hash_algorithm": "sha256",
            "aggregate_serialization": release_check.GENERATION_SOURCE_BUNDLE_SERIALIZATION,
            "config_sha256_enforced_separately": True,
            "source_file_count": 14,
            "aggregate_sha256": aggregate.hexdigest(),
            "records": records,
        }

    def test_exact_root_relative_schema_and_aggregate_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = self._write_source_fixture(root)
            observed = release_check._expected_generation_source_bundle(root)
            issues: list[release_check.Issue] = []
            release_check._check_generation_source_bundle(
                root,
                {"generation_source_bundle": expected},
                {"generation_source_bundle": expected},
                issues,
            )
        self.assertEqual(observed, expected)
        self.assertEqual(issues, [])
        self.assertEqual(
            [item["path"] for item in expected["records"]],
            list(release_check.GENERATION_SOURCE_FILES),
        )
        self.assertTrue(all("/" not in name for name in release_check.GENERATION_SOURCE_FILES))

    def test_schema_algorithm_order_and_alignment_mutations_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = self._write_source_fixture(root)
            mutations = (
                ("schema_version", True, "manifest.generation_source_bundle_schema"),
                ("hash_algorithm", "SHA-256", "manifest.generation_source_bundle_schema"),
                ("aggregate_serialization", "unspecified", "manifest.generation_source_bundle_schema"),
                ("config_sha256_enforced_separately", False, "manifest.generation_source_bundle_schema"),
                ("source_file_count", 13, "manifest.generation_source_bundle_schema"),
            )
            for field, value, expected_code in mutations:
                with self.subTest(field=field):
                    changed = json.loads(json.dumps(expected))
                    changed[field] = value
                    issues: list[release_check.Issue] = []
                    release_check._check_generation_source_bundle(
                        root,
                        {"generation_source_bundle": changed},
                        {"generation_source_bundle": expected},
                        issues,
                    )
                    codes = {item.code for item in issues}
                    self.assertIn(expected_code, codes)
                    self.assertIn("generated.generation_source_bundle_alignment", codes)

            reordered = json.loads(json.dumps(expected))
            reordered["records"].reverse()
            issues = []
            release_check._check_generation_source_bundle(
                root,
                {"generation_source_bundle": reordered},
                {"generation_source_bundle": reordered},
                issues,
            )
        codes = {item.code for item in issues}
        self.assertIn("manifest.generation_source_bundle_freshness", codes)
        self.assertIn("validation.generation_source_bundle_freshness", codes)

    def test_full_check_rejects_helper_source_byte_mutation_after_relocation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "published-root-shape"
            root.mkdir()
            shutil.copy2(R6 / "config.json", root / "config.json")
            shutil.copytree(R6 / "docs", root / "docs")
            shutil.copytree(R6 / "generated", root / "generated")
            for relative in release_check.GENERATION_SOURCE_FILES:
                shutil.copy2(R6 / relative, root / relative)

            bundle = release_check._expected_generation_source_bundle(root)
            validation_path = root / "generated" / "validation.json"
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            validation["generation_source_bundle"] = bundle
            validation_path.write_text(
                json.dumps(validation, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            manifest_path = root / "generated" / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["generation_source_bundle"] = bundle
            validation_payload = validation_path.read_bytes()
            validation_record = next(
                item for item in manifest["artifacts"] if item["path"] == "validation.json"
            )
            validation_record["bytes"] = len(validation_payload)
            validation_record["sha256"] = hashlib.sha256(validation_payload).hexdigest()
            manifest_path.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            baseline = release_check.check_repository(root, source_only=False)
            self.assertTrue(baseline["passed"], baseline["issues"])

            helper = root / "design_math.py"
            helper.write_bytes(helper.read_bytes() + b"# post-generation mutation\n")
            mutated = release_check.check_repository(root, source_only=False)
        self.assertFalse(mutated["passed"])
        codes = {item["code"] for item in mutated["issues"]}
        self.assertIn("manifest.generation_source_bundle_freshness", codes)
        self.assertIn("validation.generation_source_bundle_freshness", codes)


class InstalledPackageGateTests(unittest.TestCase):
    def test_finds_nested_package_validation_reports(self) -> None:
        payload = {"release": {"validations": [{"package_id": "one_level_l", "all_checks_pass": True, "plan_checks": {}}]}}
        reports = release_check._release_validation_reports(payload)
        self.assertTrue(reports["one_level_l"]["all_checks_pass"])

    def test_canonical_package_order_includes_every_release_phase(self) -> None:
        self.assertEqual(set(release_check.PACKAGE_ORDER), set(release_check.PACKAGE_FILENAMES))
        self.assertEqual(len(release_check.PACKAGE_ORDER), 5)


class FullContractSemanticGateTests(unittest.TestCase):
    def _documents(self) -> tuple[dict[str, object], dict[str, object]]:
        blockers = ["wall, print, coupon, and creep qualification remain required"]
        common: dict[str, object] = {
            "software_model_package_eligible": True,
            "production_release_allowed": False,
            "physical_qualification_blockers": blockers,
            "unresolved_software_interface_blockers": [],
        }
        manifest = {**common, "embedded_gcode_file_count": 0}
        validation = {
            **common,
            "physical_qualification_blockers": list(blockers),
            "unresolved_software_interface_blocker_count": 0,
        }
        return manifest, validation

    def test_exact_software_physical_split_passes(self) -> None:
        manifest, validation = self._documents()
        issues: list[release_check.Issue] = []
        release_check._check_top_level_generated_semantics(
            manifest, validation, issues
        )
        self.assertEqual(issues, [])

    def test_rejects_semantic_fail_open_mutations(self) -> None:
        mutations = (
            ("manifest", "software_model_package_eligible", False, "manifest.software_model_eligibility"),
            ("validation", "production_release_allowed", True, "validation.production_release_allowed"),
            ("validation", "physical_qualification_blockers", [], "validation.physical_qualification_blockers"),
            ("manifest", "unresolved_software_interface_blockers", ["open"], "manifest.software_interface_blockers"),
            ("validation", "unresolved_software_interface_blocker_count", 1, "validation.software_interface_blocker_count"),
            ("manifest", "embedded_gcode_file_count", 1, "manifest.gcode_count"),
        )
        for target, key, value, expected_code in mutations:
            with self.subTest(target=target, key=key):
                manifest, validation = self._documents()
                (manifest if target == "manifest" else validation)[key] = value
                issues: list[release_check.Issue] = []
                release_check._check_top_level_generated_semantics(
                    manifest, validation, issues
                )
                self.assertIn(expected_code, {item.code for item in issues})

    def test_rejects_misaligned_physical_blocker_lists(self) -> None:
        manifest, validation = self._documents()
        validation["physical_qualification_blockers"] = ["different blocker"]
        issues: list[release_check.Issue] = []
        release_check._check_top_level_generated_semantics(
            manifest, validation, issues
        )
        self.assertIn(
            "generated.physical_blocker_alignment",
            {item.code for item in issues},
        )


class SidecarReportGateTests(unittest.TestCase):
    def _write_reports(self, root: Path) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        (root / "generated").mkdir()
        (root / "config.json").write_text("{}\n", encoding="utf-8")
        config_hash = hashlib.sha256((root / "config.json").read_bytes()).hexdigest()
        packages = [
            {"package_id": package_id, "filename": release_check.PACKAGE_FILENAMES[package_id]}
            for package_id in release_check.PACKAGE_ORDER
        ]
        blockers = ["physical coupon and wall qualification remain required"]
        common = {
            "project_name": "Story Corner",
            "revision": "r6",
            "config_sha256": config_hash,
            "canonical_packages": packages,
            "software_model_package_eligible": True,
            "physical_installation_qualified": False,
            "production_release_eligible": False,
            "physical_qualification_blockers": blockers,
        }
        slice_report = {
            **common,
            "performed": False,
            "embedded_gcode_allowed": False,
            "printer_profile_embedded": False,
            "printer_confirmed": False,
            "nozzle_confirmed": False,
            "build_plate_confirmed": False,
            "petg_product_confirmed": False,
            "bambu_studio_sliced_mass_required": True,
            "weighed_finished_tare_required": True,
        }
        audits = [
            {
                "package_id": package_id,
                "all_checks_pass": True,
                "software_model_package_eligible": True,
                "physical_installation_qualified": False,
                "production_release_eligible": False,
            }
            for package_id in release_check.PACKAGE_ORDER
        ]
        estimates = {
            package_id: {
                "filename": release_check.PACKAGE_FILENAMES[package_id],
                "physical_object_count": release_check.EXPECTED_EXACT_PACKAGE_COUNTS.get(package_id, 1),
                "repeat_weighted_model_solid_volume_mm3": 1000.0,
                "contextual_all_solid_petg_mass_g": 1.27,
                "sliced_or_finished_mass_claim": False,
                "load_capacity_claim": False,
            }
            for package_id in release_check.PACKAGE_ORDER
        }
        estimates["two_level_full_project"][
            "repeat_weighted_model_solid_volume_mm3"
        ] = 2000.0
        model_report = {
            **common,
            "all_packages_model_only": True,
            "safety_description": release_check.SAFETY_DESCRIPTION,
            "canonical_package_count": len(release_check.PACKAGE_ORDER),
            "package_audits": audits,
            "all_package_audits_pass": True,
            "repeat_weighted_solid_model_mass": {
                "package_estimates": estimates,
                "one_level_contextual_all_solid_petg_mass_g": 10.0,
                "two_level_contextual_all_solid_petg_mass_g": 20.0,
                "bambu_sliced_mass_required_before_print": True,
                "weighed_finished_tare_required_for_physical_qualification": True,
                "tested_load_rating_created": False,
            },
        }
        (root / "generated" / "slice_report.json").write_text(
            json.dumps(slice_report), encoding="utf-8"
        )
        (root / "generated" / "model_3mf_report.json").write_text(
            json.dumps(model_report), encoding="utf-8"
        )
        report_names = {
            "slice_report": "slice_report.json",
            "model_3mf_report": "model_3mf_report.json",
        }
        plan_records = [
            {
                "package_id": package_id,
                "filename": release_check.PACKAGE_FILENAMES[package_id],
                "physical_object_count": estimates[package_id]["physical_object_count"],
            }
            for package_id in release_check.PACKAGE_ORDER
        ]
        source = {
            "project_name": "Story Corner",
            "revision": "r6",
            "package_counts": dict(release_check.EXPECTED_EXACT_PACKAGE_COUNTS),
        }
        return (
            source,
            {"release_report_artifacts": report_names},
            {
                "release_report_artifacts": report_names,
                "release_package_planning": {"plans": plan_records},
            },
        )

    def test_exact_unsliced_model_reports_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, manifest, validation = self._write_reports(root)
            issues: list[release_check.Issue] = []
            release_check._check_release_sidecars(root, source, manifest, validation, issues)
        self.assertEqual(issues, [])

    def test_rejects_sliced_claim_and_incomplete_audit_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, manifest, validation = self._write_reports(root)
            slice_path = root / "generated" / "slice_report.json"
            slice_report = json.loads(slice_path.read_text(encoding="utf-8"))
            slice_report["performed"] = True
            slice_path.write_text(json.dumps(slice_report), encoding="utf-8")
            model_path = root / "generated" / "model_3mf_report.json"
            model_report = json.loads(model_path.read_text(encoding="utf-8"))
            model_report["package_audits"].pop()
            model_report["repeat_weighted_solid_model_mass"]["package_estimates"][
                "print_first_prototypes"
            ]["physical_object_count"] = 99
            model_path.write_text(json.dumps(model_report), encoding="utf-8")
            issues: list[release_check.Issue] = []
            release_check._check_release_sidecars(root, source, manifest, validation, issues)
        codes = {item.code for item in issues}
        self.assertIn("reports.slice.performed", codes)
        self.assertIn("reports.model.audit_set", codes)
        self.assertIn("reports.model.mass_count", codes)

    def test_accepts_exact_independent_levels_after_three_decimal_rounding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, manifest, validation = self._write_reports(root)
            model_path = root / "generated" / "model_3mf_report.json"
            model_report = json.loads(model_path.read_text(encoding="utf-8"))
            mass = model_report["repeat_weighted_solid_model_mass"]
            mass["one_level_contextual_all_solid_petg_mass_g"] = 16000.338
            mass["two_level_contextual_all_solid_petg_mass_g"] = 32000.675
            mass["package_estimates"]["one_level_l"][
                "repeat_weighted_model_solid_volume_mm3"
            ] = 12598691.106
            mass["package_estimates"]["two_level_full_project"][
                "repeat_weighted_model_solid_volume_mm3"
            ] = 25197382.211
            model_path.write_text(json.dumps(model_report), encoding="utf-8")
            issues: list[release_check.Issue] = []
            release_check._check_release_sidecars(
                root, source, manifest, validation, issues
            )
        self.assertNotIn(
            "reports.model.mass_levels", {item.code for item in issues}
        )
        self.assertNotIn(
            "reports.model.volume_levels", {item.code for item in issues}
        )


class BuildWrapperSafetyTests(unittest.TestCase):
    def test_build_wrapper_has_no_publication_or_replace_path(self) -> None:
        source = (R6 / "build_release.py").read_text(encoding="utf-8")
        self.assertNotIn("--promote-to", source)
        self.assertNotIn("os.replace", source)
        self.assertFalse(hasattr(build_release, "atomic_promote_new"))


if __name__ == "__main__":
    unittest.main()
