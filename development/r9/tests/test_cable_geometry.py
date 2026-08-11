#!/usr/bin/env python3
"""Contracts for the additive-only R9 outer-bookend cable system."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


R9 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R9))

import cable_geometry as cable  # noqa: E402
import support_geometry as support  # noqa: E402


def assert_one_body(test: unittest.TestCase, mesh) -> None:
    test.assertFalse(mesh.is_empty)
    test.assertTrue(mesh.is_watertight)
    test.assertTrue(mesh.is_winding_consistent)
    test.assertTrue(mesh.is_volume)
    test.assertGreater(float(mesh.volume), 0.0)
    test.assertEqual(len(mesh.split(only_watertight=False)), 1)


class R9CableGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rail = cable.build_two_socket_outer_bookend_rail_fit_coupon()
        cls.blank = cable.build_flush_blank_module()
        cls.organizer = cable.build_multi_cable_organizer_hook_module()

    def test_scope_is_petg_only_zero_rated_and_endpoint_unqualified(self) -> None:
        self.assertTrue(cable.QUALIFICATION_ONLY)
        self.assertFalse(cable.PRODUCTION_READY)
        self.assertFalse(cable.PHYSICAL_QUALIFICATION_COMPLETE)
        self.assertEqual(cable.PRINTED_MATERIAL, "PETG")
        self.assertEqual((cable.RATED_LOAD_KG, cable.RATED_LOAD_LB), (0.0, 0.0))
        self.assertFalse(cable.STRUCTURAL_OR_SHELF_LOAD_CREDIT)
        self.assertFalse(cable.SUPPORT_GEOMETRY_SUBTRACTION_ALLOWED)
        self.assertFalse(cable.ENDPOINT_INSTALLED_CLEARANCE_QUALIFIED)
        self.assertFalse(cable.ENDPOINT_ATTACHMENT_AUTHORED)

    def test_config_limits_two_socket_rails_to_two_outer_bookends_per_level(self) -> None:
        accessory = cable._ACCESSORY_CONFIG
        self.assertTrue(accessory["rails_allowed_on_outer_feature_columns_only"])
        self.assertFalse(accessory["rails_or_pegs_on_compact_supports_allowed"])
        self.assertFalse(accessory["rails_or_pegs_at_inside_corner_allowed"])
        self.assertEqual(accessory["rails_per_level"], 2)
        self.assertEqual(accessory["sockets_per_rail"], 2)
        self.assertEqual(cable.SOCKET_CENTER_Z_MM, (18.0, 44.0))

    def test_rail_is_exact_separate_one_body_with_two_r8_clearance_sockets(self) -> None:
        assert_one_body(self, self.rail)
        np.testing.assert_allclose(self.rail.bounds[0], (0.0, 0.0, 0.0), atol=1.0e-7)
        np.testing.assert_allclose(self.rail.extents, (36.0, 8.8, 62.0), atol=1.0e-6)
        for center_z in cable.SOCKET_CENTER_Z_MM:
            spec = cable.socket_spec(center_z_mm=center_z)
            self.assertEqual(spec.clearance_per_face_mm, 0.4)
            self.assertEqual(spec.cavity_back_y_mm, 2.4)
            self.assertEqual(spec.service_lift_mm, 8.0)
            self.assertAlmostEqual(
                spec.main_pocket_width_mm - cable.LUG_HEAD_WIDTH_MM, 0.8
            )
            self.assertAlmostEqual(
                spec.neck_width_mm - cable.LUG_STEM_WIDTH_MM, 0.8
            )
            self.assertGreater(spec.keyed_pocket_width_mm, spec.main_pocket_width_mm)
            cutters = cable.socket_cutters(center_z_mm=center_z)
            self.assertEqual(len(cutters), 4)
            self.assertTrue(
                all(
                    float(cutter.bounds[0, 1])
                    >= cable.UNINTERRUPTED_BACK_WEB_MM - 1.0e-8
                    for cutter in cutters
                )
            )

        # A section inside the separate rail's back web is one full rectangle.
        section = self.rail.section(
            plane_origin=(0.0, 1.2, 0.0), plane_normal=(0.0, 1.0, 0.0)
        )
        self.assertIsNotNone(section)
        self.assertEqual(len(section.discrete), 1)
        points = np.vstack(section.discrete)
        np.testing.assert_allclose(np.ptp(points, axis=0), (36.0, 0.0, 62.0), atol=1.0e-6)

    def test_building_the_additive_rail_never_changes_the_support_mesh(self) -> None:
        before = support.build_outer_feature_support_candidate()
        before_digest = support.mesh_fingerprint(before)
        _ = cable.build_two_socket_outer_bookend_rail_fit_coupon()
        after = support.build_outer_feature_support_candidate()
        self.assertEqual(before_digest, support.mesh_fingerprint(after))
        self.assertTrue(support.wall_strap_is_uninterrupted(after))
        self.assertEqual(after.euler_number, 0)

    def test_blank_and_multi_cable_comb_share_one_exact_common_key(self) -> None:
        for mesh in (self.blank, self.organizer):
            assert_one_body(self, mesh)
            self.assertAlmostEqual(float(mesh.bounds[0, 1]), -6.0, places=6)
            rear = mesh.vertices[mesh.vertices[:, 1] < -5.9]
            self.assertGreater(len(rear), 0)
            self.assertAlmostEqual(float(rear[:, 0].min()), -7.0, places=6)
            self.assertAlmostEqual(float(rear[:, 0].max()), 5.5, places=6)
            self.assertLessEqual(float(mesh.bounds[0, 2]), -8.0 + 1.0e-7)
            self.assertGreaterEqual(float(mesh.bounds[1, 2]), 8.0 - 1.0e-7)
        self.assertAlmostEqual(float(self.blank.bounds[1, 1]), 3.2, places=6)
        self.assertGreater(float(self.organizer.extents[0]), 25.0)
        self.assertGreater(float(self.organizer.bounds[1, 1]), 20.0)
        front = self.organizer.vertices[self.organizer.vertices[:, 1] > 21.0]
        self.assertGreaterEqual(len(front), 3 * 32)
        self.assertGreater(float(np.ptp(front[:, 2])), 6.9)

    def test_both_modules_insert_up_then_drop_exactly_eight_mm_without_collision(self) -> None:
        for module in (self.blank, self.organizer):
            for station_index, center_z in enumerate(cable.SOCKET_CENTER_Z_MM):
                transforms = cable.seating_transforms(station_index)
                np.testing.assert_allclose(
                    transforms.seated[:3, 3],
                    (18.0, 8.8, center_z),
                    atol=1.0e-12,
                )
                np.testing.assert_allclose(
                    transforms.insertion[:3, 3] - transforms.seated[:3, 3],
                    (0.0, 0.0, 8.0),
                    atol=1.0e-12,
                )
                insertion = cable.transformed_module(
                    module, station_index, insertion=True
                )
                seated = cable.transformed_module(
                    module, station_index, insertion=False
                )
                self.assertAlmostEqual(
                    cable.positive_intersection_volume(self.rail, insertion),
                    0.0,
                    places=7,
                )
                self.assertAlmostEqual(
                    cable.positive_intersection_volume(self.rail, seated),
                    0.0,
                    places=7,
                )
        with self.assertRaises(IndexError):
            cable.seating_transforms(2)

    def test_sampled_install_and_removal_service_paths_are_exact_and_collision_free(self) -> None:
        for module in (self.blank, self.organizer):
            for station_index in range(2):
                path = cable.service_path_transforms(station_index)
                self.assertEqual(path.increment_mm, 1.0)
                self.assertEqual(len(path.insertion_approach), 7)
                self.assertEqual(len(path.gravity_drop), 9)
                self.assertEqual(len(path.removal_lift), 9)
                self.assertEqual(len(path.removal_outward), 7)
                for forward, reverse in zip(
                    path.gravity_drop, reversed(path.removal_lift)
                ):
                    np.testing.assert_allclose(forward, reverse, atol=1.0e-12)
                for forward, reverse in zip(
                    path.insertion_approach, reversed(path.removal_outward)
                ):
                    np.testing.assert_allclose(forward, reverse, atol=1.0e-12)
                for matrix in (*path.insertion_approach, *path.gravity_drop):
                    posed = module.copy()
                    posed.apply_transform(matrix)
                    self.assertAlmostEqual(
                        cable.positive_intersection_volume(self.rail, posed),
                        0.0,
                        places=7,
                    )

    def test_saved_orientations_are_support_free_and_fit_a1_mini_with_margins(self) -> None:
        saved = cable.build_saved_cable_qualification_parts()
        evidence = cable.saved_cable_print_evidence()
        self.assertEqual(tuple(saved), tuple(item.part_name for item in evidence))
        expected_extents = {
            "r9_two_socket_outer_bookend_rail_fit_coupon": (36.0, 62.0, 8.8),
            "r9_flush_blank_cable_module": (20.0, 9.2, 16.0),
            "r9_multi_cable_comb_hook_module": (28.0, 30.5, 16.0),
        }
        expected_layers = {
            "r9_two_socket_outer_bookend_rail_fit_coupon": 44,
            "r9_flush_blank_cable_module": 80,
            "r9_multi_cable_comb_hook_module": 80,
        }
        for item in evidence:
            with self.subTest(part=item.part_name):
                self.assertFalse(item.support_required)
                self.assertEqual(item.support_classification, "support_free")
                self.assertIn("overlaps deposited material below", item.support_evidence)
                self.assertEqual(item.body_count, 1)
                self.assertTrue(item.watertight)
                self.assertTrue(item.winding_consistent)
                self.assertTrue(item.envelope.fits)
                self.assertEqual(
                    cable.saved_layer_island_report(
                        saved[item.part_name]
                    ).sampled_layer_count,
                    expected_layers[item.part_name],
                )
                np.testing.assert_allclose(
                    saved[item.part_name].extents,
                    expected_extents[item.part_name],
                    atol=1.0e-6,
                )
                self.assertTrue(
                    all(
                        required <= available + support.GEOMETRY_EPSILON
                        for required, available in zip(
                            item.envelope.required_build_volume_mm,
                            item.envelope.available_build_volume_mm,
                        )
                    )
                )

    def test_saved_geometry_is_deterministic_and_inventory_is_exact(self) -> None:
        first = cable.build_saved_cable_qualification_parts()
        second = cable.build_saved_cable_qualification_parts()
        self.assertEqual(
            tuple(first),
            (
                "r9_two_socket_outer_bookend_rail_fit_coupon",
                "r9_flush_blank_cable_module",
                "r9_multi_cable_comb_hook_module",
            ),
        )
        self.assertEqual(
            {name: support.mesh_fingerprint(mesh) for name, mesh in first.items()},
            {name: support.mesh_fingerprint(mesh) for name, mesh in second.items()},
        )

    def test_invalid_clearance_and_station_inputs_fail_closed(self) -> None:
        for value in (0.0, -0.1, 1.1, float("nan"), True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    cable.build_two_socket_outer_bookend_rail_fit_coupon(
                        clearance_per_face_mm=value
                    )
                with self.assertRaises(ValueError):
                    cable.build_common_module_base(clearance_per_face_mm=value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
