#!/usr/bin/env python3
"""Deterministic virtual-canvas layout tests for exact r6 packages."""

from __future__ import annotations

import sys
import json
import unittest
from collections import Counter
from dataclasses import replace
from itertools import combinations
from pathlib import Path


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from model_io import cuboid  # noqa: E402
from package_layout import (  # noqa: E402
    EXPECTED_EMITTED_SOURCE_PART_COUNT,
    EXPECTED_EXACT_PACKAGE_COUNTS,
    ONE_LEVEL_PACKAGE_ID,
    ONE_LEVEL_PHYSICAL_OBJECT_COUNT,
    PACKAGE_ORDER,
    PRINT_FIRST_REQUIRED_ROLES,
    QUALIFICATION_FAMILY_COUNTS,
    SAFETY_DESCRIPTION,
    TWO_LEVEL_PACKAGE_ID,
    PackageInstance,
    PackageMeshSourceAudit,
    PrototypeSpec,
    arrange_on_virtual_canvas,
    arrange_package_plan,
    build_release_package_plans,
    build_unique_parts_catalog_plan,
    bounds_overlap_in_xy,
    canvas_bounds,
    mesh_source_audit_checks,
    release_mesh_family_key,
)
from release_inventory import (  # noqa: E402
    EXPECTED_ONE_LEVEL_FAMILY_COUNTS,
    enumerate_level_inventory,
    enumerate_selected_inventory,
)


def _prototype_specs() -> tuple[PrototypeSpec, ...]:
    sources = (
        ("RECEIVER_LADDER", ("fit_clearance",)),
        ("DUAL_TONGUE_TENON", ("fit_clearance",)),
        (
            "NO_BORE_BEARING",
            ("screw_head_bearing", "wall_screw_no_bore_blocker"),
        ),
        ("STRUCTURAL_CASSETTE", ("coffer_bridge_fit", "structural_cassette")),
        ("ORNAMENT_MALE", ("ornament_connector",)),
        ("ORNAMENT_FEMALE", ("ornament_connector",)),
        ("ACTUAL_POSITIVE_CROSS_KEY", ("positive_cross_key_fit",)),
        ("ACTUAL_CROWN_PIN", ("pin_fit",)),
    )
    return tuple(
        PrototypeSpec(
            f"PRINT_FIRST::{index:02d}::{name}",
            f"prototype::{name.lower()}",
            roles,
        )
        for index, (name, roles) in enumerate(sources, start=1)
    )


def _catalog_mesh_families() -> tuple[str, ...]:
    return tuple(
        f"source::R6_DEV_TEST_SOURCE_{index:02d}"
        for index in range(1, EXPECTED_EMITTED_SOURCE_PART_COUNT + 1)
    )


class R6PackageLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.meshes = {
            "A": cuboid((152.0, 152.4, 30.0)),
            "B": cuboid((120.0, 168.0, 18.0)),
            "PIN": cuboid((5.0, 5.0, 20.0)),
        }
        self.instances = tuple(
            [PackageInstance(f"A_{index:03d}", "A") for index in range(4)]
            + [PackageInstance(f"B_{index:03d}", "B") for index in range(4)]
            + [PackageInstance(f"PIN_{index:03d}", "PIN") for index in range(20)]
        )

    def test_layout_is_deterministic_positive_and_nonoverlapping(self) -> None:
        first = arrange_on_virtual_canvas(
            self.instances,
            self.meshes,
            maximum_row_width_mm=400.0,
            gap_mm=8.0,
        )
        second = arrange_on_virtual_canvas(
            self.instances,
            self.meshes,
            maximum_row_width_mm=400.0,
            gap_mm=8.0,
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(self.instances))
        for item in first:
            self.assertTrue(all(value >= -1e-7 for value in item.placed_bounds_mm[0]))
        for left, right in combinations(first, 2):
            self.assertFalse(bounds_overlap_in_xy(left, right), (left, right))
        width, height, depth = canvas_bounds(first)
        self.assertLessEqual(width, 400.0 + 1e-7)
        self.assertGreater(height, 168.0)
        self.assertEqual(depth, 30.0)

    def test_missing_family_and_duplicate_logical_names_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing mesh families"):
            arrange_on_virtual_canvas(
                [PackageInstance("MISSING_001", "MISSING")],
                self.meshes,
            )
        with self.assertRaisesRegex(ValueError, "nonempty and unique"):
            arrange_on_virtual_canvas(
                [PackageInstance("DUP", "A"), PackageInstance("DUP", "B")],
                self.meshes,
            )


class R6ExactPackagePlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads((R6 / "config.json").read_text(encoding="utf-8"))
        cls.lower = enumerate_level_inventory(cls.cfg, "lower")
        cls.selected = enumerate_selected_inventory(cls.cfg)

    def test_all_five_plans_are_exact_deterministic_and_topology_derived(self) -> None:
        first = build_release_package_plans(
            prototypes=reversed(_prototype_specs()),
            catalog_mesh_families=reversed(_catalog_mesh_families()),
            one_level_records=reversed(self.lower),
            selected_records=reversed(self.selected),
        )
        second = build_release_package_plans(
            prototypes=_prototype_specs(),
            catalog_mesh_families=_catalog_mesh_families(),
            one_level_records=self.lower,
            selected_records=self.selected,
        )
        self.assertEqual(first, second)
        self.assertEqual(tuple(item.package_id for item in first), PACKAGE_ORDER)
        self.assertEqual(len({item.filename for item in first}), len(first))
        self.assertTrue(all(item.filename.startswith("MODEL_ONLY_R6_") for item in first))
        self.assertEqual(
            EXPECTED_EXACT_PACKAGE_COUNTS[ONE_LEVEL_PACKAGE_ID],
            sum(EXPECTED_ONE_LEVEL_FAMILY_COUNTS.values()),
        )
        self.assertEqual(
            EXPECTED_EXACT_PACKAGE_COUNTS[TWO_LEVEL_PACKAGE_ID],
            2 * sum(EXPECTED_ONE_LEVEL_FAMILY_COUNTS.values()),
        )
        self.assertEqual(first[3].physical_object_count, ONE_LEVEL_PHYSICAL_OBJECT_COUNT)
        self.assertEqual(first[4].physical_object_count, 2 * ONE_LEVEL_PHYSICAL_OBJECT_COUNT)
        self.assertEqual(first[2].physical_object_count, sum(QUALIFICATION_FAMILY_COUNTS.values()))
        self.assertEqual(first[0].physical_object_count, 8)
        self.assertEqual(first[1].physical_object_count, 49)
        self.assertEqual(first[2].physical_object_count, 25)
        self.assertEqual(first[3].physical_object_count, 258)
        self.assertEqual(first[4].physical_object_count, 516)
        self.assertEqual(first[3].level_ids, ("lower",))
        self.assertEqual(first[4].level_ids, ("lower", "upper"))
        for left, right in zip(first, second):
            self.assertEqual(left.plan_sha256, right.plan_sha256)
            self.assertEqual(left.inventory_sha256, right.inventory_sha256)
            payload = left.to_dict()
            self.assertEqual(payload["description"], SAFETY_DESCRIPTION)
            self.assertTrue(payload["model_only"])
            self.assertTrue(payload["experimental"])
            self.assertTrue(payload["unrated"])
            self.assertFalse(payload["embedded_gcode_allowed"])
            self.assertFalse(payload["printer_profile_allowed"])
            self.assertFalse(payload["wall_bores_allowed"])
            self.assertFalse(payload["rails_saddles_or_saddle_pins_allowed"])
            self.assertFalse(payload["cross_level_ties_allowed"])

    def test_worst_case_plan_is_exact_maximum_span_long_wall_taxonomy(self) -> None:
        plan = build_release_package_plans(
            prototypes=_prototype_specs(),
            catalog_mesh_families=_catalog_mesh_families(),
            one_level_records=self.lower,
            selected_records=self.selected,
        )[2]
        by_id = {item.logical_id: item for item in self.lower}
        selected_records = [by_id[item.logical_name] for item in plan.instances]
        self.assertEqual(
            dict(sorted(Counter(item.family for item in selected_records).items())),
            QUALIFICATION_FAMILY_COUNTS,
        )
        self.assertEqual({item.run for item in selected_records}, {"long_wall_5ft"})
        self.assertFalse(any(item.classification == "ornament" for item in selected_records))
        self.assertEqual(
            Counter(
                item.variant
                for item in selected_records
                if item.family == "indexed_vertical_quarter_turn_pin"
            ),
            {"keeper_reach": 1, "front_tie_reach": 1},
        )
        self.assertEqual(
            {item.logical_id for item in selected_records if item.family == "deck_cassette"},
            {
                "lower::long_wall_5ft::deck_cassette::01",
                "lower::long_wall_5ft::deck_cassette::02",
            },
        )

    def test_catalog_is_exactly_one_component_per_all_49_emitted_sources(self) -> None:
        expected = _catalog_mesh_families()
        catalog = build_unique_parts_catalog_plan(reversed(expected))
        self.assertEqual(catalog.physical_object_count, 49)
        self.assertEqual(set(catalog.mesh_families), set(expected))
        self.assertEqual(catalog.title, "Story Corner r6 — all emitted development meshes catalog")
        self.assertEqual(len(catalog.instances), len(catalog.mesh_families))

    def test_catalog_specific_audit_accepts_explicit_coupon_classes_only(self) -> None:
        catalog = build_unique_parts_catalog_plan(_catalog_mesh_families())
        audits = {}
        for index, family in enumerate(catalog.mesh_families, start=1):
            classification = (
                "development_fit_coupon" if index == 49 else "installed_current"
            )
            audits[family] = PackageMeshSourceAudit(
                mesh_family=family,
                source_part_name=family.removeprefix("source::"),
                geometry_validation_passed=True,
                current_interface_geometry=index != 49,
                software_model_package_eligible=index != 49,
                physical_installation_qualified=False,
                production_release_eligible=False,
                placeholder_or_coupon=index == 49,
                wall_bore_count=0,
                rail_or_saddle_geometry=False,
                catalog_classification=classification,
                catalog_inclusion_eligible=True,
            )
        checks = mesh_source_audit_checks(catalog, audits)
        self.assertTrue(all(checks.values()), checks)
        incomplete = dict(audits)
        incomplete.pop(catalog.mesh_families[-1])
        self.assertFalse(
            mesh_source_audit_checks(catalog, incomplete)[
                "catalog_audit_keys_equal_all_emitted_mesh_families"
            ]
        )

    def test_assembly_model_plans_require_current_zero_bore_nonplaceholder_sources(self) -> None:
        plan = build_release_package_plans(
            prototypes=_prototype_specs(),
            catalog_mesh_families=_catalog_mesh_families(),
            one_level_records=self.lower,
            selected_records=self.selected,
        )[3]
        meshes = {family: cuboid((5.0, 5.0, 5.0)) for family in plan.mesh_families}
        with self.assertRaisesRegex(ValueError, "software-model mesh-source audit failed"):
            arrange_package_plan(plan, meshes)
        audits = {
            family: PackageMeshSourceAudit(
                mesh_family=family,
                source_part_name=f"CURRENT_SOURCE::{index:03d}",
                geometry_validation_passed=True,
                current_interface_geometry=True,
                software_model_package_eligible=True,
                physical_installation_qualified=False,
                production_release_eligible=False,
                placeholder_or_coupon=False,
                wall_bore_count=0,
                rail_or_saddle_geometry=False,
                unresolved_interfaces=("R6_IFACE_UNRESOLVED",) if index == 1 else (),
            )
            for index, family in enumerate(plan.mesh_families, start=1)
        }
        with self.assertRaisesRegex(ValueError, "interface_blockers_are_closed"):
            arrange_package_plan(plan, meshes, source_audits=audits)
        first_family = plan.mesh_families[0]
        first = audits[first_family]
        audits[first_family] = replace(
            first,
            unresolved_interfaces=(),
            placeholder_or_coupon=True,
            catalog_classification="development_fit_coupon",
            wall_bore_count=1,
        )
        with self.assertRaisesRegex(ValueError, "placeholder_or_coupon"):
            arrange_package_plan(plan, meshes, source_audits=audits)

    def test_planning_fails_closed_on_missing_role_inventory_or_unsafe_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required roles"):
            build_release_package_plans(
                prototypes=_prototype_specs()[:-1],
                catalog_mesh_families=_catalog_mesh_families(),
                one_level_records=self.lower,
                selected_records=self.selected,
            )
        with self.assertRaisesRegex(ValueError, "exactly 49"):
            build_unique_parts_catalog_plan(_catalog_mesh_families()[:-1])
        with self.assertRaisesRegex(ValueError, "must be unique"):
            build_unique_parts_catalog_plan(
                (*_catalog_mesh_families()[:-1], _catalog_mesh_families()[0])
            )
        unsafe = replace(self.lower[0], level_independent=False)
        with self.assertRaisesRegex(ValueError, "cross-level dependence"):
            build_release_package_plans(
                prototypes=_prototype_specs(),
                catalog_mesh_families=_catalog_mesh_families(),
                one_level_records=(unsafe, *self.lower[1:]),
                selected_records=self.selected,
            )
        cross_level = replace(
            self.lower[0],
            interface_ref="upper::long_wall_5ft::structural_pier_x_corbel::01",
        )
        with self.assertRaisesRegex(ValueError, "interface crosses shelf levels"):
            build_release_package_plans(
                prototypes=_prototype_specs(),
                catalog_mesh_families=_catalog_mesh_families(),
                one_level_records=(cross_level, *self.lower[1:]),
                selected_records=self.selected,
            )
        with self.assertRaisesRegex(ValueError, "saddle"):
            build_unique_parts_catalog_plan(
                (*_catalog_mesh_families()[:-1], "source::legacy_sliding_saddle"),
            )
        with self.assertRaisesRegex(ValueError, "independent exact doubles"):
            build_release_package_plans(
                prototypes=_prototype_specs(),
                catalog_mesh_families=_catalog_mesh_families(),
                one_level_records=self.lower,
                selected_records=self.selected,
                mesh_family_resolver=lambda record: (
                    f"release::{record.level}::{record.family}::{record.variant}"
                ),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
