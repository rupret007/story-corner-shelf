#!/usr/bin/env python3
"""Generator-side package adapter and fail-closed source regressions."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

import generate_all_petg_r6 as generator  # noqa: E402
from package_validation import serialized_mesh_geometry_evidence  # noqa: E402
from package_layout import (  # noqa: E402
    QUALIFICATION_FAMILY_COUNTS,
    SELECTED_LEVEL_COUNT,
)
from release_inventory import EXPECTED_ONE_LEVEL_FAMILY_COUNTS  # noqa: E402


def file_digests(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class R6GeneratorPackageAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads((R6 / "config.json").read_text(encoding="utf-8"))
        cls.geometry, _warnings = generator.calculate_development_geometry(cls.cfg)
        cls.parts, *_reports = generator.build_parts(cls.cfg, cls.geometry)
        (
            cls.plans,
            cls.mesh_by_family,
            cls.source_audits,
            cls.report,
        ) = generator.build_release_package_context(
            cls.cfg,
            plan=cls.geometry["plan_object"],
            parts=cls.parts,
        )

    def test_emitted_stl_source_set_excludes_obsolete_interface_studies(self) -> None:
        names = {part.name for part in self.parts}
        self.assertEqual(len(self.parts), 49)
        self.assertNotIn(
            "R6_DEV_X_BRACED_3_4_5_CORBEL_PIER_SOLID_WALL_PLATE", names
        )
        self.assertNotIn(
            "R6_DEV_GRAND_NEAR_SEMICIRCULAR_TIED_FRAME_HALF_LONG_BAY", names
        )

    def test_dual_clearance_coupon_embodies_exact_tenon_and_real_cross_key_bore(self) -> None:
        coupon = next(
            part
            for part in self.parts
            if part.name == "R6_DEV_JOINERY_CLEARANCE_LADDER_TONGUE"
        )
        metrics = coupon.design_metrics
        self.assertEqual(
            metrics["top_tenon_stub_run_depth_engagement_mm"],
            [18.0, 8.0, 22.0],
        )
        self.assertEqual(metrics["top_tenon_through_bore_diameter_mm"], 4.0)
        self.assertTrue(metrics["dual_coupon_one_connected_body"])
        self.assertFalse(metrics["structural_credit"])
        self.assertFalse(metrics["complete_capture_claim"])
        self.assertTrue(coupon.mesh.is_watertight)
        self.assertEqual(len(coupon.mesh.split(only_watertight=False)), 1)
        bore_probe = generator.cylinder_y(
            3.5,
            7.0,
            center_xz=(37.0, 11.0),
            y0=6.5,
            sections=48,
        )
        overlap = generator.trimesh.boolean.intersection(
            [coupon.mesh, bore_probe],
            engine="manifold",
            check_volume=True,
        )
        self.assertLess(abs(float(overlap.volume)), 1.0e-7)

    def test_generation_source_bundle_is_exact_complete_and_recomputable(self) -> None:
        bundle = generator.generation_source_bundle()
        expected_paths = list(generator.GENERATION_SOURCE_BUNDLE_FILENAMES)
        self.assertEqual(expected_paths, sorted(expected_paths))
        self.assertEqual(len(expected_paths), 14)
        self.assertEqual(bundle["schema_version"], 1)
        self.assertEqual(bundle["hash_algorithm"], "sha256")
        self.assertTrue(bundle["config_sha256_enforced_separately"])
        self.assertEqual(bundle["source_file_count"], 14)
        self.assertEqual(
            [record["path"] for record in bundle["records"]], expected_paths
        )
        aggregate = hashlib.sha256()
        for record in bundle["records"]:
            path = R6 / record["path"]
            payload = path.read_bytes()
            self.assertEqual(record["size_bytes"], len(payload))
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())
            aggregate.update(record["path"].encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(str(record["size_bytes"]).encode("ascii"))
            aggregate.update(b"\0")
            aggregate.update(record["sha256"].encode("ascii"))
            aggregate.update(b"\n")
        self.assertEqual(bundle["aggregate_sha256"], aggregate.hexdigest())

        tree = ast.parse((R6 / "generate_all_petg_r6.py").read_text(encoding="utf-8"))
        imported_local_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module.split(".", 1)[0]
                if (R6 / f"{module}.py").is_file():
                    imported_local_modules.add(module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".", 1)[0]
                    if (R6 / f"{module}.py").is_file():
                        imported_local_modules.add(module)
        expected_dependencies = {
            Path(filename).stem
            for filename in expected_paths
            if filename != "generate_all_petg_r6.py"
        }
        self.assertEqual(imported_local_modules, expected_dependencies)

        allowlisted_modules = {Path(filename).stem for filename in expected_paths}
        for filename in expected_paths:
            source_path = R6 / filename
            source_tree = ast.parse(source_path.read_text(encoding="utf-8"))
            transitive_local_imports: set[str] = set()
            for node in ast.walk(source_tree):
                modules: list[str] = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    modules.append(node.module.split(".", 1)[0])
                elif isinstance(node, ast.Import):
                    modules.extend(
                        alias.name.split(".", 1)[0] for alias in node.names
                    )
                transitive_local_imports.update(
                    module
                    for module in modules
                    if (R6 / f"{module}.py").is_file()
                )
            self.assertEqual(
                transitive_local_imports - allowlisted_modules,
                set(),
                f"{filename} imports a local module outside the source bundle",
            )

    def test_all_49_actual_stls_survive_serialized_round_trip_as_closed_solids(self) -> None:
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-stl-roundtrip-") as directory:
            output = Path(directory)
            stl_output = output / "stl"
            model_output = output / "model_only_3mf"
            stl_output.mkdir()
            model_output.mkdir()
            with (
                mock.patch.object(generator, "OUT", output),
                mock.patch.object(generator, "STL_OUT", stl_output),
                mock.patch.object(generator, "MODEL_3MF_OUT", model_output),
            ):
                generator.write_part_files(
                    self.parts,
                    self.cfg,
                    include_development_3mf=False,
                )
                reports = [
                    generator.audit_serialized_stl(path)
                    for path in sorted(stl_output.glob("*.stl"))
                ]
        self.assertEqual(len(reports), 49)
        self.assertTrue(
            all(report["serialized_geometry_audit_passed"] for report in reports)
        )
        self.assertTrue(
            all(report["raw_zero_area_triangle_count"] == 0 for report in reports)
        )
        self.assertTrue(
            all(report["ordinary_reload_body_count"] == 1 for report in reports)
        )

    def test_all_49_individual_3mfs_are_exact_deterministic_stl_geometry_pairs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-individual-pairs-") as directory:
            output = Path(directory)
            stl_output = output / "stl"
            canonical_output = output / "model_only_3mf"
            individual_output = output / "individual_model_only_3mf"
            for path in (stl_output, canonical_output, individual_output):
                path.mkdir()
            with (
                mock.patch.object(generator, "OUT", output),
                mock.patch.object(generator, "STL_OUT", stl_output),
                mock.patch.object(generator, "MODEL_3MF_OUT", canonical_output),
                mock.patch.object(
                    generator,
                    "INDIVIDUAL_MODEL_3MF_OUT",
                    individual_output,
                ),
            ):
                generator.write_part_files(self.parts, self.cfg)
                first = file_digests(output)
                audits = [
                    generator.audit_individual_stl_3mf_pair(
                        source_name=part.name,
                        stl_path=stl_output / f"{part.name}.stl",
                        three_mf_path=(
                            individual_output / f"MODEL_ONLY_{part.name}.3mf"
                        ),
                    )
                    for part in sorted(self.parts, key=lambda item: item.name)
                ]
                generator.write_part_files(self.parts, self.cfg)
                second = file_digests(output)
                stl_count = len(list(stl_output.glob("*.stl")))
                individual_count = len(list(individual_output.glob("*.3mf")))
                canonical_count = len(list(canonical_output.glob("*.3mf")))
        self.assertEqual(stl_count, 49)
        self.assertEqual(individual_count, 49)
        self.assertEqual(canonical_count, 0)
        self.assertEqual(first, second)
        self.assertTrue(all(item["all_checks_pass"] for item in audits))
        self.assertTrue(
            all(
                len(item["common_canonical_triangle_digest"]) == 64
                for item in audits
            )
        )

    def test_exact_plan_counts_and_valid_alias_collapse(self) -> None:
        one_level_count = sum(EXPECTED_ONE_LEVEL_FAMILY_COUNTS.values())
        self.assertEqual(
            [plan.physical_object_count for plan in self.plans],
            [
                8,
                len(self.plans[1].mesh_families),
                sum(QUALIFICATION_FAMILY_COUNTS.values()),
                one_level_count,
                SELECTED_LEVEL_COUNT * one_level_count,
            ],
        )
        self.assertEqual(
            [plan.package_id for plan in self.plans],
            [
                "print_first_prototypes",
                "unique_parts_catalog",
                "worst_case_one_bay_qualification",
                "one_level_l",
                "two_level_full_project",
            ],
        )
        self.assertEqual(len(self.plans[0].mesh_families), 8)
        self.assertEqual(self.plans[1].physical_object_count, 49)
        self.assertEqual(
            self.plans[1].physical_object_count,
            len(self.plans[1].mesh_families),
        )
        one_level_cassettes = [
            item
            for item in self.plans[3].instances
            if "::deck_cassette::" in item.logical_name
        ]
        self.assertEqual(len(one_level_cassettes), 18)
        self.assertEqual(
            len({item.mesh_family for item in one_level_cassettes}), 18
        )
        self.assertEqual(self.report["position_specific_cassette_source_count"], 18)
        self.assertFalse(
            self.report["position_specific_cassette_aliasing_allowed"]
        )
        self.assertEqual(self.report["unresolved_mesh_families"], [])

    def test_every_canonical_package_has_repeat_weighted_solid_mass_context(self) -> None:
        report = self.report["repeat_weighted_solid_model_mass"]
        estimates = report["package_estimates"]
        self.assertEqual(set(estimates), {plan.package_id for plan in self.plans})
        for plan in self.plans:
            estimate = estimates[plan.package_id]
            self.assertEqual(
                estimate["physical_object_count"], plan.physical_object_count
            )
            self.assertGreater(
                estimate["repeat_weighted_model_solid_volume_mm3"], 0.0
            )
            self.assertGreater(estimate["contextual_all_solid_petg_mass_g"], 0.0)
            self.assertEqual(
                estimate["estimate_class"], "CAD MODEL-SOLID CONTEXT ONLY"
            )
            self.assertFalse(estimate["sliced_or_finished_mass_claim"])
            self.assertFalse(estimate["load_capacity_claim"])
        self.assertEqual(
            report["one_level_contextual_all_solid_petg_mass_g"],
            estimates["one_level_l"]["contextual_all_solid_petg_mass_g"],
        )
        self.assertEqual(
            report["two_level_contextual_all_solid_petg_mass_g"],
            estimates["two_level_full_project"][
                "contextual_all_solid_petg_mass_g"
            ],
        )
        self.assertEqual(
            report["two_level_contextual_all_solid_petg_mass_g"],
            2.0 * report["one_level_contextual_all_solid_petg_mass_g"],
        )
        self.assertEqual(
            estimates["two_level_full_project"]
            ["repeat_weighted_model_solid_volume_mm3"],
            2.0
            * estimates["one_level_l"]["repeat_weighted_model_solid_volume_mm3"],
        )
        self.assertTrue(report["bambu_sliced_mass_required_before_print"])
        self.assertTrue(
            report["weighed_finished_tare_required_for_physical_qualification"]
        )

    def test_all_five_software_model_packages_arrange_with_physical_claims_false(self) -> None:
        for index, plan in enumerate(self.plans):
            placed = generator.arrange_package_plan(
                plan,
                self.mesh_by_family,
                source_audits=None if index == 0 else self.source_audits,
            )
            self.assertEqual(len(placed), plan.physical_object_count)

    def test_release_sidecars_preserve_unsliced_and_physical_gate_truth(self) -> None:
        validations = [
            {
                "package_id": plan.package_id,
                "file": plan.filename,
                "all_checks_pass": True,
                "software_model_package_eligible": True,
                "physical_installation_qualified": False,
                "production_release_eligible": False,
            }
            for plan in self.plans
        ]
        blockers = ["physical same-PETG and wall qualification pending"]
        slice_report, model_report = generator.build_release_sidecar_reports(
            self.cfg,
            config_payload=(R6 / "config.json").read_bytes(),
            plans=self.plans,
            package_validations=validations,
            individual_pair_audits=[
                {
                    "source_part_name": f"R6_DEV_TEST_SOURCE_{index:02d}",
                    "all_checks_pass": True,
                }
                for index in range(1, 50)
            ],
            physical_blockers=blockers,
            solid_model_mass_report=self.report[
                "repeat_weighted_solid_model_mass"
            ],
        )
        expected_packages = [
            {"package_id": plan.package_id, "filename": plan.filename}
            for plan in self.plans
        ]
        self.assertFalse(slice_report["performed"])
        self.assertFalse(slice_report["embedded_gcode_allowed"])
        self.assertFalse(slice_report["printer_profile_embedded"])
        self.assertFalse(slice_report["printer_confirmed"])
        self.assertFalse(slice_report["nozzle_confirmed"])
        self.assertFalse(slice_report["build_plate_confirmed"])
        self.assertFalse(slice_report["petg_product_confirmed"])
        self.assertTrue(slice_report["bambu_studio_sliced_mass_required"])
        self.assertTrue(slice_report["weighed_finished_tare_required"])
        self.assertEqual(slice_report["canonical_packages"], expected_packages)
        self.assertTrue(model_report["all_packages_model_only"])
        self.assertEqual(model_report["canonical_packages"], expected_packages)
        self.assertEqual(model_report["package_audits"], validations)
        for report in (slice_report, model_report):
            self.assertTrue(report["software_model_package_eligible"])
            self.assertFalse(report["physical_installation_qualified"])
            self.assertFalse(report["production_release_eligible"])
            self.assertEqual(report["physical_qualification_blockers"], blockers)

    def test_one_and_two_level_schedule_artifacts_are_exact_and_deterministic(self) -> None:
        one_level_count = sum(EXPECTED_ONE_LEVEL_FAMILY_COUNTS.values())
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-schedules-") as directory:
            output = Path(directory)
            with mock.patch.object(generator, "OUT", output):
                first_paths = generator.write_release_schedules(
                    self.cfg,
                    plan=self.geometry["plan_object"],
                )
                first = {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in first_paths
                }
                one_json = json.loads(
                    (output / "parts_schedule_one_level.json").read_text(
                        encoding="utf-8"
                    )
                )
                two_json = json.loads(
                    (output / "parts_schedule_two_levels.json").read_text(
                        encoding="utf-8"
                    )
                )
                second_paths = generator.write_release_schedules(
                    self.cfg,
                    plan=self.geometry["plan_object"],
                )
                second = {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in second_paths
                }
        self.assertEqual(
            [path.name for path in first_paths],
            [
                "parts_schedule_one_level.csv",
                "parts_schedule_one_level.json",
                "parts_schedule_two_levels.csv",
                "parts_schedule_two_levels.json",
            ],
        )
        self.assertEqual(len(one_json), one_level_count)
        self.assertEqual(len(two_json), 2 * one_level_count)
        self.assertEqual(first, second)

    def test_installed_source_audits_never_hide_bores_rails_or_open_interfaces(self) -> None:
        self.assertTrue(self.source_audits)
        for family, audit in self.source_audits.items():
            self.assertEqual(family, audit.mesh_family)
            self.assertEqual(audit.wall_bore_count, 0)
            self.assertFalse(audit.rail_or_saddle_geometry)
            self.assertTrue(audit.software_model_package_eligible)
            self.assertFalse(audit.physical_installation_qualified)
            self.assertFalse(audit.production_release_eligible)
            self.assertEqual(audit.unresolved_interfaces, ())
            searchable = f"{family} {audit.source_part_name}".lower()
            self.assertNotIn("stitch_rail", searchable)
            self.assertNotIn("sliding_saddle", searchable)
            self.assertNotIn("saddle_pin", searchable)

    def test_print_first_instanced_3mf_is_strict_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-package-") as directory:
            model_output = Path(directory)
            with mock.patch.object(generator, "MODEL_3MF_OUT", model_output):
                first_report = generator.emit_print_first_package(
                    self.plans, self.mesh_by_family
                )
                path = model_output / self.plans[0].filename
                first_digest = hashlib.sha256(path.read_bytes()).hexdigest()
                second_report = generator.emit_print_first_package(
                    self.plans, self.mesh_by_family
                )
                second_digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertTrue(first_report["all_checks_pass"])
            self.assertTrue(second_report["all_checks_pass"])
            self.assertEqual(first_digest, second_digest)
            self.assertEqual(first_report["build_object_count"], 8)
            self.assertEqual(first_report["mesh_family_count"], 8)
            self.assertEqual(
                first_report["metadata"]["Description"],
                "MODEL-ONLY; EXPERIMENTAL; UNRATED; NO G-CODE",
            )

    def test_all_five_canonical_model_packages_are_strict_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-all-packages-") as directory:
            model_output = Path(directory)
            with mock.patch.object(generator, "MODEL_3MF_OUT", model_output):
                first_reports = generator.emit_all_canonical_model_packages(
                    self.plans,
                    self.mesh_by_family,
                    self.source_audits,
                )
                first = {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(model_output.glob("*.3mf"))
                }
                second_reports = generator.emit_all_canonical_model_packages(
                    self.plans,
                    self.mesh_by_family,
                    self.source_audits,
                )
                second = {
                    path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(model_output.glob("*.3mf"))
                }
            expected_pair_audits = []
            for part in sorted(self.parts, key=lambda item: item.name):
                stl_ready = generator.serialization_ready_mesh(
                    part.mesh,
                    target="stl",
                    source_name=part.name,
                )
                evidence = serialized_mesh_geometry_evidence(
                    stl_ready.vertices,
                    stl_ready.faces,
                )
                expected_pair_audits.append(
                    {
                        "source_part_name": part.name,
                        "all_checks_pass": True,
                        "triangle_count": evidence["triangle_count"],
                        "bounds_mm": evidence["bounds_mm"],
                        "common_canonical_triangle_digest": evidence[
                            "canonical_triangle_digest_common_grid"
                        ],
                    }
                )
            source_bijection = (
                generator.audit_canonical_package_sources_against_individual_exports(
                    plans=self.plans,
                    package_validations=first_reports,
                    individual_pair_audits=expected_pair_audits,
                )
            )
        expected_files = {plan.filename for plan in self.plans}
        self.assertEqual(set(first), expected_files)
        self.assertEqual(first, second)
        self.assertEqual(
            [report["package_id"] for report in first_reports],
            [plan.package_id for plan in self.plans],
        )
        self.assertEqual(first_reports, second_reports)
        self.assertTrue(source_bijection["all_checks_pass"])
        self.assertEqual(source_bijection["individual_source_count"], 49)
        self.assertEqual(source_bijection["canonical_package_count"], 5)
        mutated_reports = json.loads(json.dumps(first_reports))
        mutated_record = next(
            record
            for report in mutated_reports
            for record in report["serialized_mesh_geometry_records"]
            if str(record["name"]).endswith(
                "R6_DEV_CASSETTE_RETURN_06_OF_06"
            )
        )
        mutated_record["canonical_triangle_digest_common_grid"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "canonical-digest"):
            generator.audit_canonical_package_sources_against_individual_exports(
                plans=self.plans,
                package_validations=mutated_reports,
                individual_pair_audits=expected_pair_audits,
            )
        for report in first_reports:
            self.assertTrue(report["all_checks_pass"])
            self.assertTrue(report["software_model_package_eligible"])
            self.assertFalse(report["physical_installation_qualified"])
            self.assertFalse(report["production_release_eligible"])
            self.assertEqual(
                report["metadata"]["Description"],
                "MODEL-ONLY; EXPERIMENTAL; UNRATED; NO G-CODE",
            )
            serialized = report["serialized_mesh_geometry_audit"]
            self.assertTrue(serialized["serialized_mesh_geometry_audit_passed"])
            self.assertEqual(serialized["serialized_zero_area_triangle_count"], 0)
            self.assertEqual(serialized["serialized_mesh_failures"], [])
        self.assertEqual(
            first_reports[1]["serialized_mesh_geometry_audit"][
                "serialized_mesh_resource_count"
            ],
            49,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
