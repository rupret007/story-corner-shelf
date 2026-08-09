#!/usr/bin/env python3
"""Safety, topology, fit-envelope, and determinism tests for r6 ornament."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np


R6 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R6))

from ornament_access import carrier_coordinate_contract  # noqa: E402

from ornament_geometry import (  # noqa: E402
    KEYHOLE,
    build_ornament_families,
    compact_pier_gravity_keyhole_boss_mesh,
    gravity_keyhole_boss_mesh,
    noncapturing_loose_locator_post_mesh,
    ornament_instances_per_level,
    ornament_topology,
)


def reject_duplicates(pairs: list[tuple[str, object]]) -> dict:
    output: dict = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate JSON key {key!r}")
        output[key] = value
    return output


def mesh_digest(mesh: object) -> str:
    vertices = np.asarray(mesh.vertices, dtype="<f8")
    faces = np.asarray(mesh.faces, dtype="<i8")
    digest = hashlib.sha256()
    digest.update(vertices.tobytes(order="C"))
    digest.update(faces.tobytes(order="C"))
    return digest.hexdigest()


class R6OrnamentGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = json.loads(
            (R6 / "config.json").read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
        )
        cls.instances = ornament_instances_per_level(cls.cfg)
        cls.topology = ornament_topology(cls.cfg)
        cls.families = build_ornament_families(cls.cfg)

    def test_exact_installed_inventory_is_33_per_level_and_66_for_two(self) -> None:
        self.assertEqual(len(self.instances), 33)
        self.assertEqual(len({item.logical_id for item in self.instances}), 33)
        self.assertFalse(any(item.structural_credit for item in self.instances))
        self.assertEqual(
            self.topology,
            {
                "installed_family_count": 8,
                "installed_per_level": 33,
                "installed_selected_two_levels": 66,
                "print_first_coupon_family_count": 2,
                "per_level_by_family": {
                    "corner_fixed_rosette": 1,
                    "corner_floating_return": 1,
                    "ordinary_endcap": 2,
                    "pier_overlay": 11,
                    "return_carrier_left": 3,
                    "return_carrier_right": 3,
                    "through_carrier_left": 6,
                    "through_carrier_right": 6,
                },
                "fine_ornament_structural_credit": False,
            },
        )

    def test_catalog_has_eight_installed_families_plus_two_uninstalled_coupons(self) -> None:
        self.assertEqual(len(self.families), 10)
        installed = {key for key, value in self.families.items() if value.installed}
        coupons = {
            key for key, value in self.families.items() if value.print_first_coupon
        }
        self.assertEqual(installed, set(self.topology["per_level_by_family"]))
        self.assertEqual(
            coupons,
            {
                "print_first_keyhole_male_ladder",
                "print_first_keyhole_female_ladder",
            },
        )
        self.assertTrue(coupons.isdisjoint({item.family_id for item in self.instances}))
        self.assertFalse(any(value.structural_credit for value in self.families.values()))

    def test_keyhole_dimensions_preserve_clearance_travel_and_real_walls(self) -> None:
        spec = KEYHOLE
        self.assertAlmostEqual(
            spec.receiver_head_run_mm - spec.boss_head_run_mm,
            2.0 * spec.clearance_per_face_mm,
        )
        self.assertAlmostEqual(
            spec.receiver_head_y_mm - spec.boss_head_y_mm,
            2.0 * spec.clearance_per_face_mm,
        )
        self.assertAlmostEqual(
            spec.receiver_neck_run_mm - spec.boss_neck_run_y_mm,
            2.0 * spec.clearance_per_face_mm,
        )
        contract = self.cfg["palatine"]["ornament_keyhole_contract"]
        self.assertAlmostEqual(
            contract["elongated_receiver_head_run_mm"],
            spec.receiver_head_run_mm + contract["elongated_total_run_travel_mm"],
        )
        self.assertAlmostEqual(
            contract["elongated_receiver_neck_run_mm"],
            spec.receiver_neck_run_mm + contract["elongated_total_run_travel_mm"],
        )
        chase_w, chase_h = spec.internal_chase_run_y_mm
        outer_w, outer_h = spec.housing_run_y_mm
        self.assertAlmostEqual(outer_w - chase_w, 2.0 * spec.housing_wall_mm)
        self.assertAlmostEqual(outer_h - chase_h, 2.0 * spec.housing_wall_mm)
        self.assertGreaterEqual(chase_w, spec.receiver_head_run_mm)
        self.assertGreaterEqual(
            chase_h,
            spec.receiver_head_y_mm + spec.downward_travel_mm,
        )
        self.assertEqual(spec.rear_lip_mm, 1.6)

    def test_installed_ornament_stops_before_three_mm_unloaded_gap(self) -> None:
        isolation = self.cfg["ornament_isolation"]
        connector_max = float(isolation["connector_chase_depth_zone_mm"][1])
        structure_min = float(isolation["structural_chassis_depth_zone_mm"][0])
        self.assertAlmostEqual(structure_min - connector_max, 3.0)
        for family in self.families.values():
            if family.installed:
                self.assertGreaterEqual(float(family.mesh.bounds[0][2]), -1e-7, family.family_id)
                self.assertLessEqual(float(family.mesh.bounds[1][2]), connector_max + 1e-7, family.family_id)
                self.assertEqual(
                    family.design_metrics.get("connector_chase_max_z_mm", connector_max),
                    connector_max,
                    family.family_id,
                )

    def test_integral_boss_is_local_exception_not_a_printed_object(self) -> None:
        boss = gravity_keyhole_boss_mesh()
        self.assertTrue(boss.is_watertight)
        self.assertEqual(len(boss.split(only_watertight=False)), 1)
        self.assertAlmostEqual(float(boss.bounds[0][2]), 6.0, places=6)
        self.assertAlmostEqual(float(boss.bounds[1][2]), 13.22, places=6)
        self.assertAlmostEqual(
            7.2 * 7.2 * (float(boss.bounds[1][2]) - 13.2),
            1.0368,
            places=4,
        )
        self.assertNotIn("gravity_keyhole_boss", self.families)
        self.assertNotIn("gravity_keyhole_boss", {item.family_id for item in self.instances})
        compact = compact_pier_gravity_keyhole_boss_mesh(self.cfg)
        self.assertTrue(compact.is_watertight)
        self.assertEqual(len(compact.split(only_watertight=False)), 1)
        self.assertAlmostEqual(float(compact.bounds[0][2]), 6.0, places=6)
        self.assertAlmostEqual(float(compact.bounds[1][2]), 13.22, places=6)
        self.assertAlmostEqual(
            4.8 * 4.8 * (float(compact.bounds[1][2]) - 13.2),
            0.4608,
            places=4,
        )
        locator = noncapturing_loose_locator_post_mesh(self.cfg)
        self.assertTrue(locator.is_watertight)
        self.assertEqual(len(locator.split(only_watertight=False)), 1)
        self.assertEqual(tuple(np.round(locator.extents, 6)), (7.2, 7.2, 5.22))
        self.assertAlmostEqual(float(locator.bounds[0][2]), 8.0, places=6)
        self.assertAlmostEqual(float(locator.bounds[1][2]), 13.22, places=6)

    def test_classical_and_deco_detail_counts_are_exact(self) -> None:
        carriers = [
            family for family in self.families.values() if "_carrier_" in family.family_id
        ]
        self.assertEqual(len(carriers), 4)
        for carrier in carriers:
            metrics = carrier.design_metrics
            self.assertEqual(metrics["dentils"], 9)
            self.assertEqual(metrics["sunburst_rays"], 3)
            self.assertEqual(metrics["nested_chevrons"], 3)
            self.assertEqual(metrics["entablature_layer_heights_mm"], [6.0, 9.0, 15.0])
            self.assertEqual(metrics["gravity_receivers"], 3)
        self.assertEqual(self.families["pier_overlay"].design_metrics["flutes"], 6)
        self.assertEqual(
            self.families["pier_overlay"].design_metrics["gravity_receivers"], 2
        )
        self.assertEqual(
            self.families["pier_overlay"].design_metrics[
                "noncapturing_loose_locators"
            ],
            1,
        )
        self.assertEqual(
            self.families["corner_fixed_rosette"].design_metrics["rosette_petals"],
            9,
        )
        self.assertEqual(sum(f.design_metrics["keystone_owner"] for f in carriers), 2)
        self.assertFalse(self.cfg["palatine"]["fine_ornament_structural_credit"])

    def test_carrier_spans_and_handed_keystone_seams_remain_buildable(self) -> None:
        expected = {
            "through_carrier_left": 120.3675,
            "through_carrier_right": 120.3675,
            "return_carrier_left": 111.935,
            "return_carrier_right": 111.935,
        }
        for family_id, width in expected.items():
            family = self.families[family_id]
            self.assertAlmostEqual(family.design_metrics["width_mm"], width, places=6)
            self.assertAlmostEqual(family.design_metrics["height_mm"], 108.0)
            self.assertEqual(family.design_metrics["carrier_zone_mm"], [0.0, 3.2])
            self.assertEqual(
                family.design_metrics["centered_inset_each_nominal_end_mm"],
                0.3,
            )
            self.assertEqual(family.design_metrics["elongated_connector_indices"], [1, 2])
            self.assertEqual(family.design_metrics["fixed_connector_index"], 3)
        for run_role in ("through", "return"):
            self.assertFalse(
                self.families[f"{run_role}_carrier_left"].design_metrics["keystone_owner"]
            )
            self.assertTrue(
                self.families[f"{run_role}_carrier_right"].design_metrics["keystone_owner"]
            )

    def test_every_installed_carrier_aabb_preserves_exact_crown_pier_and_terminal_seams(self) -> None:
        for run_role, bay_count in (("through", 6), ("return", 3)):
            left_id = f"{run_role}_carrier_left"
            right_id = f"{run_role}_carrier_right"
            left_contract = carrier_coordinate_contract(self.cfg, left_id)
            right_contract = carrier_coordinate_contract(self.cfg, right_id)
            nominal = left_contract.nominal_half_span_mm
            self.assertEqual(nominal, right_contract.nominal_half_span_mm)
            left_local = tuple(float(value) for value in self.families[left_id].mesh.bounds[:, 0])
            right_local = tuple(float(value) for value in self.families[right_id].mesh.bounds[:, 0])
            self.assertAlmostEqual(left_local[0], 0.0, delta=1.0e-5)
            self.assertAlmostEqual(right_local[0], 0.0, delta=1.0e-5)
            self.assertAlmostEqual(
                left_local[1], left_contract.physical_width_mm, delta=1.0e-5
            )
            self.assertAlmostEqual(
                right_local[1], right_contract.physical_width_mm, delta=1.0e-5
            )

            installed: list[tuple[tuple[float, float], tuple[float, float]]] = []
            for bay_index in range(bay_count):
                left_spring = 2.0 * nominal * bay_index
                right_spring = 2.0 * nominal * (bay_index + 1)
                left_origin = left_contract.installed_origin_s_mm(left_spring)
                right_origin = right_contract.installed_origin_s_mm(right_spring)
                exact_left = left_contract.installed_s_bounds_mm(left_spring)
                exact_right = right_contract.installed_s_bounds_mm(right_spring)
                self.assertAlmostEqual(
                    exact_right[0] - exact_left[1], 0.6, places=9
                )
                left_bounds = (
                    left_origin + left_local[0],
                    left_origin + left_local[1],
                )
                right_bounds = (
                    right_origin + right_local[0],
                    right_origin + right_local[1],
                )
                installed.append((left_bounds, right_bounds))
                self.assertAlmostEqual(
                    right_bounds[0] - left_bounds[1], 0.6, delta=1.0e-5
                )

            for bay_index in range(bay_count - 1):
                self.assertAlmostEqual(
                    installed[bay_index + 1][0][0]
                    - installed[bay_index][1][1],
                    0.6,
                    delta=1.0e-5,
                )
            self.assertAlmostEqual(installed[0][0][0], 0.3, delta=1.0e-5)
            self.assertAlmostEqual(
                2.0 * nominal * bay_count - installed[-1][1][1],
                0.3,
                delta=1.0e-5,
            )

    def test_corner_finish_is_not_a_rigid_cross_arm_connector(self) -> None:
        fixed = self.families["corner_fixed_rosette"]
        floating = self.families["corner_floating_return"]
        self.assertEqual(floating.design_metrics["axial_float_mm"], 0.8)
        self.assertTrue(any("no mechanical engagement" in note for note in fixed.notes))
        self.assertTrue(any("never locks" in note for note in floating.notes))
        corner_instances = [
            item for item in self.instances if item.placement_role.endswith("cosmetic_corner")
        ]
        self.assertEqual(len(corner_instances), 2)
        self.assertEqual({item.run_id for item in corner_instances}, {"long_wall_5ft", "short_wall_3ft"})

    def test_all_eight_families_use_exact_parent_maps_and_99_integral_bosses(self) -> None:
        keyholes = self.cfg["palatine"]["ornament_keyhole_contract"]
        mapping = keyholes["per_parent_boss_placement_map"]
        installed = {
            key: family
            for key, family in self.families.items()
            if family.installed
        }
        self.assertEqual(set(installed), set(mapping))
        for family_id, family in installed.items():
            self.assertEqual(
                family.design_metrics["receiver_centers_local_x_y_mm"],
                mapping[family_id]["carrier_local_receiver_centers_x_y_mm"],
            )
            expected_fixed = None if family_id == "pier_overlay" else 3
            self.assertEqual(family.design_metrics["fixed_connector_index"], expected_fixed)
            self.assertEqual(family.design_metrics["elongated_connector_indices"], [1, 2])
        self.assertEqual(
            sum(record["installed_count_per_level"] * 3 for record in mapping.values()),
            99,
        )
        standard_gravity = sum(
            record["installed_count_per_level"]
            * record["attachment_feature_types"].count("gravity_keyhole")
            for record in mapping.values()
        )
        compact_gravity = sum(
            record["installed_count_per_level"]
            * record["attachment_feature_types"].count("compact_gravity_keyhole")
            for record in mapping.values()
        )
        locators = sum(
            record["installed_count_per_level"]
            * record["attachment_feature_types"].count(
                "noncapturing_loose_locator"
            )
            for record in mapping.values()
        )
        gravity = standard_gravity + compact_gravity
        self.assertEqual(
            (standard_gravity, compact_gravity, gravity, locators, gravity + locators),
            (66, 22, 88, 11, 99),
        )
        self.assertTrue(keyholes["software_model_mapping_contract_required"])
        self.assertFalse(keyholes["physical_installation_mapping_qualified"])
        self.assertFalse(keyholes["production_release_eligible"])

    def test_overhang_finishes_fit_the_pier_inset_without_crossing_visual_seams(self) -> None:
        expected_width = 30.8325
        self.assertAlmostEqual(
            self.families["ordinary_endcap"].design_metrics["width_mm"],
            expected_width,
        )
        self.assertAlmostEqual(
            self.families["corner_fixed_rosette"].design_metrics["width_mm"],
            expected_width,
        )
        floating = self.families["corner_floating_return"].design_metrics
        self.assertAlmostEqual(floating["width_mm"], 31.1325)
        self.assertEqual(floating["source_solid_x_envelope_mm"], [0.0, 31.1325])
        self.assertEqual(floating["visible_base_x_envelope_mm"], [0.8, 31.1325])
        self.assertEqual(floating["locked_piece_origin_run_s_mm"], -4.4)
        self.assertTrue(floating["remove_before_through_rosette_service"])
        self.assertAlmostEqual(
            expected_width + self.cfg["palatine"]["visual_carrier_contract"]["visual_seam_mm"],
            31.4325,
        )
        self.assertAlmostEqual(
            self.families["pier_overlay"].design_metrics["height_mm"],
            59.6,
        )

    def test_every_mesh_is_watertight_one_body_positive_and_under_180_mm(self) -> None:
        for family in self.families.values():
            mesh = family.mesh
            extents = np.asarray(mesh.extents, dtype=float)
            self.assertTrue(mesh.is_watertight, family.family_id)
            self.assertTrue(mesh.is_volume, family.family_id)
            self.assertGreater(float(mesh.volume), 0.0, family.family_id)
            self.assertEqual(len(mesh.split(only_watertight=False)), 1, family.family_id)
            self.assertLessEqual(float(extents.max()), 180.0 + 1e-7, family.family_id)

    def test_coupon_ladders_are_explicit_fit_tests_not_capacity_tests(self) -> None:
        male = self.families["print_first_keyhole_male_ladder"]
        female = self.families["print_first_keyhole_female_ladder"]
        self.assertEqual(male.design_metrics["bosses"], 4)
        self.assertEqual(female.design_metrics["receivers"], 4)
        self.assertEqual(
            female.design_metrics["clearance_per_face_mm"],
            [0.2, 0.3, 0.4, 0.5],
        )
        for coupon in (male, female):
            self.assertFalse(coupon.installed)
            self.assertTrue(coupon.print_first_coupon)
            self.assertFalse(coupon.structural_credit)
            self.assertTrue(any("PRINT FIRST" in note for note in coupon.notes))

    def test_catalog_generation_is_mesh_deterministic(self) -> None:
        repeated = build_ornament_families(self.cfg)
        self.assertEqual(tuple(repeated), tuple(self.families))
        self.assertEqual(
            {key: mesh_digest(value.mesh) for key, value in repeated.items()},
            {key: mesh_digest(value.mesh) for key, value in self.families.items()},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
