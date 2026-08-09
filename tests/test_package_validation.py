#!/usr/bin/env python3
"""Strict checks for simple and compact-instanced neutral r6 packages."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from model_io import cuboid, write_instanced_model_3mf, write_model_3mf  # noqa: E402
from package_layout import (  # noqa: E402
    EXPECTED_EMITTED_SOURCE_PART_COUNT,
    PACKAGE_ORDER,
    PRINT_FIRST_REQUIRED_ROLES,
    PRINT_FIRST_PACKAGE_ID,
    UNIQUE_PARTS_PACKAGE_ID,
    PackageInstance,
    PackageMeshSourceAudit,
    PackagePlan,
    PrototypeSpec,
    arrange_package_plan,
    build_release_package_plans,
)
from package_validation import inspect_model_only_3mf, validate_package_3mf  # noqa: E402
from release_inventory import (  # noqa: E402
    enumerate_level_inventory,
    enumerate_selected_inventory,
)


DESCRIPTION = "MODEL-ONLY; EXPERIMENTAL; UNRATED; NO G-CODE"


class R6PackageValidationTests(unittest.TestCase):
    def test_simple_package_passes_with_one_exact_build_object(self) -> None:
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-package-") as directory:
            path = Path(directory) / "simple.3mf"
            write_model_3mf(
                path,
                "simple",
                DESCRIPTION,
                [("SIMPLE_PART", cuboid((10.0, 8.0, 3.2)), (0.0, 0.0, 0.0))],
            )
            report = inspect_model_only_3mf(path)
        self.assertTrue(report["all_checks_pass"], report["checks"])
        self.assertEqual(report["mesh_family_count"], 1)
        self.assertEqual(report["component_object_count"], 0)
        self.assertEqual(report["build_object_count"], 1)
        self.assertEqual(report["build_object_names"], ["SIMPLE_PART"])

    def test_instanced_package_passes_and_counts_physical_objects_not_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-package-") as directory:
            path = Path(directory) / "instanced.3mf"
            write_instanced_model_3mf(
                path,
                "instanced",
                DESCRIPTION,
                [("PIN", cuboid((4.8, 4.8, 20.4)))],
                [
                    ("PIN_001", "PIN", (0.0, 0.0, 0.0)),
                    ("PIN_002", "PIN", (10.0, 0.0, 0.0)),
                ],
            )
            report = inspect_model_only_3mf(path)
        self.assertTrue(report["all_checks_pass"], report["checks"])
        self.assertEqual(report["resource_object_count"], 3)
        self.assertEqual(report["mesh_family_count"], 1)
        self.assertEqual(report["component_object_count"], 2)
        self.assertEqual(report["build_object_count"], 2)
        self.assertEqual(report["build_object_names"], ["PIN_001", "PIN_002"])

    def test_exact_plan_validation_and_hashes_are_deterministic(self) -> None:
        plan = PackagePlan(
            package_id=PRINT_FIRST_PACKAGE_ID,
            title="Story Corner package validator fixture",
            purpose="Exercise exact compact-instanced validation.",
            instances=(
                PackageInstance("PRINT_FIRST::KEY::001", "prototype::key"),
                PackageInstance("PRINT_FIRST::PIN::001", "prototype::pin"),
                PackageInstance("PRINT_FIRST::PIN::002", "prototype::pin"),
                PackageInstance("PRINT_FIRST::PIN::003", "prototype::pin"),
                PackageInstance("PRINT_FIRST::PIN::004", "prototype::pin"),
                PackageInstance("PRINT_FIRST::PIN::005", "prototype::pin"),
                PackageInstance("PRINT_FIRST::PIN::006", "prototype::pin"),
                PackageInstance("PRINT_FIRST::PIN::007", "prototype::pin"),
            ),
        )
        meshes = {
            "prototype::key": cuboid((30.0, 12.0, 5.0)),
            "prototype::pin": cuboid((4.8, 4.8, 20.4)),
        }
        placed = arrange_package_plan(plan, meshes, maximum_row_width_mm=80.0)
        families = [(family, meshes[family]) for family in plan.mesh_families]
        instances = [
            (item.logical_name, item.mesh_family, item.translation_mm) for item in placed
        ]
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-exact-package-") as directory:
            root = Path(directory)
            first = root / "first" / plan.filename
            second = root / "second" / plan.filename
            for path in (first, second):
                write_instanced_model_3mf(
                    path,
                    plan.title,
                    plan.description,
                    families,
                    instances,
                )
            first_report = validate_package_3mf(first, plan, placed)
            second_report = validate_package_3mf(second, plan, placed)
        self.assertTrue(first_report["all_checks_pass"], first_report)
        self.assertEqual(first_report["package_sha256"], second_report["package_sha256"])
        self.assertEqual(first_report["model_xml_sha256"], second_report["model_xml_sha256"])
        self.assertEqual(first_report["plan_sha256"], plan.plan_sha256)
        self.assertEqual(
            first_report["observed_inventory_sha256"], plan.inventory_sha256
        )
        self.assertTrue(all(first_report["plan_checks"].values()))

    def test_plan_validation_rejects_wrong_name_source_and_translation(self) -> None:
        plan = PackagePlan(
            package_id=PRINT_FIRST_PACKAGE_ID,
            title="Exact fixture",
            purpose="Prove plan equality fails closed.",
            instances=(
                *tuple(
                    PackageInstance(
                        f"OBJECT::{index:03d}",
                        "prototype::a" if index % 2 else "prototype::b",
                    )
                    for index in range(1, 9)
                ),
            ),
        )
        meshes = {
            "prototype::a": cuboid((10.0, 8.0, 4.0)),
            "prototype::b": cuboid((12.0, 6.0, 5.0)),
        }
        placed = arrange_package_plan(plan, meshes)
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-plan-tamper-") as directory:
            path = Path(directory) / plan.filename
            write_instanced_model_3mf(
                path,
                plan.title,
                plan.description,
                [(family, meshes[family]) for family in reversed(plan.mesh_families)],
                [
                    (
                        "OBJECT::WRONG" if index == 1 else item.logical_name,
                        (
                            "prototype::b"
                            if index == 0
                            else item.mesh_family
                        ),
                        placed[index].translation_mm,
                    )
                    for index, item in enumerate(plan.instances)
                ],
            )
            report = validate_package_3mf(path, plan, placed)
        self.assertTrue(report["neutral_3mf_checks_pass"], report["checks"])
        self.assertFalse(report["all_checks_pass"])
        self.assertFalse(report["plan_checks"]["exact_ordered_physical_inventory_names"])
        self.assertFalse(report["plan_checks"]["exact_ordered_mesh_source_inventory"])
        self.assertFalse(
            report["plan_checks"]["every_named_component_resolves_to_planned_mesh_family"]
        )
        self.assertFalse(report["plan_checks"]["exact_physical_inventory_sha256"])

    def test_exact_safety_metadata_and_no_gcode_entry_are_fail_closed(self) -> None:
        mesh = cuboid((5.0, 5.0, 5.0))
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-safety-tamper-") as directory:
            root = Path(directory)
            wrong_safety = root / "wrong_safety.3mf"
            write_model_3mf(
                wrong_safety,
                "wrong safety",
                "MODEL-ONLY; EXPERIMENTAL; UNRATED",
                [("OBJECT", mesh, (0.0, 0.0, 0.0))],
            )
            safety_report = inspect_model_only_3mf(wrong_safety)

            with_gcode = root / "with_gcode.3mf"
            write_model_3mf(
                with_gcode,
                "gcode injection fixture",
                DESCRIPTION,
                [("OBJECT", mesh, (0.0, 0.0, 0.0))],
            )
            with zipfile.ZipFile(with_gcode, "a") as archive:
                archive.writestr("Metadata/plate_1.gcode", b"G1 X0 Y0\n")
            gcode_report = inspect_model_only_3mf(with_gcode)
        self.assertFalse(safety_report["checks"]["safety_metadata_exact"])
        self.assertFalse(safety_report["all_checks_pass"])
        self.assertFalse(gcode_report["checks"]["exact_neutral_entries_only"])
        self.assertFalse(gcode_report["checks"]["contains_no_embedded_gcode"])
        self.assertFalse(gcode_report["checks"]["no_printer_or_slicer_profile"])
        self.assertFalse(gcode_report["all_checks_pass"])

    def test_all_five_exact_inventory_plans_emit_and_validate_with_stub_meshes(self) -> None:
        cfg = json.loads((R6 / "config.json").read_text(encoding="utf-8"))
        lower = enumerate_level_inventory(cfg, "lower")
        selected = enumerate_selected_inventory(cfg)
        prototype_roles = (
            ("receiver", ("fit_clearance",)),
            ("dual_tongue", ("fit_clearance",)),
            ("bearing", ("screw_head_bearing", "wall_screw_no_bore_blocker")),
            ("cassette", ("coffer_bridge_fit", "structural_cassette")),
            ("ornament_male", ("ornament_connector",)),
            ("ornament_female", ("ornament_connector",)),
            ("positive_key", ("positive_cross_key_fit",)),
            ("crown_pin", ("pin_fit",)),
        )
        prototypes = tuple(
            PrototypeSpec(
                f"PRINT_FIRST::{index:02d}::{name.upper()}",
                f"prototype::{name}",
                roles,
            )
            for index, (name, roles) in enumerate(prototype_roles, start=1)
        )
        catalog_families = tuple(
            f"source::R6_DEV_TEST_SOURCE_{index:02d}"
            for index in range(1, EXPECTED_EMITTED_SOURCE_PART_COUNT + 1)
        )

        def resolver(record: object) -> str:
            token = f"{record.family}::{record.variant}"  # type: ignore[attr-defined]
            index = sum(token.encode("utf-8")) % len(catalog_families)
            return catalog_families[index]

        plans = build_release_package_plans(
            prototypes=prototypes,
            catalog_mesh_families=catalog_families,
            one_level_records=lower,
            selected_records=selected,
            mesh_family_resolver=resolver,
        )
        all_families = sorted(
            {family for plan in plans for family in plan.mesh_families}
        )
        meshes = {
            family: cuboid(
                (
                    4.0 + index % 5,
                    5.0 + index % 7,
                    3.2 + index % 3,
                )
            )
            for index, family in enumerate(all_families)
        }
        audits = {
            family: PackageMeshSourceAudit(
                mesh_family=family,
                source_part_name=family.removeprefix("source::"),
                geometry_validation_passed=True,
                current_interface_geometry=True,
                software_model_package_eligible=True,
                physical_installation_qualified=False,
                production_release_eligible=False,
                placeholder_or_coupon=False,
                wall_bore_count=0,
                rail_or_saddle_geometry=False,
            )
            for index, family in enumerate(catalog_families, start=1)
        }
        reports = []
        with tempfile.TemporaryDirectory(prefix="story-corner-r6-five-packages-") as directory:
            root = Path(directory)
            for plan in plans:
                placed = arrange_package_plan(
                    plan,
                    meshes,
                    source_audits=audits,
                    maximum_row_width_mm=240.0,
                )
                path = root / plan.filename
                write_instanced_model_3mf(
                    path,
                    plan.title,
                    plan.description,
                    [(family, meshes[family]) for family in plan.mesh_families],
                    [
                        (item.logical_name, item.mesh_family, item.translation_mm)
                        for item in placed
                    ],
                )
                reports.append(
                    validate_package_3mf(
                        path,
                        plan,
                        placed,
                        source_audits=audits,
                    )
                )
                self.assertTrue(reports[-1]["software_model_package_eligible"])
                self.assertFalse(reports[-1]["physical_installation_qualified"])
                self.assertFalse(reports[-1]["production_release_eligible"])
                if plan.package_id == UNIQUE_PARTS_PACKAGE_ID:
                    without_source_evidence = validate_package_3mf(
                        path,
                        plan,
                        placed,
                    )
                    self.assertFalse(without_source_evidence["all_checks_pass"])
                    self.assertFalse(
                        without_source_evidence["plan_checks"][
                            "mesh_source::catalog_source_audits_supplied"
                        ]
                    )
        self.assertEqual(tuple(item["package_id"] for item in reports), PACKAGE_ORDER)
        self.assertTrue(all(item["all_checks_pass"] for item in reports), reports)
        self.assertEqual(
            [item["build_object_count"] for item in reports],
            [plan.physical_object_count for plan in plans],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
